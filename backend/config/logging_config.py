"""
Logging rotativo configurável.
"""

import logging
from logging.handlers import RotatingFileHandler
from backend.config.settings import settings


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("market_platform")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File handler (rotativo)
    try:
        fh = RotatingFileHandler(
            settings.LOG_FILE,
            maxBytes=settings.LOG_MAX_BYTES,
            backupCount=settings.LOG_BACKUP_COUNT,
        )
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    except (PermissionError, OSError):
        logger.warning("Não foi possível criar log em arquivo. Usando apenas console.")

    return logger


logger = setup_logging()
