"""Funções usadas pelos quatro ETLs para salvar seus resultados."""
import json
import os
from pathlib import Path

from pymongo import MongoClient

DADOS = Path(__file__).resolve().parent / "dados"


def salvar(tabela, nome, banco=None):
    """Salva CSV e, quando solicitado, a mesma tabela no MongoDB."""
    DADOS.mkdir(exist_ok=True)
    tabela.to_csv(DADOS / f"{nome}.csv", index=False, encoding="utf-8-sig")
    if banco is not None:
        # Converte NaN em null e datas em texto ISO antes de inserir.
        registros = json.loads(tabela.to_json(orient="records", date_format="iso"))
        # Estas coleções são exclusivas do trabalho: cada execução refaz a tabela.
        banco[nome].delete_many({})
        if registros:
            banco[nome].insert_many(registros)
    print(f"{nome}: {len(tabela)} registros salvos.")


def conectar():
    cliente = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017"), serverSelectionTimeoutMS=5000)
    try:
        cliente.admin.command("ping")
    except Exception:
        cliente.close()
        raise RuntimeError("MongoDB indisponível. Inicie o servidor ou execute sem --mongo para gerar apenas CSVs.") from None
    return cliente
