"""
FIE v3 -- Shared Ratio Computation Service
Batch price fetching and ratio-based relative strength computation.
Used by routers/indices.py, routers/recommendations.py, and routers/global_pulse.py.

All functions are DB-batch-optimized: no N+1 patterns.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from models import IndexPrice

logger = logging.getLogger("fie_v3.ratio_service")

# --- Period Definitions -------------------------------------------------------

PERIOD_MAP = {"1d": 1, "1w": 7, "1m": 30, "3m": 90, "6m": 180, "12m": 365}
PERIOD_TOLERANCE = {"1d": 5, "1w": 5, "1m": 10, "3m": 15, "6m": 15, "12m": 15}

# Signal thresholds
SIGNAL_STRONG_OW = 1.05
SIGNAL_STRONG_UW = 0.95


def get_signal(ratio: float) -> str:
    """Convert price ratio to signal label."""
    if ratio > SIGNAL_STRONG_OW:
        return "STRONG OW"
    elif ratio > 1.0:
        return "OVERWEIGHT"
    elif ratio < SIGNAL_STRONG_UW:
        return "STRONG UW"
    elif ratio < 1.0:
        return "UNDERWEIGHT"
    return "NEUTRAL"


# --- Batch Price Helpers ------------------------------------------------------

def resolve_period_dates(db: Session, periods: Dict[str, int] = None) -> Dict[str, Optional[str]]:
    """Resolve period target dates to closest actual DB dates. ~10 queries total."""
    periods = periods or PERIOD_MAP
    tolerances = PERIOD_TOLERANCE
    resolved = {}
    for pk, days in periods.items():
        target_str = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        tol = tolerances.get(pk, 15)
        target_dt = datetime.strptime(target_str, "%Y-%m-%d")

        before = db.query(sqlfunc.max(IndexPrice.date)).filter(IndexPrice.date <= target_str).scalar()
        after = db.query(sqlfunc.min(IndexPrice.date)).filter(IndexPrice.date >= target_str).scalar()

        best = None
        if before:
            gap = (target_dt - datetime.strptime(before, "%Y-%m-%d")).days
            if gap <= tol:
                best = before
        if after:
            gap_after = (datetime.strptime(after, "%Y-%m-%d") - target_dt).days
            if gap_after <= tol:
                if best is None:
                    best = after
                elif gap_after < abs((target_dt - datetime.strptime(best, "%Y-%m-%d")).days):
                    best = after
        resolved[pk] = best
    return resolved


def batch_latest_prices(db: Session, tickers: Set[str]) -> Dict[str, float]:
    """Fetch latest close price for many tickers in one query."""
    if not tickers:
        return {}
    subq = (
        db.query(IndexPrice.index_name, sqlfunc.max(IndexPrice.date).label("max_date"))
        .filter(IndexPrice.index_name.in_(tickers))
        .group_by(IndexPrice.index_name)
        .subquery()
    )
    rows = (
        db.query(IndexPrice.index_name, IndexPrice.close_price)
        .join(subq, (IndexPrice.index_name == subq.c.index_name) & (IndexPrice.date == subq.c.max_date))
        .all()
    )
    return {r[0]: r[1] for r in rows if r[1]}


def batch_historical_prices(
    db: Session, dates: List[str], tickers: Set[str],
) -> Dict[str, Dict[str, float]]:
    """Fetch prices at specific historical dates for many tickers in one query."""
    if not dates or not tickers:
        return {}
    rows = (
        db.query(IndexPrice.date, IndexPrice.index_name, IndexPrice.close_price)
        .filter(IndexPrice.date.in_(dates), IndexPrice.index_name.in_(tickers))
        .all()
    )
    result: Dict[str, Dict[str, float]] = {}
    for date_str, ticker, price in rows:
        if price:
            result.setdefault(date_str, {})[ticker] = price
    return result


def compute_ratio_returns(
    ticker: str,
    base_key: str,
    latest_prices: Dict[str, float],
    period_dates: Dict[str, Optional[str]],
    hist_prices: Dict[str, Dict[str, float]],
    periods: Dict[str, int] = None,
) -> Dict[str, float]:
    """Compute ratio returns using pre-fetched price data. Zero DB queries."""
    periods = periods or PERIOD_MAP
    current = latest_prices.get(ticker)
    base_current = latest_prices.get(base_key)
    if not current or not base_current or base_current <= 0:
        return {}

    ratio_today = current / base_current
    returns = {}
    for pk in periods:
        hist_date = period_dates.get(pk)
        if not hist_date:
            continue
        date_prices = hist_prices.get(hist_date, {})
        old_ticker = date_prices.get(ticker)
        old_base = date_prices.get(base_key)
        if old_ticker and old_base and old_base > 0:
            ratio_old = old_ticker / old_base
            if ratio_old > 0:
                returns[pk] = round(((ratio_today / ratio_old) - 1) * 100, 2)
    return returns


def compute_absolute_returns(
    ticker: str,
    latest_prices: Dict[str, float],
    period_dates: Dict[str, Optional[str]],
    hist_prices: Dict[str, Dict[str, float]],
    periods: Dict[str, int] = None,
) -> Dict[str, float]:
    """Compute absolute period returns for a ticker. Zero DB queries."""
    periods = periods or PERIOD_MAP
    current = latest_prices.get(ticker)
    if not current:
        return {}

    returns = {}
    for pk in periods:
        hist_date = period_dates.get(pk)
        if not hist_date:
            continue
        old_price = hist_prices.get(hist_date, {}).get(ticker)
        if old_price and old_price > 0:
            returns[pk] = round(((current / old_price) - 1) * 100, 2)
    return returns
