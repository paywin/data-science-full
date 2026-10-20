# COVID-19 e indicadores socioeconômicos — ETL integrado

Projeto do grupo para comparar a evolução dos casos de COVID-19 e de indicadores econômicos em **Brasil, Estados Unidos, China, Alemanha e Índia**, entre **2019 e 2023**. Todos os identificadores internos, nomes de funções e colunas geradas seguem português com `snake_case` (sem acentos nos nomes das colunas). O formato original em inglês das APIs é convertido na extração.

## Estrutura e responsabilidades

| Integrante | Script | Responsabilidade |
| --- | --- | --- |
| Marina — Pessoa 1 | `pessoa1_covid/etl_covid.py` | Extrai COVID diário, calcula média móvel de sete registros diários e crescimento dos casos acumulados. |
| Emily — Pessoa 2 | `pessoa2_economia/etl_economia.py` | Extrai PIB em US$ correntes, crescimento real do PIB, desemprego e população (Banco Mundial). |
| Luiz — Pessoa 3 | `pessoa3_impacto/etl_impacto.py` | Agrega COVID por país/ano, integra economia, calcula associações e compara 2020/2019. |
| Mateus — Pessoa 4 | `pessoa4_tendencias/etl_tendencias.py` | Gera séries anuais, variações anuais e comparação de 2020 com 2019. |
| Pessoa 5 | Power BI | Conecta os arquivos da pasta `dados/` ao dashboard. Não inclui arquivo `.pbix` neste repositório. |

O antigo `pessoa3_impacto/analise_integrada.py` foi mantido como atalho compatível, encaminhando para `etl_impacto.py`.

## Como executar

Na pasta raiz do repositório, com Python 3.10 ou superior:

```bash
python -m pip install -r requirements.txt
python executar_projeto.py
```

O comando executa os ETLs 1 → 2 → 3 → 4. **É necessária internet** para consultar Our World in Data e a API do Banco Mundial. Todos os arquivos finais são salvos em `dados/`, independentemente da pasta do terminal de execução.

Para processar novamente os dados locais sem consultar as APIs, coloque `dados/covid.csv` e `dados/economia_paises_2019_2023.csv` na pasta `dados/` e execute:

```bash
python executar_projeto.py --usar-arquivos-existentes
```

Para reutilizar o arquivo legado da Marina (já versionado no projeto) com nova extração econômica:

```bash
python executar_projeto.py --covid-local pessoa1_covid/dados/covid.csv
```

Os scripts também podem ser executados individualmente. Por exemplo:

```bash
python pessoa1_covid/etl_covid.py --entrada pessoa1_covid/dados/covid.csv
python pessoa2_economia/etl_economia.py
python pessoa3_impacto/etl_impacto.py
python pessoa4_tendencias/etl_tendencias.py
```

## Contrato de dados (nomes padronizados)

- **Dados diários:** `pais_codigo`, `pais`, `data`, `casos_novos`, `casos_acumulados`, `media_movel_7d`, `crescimento_casos_pct`.
- **Dados econômicos por ano:** `pais_codigo`, `pais`, `ano`, `pib_usd_correntes`, `crescimento_pib_real_pct`, `desemprego_pct`, `populacao`.
- **Base integrada:** chaves `pais_codigo` + `ano`; reúne os indicadores econômicos com `casos_novos_ano`, `pico_media_movel_7d`, `casos_acumulados_fim_ano`, `cobertura_covid`, `covid_observado`, `casos_por_milhao`, `pico_media_movel_por_milhao`, `variacao_pib_usd_correntes_pct` e `fase`.

Os dois ETLs seguintes reconhecem **também o CSV legado** de COVID (`code`, `date`, `new_cases`, `total_cases`) e de economia (`pib_usd`, `desemprego_percentual`, `pib_crescimento_real_pct`), facilitando a migração sem alterar os arquivos antigos. **A variação do PIB em dólares correntes não equivale ao crescimento real do PIB.**

## CSVs para Power BI

| Arquivo em `dados/` | Conteúdo |
| --- | --- |
| `covid.csv` | Série diária padronizada da COVID-19. |
| `economia_paises_2019_2023.csv` | Indicadores econômicos por país e ano. |
| `resumo_valores_ausentes.csv` | Total de ausências por país/indicador. |
| `base_integrada_pais_ano.csv` | Tabela principal para relacionar COVID e economia. |
| `correlacoes.csv` | Pearson e Spearman descritivos, com número de observações. |
| `variacao_2020_vs_2019.csv` | Comparação entre anos para indicadores econômicos e COVID em 2020. |
| `tendencias_anual_pais.csv` | Indicadores integrados para gráficos temporais. |
| `variacoes_anuais_pais.csv` | Diferenças interanuais e contra 2019. |
| `choque_2020_vs_2019.csv` | Recorte das variações de 2020. |

**Observações metodológicas:** 2019 é pré-pandemia: os casos novos na base anual são definidos como zero de referência, mas `covid_observado=0` e `cobertura_covid` fica vazia (não representa medição diária). Nos demais anos, `cobertura_covid` é a proporção de dias do calendário com `casos_novos` preenchido. Correções retrospectivas da fonte podem gerar casos negativos, que **não são convertidos silenciosamente em zero**. Valores econômicos ausentes permanecem vazios. Variações de taxas de desemprego e crescimento real do PIB são expressas em **pontos percentuais** (`_pp`), e não em crescimento relativo. Variações percentuais com base zero ou ausente ficam vazias. Correlacionar indicadores não prova causalidade, especialmente com apenas cinco países e anos próximos.

## Testes

```bash
python -m unittest discover -s tests -v
```

Os testes não fazem requisições externas. Validam migração de colunas antigas, tratamento de ausências, detecção de duplicatas e integração das quatro etapas. O CSV econômico gerado localmente a partir de números simulados **não deve ser usado no dashboard**; a análise final requer dados reais extraídos da API.

## Fontes

- [Our World in Data — dados COVID-19](https://catalog.ourworldindata.org/garden/covid/latest/compact/compact.csv)
- [Banco Mundial — API de indicadores](https://api.worldbank.org/v2/)
