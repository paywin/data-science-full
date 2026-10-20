"""ETL de tendências temporais — Pessoa 4.

Gera tabelas anuais e variações para casos de COVID-19, PIB e desemprego.

Entradas aceitas:
  1. Uma base integrada (ex.: covid_economia_2019_2023.csv); ou
  2. covid.csv diário + economia_paises_2019_2023.csv anual.

Por padrão, procura os arquivos na mesma pasta do script. Os nomes das
colunas aceitam tanto os CSVs dos ETLs originais quanto a base do dashboard.

Exemplos:
  python etl_tendencias.py
  python etl_tendencias.py --base-integrada minha_base.csv
  python etl_tendencias.py --covid covid.csv --economia economia_paises_2019_2023.csv

Requisitos: pip install pandas
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


PAISES = {
    "BRA": "Brasil",
    "USA": "Estados Unidos",
    "CHN": "China",
    "DEU": "Alemanha",
    "IND": "Índia",
}
ANOS = list(range(2019, 2024))

# Colunas aceitas por métrica: primeiro nome é o padrão do CSV de saída.
ALIASES = {
    "pais_codigo": ("pais_codigo", "code", "iso_code", "codigo_pais"),
    "pais": ("pais", "country", "nome_pais"),
    "ano": ("ano", "year"),
    "casos_novos_ano": ("casos_novos_ano", "casos_novos", "new_cases"),
    "pico_media_movel_7d": ("pico_media_movel_7d", "pico_media_7d", "media_movel_7d"),
    "casos_acumulados_fim_ano": ("casos_acumulados_fim_ano", "total_cases"),
    "cobertura_covid": ("cobertura_covid", "cobertura_dados"),
    "pib_usd_correntes": ("pib_usd_correntes", "pib_usd"),
    "crescimento_pib_real_pct": ("crescimento_pib_real_pct", "pib_crescimento_real_pct", "pib_crescimento"),
    "variacao_pib_usd_correntes_pct": ("variacao_pib_usd_correntes_pct", "pib_var_pct"),
    "desemprego_pct": ("desemprego_pct", "desemprego_percentual"),
    "covid_observado": ("covid_observado",),
    "fase": ("fase",),
}
METRICAS = [
    "casos_novos_ano",
    "pico_media_movel_7d",
    "casos_acumulados_fim_ano",
    "pib_usd_correntes",
    "crescimento_pib_real_pct",
    "variacao_pib_usd_correntes_pct",
    "desemprego_pct",
]


def normalizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza nomes de campos sem alterar os valores da fonte."""
    presentes = {str(c).strip().lower(): c for c in df.columns}
    renomear = {}
    for padrao, aliases in ALIASES.items():
        encontrado = next((presentes[a.lower()] for a in aliases if a.lower() in presentes), None)
        if encontrado is not None:
            renomear[encontrado] = padrao
    return df.rename(columns=renomear)


def ler_csv(caminho: Path, parse_dates: bool = False) -> pd.DataFrame:
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo de entrada não encontrado: {caminho}")
    # utf-8-sig cobre arquivos exportados pelo Excel/Power BI; sep=None detecta ; ou ,.
    return pd.read_csv(caminho, encoding="utf-8-sig", sep=None, engine="python",
                       parse_dates=["date"] if parse_dates else None)


