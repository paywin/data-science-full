"""Compatibilidade com o comando antigo: encaminha para o ETL de impacto."""

from etl_impacto import executar_etl

if __name__ == "__main__":
    executar_etl()
