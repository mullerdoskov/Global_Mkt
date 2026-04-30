"""
config/logging_config.py
Log stdout + arquivo rotativo 10MB.
"""

import os
import logging
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, "market_platform.log")
MAX_BYTES = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5


def setup_logging(level=logging.INFO) -> logging.Logger:
    """Configura logging com saída stdout + arquivo rotativo."""
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger("market_platform")
    logger.setLevel(level)

    # Evita duplicação de handlers
    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler stdout
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(fmt)
    logger.addHandler(console)

    # Handler arquivo rotativo (10MB, 5 backups)
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


# Logger global
logger = setup_logging()
