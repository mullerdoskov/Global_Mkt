"""
api/fundamentals.py
Endpoints de fundamentos e valuation.
"""

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from backend.config.settings import settings
from backend.db.connection import get_session
from backend.db.schema import Company, FinancialStatement, ValuationMultiple
from backend.api.models import FinancialsResponse, FinancialQuarter, ValuationResponse, ValuationMultiples
from backend.api._limiter import limiter

router = APIRouter(prefix="/fundamentals", tags=["fundamentals"])


@router.get("/{symbol}", response_model=FinancialsResponse)
@limiter.limit(settings.rate_limit_default)
def get_financials(request: Request, symbol: str) -> FinancialsResponse:
    """
    Retorna demonstrações financeiras (DRE, balanço, FCF) dos últimos 4 trimestres.

    Inclui:
    - Revenue, EBITDA, Net Income
    - Total Assets, Liabilities, Equity
    - Cash, Debt, Free Cash Flow
    """
    session = get_session()
    try:
        # Busca a company
        company = session.execute(
            select(Company).where(Company.ticker == symbol)
        ).scalar_one_or_none()

        if not company:
            raise HTTPException(status_code=404, detail=f"Company '{symbol}' not found")

        # Busca últimas 4 demonstrações financeiras (trimestrais)
        financials_query = select(FinancialStatement).where(
            FinancialStatement.company_id == company.id
        ).order_by(FinancialStatement.period_end.desc()).limit(4)

        financials = session.execute(financials_query).scalars().all()

        # Reverter para ordem cronológica (mais antigo primeiro)
        financials = list(reversed(financials))

        quarters = [
            FinancialQuarter(
                period_end=f.period_end,
                revenue=float(f.revenue) if f.revenue else None,
                cost_of_revenue=float(f.cost_of_revenue) if f.cost_of_revenue else None,
                gross_profit=float(f.gross_profit) if f.gross_profit else None,
                operating_income=float(f.operating_income) if f.operating_income else None,
                ebitda=float(f.ebitda) if f.ebitda else None,
                net_income=float(f.net_income) if f.net_income else None,
                total_assets=float(f.total_assets) if f.total_assets else None,
                total_liabilities=float(f.total_liabilities) if f.total_liabilities else None,
                total_equity=float(f.total_equity) if f.total_equity else None,
                cash=float(f.cash) if f.cash else None,
                total_debt=float(f.total_debt) if f.total_debt else None,
                net_debt=float(f.net_debt) if f.net_debt else None,
                operating_cash_flow=float(f.operating_cash_flow) if f.operating_cash_flow else None,
                capex=float(f.capex) if f.capex else None,
                free_cash_flow=float(f.free_cash_flow) if f.free_cash_flow else None,
                currency=f.currency,
            )
            for f in financials
        ]

        return FinancialsResponse(
            symbol=symbol,
            company_name=company.name,
            quarters=quarters,
        )

    finally:
        session.close()


@router.get("/{symbol}/valuation", response_model=ValuationResponse)
@limiter.limit(settings.rate_limit_default)
def get_valuation(request: Request, symbol: str) -> ValuationResponse:
    """
    Retorna múltiplos de valuation mais recentes.

    Inclui:
    - Razões de preço: P/E, P/B, P/S
    - Razões de valor: EV/EBITDA, EV/Revenue
    - Rentabilidade: ROE, ROA, Margens
    - Estrutura de capital: Debt/Equity, Current Ratio
    - Retorno ao acionista: Dividend Yield, Payout Ratio
    """
    session = get_session()
    try:
        # Busca a company
        company = session.execute(
            select(Company).where(Company.ticker == symbol)
        ).scalar_one_or_none()

        if not company:
            raise HTTPException(status_code=404, detail=f"Company '{symbol}' not found")

        # Busca múltiplo de valuation mais recente
        valuation_query = select(ValuationMultiple).where(
            ValuationMultiple.company_id == company.id
        ).order_by(ValuationMultiple.snapshot_date.desc()).limit(1)

        valuation = session.execute(valuation_query).scalar_one_or_none()

        multiples = None
        if valuation:
            multiples = ValuationMultiples(
                snapshot_date=valuation.snapshot_date,
                pe_ratio=float(valuation.pe_ratio) if valuation.pe_ratio else None,
                pb_ratio=float(valuation.pb_ratio) if valuation.pb_ratio else None,
                ps_ratio=float(valuation.ps_ratio) if valuation.ps_ratio else None,
                ev_ebitda=float(valuation.ev_ebitda) if valuation.ev_ebitda else None,
                ev_revenue=float(valuation.ev_revenue) if valuation.ev_revenue else None,
                roe=float(valuation.roe) if valuation.roe else None,
                roa=float(valuation.roa) if valuation.roa else None,
                gross_margin=float(valuation.gross_margin) if valuation.gross_margin else None,
                operating_margin=float(valuation.operating_margin) if valuation.operating_margin else None,
                net_margin=float(valuation.net_margin) if valuation.net_margin else None,
                debt_to_equity=float(valuation.debt_to_equity) if valuation.debt_to_equity else None,
                current_ratio=float(valuation.current_ratio) if valuation.current_ratio else None,
                dividend_yield=float(valuation.dividend_yield) if valuation.dividend_yield else None,
                payout_ratio=float(valuation.payout_ratio) if valuation.payout_ratio else None,
                net_debt_ebitda=float(valuation.net_debt_ebitda) if valuation.net_debt_ebitda else None,
            )

        return ValuationResponse(
            symbol=symbol,
            company_name=company.name,
            multiples=multiples,
        )

    finally:
        session.close()
