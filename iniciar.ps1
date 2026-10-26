param([switch]$SemMongo, [switch]$Atualizar)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonProjeto = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonProjeto)) {
    if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv .venv }
    else { & python -m venv .venv }
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar .venv. Instale Python 3.10 ou superior.' }
}
& $pythonProjeto -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependências.' }
if (-not $SemMongo -and -not $env:MONGODB_URI) {
    & $pythonProjeto iniciar_mongo.py
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao iniciar MongoDB.' }
}
$argumentos = @('executar_projeto.py')
if ($SemMongo) { $argumentos += '--sem-mongo' }
if ($Atualizar) { $argumentos += '--atualizar' }
& $pythonProjeto @argumentos
exit $LASTEXITCODE
