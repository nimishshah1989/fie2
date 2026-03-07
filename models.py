"""
FIE v3 — Database Models
Jhaveri Intelligence Platform
Simplified: webhook data only, FM actions, Claude chart analysis
"""

import enum
import os

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func

DATABASE_URL = os.getenv("DATABASE_URL", os.getenv("FIE_DATABASE_URL", "sqlite:///fie_v3.db"))
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class AlertStatus(str, enum.Enum):
    PENDING   = "PENDING"
    APPROVED  = "APPROVED"
    DENIED    = "DENIED"


class ActionPriority(str, enum.Enum):
    IMMEDIATELY    = "IMMEDIATELY"
    WITHIN_A_WEEK  = "WITHIN_A_WEEK"
    WITHIN_A_MONTH = "WITHIN_A_MONTH"


# ─── Raw TradingView Alert ──────────────────────────────

class TradingViewAlert(Base):
    __tablename__ = "tradingview_alerts"

    id          = Column(Integer, primary_key=True, autoincrement=True)

    # From webhook {{...}} variables
    ticker      = Column(String(50),  nullable=True)
    exchange    = Column(String(30),  nullable=True)
    interval    = Column(String(20),  nullable=True)
    time_utc    = Column(String(50),  nullable=True)   # {{time}}
    timenow_utc = Column(String(50),  nullable=True)   # {{timenow}}

    # OHLCV
    price_open  = Column(Float, nullable=True)
    price_high  = Column(Float, nullable=True)
    price_low   = Column(Float, nullable=True)
    price_close    = Column(Float, nullable=True)
    price_at_alert = Column(Float, nullable=True)   # = price_close at trigger time
    volume      = Column(Float, nullable=True)

    # {{strategy.order.alert_message}} — the "data" field
    alert_data  = Column(Text, nullable=True)

    # Derived from alert_data parsing (optional best-effort)
    alert_name  = Column(String(200), nullable=True)   # parsed from data or defaulted
    signal_direction = Column(String(20), nullable=True)  # BULLISH / BEARISH / NEUTRAL

    raw_payload = Column(JSON, nullable=True)
    status      = Column(SQLEnum(AlertStatus), default=AlertStatus.PENDING)
    received_at = Column(DateTime, default=func.now())

    action = relationship("AlertAction", back_populates="alert", uselist=False)

    __table_args__ = (
        Index('idx_alert_status',   'status'),
        Index('idx_alert_received', 'received_at'),
        Index('idx_alert_ticker',   'ticker'),
    )


# ─── Fund Manager Action ────────────────────────────────

