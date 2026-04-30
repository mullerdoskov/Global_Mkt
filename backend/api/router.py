"""
api/router.py
Agregador de todos os routers da API.
"""

from fastapi import APIRouter

from backend.api import assets, prices, market, fundamentals, ingestion, export

# Router principal da API
api_router = APIRouter()

# Inclui todos os sub-routers
api_router.include_router(assets.router)
api_router.include_router(prices.router)
api_router.include_router(market.router)
api_router.include_router(fundamentals.router)
api_router.include_router(ingestion.router)
api_router.include_router(export.router)
