"""Pessoa 3: integra os ETLs de COVID e economia e calcula associações descritivas."""

import argparse
import calendar
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
PAISES = {"BRA": "Brasil", "USA": "Estados Unidos", "CHN": "China", "DEU": "Alemanha", "IND": "Índia"}
ANOS = range(2019, 2024)
RENOMEAR_COVID = {"date": "data", "code": "pais_codigo", "new_cases": "casos_novos",
                  "total_cases": "casos_acumulados", "country": "pais"}
RENOMEAR_ECONOMIA = {"pib_usd": "pib_usd_correntes", "pib_crescimento_real_pct": "crescimento_pib_real_pct",
                     "desemprego_percentual": "desemprego_pct"}


def agregar_covid(dados: pd.DataFrame) -> pd.DataFrame:
    """Agrega os registros diários por país/ano sem preencher ausências com zero."""
    tabela = dados.rename(columns=RENOMEAR_COVID).copy()
    obrigatorias = {"data", "pais_codigo", "casos_novos", "casos_acumulados"}
    if obrigatorias - set(tabela.columns):
        raise ValueError(f"CSV COVID sem colunas: {sorted(obrigatorias - set(tabela.columns))}")
    tabela["data"] = pd.to_datetime(tabela["data"], errors="coerce")
    tabela = tabela.dropna(subset=["data"]).copy()
    tabela["ano"] = tabela["data"].dt.year
    tabela = tabela.loc[tabela["pais_codigo"].isin(PAISES) & tabela["ano"].isin(ANOS)].copy()
    if tabela.duplicated(["pais_codigo", "data"]).any():
        raise ValueError("COVID contém datas duplicadas para um mesmo país.")
    for coluna in ("casos_novos", "casos_acumulados"):
        tabela[coluna] = pd.to_numeric(tabela[coluna], errors="coerce")
    if "media_movel_7d" not in tabela:
        tabela = tabela.sort_values(["pais_codigo", "data"])
        tabela["media_movel_7d"] = tabela.groupby("pais_codigo")["casos_novos"].transform(
            lambda serie: serie.rolling(7, min_periods=1).mean()
        )
    else:
        tabela["media_movel_7d"] = pd.to_numeric(tabela["media_movel_7d"], errors="coerce")
    tabela = tabela.sort_values(["pais_codigo", "data"])
    agregado = tabela.groupby(["pais_codigo", "ano"], as_index=False).agg(
        casos_novos_ano=("casos_novos", lambda serie: serie.sum(min_count=1)),
        pico_media_movel_7d=("media_movel_7d", "max"),
        casos_acumulados_fim_ano=("casos_acumulados", "last"),
        dias_com_casos=("casos_novos", "count"),
        dias_observados=("data", "nunique"),
    )
    agregado["dias_calendario"] = agregado["ano"].map(lambda ano: 366 if calendar.isleap(int(ano)) else 365)
    agregado["cobertura_covid"] = agregado["dias_com_casos"] / agregado["dias_calendario"]
    agregado["covid_observado"] = 1
    return agregado.drop(columns=["dias_com_casos", "dias_observados", "dias_calendario"])


def integrar_dados(covid: pd.DataFrame, economia: pd.DataFrame) -> pd.DataFrame:
    """Cria uma linha por país/ano; não confunde 2019 com dados COVID observados."""
    economica = economia.rename(columns=RENOMEAR_ECONOMIA).copy()
    obrigatorias = {"pais_codigo", "ano", "pib_usd_correntes", "desemprego_pct"}
    if obrigatorias - set(economica.columns):
        raise ValueError(f"CSV econômico sem colunas: {sorted(obrigatorias - set(economica.columns))}")
    economica["ano"] = pd.to_numeric(economica["ano"], errors="raise").astype(int)
    economica = economica.loc[economica["pais_codigo"].isin(PAISES) & economica["ano"].isin(ANOS)].copy()
    if economica.duplicated(["pais_codigo", "ano"]).any():
        raise ValueError("CSV econômico contém país/ano duplicado.")
    for coluna in ("pib_usd_correntes", "desemprego_pct", "crescimento_pib_real_pct", "populacao"):
        if coluna not in economica:
            economica[coluna] = float("nan")
        economica[coluna] = pd.to_numeric(economica[coluna], errors="coerce")
    grade = pd.MultiIndex.from_product([PAISES, ANOS], names=["pais_codigo", "ano"]).to_frame(index=False)
    tabela = grade.merge(agregar_covid(covid), on=["pais_codigo", "ano"], how="left", validate="one_to_one")
    tabela = tabela.merge(economica.drop(columns=["pais"], errors="ignore"), on=["pais_codigo", "ano"],
                          how="left", validate="one_to_one")
    tabela.insert(1, "pais", tabela["pais_codigo"].map(PAISES))
    tabela = tabela.sort_values(["pais_codigo", "ano"]).reset_index(drop=True)
    tabela["covid_observado"] = tabela["covid_observado"].fillna(0).astype(int)
    tabela["fase"] = tabela["ano"].map(lambda ano: "Pré-pandemia" if ano == 2019
                                     else ("Fase crítica" if ano <= 2021 else "Pós-pico"))
    # 2019 é referência pré-pandemia, não uma medição diária de COVID.
    tabela.loc[tabela["ano"] == 2019, ["casos_novos_ano", "pico_media_movel_7d"]] = 0
    tabela.loc[tabela["ano"] == 2019, "cobertura_covid"] = float("nan")
    anterior = tabela.groupby("pais_codigo")["pib_usd_correntes"].shift(1)
    tabela["variacao_pib_usd_correntes_pct"] = (
        (tabela["pib_usd_correntes"] / anterior.where(anterior > 0) - 1) * 100
    )
    populacao_valida = tabela["populacao"].where(tabela["populacao"] > 0)
    tabela["casos_por_milhao"] = tabela["casos_novos_ano"] / populacao_valida * 1_000_000
    tabela["pico_media_movel_por_milhao"] = tabela["pico_media_movel_7d"] / populacao_valida * 1_000_000
    return tabela


