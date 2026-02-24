"""
FIE Phase 1 — Database Models
TradingView Alert Intelligence Dashboard
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

DATABASE_URL = os.getenv("DATABASE_URL", os.getenv("FIE_DATABASE_URL", "sqlite:///fie_phase1.db"))

# Railway Postgres uses postgres:// but SQLAlchemy needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLite needs check_same_thread=False; PostgreSQL does not
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ─── Enums ─────────────────────────────────────────────

class AlertStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    EXPIRED = "EXPIRED"

class AlertType(str, enum.Enum):
    ABSOLUTE = "ABSOLUTE"       # Single index/stock alert
    RELATIVE = "RELATIVE"       # Ratio/spread of two indices

class ActionCall(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"
    OVERBOUGHT = "OVERBOUGHT"
    OVERSOLD = "OVERSOLD"
    EXIT = "EXIT"
    ACCUMULATE = "ACCUMULATE"
    REDUCE = "REDUCE"
    SWITCH = "SWITCH"
    WATCH = "WATCH"

class SignalDirection(str, enum.Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


# ─── TradingView Alert (Raw Ingestion) ─────────────────

class TradingViewAlert(Base):
    """Raw webhook data from TradingView — stores everything we receive"""
    __tablename__ = "tradingview_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # ─ TradingView Core Fields ─
    ticker = Column(String(50), nullable=True)              # {{ticker}}
    exchange = Column(String(30), nullable=True)             # {{exchange}}
    interval = Column(String(20), nullable=True)             # {{interval}} - e.g., "1D", "4H", "1W"
    
    # ─ Price Data at Alert Time ─
    price_open = Column(Float, nullable=True)                # {{open}}
    price_high = Column(Float, nullable=True)                # {{high}}
    price_low = Column(Float, nullable=True)                 # {{low}}
    price_close = Column(Float, nullable=True)               # {{close}}
    price_at_alert = Column(Float, nullable=True)            # Current price when alert fired
    volume = Column(Float, nullable=True)                    # {{volume}}
    
    # ─ Time Data ─
    time_utc = Column(String(50), nullable=True)             # {{time}}
    timenow_utc = Column(String(50), nullable=True)          # {{timenow}}
    
    # ─ Alert Metadata ─
    alert_name = Column(String(200), nullable=True)          # Name set by FM in TradingView
    alert_message = Column(Text, nullable=True)              # Full alert message body
    alert_condition = Column(String(500), nullable=True)     # The condition that triggered
    
    # ─ Indicator Values (from alert message JSON) ─
    indicator_values = Column(JSON, nullable=True)           # All indicator data as JSON
    
    # ─ For Relative Alerts (Index A / Index B) ─
    alert_type = Column(SQLEnum(AlertType), default=AlertType.ABSOLUTE)
    numerator_ticker = Column(String(50), nullable=True)     # For relative: Index A
    denominator_ticker = Column(String(50), nullable=True)   # For relative: Index B
    numerator_price = Column(Float, nullable=True)
    denominator_price = Column(Float, nullable=True)
    ratio_value = Column(Float, nullable=True)               # A/B ratio at alert time
    
    # ─ Signal Interpretation ─
    signal_direction = Column(SQLEnum(SignalDirection), nullable=True)
    signal_strength = Column(Float, nullable=True)           # 0-100
    signal_summary = Column(Text, nullable=True)             # Human-readable interpretation
    
    # ─ Sector Mapping ─
    sector = Column(String(100), nullable=True)
    asset_class = Column(String(50), nullable=True)          # EQUITY, DEBT, COMMODITY, CURRENCY, INDEX
    
    # ─ Raw Payload ─
    raw_payload = Column(JSON, nullable=True)                # Complete raw webhook JSON
    
    # ─ Processing Status ─
    status = Column(SQLEnum(AlertStatus), default=AlertStatus.PENDING)
    processed = Column(Boolean, default=False)
    
    # ─ Timestamps ─
    received_at = Column(DateTime, default=func.now())
    
    # ─ Relationships ─
    action = relationship("AlertAction", back_populates="alert", uselist=False)
    performance_records = relationship("AlertPerformance", back_populates="alert")

    __table_args__ = (
        Index('idx_alert_status', 'status'),
        Index('idx_alert_received', 'received_at'),
        Index('idx_alert_ticker', 'ticker'),
        Index('idx_alert_sector', 'sector'),
    )


# ─── Fund Manager Action on Alert ──────────────────────

class AlertAction(Base):
    """Fund Manager's decision and actionable calls on each alert"""
    __tablename__ = "alert_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(Integer, ForeignKey("tradingview_alerts.id"), unique=True, nullable=False)
    
    # ─ FM Decision ─
    decision = Column(SQLEnum(AlertStatus), nullable=False)  # APPROVED or DENIED
    decision_at = Column(DateTime, default=func.now())
    decision_by = Column(String(100), default="Fund Manager")
    
    # ─ Primary Actionable (on the alert ticker / numerator) ─
    primary_call = Column(SQLEnum(ActionCall), nullable=True)
    primary_ticker = Column(String(50), nullable=True)
    primary_notes = Column(Text, nullable=True)
    primary_target_price = Column(Float, nullable=True)
    primary_stop_loss = Column(Float, nullable=True)
    
    # ─ Secondary Actionable (for relative alerts — on the denominator) ─
    secondary_call = Column(SQLEnum(ActionCall), nullable=True)
    secondary_ticker = Column(String(50), nullable=True)
    secondary_notes = Column(Text, nullable=True)
    secondary_target_price = Column(Float, nullable=True)
    secondary_stop_loss = Column(Float, nullable=True)
    
    # ─ Conviction & Context ─
    conviction = Column(String(20), nullable=True)           # HIGH, MEDIUM, LOW
    fm_remarks = Column(Text, nullable=True)                 # Free-form notes
    
    # ─ Price at Decision Time ─
    price_at_decision = Column(Float, nullable=True)         # Numerator/main ticker
    secondary_price_at_decision = Column(Float, nullable=True)
    
    # ─ Timestamps ─
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # ─ Relationship ─
    alert = relationship("TradingViewAlert", back_populates="action")


