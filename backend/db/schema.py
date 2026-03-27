"""
Schema ORM — 9 tabelas para o Market Platform Unified.
Compatível com PostgreSQL (produção) e SQLite (dev).
"""

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ══════════════════════════════════════════════════════════
#  ENUMS
# ══════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════
#  TABELA 1: countries
# ══════════════════════════════════════════════════════════

class Country(Base):
    __tablename__ = "countries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    currency = Column(String(10))
    exchange = Column(String(100))

    # Relacionamentos
    companies = relationship("Company", back_populates="country")

    def __repr__(self):
        return f"<Country(code={self.code}, name={self.name})>"


# ══════════════════════════════════════════════════════════
#  TABELA 2: sectors_gics
# ══════════════════════════════════════════════════════════

class SectorGICS(Base):
    __tablename__ = "sectors_gics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    gics_code = Column(Integer, unique=True, nullable=False, index=True)
    sector_name = Column(String(100), nullable=False)
    industry_group = Column(String(150))

    # Relacionamentos
    companies = relationship("Company", back_populates="sector")

    def __repr__(self):
        return f"<SectorGICS(code={self.gics_code}, name={self.sector_name})>"


# ══════════════════════════════════════════════════════════
#  TABELA 3: companies
# ══════════════════════════════════════════════════════════

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    country_id = Column(Integer, ForeignKey("countries.id"), nullable=True)
    sector_id = Column(Integer, ForeignKey("sectors_gics.id"), nullable=True)
    description = Column(Text, nullable=True)
    website = Column(String(300), nullable=True)
    employees = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    country = relationship("Country", back_populates="companies")
    sector = relationship("SectorGICS", back_populates="companies")
    assets = relationship("Asset", back_populates="company")

    def __repr__(self):
        return f"<Company(name={self.name})>"