def calcular_correlacoes(base: pd.DataFrame) -> pd.DataFrame:
    """Pearson/Spearman por ano e agregado; associação não implica causalidade."""
    colunas = ["escopo", "ano", "indicador_covid", "indicador_economico", "observacoes", "pearson_r", "spearman_rho"]
    pares = [("casos_por_milhao", "crescimento_pib_real_pct"),
             ("casos_por_milhao", "desemprego_pct"),
             ("pico_media_movel_por_milhao", "crescimento_pib_real_pct"),
             ("pico_media_movel_por_milhao", "desemprego_pct")]
    registros = []
    filtrada = base.loc[(base["ano"] >= 2020) & (base["covid_observado"] == 1)]
    grupos = [("geral", "2020-2023", filtrada)] + [("anual", str(ano), filtrada.loc[filtrada["ano"] == ano])
                                                  for ano in range(2020, 2024)]
    for escopo, ano, grupo in grupos:
        for indicador_covid, indicador_economico in pares:
            valores = grupo[[indicador_covid, indicador_economico]].dropna()
            if len(valores) < 3 or any(valores[col].nunique() < 2 for col in valores.columns):
                pearson = spearman = float("nan")
            else:
                pearson = valores[indicador_covid].corr(valores[indicador_economico], method="pearson")
                spearman = valores[indicador_covid].corr(valores[indicador_economico], method="spearman")
            registros.append({"escopo": escopo, "ano": ano, "indicador_covid": indicador_covid,
                              "indicador_economico": indicador_economico, "observacoes": len(valores),
                              "pearson_r": pearson, "spearman_rho": spearman})
    return pd.DataFrame(registros, columns=colunas)


def comparar_2020(base: pd.DataFrame) -> pd.DataFrame:
    ano_2019 = base.loc[base["ano"] == 2019].set_index("pais_codigo")
    ano_2020 = base.loc[base["ano"] == 2020].set_index("pais_codigo")
    comparacao = ano_2020[["pais", "casos_novos_ano", "casos_por_milhao", "crescimento_pib_real_pct"]].copy()
    comparacao["variacao_desemprego_pp"] = ano_2020["desemprego_pct"] - ano_2019["desemprego_pct"]
    comparacao["variacao_pib_usd_correntes_pct"] = ano_2020["variacao_pib_usd_correntes_pct"]
    return comparacao.reset_index()


def executar_etl(caminho_covid: Path | None = None, caminho_economia: Path | None = None,
                  saida: Path | None = None) -> Path:
    origem_covid = caminho_covid or RAIZ / "dados" / "covid.csv"
    origem_economia = caminho_economia or RAIZ / "dados" / "economia_paises_2019_2023.csv"
    destino = saida or RAIZ / "dados"
    covid = pd.read_csv(origem_covid, encoding="utf-8-sig")
    economia = pd.read_csv(origem_economia, encoding="utf-8-sig")
    base = integrar_dados(covid, economia)
    destino.mkdir(parents=True, exist_ok=True)
    arquivo = destino / "base_integrada_pais_ano.csv"
    base.to_csv(arquivo, index=False, encoding="utf-8-sig")
    calcular_correlacoes(base).to_csv(destino / "correlacoes.csv", index=False, encoding="utf-8-sig")
    comparar_2020(base).to_csv(destino / "variacao_2020_vs_2019.csv", index=False, encoding="utf-8-sig")
    print(f"Impacto: {len(base)} registros -> {arquivo}")
    return arquivo


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--covid", type=Path)
    parser.add_argument("--economia", type=Path)
    parser.add_argument("--saida", type=Path)
    argumentos = parser.parse_args()
    executar_etl(argumentos.covid, argumentos.economia, argumentos.saida)