# ─── Performance Tracking ──────────────────────────────

class AlertPerformance(Base):
    """Daily performance snapshot for approved alerts"""
    __tablename__ = "alert_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(Integer, ForeignKey("tradingview_alerts.id"), nullable=False)
    
    # ─ Which ticker this tracks ─
    ticker = Column(String(50), nullable=False)
    is_primary = Column(Boolean, default=True)               # True = numerator/main, False = denominator
    
    # ─ Reference Price (at approval) ─
    reference_price = Column(Float, nullable=False)
    reference_date = Column(DateTime, nullable=False)
    
    # ─ Current Snapshot ─
    current_price = Column(Float, nullable=True)
    snapshot_date = Column(DateTime, default=func.now())
    
    # ─ Returns ─
    return_absolute = Column(Float, nullable=True)           # Current - Reference
    return_pct = Column(Float, nullable=True)                # (Current - Reference) / Reference * 100
    
    # ─ Period Returns ─
    return_1d = Column(Float, nullable=True)
    return_1w = Column(Float, nullable=True)
    return_1m = Column(Float, nullable=True)
    return_3m = Column(Float, nullable=True)
    return_6m = Column(Float, nullable=True)
    return_12m = Column(Float, nullable=True)
    
    # ─ High/Low since approval ─
    high_since = Column(Float, nullable=True)
    low_since = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    
    # ─ Relationship ─
    alert = relationship("TradingViewAlert", back_populates="performance_records")

    __table_args__ = (
        Index('idx_perf_alert', 'alert_id'),
        Index('idx_perf_ticker', 'ticker'),
        Index('idx_perf_date', 'snapshot_date'),
    )


# ─── Sector/Index Mapping Reference ────────────────────

class InstrumentMap(Base):
    """Reference table mapping tickers to sectors and asset classes"""
    __tablename__ = "instrument_map"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=True)
    sector = Column(String(100), nullable=True)
    asset_class = Column(String(50), nullable=True)
    exchange = Column(String(30), nullable=True)
    is_index = Column(Boolean, default=False)
    related_etf = Column(String(50), nullable=True)          # Related ETF if index
    components = Column(JSON, nullable=True)                  # Top holdings/components
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


