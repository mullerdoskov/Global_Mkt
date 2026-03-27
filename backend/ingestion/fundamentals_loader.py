"""
Ingestão de demonstrativos financeiros e múltiplos de valuation.
"""

from datetime import date, datetime

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config.logging_config import logger
from backend.config.symbols import get_symbols
from backend.db.connection import get_session
from backend.db.schema import (
    Asset,
    FinancialStatement,
    IngestionLog,
    IngestionStatus,
    PeriodType,
    ValuationMultiple,
)
from backend.ingestion.yf_client import yf_client


def _safe_float(val) -> float | None:
    """Converte para float de forma segura."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _ingest_financials_for_asset(session: Session, asset_id: int, symbol: str) -> int:
    """Ingere demonstrativos financeiros de um ativo. Retorna rows inseridas."""
    data = yf_client.fetch_financials(symbol)
    rows = 0

    income_stmt = data.get("income_stmt")
    balance_sheet = data.get("balance_sheet")
    cash_flow = data.get("cash_flow")

    if income_stmt is None or income_stmt.empty:
        return 0

    # Cada coluna = um período
    for col in income_stmt.columns:
        period_end = col.date() if hasattr(col, "date") else col

        # Verificar se já existe
        existing = session.execute(
            select(FinancialStatement).where(
                FinancialStatement.asset_id == asset_id,
                FinancialStatement.period_type == PeriodType.quarterly,
                FinancialStatement.period_end == period_end,
            )
        ).scalar_one_or_none()

        if existing:
            continue

        stmt = FinancialStatement(
            asset_id=asset_id,
            period_type=PeriodType.quarterly,
            period_end=period_end,
        )

        # DRE
        if income_stmt is not None and not income_stmt.empty:
            inc = income_stmt[col] if col in income_stmt.columns else {}
            stmt.revenue = _safe_float(inc.get("Total Revenue"))
            stmt.gross_profit = _safe_float(inc.get("Gross Profit"))
            stmt.operating_income = _safe_float(inc.get("Operating Income"))
            stmt.net_income = _safe_float(inc.get("Net Income"))
            stmt.ebitda = _safe_float(inc.get("EBITDA"))

        # Balanço
        if balance_sheet is not None and not balance_sheet.empty and col in balance_sheet.columns:
            bs = balance_sheet[col]
            stmt.total_assets = _safe_float(bs.get("Total Assets"))
            stmt.total_liabilities = _safe_float(bs.get("Total Liabilities Net Minority Interest"))
            stmt.total_equity = _safe_float(bs.get("Stockholders Equity"))
            stmt.cash_and_equivalents = _safe_float(bs.get("Cash And Cash Equivalents"))
            stmt.total_debt = _safe_float(bs.get("Total Debt"))

        # Fluxo de Caixa
        if cash_flow is not None and not cash_flow.empty and col in cash_flow.columns:
            cf = cash_flow[col]
            stmt.operating_cash_flow = _safe_float(cf.get("Operating Cash Flow"))
            stmt.capex = _safe_float(cf.get("Capital Expenditure"))
            stmt.free_cash_flow = _safe_float(cf.get("Free Cash Flow"))

        session.add(stmt)
        rows += 1

    session.flush()
    return rows


def _ingest_valuation_for_asset(session: Session, asset_id: int, symbol: str) -> int:
    """Ingere múltiplos de valuation de um ativo."""
    info = yf_client.fetch_info(symbol)
    if not info:
        return 0

    today = date.today()

    # Verificar se já existe para hoje
    existing = session.execute(
        select(ValuationMultiple).where(
            ValuationMultiple.asset_id == asset_id,
            ValuationMultiple.date == today,
        )
    ).scalar_one_or_none()

    if existing:
        return 0

    mult = ValuationMultiple(
        asset_id=asset_id,
        date=today,
        pe_ratio=_safe_float(info.get("trailingPE")),
        pb_ratio=_safe_float(info.get("priceToBook")),
        ps_ratio=_safe_float(info.get("priceToSalesTrailing12Months")),
        ev_ebitda=_safe_float(info.get("enterpriseToEbitda")),
        dividend_yield=_safe_float(info.get("dividendYield")),
        roe=_safe_float(info.get("returnOnEquity")),
        roa=_safe_float(info.get("returnOnAssets")),
        market_cap=_safe_float(info.get("marketCap")),
        enterprise_value=_safe_float(info.get("enterpriseValue")),
    )

    # Converter dividend_yield de decimal para percentual
    if mult.dividend_yield and mult.dividend_yield < 1:
        mult.dividend_yield = mult.dividend_yield * 100

    # Converter ROE/ROA de decimal para percentual
    if mult.roe and -1 < mult.roe < 1:
        mult.roe = mult.roe * 100
    if mult.roa and -1 < mult.roa < 1:
        mult.roa = mult.roa * 100

    session.add(mult)
    session.flush()
    return 1


def ingest_fundamentals(
    asset_type: str | None = None,
    country: str | None = None,
    symbols_filter: list[str] | None = None,
) -> dict:
    """
    Pipeline de ingestão de fundamentos (financials + valuation).

    Args:
        asset_type: Filtrar por tipo (só stocks fazem sentido)
        country: Filtrar por país
        symbols_filter: Lista explícita de símbolos

    Returns:
        Dict com estatísticas.
    """
    # Fundamentals só fazem sentido para stocks
    if asset_type is None:
        asset_type = "stock"

    all_syms = get_symbols(asset_type=asset_type, country=country)
    if symbols_filter:
        all_syms = [s for s in all_syms if s[0] in symbols_filter]

    total = len(all_syms)
    success = 0
    errors_list = []

    logger.info(f"Iniciando ingestão de fundamentos: {total} símbolos")

    with get_session() as session:
        for i, (sym, name, atype, cty) in enumerate(all_syms, 1):
            logger.info(f"[{i}/{total}] {sym} — fundamentos")

            try:
                asset_id = session.execute(
                    select(Asset.id).where(Asset.symbol == sym)
                ).scalar_one_or_none()

                if not asset_id:
                    logger.warning(f"[{sym}] Asset não encontrado no banco, pulando")
                    continue

                fin_rows = _ingest_financials_for_asset(session, asset_id, sym)
                val_rows = _ingest_valuation_for_asset(session, asset_id, sym)

                # Log de ingestão
                log = IngestionLog(
                    asset_id=asset_id,
                    status=IngestionStatus.success,
                    rows_inserted=fin_rows + val_rows,
                    data_type="fundamentals",
                    finished_at=datetime.utcnow(),
                )
                session.add(log)
                session.commit()

                success += 1
                logger.info(f"[{sym}] {fin_rows} financials + {val_rows} valuation inseridos")

            except Exception as e:
                session.rollback()
                errors_list.append({"symbol": sym, "error": str(e)[:200]})
                logger.error(f"[{sym}] ERRO: {e}")

    return {
        "total": total,
        "success": success,
        "errors": len(errors_list),
        "error_details": errors_list[:20],
    }
