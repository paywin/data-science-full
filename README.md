# Projeto de análise socioeconômica da COVID-19

Repositório reunido a partir dos arquivos fornecidos para as Pessoas 1, 2 e 3, mais o ETL de tendências desenvolvido para a Pessoa 4.

## Estrutura

- `pessoa1_covid/`: ETL diário e dados de COVID-19.
- `pessoa2_economia/`: ETL de PIB e desemprego via Banco Mundial.
- `pessoa3_impacto/`: integração/análise de impacto e README original.
- `pessoa4_tendencias/`: tendências anuais, variações interanuais e comparação 2020 vs 2019.

Os CSVs econômicos são produzidos ao executar o ETL da Pessoa 2; eles não estavam incluídos no ZIP recebido. O ETL da Pessoa 4 lê uma base integrada ou os CSVs gerados pelas Pessoas 1 e 2. Consulte o README de cada pasta para instruções.

Os diretórios `.git` e `.venv` presentes dentro do ZIP da Pessoa 1 foram omitidos; eles são estado interno do Git e ambiente Python local, não arquivos do projeto.