class AlertAction(Base):
    __tablename__ = "alert_actions"

    id       = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(Integer, ForeignKey("tradingview_alerts.id"), unique=True, nullable=False)

    decision     = Column(SQLEnum(AlertStatus), nullable=False)
    decision_at  = Column(DateTime, default=func.now())

    # Action (mandatory if APPROVED)
    action_call  = Column(String(50),  nullable=True)   # BUY / SELL / RATIO / etc.

    # For ratio / relative trades
    is_ratio     = Column(Boolean, default=False)
    ratio_long   = Column(String(100), nullable=True)   # "LONG 60% RELIANCE"
    ratio_short  = Column(String(100), nullable=True)   # "SHORT 40% HDFCBANK"
    ratio_numerator_ticker   = Column(String(50), nullable=True)   # proxy ticker for numerator
    ratio_denominator_ticker = Column(String(50), nullable=True)   # proxy ticker for denominator

    # Priority
    priority     = Column(SQLEnum(ActionPriority), nullable=True)

    # Chart image (base64)
    chart_image_b64 = Column(Text, nullable=True)

    # Claude's analysis of the chart image (8 bullet points)
    chart_analysis  = Column(Text, nullable=True)   # JSON array of strings

    # FM commentary
    fm_notes = Column(Text, nullable=True)

    # Trade parameters (FM suggested)
    entry_price_low   = Column(Float, nullable=True)
    entry_price_high  = Column(Float, nullable=True)
    stop_loss         = Column(Float, nullable=True)
    target_price      = Column(Float, nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    alert = relationship("TradingViewAlert", back_populates="action")


# ─── Index Prices (EOD) ────────────────────────────────

class IndexPrice(Base):
    __tablename__ = "index_prices"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    date        = Column(String(10), nullable=False)   # "YYYY-MM-DD"
    index_name  = Column(String(50), nullable=False)   # e.g. "NIFTY", "BANKNIFTY"
    close_price = Column(Float, nullable=True)
    open_price  = Column(Float, nullable=True)
    high_price  = Column(Float, nullable=True)
    low_price   = Column(Float, nullable=True)
    volume      = Column(Float, nullable=True)
    fetched_at  = Column(DateTime, default=func.now())

    __table_args__ = (
        Index('idx_indexprice_date_name', 'date', 'index_name', unique=True),
        Index('idx_indexprice_name', 'index_name'),
        # Standalone date index for date-range queries (min/max date, date filtering)
        Index('idx_indexprice_date', 'date'),
    )


# ─── Init ───────────────────────────────────────────────

def init_db():
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    print("FIE v3 database initialized")


def _run_migrations():
    """Idempotent column additions and index creation for existing databases."""
    db = SessionLocal()
    migrations = [
        "ALTER TABLE alert_actions ADD COLUMN is_ratio BOOLEAN DEFAULT FALSE",
        "ALTER TABLE alert_actions ADD COLUMN ratio_long VARCHAR(100)",
        "ALTER TABLE alert_actions ADD COLUMN ratio_short VARCHAR(100)",
        "ALTER TABLE alert_actions ADD COLUMN priority VARCHAR(30)",
        "ALTER TABLE alert_actions ADD COLUMN action_call VARCHAR(50)",
        "ALTER TABLE alert_actions ADD COLUMN chart_analysis TEXT",
        "ALTER TABLE tradingview_alerts ADD COLUMN price_at_alert FLOAT",
        "ALTER TABLE alert_actions ADD COLUMN ratio_numerator_ticker VARCHAR(50)",
        "ALTER TABLE alert_actions ADD COLUMN ratio_denominator_ticker VARCHAR(50)",
        "ALTER TABLE alert_actions ADD COLUMN fm_notes TEXT",
        "ALTER TABLE alert_actions ADD COLUMN entry_price_low FLOAT",
        "ALTER TABLE alert_actions ADD COLUMN entry_price_high FLOAT",
        "ALTER TABLE alert_actions ADD COLUMN stop_loss FLOAT",
        "ALTER TABLE alert_actions ADD COLUMN target_price FLOAT",
        "ALTER TABLE model_portfolios ADD COLUMN inception_date VARCHAR(10)",
        "ALTER TABLE microbaskets ADD COLUMN portfolio_size FLOAT",
        "ALTER TABLE portfolio_holdings ADD COLUMN yf_symbol_override VARCHAR(50)",
        "ALTER TABLE microbasket_constituents ADD COLUMN buy_price FLOAT",
        "ALTER TABLE microbasket_constituents ADD COLUMN quantity INTEGER",
        "ALTER TABLE model_portfolios ADD COLUMN portfolio_type VARCHAR(20) DEFAULT 'manual'",
        "ALTER TABLE model_portfolios ADD COLUMN ucc_code VARCHAR(50)",
        "ALTER TABLE pms_nav_daily ADD COLUMN etf_investment FLOAT",
        "ALTER TABLE pms_nav_daily ADD COLUMN unit_nav FLOAT",
    ]
    for sql in migrations:
        try:
            from sqlalchemy import text
            db.execute(text(sql))
            db.commit()
        except Exception:
            db.rollback()

    # Index migrations — CREATE INDEX IF NOT EXISTS for existing databases
    index_migrations = [
        "CREATE INDEX IF NOT EXISTS idx_indexprice_date ON index_prices (date)",
        "CREATE INDEX IF NOT EXISTS idx_pms_nav_date ON pms_nav_daily (date)",
        "CREATE INDEX IF NOT EXISTS idx_metric_portfolio ON portfolio_metrics (portfolio_id)",
        "CREATE INDEX IF NOT EXISTS idx_metric_portfolio_period ON portfolio_metrics (portfolio_id, period)",
    ]
    for sql in index_migrations:
        try:
            from sqlalchemy import text
            db.execute(text(sql))
            db.commit()
        except Exception:
            db.rollback()

    # Seed inception dates for existing portfolios (idempotent — only sets if NULL)
    seed_dates = [
        ("UPDATE model_portfolios SET inception_date = '2021-08-02' WHERE id = 1 AND inception_date IS NULL"),
        ("UPDATE model_portfolios SET inception_date = '2020-09-28' WHERE id = 2 AND inception_date IS NULL"),
    ]
    for sql in seed_dates:
        try:
            from sqlalchemy import text
            db.execute(text(sql))
            db.commit()
        except Exception:
            db.rollback()

    db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
#  MODEL PORTFOLIO TABLES (added for portfolio management)
# ═══════════════════════════════════════════════════════════

class PortfolioStatus(str, enum.Enum):
    ACTIVE   = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class TransactionType(str, enum.Enum):
    BUY  = "BUY"
    SELL = "SELL"


class ModelPortfolio(Base):
    __tablename__ = "model_portfolios"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    benchmark   = Column(String(50), default="NIFTY")
    status      = Column(SQLEnum(PortfolioStatus), default=PortfolioStatus.ACTIVE)
    inception_date = Column(String(10), nullable=True)
    portfolio_type = Column(String(20), default="manual")  # 'manual' or 'pms'
    ucc_code    = Column(String(50), nullable=True)        # e.g. 'BJ53' for PMS filtering
    tenant_id   = Column(String(50), default="jhaveri")
    created_at  = Column(DateTime, default=func.now())
    updated_at  = Column(DateTime, default=func.now(), onupdate=func.now())

    holdings     = relationship("PortfolioHolding", back_populates="portfolio", lazy="dynamic")
    transactions = relationship("PortfolioTransaction", back_populates="portfolio", lazy="dynamic")
    nav_history  = relationship("PortfolioNAV", back_populates="portfolio", lazy="dynamic")

    __table_args__ = (
        Index('idx_portfolio_tenant', 'tenant_id'),
        Index('idx_portfolio_status', 'status'),
    )


class PortfolioHolding(Base):
    __tablename__ = "portfolio_holdings"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id  = Column(Integer, ForeignKey("model_portfolios.id"), nullable=False)
    ticker        = Column(String(50), nullable=False)
    exchange      = Column(String(20), default="NSE")
    quantity      = Column(Integer, nullable=False, default=0)
    avg_cost      = Column(Float, nullable=False, default=0.0)
    total_cost    = Column(Float, nullable=False, default=0.0)
    sector        = Column(String(100), nullable=True)
    yf_symbol_override = Column(String(50), nullable=True)
    added_at      = Column(DateTime, default=func.now())
    updated_at    = Column(DateTime, default=func.now(), onupdate=func.now())

    portfolio = relationship("ModelPortfolio", back_populates="holdings")

    __table_args__ = (
        Index('idx_holding_portfolio_ticker', 'portfolio_id', 'ticker', unique=True),
        Index('idx_holding_portfolio', 'portfolio_id'),
    )


class PortfolioTransaction(Base):
    __tablename__ = "portfolio_transactions"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id  = Column(Integer, ForeignKey("model_portfolios.id"), nullable=False)
    ticker        = Column(String(50), nullable=False)
    exchange      = Column(String(20), default="NSE")
    txn_type      = Column(SQLEnum(TransactionType), nullable=False)
    quantity      = Column(Integer, nullable=False)
    price         = Column(Float, nullable=False)
    total_value   = Column(Float, nullable=False)
    txn_date      = Column(String(10), nullable=False)
    notes         = Column(Text, nullable=True)
    created_at    = Column(DateTime, default=func.now())

    realized_pnl       = Column(Float, nullable=True)
    realized_pnl_pct   = Column(Float, nullable=True)
    cost_basis_at_sell  = Column(Float, nullable=True)

    portfolio = relationship("ModelPortfolio", back_populates="transactions")

    __table_args__ = (
        Index('idx_txn_portfolio', 'portfolio_id'),
        Index('idx_txn_portfolio_date', 'portfolio_id', 'txn_date'),
        Index('idx_txn_ticker', 'ticker'),
    )


class PortfolioNAV(Base):
    __tablename__ = "portfolio_nav"

    id                      = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id            = Column(Integer, ForeignKey("model_portfolios.id"), nullable=False)
    date                    = Column(String(10), nullable=False)
    total_value             = Column(Float, nullable=False)
    total_cost              = Column(Float, nullable=False)
    unrealized_pnl          = Column(Float, nullable=True)
    realized_pnl_cumulative = Column(Float, nullable=True)
    num_holdings            = Column(Integer, nullable=True)
    computed_at             = Column(DateTime, default=func.now())

    portfolio = relationship("ModelPortfolio", back_populates="nav_history")

    __table_args__ = (
        Index('idx_nav_portfolio_date', 'portfolio_id', 'date', unique=True),
        Index('idx_nav_portfolio', 'portfolio_id'),
    )


# ═══════════════════════════════════════════════════════════
#  MICROBASKET TABLES (custom stock baskets with ratio analysis)
# ═══════════════════════════════════════════════════════════

class BasketStatus(str, enum.Enum):
    ACTIVE   = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class Microbasket(Base):
    __tablename__ = "microbaskets"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    name           = Column(String(100), nullable=False, unique=True)
    slug           = Column(String(100), nullable=False, unique=True)   # "MB_HEALTHCARE"
    description    = Column(Text, nullable=True)
    benchmark      = Column(String(50), default="NIFTY")
    portfolio_size = Column(Float, nullable=True)   # Total investment in INR (e.g. 500000)
    status         = Column(SQLEnum(BasketStatus), default=BasketStatus.ACTIVE)
    created_at     = Column(DateTime, default=func.now())
    updated_at     = Column(DateTime, default=func.now(), onupdate=func.now())

    constituents = relationship(
        "MicrobasketConstituent", back_populates="basket",
        cascade="all, delete-orphan",
    )


class IndexConstituent(Base):
    """Stores constituents of NSE sector indices for the recommendation engine."""
    __tablename__ = "index_constituents"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    index_name   = Column(String(100), nullable=False)   # e.g. "NIFTY BANK"
    ticker       = Column(String(50), nullable=False)
    company_name = Column(String(200), nullable=True)
    weight_pct   = Column(Float, nullable=True)
    last_price   = Column(Float, nullable=True)
    fetched_at   = Column(DateTime, default=func.now())

    __table_args__ = (
        Index('idx_constituent_index_ticker', 'index_name', 'ticker', unique=True),
    )


class MicrobasketConstituent(Base):
    __tablename__ = "microbasket_constituents"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    basket_id    = Column(Integer, ForeignKey("microbaskets.id"), nullable=False)
    ticker       = Column(String(50), nullable=False)
    company_name = Column(String(200), nullable=True)
    weight_pct   = Column(Float, nullable=False)   # e.g. 20.0 = 20%
    buy_price    = Column(Float, nullable=True)     # initial buy price per share
    quantity     = Column(Integer, nullable=True)    # number of shares purchased
    added_at     = Column(DateTime, default=func.now())

    basket = relationship("Microbasket", back_populates="constituents")

    __table_args__ = (
        Index('idx_constituent_basket_ticker', 'basket_id', 'ticker', unique=True),
    )


# ═══════════════════════════════════════════════════════════
#  PMS (Portfolio Management Service) TABLES
# ═══════════════════════════════════════════════════════════

class PmsNavDaily(Base):
    """Daily NAV record from PMS broker NAV report."""
    __tablename__ = "pms_nav_daily"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id   = Column(Integer, ForeignKey("model_portfolios.id"), nullable=False)
    date           = Column(Date, nullable=False)
    corpus         = Column(Float, nullable=True)
    equity_holding = Column(Float, nullable=True)
    etf_investment = Column(Float, nullable=True)
    cash_equivalent = Column(Float, nullable=True)
    bank_balance   = Column(Float, nullable=True)
    nav            = Column(Float, nullable=False)
    unit_nav       = Column(Float, nullable=True)   # TWR-adjusted index (base 100)
    liquidity_pct  = Column(Float, nullable=True)
    high_water_mark = Column(Float, nullable=True)
    created_at     = Column(DateTime, default=func.now())

    __table_args__ = (
        UniqueConstraint('portfolio_id', 'date', name='uq_pms_nav_portfolio_date'),
        Index('idx_pms_nav_portfolio_date', 'portfolio_id', 'date'),
        # Standalone date index for date-range queries across all portfolios
        Index('idx_pms_nav_date', 'date'),
    )


class PmsTransaction(Base):
    """Individual buy/sell transaction from PMS broker transaction log."""
    __tablename__ = "pms_transactions"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id   = Column(Integer, ForeignKey("model_portfolios.id"), nullable=False)
    date           = Column(Date, nullable=False)
    script         = Column(String(100), nullable=False)
    exchange       = Column(String(20), nullable=True)
    stno           = Column(String(50), nullable=True)
    # Buy columns
    buy_qty        = Column(Float, nullable=True)
    buy_rate       = Column(Float, nullable=True)
    buy_gst        = Column(Float, nullable=True)
    buy_other_charges = Column(Float, nullable=True)
    buy_stt        = Column(Float, nullable=True)
    buy_cost_rate  = Column(Float, nullable=True)
    buy_amt_with_cost = Column(Float, nullable=True)
    buy_amt_without_stt = Column(Float, nullable=True)
    # Sale columns
    sale_qty       = Column(Float, nullable=True)
    sale_rate      = Column(Float, nullable=True)
    sale_gst       = Column(Float, nullable=True)
    sale_stt       = Column(Float, nullable=True)
    sale_other_charges = Column(Float, nullable=True)
    sale_cost_rate = Column(Float, nullable=True)
    sale_amt_with_cost = Column(Float, nullable=True)
    sale_amt_without_stt = Column(Float, nullable=True)

    __table_args__ = (
        Index('idx_pms_txn_portfolio_date', 'portfolio_id', 'date'),
    )


class PortfolioMetric(Base):
    """Computed risk/return metrics for a portfolio over a given period."""
    __tablename__ = "portfolio_metrics"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id    = Column(Integer, ForeignKey("model_portfolios.id"), nullable=False)
    as_of_date      = Column(Date, nullable=False)
    period          = Column(String(10), nullable=False)  # 1M, 3M, 6M, 1Y, 3Y, 5Y, SI
    start_date      = Column(Date, nullable=True)
    end_date        = Column(Date, nullable=True)
    start_nav       = Column(Float, nullable=True)
    end_nav         = Column(Float, nullable=True)
    absolute_return = Column(Float, nullable=True)
    return_pct      = Column(Float, nullable=True)
    cagr_pct        = Column(Float, nullable=True)
    volatility_pct  = Column(Float, nullable=True)
    max_drawdown_pct = Column(Float, nullable=True)
    sharpe_ratio    = Column(Float, nullable=True)
    sortino_ratio   = Column(Float, nullable=True)
    calmar_ratio    = Column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint('portfolio_id', 'as_of_date', 'period',
                         name='uq_metric_portfolio_date_period'),
        # Index for portfolio lookups and period filtering
        Index('idx_metric_portfolio', 'portfolio_id'),
        Index('idx_metric_portfolio_period', 'portfolio_id', 'period'),
    )


class DrawdownEvent(Base):
    """Peak-to-trough drawdown events for a portfolio."""
    __tablename__ = "drawdown_events"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id   = Column(Integer, ForeignKey("model_portfolios.id"), nullable=False)
    peak_date      = Column(Date, nullable=False)
    peak_nav       = Column(Float, nullable=False)
    trough_date    = Column(Date, nullable=True)
    trough_nav     = Column(Float, nullable=True)
    drawdown_pct   = Column(Float, nullable=True)
    duration_days  = Column(Integer, nullable=True)
    recovery_date  = Column(Date, nullable=True)
    recovery_days  = Column(Integer, nullable=True)
    status         = Column(String(20), default="underwater")  # 'recovered' or 'underwater'

    __table_args__ = (
        Index('idx_drawdown_portfolio', 'portfolio_id'),
    )
