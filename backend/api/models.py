"""
api/models.py
Response models Pydantic para os endpoints.
"""

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


# ══════════════════════════════════════════════
# MODELOS DE ASSETS
# ══════════════════════════════════════════════

class AssetInfo(BaseModel):
    """Informações básicas de um ativo."""
    symbol: str
    name: str
    asset_type: str
    currency: Optional[str] = None
    exchange: Optional[str] = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class CompanyInfo(BaseModel):
    """Informações de uma companhia."""
    ticker: str
    name: str
    country_iso2: Optional[str] = None
    sector: Optional[str] = None
    market_cap: Optional[int] = None
    employees: Optional[int] = None
    currency: Optional[str] = None
    exchange: Optional[str] = None


class AssetDetail(BaseModel):
    """Detalhes completos de um ativo."""
    symbol: str
    name: str
    asset_type: str
    currency: Optional[str] = None
    exchange: Optional[str] = None
    company: Optional[CompanyInfo] = None
    latest_price: Optional[float] = None
    latest_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


class AssetListResponse(BaseModel):
    """Resposta de listagem de ativos com paginação."""
    total: int
    page: int
    page_size: int
    assets: List[AssetInfo]


# ══════════════════════════════════════════════
# MODELOS DE PREÇOS
# ══════════════════════════════════════════════

class PriceBar(BaseModel):
    """Uma barra OHLCV."""
    date: date
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    adj_close: Optional[float] = None
    volume: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class PriceHistoryResponse(BaseModel):
    """Série histórica de preços."""
    symbol: str
    period: str
    interval: str
    count: int
    prices: List[PriceBar]


class ReturnData(BaseModel):
    """Retorno diário e acumulado."""
    date: date
    daily_return: Optional[float] = None
    cumulative_return: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class ReturnsResponse(BaseModel):
    """Série de retornos."""
    symbol: str
    period: str
    count: int
    returns: List[ReturnData]


class LatestPrice(BaseModel):
    """Último preço de um ativo."""
    symbol: str
    name: str
    close: Optional[float] = None
    price_date: Optional[date] = None
    change_pct: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class LatestPricesResponse(BaseModel):
    """Snapshot com últimos preços de vários ativos."""
    as_of: date
    total: int
    page: int
    page_size: int
    prices: List[LatestPrice]


# ══════════════════════════════════════════════
# MODELOS DE MERCADO
# ══════════════════════════════════════════════

class IndexSnapshot(BaseModel):
    """Snapshot de um índice."""
    symbol: str
    name: str
    close: Optional[float] = None
    index_date: Optional[date] = None
    change_pct: Optional[float] = None


class MarketSummaryResponse(BaseModel):
    """Resumo dos índices globais."""
    as_of: date
    indices: List[IndexSnapshot]


class SectorPerformance(BaseModel):
    """Performance de um setor."""
    sector: str
    sector_pt: str
    avg_return_pct: Optional[float] = None
    asset_count: int
    period: str


class SectorsResponse(BaseModel):
    """Performance por setor."""
    period: str
    as_of: date
    sectors: List[SectorPerformance]


class CountryAssets(BaseModel):
    """Contagem de ativos por país."""
    country_iso2: str
    country_name: str
    asset_count: int


class CountriesResponse(BaseModel):
    """Lista de países com contagem de ativos."""
    total_countries: int
    countries: List[CountryAssets]


# ══════════════════════════════════════════════
# MODELOS DE FUNDAMENTOS
# ══════════════════════════════════════════════

class FinancialQuarter(BaseModel):
    """Um trimestre de dados financeiros."""
    period_end: date
    revenue: Optional[float] = None
    cost_of_revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_income: Optional[float] = None
    ebitda: Optional[float] = None
    net_income: Optional[float] = None
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    cash: Optional[float] = None
    total_debt: Optional[float] = None
    net_debt: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    capex: Optional[float] = None
    free_cash_flow: Optional[float] = None
    currency: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FinancialsResponse(BaseModel):
    """Demonstrações financeiras (últimos 4 trimestres)."""
    symbol: str
    company_name: str
    quarters: List[FinancialQuarter]


class ValuationMultiples(BaseModel):
    """Múltiplos de valuation."""
    snapshot_date: date
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    ev_revenue: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    payout_ratio: Optional[float] = None
    net_debt_ebitda: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class ValuationResponse(BaseModel):
    """Resposta com múltiplos de valuation."""
    symbol: str
    company_name: str
    multiples: Optional[ValuationMultiples] = None


# ══════════════════════════════════════════════
# MODELOS DE INGESTÃO
# ══════════════════════════════════════════════

class IngestionLogEntry(BaseModel):
    """Entrada de log de ingestão."""
    symbol: str
    ingestion_type: str
    status: str
    rows_inserted: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class IngestionStatusResponse(BaseModel):
    """Status geral da ingestão."""
    last_update: Optional[datetime] = None
    total_assets: int
    recent_logs: List[IngestionLogEntry]
    success_count: int
    error_count: int


# ══════════════════════════════════════════════
# MODELOS GENÉRICOS
# ══════════════════════════════════════════════

class ErrorResponse(BaseModel):
    """Resposta de erro padronizada."""
    detail: str
    status_code: int


class HealthResponse(BaseModel):
    """Resposta de health check."""
    status: str
    version: str = "1.0.0"
    database: str


# ══════════════════════════════════════════════
# MODELOS DE WATCHLIST (ISSUE-018)
# ══════════════════════════════════════════════

class WatchlistItemOut(BaseModel):
    """Um item da watchlist enriquecido com dados do asset."""
    symbol: str
    name: str
    asset_type: str
    currency: Optional[str] = None
    exchange: Optional[str] = None
    position: int
    added_at: datetime


class WatchlistResponse(BaseModel):
    """Resposta de GET /api/watchlist."""
    items: List[WatchlistItemOut]


class WatchlistMutationResponse(BaseModel):
    """Resposta de POST/DELETE: estado terminal do item."""
    symbol: str
    in_watchlist: bool
    position: Optional[int] = None
