import os

import pytest

# Define antes de qualquer import do backend para que load_dotenv() e pydantic-settings
# não sobrescrevam com as credenciais reais do .env
os.environ.setdefault("MARKET_DB_URL", "sqlite:///./test_market.db")

# Rate limiting (ISSUE-010): em testes o limiter é instanciado como no-op para
# não interferir nos smoke tests, que disparam várias chamadas em sequência da
# mesma origem (TestClient). Os testes específicos de rate limiting alternam
# `limiter.enabled=True` localmente via fixture (ver test_rate_limiting.py).
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

# Cache (ISSUE-011): em testes o `@cache(...)` é no-op via `enable=False` na
# inicialização do FastAPICache. Mantém o decorador instalado nas rotas mas
# faz com que cada chamada exercite o handler real — essencial para os smoke
# tests que verificam efeitos (chamadas a session.execute) e para o teste de
# rate limiting que dispara 80 requisições e exige 80 execuções de handler.
# Os testes específicos de cache (`test_cache.py`) re-inicializam localmente.
os.environ.setdefault("CACHE_ENABLED", "false")


@pytest.fixture(autouse=True, scope="session")
def _init_cache_for_tests():
    """ISSUE-014: substitui o side effect de import que `_cache.py` tinha.

    Antes desta fixture, `backend.api._cache` chamava `init_cache_sync()` no
    momento do import — necessário porque `TestClient(app)` sem context-manager
    não dispara o lifespan, e qualquer rota decorada com `@cache(...)` falharia
    com `AssertionError: You must call FastAPICache.init`.

    Movido para fixture session-scoped autouse: efeito equivalente, sem poluir
    o módulo com side effect. `init_cache_sync` chama `FastAPICache.reset()`
    antes de `init`, então é seguro re-rodar mesmo que `test_cache.py` tenha
    re-inicializado localmente em testes anteriores.
    """
    from backend.api._cache import init_cache_sync
    init_cache_sync()
    yield
