"""Testes do backup automatico do PostgreSQL (ISSUE-023).

ISSUE-023 e puramente shell — pg_dump faz o trabalho. Nao ha modulo
Python a testar. Os testes sao todos static checks sobre os scripts:
verificam que existem, que o conteudo cobre os requisitos do
DECISIONS.md (URL passthrough, abort em sqlite, retencao por mtime,
log per-run), e que o registrador do Task Scheduler usa trigger
semanal idempotente apontando para o wrapper.

Nao toca rede, banco real, nem chama pg_dump. Todos os checks sao
read-only sobre o filesystem.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
PS1_WRAPPER = SCRIPTS_DIR / "backup_postgres.ps1"
SH_WRAPPER = SCRIPTS_DIR / "backup_postgres.sh"
PS1_REGISTER = SCRIPTS_DIR / "Register-BackupTask.ps1"


# ---------------------------------------------------------------------------
# Existencia
# ---------------------------------------------------------------------------


def test_ps1_wrapper_exists():
    assert PS1_WRAPPER.exists(), f"esperado em {PS1_WRAPPER}"


def test_sh_wrapper_exists():
    assert SH_WRAPPER.exists(), f"esperado em {SH_WRAPPER}"


def test_register_backup_task_exists():
    assert PS1_REGISTER.exists(), f"esperado em {PS1_REGISTER}"


# ---------------------------------------------------------------------------
# PS1 wrapper: conteudo
# ---------------------------------------------------------------------------


def test_ps1_loads_dotenv():
    body = PS1_WRAPPER.read_text(encoding="utf-8")
    # Carrega .env para ter acesso a MARKET_DB_URL
    assert ".env" in body
    assert "MARKET_DB_URL" in body


def test_ps1_aborts_on_sqlite_url():
    body = PS1_WRAPPER.read_text(encoding="utf-8")
    # Backup nao se aplica a SQLite — deve abortar com exit 1
    assert 'StartsWith("sqlite' in body or 'sqlite:' in body
    # Mensagem mencionando filesystem ou copia
    assert "filesystem" in body.lower() or "copia" in body.lower()


def test_ps1_uses_pg_dump_with_custom_format():
    body = PS1_WRAPPER.read_text(encoding="utf-8")
    assert "pg_dump" in body
    # -Fc = formato custom, ja comprimido (decisao em DECISIONS.md)
    assert "-Fc" in body
    # Strip do +psycopg2 antes de passar para pg_dump (pg_dump nao reconhece)
    assert "psycopg2" in body


def test_ps1_writes_log_per_run():
    body = PS1_WRAPPER.read_text(encoding="utf-8")
    # Log com timestamp UTC, similar ao scheduler (ISSUE-015)
    assert "backup_" in body
    assert ".log" in body
    assert "ToUniversalTime" in body or "Z" in body  # UTC


def test_ps1_implements_retention_by_mtime():
    body = PS1_WRAPPER.read_text(encoding="utf-8")
    # Retencao: deletar .dump com LastWriteTime mais antigo que cutoff
    assert "LastWriteTime" in body
    assert "AddDays" in body
    assert "Remove-Item" in body
    assert "market_db_*.dump" in body


def test_ps1_default_retention_is_90_days():
    body = PS1_WRAPPER.read_text(encoding="utf-8")
    # Default = 90 dias (~12 semanas, ~3 meses)
    assert "90" in body


def test_ps1_exit_codes_documented():
    body = PS1_WRAPPER.read_text(encoding="utf-8")
    # Tres exit codes contratuais: 0 OK, 1 hard fail, 2 partial (warnings)
    assert "exit 0" in body
    assert "exit 1" in body
    assert "exit 2" in body


# ---------------------------------------------------------------------------
# SH wrapper: conteudo
# ---------------------------------------------------------------------------


def test_sh_has_shebang_and_strict_mode():
    body = SH_WRAPPER.read_text(encoding="utf-8")
    assert body.startswith("#!/usr/bin/env bash") or body.startswith("#!/bin/bash")
    # set -euo pipefail — strict mode
    assert "set -euo pipefail" in body or "set -e" in body


def test_sh_loads_dotenv():
    body = SH_WRAPPER.read_text(encoding="utf-8")
    assert ".env" in body
    assert "MARKET_DB_URL" in body


def test_sh_aborts_on_sqlite_url():
    body = SH_WRAPPER.read_text(encoding="utf-8")
    assert "sqlite:" in body
    # Mensagem mencionando filesystem ou copia
    assert "filesystem" in body.lower() or "copia" in body.lower()


def test_sh_uses_pg_dump_with_custom_format():
    body = SH_WRAPPER.read_text(encoding="utf-8")
    assert "pg_dump" in body
    assert "-Fc" in body
    assert "psycopg2" in body  # strip do +psycopg2


def test_sh_implements_retention_via_find_mtime():
    body = SH_WRAPPER.read_text(encoding="utf-8")
    # find -mtime +N -type f para listar candidatos a purga
    assert "find" in body
    assert "-mtime" in body
    assert "market_db_*.dump" in body


def test_sh_passes_bash_n():
    """bash -n faz parse syntax sem executar. So roda se bash funcional existir."""
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash nao disponivel neste ambiente")
    probe = subprocess.run(
        [bash, "-c", "exit 0"], capture_output=True, text=True, timeout=10
    )
    if probe.returncode != 0:
        pytest.skip(
            f"bash presente mas nao funcional (provavel WSL relay sem distro): "
            f"stderr={probe.stderr!r}"
        )
    result = subprocess.run(
        [bash, "-n", str(SH_WRAPPER)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"bash -n falhou: stderr={result.stderr!r}"
    )


# ---------------------------------------------------------------------------
# Register-BackupTask.ps1: configuracao
# ---------------------------------------------------------------------------


def test_register_uses_weekly_trigger():
    body = PS1_REGISTER.read_text(encoding="utf-8")
    # Inspeção textual — Register-ScheduledTask nao esta disponivel em
    # todo ambiente de teste. Verificamos a configuração em vez do efeito.
    assert "New-ScheduledTaskTrigger" in body
    assert "-Weekly" in body
    # Default: domingo
    assert "Sunday" in body


def test_register_default_at_03h_local():
    body = PS1_REGISTER.read_text(encoding="utf-8")
    # Default 03:00 hora local (justificativa em DECISIONS.md: domingo
    # de madrugada e a janela de menor uso)
    assert '"03:00"' in body


def test_register_points_to_backup_wrapper():
    body = PS1_REGISTER.read_text(encoding="utf-8")
    # Aponta para o .ps1 wrapper (e nao para qualquer outro script)
    assert "backup_postgres.ps1" in body


def test_register_is_idempotent():
    body = PS1_REGISTER.read_text(encoding="utf-8")
    # Se ja existe, desregistra antes de recriar — mesmo padrao do
    # Register-ScheduledTask.ps1 do ISSUE-015
    assert "Get-ScheduledTask" in body
    assert "Unregister-ScheduledTask" in body
    assert "Register-ScheduledTask" in body


def test_register_passes_retention_days_to_wrapper():
    body = PS1_REGISTER.read_text(encoding="utf-8")
    # -RetentionDays vai para o wrapper como argumento
    assert "-RetentionDays" in body
