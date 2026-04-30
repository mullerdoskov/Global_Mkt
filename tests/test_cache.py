"""
tests/test_cache.py
Testes do cache HTTP (fastapi-cache2) — ISSUE-011.

Cobertura:

1. **Wiring** — FastAPICache foi inicializado em escopo de import por
   `backend.api._cache`. Backend é `InMemoryBackend` (default sem Redis URL),
   prefix é "mp", e `enable=False` em testes (definido por `conftest.py`).

2. **No-op quando desabilitado** — com `enable=False`, o decorador `@cache`
   não memoiza: múltiplas chamadas ao mesmo endpoint executam o handler N
   vezes (visto via mock de `session.execute`).

3. **Cache hit** — com `enable=True` e InMemoryBackend, a 2ª chamada não
   executa o handler real (zero novas execuções no mock).

4. **Diferentes query params produzem chaves distintas** — sectors com
   `period=90d` e `period=180d` ambos miss-cache na 1ª chamada.

5. **`init_cache_async` sem Redis URL** — cai limpo em InMemoryBackend.

6. **`init_cache_async` com Redis URL inválida** — falha graciosamente,
   InMemoryBackend mantido, sem exceção propagada.

Nenhum teste depende de Redis real disponível — InMemoryBackend cobre o
ciclo de hit/miss/clear.
"""

import asyncio
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

from backend.app import app
from backend.api import _cache as cache_mod
from backend.api import market as market_mod
from backend.config.settings import settings


client = TestClient(app, raise_server_exceptions=False)


# ════════════════════════════════════════════════════════════════════
# Helpers — reaproveita o estilo de mocks de test_api_smoke
# ════════════════════════════════════════════════════════════════════

