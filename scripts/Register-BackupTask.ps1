<#
.SYNOPSIS
    Registra (ou re-registra) o job semanal no Windows Task Scheduler que
    dispara `backup_postgres.ps1`.

.DESCRIPTION
    ISSUE-023 — backups automaticos.

    Idempotente: se a task ja existir, e desregistrada e recriada com a
    nova configuracao. Roda como o usuario atual.

    Default: dispara todo domingo as 03:00 hora local da maquina.
    Justificativa: domingo de madrugada e a janela de menor uso da
    plataforma. Local — assume maquina em America/Sao_Paulo.

.PARAMETER TaskName
    Nome registrado no Task Scheduler. Default: "MDP Postgres Backup".

.PARAMETER At
    Hora do disparo, formato "HH:mm". Default: "03:00".

.PARAMETER DayOfWeek
    Dia da semana. Default: Sunday.

.PARAMETER RetentionDays
    Idade max em dias passada ao wrapper. Default: 90.

.EXAMPLE
    .\Register-BackupTask.ps1
    .\Register-BackupTask.ps1 -At "04:00" -RetentionDays 180

.NOTES
    Para desregistrar: Unregister-ScheduledTask -TaskName "MDP Postgres Backup" -Confirm:$false
    Para inspecionar:  Get-ScheduledTask -TaskName "MDP Postgres Backup"
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MDP Postgres Backup",
    [string]$At = "03:00",
    [ValidateSet("Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday")]
    [string]$DayOfWeek = "Sunday",
    [int]$RetentionDays = 90
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WrapperPath = Join-Path $ScriptDir "backup_postgres.ps1"

if (-not (Test-Path $WrapperPath)) {
    throw "Wrapper nao encontrado em $WrapperPath. Execute este script a partir de scripts/."
}

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$WrapperPath`" -RetentionDays $RetentionDays"

# Trigger semanal — domingo (default) 03:00.
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DayOfWeek -At $At

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

# StartWhenAvailable: se a maquina estiver dormindo, dispara assim que
# voltar. ExecutionTimeLimit: 1h e folga sobrada para um pg_dump de
# market_db (2-3 GB tipicos -> minutos). Mata runs enroscados.

# Idempotencia: se ja existe, desregistra antes de recriar.
$Existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($Existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "MDP — backup semanal do PostgreSQL via pg_dump (ISSUE-023)" | Out-Null

Write-Host "Task '$TaskName' registrada. Dispara $DayOfWeek as $At." -ForegroundColor Green
Write-Host "Retencao: $RetentionDays dias. Wrapper: $WrapperPath" -ForegroundColor Green
Write-Host "Inspecionar:  Get-ScheduledTask -TaskName '$TaskName' | Format-List *"
Write-Host "Desregistrar: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
