# COVID-19 e indicadores socioeconômicos — ETL integrado

Pipeline para Brasil, Estados Unidos, China, Alemanha e Índia, de 2019 a 2023. As quatro etapas extraem, transformam com Pandas, salvam CSV e carregam MongoDB. Power BI não é necessário para executar este projeto.

## Executar no Windows

Requisito: Python 3.10 ou superior instalado e internet na primeira execução.

Na pasta do projeto, execute no Git Bash ou Prompt de Comando:

```bash
./iniciar.cmd
```

No PowerShell:

```powershell
.\iniciar.cmd
```

Esse comando cria uma `.venv` exclusiva do projeto, instala as dependências, inicia MongoDB Community portátil e executa os quatro ETLs. Não utiliza a `.venv` de outro projeto. O MongoDB é baixado do servidor oficial, validado por SHA256 e executado sem janela, sem serviço do Windows e somente em `127.0.0.1:27017`. O primeiro download do MongoDB e da COVID pode demorar. Arquivos do banco ficam em `.mongo/`; não apague essa pasta se quiser preservá-los.

Se já houver MongoDB respondendo nessa porta, ele será utilizado. O banco do projeto é `covid_socioeconomia`. As coleções listadas abaixo são gerenciadas pelo ETL e substituídas pelo snapshot da execução; não acrescente registros manuais nelas.

Para iniciar sem carregar MongoDB, explicitamente:

```powershell
.\iniciar.cmd -SemMongo
```

Esse modo gera CSVs, mas não conclui o requisito acadêmico de armazenamento no banco.

## Execução manual / Git Bash

```bash
# Se existir outro ambiente ativo, saia dele primeiro.
deactivate
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements.txt
python iniciar_mongo.py
python executar_projeto.py
```

O comando `deactivate` só se aplica quando há uma venv ativa. No PowerShell, a ativação é `.\.venv\Scripts\Activate.ps1`; também é possível chamar `.\.venv\Scripts\python.exe` diretamente.

Linux/macOS: crie a venv normalmente e use MongoDB instalado ou `docker compose up -d mongodb`. O inicializador portátil é específico de Windows x86_64. O Compose é uma alternativa ao MongoDB portátil; não execute os dois na mesma porta.

## Configuração do MongoDB

Variáveis opcionais:

- `MONGODB_URI`: padrão `mongodb://127.0.0.1:27017`.
- `MONGODB_DATABASE`: padrão `covid_socioeconomia`; use um banco dedicado ao projeto.

Exemplo PowerShell:

```powershell
$env:MONGODB_URI = 'mongodb://127.0.0.1:27017'
$env:MONGODB_DATABASE = 'covid_socioeconomia'
.\.venv\Scripts\python.exe executar_projeto.py
```

Credenciais de Atlas devem ser fornecidas pelo ambiente, nunca pelo código ou Git. O usuário do banco precisa criar índices/coleções, inserir e renomear coleções no banco dedicado. A carga usa uma coleção temporária e publicação por rename; se falhar antes da publicação, o snapshot anterior daquela coleção fica preservado. Cada coleção tem índice único por chave natural. A reexecução atualiza o snapshot sem duplicatas e remove registros que deixaram de existir na fonte.

A publicação é atômica por coleção, não uma transação envolvendo todo o pipeline. Só consuma os resultados de uma execução cujo `dados/status_execucao.json` indique `concluido` (ou `concluido_csv` no modo somente CSV). Não rode duas execuções simultaneamente na mesma pasta/banco.

## Etapas e responsáveis

| Etapa | Responsável | Script | Resultado |
|---|---|---|---|
| 1 | Marina | `pessoa1_covid/etl_covid.py` | COVID diária, média móvel e crescimento |
| 2 | Emily | `pessoa2_economia/etl_economia.py` | PIB nominal, crescimento real do PIB, desemprego e população |
| 3 | Luiz | `pessoa3_impacto/etl_impacto.py` | Integração por país/ano e correlações |
| 4 | Mateus | `pessoa4_tendencias/etl_tendencias.py` | Tendências, variações e comparação com 2019 |

Os scripts individuais também carregam MongoDB. Para rodar um deles só com CSVs, defina `ETL_SEM_MONGO=1` no ambiente. O atalho `pessoa3_impacto/analise_integrada.py` foi preservado.

## Fontes, cache e reexecução

