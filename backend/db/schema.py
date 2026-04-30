"""
db/schema.py
11 tabelas ORM — DDL completo com índices, constraints e relacionamentos.
Criação idempotente (CREATE IF NOT EXISTS).

ISSUE-018: tabelas user_sessions + watchlist_items para watchlist persistente
via cookie UUID anônimo (ver DECISIONS.md, ADR de 2026-04-30).
"""

from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, Date, DateTime, Boolean,
    Text, Numeric, ForeignKey, UniqueConstraint, Index, Enum as SAEnum,
    Uuid, func
)
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    pass


# ──────────────────────────────────────────────
# ENUMS
# ──────────────────────────────────────────────
class AssetType(str, enum.Enum):
    stock = "stock"
    index = "index"
    commodity = "commodity"
    fx = "fx"
    crypto = "crypto"
    etf = "etf"


class PeriodType(str, enum.Enum):
    quarterly = "quarterly"
    annual = "annual"


class IngestionStatus(str, enum.Enum):
    success = "success"
    error = "error"
    partial = "partial"


# ──────────────────────────────────────────────
# 1. COUNTRIES (Referência)
# ──────────────────────────────────────────────
class Country(Base):
    __tablename__ = "countries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    iso2 = Column(String(2), unique=True, nullable=False)
    iso3 = Column(String(3), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    name_pt = Column(String(100))
    region = Column(String(50))
    currency_code = Column(String(3))
    main_exchange = Column(String(50))
    yf_suffix = Column(String(10), default="")

    companies = relationship("Company", back_populates="country")

    def __repr__(self):
        return f"<Country {self.iso2} - {self.name}>"


# ──────────────────────────────────────────────
# 2. SECTORS_GICS (Referência)
# ──────────────────────────────────────────────
class SectorGICS(Base):
    __tablename__ = "sectors_gics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sector = Column(String(100), nullable=False)
    sector_pt = Column(String(100))
    industry_group = Column(String(150))
    industry = Column(String(150))
    sub_industry = Column(String(200))
    gics_code = Column(String(20))

    companies = relationship("Company", back_populates="sector_gics")

    __table_args__ = (
        Index("ix_sectors_gics_sector", "sector"),
        Index("ix_sectors_gics_gics_code", "gics_code"),
    )

    def __repr__(self):
        return f"<SectorGICS {self.sector} ({self.gics_code})>"


# ──────────────────────────────────────────────
# 3. COMPANIES (Mestre)
# ──────────────────────────────────────────────
class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    country_id = Column(Integer, ForeignKey("countries.id"))
    sector_gics_id = Column(Integer, ForeignKey("sectors_gics.id"))
    exchange = Column(String(50))
    currency = Column(String(3))
    market_cap = Column(BigInteger)
    employees = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    country = relationship("Country", back_populates="companies")
    sector_gics = relationship("SectorGICS", back_populates="companies")
    assets = relationship("Asset", back_populates="company")
    financial_statements = relationship("FinancialStatement", back_populates="company")
    valuation_multiples = relationship("ValuationMultiple", back_populates="company")

    __table_args__ = (
        Index("ix_companies_ticker", "ticker"),
        Index("ix_companies_country_id", "country_id"),
        Index("ix_companies_sector_gics_id", "sector_gics_id"),
    )

    def __repr__(self):
        return f"<Company {self.ticker} - {self.name}>"


# ──────────────────────────────────────────────
# 4. ASSETS (Mestre)
# ──────────────────────────────────────────────
class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, nullable=False)
    asset_type = Column(SAEnum(AssetType), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    name = Column(String(200))
    currency = Column(String(3))
    exchange = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    company = relationship("Company", back_populates="assets")
    prices = relationship("PriceDaily", back_populates="asset")

    __table_args__ = (
        Index("ix_assets_symbol", "symbol"),
        Index("ix_assets_asset_type", "asset_type"),
    )

    def __repr__(self):
        return f"<Asset {self.symbol} ({self.asset_type})>"


# ──────────────────────────────────────────────
# 5. TRADING_CALENDAR (Suporte)
# ──────────────────────────────────────────────
class TradingCalendar(Base):
    __tablename__ = "trading_calendar"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    exchange = Column(String(20), nullable=False)
    is_business_day = Column(Boolean, default=True)
    holiday_name = Column(String(100))

    __table_args__ = (
        UniqueConstraint("date", "exchange", name="uq_calendar_date_exchange"),
        Index("ix_trading_calendar_date", "date"),
        Index("ix_trading_calendar_exchange", "exchange"),
    )

    def __repr__(self):
        return f"<TradingCalendar {self.date} {self.exchange} bday={self.is_business_day}>"


# ──────────────────────────────────────────────
# 6. PRICES_DAILY (Fato)
# ──────────────────────────────────────────────
class PriceDaily(Base):
    __tablename__ = "prices_daily"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    date = Column(Date, nullable=False)
    open = Column(Numeric(18, 6))
    high = Column(Numeric(18, 6))
    low = Column(Numeric(18, 6))
    close = Column(Numeric(18, 6))
    adj_close = Column(Numeric(18, 6))
    volume = Column(BigInteger)
    created_at = Column(DateTime, server_default=func.now())

    asset = relationship("Asset", back_populates="prices")

    __table_args__ = (
        UniqueConstraint("asset_id", "date", name="uq_prices_asset_date"),
        Index("ix_prices_daily_asset_id", "asset_id"),
        Index("ix_prices_daily_date", "date"),
        Index("ix_prices_daily_asset_date", "asset_id", "date"),
    )

    def __repr__(self):
        return f"<PriceDaily asset={self.asset_id} date={self.date} close={self.close}>"


# ──────────────────────────────────────────────
# 7. FINANCIAL_STATEMENTS (Fato)
# ──────────────────────────────────────────────
class FinancialStatement(Base):
    __tablename__ = "financial_statements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    period_end = Column(Date, nullable=False)
    period_type = Column(SAEnum(PeriodType), nullable=False)
    # DRE
    revenue = Column(Numeric(18, 2))
    cost_of_revenue = Column(Numeric(18, 2))
    gross_profit = Column(Numeric(18, 2))
    operating_income = Column(Numeric(18, 2))
    ebitda = Column(Numeric(18, 2))
    net_income = Column(Numeric(18, 2))
    # Balanço
    total_assets = Column(Numeric(18, 2))
    total_liabilities = Column(Numeric(18, 2))
    total_equity = Column(Numeric(18, 2))
    cash = Column(Numeric(18, 2))
    total_debt = Column(Numeric(18, 2))
    net_debt = Column(Numeric(18, 2))
    # Fluxo de Caixa
    operating_cash_flow = Column(Numeric(18, 2))
    capex = Column(Numeric(18, 2))
    free_cash_flow = Column(Numeric(18, 2))
    currency = Column(String(3))
    created_at = Column(DateTime, server_default=func.now())

    company = relationship("Company", back_populates="financial_statements")

    __table_args__ = (
        UniqueConstraint("company_id", "period_end", "period_type",
                         name="uq_financials_company_period"),
        Index("ix_financial_statements_company_id", "company_id"),
        Index("ix_financial_statements_period_end", "period_end"),
    )

    def __repr__(self):
        return f"<FinancialStatement company={self.company_id} period={self.period_end}>"


# ──────────────────────────────────────────────
# 8. VALUATION_MULTIPLES (Fato)
# ──────────────────────────────────────────────
class ValuationMultiple(Base):
    __tablename__ = "valuation_multiples"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    pe_ratio = Column(Numeric(12, 4))
    pb_ratio = Column(Numeric(12, 4))
    ps_ratio = Column(Numeric(12, 4))
    ev_ebitda = Column(Numeric(12, 4))
    ev_revenue = Column(Numeric(12, 4))
    roe = Column(Numeric(10, 4))
    roa = Column(Numeric(10, 4))
    gross_margin = Column(Numeric(10, 4))
    operating_margin = Column(Numeric(10, 4))
    net_margin = Column(Numeric(10, 4))
    debt_to_equity = Column(Numeric(12, 4))
    current_ratio = Column(Numeric(10, 4))
    dividend_yield = Column(Numeric(10, 6))
    payout_ratio = Column(Numeric(10, 4))
    net_debt_ebitda = Column(Numeric(12, 4))
    created_at = Column(DateTime, server_default=func.now())

    company = relationship("Company", back_populates="valuation_multiples")

    __table_args__ = (
        UniqueConstraint("company_id", "snapshot_date",
                         name="uq_valuation_company_date"),
        Index("ix_valuation_multiples_company_id", "company_id"),
        Index("ix_valuation_multiples_snapshot_date", "snapshot_date"),
    )

    def __repr__(self):
        return f"<ValuationMultiple company={self.company_id} date={self.snapshot_date}>"


# ──────────────────────────────────────────────
# 9. INGESTION_LOG (Auditoria)
# ──────────────────────────────────────────────
class IngestionLog(Base):
    __tablename__ = "ingestion_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    ingestion_type = Column(String(30), nullable=False)  # prices, fundamentals, valuations
    rows_inserted = Column(Integer, default=0)
    status = Column(SAEnum(IngestionStatus), nullable=False)
    error_message = Column(Text)
    duration_seconds = Column(Float)
    started_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime)

    __table_args__ = (
        Index("ix_ingestion_log_symbol", "symbol"),
        Index("ix_ingestion_log_status", "status"),
        Index("ix_ingestion_log_started_at", "started_at"),
    )

    def __repr__(self):
        return f"<IngestionLog {self.symbol} {self.ingestion_type} {self.status}>"


