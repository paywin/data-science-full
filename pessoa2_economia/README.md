# Pessoa 2 — ETL econômico (Emily)

Execute `python pessoa2_economia/etl_economia.py` na raiz do repositório após instalar `requirements.txt`. O script consulta a API do Banco Mundial para PIB em dólares correntes, crescimento real do PIB, desemprego e população de cinco países em 2019–2023. Salva em `dados/economia_paises_2019_2023.csv` e `dados/resumo_valores_ausentes.csv`. Os nomes das colunas são em português, e valores desconhecidos são mantidos vazios. Não há preenchimento de lacunas com zero.
