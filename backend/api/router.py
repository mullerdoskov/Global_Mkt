"""
Agregador de sub-routers da API.
"""

from fastapi import APIRouter

from backend.api.assets import router as assets_router
from backend.api.prices import router as prices_router
from backend.api.market import router as market_router
from backend.api.fundamentals import router as fundamentals_router
from backend.api.ingestion import router as ingestion_router

api_router = APIRouter(prefix="/api")

api_router.include_router(assets_router)
api_router.include_router(prices_router)
api_router.include_router(market_router)
api_router.include_router(fundamentals_router)
api_router.include_router(ingestion_router)
