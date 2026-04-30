"""
api/prices.py
Endpoints de preços históricos e retornos.
"""

from typing import Optional
from datetime import date, timedelta
from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import select
import pandas as pd

from backend.db.connection import get_session
from backend.db.schema import Asset, PriceDaily
from backend.api.models import PriceHistoryResponse, PriceBar, ReturnsResponse, ReturnData, LatestPricesResponse, LatestPrice

router = APIRouter(prefix="/prices", tags=["prices"])


def _parse_period(period: str) -> int:
    """
    Converte período (ex: '90d', '1y') para dias.

    Formatos suportados:
    - '30d' = 30 dias
    - '1y' ou '12m' = 365 dias
    """
    if period.endswith("d"):
        return int(period[:-1])
    elif period.endswith("m"):
        months = int(period[:-1])
        return months * 30
    elif period.endswith("y"):
        years = int(period[:-1])
        return years * 365
    else:
        return 90  # Default


@router.get("/{symbol}/history", response_model=PriceHistoryResponse)
def get_price_history(
    symbol: str,
    period: str = Query("90d", description="Período: 30d, 1y, etc."),
    interval: str = Query("1d", description="Intervalo: 1d (diário), não suportado intraday no momento"),
) -> PriceHistoryResponse:
    """
    Retorna série histórica OHLCV de um ativo.

    Parâmetros:
    - symbol: Símbolo do ativo (ex: PETR3.SA, AAPL)
    - period: Período de dados (default: 90d). Formatos: 30d, 1y, 6m, etc.
    - interval: Intervalo (default: 1d para diário)
    """
    session = get_session()
    try:
        # Busca o ativo
        asset = session.execute(
            select(Asset).where(Asset.symbol == symbol)
        ).scalar_one_or_none()

        if not asset:
            raise HTTPException(status_code=404, detail=f"Asset '{symbol}' not found")

        # Calcula data inicial
        days = _parse_period(period)
        start_date = date.today() - timedelta(days=days)

        # Busca preços
        prices_query = select(PriceDaily).where(
            (PriceDaily.asset_id == asset.id) &
            (PriceDaily.date >= start_date)
        ).order_by(PriceDaily.date)

        price_rows = session.execute(prices_query).scalars().all()

        price_bars = [
            PriceBar(
                date=p.date,
                open=float(p.open) if p.open else None,
                high=float(p.high) if p.high else None,
                low=float(p.low) if p.low else None,
                close=float(p.close) if p.close else None,
                adj_close=float(p.adj_close) if p.adj_close else None,
                volume=p.volume,
            )
            for p in price_rows
        ]

        return PriceHistoryResponse(
            symbol=symbol,
            period=period,
            interval=interval,
            count=len(price_bars),
            prices=price_bars,
        )

    finally:
        session.close()


@router.get("/{symbol}/returns", response_model=ReturnsResponse)
def get_returns(
    symbol: str,
    period: str = Query("90d", description="Período: 30d, 1y, etc."),
) -> ReturnsResponse:
    """
    Calcula retorno diário e acumulado de um ativo.

    Retorna:
    - daily_return: retorno do dia anterior
    - cumulative_return: retorno acumulado desde o início do período
    """
    session = get_session()
    try:
        # Busca o ativo
        asset = session.execute(
            select(Asset).where(Asset.symbol == symbol)
        ).scalar_one_or_none()

        if not asset:
            raise HTTPException(status_code=404, detail=f"Asset '{symbol}' not found")

        # Calcula data inicial
        days = _parse_period(period)
        start_date = date.today() - timedelta(days=days)

        # Busca preços
        prices_query = select(PriceDaily).where(
            (PriceDaily.asset_id == asset.id) &
            (PriceDaily.date >= start_date)
        ).order_by(PriceDaily.date)

        price_rows = session.execute(prices_query).scalars().all()

        if not price_rows:
            return ReturnsResponse(symbol=symbol, period=period, count=0, returns=[])

        # Calcula retornos com pandas
        df = pd.DataFrame([
            {"date": p.date, "close": float(p.close) if p.close else None}
            for p in price_rows
        ])

        df = df.dropna(subset=["close"])
        df["daily_return"] = df["close"].pct_change() * 100  # em percentual

        # Retorno acumulado: (fechamento atual / fechamento inicial - 1) * 100
        if len(df) > 0:
            first_close = df.iloc[0]["close"]
            df["cumulative_return"] = ((df["close"] / first_close) - 1) * 100
        else:
            df["cumulative_return"] = None

        returns = [
            ReturnData(
                date=row["date"],
                daily_return=float(row["daily_return"]) if pd.notna(row["daily_return"]) else None,
                cumulative_return=float(row["cumulative_return"]) if pd.notna(row["cumulative_return"]) else None,
            )
            for _, row in df.iterrows()
        ]

        return ReturnsResponse(
            symbol=symbol,
            period=period,
            count=len(returns),
            returns=returns,
        )

    finally:
        session.close()