# ─── Initialize Database ───────────────────────────────

def init_db():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)
    _seed_instrument_map()
    print("✅ Database initialized")


def get_db():
    """Dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _seed_instrument_map():
    """Seed common Indian market instruments"""
    db = SessionLocal()
    if db.query(InstrumentMap).count() > 0:
        db.close()
        return
    
    instruments = [
        # Major Indices
        {"ticker": "NIFTY", "name": "Nifty 50", "sector": "Broad Market", "asset_class": "INDEX", "exchange": "NSE", "is_index": True, "related_etf": "NIFTYBEES.NS"},
        {"ticker": "BANKNIFTY", "name": "Bank Nifty", "sector": "Banking", "asset_class": "INDEX", "exchange": "NSE", "is_index": True, "related_etf": "BANKBEES.NS"},
        {"ticker": "NIFTYIT", "name": "Nifty IT", "sector": "Information Technology", "asset_class": "INDEX", "exchange": "NSE", "is_index": True},
        {"ticker": "NIFTYPHARMA", "name": "Nifty Pharma", "sector": "Pharma & Healthcare", "asset_class": "INDEX", "exchange": "NSE", "is_index": True},
        {"ticker": "NIFTYFMCG", "name": "Nifty FMCG", "sector": "FMCG", "asset_class": "INDEX", "exchange": "NSE", "is_index": True},
        {"ticker": "NIFTYAUTO", "name": "Nifty Auto", "sector": "Automobile", "asset_class": "INDEX", "exchange": "NSE", "is_index": True},
        {"ticker": "NIFTYMETAL", "name": "Nifty Metal", "sector": "Metal & Mining", "asset_class": "INDEX", "exchange": "NSE", "is_index": True},
        {"ticker": "NIFTYREALTY", "name": "Nifty Realty", "sector": "Real Estate", "asset_class": "INDEX", "exchange": "NSE", "is_index": True},
        {"ticker": "NIFTYENERGY", "name": "Nifty Energy", "sector": "Energy", "asset_class": "INDEX", "exchange": "NSE", "is_index": True},
        {"ticker": "NIFTYPSUBANK", "name": "Nifty PSU Bank", "sector": "Banking", "asset_class": "INDEX", "exchange": "NSE", "is_index": True},
        {"ticker": "NIFTYPVTBANK", "name": "Nifty Pvt Bank", "sector": "Banking", "asset_class": "INDEX", "exchange": "NSE", "is_index": True},
        {"ticker": "NIFTYMIDCAP", "name": "Nifty Midcap 150", "sector": "Broad Market", "asset_class": "INDEX", "exchange": "NSE", "is_index": True},
        {"ticker": "NIFTYSMALLCAP", "name": "Nifty Smallcap 250", "sector": "Broad Market", "asset_class": "INDEX", "exchange": "NSE", "is_index": True},
        {"ticker": "NIFTY500", "name": "Nifty 500", "sector": "Broad Market", "asset_class": "INDEX", "exchange": "NSE", "is_index": True},
        {"ticker": "NIFTYINFRA", "name": "Nifty Infra", "sector": "Infrastructure", "asset_class": "INDEX", "exchange": "NSE", "is_index": True},
        {"ticker": "NIFTYMEDIA", "name": "Nifty Media", "sector": "Media & Entertainment", "asset_class": "INDEX", "exchange": "NSE", "is_index": True},
        # Commodities
        {"ticker": "GOLD", "name": "Gold", "sector": "Commodities", "asset_class": "COMMODITY", "exchange": "MCX"},
        {"ticker": "SILVER", "name": "Silver", "sector": "Commodities", "asset_class": "COMMODITY", "exchange": "MCX"},
        {"ticker": "CRUDEOIL", "name": "Crude Oil", "sector": "Commodities", "asset_class": "COMMODITY", "exchange": "MCX"},
        # Currency
        {"ticker": "USDINR", "name": "USD/INR", "sector": "Currency", "asset_class": "CURRENCY", "exchange": "NSE"},
    ]
    
    for inst in instruments:
        db.add(InstrumentMap(**inst))
    
    db.commit()
    db.close()
    print("✅ Instrument map seeded")


if __name__ == "__main__":
    init_db()
