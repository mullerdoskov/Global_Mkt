"""
api/_cache.py
Cache HTTP compartilhado por toda a API (ISSUE-011).

Estratégia em três camadas:

1. **InMemoryBackend síncrono** (`init_cache_sync`) é instalado no momento
   em que `backend.app` é importado, ANTES de qualquer requisição. Isso
   garante que o decorador `@cache(...)` em rotas funcione mesmo em testes
   que usam `TestClient(app)` sem context-manager (lifespan não roda).
   `FastAPICache` é classe singleton — chamadas posteriores a `init` apenas
   substituem o backend, sem efeito colateral em rotas decoradas.

2. **Upgrade opcional para Redis** (`init_cache_async`) acontece dentro do
   lifespan startup do FastAPI quando `settings.redis_url` está setada.
   Se o `ping()` falhar, log warning e continua com o InMemoryBackend já
   instalado pelo passo 1 — Redis é um nice-to-have, não bloqueia o start.

3. **Flag global** `settings.cache_enabled` é passada como `enable=` para
   `FastAPICache.init`. Quando `False`, `@cache(...)` vira no-op silencioso
   (não lê, não escreve, executa sempre o handler). Usado por `conftest.py`
   para que smoke tests não dependam do backend de cache. O wiring do
   decorador continua em vigor — o que muda é só o comportamento de leitura
   e escrita.

A escolha do InMemoryBackend como default (não Redis) é deliberada: ambiente
de dev local e CI normalmente não tem Redis rodando, e exigir Redis para
subir a API quebraria o setup atual. Quando `REDIS_URL` é setada, o cache
passa a ser distribuído (multi-worker, múltiplas instâncias compartilham
chaves). O trade-off de InMemoryBackend é cache process-local — ver
DECISIONS.md.
"""

from __future__ import annotations

import logging
from typing import Tuple

from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

from backend.config.settings import settings

logger = logging.getLogger(__name__)

# Prefixo aplicado a todas as chaves de cache. Mantém isolamento se um Redis
# vier a ser compartilhado entre apps no futuro.
CACHE_PREFIX = "mp"


def init_cache_sync() -> str:
    """
    Inicializa `FastAPICache` com `InMemoryBackend` de forma síncrona.

    Idempotente: chama `FastAPICache.reset()` antes do `init` para contornar
    a guarda interna `if cls._init: return` da fastapi-cache2 — caso contrário
    chamadas subsequentes (ex.: lifespan tentando upgrade para Redis) seriam
    silenciosamente ignoradas. Retorna o nome do backend para logging.
    """
    FastAPICache.reset()
    FastAPICache.init(
        backend=InMemoryBackend(),
        prefix=CACHE_PREFIX,
        enable=settings.cache_enabled,
    )
    return "in-memory"


async def init_cache_async() -> Tuple[str, bool]:
    """
    Tenta upgrade para `RedisBackend` se `settings.redis_url` estiver setada
    e o ping responder. Retorna `(backend_name, redis_active)`.

    Em qualquer falha (URL não setada, módulo redis ausente, ping falhou),
    cai de volta no `InMemoryBackend` síncrono — não levanta exceção. Cache
    ser opcional é decisão arquitetural; ver DECISIONS.md.

    `FastAPICache.reset()` é chamado antes de qualquer `init` para anular a
    guarda interna que ignoraria re-inicializações.
    """
    if not settings.redis_url:
        init_cache_sync()
        return ("in-memory", False)

    try:
        from redis import asyncio as aioredis
        from fastapi_cache.backends.redis import RedisBackend
    except ImportError as e:
        logger.warning(
            "REDIS_URL setada (%s) mas dependências ausentes (%s); "
            "caindo em InMemoryBackend.",
            settings.redis_url, e,
        )
        init_cache_sync()
        return ("in-memory (redis import failed)", False)

    try:
        redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf8",
            decode_responses=False,
        )
        await redis_client.ping()
    except Exception as e:
        logger.warning(
            "REDIS_URL setada (%s) mas conexão falhou (%s); "
            "caindo em InMemoryBackend.",
            settings.redis_url, e,
        )
        init_cache_sync()
        return ("in-memory (redis unreachable)", False)

    FastAPICache.reset()
    FastAPICache.init(
        backend=RedisBackend(redis_client),
        prefix=CACHE_PREFIX,
        enable=settings.cache_enabled,
    )
    return (f"redis ({settings.redis_url})", True)


# Side effect intencional no import: garante que `FastAPICache._backend` está
# instalado antes de qualquer rota decorada com `@cache(...)` ser exercitada.
# Caso contrário, testes que usam `TestClient(app)` sem context-manager (e que
# portanto não disparam o lifespan) acionariam `AssertionError: You must call
# FastAPICache.init` na primeira requisição. Idempotente e barato.
init_cache_sync()
