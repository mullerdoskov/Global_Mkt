"""
ingestion/loader.py
Download → normalização → upsert de preços OHLCV no banco.
"""

import time
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy import select, text

from backend.db.connection import get_session, IS_SQLITE
from backend.db.schema import (
    Asset, AssetType, Company, Country, PriceDaily,
    IngestionLog, IngestionStatus
)

if not IS_SQLITE:
    from sqlalchemy.dialects.postgresql import insert as pg_insert
from backend.config.symbols import SYMBOLS_BY_TYPE, get_country_for_symbol, ALL_STOCKS
from backend.data.sectors_gics import TICKER_SECTOR_MAP
from backend.ingestion.yf_client import YFinanceClient, BATCH_SIZE

logger = logging.getLogger("market_platform")


def _safe_float(val):
    """Converte valor para float, tratando NaN."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val):
    """Converte valor para int, tratando NaN."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def ensure_asset_exists(session, symbol: str, asset_type: str, client: YFinanceClient = None) -> int:
    """
    Garante que o ativo existe na tabela assets. Cria company se for stock.
    Retorna o asset_id.
    """
    # Verifica se já existe
    asset = session.execute(
        select(Asset).where(Asset.symbol == symbol)
    ).scalar_one_or_none()

    if asset:
        return asset.id

    company_id = None
    name = symbol
    currency = "USD"
    exchange = None

    # Se for ação, busca info e cria company
    if asset_type == "stock" and client:
        try:
            info = client.get_info(symbol)
            name = info.get("longName") or info.get("shortName") or symbol
            currency = info.get("currency", "USD")
            exchange = info.get("exchange")
            market_cap = info.get("marketCap")
            employees = info.get("fullTimeEmployees")

            # Busca país
            country_iso = get_country_for_symbol(symbol)
            country = session.execute(
                select(Country).where(Country.iso2 == country_iso)
            ).scalar_one_or_none()

            # Busca setor GICS
            gics_code = TICKER_SECTOR_MAP.get(symbol)
            sector_id = None
            if gics_code:
                from db.schema import SectorGICS
                sector = session.execute(
                    select(SectorGICS).where(SectorGICS.gics_code == gics_code)
                ).first()
                if sector:
                    sector_id = sector[0].id

            # Cria company
            company = Company(
                ticker=symbol,
                name=name,
                country_id=country.id if country else None,
                sector_gics_id=sector_id,
                exchange=exchange,
                currency=currency,
                market_cap=market_cap,
                employees=employees,
            )
            session.add(company)
            session.flush()
            company_id = company.id
            logger.info(f"🏢 Company criada: {symbol} — {name}")

        except Exception as e:
            logger.warning(f"⚠️  Não foi possível criar company para {symbol}: {e}")

    # Cria asset
    asset = Asset(
        symbol=symbol,
        asset_type=AssetType(asset_type),
        company_id=company_id,
        name=name,
        currency=currency,
        exchange=exchange,
    )
    session.add(asset)
    session.flush()
    logger.info(f"📦 Asset criado: {symbol} ({asset_type})")
    return asset.id


def upsert_prices(session, asset_id: int, df: pd.DataFrame) -> int:
    """
    Faz upsert de preços OHLCV no banco.
    Retorna número de linhas inseridas/atualizadas.
    """
    if df is None or df.empty:
        return 0

    rows = []
    for idx, row in df.iterrows():
        # idx pode ser DatetimeIndex
        dt = idx.date() if hasattr(idx, 'date') else idx

        rows.append({
            "asset_id": asset_id,
            "date": dt,
            "open": _safe_float(row.get("Open")),
            "high": _safe_float(row.get("High")),
            "low": _safe_float(row.get("Low")),
            "close": _safe_float(row.get("Close")),
            "adj_close": _safe_float(row.get("Adj Close")),
            "volume": _safe_int(row.get("Volume")),
        })

    if not rows:
        return 0

    if IS_SQLITE:
        # SQLite: INSERT OR REPLACE
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        stmt = sqlite_insert(PriceDaily).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["asset_id", "date"],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "adj_close": stmt.excluded.adj_close,
                "volume": stmt.excluded.volume,
            }
        )
    else:
        # PostgreSQL: ON CONFLICT com constraint nomeada
        stmt = pg_insert(PriceDaily).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_prices_asset_date",
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "adj_close": stmt.excluded.adj_close,
                "volume": stmt.excluded.volume,
            }
        )
    session.execute(stmt)
    session.commit()
    return len(rows)


def log_ingestion(session, symbol: str, ingestion_type: str,
                  rows: int, status: IngestionStatus,
                  error_msg: str = None, duration: float = None):
    """Registra resultado da ingestão no log."""
    entry = IngestionLog(
        symbol=symbol,
        ingestion_type=ingestion_type,
        rows_inserted=rows,
        status=status,
        error_message=error_msg,
        duration_seconds=duration,
        finished_at=datetime.utcnow() if status != IngestionStatus.partial else None,
    )
    session.add(entry)
    session.commit()


def ingest_prices(period: str = "90d", asset_types: list[str] = None):
    """
    Pipeline principal de ingestão de preços OHLCV.

    Args:
        period: Período de dados (default: 90 dias).
        asset_types: Lista de tipos para ingerir. None = todos.
    """
    client = YFinanceClient()

    if asset_types is None:
        asset_types = list(SYMBOLS_BY_TYPE.keys())

    total_success = 0
    total_errors = 0

    for asset_type in asset_types:
        symbols = SYMBOLS_BY_TYPE.get(asset_type, [])
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 Ingestão: {asset_type.upper()} — {len(symbols)} tickers")
        logger.info(f"{'='*60}")

        for i in range(0, len(symbols), BATCH_SIZE):
            batch = symbols[i:i + BATCH_SIZE]
            logger.info(f"📦 Batch {i // BATCH_SIZE + 1}: {batch}")

            for symbol in batch:
                start_time = time.time()
                session = get_session()

                try:
                    # Garantir que o ativo existe
                    asset_id = ensure_asset_exists(session, symbol, asset_type, client)

                    # Baixar preços
                    df = client.download_prices(symbol, period=period)
                    if df is not None and not df.empty:
                        rows = upsert_prices(session, asset_id, df)
                        duration = time.time() - start_time
                        log_ingestion(session, symbol, "prices", rows,
                                      IngestionStatus.success, duration=duration)
                        total_success += 1
                        logger.info(f"✅ {symbol}: {rows} preços — {duration:.1f}s")
                    else:
                        log_ingestion(session, symbol, "prices", 0,
                                      IngestionStatus.error, "Sem dados retornados")
                        total_errors += 1

                except Exception as e:
                    duration = time.time() - start_time
                    log_ingestion(session, symbol, "prices", 0,
                                  IngestionStatus.error, str(e)[:500], duration)
                    total_errors += 1
                    logger.error(f"❌ {symbol}: {e}")
                finally:
                    session.close()

            # Pausa entre batches
            if i + BATCH_SIZE < len(symbols):
                client.sleep_between_batches()

        # Pausa entre tipos de ativo
        if asset_type != asset_types[-1]:
            client.sleep_between_types()

    logger.info(f"\n{'='*60}")
    logger.info(f"📊 RESUMO: {total_success} sucesso, {total_errors} erros")
    logger.info(f"{'='*60}")
    return total_success, total_errors


def update_prices(lookback_days: int = 5):
    """Atualização incremental — últimos N dias."""
    logger.info(f"🔄 Atualização incremental: últimos {lookback_days} dias")
    return ingest_prices(period=f"{lookback_days}d")
