"""Configuração, extração HTTP e persistência compartilhadas pelos quatro ETLs."""
import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parent
PAISES = {"BRA": "Brasil", "USA": "Estados Unidos", "CHN": "China", "DEU": "Alemanha", "IND": "Índia"}
ANOS = range(2019, 2024)
LOG = logging.getLogger("etl")


def configurar_logs():
    pasta = RAIZ / "logs"
    pasta.mkdir(exist_ok=True)
    if not LOG.handlers:
        LOG.setLevel(logging.INFO)
        formato = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        for handler in (logging.StreamHandler(), logging.FileHandler(pasta / "etl.log", encoding="utf-8")):
            handler.setFormatter(formato)
            LOG.addHandler(handler)


def obter(url, *, params=None, cache=None, validar=None, tentativas=3):
    """Downloads incompletos ou inválidos nunca substituem o cache."""
    configurar_logs()
    cache = Path(cache) if cache else None
    if cache and cache.exists() and os.getenv("ETL_ATUALIZAR") != "1":
        conteudo = cache.read_bytes()
        try:
            if validar:
                validar(conteudo)
            LOG.info("Reutilizando cache: %s", cache.name)
            return conteudo
        except (ValueError, KeyError, TypeError):
            LOG.warning("Cache inválido; buscando novamente: %s", cache.name)
    for tentativa in range(1, tentativas + 1):
        try:
            with requests.get(url, params=params, timeout=(15, 90)) as resposta:
                resposta.raise_for_status()
                conteudo = resposta.content
            if validar:
                validar(conteudo)
            if cache:
                cache.parent.mkdir(parents=True, exist_ok=True)
                temporario = cache.with_suffix(cache.suffix + ".tmp")
                temporario.write_bytes(conteudo)
                temporario.replace(cache)
                metadados = {"url": url, "parametros": params, "coletado_em_utc": datetime.now(timezone.utc).isoformat(),
                             "sha256": hashlib.sha256(conteudo).hexdigest()}
                cache.with_suffix(cache.suffix + ".meta.json").write_text(json.dumps(metadados, indent=2), encoding="utf-8")
            return conteudo
        except (requests.RequestException, ValueError, KeyError, TypeError) as erro:
            LOG.warning("Falha HTTP/validação (%s), tentativa %s/%s: %s", type(erro).__name__, tentativa, tentativas, url)
            if isinstance(erro, requests.HTTPError) and erro.response is not None and 400 <= erro.response.status_code < 500 and erro.response.status_code != 429:
                break
            if tentativa < tentativas:
                time.sleep(2 ** tentativa)
    raise RuntimeError(f"Não foi possível extrair {url}. Consulte logs/etl.log; o cache concluído foi preservado.")


def salvar_csv(tabela, destino):
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(".csv.tmp")
    tabela.to_csv(temporario, index=False, encoding="utf-8-sig")
    temporario.replace(destino)
    LOG.info("CSV %s: %s registros", destino.name, len(tabela))


def conectar_mongo():
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
    cliente = MongoClient(os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017"), serverSelectionTimeoutMS=5000)
    try:
        cliente.admin.command("ping")
    except PyMongoError:
        cliente.close()
        raise RuntimeError("MongoDB indisponível. Inicie o MongoDB local ou configure MONGODB_URI. Para executar apenas CSVs, use --sem-mongo.") from None
    return cliente


def carregar_mongo(tabela, colecao, chaves):
    """Publica um snapshot completo usando staging, chave única e rename atômico."""
    configurar_logs()
    if os.getenv("ETL_SEM_MONGO") == "1":
        LOG.info("MongoDB desativado explicitamente: %s", colecao)
        return
    from pymongo import ReplaceOne
    from pymongo.errors import PyMongoError
    import uuid
    if tabela[chaves].isna().any().any() or tabela.duplicated(chaves).any():
        raise ValueError(f"Chaves nulas ou duplicadas em {colecao}")
    registros = json.loads(tabela.to_json(orient="records", date_format="iso"))
    with conectar_mongo() as cliente:
        banco = cliente[os.getenv("MONGODB_DATABASE", "covid_socioeconomia")]
        nome_temporario = f"_staging_{colecao}_{uuid.uuid4().hex}"
        temporaria = banco[nome_temporario]
        try:
            temporaria.create_index([(chave, 1) for chave in chaves], unique=True)
            for inicio in range(0, len(registros), 1000):
                lote = registros[inicio:inicio + 1000]
                temporaria.bulk_write([ReplaceOne({chave: r[chave] for chave in chaves}, r, upsert=True) for r in lote], ordered=False)
            temporaria.rename(colecao, dropTarget=True)
        except PyMongoError:
            banco.drop_collection(nome_temporario)
            raise RuntimeError(f"Falha na carga MongoDB da coleção {colecao}; verifique permissões e conectividade.") from None
    LOG.info("MongoDB %s: %s registros", colecao, len(registros))
