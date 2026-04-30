"""
ingestion/fundamentals_loader.py
Ingestão de DRE, balanço, fluxo de caixa e múltiplos de valuation.
"""

import time
import logging
import numpy as np
from datetime import datetime, date
from sqlalchemy import select

from backend.db.connection import get_session, IS_SQLITE
from backend.db.schema import (
    Company, FinancialStatement, ValuationMultiple,
    PeriodType, IngestionLog, IngestionStatus
)
from backend.config.symbols import ALL_STOCKS
from backend.ingestion.yf_client import YFinanceClient, BATCH_SIZE

logger = logging.getLogger("market_platform")


def _safe(val):
    """Converte para float seguro, tratando NaN e None."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if np.isnan(f) or np.isinf(f) else f
    except (ValueError, TypeError):
        return None


def _get_field(df, field_names):
    """Busca campo no DataFrame tentando múltiplos nomes (yfinance varia)."""
    if df is None or df.empty:
        return None
    for name in field_names:
        if name in df.index:
            return df.loc[name]
    return None


def compute_net_debt_ebitda(net_debt, ebitda):
    """
    Net Debt / EBITDA. Retorna None quando algum operando está ausente,
    quando o EBITDA é zero (divisão indefinida) ou quando o resultado não é
    finito (NaN/inf). Aceita Decimal/float/int/None.
    """
    if net_debt is None or ebitda is None:
        return None
    try:
        nd = float(net_debt)
        eb = float(ebitda)
    except (TypeError, ValueError):
        return None
    if np.isnan(nd) or np.isnan(eb) or np.isinf(nd) or np.isinf(eb):
        return None
    if eb == 0:
        return None
    ratio = nd / eb
    if np.isnan(ratio) or np.isinf(ratio):
        return None
    return ratio


def latest_net_debt_ebitda(session, company_id):
    """
    Busca a `FinancialStatement` mais recente da empresa (maior `period_end`)
    e devolve `Net Debt / EBITDA` calculado a partir dos campos persistidos.
    Retorna None se a empresa não tem demonstração ou se algum operando
    está ausente/zero.
    """
    latest = session.execute(
        select(FinancialStatement)
        .where(FinancialStatement.company_id == company_id)
        .order_by(FinancialStatement.period_end.desc())
        .limit(1)
    ).scalar_one_or_none()
    if latest is None:
        return None
    return compute_net_debt_ebitda(latest.net_debt, latest.ebitda)


def ingest_financials_for_symbol(client: YFinanceClient, symbol: str) -> tuple[int, int]:
    """
    Ingere dados financeiros e múltiplos de valuation para um ticker.

    Returns:
        (financial_rows, valuation_rows) inseridos.
    """
    session = get_session()
    fin_rows = 0
    val_rows = 0

    try:
        # Busca company
        company = session.execute(
            select(Company).where(Company.ticker == symbol)
        ).scalar_one_or_none()

        if not company:
            logger.warning(f"⚠️  {symbol}: company não encontrada, pulando fundamentos")
            return 0, 0

        # ─── DEMONSTRAÇÕES FINANCEIRAS ───
        financials = client.get_financials(symbol)
        if financials:
            income = financials.get("income_stmt")
            balance = financials.get("balance_sheet")
            cashflow = financials.get("cashflow")

            if income is not None and not income.empty:
                for col in income.columns:
                    period_end = col.date() if hasattr(col, 'date') else col

                    # Extrair campos do income statement
                    revenue = _safe(_get_field(income[col], ["Total Revenue", "Revenue"]))
                    cost_rev = _safe(_get_field(income[col], ["Cost Of Revenue"]))
                    gross = _safe(_get_field(income[col], ["Gross Profit"]))
                    op_income = _safe(_get_field(income[col], ["Operating Income", "Operating Revenue"]))
                    ebitda = _safe(_get_field(income[col], ["EBITDA", "Normalized EBITDA"]))
                    net_income = _safe(_get_field(income[col], ["Net Income", "Net Income Common Stockholders"]))

                    # Balanço (se disponível para o mesmo período)
                    total_assets = total_liab = total_equity = cash = total_debt = net_debt = None
                    if balance is not None and not balance.empty and col in balance.columns:
                        total_assets = _safe(_get_field(balance[col], ["Total Assets"]))
                        total_liab = _safe(_get_field(balance[col], ["Total Liabilities Net Minority Interest", "Total Liabilities"]))
                        total_equity = _safe(_get_field(balance[col], ["Total Equity Gross Minority Interest", "Stockholders Equity"]))
                        cash = _safe(_get_field(balance[col], ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"]))
                        total_debt = _safe(_get_field(balance[col], ["Total Debt", "Long Term Debt"]))
                        if cash is not None and total_debt is not None:
                            net_debt = total_debt - cash

                    # Fluxo de caixa
                    ocf = capex = fcf = None
                    if cashflow is not None and not cashflow.empty and col in cashflow.columns:
                        ocf = _safe(_get_field(cashflow[col], ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"]))
                        capex = _safe(_get_field(cashflow[col], ["Capital Expenditure"]))
                        if ocf is not None and capex is not None:
                            fcf = ocf + capex  # capex é negativo

                    row_data = {
                        "company_id": company.id,
                        "period_end": period_end,
                        "period_type": PeriodType.quarterly,
                        "revenue": revenue,
                        "cost_of_revenue": cost_rev,
                        "gross_profit": gross,
                        "operating_income": op_income,
                        "ebitda": ebitda,
                        "net_income": net_income,
                        "total_assets": total_assets,
                        "total_liabilities": total_liab,
                        "total_equity": total_equity,
                        "cash": cash,
                        "total_debt": total_debt,
                        "net_debt": net_debt,
                        "operating_cash_flow": ocf,
                        "capex": capex,
                        "free_cash_flow": fcf,
                        "currency": company.currency,
                    }

                    if IS_SQLITE:
                        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
                        stmt = sqlite_insert(FinancialStatement).values(row_data)
                        stmt = stmt.on_conflict_do_update(
                            index_elements=["company_id", "period_end", "period_type"],
                            set_={k: stmt.excluded[k] for k in row_data if k not in ("company_id", "period_end", "period_type")}
                        )
                    else:
                        from sqlalchemy.dialects.postgresql import insert as pg_insert
                        stmt = pg_insert(FinancialStatement).values(row_data)
                        stmt = stmt.on_conflict_do_update(
                            constraint="uq_financials_company_period",
                            set_={k: stmt.excluded[k] for k in row_data if k not in ("company_id", "period_end", "period_type")}
                        )
                    session.execute(stmt)
                    fin_rows += 1

                session.commit()

        # ─── MÚLTIPLOS DE VALUATION ───
        info = client.get_info(symbol)
        if info:
            snapshot = {
                "company_id": company.id,
                "snapshot_date": date.today(),
                "pe_ratio": _safe(info.get("trailingPE")),
                "pb_ratio": _safe(info.get("priceToBook")),
                "ps_ratio": _safe(info.get("priceToSalesTrailing12Months")),
                "ev_ebitda": _safe(info.get("enterpriseToEbitda")),
                "ev_revenue": _safe(info.get("enterpriseToRevenue")),
                "roe": _safe(info.get("returnOnEquity")),
                "roa": _safe(info.get("returnOnAssets")),
                "gross_margin": _safe(info.get("grossMargins")),
                "operating_margin": _safe(info.get("operatingMargins")),
                "net_margin": _safe(info.get("profitMargins")),
                "debt_to_equity": _safe(info.get("debtToEquity")),
                "current_ratio": _safe(info.get("currentRatio")),
                "dividend_yield": _safe(info.get("dividendYield")),
                "payout_ratio": _safe(info.get("payoutRatio")),
                "net_debt_ebitda": latest_net_debt_ebitda(session, company.id),
            }

            if IS_SQLITE:
                from sqlalchemy.dialects.sqlite import insert as sqlite_insert
                stmt = sqlite_insert(ValuationMultiple).values(snapshot)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["company_id", "snapshot_date"],
                    set_={k: stmt.excluded[k] for k in snapshot if k not in ("company_id", "snapshot_date")}
                )
            else:
                from sqlalchemy.dialects.postgresql import insert as pg_insert
                stmt = pg_insert(ValuationMultiple).values(snapshot)
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_valuation_company_date",
                    set_={k: stmt.excluded[k] for k in snapshot if k not in ("company_id", "snapshot_date")}
                )
            session.execute(stmt)
            session.commit()
            val_rows = 1

        return fin_rows, val_rows

    except Exception as e:
        session.rollback()
        logger.error(f"❌ {symbol} fundamentos: {e}")
        raise
    finally:
        session.close()


def ingest_fundamentals():
    """Pipeline de ingestão de fundamentos para todas as ações."""
    client = YFinanceClient()
    total_fin = 0
    total_val = 0
    total_errors = 0

    logger.info(f"\n{'='*60}")
    logger.info(f"🚀 Ingestão de FUNDAMENTOS — {len(ALL_STOCKS)} empresas")
    logger.info(f"{'='*60}")

    for i in range(0, len(ALL_STOCKS), BATCH_SIZE):
        batch = ALL_STOCKS[i:i + BATCH_SIZE]
        logger.info(f"📦 Batch {i // BATCH_SIZE + 1}: {batch}")

        for symbol in batch:
            start_time = time.time()
            session = get_session()

            try:
                fin_rows, val_rows = ingest_financials_for_symbol(client, symbol)
                duration = time.time() - start_time

                log_entry = IngestionLog(
                    symbol=symbol,
                    ingestion_type="fundamentals",
                    rows_inserted=fin_rows + val_rows,
                    status=IngestionStatus.success,
                    duration_seconds=duration,
                    finished_at=datetime.utcnow(),
                )
                session.add(log_entry)
                session.commit()

                total_fin += fin_rows
                total_val += val_rows
                logger.info(f"✅ {symbol}: {fin_rows} demonstrações, {val_rows} valuations — {duration:.1f}s")

            except Exception as e:
                duration = time.time() - start_time
                log_entry = IngestionLog(
                    symbol=symbol,
                    ingestion_type="fundamentals",
                    rows_inserted=0,
                    status=IngestionStatus.error,
                    error_message=str(e)[:500],
                    duration_seconds=duration,
                    finished_at=datetime.utcnow(),
                )
                session.add(log_entry)
                session.commit()
                total_errors += 1
                logger.error(f"❌ {symbol}: {e}")
            finally:
                session.close()

        if i + BATCH_SIZE < len(ALL_STOCKS):
            client.sleep_between_batches()

    logger.info(f"\n{'='*60}")
    logger.info(f"📊 RESUMO FUNDAMENTOS: {total_fin} demonstrações, {total_val} valuations, {total_errors} erros")
    logger.info(f"{'='*60}")
    return total_fin, total_val, total_errors