# ══════════════════════════════════════════════════════════
#  TABELA 4: assets
# ══════════════════════════════════════════════════════════

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(30), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    asset_type = Column(Enum(AssetType, native_enum=False, length=20), nullable=False)
    country = Column(String(10), nullable=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    company = relationship("Company", back_populates="assets")
    prices = relationship("PriceDaily", back_populates="asset", cascade="all, delete-orphan")
    financial_statements = relationship("FinancialStatement", back_populates="asset", cascade="all, delete-orphan")
    valuation_multiples = relationship("ValuationMultiple", back_populates="asset", cascade="all, delete-orphan")
    ingestion_logs = relationship("IngestionLog", back_populates="asset", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_assets_type_country", "asset_type", "country"),
    )

    def __repr__(self):
        return f"<Asset(symbol={self.symbol}, type={self.asset_type})>"


# ══════════════════════════════════════════════════════════
#  TABELA 5: trading_calendar
# ══════════════════════════════════════════════════════════

class TradingCalendar(Base):
    __tablename__ = "trading_calendar"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    market = Column(String(20), nullable=False)  # B3, NYSE, etc.
    is_open = Column(Boolean, default=True)
    note = Column(String(200), nullable=True)

    __table_args__ = (
        UniqueConstraint("date", "market", name="uq_calendar_date_market"),
    )

    def __repr__(self):
        return f"<TradingCalendar(date={self.date}, market={self.market}, open={self.is_open})>"


# ══════════════════════════════════════════════════════════
#  TABELA 6: prices_daily  (a mais populada)
# ══════════════════════════════════════════════════════════

class PriceDaily(Base):
    __tablename__ = "prices_daily"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    open = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    close = Column(Float, nullable=True)
    adj_close = Column(Float, nullable=True)
    volume = Column(Float, nullable=True)  # Float para volumes gigantes de crypto
    change_pct = Column(Float, nullable=True)  # variação percentual diária

    # Relacionamento
    asset = relationship("Asset", back_populates="prices")

    __table_args__ = (
        UniqueConstraint("asset_id", "date", name="uq_price_asset_date"),
        Index("ix_prices_asset_date", "asset_id", "date"),
    )

    def __repr__(self):
        return f"<PriceDaily(asset_id={self.asset_id}, date={self.date}, close={self.close})>"


# ══════════════════════════════════════════════════════════
#  TABELA 7: financial_statements
# ══════════════════════════════════════════════════════════

class FinancialStatement(Base):
    __tablename__ = "financial_statements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    period_type = Column(Enum(PeriodType, native_enum=False, length=20), nullable=False)
    period_end = Column(Date, nullable=False)

    # DRE
    revenue = Column(Numeric(20, 2), nullable=True)
    gross_profit = Column(Numeric(20, 2), nullable=True)
    operating_income = Column(Numeric(20, 2), nullable=True)
    net_income = Column(Numeric(20, 2), nullable=True)
    ebitda = Column(Numeric(20, 2), nullable=True)

    # Balanço
    total_assets = Column(Numeric(20, 2), nullable=True)
    total_liabilities = Column(Numeric(20, 2), nullable=True)
    total_equity = Column(Numeric(20, 2), nullable=True)
    cash_and_equivalents = Column(Numeric(20, 2), nullable=True)
    total_debt = Column(Numeric(20, 2), nullable=True)

    # Fluxo de Caixa
    operating_cash_flow = Column(Numeric(20, 2), nullable=True)
    capex = Column(Numeric(20, 2), nullable=True)
    free_cash_flow = Column(Numeric(20, 2), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacionamento
    asset = relationship("Asset", back_populates="financial_statements")

    __table_args__ = (
        UniqueConstraint("asset_id", "period_type", "period_end", name="uq_financial_statement"),
        Index("ix_financials_asset_period", "asset_id", "period_end"),
    )

    def __repr__(self):
        return f"<FinancialStatement(asset_id={self.asset_id}, period={self.period_end})>"


# ══════════════════════════════════════════════════════════
#  TABELA 8: valuation_multiples
# ══════════════════════════════════════════════════════════

class ValuationMultiple(Base):
    __tablename__ = "valuation_multiples"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)

    pe_ratio = Column(Float, nullable=True)        # P/E
    pb_ratio = Column(Float, nullable=True)        # P/B (Price/Book)
    ps_ratio = Column(Float, nullable=True)        # P/S (Price/Sales)
    ev_ebitda = Column(Float, nullable=True)       # EV/EBITDA
    dividend_yield = Column(Float, nullable=True)  # Dividend Yield %
    roe = Column(Float, nullable=True)             # Return on Equity %
    roa = Column(Float, nullable=True)             # Return on Assets %
    market_cap = Column(Numeric(20, 2), nullable=True)
    enterprise_value = Column(Numeric(20, 2), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacionamento
    asset = relationship("Asset", back_populates="valuation_multiples")

    __table_args__ = (
        UniqueConstraint("asset_id", "date", name="uq_valuation_asset_date"),
    )

    def __repr__(self):
        return f"<ValuationMultiple(asset_id={self.asset_id}, date={self.date})>"


# ══════════════════════════════════════════════════════════
#  TABELA 9: ingestion_log
# ══════════════════════════════════════════════════════════

class IngestionLog(Base):
    __tablename__ = "ingestion_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    status = Column(Enum(IngestionStatus, native_enum=False, length=20), nullable=False)
    rows_inserted = Column(Integer, default=0)
    rows_updated = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    data_type = Column(String(50), default="prices")  # prices, fundamentals, valuation

    # Relacionamento
    asset = relationship("Asset", back_populates="ingestion_logs")

    __table_args__ = (
        Index("ix_ingestion_log_status", "status"),
        Index("ix_ingestion_log_asset_started", "asset_id", "started_at"),
    )

    def __repr__(self):
        return f"<IngestionLog(asset_id={self.asset_id}, status={self.status})>"
