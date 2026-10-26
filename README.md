# COVID-19 e economia — trabalho de Data Science

Análise de Brasil, Estados Unidos, China, Alemanha e Índia, entre 2019 e 2023.

## Para que serve cada arquivo?

| Arquivo | Responsável / função |
|---|---|
| `etl_covid.py` | Marina: baixa COVID, calcula crescimento e média móvel de 7 dias. |
| `etl_economia.py` | Emily: busca PIB, crescimento real, desemprego e população no Banco Mundial. |
| `etl_impacto.py` | Luiz: junta os dados por país/ano e calcula correlações. |
| `etl_tendencias.py` | Mateus: calcula as variações anuais. |
| `executar_projeto.py` | Executa os quatro ETLs na ordem correta. |
| `banco.py` | Salva os CSVs e faz a conexão/gravação no MongoDB. |
| `requirements.txt` | Lista as bibliotecas que precisam ser instaladas. |
| `testes.py` | Confere os principais cálculos e o tratamento de falhas. |

O README é este guia. O `.gitignore` apenas impede que arquivos gerados sejam enviados ao GitHub.

## Como rodar

Use Python 3.10 ou superior. Na pasta do projeto:

```bash
python -m pip install -r requirements.txt
python executar_projeto.py
```

Isso gera os CSVs. Na primeira execução, é necessária internet. A fonte de COVID é grande, então o primeiro download pode demorar. Há três tentativas se a conexão falhar.

**Para completar a entrega com MongoDB**, instale e inicie o servidor MongoDB Community e execute:

```bash
python executar_projeto.py --mongo
```

A conexão padrão é `mongodb://localhost:27017`, banco `covid_socioeconomia`. Para outra conexão, defina a variável de ambiente `MONGODB_URI`. Não coloque senhas no código. O programa não instala nem inicia o servidor do banco.

As coleções usadas pelo programa guardam apenas os dados gerados pelo trabalho. Cada execução refaz essas coleções para não duplicar registros. Se a carga for interrompida, execute novamente. Não guarde registros manuais nessas coleções.

Opcional: para não misturar bibliotecas de outros projetos, crie uma `.venv` com `python -m venv .venv` e ative-a antes de instalar as dependências. No Git Bash do Windows: `source .venv/Scripts/activate`. Se estiver em outra venv, execute `deactivate` primeiro.

## O que será gerado?

Tudo fica dentro de `dados/`:

- `covid.csv`: medidas diárias e média móvel.
- `economia_paises_2019_2023.csv`: 25 linhas, uma por país/ano.
- `base_integrada_pais_ano.csv`: COVID e economia juntas.
- `correlacoes.csv`: correlações Pearson e Spearman.
- `tendencias_anual_pais.csv`: indicadores e suas variações anuais na mesma tabela.

A subpasta `brutos/` guarda apenas dois arquivos de entrada (`covid.csv` e `economia.json`). Eles são reutilizados nas próximas execuções. Para atualizar os dados, remova esses dois arquivos e execute novamente; isso exige internet. As consultas econômicas concluídas são guardadas mesmo que uma consulta posterior falhe.

Com `--mongo`, as cinco tabelas e os dois conjuntos de dados brutos também são carregados no banco. São gerados dois CSVs adicionais de dados brutos nesse modo. Os ETLs podem ser executados individualmente com `python etl_covid.py`, por exemplo; nesse caso salvam apenas CSV.

## Como interpretar

- Valores desconhecidos ficam vazios, não são substituídos por zero.
- A média móvel exige sete dias completos. Crescimento diário exige o dia anterior.
- Não há série diária de COVID em 2019. Na base anual, zero em 2019 é uma referência pré-pandemia e esse ano não entra nas correlações.
- `cobertura_covid` mostra a fração do ano com dados. A soma anual pode estar incompleta; correlações usam apenas cobertura de pelo menos 90% e três pares válidos. Esse limiar foi escolhido para o trabalho.
- PIB em dólares correntes é diferente de crescimento real do PIB. Mudanças no desemprego são expressas em pontos percentuais.
- Correlação indica associação, não prova que a pandemia causou uma mudança econômica.

Para testar: `python -m unittest testes -v`. Os testes não precisam de internet nem de MongoDB.

Fontes: [Our World in Data](https://catalog.ourworldindata.org/garden/covid/latest/compact/compact.csv) e [Banco Mundial](https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures). A fonte OWID substitui a API de COVID citada no enunciado. Power BI fica fora desta etapa; pode ler os CSVs depois.