- COVID: [Our World in Data, compact](https://catalog.ourworldindata.org/garden/covid/latest/compact/compact.csv), alternativa à API mencionada no enunciado. Essa escolha está explícita e deve ser registrada na apresentação.
- Economia: [API do Banco Mundial](https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures), indicadores `NY.GDP.MKTP.CD`, `NY.GDP.MKTP.KD.ZG`, `SL.UEM.TOTL.ZS`, `SP.POP.TOTL`.
- MongoDB portátil: [distribuição oficial](https://www.mongodb.com/try/download/community), versão 8.0.34 fixada no inicializador com checksum.

São quatro consultas econômicas no caso usual, uma por indicador contendo todos os países. Há suporte a paginação. Cada download tem limite de conexão/leitura e até três tentativas com espera progressiva. Respostas inválidas são rejeitadas; falhas HTTP permanentes não são repetidas.

O cache em `dados/brutos/` é reutilizado por padrão para facilitar a apresentação e evitar novas falhas de rede. Cada fonte baixada recebe um `.meta.json` com URL, parâmetros, horário UTC e SHA256. Ele não expira automaticamente: para obter revisões recentes das fontes, execute:

```bash
python executar_projeto.py --atualizar
```

Se uma atualização falhar, a execução falha claramente; não troca silenciosamente dados novos por cache antigo. Downloads incompletos não substituem o cache anterior.

Outras opções:

```bash
python executar_projeto.py --covid-local pessoa1_covid/dados/covid.csv
python executar_projeto.py --usar-arquivos-existentes
python executar_projeto.py --sem-mongo
```

`--usar-arquivos-existentes` exige `dados/covid.csv` e `dados/economia_paises_2019_2023.csv`; reprocessa as entradas locais sem novas consultas e recarrega os resultados. Não recupera o payload original do Banco Mundial se o cache bruto tiver sido removido. `--covid-local` usa o CSV fornecido para COVID e o cache/API para economia.

## CSVs e coleções

Arquivos UTF-8 com BOM, separados por vírgula e números com ponto decimal; datas em formato ISO. Chaves: `pais_codigo` ISO3 e `ano` (ou `data` para séries diárias). Os nomes dos arquivos e das colunas anteriores foram preservados; foram acrescentados campos de qualidade.

| CSV em `dados/` | Coleção MongoDB | Chave |
|---|---|---|
| `covid.csv` | `covid` | país + data |
| `economia_paises_2019_2023.csv` | `economia` | país + ano |
| `resumo_valores_ausentes.csv` | `resumo_valores_ausentes` | país |
| `base_integrada_pais_ano.csv` | `base_integrada_pais_ano` | país + ano |
| `correlacoes.csv` | `correlacoes` | escopo + ano + par de indicadores |
| `variacao_2020_vs_2019.csv` | `variacao_2020_vs_2019` | país |
| `tendencias_anual_pais.csv` | `tendencias_anual_pais` | país + ano |
| `variacoes_anuais_pais.csv` | `variacoes_anuais_pais` | país + ano |
| `choque_2020_vs_2019.csv` | `choque_2020_vs_2019` | país + ano |

Também são carregadas `covid_brutos` (medidas originais recortadas por país/data) e `economia_brutos` (payload original por país/ano/indicador). A fonte COVID completa e as respostas JSON econômicas ficam no cache local. Valores ausentes viram campos vazios no CSV e `null` no MongoDB. Datas são armazenadas no banco como strings ISO; anos como inteiros.

## Decisões metodológicas e qualidade

- Todos os CSVs analíticos usam o recorte de 2019 a 2023. A COVID disponível começa em 2020; não são fabricados registros diários de 2019.
- 2019 é uma referência pré-pandemia na base anual, com casos novos/pico iguais a zero por convenção, `covid_observado=0` e cobertura vazia. Não entra nas correlações.
- Média móvel de sete **dias de calendário**, exigindo sete dias com valores preenchidos. Janelas incompletas ficam vazias. O crescimento diário exige observação no dia imediatamente anterior e denominador positivo.
- Ausências não são convertidas em zero; correções negativas da fonte são preservadas. Datas inválidas e duplicatas geram erro.
- Soma anual de casos pode representar um ano incompleto: consulte `cobertura_covid` e `cobertura_adequada`. Acumulado de fim de ano só é preenchido quando existe valor em 31/12; `ultima_data_covid` identifica a última data disponível.
- Correlações exigem cobertura anual de pelo menos 90%, três pares válidos e variabilidade. O limiar é uma escolha explícita deste projeto, não uma garantia estatística; a função aceita outro valor. CSV registra `cobertura_minima`, `excluidos_baixa_cobertura` e `observacoes`. Pares com valores ausentes são excluídos depois do filtro de cobertura.
- Pearson/Spearman são associações descritivas; não provam causalidade. Há poucos países, diferenças de notificação e dependência entre anos do mesmo país.
- PIB em dólares correntes não equivale a crescimento real. Variações de desemprego e crescimento real são em pontos percentuais. Variações anuais exigem anos consecutivos; base zero/ausente gera percentual vazio.

## Testes, logs e agendamento

```bash
python -m unittest discover -s tests -v
```

Os testes de transformação e HTTP usam dados simulados/mocks. Para incluir o teste de MongoDB real, defina `MONGO_TEST_URI` apontando para seu MongoDB. Esse teste cria e remove apenas um banco temporário com prefixo `teste_etl_`.

`VALIDACAO.json` registra a validação realizada na versão entregue. `logs/etl.log` contém tentativas, cargas e falhas; `dados/status_execucao.json` informa o resultado mais recente. O processo retorna código diferente de zero em caso de falha.

Agendamento opcional no Windows, depois de testar manualmente:

```powershell
.\agendar.ps1 -Horario '09:00'
```

Cria uma tarefa diária para atualizar fontes enquanto o usuário estiver conectado. Nenhum agendamento é criado automaticamente. Para removê-la, use o Agendador de Tarefas do Windows.

## Power BI

Pode ler os CSVs diretamente em `dados/`. Esta correção não altera o relatório online nem suas credenciais. A atualização do relatório deve usar resultados de uma execução concluída e interpretar os campos de cobertura e ausências.
