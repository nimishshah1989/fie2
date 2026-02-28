"""
Portfolio Models — Jhaveri Intelligence Platform
Model Portfolio Management: strategies, holdings, transactions, daily NAV
Shares DB engine/session from models.py, creates new tables only.
"""

from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, Boolean,
    Enum as SQLEnum, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

# Import shared DB engine and session from existing models
from models import Base, engine, SessionLocal, IndexPrice


# ─── Enums ─────────────────────────────────────────────

class PortfolioStatus(str, enum.Enum):
    ACTIVE   = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class TransactionType(str, enum.Enum):
    BUY  = "BUY"
    SELL = "SELL"


# ─── Model Portfolio (Strategy Container) ──────────────

class ModelPortfolio(Base):
    __tablename__ = "model_portfolios"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    benchmark   = Column(String(50), default="NIFTY")
    status      = Column(SQLEnum(PortfolioStatus), default=PortfolioStatus.ACTIVE)
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


# ─── Portfolio Holding (Current Position State) ────────

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
    added_at      = Column(DateTime, default=func.now())
    updated_at    = Column(DateTime, default=func.now(), onupdate=func.now())

    portfolio = relationship("ModelPortfolio", back_populates="holdings")

    __table_args__ = (
        Index('idx_holding_portfolio_ticker', 'portfolio_id', 'ticker', unique=True),
        Index('idx_holding_portfolio', 'portfolio_id'),
    )


# ─── Portfolio Transaction (Immutable Trade Log) ──────

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

    # P&L fields (populated on SELL transactions only)
    realized_pnl       = Column(Float, nullable=True)
    realized_pnl_pct   = Column(Float, nullable=True)
    cost_basis_at_sell  = Column(Float, nullable=True)

    portfolio = relationship("ModelPortfolio", back_populates="transactions")

    __table_args__ = (
        Index('idx_txn_portfolio', 'portfolio_id'),
        Index('idx_txn_portfolio_date', 'portfolio_id', 'txn_date'),
        Index('idx_txn_ticker', 'ticker'),
    )


# ─── Portfolio NAV (Daily Snapshot for Charts) ────────

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


# ─── Init ──────────────────────────────────────────────

def init_portfolio_db():
    """Create portfolio tables. Safe to call multiple times (idempotent)."""
    Base.metadata.create_all(bind=engine)
    print("Portfolio tables initialized")
