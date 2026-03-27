"""
Endpoints: /api/market/summary, /api/market/sectors, /api/market/countries
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.api.models import (
    CountriesResponse,
    CountryItem,
    IndexItem,
    MarketSummaryResponse,
    SectorItem,
    SectorsResponse,
)
from backend.data.sectors_gics import COUNTRIES, TICKER_SECTOR_MAP, get_sector_name
from backend.db.connection import get_db
from backend.db.schema import Asset, PriceDaily

router = APIRouter(prefix="/market", tags=["Market"])


@router.get("/summary", response_model=MarketSummaryResponse)
def market_summary(db: Session = Depends(get_db)):
    """Resumo de mercado: últimos preços dos principais índices."""

    # Subquery: última data por asset
    latest_sq = (
        select(
            PriceDaily.asset_id,
            func.max(PriceDaily.date).label("max_date"),
        )
        .group_by(PriceDaily.asset_id)
        .subquery()
    )

    rows = db.execute(
        select(
            Asset.symbol,
            Asset.name,
            PriceDaily.close,
            PriceDaily.change_pct,
            PriceDaily.date,
        )
        .join(PriceDaily, PriceDaily.asset_id == Asset.id)
        .join(
            latest_sq,
            (PriceDaily.asset_id == latest_sq.c.asset_id)
            & (PriceDaily.date == latest_sq.c.max_date),
        )
        .where(Asset.asset_type == "index")
        .order_by(Asset.symbol)
    ).fetchall()

    as_of = rows[0][4] if rows else None

    return MarketSummaryResponse(
        as_of=as_of,
        indices=[
            IndexItem(
                symbol=r[0],
                name=r[1],
                close=r[2],
                change_pct=r[3],
                date=r[4],
            )
            for r in rows
        ],
    )


@router.get("/sectors", response_model=SectorsResponse)
def sector_performance(
    period: str = Query("30d", description="Período de análise"),
    db: Session = Depends(get_db),
):
    """Performance média por setor GICS (baseado em change_pct dos últimos N dias)."""
    from backend.api.prices import _parse_period

    start_date = _parse_period(period)

    # Buscar todos os assets com preço e setor mapeado
    rows = db.execute(
        select(Asset.symbol, func.avg(PriceDaily.change_pct))
        .join(PriceDaily, PriceDaily.asset_id == Asset.id)
        .where(
            Asset.asset_type == "stock",
            PriceDaily.date >= start_date,
            PriceDaily.change_pct.isnot(None),
        )
        .group_by(Asset.symbol)
    ).fetchall()

    # Agrupar por setor
    sector_data = {}
    for symbol, avg_change in rows:
        gics_code = TICKER_SECTOR_MAP.get(symbol)
        if gics_code is None:
            continue
        sector_name = get_sector_name(gics_code)
        if sector_name not in sector_data:
            sector_data[sector_name] = {"total": 0, "count": 0}
        if avg_change is not None:
            sector_data[sector_name]["total"] += float(avg_change)
            sector_data[sector_name]["count"] += 1

    sectors = []
    for name, data in sorted(sector_data.items()):
        avg = data["total"] / data["count"] if data["count"] > 0 else 0
        sectors.append(
            SectorItem(
                sector=name,
                count=data["count"],
                avg_return_pct=round(avg, 4),
            )
        )

    return SectorsResponse(
        period=period,
        as_of=date.today(),
        sectors=sectors,
    )


@router.get("/countries", response_model=CountriesResponse)
def list_countries(db: Session = Depends(get_db)):
    """Lista países com contagem de assets."""
    rows = db.execute(
        select(Asset.country, func.count(Asset.id))
        .where(Asset.is_active == True, Asset.country.isnot(None))
        .group_by(Asset.country)
        .order_by(func.count(Asset.id).desc())
    ).fetchall()

    countries = []
    for code, count in rows:
        info = COUNTRIES.get(code, {})
        countries.append(
            CountryItem(
                code=code,
                name=info.get("name", code),
                asset_count=count,
                currency=info.get("currency"),
            )
        )

    return CountriesResponse(
        total_countries=len(countries),
        countries=countries,
    )
