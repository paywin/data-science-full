Warning: fs was declared with const; use let for reassignable variables.
from pathlib import Path

import pandas as pd

# URL dos dados públicos da COVID-19
url = (
    "https://catalog.ourworldindata.org/"
    "garden/covid/latest/compact/compact.csv"
)

# Caminhos do projeto
pasta_projeto = Path(__file__).resolve().parent.parent
pasta_dados = pasta_projeto / "dados"
arquivo_saida = pasta_dados / "covid.csv"

# Códigos dos países conforme a coluna "code"
paises = ["BRA", "USA", "CHN", "DEU", "IND"]


def executar_etl():
    print("Iniciando o ETL da COVID-19...")

    # EXTRACT: carregar os dados
    df = pd.read_csv(url)

    print(f"Dados recebidos: {len(df)} linhas")

    # Verificar as colunas necessárias
    colunas_obrigatorias = [
        "date",
        "country",
        "code",
        "new_cases",
        "total_cases",
    ]

    faltantes = [
        coluna
        for coluna in colunas_obrigatorias
        if coluna not in df.columns
    ]

    if faltantes:
        raise ValueError(
            f"Colunas não encontradas na fonte: {faltantes}"
        )

    # Selecionar os cinco países
    df = df[df["code"].isin(paises)].copy()

    if df.empty:
        raise ValueError(
            "Nenhum registro encontrado para os países selecionados."
        )

    # Manter somente as colunas necessárias
    df = df[
        ["date", "country", "code", "new_cases", "total_cases"]
    ].copy()

    # TRANSFORM: tratar datas e valores numéricos
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    for coluna in ["new_cases", "total_cases"]:
        df[coluna] = pd.to_numeric(
            df[coluna], errors="coerce"
        )

    # Remover registros sem data ou identificação do país
    df = df.dropna(
        subset=["date", "country", "code"]
    )

    # Ordenar por país e data
    df = df.sort_values(
        ["country", "date"]
    ).reset_index(drop=True)

    # Média móvel de 7 dias
    df["media_movel_7d"] = (
        df.groupby("country")["new_cases"]
        .transform(
            lambda serie: serie.rolling(
                window=7, min_periods=1
            ).mean()
        )
    )

    # Crescimento percentual dos casos acumulados
    casos_anteriores = (
        df.groupby("country")["total_cases"].shift(1)
    )

    df["crescimento_percentual"] = (
        (
            df["total_cases"] - casos_anteriores
        )
        / casos_anteriores.where(casos_anteriores > 0)
    ) * 100

    # LOAD: criar a pasta e salvar o CSV
    pasta_dados.mkdir(parents=True, exist_ok=True)

    df.to_csv(
        arquivo_saida,
        index=False,
        na_rep=""
    )

    print("\nETL concluído com sucesso!")
    print(f"Arquivo salvo em: {arquivo_saida}")
    print(f"Total de registros processados: {len(df)}")
    print("\nPrévia dos dados:")
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    try:
        executar_etl()
    except Exception as erro:
        print(f"Erro durante o ETL: {erro}")
        raise