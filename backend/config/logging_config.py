"""
config/logging_config.py
Log stdout + arquivo rotativo 10MB.

ISSUE-014: importar este módulo é um no-op. Em particular, NÃO cria mais o
diretório `logs/` nem abre file handler. A inicialização acontece somente
quando algum caller invoca `setup_logging()` ou `get_logger(name)`.
"""

from __future__ import annotations

import os
import logging
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, "market_platform.log")
MAX_BYTES = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configura o logger raiz `market_platform` (stdout + arquivo rotativo).

    Idempotente: se o logger já tem handlers, retorna sem reconfigurar.
    Pode ser chamado múltiplas vezes sem duplicar saída.
    """
    logger = logging.getLogger("market_platform")
    logger.setLevel(level)

    if logger.handlers:
        return logger

    # Cria o diretório de logs apenas quando alguém de fato vai logar — não
    # mais em escopo de import.
    os.makedirs(LOG_DIR, exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(fmt)
    logger.addHandler(console)

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str | None = None, level: int = logging.INFO) -> logging.Logger:
    """Retorna o logger `market_platform` ou um child (`name`) já configurado.

    Recomendado para módulos que só precisam *usar* o logger — em vez de
    `logger = setup_logging()` em escopo de import (que dispara filesystem
    side effects), use `logger = get_logger(__name__)` dentro da função ou
    no escopo do módulo se realmente necessário.
    """
    setup_logging(level=level)
    if name is None or name == "market_platform":
        return logging.getLogger("market_platform")
    return logging.getLogger(f"market_platform.{name}")
