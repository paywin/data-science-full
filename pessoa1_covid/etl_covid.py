"""Pessoa 1: extrai e padroniza os dados diários de COVID-19."""

import argparse
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
FONTE_COVID = "https://catalog.ourworldindata.org/garden/covid/latest/compact/compact.csv"
PAISES = {"BRA": "Brasil", "USA": "Estados Unidos", "CHN": "China", "DEU": "Alemanha", "IND": "Índia"}
COLUNAS = {"date": "data", "code": "pais_codigo", "new_cases": "casos_novos", "total_cases": "casos_acumulados"}


def transformar_covid(dados: pd.DataFrame) -> pd.DataFrame:
    """Aceita a fonte original ou um CSV já padronizado; preserva ausências."""
    tabela = dados.rename(columns=COLUNAS).copy()
    obrigatorias = {"data", "pais_codigo", "casos_novos", "casos_acumulados"}
    faltantes = obrigatorias - set(tabela.columns)
    if faltantes:
        raise ValueError(f"Faltam colunas no arquivo COVID: {sorted(faltantes)}")
    tabela["data"] = pd.to_datetime(tabela["data"], errors="coerce")
    tabela = tabela.loc[tabela["pais_codigo"].isin(PAISES)].dropna(subset=["data"]).copy()
    if tabela.empty:
        raise ValueError("Nenhum dado de COVID encontrado para os países definidos.")
    if tabela.duplicated(["pais_codigo", "data"]).any():
        raise ValueError("Há registros duplicados para o mesmo país e data.")
    tabela["pais"] = tabela["pais_codigo"].map(PAISES)
    for coluna in ("casos_novos", "casos_acumulados"):
        tabela[coluna] = pd.to_numeric(tabela[coluna], errors="coerce")
    tabela = tabela.sort_values(["pais_codigo", "data"]).reset_index(drop=True)
    tabela["media_movel_7d"] = tabela.groupby("pais_codigo")["casos_novos"].transform(
        lambda valores: valores.rolling(7, min_periods=1).mean()
    )
    anteriores = tabela.groupby("pais_codigo")["casos_acumulados"].shift(1)
    tabela["crescimento_casos_pct"] = (
        (tabela["casos_acumulados"] - anteriores) / anteriores.where(anteriores > 0) * 100
    )
    return tabela[["pais_codigo", "pais", "data", "casos_novos", "casos_acumulados",
                   "media_movel_7d", "crescimento_casos_pct"]]


def executar_etl(entrada: Path | None = None, saida: Path | None = None) -> Path:
    """Extrai, transforma e grava CSV diário centralizado em dados/."""
    origem = entrada if entrada is not None else FONTE_COVID
    destino = saida or RAIZ / "dados" / "covid.csv"
    dados = pd.read_csv(origem, encoding="utf-8-sig" if entrada else "utf-8")
    tabela = transformar_covid(dados)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(destino, index=False, encoding="utf-8-sig")
    print(f"COVID: {len(tabela)} registros -> {destino}")
    return destino


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, help="CSV local em vez da fonte online")
    parser.add_argument("--saida", type=Path, help="Destino do CSV padronizado")
    argumentos = parser.parse_args()
    executar_etl(argumentos.entrada, argumentos.saida)
