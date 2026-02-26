"""
FIE v3 — Database Models
Jhaveri Intelligence Platform
Simplified: webhook data only, FM actions, Claude chart analysis
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Text, DateTime, Boolean, JSON,
    Enum as SQLEnum, ForeignKey, Index
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
import os

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
    )


# ─── Init ───────────────────────────────────────────────

def init_db():
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    print("FIE v3 database initialized")


def _run_migrations():
    """Idempotent column additions."""
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
    ]
    for sql in migrations:
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
