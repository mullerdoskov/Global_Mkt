#!/usr/bin/env bash
# ISSUE-023 — backup automatico do PostgreSQL via pg_dump.
#
# Wrapper para cron / WSL. Equivalente shell do backup_postgres.ps1.
#
# Resolve o root do projeto a partir do path do proprio script,
# carrega .env, le MARKET_DB_URL, e dispara pg_dump em formato custom
# (-Fc, ja comprimido) para <BACKUP_DIR>/market_db_<UTC>.dump.
#
# Aborta com exit 1 se MARKET_DB_URL aponta para sqlite:// — backup
# nao se aplica a DB de arquivo (use o filesystem para SQLite).
#
# Apos o dump, purga arquivos market_db_*.dump em <BACKUP_DIR> com
# mtime mais antigo que $RETENTION_DAYS (default 90).
#
# Uso:
#     ./backup_postgres.sh                       # defaults
#     ./backup_postgres.sh --retention-days 180  # retencao customizada
#
# Sobrescritas via env:
#     BACKUP_DIR             — diretorio destino dos .dump
#     BACKUP_RETENTION_DAYS  — idade max em dias
#     BACKUP_LOG_DIR         — diretorio dos logs
#
# Exit codes:
#     0 = OK
#     1 = falha (URL ausente, sqlite, pg_dump nao encontrado, dump falhou)
#     2 = dump OK mas retencao gerou warnings
#
# Exemplo cron (semanal, domingo 03:00):
#     0 3 * * 0 /caminho/para/backup_postgres.sh >> /tmp/mdp_backup.log 2>&1

set -euo pipefail

RETENTION_DAYS=""
BACKUP_DIR_ARG=""
LOG_DIR_ARG=""
while [ $# -gt 0 ]; do
    case "$1" in
        --retention-days) RETENTION_DAYS="$2"; shift 2 ;;
        --backup-dir)     BACKUP_DIR_ARG="$2"; shift 2 ;;
        --log-dir)        LOG_DIR_ARG="$2"; shift 2 ;;
        *) echo "arg desconhecido: $1" >&2; exit 1 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Carrega .env (formato KEY=VALUE)
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$PROJECT_ROOT/.env"
    set +a
fi

# Resolve params (CLI flag > env var > default)
BACKUP_DIR="${BACKUP_DIR_ARG:-${BACKUP_DIR:-$PROJECT_ROOT/backups/postgres}}"
RETENTION_DAYS="${RETENTION_DAYS:-${BACKUP_RETENTION_DAYS:-90}}"
LOG_DIR="${LOG_DIR_ARG:-${BACKUP_LOG_DIR:-$PROJECT_ROOT/logs/backups}}"

mkdir -p "$BACKUP_DIR" "$LOG_DIR"

STAMP="$(date -u +%Y-%m-%dT%H%M%SZ)"
LOG_FILE="$LOG_DIR/backup_$STAMP.log"
DUMP_FILE="$BACKUP_DIR/market_db_$STAMP.dump"

log() {
    local ts
    ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "[$ts] $*" >> "$LOG_FILE"
}

log "Run iniciado. backup_dir=$BACKUP_DIR retention_days=$RETENTION_DAYS"

# Valida MARKET_DB_URL
if [ -z "${MARKET_DB_URL:-}" ]; then
    log "ERRO: MARKET_DB_URL nao setada. Backup abortado."
    exit 1
fi
if [[ "$MARKET_DB_URL" == sqlite:* ]]; then
    log "ERRO: MARKET_DB_URL aponta para SQLite. pg_dump nao se aplica."
    log "Para SQLite, faca copia do arquivo .sqlite via filesystem."
    exit 1
fi

DB_URL_CLEAN="${MARKET_DB_URL/+psycopg2/}"

# Verifica pg_dump no PATH
if ! command -v pg_dump >/dev/null 2>&1; then
    log "ERRO: pg_dump nao encontrado no PATH. Instale postgresql-client."
    exit 1
fi
log "pg_dump=$(command -v pg_dump)"

log "Iniciando pg_dump -> $DUMP_FILE"
if ! pg_dump --dbname="$DB_URL_CLEAN" -Fc -f "$DUMP_FILE" >> "$LOG_FILE" 2>&1; then
    log "ERRO: pg_dump retornou $?. Backup abortado."
    [ -f "$DUMP_FILE" ] && rm -f "$DUMP_FILE"
    exit 1
fi

DUMP_SIZE=$(stat -c%s "$DUMP_FILE" 2>/dev/null || stat -f%z "$DUMP_FILE")
log "pg_dump OK. arquivo=$DUMP_FILE bytes=$DUMP_SIZE"

# Retencao: deleta .dump com mtime mais antigo que RETENTION_DAYS.
# `-mtime +N` em find = mais que N dias. Usamos -print -delete para
# logar o que foi removido. find nao quebra o pipeline em set -e mesmo
# quando nao acha nada — comportamento desejado.
PRUNED=0
PRUNE_WARNINGS=0
while IFS= read -r f; do
    if rm -f "$f" 2>>"$LOG_FILE"; then
        log "PURGE $(basename "$f")"
        PRUNED=$((PRUNED + 1))
    else
        log "WARN purge falhou para $(basename "$f")"
        PRUNE_WARNINGS=$((PRUNE_WARNINGS + 1))
    fi
done < <(find "$BACKUP_DIR" -maxdepth 1 -name 'market_db_*.dump' -type f -mtime "+$RETENTION_DAYS" 2>/dev/null)

log "Run concluido. dump_ok=1 pruned=$PRUNED warnings=$PRUNE_WARNINGS"

if [ "$PRUNE_WARNINGS" -gt 0 ]; then
    exit 2
fi
exit 0
