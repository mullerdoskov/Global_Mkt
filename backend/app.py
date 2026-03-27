"""
FastAPI principal — Market Platform Unified v2.0
Lifespan, CORS, error handlers, health check.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from sqlalchemy import func, select, text

from backend.api.models import HealthResponse
from backend.api.router import api_router
from backend.config.logging_config import logger
from backend.config.settings import settings
from backend.db.connection import engine, init_db, check_connection
from backend.db.schema import Asset, PriceDaily


# ══════════════════════════════════════════════════════════
#  LIFESPAN
# ══════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: verifica DB e cria tabelas. Shutdown: cleanup."""
    logger.info("=" * 60)
    logger.info("Market Platform Unified v2.0 — Iniciando...")
    logger.info("=" * 60)

    # Verificar conexão
    db_status = check_connection()
    if db_status["status"] == "ok":
        logger.info(f"Banco conectado: {db_status['url']}")
    else:
        logger.error(f"ERRO de conexão: {db_status.get('error')}")

    # Criar tabelas
    init_db()
    logger.info("Tabelas verificadas/criadas com sucesso")

    # Contagem rápida
    try:
        with engine.connect() as conn:
            assets_count = conn.execute(text("SELECT COUNT(*) FROM assets")).scalar() or 0
            prices_count = conn.execute(text("SELECT COUNT(*) FROM prices_daily")).scalar() or 0
            logger.info(f"Assets: {assets_count} | Preços: {prices_count}")
    except Exception:
        logger.info("Banco vazio (primeira execução)")

    logger.info("Servidor pronto!")
    logger.info("=" * 60)

    yield  # App running

    logger.info("Servidor encerrando...")


# ══════════════════════════════════════════════════════════
#  APP
# ══════════════════════════════════════════════════════════

app = FastAPI(
    title="Market Platform Unified",
    description="API de dados de mercado financeiro — Inteligência de Mercado",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router principal
app.include_router(api_router)


# ══════════════════════════════════════════════════════════
#  ERROR HANDLERS (fix do bug original — usa JSONResponse)
# ══════════════════════════════════════════════════════════

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handler genérico que retorna JSONResponse (não HTTPException para evitar loop)."""
    logger.error(f"Erro não tratado em {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "path": str(request.url)},
    )


# ══════════════════════════════════════════════════════════
#  HEALTH CHECK
# ══════════════════════════════════════════════════════════

@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Verifica saúde do sistema."""
    db_status = check_connection()

    assets_count = 0
    prices_count = 0
    try:
        with engine.connect() as conn:
            assets_count = conn.execute(text("SELECT COUNT(*) FROM assets")).scalar() or 0
            prices_count = conn.execute(text("SELECT COUNT(*) FROM prices_daily")).scalar() or 0
    except Exception:
        pass

    return HealthResponse(
        status="ok" if db_status["status"] == "ok" else "degraded",
        db=db_status["status"],
        assets_count=assets_count,
        prices_count=prices_count,
    )