# ──────────────────────────────────────────────
# 10. USER_SESSIONS (Sessões anônimas via cookie — ISSUE-018)
# ──────────────────────────────────────────────
class UserSession(Base):
    """Sessão anônima identificada por UUID v4 em cookie HTTP.

    Sem PII. Sem auth. Quando ISSUE de SSO M365 for retomada, esta tabela
    ganha relacionamento opcional com tabela `users` via coluna
    `linked_user_id` (ALTER aditiva, sem perda de dados).
    """
    __tablename__ = "user_sessions"

    uuid = Column(Uuid(as_uuid=True), primary_key=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    last_seen_at = Column(DateTime, server_default=func.now(), nullable=False)

    watchlist_items = relationship(
        "WatchlistItem",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<UserSession {self.uuid}>"


# ──────────────────────────────────────────────
# 11. WATCHLIST_ITEMS (Watchlist persistente — ISSUE-018)
# ──────────────────────────────────────────────
class WatchlistItem(Base):
    """Um asset numa watchlist de uma sessão.

    `position` é a ordem desejada na UI (ASC). `UNIQUE(session_uuid, asset_id)`
    garante idempotência do POST. CASCADE em ambos FKs mantém a tabela
    limpa: se a sessão sumir ou o asset for despromovido, items somem
    sem trabalho extra.
    """
    __tablename__ = "watchlist_items"

    # SQLite só auto-incrementa "INTEGER PRIMARY KEY" (rowid alias). BigInteger
    # vira BIGINT que não tem essa propriedade, então usamos Integer.
    # Watchlist é per-user, então Integer dá folga sobrada.
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_uuid = Column(
        Uuid(as_uuid=True),
        ForeignKey("user_sessions.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id = Column(
        Integer,
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    position = Column(Integer, nullable=False, default=0)
    added_at = Column(DateTime, server_default=func.now(), nullable=False)

    session = relationship("UserSession", back_populates="watchlist_items")
    asset = relationship("Asset")

    __table_args__ = (
        UniqueConstraint("session_uuid", "asset_id",
                         name="uq_watchlist_session_asset"),
        Index("ix_watchlist_items_session_uuid", "session_uuid"),
        Index("ix_watchlist_items_asset_id", "asset_id"),
    )

    def __repr__(self):
        return f"<WatchlistItem session={self.session_uuid} asset={self.asset_id}>"


# ──────────────────────────────────────────────
# SETUP — Cria todas as tabelas
# ──────────────────────────────────────────────
def create_all_tables(engine):
    """Cria todas as tabelas no banco (idempotente)."""
    Base.metadata.create_all(engine)
    print("✅ Todas as 11 tabelas criadas/verificadas com sucesso.")
