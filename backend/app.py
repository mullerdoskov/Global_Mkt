"""
app.py
FastAPI app principal do market_platform_unified backend.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from starlette.responses import JSONResponse

from backend.config.settings import settings
from backend.config.logging_config import setup_logging
from backend.db.connection import test_connection, engine
from backend.db.schema import create_all_tables
from backend.api.router import api_router
from backend.api.models import HealthResponse

# Setup logging
logger = setup_logging()

logger.info("=" * 60)
logger.info("🚀 Iniciando market_platform_unified backend")
logger.info("=" * 60)


# ══════════════════════════════════════════════
# LIFECYCLE — Startup / Shutdown
# ══════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager para startup e shutdown da aplicação.
    """
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

# Parse CORS origins — aceita file:// (origin "null") para dev local
cors_origins = [o.strip() for o in settings.cors_origins.split(",")]
cors_origins.append("null")  # file:// envia origin "null"
if "*" in cors_origins:
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info(f"✅ CORS habilitado para: {cors_origins}")


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


# Inclui routers da API
app.include_router(
    api_router,
    prefix=settings.api_prefix,
)


# ══════════════════════════════════════════════
# ROOT
# ══════════════════════════════════════════════

@app.get("/", tags=["root"])
def root():
    """
    Informações sobre a API.
    """
    return {
        "name": "Market Platform Unified",
        "version": "1.0.0",
        "description": "API unificada de dados financeiros",
        "docs": "/docs",
        "api_prefix": settings.api_prefix,
    }


# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn

    logger.info(f"🚀 Iniciando servidor em {settings.host}:{settings.port}")
    logger.info(f"📖 Docs disponível em http://{settings.host}:{settings.port}/docs")

    uvicorn.run(
        "backend.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )
