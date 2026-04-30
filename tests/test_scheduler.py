"""Testes do agendamento (ISSUE-015).

Cobre:
- O módulo Python `backend.scheduling.incremental_update`:
  * exit codes 0 / 1 / 2 conforme contrato.
  * geração de arquivo de log per-run com timestamp.
  * resolução de log dir (default vs override vs env var).
  * propagação correta de lookback_days.
  * validação de input.
- Static checks sobre os wrappers shell (`scheduled_update.ps1`,
  `scheduled_update.sh`, `Register-ScheduledTask.ps1`):
  * existem.
  * delegam ao módulo Python (não duplicam lógica).
  * `.sh` tem shebang e é syntaticamente válido (`bash -n`) quando
    bash estiver disponível no ambiente.
  * `Register-ScheduledTask.ps1` configura trigger diário 22:00
    apontando para `scheduled_update.ps1`.

Não toca rede, banco ou yfinance. `update_prices` é sempre injetado
como fake.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from backend.scheduling import incremental_update as mod
from backend.scheduling.incremental_update import (
    DEFAULT_LOOKBACK_DAYS,
    EXIT_HARD_FAIL,
    EXIT_OK,
    EXIT_PARTIAL,
    _build_run_log_path,
    _resolve_log_dir,
    main,
    run_incremental_update,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
PS1_WRAPPER = SCRIPTS_DIR / "scheduled_update.ps1"
SH_WRAPPER = SCRIPTS_DIR / "scheduled_update.sh"
PS1_REGISTER = SCRIPTS_DIR / "Register-ScheduledTask.ps1"


# ---------------------------------------------------------------------------
# Python module: exit code contract
# ---------------------------------------------------------------------------


def test_returns_exit_ok_when_no_errors(tmp_path):
    def fake_update(days: int):
        return (42, 0)

    code = run_incremental_update(
        lookback_days=5, log_dir=tmp_path, update_fn=fake_update
    )
    assert code == EXIT_OK


def test_returns_exit_partial_when_errors_positive(tmp_path):
    def fake_update(days: int):
        return (40, 2)

    code = run_incremental_update(
        lookback_days=5, log_dir=tmp_path, update_fn=fake_update
    )
    assert code == EXIT_PARTIAL


def test_returns_exit_hard_fail_when_update_raises(tmp_path):
    def fake_update(days: int):
        raise RuntimeError("yfinance offline")

    code = run_incremental_update(
        lookback_days=5, log_dir=tmp_path, update_fn=fake_update
    )
    assert code == EXIT_HARD_FAIL


def test_zero_success_zero_errors_is_ok(tmp_path):
    """Pipeline rodou mas não havia ativos a atualizar — sucesso vacuo."""
    def fake_update(days: int):
        return (0, 0)

    code = run_incremental_update(
        lookback_days=5, log_dir=tmp_path, update_fn=fake_update
    )
    assert code == EXIT_OK


# ---------------------------------------------------------------------------
# Python module: lookback_days plumbing
# ---------------------------------------------------------------------------


def test_lookback_days_passed_through(tmp_path):
    captured = {}

    def fake_update(days: int):
        captured["days"] = days
        return (1, 0)

    run_incremental_update(
        lookback_days=10, log_dir=tmp_path, update_fn=fake_update
    )
    assert captured["days"] == 10


def test_default_lookback_is_five(tmp_path):
    captured = {}

    def fake_update(days: int):
        captured["days"] = days
        return (1, 0)

    run_incremental_update(log_dir=tmp_path, update_fn=fake_update)
    assert captured["days"] == DEFAULT_LOOKBACK_DAYS == 5


@pytest.mark.parametrize("invalid", [0, -1, -100])
def test_invalid_lookback_raises(tmp_path, invalid):
    def fake_update(days: int):  # pragma: no cover — não deve ser chamado
        return (1, 0)

    with pytest.raises(ValueError):
        run_incremental_update(
            lookback_days=invalid, log_dir=tmp_path, update_fn=fake_update
        )


# ---------------------------------------------------------------------------
# Python module: log file
# ---------------------------------------------------------------------------


def test_log_file_created_with_expected_naming(tmp_path):
    def fake_update(days: int):
        return (1, 0)

    run_incremental_update(
        lookback_days=5,
        log_dir=tmp_path,
        update_fn=fake_update,
        stamp="2026-04-30T220000Z",
    )
    expected = tmp_path / "incremental_update_2026-04-30T220000Z.log"
    assert expected.exists()
    content = expected.read_text(encoding="utf-8")
    assert "Run iniciado" in content
    assert "Run concluído" in content
    assert "success=1" in content
    assert "errors=0" in content


def test_log_captures_traceback_on_hard_fail(tmp_path):
    def fake_update(days: int):
        raise RuntimeError("boom")

    code = run_incremental_update(
        lookback_days=5,
        log_dir=tmp_path,
        update_fn=fake_update,
        stamp="2026-04-30T230000Z",
    )
    assert code == EXIT_HARD_FAIL
    log = (tmp_path / "incremental_update_2026-04-30T230000Z.log").read_text(
        encoding="utf-8"
    )
    assert "Run abortado" in log
    assert "RuntimeError" in log
    assert "boom" in log


def test_log_dir_is_created_if_missing(tmp_path):
    target = tmp_path / "deep" / "nested" / "logs"

    def fake_update(days: int):
        return (1, 0)

    assert not target.exists()
    run_incremental_update(lookback_days=5, log_dir=target, update_fn=fake_update)
    assert target.exists()
    assert any(target.iterdir())


def test_build_run_log_path_format():
    log_dir = Path("/tmp/mdp/sched")
    p = _build_run_log_path(log_dir, "2026-04-30T223000Z")
    assert p.name == "incremental_update_2026-04-30T223000Z.log"
    assert p.parent == log_dir


def test_build_run_log_path_stamp_is_utc_iso_like():
    log_dir = Path("/tmp")
    p = _build_run_log_path(log_dir)
    # stamp default tem formato YYYY-MM-DDTHHMMSSZ
    assert re.match(
        r"^incremental_update_\d{4}-\d{2}-\d{2}T\d{6}Z\.log$",
        p.name,
    ), p.name


# ---------------------------------------------------------------------------
# Python module: log dir resolution
# ---------------------------------------------------------------------------


def test_resolve_log_dir_default_is_repo_logs_scheduler():
    # Sem override e sem env var, default = <repo>/logs/scheduler
    saved = os.environ.pop("SCHEDULER_LOG_DIR", None)
    try:
        resolved = _resolve_log_dir(None)
        assert resolved.name == "scheduler"
        assert resolved.parent.name == "logs"
    finally:
        if saved is not None:
            os.environ["SCHEDULER_LOG_DIR"] = saved


def test_resolve_log_dir_env_var_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("SCHEDULER_LOG_DIR", str(tmp_path))
    resolved = _resolve_log_dir(None)
    assert resolved == tmp_path.resolve()


def test_resolve_log_dir_explicit_override_wins_over_env(tmp_path, monkeypatch):
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.setenv("SCHEDULER_LOG_DIR", str(tmp_path))
    resolved = _resolve_log_dir(str(other))
    assert resolved == other.resolve()


# ---------------------------------------------------------------------------
# Python module: argparse / main()
# ---------------------------------------------------------------------------


def test_main_passes_args_to_runner(monkeypatch, tmp_path):
    captured = {}

    def fake_runner(lookback_days, log_dir):
        captured["days"] = lookback_days
        captured["log_dir"] = log_dir
        return EXIT_OK

    monkeypatch.setattr(mod, "run_incremental_update", fake_runner)
    rc = main(["-d", "7", "--log-dir", str(tmp_path)])
    assert rc == EXIT_OK
    assert captured["days"] == 7
    assert captured["log_dir"] == tmp_path.resolve()


def test_main_uses_defaults(monkeypatch):
    captured = {}

    def fake_runner(lookback_days, log_dir):
        captured["days"] = lookback_days
        captured["log_dir"] = log_dir
        return EXIT_OK

    monkeypatch.setattr(mod, "run_incremental_update", fake_runner)
    monkeypatch.delenv("SCHEDULER_LOG_DIR", raising=False)
    rc = main([])
    assert rc == EXIT_OK
    assert captured["days"] == DEFAULT_LOOKBACK_DAYS
    # default log dir = repo/logs/scheduler
    assert captured["log_dir"].name == "scheduler"


# ---------------------------------------------------------------------------
# Static checks: wrappers exist and delegate (não duplicam lógica)
# ---------------------------------------------------------------------------


def test_ps1_wrapper_exists():
    assert PS1_WRAPPER.exists(), f"esperado em {PS1_WRAPPER}"


def test_sh_wrapper_exists():
    assert SH_WRAPPER.exists(), f"esperado em {SH_WRAPPER}"


def test_register_task_script_exists():
    assert PS1_REGISTER.exists(), f"esperado em {PS1_REGISTER}"


def test_ps1_wrapper_delegates_to_python_module():
    body = PS1_WRAPPER.read_text(encoding="utf-8")
    # Não tenta reimplementar update_prices em PowerShell — só delega.
    assert "backend.scheduling.incremental_update" in body
    # Carrega .env e ativa venv (passos de environment setup).
    assert ".env" in body
    assert "venv" in body or ".venv" in body


def test_sh_wrapper_has_shebang_and_delegates():
    body = SH_WRAPPER.read_text(encoding="utf-8")
    assert body.startswith("#!/usr/bin/env bash") or body.startswith("#!/bin/bash")
    assert "backend.scheduling.incremental_update" in body
    assert "set -e" in body  # propaga erros
    assert ".env" in body


def test_sh_wrapper_passes_bash_n():
    """bash -n faz parse syntax sem executar. Só roda se bash funcional existir."""
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash não disponível neste ambiente")
    probe = subprocess.run(
        [bash, "-c", "exit 0"], capture_output=True, text=True, timeout=10
    )
    if probe.returncode != 0:
        pytest.skip(
            f"bash presente mas não funcional (provável WSL relay sem distro): "
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


def test_register_task_uses_daily_22h_trigger():
    body = PS1_REGISTER.read_text(encoding="utf-8")
    # Trigger diário, 22:00 default. Inspeção textual — Register-ScheduledTask
    # não está disponível em todo ambiente de teste (Linux/CI), então
    # verificamos a configuração em vez do efeito.
    assert "New-ScheduledTaskTrigger" in body
    assert "-Daily" in body
    assert '"22:00"' in body
    # Aponta para o wrapper
    assert "scheduled_update.ps1" in body
    # Idempotente
    assert "Unregister-ScheduledTask" in body
