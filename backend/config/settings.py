"""
config/settings.py
Configurações centralizadas usando pydantic-settings.
"""

from typing import Optional

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

    # Rate limit dedicado para o endpoint de exportação CSV (ISSUE-017).
    # Mais agressivo que o default: cada request retorna potencialmente
    # milhares de linhas do banco, então sem um gate apertado, varrer
    # todo o histórico fica trivial. Default 10/min/IP. Quando
    # `rate_limit_enabled=False` (testes), este limite também vira no-op.
    rate_limit_export: str = "10/minute"

    # Cache (ISSUE-011). Se `redis_url` setada, o backend de cache vira Redis
    # (e na presença de multi-worker, distribuído entre eles). Se não setada,
    # cai em InMemoryBackend (process-local). `cache_enabled=False` transforma
    # `@cache(...)` em no-op — testes usam isso, e dev local pode usar para
    # depurar sem interferência de cache.
    redis_url: Optional[str] = None
    cache_enabled: bool = True

    class Config:
        """Configuração de origem dos valores."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Instância global de settings
settings = Settings()
