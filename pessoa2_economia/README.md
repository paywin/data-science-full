Warning: fs was declared with const; use let for reassignable variables.
# Pessoa 2 — ETL de indicadores socioeconômicos

## O que faz
- Consulta a API pública do Banco Mundial.
- Busca PIB e desemprego para Brasil, Estados Unidos, China, Alemanha e Índia.
- Considera os anos de 2019 a 2023.
- Organiza os dados em uma linha por país/ano.
- Mantém valores que não foram disponibilizados como ausentes (NaN), sem inventar números.
- Gera dois CSVs: dados econômicos e resumo de valores ausentes.

## Como executar
No terminal, dentro desta pasta:

```bash
pip install pandas requests
python etl_economia.py
```

É necessário ter conexão com a internet para consultar a API do Banco Mundial.

## Arquivos gerados ao executar
- `economia_paises_2019_2023.csv`: tabela principal para a Pessoa 3 e o Power BI.
- `resumo_valores_ausentes.csv`: quantidade de valores ausentes por país e indicador.

O script salva os CSVs na pasta em que for executado.