def agrega_covid_diario(covid: pd.DataFrame) -> pd.DataFrame:
    df = normalizar_colunas(covid)
    obrigatorias = {"pais_codigo", "date"}
    faltantes = obrigatorias - set(df.columns)
    if faltantes:
        raise ValueError(f"O CSV diário de COVID não contém as colunas: {sorted(faltantes)}")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "pais_codigo"]).copy()
    df["ano"] = df["date"].dt.year
    df = df[df["ano"].isin(ANOS) & df["pais_codigo"].isin(PAISES)].copy()
    for coluna in ("new_cases", "total_cases", "media_movel_7d"):
        if coluna in df:
            df[coluna] = pd.to_numeric(df[coluna], errors="coerce")

    agregacoes = {}
    if "new_cases" in df:
        agregacoes["casos_novos_ano"] = ("new_cases", lambda s: s.sum(min_count=1))
        agregacoes["dias_com_casos"] = ("new_cases", "count")
    if "total_cases" in df:
        agregacoes["casos_acumulados_fim_ano"] = ("total_cases", "last")
    if "media_movel_7d" in df:
        agregacoes["pico_media_movel_7d"] = ("media_movel_7d", "max")
    if not agregacoes:
        raise ValueError("O CSV diário precisa ter ao menos new_cases, total_cases ou media_movel_7d.")

    df = df.sort_values(["pais_codigo", "date"])
    anual = df.groupby(["pais_codigo", "ano"], as_index=False).agg(**agregacoes)
    if "dias_com_casos" in anual:
        dias_ano = df.groupby(["pais_codigo", "ano"])["date"].size().rename("dias_no_ano")
        anual = anual.merge(dias_ano, on=["pais_codigo", "ano"], how="left")
        anual["cobertura_covid"] = anual["dias_com_casos"] / anual["dias_no_ano"]
        anual = anual.drop(columns=["dias_com_casos", "dias_no_ano"])
    return anual


def grade_pais_ano() -> pd.DataFrame:
    return pd.MultiIndex.from_product(
        [PAISES.keys(), ANOS], names=["pais_codigo", "ano"]
    ).to_frame(index=False)


def carregar_base(args: argparse.Namespace) -> pd.DataFrame:
    if args.base_integrada:
        df = normalizar_colunas(ler_csv(args.base_integrada))
        if "ano" not in df or not ({"pais_codigo", "pais"} & set(df.columns)):
            raise ValueError("A base integrada precisa incluir ano e pais_codigo ou pais.")
    else:
        if not args.covid or not args.economia:
            raise ValueError("Informe --base-integrada ou os dois arquivos --covid e --economia.")
        covid = agrega_covid_diario(ler_csv(args.covid))
        economia = normalizar_colunas(ler_csv(args.economia))
        if not {"pais_codigo", "ano"}.issubset(economia.columns):
            raise ValueError("O CSV econômico precisa incluir pais_codigo e ano.")
        df = grade_pais_ano().merge(covid, on=["pais_codigo", "ano"], how="left")
        df = df.merge(economia.drop(columns=["pais"], errors="ignore"),
                      on=["pais_codigo", "ano"], how="left", suffixes=("", "_economia"))

    df["ano"] = pd.to_numeric(df["ano"], errors="coerce")
    df = df[df["ano"].isin(ANOS)].copy()
    if "pais_codigo" not in df:
        nomes_para_codigo = {v.casefold(): k for k, v in PAISES.items()}
        df["pais_codigo"] = df["pais"].astype(str).str.casefold().map(nomes_para_codigo)
    df = df[df["pais_codigo"].isin(PAISES)].copy()
    if "pais" not in df:
        df["pais"] = df["pais_codigo"].map(PAISES)
    else:
        df["pais"] = df["pais"].fillna(df["pais_codigo"].map(PAISES))

    # Uma linha por país/ano, conforme o contrato dos ETLs anteriores.
    for coluna in METRICAS + ["cobertura_covid"]:
        if coluna in df:
            df[coluna] = pd.to_numeric(df[coluna], errors="coerce")
    chaves = ["pais_codigo", "pais", "ano"]
    if df.duplicated(["pais_codigo", "ano"]).any():
        num = [c for c in METRICAS + ["cobertura_covid"] if c in df]
        outros = [c for c in df if c not in chaves + num]
        regras = {c: "mean" for c in num}
        regras.update({c: "first" for c in outros})
        df = df.groupby(chaves, as_index=False).agg(regras)
    return df.sort_values(["pais_codigo", "ano"]).reset_index(drop=True)


