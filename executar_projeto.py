"""Executa COVID, economia, impacto e tendências com logs e status verificável."""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys

from infra import RAIZ, LOG, configurar_logs, conectar_mongo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--usar-arquivos-existentes", action="store_true")
    parser.add_argument("--covid-local", type=Path)
    parser.add_argument("--sem-mongo", action="store_true", help="Modo explícito somente CSV; não conclui o requisito de banco")
    parser.add_argument("--atualizar", action="store_true", help="Consulta as fontes novamente, sem reutilizar cache")
    args = parser.parse_args()
    if args.usar_arquivos_existentes and (args.covid_local or args.atualizar):
        parser.error("--usar-arquivos-existentes não combina com --covid-local ou --atualizar")
    os.environ["ETL_SEM_MONGO"] = "1" if args.sem_mongo else "0"
    os.environ["ETL_ATUALIZAR"] = "1" if args.atualizar else "0"
    configurar_logs()
    pasta = RAIZ / "dados"
    pasta.mkdir(exist_ok=True)
    status = {"inicio_utc": datetime.now(timezone.utc).isoformat(), "status": "executando", "etapas_concluidas": [], "mongodb": not args.sem_mongo}
    caminho_status = pasta / "status_execucao.json"
    def gravar_status():
        temporario = caminho_status.with_suffix(".tmp")
        temporario.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
        temporario.replace(caminho_status)
    gravar_status()
    try:
        if not args.sem_mongo:
            with conectar_mongo():
                pass
        from pessoa1_covid.etl_covid import executar_etl as covid
        from pessoa2_economia.etl_economia import executar_etl as economia
        from pessoa3_impacto.etl_impacto import executar_etl as impacto
        from pessoa4_tendencias.etl_tendencias import executar_etl as tendencias
        if args.usar_arquivos_existentes:
            for nome in ("covid.csv", "economia_paises_2019_2023.csv"):
                if not (pasta / nome).is_file():
                    raise FileNotFoundError(f"Arquivo necessário não encontrado: {nome}")
            # Revalida e recarrega as entradas; não afirma ter extraído novos dados.
            covid(pasta / "covid.csv")
            import pandas as pd
            from infra import carregar_mongo
            economica = pd.read_csv(pasta / "economia_paises_2019_2023.csv")
            from pessoa2_economia.etl_economia import INDICADORES, montar_economia
            tabelas = {c: economica[["pais_codigo", "ano", c]] for c in INDICADORES.values()}
            economica = montar_economia(tabelas)
            carregar_mongo(economica, "economia", ["pais_codigo", "ano"])
            status["etapas_concluidas"].extend(["covid_local", "economia_local"])
        else:
            covid(args.covid_local)
            status["etapas_concluidas"].append("covid")
            gravar_status()
            economia()
            status["etapas_concluidas"].append("economia")
        gravar_status()
        impacto()
        status["etapas_concluidas"].append("impacto")
        gravar_status()
        tendencias()
        status["etapas_concluidas"].append("tendencias")
        status["status"] = "concluido_csv" if args.sem_mongo else "concluido"
        LOG.info("Projeto finalizado: %s. Saídas em %s", status["status"], pasta)
        return 0
    except Exception as erro:
        status["status"] = "falhou"
        # Não expor credenciais de conexão em traceback de drivers.
        from pymongo.errors import PyMongoError
        mensagem = "Falha de acesso ao MongoDB" if isinstance(erro, PyMongoError) else str(erro)
        status["erro"] = mensagem
        LOG.error("Execução interrompida: %s", mensagem)
        return 1
    finally:
        status["fim_utc"] = datetime.now(timezone.utc).isoformat()
        gravar_status()


if __name__ == "__main__":
    sys.exit(main())
