"""Atualização incremental agendada — wrapper testável de `update_prices`.

ISSUE-015: Windows Task Scheduler / cron invocam um wrapper shell que
chama este módulo. A lógica fica aqui (Python) para ser testável; os
shell scripts em `scripts/` carregam apenas variáveis de ambiente e
delegam.

Contrato de exit code (consumido pelo Task Scheduler / cron):
- 0  → run completou e todas as ingestões foram bem-sucedidas.
- 2  → run completou mas houve N>0 erros parciais. Considerado
       "completo com warnings" — o Task Scheduler não deve
       reagendar automaticamente; o operador inspeciona o log.
- 1  → falha não recuperada (exception). Ação humana necessária.

Justificativa do código 2 separado: sem ele, qualquer falha parcial
de yfinance (rate-limit em 1 ticker de ~600) marcaria o run inteiro
como FAILED no Task Scheduler. Diferenciar permite alertar com
prioridade certa.

Uso direto:
    python -m backend.scheduling.incremental_update [-d 5] [--log-dir DIR]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional, Tuple

EXIT_OK = 0
EXIT_HARD_FAIL = 1
EXIT_PARTIAL = 2

DEFAULT_LOOKBACK_DAYS = 5

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_LOG_DIR = _PROJECT_ROOT / "logs" / "scheduler"


def _resolve_log_dir(override: Optional[str]) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    env = os.environ.get("SCHEDULER_LOG_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return DEFAULT_LOG_DIR


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


def _build_run_log_path(log_dir: Path, stamp: Optional[str] = None) -> Path:
    return log_dir / f"incremental_update_{stamp or _utc_stamp()}.log"


def _make_file_handler(log_path: Path) -> logging.FileHandler:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setLevel(logging.INFO)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
    )
    return handler


def run_incremental_update(
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    log_dir: Optional[Path] = None,
    update_fn: Optional[Callable[[int], Tuple[int, int]]] = None,
    stamp: Optional[str] = None,
) -> int:
    """Executa a atualização incremental e retorna exit code.

    Parameters
    ----------
    lookback_days
        Quantos dias para trás re-baixar. Default 5 (mesmo do CLI).
    log_dir
        Diretório onde gravar o log do run. Default: `logs/scheduler/`
        relativo à raiz do projeto. Pode ser sobrescrito por
        `SCHEDULER_LOG_DIR`.
    update_fn
        Injetável para testes. Por padrão importa
        `backend.ingestion.loader.update_prices`. A função deve aceitar
        um inteiro `lookback_days` e retornar tupla `(success, errors)`.
    stamp
        Timestamp UTC pré-formatado para o nome do arquivo. Default:
        `_utc_stamp()` na hora da chamada.
    """
    if lookback_days < 1:
        raise ValueError(
            f"lookback_days deve ser >=1, recebido {lookback_days!r}"
        )

    resolved_log_dir = log_dir if log_dir is not None else _resolve_log_dir(None)
    log_path = _build_run_log_path(resolved_log_dir, stamp)
    file_handler = _make_file_handler(log_path)

    logger = logging.getLogger("scheduler.incremental_update")
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    started_at = datetime.now(timezone.utc)
    logger.info(
        "Run iniciado: lookback_days=%d, log_path=%s",
        lookback_days,
        log_path,
    )

    try:
        if update_fn is None:
            from backend.ingestion.loader import update_prices as update_fn  # noqa: PLC0415

        success, errors = update_fn(lookback_days)
        finished_at = datetime.now(timezone.utc)
        elapsed = (finished_at - started_at).total_seconds()
        logger.info(
            "Run concluído: success=%d, errors=%d, elapsed=%.1fs",
            success,
            errors,
            elapsed,
        )
        return EXIT_PARTIAL if errors > 0 else EXIT_OK
    except Exception:
        logger.exception("Run abortado por exception não tratada")
        return EXIT_HARD_FAIL
    finally:
        logger.removeHandler(file_handler)
        file_handler.close()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m backend.scheduling.incremental_update",
        description="Atualização incremental dos últimos N dias (ISSUE-015).",
    )
    parser.add_argument(
        "-d",
        "--days",
        type=int,
        default=DEFAULT_LOOKBACK_DAYS,
        help=f"Lookback em dias (default: {DEFAULT_LOOKBACK_DAYS}).",
    )
    parser.add_argument(
        "--log-dir",
        default=None,
        help=(
            "Diretório de log. Default: <repo>/logs/scheduler/. "
            "Sobrescrito por env SCHEDULER_LOG_DIR."
        ),
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    log_dir = _resolve_log_dir(args.log_dir)
    return run_incremental_update(lookback_days=args.days, log_dir=log_dir)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
