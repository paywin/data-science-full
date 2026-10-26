param([string]$Horario = '09:00')
$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'iniciar.ps1'
$acao = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -ExecutionPolicy Bypass -File "' + $script + '" -Atualizar') -WorkingDirectory $PSScriptRoot
$gatilho = New-ScheduledTaskTrigger -Daily -At $Horario
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName 'DataScience-Covid-ETL' -Action $acao -Trigger $gatilho -Principal $principal -Description 'Atualiza COVID e economia; exige sessão iniciada e internet.'
