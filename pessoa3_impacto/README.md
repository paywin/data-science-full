Warning: fs was declared with const; use let for reassignable variables.
# Impacto da COVID-19 em 5 economias (2019–2023)

Dashboard interativo comparando **Brasil, Estados Unidos, China, Alemanha e Índia** antes (2019), durante (2020–2021) e depois (2022–2023) da fase mais crítica da pandemia.

**Indicadores:** crescimento do PIB, desemprego, inflação e expectativa de vida.

## Ver o dashboard
Abra o `index.html` no navegador (precisa de internet para carregar o Chart.js e a fonte), ou use o link do GitHub Pages do repositório.

## Estrutura
- `index.html`: dashboard (HTML + JavaScript, arquivo único)
- `etl/etl_template.py`: ETL padrão do grupo (API do Banco Mundial → Pandas → CSV → MongoDB)
- `data/processed/`: CSVs gerados pelo ETL (lidos pelo Power BI)

## Rodar o ETL
```bash
pip install -r etl/requirements.txt
python etl/etl_template.py
```
Defina `MONGO_URI` se não usar o MongoDB local (`mongodb://localhost:27017`).

## Aviso sobre os dados
Os valores do dashboard são aproximados (Banco Mundial e FMI) e servem de protótipo. Substitua pelos CSVs gerados no ETL antes de apresentar.