def _result(scalar_one_or_none=None, scalars_all=None, scalar=None):
    """Constrói um stub para o retorno de `session.execute(...)`."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = scalar_one_or_none
    r.scalar.return_value = scalar
    scalars_proxy = MagicMock()
    scalars_proxy.all.return_value = scalars_all or []
    r.scalars.return_value = scalars_proxy
    return r


def _session_with_results(*results):
    """`session.execute` retorna um resultado por chamada, em sequência."""
    session = MagicMock()
    session.execute.side_effect = list(results) * 100  # repete pra sobrar
    return session


def _index_asset(symbol="^BVSP", asset_id=100):
    a = MagicMock()
    a.id = asset_id
    a.symbol = symbol
    a.name = f"Index {symbol}"
    a.asset_type = MagicMock()
    a.asset_type.value = "index"
    return a


def _index_price(asset_id, the_date, close):
    p = MagicMock()
    p.asset_id = asset_id
    p.date = the_date
    p.close = close
    return p


@pytest.fixture
def reset_cache_state():
    """
    Garante que cada teste comece com um estado limpo do FastAPICache.
    Re-inicializa em InMemoryBackend com `enable=False` (estado-padrão dos
    testes vindo do conftest.py) tanto antes quanto depois — porque a guarda
    `if cls._init: return` da fastapi-cache2 ignora `init` subsequentes a
    menos que `reset()` seja chamado. Os testes que querem `enable=True`
    fazem reset+init explicitamente no corpo.
    """
    FastAPICache.reset()
    FastAPICache.init(
        backend=InMemoryBackend(),
        prefix=cache_mod.CACHE_PREFIX,
        enable=False,
    )
    yield
    FastAPICache.reset()
    FastAPICache.init(
        backend=InMemoryBackend(),
        prefix=cache_mod.CACHE_PREFIX,
        enable=False,
    )


# ════════════════════════════════════════════════════════════════════
# 1. WIRING
# ════════════════════════════════════════════════════════════════════

class TestCacheWiring:
    def test_backend_instalado(self):
        # `init_cache_sync()` é chamado no import de `backend.api._cache`.
        # Sem isso, qualquer rota decorada com `@cache(...)` lançaria
        # `AssertionError: You must call init first!` na primeira request.
        backend = FastAPICache.get_backend()
        assert backend is not None
        assert isinstance(backend, InMemoryBackend)

    def test_prefix_correto(self):
        assert FastAPICache.get_prefix() == "mp"

    def test_enable_lido_de_settings(self):
        # `conftest.py` define CACHE_ENABLED=false → `settings.cache_enabled=False`
        # → `FastAPICache._enable=False`. Decoradores ficam montados mas
        # não cacheiam.
        assert settings.cache_enabled is False
        assert FastAPICache.get_enable() is False

    def test_decorador_aplicado_em_market_endpoints(self):
        # Verifica via repr/__wrapped__ que o handler foi decorado por
        # `@cache(...)`. Não dependemos do nome interno do wrapper — só
        # checamos que o handler em runtime difere da função "nua" e que
        # `__wrapped__` aponta para a original (convenção do `@functools.wraps`).
        for route in app.routes:
            path = getattr(route, "path", "")
            if path in ("/api/market/summary", "/api/market/sectors"):
                endpoint = route.endpoint
                # `cache` usa `@functools.wraps` no inner async — `__wrapped__`
                # só estaria presente se outro decorador (limiter) o setasse.
                # Em vez disso, garantimos que o nome do módulo é
                # fastapi_cache.decorator (o wrapper da cadeia mais externa
                # ainda preserva atributos via @wraps).
                # Checagem mais robusta: o handler tem o atributo extra
                # `__signature__` que o cache injeta com kwargs `__fastapi_cache_request`
                # e `__fastapi_cache_response`. Procuramos algum desses.
                import inspect
                params = inspect.signature(endpoint).parameters
                has_cache_injected = any(
                    "fastapi_cache" in p for p in params.keys()
                )
                assert has_cache_injected, (
                    f"endpoint {path} não parece ter sido decorado por @cache; "
                    f"params={list(params.keys())}"
                )


# ════════════════════════════════════════════════════════════════════
# 2. NO-OP QUANDO DESABILITADO (default em testes)
# ════════════════════════════════════════════════════════════════════

class TestCacheDisabledNoOp:
    def test_endpoint_executa_handler_em_toda_chamada_quando_desabilitado(self, reset_cache_state):
        # Defaults dos testes: enable=False. Cada chamada a /api/market/summary
        # deve executar o handler (e portanto consumir o mock de session) de
        # novo. Validamos via contagem de chamadas a session.execute: o
        # endpoint faz 3 queries por índice (asset, latest_price, prev_price);
        # com 1 índice mockado, 3 queries por request × 2 requests = 6 total.
        fake_indices = ["^BVSP"]
        bvsp_asset = _index_asset("^BVSP", asset_id=100)
        bvsp_now = _index_price(100, date(2026, 4, 25), 130000.0)
        bvsp_prev = _index_price(100, date(2026, 4, 24), 128000.0)

        session = _session_with_results(
            _result(scalar_one_or_none=bvsp_asset),
            _result(scalar_one_or_none=bvsp_now),
            _result(scalar_one_or_none=bvsp_prev),
        )

        with patch.object(market_mod, "get_session", return_value=session), \
             patch.object(market_mod, "INDICES", fake_indices):
            r1 = client.get("/api/market/summary")
            r2 = client.get("/api/market/summary")

        assert r1.status_code == 200
        assert r2.status_code == 200
        # 3 queries × 2 requests = 6. Se cache estivesse ativo (incorretamente),
        # a 2ª request retornaria do cache e session.execute seria chamado
        # apenas 3 vezes.
        assert session.execute.call_count == 6, (
            f"esperado 6 execuções (no-op cache), got {session.execute.call_count}"
        )


# ════════════════════════════════════════════════════════════════════
# 3. CACHE HIT REAL COM IN-MEMORY BACKEND
# ════════════════════════════════════════════════════════════════════

class TestCacheHitInMemory:
    def test_segunda_chamada_serve_do_cache(self, reset_cache_state):
        # Liga o cache localmente com InMemoryBackend e enable=True.
        # `reset()` é obrigatório porque `init` da fastapi-cache2 retorna
        # cedo se já inicializado.
        FastAPICache.reset()
        FastAPICache.init(
            backend=InMemoryBackend(),
            prefix=cache_mod.CACHE_PREFIX,
            enable=True,
        )

        fake_indices = ["^BVSP"]
        bvsp_asset = _index_asset("^BVSP", asset_id=100)
        bvsp_now = _index_price(100, date(2026, 4, 25), 130000.0)
        bvsp_prev = _index_price(100, date(2026, 4, 24), 128000.0)

        session = _session_with_results(
            _result(scalar_one_or_none=bvsp_asset),
            _result(scalar_one_or_none=bvsp_now),
            _result(scalar_one_or_none=bvsp_prev),
        )

        with patch.object(market_mod, "get_session", return_value=session), \
             patch.object(market_mod, "INDICES", fake_indices):
            r1 = client.get("/api/market/summary")
            r2 = client.get("/api/market/summary")

        assert r1.status_code == 200
        assert r2.status_code == 200
        # Conteúdo idêntico (cache devolve a mesma resposta serializada).
        assert r1.json() == r2.json()
        # Apenas a primeira request executou o handler — 3 queries no total.
        assert session.execute.call_count == 3, (
            f"esperado 3 execuções (1ª miss-cache, 2ª hit), "
            f"got {session.execute.call_count}"
        )

    def test_query_params_diferentes_geram_chaves_diferentes(self, reset_cache_state):
        # /api/market/sectors?period=90d e ?period=180d devem produzir entradas
        # de cache distintas — ambas miss-cache na 1ª chamada.
        FastAPICache.reset()
        FastAPICache.init(
            backend=InMemoryBackend(),
            prefix=cache_mod.CACHE_PREFIX,
            enable=True,
        )

        # Sector handler chama: sectors → companies → assets → prices.
        # Sem ativos válidos, retorna SectorPerformance com avg_return=None.
        # 4 execuções por request, 2 requests com chaves distintas → 8 total.
        sector = MagicMock()
        sector.id = 1
        sector.sector = "Energy"
        sector.sector_pt = "Energia"

        def _build_results():
            # Constrói uma sequência fresh para cada request — a 1ª request
            # consome 4, a 2ª consome outras 4. side_effect "*100" do helper
            # garante reposição.
            return [
                _result(scalars_all=[sector]),         # sectors
                _result(scalars_all=[]),               # companies (vazio)
            ]

        session = _session_with_results(*_build_results())

        with patch.object(market_mod, "get_session", return_value=session):
            r1 = client.get("/api/market/sectors?period=90d")
            r2 = client.get("/api/market/sectors?period=180d")
            # 3ª: repete o primeiro → cache hit, não executa handler
            r3 = client.get("/api/market/sectors?period=90d")

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 200

        # 1ª e 2ª são miss-cache (chaves distintas), executam handler:
        # 2 queries × 2 requests = 4 (sectors + companies cada).
        # 3ª é cache hit, zero queries adicionais. Total: 4.
        assert session.execute.call_count == 4, (
            f"esperado 4 execuções (2 misses + 1 hit), "
            f"got {session.execute.call_count}"
        )


# ════════════════════════════════════════════════════════════════════
# 4. UPGRADE PARA REDIS — sem Redis, com Redis indisponível
# ════════════════════════════════════════════════════════════════════

class TestInitCacheAsync:
    def test_sem_redis_url_retorna_in_memory(self, reset_cache_state):
        # Quando `settings.redis_url` é None, init_cache_async cai imediatamente
        # em InMemoryBackend e retorna a flag redis_active=False.
        with patch.object(settings, "redis_url", None):
            backend_name, redis_active = asyncio.run(cache_mod.init_cache_async())
        assert backend_name == "in-memory"
        assert redis_active is False
        assert isinstance(FastAPICache.get_backend(), InMemoryBackend)

    def test_redis_url_inacessivel_cai_em_in_memory(self, reset_cache_state):
        # URL aparentemente válida mas que não responde. O ping deve falhar
        # rapidamente; o init não deve propagar a exceção. Usamos uma porta
        # propositalmente fechada (1 = reservada) para garantir falha rápida.
        with patch.object(settings, "redis_url", "redis://127.0.0.1:1/0"):
            backend_name, redis_active = asyncio.run(cache_mod.init_cache_async())
        assert "in-memory" in backend_name
        assert "unreachable" in backend_name or "import" in backend_name or backend_name == "in-memory"
        assert redis_active is False
        assert isinstance(FastAPICache.get_backend(), InMemoryBackend)
