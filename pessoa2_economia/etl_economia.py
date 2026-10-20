Warning: fs was declared with const; use let for reassignable variables.
"""
ETL de indicadores socioeconômicos — Pessoa 2

Busca PIB e desemprego no Banco Mundial para 5 países (2019–2023),
organiza os dados por país/ano, trata valores ausentes e salva CSVs.

Como executar:
    pip install pandas requests
    python etl_economia.py
"""

import requests
import pandas as pd

# Países escolhidos no planejamento do projeto
PAISES = {
    "BRA": "Brasil",
    "USA": "Estados Unidos",
    "CHN": "China",
    "DEU": "Alemanha",
    "IND": "Índia",
}

ANO_INICIAL = 2019
ANO_FINAL = 2023

# Indicadores do Banco Mundial:
# NY.GDP.MKTP.CD = PIB (US$ correntes)
# SL.UEM.TOTL.ZS = Desemprego (% da força de trabalho)
INDICADORES = {
    "NY.GDP.MKTP.CD": "pib_usd",
    "SL.UEM.TOTL.ZS": "desemprego_percentual",
}


def buscar_indicador(codigo_indicador, nome_coluna):
    """Busca um indicador no Banco Mundial e devolve uma tabela organizada."""
    codigos_paises = ";".join(PAISES.keys())
    url = (
        "https://api.worldbank.org/v2/country/"
        f"{codigos_paises}/indicator/{codigo_indicador}"
    )
    parametros = {
        "format": "json",
        "date": f"{ANO_INICIAL}:{ANO_FINAL}",
        "per_page": 2000,
    }

    resposta = requests.get(url, params=parametros, timeout=30)
    resposta.raise_for_status()
    dados_json = resposta.json()

    # A API retorna os dados na segunda posição da lista
    registros = dados_json[1] if len(dados_json) > 1 else []

    linhas = []
    for item in registros:
        linhas.append({
            "pais_codigo": item.get("countryiso3code"),
            "pais": item.get("country", {}).get("value"),
            "ano": int(item["date"]),
            nome_coluna: item.get("value"),
        })

    return pd.DataFrame(linhas)


def executar_etl():
    """Executa a extração, limpeza e gravação dos arquivos."""
    tabelas = []

    for codigo_indicador, nome_coluna in INDICADORES.items():
        print(f"Buscando {nome_coluna}...")
        tabela = buscar_indicador(codigo_indicador, nome_coluna)
        tabelas.append(tabela)

    # Junta PIB e desemprego usando país e ano como chave
    economia = tabelas[0].merge(
        tabelas[1],
        on=["pais_codigo", "pais", "ano"],
        how="outer"
    )

    # Garante que todos os países e anos estejam representados
    anos = list(range(ANO_INICIAL, ANO_FINAL + 1))
    grade = pd.MultiIndex.from_product(
        [PAISES.keys(), anos],
        names=["pais_codigo", "ano"]
    ).to_frame(index=False)

    economia = grade.merge(
        economia,
        on=["pais_codigo", "ano"],
        how="left"
    )

    # Preenche o nome do país caso algum indicador esteja ausente
    economia["pais"] = economia["pais"].fillna(
        economia["pais_codigo"].map(PAISES)
    )

    # Mantém valores ausentes como NaN (não inventa dados).
    # Também gera uma tabela simples com a quantidade de ausências.
    colunas_indicadores = ["pib_usd", "desemprego_percentual"]
    resumo_ausentes = (
        economia.groupby("pais")[colunas_indicadores]
        .apply(lambda grupo: grupo.isna().sum())
        .reset_index()
    )

    # Ordena para facilitar o uso na análise e no Power BI
    economia = economia.sort_values(["pais", "ano"]).reset_index(drop=True)

    economia.to_csv("economia_paises_2019_2023.csv", index=False, encoding="utf-8-sig")
    resumo_ausentes.to_csv("resumo_valores_ausentes.csv", index=False, encoding="utf-8-sig")

    print("\nETL concluído!")
    print("Arquivo principal: economia_paises_2019_2023.csv")
    print("Resumo de ausências: resumo_valores_ausentes.csv")
    print(f"Total de linhas: {len(economia)}")


if __name__ == "__main__":
    executar_etl()
