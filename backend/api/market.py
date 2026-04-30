"""
api/market.py
Endpoints de mercado: índices, setores, países.
"""

from datetime import date, timedelta
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select, func
import pandas as pd

from backend.config.settings import settings
from backend.db.connection import get_session
from backend.db.schema import Asset, PriceDaily, Company, SectorGICS, Country
from backend.config.symbols import INDICES
from backend.api.models import (
    MarketSummaryResponse, IndexSnapshot,
    SectorsResponse, SectorPerformance,
    CountriesResponse, CountryAssets
)
from backend.api._limiter import limiter

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/summary", response_model=MarketSummaryResponse)
@limiter.limit(settings.rate_limit_default)
def get_market_summary(request: Request) -> MarketSummaryResponse:
    """
    Retorna resumo dos 16 índices globais com últimos preços.

    Inclui: S&P 500, NASDAQ, Ibovespa, DAX, FTSE, etc.
    """
    session = get_session()
    try:
        indices_snapshot = []

        for index_symbol in INDICES:
            # Busca o ativo
            asset = session.execute(
                select(Asset).where(Asset.symbol == index_symbol)
            ).scalar_one_or_none()

            if not asset:
                # Tenta buscar mesmo assim, colocando None
                indices_snapshot.append(
                    IndexSnapshot(symbol=index_symbol, name=index_symbol, close=None, index_date=None, change_pct=None)
                )
                continue

            # Busca último preço
            latest_price_query = select(PriceDaily).where(
                PriceDaily.asset_id == asset.id
            ).order_by(PriceDaily.date.desc()).limit(1)

            price_row = session.execute(latest_price_query).scalar_one_or_none()

            if price_row and price_row.close:
                # Calcula mudança percentual
                prev_price_query = select(PriceDaily).where(
                    (PriceDaily.asset_id == asset.id) &
                    (PriceDaily.date < price_row.date)
                ).order_by(PriceDaily.date.desc()).limit(1)

                prev_price_row = session.execute(prev_price_query).scalar_one_or_none()
                change_pct = None

                if prev_price_row and prev_price_row.close:
                    change_pct = ((float(price_row.close) / float(prev_price_row.close)) - 1) * 100

                indices_snapshot.append(
                    IndexSnapshot(
                        symbol=index_symbol,
                        name=asset.name or index_symbol,
                        close=float(price_row.close),
                        index_date=price_row.date,
                        change_pct=change_pct,
                    )
                )
            else:
                indices_snapshot.append(
                    IndexSnapshot(symbol=index_symbol, name=asset.name or index_symbol, close=None, index_date=None)
                )

        return MarketSummaryResponse(
            as_of=date.today(),
            indices=indices_snapshot,
        )

    finally:
        session.close()


@router.get("/sectors", response_model=SectorsResponse)
@limiter.limit(settings.rate_limit_default)
def get_sectors_performance(request: Request, period: str = "90d") -> SectorsResponse:
    """
    Retorna performance por setor GICS (retorno médio por setor).

    Parâmetro:
    - period: Período para cálculo (90d por padrão)
    """
    session = get_session()
    try:
        # Calcula data inicial
        if period.endswith("d"):
            days = int(period[:-1])
        elif period.endswith("m"):
            days = int(period[:-1]) * 30
        elif period.endswith("y"):
            days = int(period[:-1]) * 365
        else:
            days = 90

        start_date = date.today() - timedelta(days=days)

        # Busca todos os setores
        sectors_query = select(SectorGICS).order_by(SectorGICS.sector)
        sectors = session.execute(sectors_query).scalars().all()

        sector_performances = []

        for sector in sectors:
            # Busca companies do setor
            companies_query = select(Company).where(Company.sector_gics_id == sector.id)
            companies = session.execute(companies_query).scalars().all()

            if not companies:
                continue

            # Busca preços de ativos dessas companies
            asset_ids = []
            for company in companies:
                assets_query = select(Asset).where(Asset.company_id == company.id)
                assets = session.execute(assets_query).scalars().all()
                asset_ids.extend([a.id for a in assets])

            if not asset_ids:
                continue

            # Calcula retorno médio do setor
            prices_query = select(PriceDaily).where(
                (PriceDaily.asset_id.in_(asset_ids)) &
                (PriceDaily.date >= start_date)
            ).order_by(PriceDaily.asset_id, PriceDaily.date)

            price_rows = session.execute(prices_query).scalars().all()

            if not price_rows:
                sector_performances.append(
                    SectorPerformance(
                        sector=sector.sector,
                        sector_pt=sector.sector_pt or sector.sector,
                        avg_return_pct=None,
                        asset_count=len(asset_ids),
                        period=period,
                    )
                )
                continue

            # Agrupa por asset e calcula retorno
            returns_by_asset = {}
            for price in price_rows:
                asset_id = price.asset_id
                if asset_id not in returns_by_asset:
                    returns_by_asset[asset_id] = []
                returns_by_asset[asset_id].append(float(price.close) if price.close else None)

            # Calcula retorno de cada ativo
            asset_returns = []
            for asset_id, closes in returns_by_asset.items():
                closes = [c for c in closes if c is not None]
                if len(closes) >= 2:
                    ret = ((closes[-1] / closes[0]) - 1) * 100
                    asset_returns.append(ret)

            # Média
            avg_return = sum(asset_returns) / len(asset_returns) if asset_returns else None

            sector_performances.append(
                SectorPerformance(
                    sector=sector.sector,
                    sector_pt=sector.sector_pt or sector.sector,
                    avg_return_pct=avg_return,
                    asset_count=len(asset_ids),
                    period=period,
                )
            )

        return SectorsResponse(
            period=period,
            as_of=date.today(),
            sectors=sector_performances,
        )

    finally:
        session.close()


@router.get("/countries", response_model=CountriesResponse)
@limiter.limit(settings.rate_limit_default)
def get_countries(request: Request) -> CountriesResponse:
    """
    Retorna lista de países com contagem de ativos.
    """
    session = get_session()
    try:
        # Busca todos os países
        countries_query = select(Country).order_by(Country.name)
        countries = session.execute(countries_query).scalars().all()

        country_assets_list = []

        for country in countries:
            # Conta ativos do país
            companies_query = select(Company).where(Company.country_id == country.id)
            companies = session.execute(companies_query).scalars().all()

            asset_count = 0
            for company in companies:
                assets_query = select(func.count()).select_from(Asset).where(Asset.company_id == company.id)
                count = session.execute(assets_query).scalar() or 0
                asset_count += count

            if asset_count > 0:
                country_assets_list.append(
                    CountryAssets(
                        country_iso2=country.iso2,
                        country_name=country.name,
                        asset_count=asset_count,
                    )
                )

        return CountriesResponse(
            total_countries=len(country_assets_list),
            countries=country_assets_list,
        )

    finally:
        session.close()