def criar_tabelas(base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dados = base.copy()
    for coluna in METRICAS + ["cobertura_covid"]:
        if coluna not in dados:
            dados[coluna] = float("nan")
    if "fase" not in dados:
        dados["fase"] = dados["ano"].map(
            lambda ano: "Pré-pandemia" if ano == 2019 else
            "Fase crítica" if ano in (2020, 2021) else "Pós-pico"
        )
    # 2019 é explicitamente uma referência pré-pandemia: zero casos observados,
    # e não uma observação diária da COVID. Mantém a distinção no campo de cobertura.
    pre = dados["ano"] == 2019
    for col in ("casos_novos_ano", "pico_media_movel_7d"):
        dados.loc[pre & dados[col].isna(), col] = 0
    if "covid_observado" not in dados:
        dados["covid_observado"] = (~pre).astype(int)
    dados.loc[pre & dados["cobertura_covid"].isna(), "cobertura_covid"] = 1.0
    dados["ano"] = dados["ano"].astype(int)
    dados = dados.sort_values(["pais_codigo", "ano"]).reset_index(drop=True)

    variacoes = dados[["pais_codigo", "pais", "ano", "fase"]].copy()
    base_2019 = dados[dados["ano"] == 2019].set_index("pais_codigo")
    comparadores = {
        "casos_novos_ano": "casos_novos_ano",
        "pico_media_movel_7d": "pico_media_movel_7d",
        "pib_usd_correntes": "pib_usd_correntes",
        "crescimento_pib_real_pct": "crescimento_pib_real_pct",
        "desemprego_pct": "desemprego_pct",
    }
    for campo in comparadores:
        previo = dados.groupby("pais_codigo")[campo].shift(1)
        variacoes[f"variacao_{campo}_absoluta"] = dados[campo] - previo
        percentual = dados[campo].div(previo.where(previo.ne(0))).sub(1).mul(100)
        variacoes[f"variacao_{campo}_pct"] = percentual
        referencia = dados["pais_codigo"].map(base_2019[campo])
        variacoes[f"variacao_{campo}_vs_2019"] = dados[campo] - referencia

    # Para taxas percentuais, a diferença em pontos percentuais é mais intuitiva que % relativo.
    for campo in ("crescimento_pib_real_pct", "desemprego_pct"):
        variacoes[f"variacao_{campo}_pp"] = variacoes[f"variacao_{campo}_absoluta"]

    colunas_anual = ["pais_codigo", "pais", "ano", "fase", "covid_observado",
                     *METRICAS, "cobertura_covid"]
    anual = dados[[c for c in colunas_anual if c in dados]].copy()
    return anual, variacoes, variacoes[variacoes["ano"] == 2020].copy()


def main() -> None:
    pasta = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-integrada", type=Path,
                        default=pasta / "covid_economia_2019_2023.csv")
    parser.add_argument("--covid", type=Path, help="CSV diário gerado pela Pessoa 1")
    parser.add_argument("--economia", type=Path, help="CSV anual gerado pela Pessoa 2")
    parser.add_argument("--saida", type=Path, default=pasta,
                        help="Pasta de saída dos CSVs (padrão: pasta deste script)")
    args = parser.parse_args()

    # A base integrada é a opção padrão. Se ela não existir, tenta os CSVs separados.
    if args.covid and args.economia:
        args.base_integrada = None
    elif args.base_integrada and not args.base_integrada.exists():
        candidato_covid = pasta / "covid.csv"
        candidato_economia = pasta / "economia_paises_2019_2023.csv"
        if candidato_covid.exists() and candidato_economia.exists():
            args.covid, args.economia = candidato_covid, candidato_economia
            args.base_integrada = None
        else:
            parser.error(
                f"Não encontrei {args.base_integrada}. Coloque a base integrada nesta pasta, "
                "ou informe --covid e --economia."
            )

    base = carregar_base(args)
    anual, variacoes, choque_2020 = criar_tabelas(base)
    args.saida.mkdir(parents=True, exist_ok=True)
    arquivos = {
        "tendencias_anual_pais.csv": anual,
        "variacoes_anuais_pais.csv": variacoes,
        "choque_2020_vs_2019.csv": choque_2020,
    }
    for nome, tabela in arquivos.items():
        tabela.to_csv(args.saida / nome, index=False, encoding="utf-8-sig", na_rep="")
        print(f"Gerado: {args.saida / nome} ({len(tabela)} linhas)")
    print(f"Países: {base['pais'].nunique()} | Anos: {base['ano'].min()}–{base['ano'].max()}")
    print("Ausências por indicador na tabela anual:")
    print(anual[METRICAS].isna().sum().to_string())


if __name__ == "__main__":
    main()
