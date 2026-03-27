"""
Pipeline de ingestão de preços: yfinance → PostgreSQL (upsert).
Usa batch download (yf.download) para evitar rate-limit.
"""

from datetime import date, datetime
from typing import List, Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config.logging_config import logger
from backend.config.settings import settings
from backend.config.symbols import ALL_SYMBOLS, get_symbols
from backend.db.connection import get_session
from backend.db.schema import Asset, AssetType, IngestionLog, IngestionStatus, PriceDaily
from backend.ingestion.yf_client import yf_client


def ensure_assets_exist(session: Session, symbols: list[tuple] | None = None):
    """
    Garante que todos os símbolos existam na tabela assets.
    Cria os que não existem ainda.
    """
    if symbols is None:
        symbols = ALL_SYMBOLS

    existing = {
        row[0]
        for row in session.execute(select(Asset.symbol)).fetchall()
    }

    new_assets = []
    for sym, name, atype, country in symbols:
        if sym not in existing:
            new_assets.append(
                Asset(
                    symbol=sym,
                    name=name,
                    asset_type=AssetType(atype),
                    country=country,
                    is_active=True,
                )
            )

    if new_assets:
        session.add_all(new_assets)
        session.flush()
        logger.info(f"Criados {len(new_assets)} novos assets no banco")

    return len(new_assets)


def _upsert_prices(session: Session, asset_id: int, df: pd.DataFrame) -> tuple[int, int]:
    """
    Upsert de preços: insere novos, atualiza existentes.
    Retorna (inserted, updated).
    """
    if df.empty:
        return 0, 0

    inserted = 0
    updated = 0

    for _, row in df.iterrows():
        row_date = row["Date"]
        if isinstance(row_date, pd.Timestamp):
            row_date = row_date.date()

        # Calcular change_pct
        change_pct = None
        if pd.notna(row.get("Close")) and pd.notna(row.get("Open")) and row["Open"] != 0:
            change_pct = ((row["Close"] - row["Open"]) / row["Open"]) * 100

        existing = session.execute(
            select(PriceDaily).where(
                PriceDaily.asset_id == asset_id,
                PriceDaily.date == row_date,
            )
        ).scalar_one_or_none()

        if existing:
            existing.open = float(row["Open"]) if pd.notna(row["Open"]) else None
            existing.high = float(row["High"]) if pd.notna(row["High"]) else None
            existing.low = float(row["Low"]) if pd.notna(row["Low"]) else None
            existing.close = float(row["Close"]) if pd.notna(row["Close"]) else None
            existing.adj_close = float(row["Adj Close"]) if pd.notna(row.get("Adj Close")) else None
            existing.volume = float(row["Volume"]) if pd.notna(row["Volume"]) else None
            existing.change_pct = change_pct
            updated += 1
        else:
            price = PriceDaily(
                asset_id=asset_id,
                date=row_date,
                open=float(row["Open"]) if pd.notna(row["Open"]) else None,
                high=float(row["High"]) if pd.notna(row["High"]) else None,
                low=float(row["Low"]) if pd.notna(row["Low"]) else None,
                close=float(row["Close"]) if pd.notna(row["Close"]) else None,
                adj_close=float(row["Adj Close"]) if pd.notna(row.get("Adj Close")) else None,
                volume=float(row["Volume"]) if pd.notna(row["Volume"]) else None,
                change_pct=change_pct,
            )
            session.add(price)
            inserted += 1

    session.flush()
    return inserted, updated


