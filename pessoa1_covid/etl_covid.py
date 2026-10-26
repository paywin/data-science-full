"""Pessoa 1: COVID diária no período 2019–2023."""
import argparse
from io import BytesIO
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from infra import ANOS, PAISES, RAIZ, carregar_mongo, obter, salvar_csv

FONTE_COVID = "https://catalog.ourworldindata.org/garden/covid/latest/compact/compact.csv"
COLUNAS = {"date": "data", "code": "pais_codigo", "new_cases": "casos_novos", "total_cases": "casos_acumulados"}


def transformar_covid(dados: pd.DataFrame) -> pd.DataFrame:
    tabela = dados.rename(columns=COLUNAS).copy()
    obrigatorias = {"data", "pais_codigo", "casos_novos", "casos_acumulados"}
    if obrigatorias - set(tabela.columns):
        raise ValueError(f"Faltam colunas no arquivo COVID: {sorted(obrigatorias - set(tabela.columns))}")
    tabela = tabela.loc[tabela["pais_codigo"].isin(PAISES)].copy()
    tabela["data"] = pd.to_datetime(tabela["data"], errors="raise").dt.normalize()
    tabela = tabela.loc[tabela["data"].dt.year.isin(ANOS)].copy()
    if tabela.empty:
        raise ValueError("Nenhum dado de COVID encontrado no período e países definidos.")
    if tabela.duplicated(["pais_codigo", "data"]).any():
        raise ValueError("Há registros duplicados para o mesmo país e data.")
    tabela["pais"] = tabela["pais_codigo"].map(PAISES)
    for coluna in ("casos_novos", "casos_acumulados"):
        tabela[coluna] = pd.to_numeric(tabela[coluna], errors="coerce").replace([float("inf"), -float("inf")], float("nan"))
    tabela = tabela.sort_values(["pais_codigo", "data"]).reset_index(drop=True)
    tabela["media_movel_7d"] = float("nan")
    for _, grupo in tabela.groupby("pais_codigo"):
        serie = grupo.set_index("data")["casos_novos"]
        # Exige sete dias distintos preenchidos; lacunas não são convertidas em zero.
        tabela.loc[grupo.index, "media_movel_7d"] = serie.rolling("7D", min_periods=7).mean().to_numpy()
    anteriores = tabela.groupby("pais_codigo")["casos_acumulados"].shift(1)
    dias = tabela.groupby("pais_codigo")["data"].diff().dt.days
    tabela["crescimento_casos_pct"] = (tabela["casos_acumulados"] - anteriores) / anteriores.where((anteriores > 0) & (dias == 1)) * 100
    return tabela[["pais_codigo", "pais", "data", "casos_novos", "casos_acumulados", "media_movel_7d", "crescimento_casos_pct"]]


def ler_fonte(conteudo):
    dados = pd.read_csv(BytesIO(conteudo), usecols=list(COLUNAS))
    transformar_covid(dados)
    return dados


def executar_etl(entrada: Path | None = None, saida: Path | None = None) -> Path:
    destino = saida or RAIZ / "dados" / "covid.csv"
    if entrada:
        dados = pd.read_csv(entrada, encoding="utf-8-sig")
    else:
        conteudo = obter(FONTE_COVID, cache=RAIZ / "dados/brutos/covid_fonte.csv", validar=ler_fonte)
        dados = ler_fonte(conteudo)
    tabela = transformar_covid(dados)
    if set(tabela["pais_codigo"]) != set(PAISES):
        raise ValueError("Fonte COVID incompleta: faltam países do escopo.")
    brutos = dados.rename(columns=COLUNAS).copy()
    brutos["data"] = pd.to_datetime(brutos["data"], errors="coerce")
    brutos = brutos.loc[brutos["pais_codigo"].isin(PAISES) & brutos["data"].dt.year.isin(ANOS), ["pais_codigo", "data", "casos_novos", "casos_acumulados"]]
    salvar_csv(brutos, destino.parent / "brutos/covid_recorte.csv")
    salvar_csv(tabela, destino)
    carregar_mongo(brutos, "covid_brutos", ["pais_codigo", "data"])
    carregar_mongo(tabela, "covid", ["pais_codigo", "data"])
    return destino


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path)
    parser.add_argument("--saida", type=Path)
    argumentos = parser.parse_args()
    executar_etl(argumentos.entrada, argumentos.saida)
