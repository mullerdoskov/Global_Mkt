<#
.SYNOPSIS
    Wrapper PowerShell invocado pelo Windows Task Scheduler.

.DESCRIPTION
    ISSUE-015 — agendamento incremental.

    Resolve o root do projeto (a partir do path do próprio script),
    ativa o venv se existir, carrega .env, e delega para o módulo Python
    backend.scheduling.incremental_update.

    Toda a lógica de logging, exit codes e tratamento de erro fica no
    módulo Python (testável). Este script é apenas environment setup.

.PARAMETER Days
    Lookback em dias. Default: 5.

.PARAMETER LogDir
    Diretório de log. Default: <root>\logs\scheduler\.

.EXAMPLE
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File scheduled_update.ps1
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File scheduled_update.ps1 -Days 10

.NOTES
    Exit codes (propagados do módulo Python):
        0 = OK
        1 = falha não recuperada (exception)
        2 = run completo com erros parciais
#>
[CmdletBinding()]
param(
    [int]$Days = 5,
    [string]$LogDir = ""
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")

Set-Location $ProjectRoot

# Ativa venv se existir (procura .venv\ depois venv\)
$VenvActivate = $null
foreach ($name in @(".venv", "venv")) {
    $candidate = Join-Path $ProjectRoot "$name\Scripts\Activate.ps1"
    if (Test-Path $candidate) {
        $VenvActivate = $candidate
        break
    }
}
if ($VenvActivate) {
    . $VenvActivate
}

# Carrega .env (formato KEY=VALUE, ignora comentários e linhas vazias)
$EnvFile = Join-Path $ProjectRoot ".env"
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $key, $value = $line -split "=", 2
            [System.Environment]::SetEnvironmentVariable($key.Trim(), $value.Trim(), "Process")
        }
    }
}

# Delega ao módulo Python
$PyArgs = @("-m", "backend.scheduling.incremental_update", "-d", $Days)
if ($LogDir) {
    $PyArgs += @("--log-dir", $LogDir)
}

& python @PyArgs
exit $LASTEXITCODE
