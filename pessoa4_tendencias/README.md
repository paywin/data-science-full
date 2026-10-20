# Pessoa 4 — ETL de tendências temporais

O arquivo `etl_tendencias.py` prepara séries anuais para comparar COVID-19,
crescimento do PIB e desemprego nos cinco países do projeto, de 2019 a 2023.

## Como executar

Requisito: `pip install pandas`

Com a base integrada usada no dashboard (`covid_economia_2019_2023.csv`) na
mesma pasta do script:

```bash
python etl_tendencias.py
```

Ou informe explicitamente os arquivos:

```bash
python etl_tendencias.py --base-integrada caminho/para/covid_economia_2019_2023.csv
```

Também pode combinar a saída diária da Pessoa 1 com a saída anual da Pessoa 2:

```bash
python etl_tendencias.py --covid caminho/para/covid.csv --economia caminho/para/economia_paises_2019_2023.csv
```

Por padrão, os CSVs são salvos ao lado do script. Use `--saida pasta` para
escolher outra pasta.

## Arquivos gerados

- `tendencias_anual_pais.csv`: uma linha por país/ano, com métricas anuais e a
  fase (pré-pandemia, fase crítica ou pós-pico).
- `variacoes_anuais_pais.csv`: diferença absoluta, variação percentual contra o
  ano anterior e diferença contra 2019.
- `choque_2020_vs_2019.csv`: recorte de 2020 para comparar com o ano-base 2019.

Para crescimento do PIB e desemprego, a coluna terminada em `_pp` indica a
diferença em pontos percentuais. A variação percentual relativa também é
calculada, mas deve ser interpretada com cuidado para taxas.

## Cuidados com os dados

- Valores ausentes continuam vazios; não são substituídos por zero.
- 2019 é tratado como referência pré-pandemia: casos novos e pico COVID iguais a
  zero significam “antes da pandemia”, não observações diárias de zero casos.
- A taxa de variação percentual fica ausente quando o valor anterior é zero ou
  ausente, para evitar divisão inválida ou uma taxa sem sentido.
- Os resultados mostram evolução temporal e associação descritiva. Sozinhos,
  não demonstram que a pandemia causou mudanças no PIB ou no desemprego.
