"""
config/settings.py
Configurações centralizadas usando pydantic-settings.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configurações globais da aplicação."""

    # Banco de dados — obrigatório (sem default com credencial). Ver ISSUE-004.
    market_db_url: str

    # CORS — origens permitidas
    cors_origins: str = "*"

    # API
    api_prefix: str = "/api"

    # Debug mode
    debug: bool = False

    # Porta e host
    host: str = "0.0.0.0"
    port: int = 8000

    # Rate limiting (ISSUE-010). `rate_limit_default` aceita o vocabulário do
    # `limits` (ex.: "60/minute", "1000/hour"). `rate_limit_enabled=False`
    # transforma o limiter em no-op — usado pela suíte de testes para não
    # afetar smoke tests, e pode ser desligado em dev local se necessário.
    rate_limit_default: str = "60/minute"
    rate_limit_enabled: bool = True

    class Config:
        """Configuração de origem dos valores."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Instância global de settings
settings = Settings()
