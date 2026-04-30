<#
.SYNOPSIS
    Backup do PostgreSQL via pg_dump, invocado pelo Windows Task Scheduler.

.DESCRIPTION
    ISSUE-023 — backups automaticos.

    Resolve o root do projeto a partir do path do proprio script,
    carrega .env, le MARKET_DB_URL, e dispara pg_dump em formato
    custom (-Fc, ja comprimido) para <BACKUP_DIR>/market_db_<UTC>.dump.

    Aborta com exit 1 se MARKET_DB_URL aponta para sqlite:// — backup
    nao se aplica a DB de arquivo. Em SQLite o backup e uma copia
    do .sqlite (responsabilidade do filesystem / OneDrive).

    Apos o dump, purga arquivos market_db_*.dump em <BACKUP_DIR> com
    LastWriteTime mais antigo que -RetentionDays (default 90).

    Toda a saida (pg_dump + log de retencao) vai para
    <LogDir>/backup_<UTC>.log. Senha NAO e logada.

.PARAMETER BackupDir
    Diretorio destino dos .dump. Default: <root>\backups\postgres\.
    Sobrescrevivel via env BACKUP_DIR.

.PARAMETER RetentionDays
    Idade em dias acima da qual .dump e deletado. Default: 90.
    Sobrescrevivel via env BACKUP_RETENTION_DAYS.

.PARAMETER LogDir
    Diretorio dos logs deste wrapper. Default: <root>\logs\backups\.
    Sobrescrevivel via env BACKUP_LOG_DIR.

.EXAMPLE
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File backup_postgres.ps1
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File backup_postgres.ps1 -RetentionDays 180

.NOTES
    Exit codes:
        0 = OK (dump + retencao concluidos)
        1 = falha (pg_dump nao encontrado, MARKET_DB_URL ausente / sqlite,
            ou pg_dump retornou nao-zero)
        2 = dump OK mas retencao gerou warnings (ex.: file in use)
#>
[CmdletBinding()]
param(
    [string]$BackupDir = "",
    [int]$RetentionDays = 0,
    [string]$LogDir = ""
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $ProjectRoot

# Carrega .env (formato KEY=VALUE)
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

# Resolve params (CLI flag > env var > default)
if (-not $BackupDir) { $BackupDir = $env:BACKUP_DIR }
if (-not $BackupDir) { $BackupDir = Join-Path $ProjectRoot "backups\postgres" }

if ($RetentionDays -le 0) {
    if ($env:BACKUP_RETENTION_DAYS) {
        $RetentionDays = [int]$env:BACKUP_RETENTION_DAYS
    } else {
        $RetentionDays = 90
    }
}

if (-not $LogDir) { $LogDir = $env:BACKUP_LOG_DIR }
if (-not $LogDir) { $LogDir = Join-Path $ProjectRoot "logs\backups" }

# Cria diretorios
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$Stamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHHmmssZ")
$LogFile = Join-Path $LogDir "backup_$Stamp.log"
$DumpFile = Join-Path $BackupDir "market_db_$Stamp.dump"

function Write-Log {
    param([string]$Message)
    $ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    $line = "[$ts] $Message"
    Add-Content -Path $LogFile -Value $line
}

Write-Log "Run iniciado. backup_dir=$BackupDir retention_days=$RetentionDays"

# Valida MARKET_DB_URL
$DbUrl = $env:MARKET_DB_URL
if (-not $DbUrl) {
    Write-Log "ERRO: MARKET_DB_URL nao setada. Backup abortado."
    exit 1
}
if ($DbUrl.StartsWith("sqlite:")) {
    Write-Log "ERRO: MARKET_DB_URL aponta para SQLite. pg_dump nao se aplica."
    Write-Log "Para SQLite, faca copia do arquivo .sqlite via filesystem."
    exit 1
}

# pg_dump aceita +psycopg2 desde PG 9.x? Nao — strip o driver tag.
$DbUrlClean = $DbUrl -replace '\+psycopg2', ''

# Verifica pg_dump no PATH
$PgDump = Get-Command pg_dump -ErrorAction SilentlyContinue
if (-not $PgDump) {
    Write-Log "ERRO: pg_dump nao encontrado no PATH. Instale o PostgreSQL client."
    exit 1
}
Write-Log "pg_dump=$($PgDump.Source)"

# Dump em formato custom (-Fc, ja comprimido). Senha vai pela URL —
# argumento curto: visivel em ps -ef em sistemas mal configurados.
# Aceitavel para single-machine em ambiente de confianca; documentado
# em DECISIONS.md.
Write-Log "Iniciando pg_dump -> $DumpFile"
& $PgDump.Source --dbname="$DbUrlClean" -Fc -f $DumpFile 2>&1 | ForEach-Object { Write-Log $_ }
$DumpExit = $LASTEXITCODE

if ($DumpExit -ne 0) {
    Write-Log "ERRO: pg_dump retornou $DumpExit. Backup abortado."
    if (Test-Path $DumpFile) { Remove-Item $DumpFile -Force }
    exit 1
}

$DumpSize = (Get-Item $DumpFile).Length
Write-Log "pg_dump OK. arquivo=$DumpFile bytes=$DumpSize"

# Retencao: deleta .dump com mtime mais antigo que RetentionDays
$Cutoff = (Get-Date).AddDays(-$RetentionDays)
$Pruned = 0
$PruneWarnings = 0
Get-ChildItem -Path $BackupDir -Filter "market_db_*.dump" -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -lt $Cutoff } |
    ForEach-Object {
        try {
            Remove-Item $_.FullName -Force -ErrorAction Stop
            Write-Log "PURGE $($_.Name) (mtime=$($_.LastWriteTime))"
            $Pruned++
        } catch {
            Write-Log "WARN purge falhou para $($_.Name): $_"
            $PruneWarnings++
        }
    }
Write-Log "Run concluido. dump_ok=1 pruned=$Pruned warnings=$PruneWarnings"

if ($PruneWarnings -gt 0) { exit 2 }
exit 0
