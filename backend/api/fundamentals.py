"""
Endpoints: /api/fundamentals/{symbol}, /api/fundamentals/{symbol}/valuation
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.models import (
    FinancialQuarter,
    FinancialsResponse,
    ValuationData,
    ValuationResponse,
)
from backend.db.connection import get_db
from backend.db.schema import Asset, FinancialStatement, ValuationMultiple

router = APIRouter(prefix="/fundamentals", tags=["Fundamentals"])


@router.get("/{symbol}", response_model=FinancialsResponse)
def get_financials(symbol: str, db: Session = Depends(get_db)):
    """Demonstrativos financeiros trimestrais de um ativo."""
    asset = db.execute(
        select(Asset).where(Asset.symbol == symbol)
    ).scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset '{symbol}' não encontrado")

    stmts = db.execute(
        select(FinancialStatement)
        .where(FinancialStatement.asset_id == asset.id)
        .order_by(FinancialStatement.period_end.desc())
        .limit(8)
    ).scalars().all()

    quarters = [
        FinancialQuarter(
            period_end=s.period_end,
            period_type=s.period_type.value if hasattr(s.period_type, "value") else str(s.period_type),
            revenue=float(s.revenue) if s.revenue else None,
            gross_profit=float(s.gross_profit) if s.gross_profit else None,
            operating_income=float(s.operating_income) if s.operating_income else None,
            net_income=float(s.net_income) if s.net_income else None,
            ebitda=float(s.ebitda) if s.ebitda else None,
            total_assets=float(s.total_assets) if s.total_assets else None,
            total_liabilities=float(s.total_liabilities) if s.total_liabilities else None,
            total_equity=float(s.total_equity) if s.total_equity else None,
            cash_and_equivalents=float(s.cash_and_equivalents) if s.cash_and_equivalents else None,
            total_debt=float(s.total_debt) if s.total_debt else None,
            operating_cash_flow=float(s.operating_cash_flow) if s.operating_cash_flow else None,
            capex=float(s.capex) if s.capex else None,
            free_cash_flow=float(s.free_cash_flow) if s.free_cash_flow else None,
        )
        for s in stmts
    ]

    return FinancialsResponse(
        symbol=asset.symbol,
        company_name=asset.name,
        quarters=quarters,
    )


@router.get("/{symbol}/valuation", response_model=ValuationResponse)
def get_valuation(symbol: str, db: Session = Depends(get_db)):
    """Múltiplos de valuation mais recentes de um ativo."""
    asset = db.execute(
        select(Asset).where(Asset.symbol == symbol)
    ).scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset '{symbol}' não encontrado")

    mult = db.execute(
        select(ValuationMultiple)
        .where(ValuationMultiple.asset_id == asset.id)
        .order_by(ValuationMultiple.date.desc())
        .limit(1)
    ).scalar_one_or_none()

    multiples = None
    if mult:
        multiples = ValuationData(
            pe_ratio=mult.pe_ratio,
            pb_ratio=mult.pb_ratio,
            ps_ratio=mult.ps_ratio,
            ev_ebitda=mult.ev_ebitda,
            dividend_yield=mult.dividend_yield,
            roe=mult.roe,
            roa=mult.roa,
            market_cap=float(mult.market_cap) if mult.market_cap else None,
            enterprise_value=float(mult.enterprise_value) if mult.enterprise_value else None,
            date=mult.date,
        )

    return ValuationResponse(
        symbol=asset.symbol,
        company_name=asset.name,
        multiples=multiples,
    )
