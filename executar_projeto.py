"""Executa as quatro partes do trabalho na ordem correta."""
import argparse
import sys

import etl_covid
import etl_economia
import etl_impacto
import etl_tendencias
from banco import conectar


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mongo", action="store_true", help="Salvar também no MongoDB; exige o servidor iniciado")
    args = parser.parse_args()
    cliente = None
    try:
        cliente = conectar() if args.mongo else None
        banco = cliente["covid_socioeconomia"] if cliente is not None else None
        for etapa in [etl_covid, etl_economia, etl_impacto, etl_tendencias]:
            print(f"\nExecutando {etapa.__name__}...")
            etapa.executar(banco)
        print("\nConcluído! CSVs na pasta dados/." + (" Dados também salvos no MongoDB." if args.mongo else " Para incluir o banco, use --mongo."))
        return 0
    except Exception as erro:
        from pymongo.errors import PyMongoError
        mensagem = "Falha ao gravar no MongoDB; verifique o servidor e execute novamente." if isinstance(erro, PyMongoError) else str(erro)
        print(f"\nExecução interrompida: {mensagem}")
        return 1
    finally:
        if cliente is not None:
            cliente.close()


if __name__ == "__main__":
    sys.exit(main())
