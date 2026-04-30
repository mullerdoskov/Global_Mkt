"""
config/settings.py
Configurações centralizadas usando pydantic-settings.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configurações globais da aplicação."""

    # Banco de dados
    market_db_url: str = "postgresql+psycopg2://postgres:141592@localhost:5432/market_db"

    # CORS — origens permitidas
    cors_origins: str = "*"

    # API
    api_prefix: str = "/api"

    # Debug mode
    debug: bool = False

    # Porta e host
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        """Configuração de origem dos valores."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Instância global de settings
settings = Settings()
