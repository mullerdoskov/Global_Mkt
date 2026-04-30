#!/usr/bin/env bash
# ISSUE-015 — wrapper para cron / WSL.
#
# Resolve o root do projeto (a partir do path do próprio script),
# ativa o venv se existir, carrega .env, e delega para o módulo Python
# backend.scheduling.incremental_update.
#
# Toda a lógica fica no módulo Python (testável). Este script é apenas
# environment setup.
#
# Uso:
#     ./scheduled_update.sh           # lookback default (5 dias)
#     ./scheduled_update.sh 10        # lookback customizado
#
# Exit codes (propagados do módulo Python):
#     0 = OK
#     1 = falha não recuperada
#     2 = run completo com erros parciais
#
# Exemplo de linha cron (diário 22h, log do wrapper em /tmp):
#     0 22 * * * /caminho/para/scheduled_update.sh >> /tmp/mdp_wrapper.log 2>&1

set -euo pipefail

DAYS="${1:-5}"
LOG_DIR="${2:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Ativa venv se existir
for name in .venv venv; do
    if [ -f "$PROJECT_ROOT/$name/bin/activate" ]; then
        # shellcheck disable=SC1090
        . "$PROJECT_ROOT/$name/bin/activate"
        break
    fi
done

# Carrega .env (formato KEY=VALUE, ignora comentários e linhas vazias)
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$PROJECT_ROOT/.env"
    set +a
fi

PY_ARGS=("-m" "backend.scheduling.incremental_update" "-d" "$DAYS")
if [ -n "$LOG_DIR" ]; then
    PY_ARGS+=("--log-dir" "$LOG_DIR")
fi

exec python "${PY_ARGS[@]}"