def ingest_prices(
    symbols: list[tuple] | None = None,
    start: str | date | None = None,
    end: str | date | None = None,
    period: str = "1y",
    asset_type: str | None = None,
    country: str | None = None,
) -> dict:
    """
    Pipeline principal de ingestão de preços.
    Usa BATCH download em lotes para evitar rate-limit.

    Args:
        symbols: Lista de (symbol, name, type, country). Se None, usa filtros.
        start: Data inicial (YYYY-MM-DD)
        end: Data final (YYYY-MM-DD)
        period: Período se start/end não fornecidos (1y, 6mo, etc)
        asset_type: Filtrar por tipo (stock, index, etc)
        country: Filtrar por país (BR, US, etc)

    Returns:
        Dict com estatísticas da ingestão.
    """
    if symbols is None:
        symbols = get_symbols(asset_type=asset_type, country=country)

    total = len(symbols)
    success_count = 0
    error_count = 0
    total_inserted = 0
    total_updated = 0
    errors = []

    logger.info(f"Iniciando ingestão de preços: {total} símbolos")
    if start:
        logger.info(f"  Range: {start} → {end or 'hoje'}")
    else:
        logger.info(f"  Período: {period}")

    # Tamanho do batch — agrupa símbolos para baixar juntos
    batch_size = settings.INGEST_BATCH_SIZE

    with get_session() as session:
        # Garantir que assets existam
        ensure_assets_exist(session, symbols)
        session.commit()

        # Mapa symbol → asset_id
        asset_ids = {}
        for sym, name, atype, cty in symbols:
            aid = session.execute(select(Asset.id).where(Asset.symbol == sym)).scalar_one_or_none()
            if aid:
                asset_ids[sym] = aid

        # Processar em batches
        for batch_start in range(0, total, batch_size):
            batch = symbols[batch_start : batch_start + batch_size]
            batch_syms = [s[0] for s in batch]
            batch_num = (batch_start // batch_size) + 1
            total_batches = (total + batch_size - 1) // batch_size

            logger.info(f"━━ Batch {batch_num}/{total_batches}: {len(batch_syms)} símbolos ━━")
            logger.info(f"   {', '.join(batch_syms[:5])}{'...' if len(batch_syms) > 5 else ''}")

            # Batch download
            batch_data = yf_client.fetch_prices_batch(
                symbols=batch_syms,
                start=start,
                end=end,
                period=period,
            )

            # Processar cada símbolo do batch
            for sym, name, atype, cty in batch:
                asset_id = asset_ids.get(sym)
                if not asset_id:
                    continue

                log_entry = IngestionLog(
                    asset_id=asset_id,
                    status=IngestionStatus.success,
                    data_type="prices",
                )

                try:
                    df = batch_data.get(sym, pd.DataFrame())

                    if df.empty:
                        # Fallback: tentar download individual
                        logger.info(f"  [{sym}] Sem dados no batch, tentando individual...")
                        df = yf_client.fetch_prices(symbol=sym, start=start, end=end, period=period)

                    if df.empty:
                        log_entry.status = IngestionStatus.partial
                        log_entry.error_message = "Sem dados retornados"
                        error_count += 1
                        errors.append({"symbol": sym, "error": "Sem dados"})
                        logger.warning(f"  [{sym}] Sem dados")
                    else:
                        ins, upd = _upsert_prices(session, asset_id, df)
                        log_entry.rows_inserted = ins
                        log_entry.rows_updated = upd
                        total_inserted += ins
                        total_updated += upd
                        success_count += 1
                        logger.info(f"  [{sym}] {ins} inseridos, {upd} atualizados")

                except Exception as e:
                    log_entry.status = IngestionStatus.error
                    log_entry.error_message = str(e)[:500]
                    error_count += 1
                    errors.append({"symbol": sym, "error": str(e)[:200]})
                    logger.error(f"  [{sym}] ERRO: {e}")

                log_entry.finished_at = datetime.utcnow()
                session.add(log_entry)

            # Commit por batch (não por símbolo — mais eficiente)
            session.commit()
            logger.info(f"━━ Batch {batch_num} concluído ━━\n")

    result = {
        "total_symbols": total,
        "success": success_count,
        "errors": error_count,
        "rows_inserted": total_inserted,
        "rows_updated": total_updated,
        "error_details": errors[:20],
    }

    logger.info(
        f"Ingestão concluída: {success_count}/{total} OK, "
        f"{total_inserted} inseridos, {total_updated} atualizados"
    )

    return result
