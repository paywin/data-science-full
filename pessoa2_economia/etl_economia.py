"""Pessoa 2: Banco Mundial, cinco países, 2019–2023, cache por indicador/página."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from infra import ANOS, PAISES, RAIZ, LOG, carregar_mongo, obter, salvar_csv

INDICADORES = {
    "NY.GDP.MKTP.CD": "pib_usd_correntes",
    "NY.GDP.MKTP.KD.ZG": "crescimento_pib_real_pct",
    "SL.UEM.TOTL.ZS": "desemprego_pct",
    "SP.POP.TOTL": "populacao",
}


def validar_resposta(conteudo):
    dados = json.loads(conteudo)
    if not isinstance(dados, list) or len(dados) != 2 or not isinstance(dados[0], dict) or not isinstance(dados[1], list):
        raise ValueError("Resposta inválida ou vazia do Banco Mundial")
    if not dados[1] or int(dados[0].get("pages", 0)) < 1:
        raise ValueError("Banco Mundial não retornou observações")
    for item in dados[1]:
        if not isinstance(item, dict) or item.get("countryiso3code") not in PAISES or str(item.get("date")) not in {str(a) for a in ANOS} or "value" not in item:
            raise ValueError("Registro econômico fora do contrato esperado")
    return dados


def buscar_indicador(codigo: str, coluna: str) -> pd.DataFrame:
    registros = []
    respostas_brutas = []
    pagina = 1
    url = f"https://api.worldbank.org/v2/country/{';'.join(PAISES)}/indicator/{codigo}"
    while True:
        parametros = {"format": "json", "date": "2019:2023", "per_page": 1000, "page": pagina}
        def validar_indicador(conteudo):
            _, itens_validacao = validar_resposta(conteudo)
            if any(item.get("indicator", {}).get("id") != codigo for item in itens_validacao):
                raise ValueError(f"Indicador incorreto na resposta de {codigo}")
        conteudo = obter(url, params=parametros, cache=RAIZ / f"dados/brutos/banco_mundial/{codigo}_2019_2023_p{pagina}.json", validar=validar_indicador)
        metadados, itens = validar_resposta(conteudo)
        for item in itens:
            if item.get("indicator", {}).get("id") != codigo:
                raise ValueError(f"Indicador incorreto na resposta de {codigo}")
            registros.append({"pais_codigo": item["countryiso3code"], "ano": int(item["date"]), coluna: item["value"]})
            respostas_brutas.append({"pais_codigo": item["countryiso3code"], "ano": int(item["date"]), "indicador": codigo, "resposta_original": item})
        if pagina >= int(metadados["pages"]):
            break
        pagina += 1
        if pagina > 100:
            raise ValueError("Paginação excessiva na API econômica")
    tabela = pd.DataFrame(registros, columns=["pais_codigo", "ano", coluna])
    if tabela.duplicated(["pais_codigo", "ano"]).any():
        raise ValueError(f"A API retornou dados duplicados para {codigo}")
    tabela[coluna] = pd.to_numeric(tabela[coluna], errors="coerce").replace([float("inf"), -float("inf")], float("nan"))
    if set(tabela["pais_codigo"]) != set(PAISES) or not tabela[coluna].notna().any():
        raise ValueError(f"Indicador {codigo} incompleto ou sem valores válidos")
    tabela.attrs["brutos"] = respostas_brutas
    return tabela


def montar_economia(tabelas: dict[str, pd.DataFrame]) -> pd.DataFrame:
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
    brutos = []
    for codigo, coluna in INDICADORES.items():
        LOG.info("Banco Mundial: buscando %s", coluna)
        tabelas[coluna] = buscar_indicador(codigo, coluna)
        brutos.append(pd.DataFrame(tabelas[coluna].attrs["brutos"]))
    economia = montar_economia(tabelas)
    arquivo = destino / "economia_paises_2019_2023.csv"
    resumo = economia.groupby(["pais_codigo", "pais"], as_index=False)[list(INDICADORES.values())].agg(lambda serie: int(serie.isna().sum()))
    salvar_csv(economia, arquivo)
    salvar_csv(resumo, destino / "resumo_valores_ausentes.csv")
    carregar_mongo(pd.concat(brutos, ignore_index=True), "economia_brutos", ["pais_codigo", "ano", "indicador"])
    carregar_mongo(economia, "economia", ["pais_codigo", "ano"])
    carregar_mongo(resumo, "resumo_valores_ausentes", ["pais_codigo"])
    return arquivo


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path)
    argumentos = parser.parse_args()
    executar_etl(argumentos.saida)
