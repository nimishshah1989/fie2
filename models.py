"""
FIE Phase 2 — Database Models
Jhaveri Intelligence Platform
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

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ─── Enums ─────────────────────────────────────────────

class AlertStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    REVIEW_LATER = "REVIEW_LATER"
    EXPIRED = "EXPIRED"

class AlertType(str, enum.Enum):
    ABSOLUTE = "ABSOLUTE"
    RELATIVE = "RELATIVE"

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
    __tablename__ = "tradingview_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    ticker = Column(String(50), nullable=True)
    exchange = Column(String(30), nullable=True)
    interval = Column(String(20), nullable=True)
    
    price_open = Column(Float, nullable=True)
    price_high = Column(Float, nullable=True)
    price_low = Column(Float, nullable=True)
    price_close = Column(Float, nullable=True)
    price_at_alert = Column(Float, nullable=True)
    volume = Column(Float, nullable=True)
    
    time_utc = Column(String(50), nullable=True)
    timenow_utc = Column(String(50), nullable=True)
    
    alert_name = Column(String(200), nullable=True)
    alert_message = Column(Text, nullable=True)
    alert_condition = Column(String(500), nullable=True)
    
    indicator_values = Column(JSON, nullable=True)
    
    alert_type = Column(SQLEnum(AlertType), default=AlertType.ABSOLUTE)
    numerator_ticker = Column(String(50), nullable=True)
    denominator_ticker = Column(String(50), nullable=True)
    numerator_price = Column(Float, nullable=True)
    denominator_price = Column(Float, nullable=True)
    ratio_value = Column(Float, nullable=True)
    
    signal_direction = Column(SQLEnum(SignalDirection), nullable=True)
    signal_strength = Column(Float, nullable=True)
    signal_summary = Column(Text, nullable=True)
    
    sector = Column(String(100), nullable=True)
    asset_class = Column(String(50), nullable=True)
    
    raw_payload = Column(JSON, nullable=True)
    
    status = Column(SQLEnum(AlertStatus), default=AlertStatus.PENDING)
    processed = Column(Boolean, default=False)
    
    received_at = Column(DateTime, default=func.now())
    
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
    __tablename__ = "alert_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(Integer, ForeignKey("tradingview_alerts.id"), unique=True, nullable=False)
    
    decision = Column(SQLEnum(AlertStatus), nullable=False)
    decision_at = Column(DateTime, default=func.now())
    decision_by = Column(String(100), default="Fund Manager")
    
    primary_call = Column(SQLEnum(ActionCall), nullable=True)
    primary_ticker = Column(String(50), nullable=True)
    primary_notes = Column(Text, nullable=True)
    primary_target_price = Column(Float, nullable=True)
    primary_stop_loss = Column(Float, nullable=True)
    
    secondary_call = Column(SQLEnum(ActionCall), nullable=True)
    secondary_ticker = Column(String(50), nullable=True)
    secondary_notes = Column(Text, nullable=True)
    secondary_target_price = Column(Float, nullable=True)
    secondary_stop_loss = Column(Float, nullable=True)
    
    conviction = Column(String(20), nullable=True)
    fm_remarks = Column(Text, nullable=True)
    
    # Chart image attachment
    chart_image_b64 = Column(Text, nullable=True)
    chart_image_path = Column(String(500), nullable=True)  # future: file path on volume

    # Leg 2 (for relative/ratio alerts)
    leg2_ticker = Column(String(50), nullable=True)
    leg2_call = Column(SQLEnum(ActionCall), nullable=True)
    leg2_target_price = Column(Float, nullable=True)
    leg2_stop_loss = Column(Float, nullable=True)
    leg2_notes = Column(Text, nullable=True)
    
    price_at_decision = Column(Float, nullable=True)
    secondary_price_at_decision = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    alert = relationship("TradingViewAlert", back_populates="action")


# ─── Performance Tracking ──────────────────────────────

class AlertPerformance(Base):
    __tablename__ = "alert_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(Integer, ForeignKey("tradingview_alerts.id"), nullable=False)
    
    ticker = Column(String(50), nullable=False)
    is_primary = Column(Boolean, default=True)
    
    reference_price = Column(Float, nullable=False)
    reference_date = Column(DateTime, nullable=False)
    
    current_price = Column(Float, nullable=True)
    snapshot_date = Column(DateTime, default=func.now())
    
    return_absolute = Column(Float, nullable=True)
    return_pct = Column(Float, nullable=True)
    
    return_1d = Column(Float, nullable=True)
    return_1w = Column(Float, nullable=True)
    return_1m = Column(Float, nullable=True)
    return_3m = Column(Float, nullable=True)
    return_6m = Column(Float, nullable=True)
    return_12m = Column(Float, nullable=True)
    
    high_since = Column(Float, nullable=True)
    low_since = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    
    alert = relationship("TradingViewAlert", back_populates="performance_records")

    __table_args__ = (
        Index('idx_perf_alert', 'alert_id'),
        Index('idx_perf_ticker', 'ticker'),
        Index('idx_perf_date', 'snapshot_date'),
    )


# ─── Sector/Index Mapping Reference ────────────────────

class InstrumentMap(Base):
    __tablename__ = "instrument_map"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=True)
    sector = Column(String(100), nullable=True)
    asset_class = Column(String(50), nullable=True)
    exchange = Column(String(30), nullable=True)
    is_index = Column(Boolean, default=False)
    related_etf = Column(String(50), nullable=True)
    components = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


# ─── Initialize Database ───────────────────────────────

def init_db():
    Base.metadata.create_all(bind=engine)
    _seed_instrument_map()
    _migrate_columns()
    print("Database initialized")


def _migrate_columns():
    """Safely add new columns to existing tables — idempotent, ignores if already exists."""
    db = SessionLocal()
    migrations = [
        "ALTER TABLE alert_actions ADD COLUMN chart_image_b64 TEXT",
        "ALTER TABLE alert_actions ADD COLUMN primary_target_price FLOAT",
        "ALTER TABLE alert_actions ADD COLUMN primary_stop_loss FLOAT",
        "ALTER TABLE alert_actions ADD COLUMN chart_image_path VARCHAR(500)",
        "ALTER TABLE alert_actions ADD COLUMN leg2_ticker VARCHAR(50)",
        "ALTER TABLE alert_actions ADD COLUMN leg2_call VARCHAR(50)",
        "ALTER TABLE alert_actions ADD COLUMN leg2_target_price FLOAT",
        "ALTER TABLE alert_actions ADD COLUMN leg2_stop_loss FLOAT",
        "ALTER TABLE alert_actions ADD COLUMN leg2_notes TEXT",
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


def _seed_instrument_map():
    db = SessionLocal()
    if db.query(InstrumentMap).count() > 0:
        db.close()
        return
    
    instruments = [
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
        {"ticker": "NIFTYCPSE", "name": "Nifty CPSE", "sector": "PSU", "asset_class": "INDEX", "exchange": "NSE", "is_index": True},
        {"ticker": "NIFTYFINSERVICE", "name": "Nifty Fin Services", "sector": "Financial Services", "asset_class": "INDEX", "exchange": "NSE", "is_index": True},
        {"ticker": "NIFTYHEALTHCARE", "name": "Nifty Healthcare", "sector": "Healthcare", "asset_class": "INDEX", "exchange": "NSE", "is_index": True},
        {"ticker": "NIFTYCONSUMER", "name": "Nifty Consumer Durables", "sector": "Consumer", "asset_class": "INDEX", "exchange": "NSE", "is_index": True},
        {"ticker": "NIFTYCOMMODITIES", "name": "Nifty Commodities", "sector": "Commodities", "asset_class": "INDEX", "exchange": "NSE", "is_index": True},
        {"ticker": "SENSEX", "name": "S&P BSE Sensex", "sector": "Broad Market", "asset_class": "INDEX", "exchange": "BSE", "is_index": True},
        {"ticker": "GOLD", "name": "Gold", "sector": "Commodities", "asset_class": "COMMODITY", "exchange": "MCX"},
        {"ticker": "SILVER", "name": "Silver", "sector": "Commodities", "asset_class": "COMMODITY", "exchange": "MCX"},
        {"ticker": "CRUDEOIL", "name": "Crude Oil", "sector": "Commodities", "asset_class": "COMMODITY", "exchange": "MCX"},
        {"ticker": "USDINR", "name": "USD/INR", "sector": "Currency", "asset_class": "CURRENCY", "exchange": "NSE"},
    ]
    
    for inst in instruments:
        db.add(InstrumentMap(**inst))
    
    db.commit()
    db.close()


if __name__ == "__main__":
    init_db()
