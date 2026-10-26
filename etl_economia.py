"""Emily: extrair indicadores do Banco Mundial por país e ano."""
import json
import time

import pandas as pd
import requests

from banco import DADOS, salvar
from etl_covid import PAISES

INDICADORES = {
    "NY.GDP.MKTP.CD": "pib_usd_correntes",
    "NY.GDP.MKTP.KD.ZG": "crescimento_pib_real_pct",
    "SL.UEM.TOTL.ZS": "desemprego_pct",
    "SP.POP.TOTL": "populacao",
}


def validar(resposta, codigo):
    if not isinstance(resposta, list) or len(resposta) != 2 or not isinstance(resposta[0], dict):
        raise ValueError("Resposta inesperada do Banco Mundial.")
    if int(resposta[0].get("pages", 0)) != 1 or not isinstance(resposta[1], list) or not resposta[1]:
        raise ValueError("Resposta vazia ou incompleta do Banco Mundial.")
    for item in resposta[1]:
        if item.get("countryiso3code") not in PAISES or item.get("indicator", {}).get("id") != codigo or item.get("date") not in [str(a) for a in range(2019, 2024)]:
            raise ValueError("País, indicador ou ano inesperado na resposta.")


def buscar(codigo):
    url = f"https://api.worldbank.org/v2/country/{';'.join(PAISES)}/indicator/{codigo}"
    for tentativa in range(3):
        try:
            resposta = requests.get(url, params={"format": "json", "date": "2019:2023", "per_page": 1000}, timeout=(15, 90))
            resposta.raise_for_status()
            dados = resposta.json()
            validar(dados, codigo)
            return dados
        except (requests.RequestException, ValueError) as erro:
            print(f"Banco Mundial: {codigo}, tentativa {tentativa + 1}/3 falhou.")
            if tentativa == 2:
                raise RuntimeError(f"Não foi possível buscar {codigo}. Execute novamente; as consultas concluídas foram guardadas.") from erro
            time.sleep(2)


def transformar(respostas):
    tabela = pd.MultiIndex.from_product([PAISES, range(2019, 2024)], names=["pais_codigo", "ano"]).to_frame(index=False)
    for codigo, coluna in INDICADORES.items():
        validar(respostas[codigo], codigo)
        linhas = [{"pais_codigo": item["countryiso3code"], "ano": int(item["date"]), coluna: item.get("value")} for item in respostas[codigo][1]]
        indicador = pd.DataFrame(linhas)
        indicador[coluna] = pd.to_numeric(indicador[coluna], errors="coerce")
        if not indicador[coluna].notna().any():
            raise ValueError(f"Indicador sem valores: {codigo}")
        tabela = tabela.merge(indicador, on=["pais_codigo", "ano"], how="left", validate="one_to_one")
    tabela.insert(1, "pais", tabela["pais_codigo"].map(PAISES))
    return tabela.sort_values(["pais_codigo", "ano"])


def executar(banco=None):
    arquivo = DADOS / "brutos" / "economia.json"
    respostas = json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else {}
    for codigo in INDICADORES:
        if codigo not in respostas:
            print(f"Banco Mundial: buscando {INDICADORES[codigo]}...")
            respostas[codigo] = buscar(codigo)
            arquivo.parent.mkdir(parents=True, exist_ok=True)
            temporario = arquivo.with_suffix(".tmp")
            temporario.write_text(json.dumps(respostas), encoding="utf-8")
            temporario.replace(arquivo)
    tabela = transformar(respostas)
    if banco is not None:
        originais = [item for resposta in respostas.values() for item in resposta[1]]
        salvar(pd.DataFrame(originais), "economia_brutos", banco)
    print("Valores econômicos ausentes:", int(tabela[list(INDICADORES.values())].isna().sum().sum()))
    salvar(tabela, "economia_paises_2019_2023", banco)


if __name__ == "__main__":
    executar()
