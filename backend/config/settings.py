"""
Configurações centralizadas via pydantic-settings.
Lê variáveis do .env automaticamente.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── Banco de dados ──
    MARKET_DB_URL: str = "postgresql+psycopg2://postgres:141592@localhost:5432/market_db"

    # ── CORS ──
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # ── API ──
    API_PREFIX: str = "/api"
    PAGE_SIZE_DEFAULT: int = 50
    PAGE_SIZE_MAX: int = 200

    # ── Ingestão ──
    INGEST_BATCH_SIZE: int = 20
    INGEST_RATE_LIMIT: float = 0.5  # segundos entre requests
    INGEST_MAX_RETRIES: int = 3
    INGEST_BACKOFF_FACTOR: float = 2.0

    # ── Logging ──
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "market_platform.log"
    LOG_MAX_BYTES: int = 10_485_760  # 10 MB
    LOG_BACKUP_COUNT: int = 3

    @property
    def cors_origins_list(self) -> List[str]:
        origins = [o.strip() for o in self.CORS_ORIGINS.split(",")]
        if "null" not in origins:
            origins.append("null")  # suporte a file://
        return origins

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
