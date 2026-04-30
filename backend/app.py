"""
app.py
FastAPI app principal do market_platform_unified backend.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy.exc import SQLAlchemyError
from starlette.responses import JSONResponse

from backend.config.settings import settings
from backend.config.logging_config import setup_logging
from backend.db.connection import test_connection, engine
from backend.db.schema import create_all_tables
from backend.api.router import api_router
from backend.api.models import HealthResponse
from backend.api._limiter import limiter
from backend.api._cache import init_cache_async

# Diretório com o SPA estático (frontend/index.html). Resolvido a partir de
# backend/app.py para não depender do CWD em que uvicorn for invocado.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# ISSUE-024: importar `backend.app` é livre de I/O em disco — apenas referencia
# o logger. `setup_logging()` (cria `logs/`, anexa handlers) ficou para o
# lifespan. Antes desta issue a chamada acontecia em escopo de módulo,
# fazendo qualquer `import backend.app` criar o diretório `logs/` e abrir
# RotatingFileHandler. ISSUE-014 já tinha eliminado o mesmo padrão de
# `logging_config.py` e `_cache.py`; ISSUE-024 fecha o gap em `app.py`.
logger = logging.getLogger("market_platform")


# ══════════════════════════════════════════════
# LIFECYCLE — Startup / Shutdown
# ══════════════════════════════════════════════

def _log_startup_banner() -> None:
    """Emite as linhas de banner que antes ficavam em escopo de import.

    Chamado pelo lifespan logo após `setup_logging()`, mantém visibilidade
    do estado de boot (CORS, rate limiting, mount do frontend) sem incorrer
    em I/O em disco no momento do import.
    """
    logger.info("=" * 60)
    logger.info("🚀 Iniciando market_platform_unified backend")
    logger.info("=" * 60)
    logger.info(f"✅ CORS habilitado para: {cors_origins}")
    logger.info(
        f"✅ Rate limiting (slowapi) "
        f"{'habilitado' if settings.rate_limit_enabled else 'DESABILITADO (no-op)'}; "
        f"default={settings.rate_limit_default}"
    )
    if FRONTEND_DIR.is_dir():
        logger.info(f"✅ Frontend estático montado em / a partir de {FRONTEND_DIR}")
    else:
        logger.warning(
            f"⚠️  Diretório de frontend não encontrado em {FRONTEND_DIR}; "
            "rota / não disponível"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager para startup e shutdown da aplicação.
    """
    # ISSUE-024: setup_logging() (cria `logs/`, anexa StreamHandler +
    # RotatingFileHandler) é o primeiro passo do lifespan — não roda mais
    # em escopo de import. setup_logging é idempotente, então re-execuções
    # do lifespan (ex.: testes que entram/saem do TestClient) não duplicam
    # handlers.
    setup_logging()
    _log_startup_banner()

    # STARTUP
    logger.info("🔌 Testando conexão com banco de dados...")
    if not test_connection():
        logger.error("❌ Falha na conexão com o banco. Continuando mesmo assim...")
    else:
        logger.info("✅ Banco de dados conectado com sucesso")

    # Cria tabelas
    logger.info("📊 Criando/verificando tabelas...")
    try:
        create_all_tables(engine)
        logger.info("✅ Tabelas criadas/verificadas")
    except Exception as e:
        logger.error(f"⚠️  Erro ao criar tabelas: {e}")

    # Cache (ISSUE-011): tenta upgrade para Redis se REDIS_URL setada; caso
    # contrário mantém o InMemoryBackend já instalado em escopo de import por
    # `backend.api._cache`. Falha no Redis cai silenciosamente em InMemory.
    backend_name, redis_active = await init_cache_async()
    logger.info(
        f"✅ Cache: backend={backend_name}, "
        f"enabled={'sim' if settings.cache_enabled else 'NÃO (no-op)'}"
    )

    logger.info("✅ Backend iniciado com sucesso")

    yield

    # SHUTDOWN
    logger.info("🛑 Encerrando backend...")
    engine.dispose()
    logger.info("✅ Backend encerrado")


# ══════════════════════════════════════════════
# FAST API APP
# ══════════════════════════════════════════════

