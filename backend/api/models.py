"""
Modelos Pydantic para request/response da API REST.
~30 modelos cobrindo todos os endpoints.
"""

from datetime import date, datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════
#  ASSETS
# ══════════════════════════════════════════════════════════

class AssetBase(BaseModel):
    symbol: str
    name: str
    asset_type: str
    country: Optional[str] = None
    is_active: bool = True


class AssetItem(AssetBase):
    id: int

    class Config:
        from_attributes = True


class AssetDetail(AssetBase):
    id: int
    company: Optional[dict] = None
    latest_price: Optional[dict] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AssetListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 50
    assets: List[AssetItem]


# ══════════════════════════════════════════════════════════
#  PRICES
# ══════════════════════════════════════════════════════════

class PriceItem(BaseModel):
    symbol: str
    name: str
    asset_type: str
    close: Optional[float] = None
    change_pct: Optional[float] = None
    date: Optional[date] = None
    volume: Optional[float] = None


class LatestPricesResponse(BaseModel):
    as_of: Optional[date] = None
    count: int
    prices: List[PriceItem]


class OHLCVItem(BaseModel):
    date: date
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    adj_close: Optional[float] = None
    volume: Optional[float] = None
    change_pct: Optional[float] = None


class PriceHistoryResponse(BaseModel):
    symbol: str
    period: str
    interval: str = "1d"
    count: int
    prices: List[OHLCVItem]


class ReturnItem(BaseModel):
    date: date
    close: Optional[float] = None
    change_pct: Optional[float] = None
    cumulative_return: Optional[float] = None


class ReturnsResponse(BaseModel):
    symbol: str
    period: str
    count: int
    returns: List[ReturnItem]


# ══════════════════════════════════════════════════════════
#  MARKET
# ══════════════════════════════════════════════════════════

class IndexItem(BaseModel):
    symbol: str
    name: str
    close: Optional[float] = None
    change_pct: Optional[float] = None
    date: Optional[date] = None


class MarketSummaryResponse(BaseModel):
    as_of: Optional[date] = None
    indices: List[IndexItem]


class SectorItem(BaseModel):
    sector: str
    count: int = 0
    avg_return_pct: Optional[float] = Field(None, alias="avg_performance")

    class Config:
        populate_by_name = True


class SectorsResponse(BaseModel):
    period: str = "30d"
    as_of: Optional[date] = None
    sectors: List[SectorItem]


class CountryItem(BaseModel):
    code: str
    name: str
    asset_count: int = 0
    currency: Optional[str] = None


class CountriesResponse(BaseModel):
    total_countries: int
    countries: List[CountryItem]


# ══════════════════════════════════════════════════════════
#  FUNDAMENTALS
# ══════════════════════════════════════════════════════════

class FinancialQuarter(BaseModel):
    period_end: Optional[date] = None
    period_type: str = "quarterly"
    revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_income: Optional[float] = None
    net_income: Optional[float] = None
    ebitda: Optional[float] = None
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    total_debt: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    capex: Optional[float] = None
    free_cash_flow: Optional[float] = None


class FinancialsResponse(BaseModel):
    symbol: str
    company_name: Optional[str] = None
    quarters: List[FinancialQuarter]


class ValuationData(BaseModel):
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    dividend_yield: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    market_cap: Optional[float] = None
    enterprise_value: Optional[float] = None
    date: Optional[date] = None


class ValuationResponse(BaseModel):
    symbol: str
    company_name: Optional[str] = None
    multiples: Optional[ValuationData] = None


# ══════════════════════════════════════════════════════════
#  INGESTION
# ══════════════════════════════════════════════════════════

class IngestionLogItem(BaseModel):
    symbol: Optional[str] = None
    status: str
    data_type: str = "prices"
    rows_inserted: int = 0
    rows_updated: int = 0
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None


class IngestionStatusResponse(BaseModel):
    total_assets: int
    success_count: int
    error_count: int
    partial_count: int = 0
    recent_logs: List[IngestionLogItem]


# ══════════════════════════════════════════════════════════
#  GENERIC
# ══════════════════════════════════════════════════════════

class HealthResponse(BaseModel):
    status: str
    db: str
    assets_count: int = 0
    prices_count: int = 0
    version: str = "2.0.0"


class ErrorResponse(BaseModel):
    detail: str
    status_code: int = 500
