"""Marina: extrair COVID, calcular métricas diárias e salvar."""
from io import BytesIO
import time

import pandas as pd
import requests

from banco import DADOS, salvar

PAISES = {"BRA": "Brasil", "USA": "Estados Unidos", "CHN": "China", "DEU": "Alemanha", "IND": "Índia"}
FONTE = "https://catalog.ourworldindata.org/garden/covid/latest/compact/compact.csv"
COLUNAS = {"code": "pais_codigo", "date": "data", "new_cases": "casos_novos", "total_cases": "casos_acumulados"}


def transformar(dados):
    tabela = dados.rename(columns=COLUNAS).copy()
    tabela = tabela[tabela["pais_codigo"].isin(PAISES)].copy()
    tabela["data"] = pd.to_datetime(tabela["data"], errors="raise").dt.normalize()
    tabela = tabela[tabela["data"].dt.year.between(2019, 2023)].copy()
    if tabela.empty or tabela.duplicated(["pais_codigo", "data"]).any():
        raise ValueError("COVID sem dados no período ou com país/data duplicados.")
    for coluna in ["casos_novos", "casos_acumulados"]:
        tabela[coluna] = pd.to_numeric(tabela[coluna], errors="coerce")
    tabela["pais"] = tabela["pais_codigo"].map(PAISES)
    tabela = tabela.sort_values(["pais_codigo", "data"]).reset_index(drop=True)
    tabela["media_movel_7d"] = float("nan")
    for _, grupo in tabela.groupby("pais_codigo"):
        # Sete dias de calendário completos; não sete registros separados por meses.
        media = grupo.set_index("data")["casos_novos"].rolling("7D", min_periods=7).mean()
        tabela.loc[grupo.index, "media_movel_7d"] = media.to_numpy()
    anterior = tabela.groupby("pais_codigo")["casos_acumulados"].shift(1)
    intervalo = tabela.groupby("pais_codigo")["data"].diff().dt.days
    tabela["crescimento_casos_pct"] = (tabela["casos_acumulados"] - anterior) / anterior.where((anterior > 0) & (intervalo == 1)) * 100
    return tabela[["pais_codigo", "pais", "data", "casos_novos", "casos_acumulados", "media_movel_7d", "crescimento_casos_pct"]]


def executar(banco=None):
    arquivo = DADOS / "brutos" / "covid.csv"
    if arquivo.exists():
        print("COVID: reutilizando os dados baixados.")
        dados = pd.read_csv(arquivo)
    else:
        for tentativa in range(3):
            try:
                resposta = requests.get(FONTE, timeout=(15, 90))
                resposta.raise_for_status()
                dados = pd.read_csv(BytesIO(resposta.content), usecols=list(COLUNAS))
                break
            except (requests.RequestException, ValueError) as erro:
                print(f"COVID: tentativa {tentativa + 1}/3 falhou.")
                if tentativa == 2:
                    raise RuntimeError("Não foi possível baixar COVID. Tente novamente.") from erro
                time.sleep(2)
    tabela = transformar(dados)
    if set(tabela["pais_codigo"]) != set(PAISES):
        raise ValueError("Faltam países na fonte COVID.")
    # Guarda somente os dados originais do recorte, para não baixar tudo novamente.
    brutos = tabela[["pais_codigo", "data", "casos_novos", "casos_acumulados"]]
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    brutos.to_csv(arquivo, index=False)
    if banco is not None:
        salvar(brutos, "covid_brutos", banco)
    salvar(tabela, "covid", banco)


if __name__ == "__main__":
    executar()