@router.get("/debug")
def debug_prices():
    """Endpoint de debug — mostra contagens e amostra de dados."""
    from sqlalchemy import text as sql_text
    session = get_session()
    try:
        assets_count = session.execute(sql_text("SELECT COUNT(*) FROM assets")).scalar()
        prices_count = session.execute(sql_text("SELECT COUNT(*) FROM prices_daily")).scalar()
        sample = session.execute(sql_text("""
            SELECT a.symbol, a.name, a.asset_type::text, p.close, p.date
            FROM assets a
            JOIN prices_daily p ON p.asset_id = a.id
            ORDER BY p.date DESC
            LIMIT 5
        """)).fetchall()
        return {
            "assets_count": assets_count,
            "prices_count": prices_count,
            "sample": [
                {"symbol": r[0], "name": r[1], "type": r[2], "close": float(r[3]) if r[3] else None, "date": str(r[4])}
                for r in sample
            ]
        }
    finally:
        session.close()


@router.get("", response_model=LatestPricesResponse)
def get_latest_prices(
    asset_type: Optional[str] = Query(None, description="Filtra por tipo: stock, index, etc."),
    page: int = Query(1, ge=1, description="Página (começa em 1)"),
    page_size: int = Query(50, ge=1, le=100, description="Itens por página (máx 100)"),
) -> LatestPricesResponse:
    """
    Retorna snapshot com últimos preços de todos (ou filtrados) ativos.
    Usa DISTINCT ON (PostgreSQL-native) para obter o preço mais recente por ativo.
    """
    from sqlalchemy import text as sql_text
    import logging
    logger = logging.getLogger("market_platform")

    type_clause = "AND a.asset_type::text = :asset_type" if asset_type else ""
    offset = (page - 1) * page_size
    row_params: dict = {"page_size": page_size, "offset": offset}
    count_params: dict = {}
    if asset_type:
        row_params["asset_type"] = asset_type
        count_params["asset_type"] = asset_type

    count_sql = f"""
        SELECT COUNT(DISTINCT a.id)
        FROM assets a
        JOIN prices_daily p ON p.asset_id = a.id
        WHERE 1=1 {type_clause}
    """
    rows_sql = f"""
        SELECT DISTINCT ON (a.id)
            a.symbol, a.name, a.asset_type::text, p.close, p.date
        FROM assets a
        JOIN prices_daily p ON p.asset_id = a.id
        WHERE 1=1 {type_clause}
        ORDER BY a.id, p.date DESC
        LIMIT :page_size OFFSET :offset
    """

    session = get_session()
    try:
        logger.info("Executando query latest_prices, asset_type=%s page=%s page_size=%s", asset_type, page, page_size)
        total = session.execute(sql_text(count_sql), count_params).scalar() or 0
        rows = session.execute(sql_text(rows_sql), row_params).fetchall()
        logger.info("Query retornou %d rows (total=%d)", len(rows), total)

        latest_prices = [
            LatestPrice(
                symbol=row[0],
                name=row[1] or row[0],
                close=float(row[3]),
                price_date=row[4],
                change_pct=None,
            )
            for row in rows
            if row[3] is not None
        ]

        return LatestPricesResponse(
            as_of=date.today(),
            total=total,
            page=page,
            page_size=page_size,
            prices=latest_prices,
        )

    finally:
        session.close()
