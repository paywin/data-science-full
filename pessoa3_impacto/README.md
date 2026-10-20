# Pessoa 3 — Impacto socioeconômico (Luiz)

Execute `python pessoa3_impacto/etl_impacto.py` depois dos ETLs 1 e 2. O código une a COVID diária agregada por ano aos indicadores econômicos usando as chaves `pais_codigo` e `ano`, com 25 combinações para 2019–2023. Gera `dados/base_integrada_pais_ano.csv`, `dados/correlacoes.csv` (Pearson, Spearman e quantidade de observações, por ano e no período) e `dados/variacao_2020_vs_2019.csv`. **Correlações são descritivas e não indicam causalidade.** O script antigo `analise_integrada.py` permanece como atalho.
