"""
Endpoints: /api/prices, /api/prices/{sym}/history, /api/prices/{sym}/returns, /api/prices/debug
Fix do bug original: usa DISTINCT ON (PostgreSQL) ou subquery otimizada.
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import distinct, func, select, text
from sqlalchemy.orm import Session

from backend.api.models import (
    LatestPricesResponse,
    OHLCVItem,
    PriceHistoryResponse,
    PriceItem,
    ReturnItem,
    ReturnsResponse,
)
from backend.db.connection import get_db
from backend.db.schema import Asset, PriceDaily

router = APIRouter(prefix="/prices", tags=["Prices"])


def _parse_period(period: str) -> date:
    """Converte string de período em data inicial."""
    today = date.today()
    period = period.lower().strip()
    mapping = {
        "7d": 7, "1w": 7,
        "30d": 30, "1m": 30, "1mo": 30,
        "90d": 90, "3m": 90, "3mo": 90,
        "180d": 180, "6m": 180, "6mo": 180,
        "365d": 365, "1y": 365,
        "730d": 730, "2y": 730,
        "1825d": 1825, "5y": 1825,
    }
    days = mapping.get(period, 90)
    return today - timedelta(days=days)


@router.get("/debug")
def prices_debug(db: Session = Depends(get_db)):
    """Endpoint de debug: contagens e amostra de dados."""
    total_assets = db.execute(select(func.count(Asset.id))).scalar() or 0
    total_prices = db.execute(select(func.count(PriceDaily.id))).scalar() or 0

    sample = db.execute(
        select(Asset.symbol, PriceDaily.date, PriceDaily.close)
        .join(PriceDaily, PriceDaily.asset_id == Asset.id)
        .order_by(PriceDaily.date.desc())
        .limit(5)
    ).fetchall()

    return {
        "total_assets": total_assets,
        "total_prices": total_prices,
        "sample": [
            {"symbol": row[0], "date": str(row[1]), "close": row[2]}
            for row in sample
        ],
    }


@router.get("", response_model=LatestPricesResponse)
def latest_prices(
    asset_type: str | None = Query(None),
    country: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    Último preço de cada asset.
    FIX: usa subquery com MAX(date) agrupado, evitando subquery correlacionada.
    """
    # Subquery: última data por asset
    latest_date_sq = (
        select(
            PriceDaily.asset_id,
            func.max(PriceDaily.date).label("max_date"),
        )
        .group_by(PriceDaily.asset_id)
        .subquery()
    )

    # Query principal: join assets + prices + latest_date
    query = (
        select(
            Asset.symbol,
            Asset.name,
            Asset.asset_type,
            PriceDaily.close,
            PriceDaily.change_pct,
            PriceDaily.date,
            PriceDaily.volume,
        )
        .join(PriceDaily, PriceDaily.asset_id == Asset.id)
        .join(
            latest_date_sq,
            (PriceDaily.asset_id == latest_date_sq.c.asset_id)
            & (PriceDaily.date == latest_date_sq.c.max_date),
        )
        .where(Asset.is_active == True)
    )

    if asset_type:
        query = query.where(Asset.asset_type == asset_type)
    if country:
        query = query.where(Asset.country == country.upper())

    query = query.order_by(Asset.symbol)

    # Paginação
    offset = (page - 1) * page_size
    rows = db.execute(query.offset(offset).limit(page_size)).fetchall()

    # Data de referência
    as_of = rows[0][5] if rows else None

    prices = [
        PriceItem(
            symbol=row[0],
            name=row[1],
            asset_type=row[2].value if hasattr(row[2], "value") else str(row[2]),
            close=row[3],
            change_pct=row[4],
            date=row[5],
            volume=row[6],
        )
        for row in rows
    ]

    return LatestPricesResponse(
        as_of=as_of,
        count=len(prices),
        prices=prices,
    )


@router.get("/{symbol}/history", response_model=PriceHistoryResponse)
def price_history(
    symbol: str,
    period: str = Query("90d", description="7d, 30d, 90d, 180d, 365d"),
    db: Session = Depends(get_db),
):
    """Histórico de preços OHLCV para um símbolo."""
    asset = db.execute(
        select(Asset).where(Asset.symbol == symbol)
    ).scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset '{symbol}' não encontrado")

    start_date = _parse_period(period)

    prices = db.execute(
        select(PriceDaily)
        .where(PriceDaily.asset_id == asset.id, PriceDaily.date >= start_date)
        .order_by(PriceDaily.date)
    ).scalars().all()

    return PriceHistoryResponse(
        symbol=symbol,
        period=period,
        count=len(prices),
        prices=[
            OHLCVItem(
                date=p.date,
                open=p.open,
                high=p.high,
                low=p.low,
                close=p.close,
                adj_close=p.adj_close,
                volume=p.volume,
                change_pct=p.change_pct,
            )
            for p in prices
        ],
    )


@router.get("/{symbol}/returns", response_model=ReturnsResponse)
def price_returns(
    symbol: str,
    period: str = Query("90d"),
    db: Session = Depends(get_db),
):
    """Retornos diários e acumulados de um símbolo."""
    asset = db.execute(
        select(Asset).where(Asset.symbol == symbol)
    ).scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset '{symbol}' não encontrado")

    start_date = _parse_period(period)

    prices = db.execute(
        select(PriceDaily)
        .where(PriceDaily.asset_id == asset.id, PriceDaily.date >= start_date)
        .order_by(PriceDaily.date)
    ).scalars().all()

    if not prices:
        return ReturnsResponse(symbol=symbol, period=period, count=0, returns=[])

    # Calcular retorno acumulado
    base_close = prices[0].close if prices[0].close else 1
    returns = []
    for p in prices:
        cum_return = ((p.close / base_close) - 1) * 100 if p.close and base_close else None
        returns.append(
            ReturnItem(
                date=p.date,
                close=p.close,
                change_pct=p.change_pct,
                cumulative_return=round(cum_return, 4) if cum_return is not None else None,
            )
        )

    return ReturnsResponse(
        symbol=symbol,
        period=period,
        count=len(returns),
        returns=returns,
    )