app = FastAPI(
    title="Market Platform Unified",
    description="API unificada de dados financeiros — preços, fundamentos, múltiplos",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ══════════════════════════════════════════════
# CORS MIDDLEWARE
# ══════════════════════════════════════════════

# Parse CORS origins. ISSUE-007: a origem "null" (que o navegador envia para
# arquivos abertos via file://) deixa de ser injetada — o frontend agora é
# servido pelo próprio backend via StaticFiles, mesmo origin que a API.
cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if "*" in cors_origins:
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ISSUE-024: o "✅ CORS habilitado..." virou parte de `_log_startup_banner()`,
# emitido pelo lifespan após setup_logging.


# ══════════════════════════════════════════════
# RATE LIMITING (ISSUE-010)
# ══════════════════════════════════════════════
#
# Limiter é compartilhado entre app e routers (ver `backend/api/_limiter.py`).
# Cada endpoint público dos sub-routers em `backend/api/*.py` usa
# `@limiter.limit(settings.rate_limit_default)`. Endpoints administrativos
# (`/health`, `/api/info`) ficam fora — health checks de monitoramento e
# discovery não devem ser limitados. Estáticos sob `/` (StaticFiles) também
# ficam fora porque o middleware só atua em rotas decoradas.
#
# Quando `settings.rate_limit_enabled=False` (ex.: testes), o limiter é
# instanciado como no-op — middleware e decoradores ficam em vigor, mas
# não bloqueiam.

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ISSUE-024: o "✅ Rate limiting..." virou parte de `_log_startup_banner()`,
# emitido pelo lifespan após setup_logging.


# ══════════════════════════════════════════════
# ERROR HANDLERS
# ══════════════════════════════════════════════

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request, exc):
    """Handler para erros SQLAlchemy."""
    logger.exception("Erro SQLAlchemy não tratado", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro ao acessar banco de dados"},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handler para exceções genéricas não tratadas."""
    logger.exception("Erro não tratado", exc_info=exc)
    if settings.debug:
        import traceback
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "traceback": traceback.format_exc()},
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor"},
    )


# ══════════════════════════════════════════════
# ROUTERS
# ══════════════════════════════════════════════

# Health check
@app.get("/health", response_model=HealthResponse, tags=["health"])
def health_check() -> HealthResponse:
    """
    Health check da API.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        database="connected",
    )


# Endpoint de "info" da API. ISSUE-007: movido de "/" para "{api_prefix}/info"
# porque "/" passa a servir o SPA estático (frontend/index.html). O conteúdo
# (nome/versão/descrição) é preservado para qualquer consumidor externo.
@app.get(f"{settings.api_prefix}/info", tags=["root"])
def api_info():
    """Informações sobre a API."""
    return {
        "name": "Market Platform Unified",
        "version": "1.0.0",
        "description": "API unificada de dados financeiros",
        "docs": "/docs",
        "api_prefix": settings.api_prefix,
    }


# Inclui routers da API
app.include_router(
    api_router,
    prefix=settings.api_prefix,
)


# ══════════════════════════════════════════════
# FRONTEND ESTÁTICO (ISSUE-007)
# ══════════════════════════════════════════════
#
# Mount registrado por último: rotas explícitas (/health, /docs, /openapi.json,
# /redoc, /api/*) já foram resolvidas pelo Starlette antes de a requisição cair
# aqui. Caminhos não cobertos são servidos a partir de frontend/, com html=True
# fazendo `/` retornar `frontend/index.html`.

if FRONTEND_DIR.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=FRONTEND_DIR, html=True),
        name="frontend",
    )

# ISSUE-024: a mensagem ("Frontend estático montado..." vs warning de diretório
# ausente) virou parte de `_log_startup_banner()`, emitido pelo lifespan após
# setup_logging.


# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn

    # ISSUE-024: quando rodado direto (`python backend/app.py`), uvicorn é
    # invocado a partir deste bloco — antes do lifespan que normalmente faz
    # setup_logging. Inicializa explicitamente aqui para que as duas linhas
    # abaixo não saiam para um logger sem handlers.
    setup_logging()
    logger.info(f"🚀 Iniciando servidor em {settings.host}:{settings.port}")
    logger.info(f"📖 Docs disponível em http://{settings.host}:{settings.port}/docs")

    uvicorn.run(
        "backend.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )
