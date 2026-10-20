"""Pessoa 2: extrai indicadores anuais do Banco Mundial (2019 a 2023)."""

import argparse
from pathlib import Path

import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parents[1]
PAISES = {"BRA": "Brasil", "USA": "Estados Unidos", "CHN": "China", "DEU": "Alemanha", "IND": "Índia"}
ANOS = range(2019, 2024)
INDICADORES = {
    "NY.GDP.MKTP.CD": "pib_usd_correntes",
    "NY.GDP.MKTP.KD.ZG": "crescimento_pib_real_pct",
    "SL.UEM.TOTL.ZS": "desemprego_pct",
    "SP.POP.TOTL": "populacao",
}


def buscar_indicador(codigo: str, coluna: str) -> pd.DataFrame:
    """Consulta a API por país, rejeitando resposta inválida sem gerar dados fictícios."""
    registros = []
    for pais_codigo in PAISES:
        url = f"https://api.worldbank.org/v2/country/{pais_codigo}/indicator/{codigo}"
        resposta = requests.get(url, params={"format": "json", "date": "2019:2023", "per_page": 100}, timeout=40)
        resposta.raise_for_status()
        conteudo = resposta.json()
        if not isinstance(conteudo, list) or len(conteudo) < 2 or (conteudo[1] is not None and not isinstance(conteudo[1], list)):
            raise ValueError(f"Resposta inesperada da API do Banco Mundial para {pais_codigo}/{codigo}")
        for item in conteudo[1] or []:
            if str(item.get("date", "")).isdigit():
                registros.append({"pais_codigo": pais_codigo, "ano": int(item["date"]), coluna: item.get("value")})
    tabela = pd.DataFrame(registros, columns=["pais_codigo", "ano", coluna])
    if tabela.duplicated(["pais_codigo", "ano"]).any():
        raise ValueError(f"A API retornou dados duplicados para {codigo}")
    tabela[coluna] = pd.to_numeric(tabela[coluna], errors="coerce")
    return tabela


def montar_economia(tabelas: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Garante 25 pares país/ano e mantém valores desconhecidos como NaN."""
    economia = pd.MultiIndex.from_product([PAISES, ANOS], names=["pais_codigo", "ano"]).to_frame(index=False)
    for coluna in INDICADORES.values():
        if coluna not in tabelas:
            raise ValueError(f"Indicador não fornecido: {coluna}")
        economia = economia.merge(tabelas[coluna], on=["pais_codigo", "ano"], how="left", validate="one_to_one")
    economia.insert(1, "pais", economia["pais_codigo"].map(PAISES))
    return economia.sort_values(["pais_codigo", "ano"]).reset_index(drop=True)


def executar_etl(saida: Path | None = None) -> Path:
    destino = saida or RAIZ / "dados"
    tabelas = {}
    for codigo, coluna in INDICADORES.items():
        print(f"Banco Mundial: buscando {coluna}...")
        tabelas[coluna] = buscar_indicador(codigo, coluna)
    economia = montar_economia(tabelas)
    colunas = list(INDICADORES.values())
    if economia[colunas].notna().sum().sum() == 0:
        raise ValueError("A API não retornou valores econômicos válidos; nenhum CSV foi gravado.")
    destino.mkdir(parents=True, exist_ok=True)
    arquivo = destino / "economia_paises_2019_2023.csv"
    economia.to_csv(arquivo, index=False, encoding="utf-8-sig")
    resumo = economia.groupby(["pais_codigo", "pais"], as_index=False)[colunas].agg(lambda serie: int(serie.isna().sum()))
    resumo.to_csv(destino / "resumo_valores_ausentes.csv", index=False, encoding="utf-8-sig")
    print(f"Economia: {len(economia)} registros -> {arquivo}")
    return arquivo


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, help="Pasta de CSVs gerados")
    argumentos = parser.parse_args()
    executar_etl(argumentos.saida)
