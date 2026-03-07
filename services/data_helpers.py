"""
FIE v3 — Shared Data Helpers
Database upsert and portfolio ticker helpers used by backfill, scheduler, and routers.
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models import (
    IndexPrice,
    ModelPortfolio,
    PortfolioHolding,
    PortfolioStatus,
)

logger = logging.getLogger("fie_v3.data")


def upsert_price_row(db: Session, idx_name: str, row: dict) -> bool:
    """Upsert a single IndexPrice row. Returns True if stored."""
    if not row.get("close"):
        return False
    existing = db.query(IndexPrice).filter_by(
        date=row["date"], index_name=idx_name
    ).first()
    if existing:
        existing.close_price = row["close"]
        existing.open_price  = row.get("open")
        existing.high_price  = row.get("high")
        existing.low_price   = row.get("low")
        existing.volume      = row.get("volume")
        existing.fetched_at  = datetime.now()
    else:
        db.add(IndexPrice(
            date=row["date"], index_name=idx_name,
            close_price=row["close"], open_price=row.get("open"),
            high_price=row.get("high"), low_price=row.get("low"),
            volume=row.get("volume"),
        ))
    return True


def get_portfolio_tickers(db: Session) -> list:
    """Unique stock tickers from active portfolios (excluding ETFs/indices)."""
    from price_service import NSE_ETF_UNIVERSE, NSE_TICKER_MAP
    try:
        holdings = (
            db.query(PortfolioHolding.ticker)
            .join(ModelPortfolio, PortfolioHolding.portfolio_id == ModelPortfolio.id)
            .filter(
                ModelPortfolio.status == PortfolioStatus.ACTIVE,
                PortfolioHolding.quantity > 0,
            )
            .distinct()
            .all()
        )
        etf_keys = set(k.upper() for k in NSE_ETF_UNIVERSE)
        index_keys = set(k.upper() for k in NSE_TICKER_MAP)
        tickers = []
        for (ticker,) in holdings:
            if not ticker:
                continue
            clean = ticker.upper().strip()
            if clean.startswith("MB_"):
                continue
            if clean not in etf_keys and clean not in index_keys:
                tickers.append(clean)
        return tickers
    except Exception as e:
        logger.warning("Failed to get portfolio tickers: %s", e)
        return []


def get_all_portfolio_tickers_with_inception(db: Session) -> dict:
    """All tickers (stocks + ETFs) from active portfolios with their earliest inception date.
    Returns {ticker: inception_date_str}."""
    try:
        holdings = (
            db.query(PortfolioHolding.ticker, ModelPortfolio.inception_date)
            .join(ModelPortfolio, PortfolioHolding.portfolio_id == ModelPortfolio.id)
            .filter(
                ModelPortfolio.status == PortfolioStatus.ACTIVE,
                PortfolioHolding.quantity > 0,
            )
            .all()
        )
        ticker_dates = {}
        for ticker, inception_date in holdings:
            if not ticker:
                continue
            clean = ticker.upper().strip()
            if clean.startswith("MB_"):
                continue
            if inception_date:
                if clean not in ticker_dates or inception_date < ticker_dates[clean]:
                    ticker_dates[clean] = inception_date
            elif clean not in ticker_dates:
                ticker_dates[clean] = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        return ticker_dates
    except Exception as e:
        logger.warning("Failed to get portfolio tickers with inception: %s", e)
        return {}
