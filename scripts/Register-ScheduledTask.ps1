<#
.SYNOPSIS
    Registra (ou re-registra) o job no Windows Task Scheduler que dispara
    `scheduled_update.ps1` diariamente.

.DESCRIPTION
    ISSUE-015 — primeira opção de agendamento (ver DECISIONS.md).

    Idempotente: se a task já existir, é desregistrada e recriada com a
    nova configuração. Roda como o usuário atual (sem `-User SYSTEM`,
    para evitar a complicação de senha em interativo).

    Default: dispara todo dia às 22:00 hora local da máquina.
    A escolha de "hora local" é deliberada — quem opera está em
    Brasília, e essa máquina deve estar em America/Sao_Paulo. Se a
    máquina alvo estiver em outro fuso, ajuste -At ou troque o fuso da
    máquina (não há suporte direto a "22:00 BRT" no Task Scheduler
    nativo).

.PARAMETER TaskName
    Nome registrado no Task Scheduler. Default: "MDP Incremental Update".

.PARAMETER At
    Hora do disparo, formato "HH:mm". Default: "22:00".

.PARAMETER Days
    Lookback em dias passado para `scheduled_update.ps1 -Days`. Default: 5.

.EXAMPLE
    # Registrar com defaults (22:00 local, lookback 5 dias)
    .\Register-ScheduledTask.ps1

.EXAMPLE
    # Customizar
    .\Register-ScheduledTask.ps1 -At "21:30" -Days 10

.NOTES
    Para desregistrar: Unregister-ScheduledTask -TaskName "MDP Incremental Update" -Confirm:$false
    Para inspecionar:  Get-ScheduledTask -TaskName "MDP Incremental Update"
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MDP Incremental Update",
    [string]$At = "22:00",
    [int]$Days = 5
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WrapperPath = Join-Path $ScriptDir "scheduled_update.ps1"

if (-not (Test-Path $WrapperPath)) {
    throw "Wrapper não encontrado em $WrapperPath. Execute este script a partir de scripts/."
}

# Compõe a linha de comando do PowerShell que o Scheduler vai executar.
# -NoProfile evita carregar profile do usuário (mais rápido / determinístico).
# -ExecutionPolicy Bypass libera execução do .ps1 mesmo se a policy do
# usuário for Restricted. -File invoca o wrapper com o argumento -Days.
$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$WrapperPath`" -Days $Days"

$Trigger = New-ScheduledTaskTrigger -Daily -At $At

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

# StartWhenAvailable: se a máquina estiver dormindo às 22h, dispara assim
# que voltar. ExecutionTimeLimit: 2h. update-prices completa em ~10min com
# rate-limit de yfinance — 2h é margem confortável e mata runs enroscados.

# Idempotência: se já existe, desregistra antes de recriar.
$Existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($Existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "MDP — atualização incremental diária (ISSUE-015)" | Out-Null

Write-Host "Task '$TaskName' registrada. Dispara diariamente às $At." -ForegroundColor Green
Write-Host "Lookback: $Days dias. Wrapper: $WrapperPath" -ForegroundColor Green
Write-Host "Inspecionar:  Get-ScheduledTask -TaskName '$TaskName' | Format-List *"
Write-Host "Desregistrar: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
