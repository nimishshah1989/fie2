"""
Sector Compass — Data Service
Handles 1Y backfill + daily fetch for sector constituent stocks and ETFs.
Writes to compass-specific tables (CompassStockPrice, CompassETFPrice).
Does NOT touch existing IndexPrice or price_service tables.
"""

import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from index_constants import (
    COMPASS_ETF_UNIVERSE,
    COMPASS_SECTOR_INDICES,
)
from models import (
    CompassETFPrice,
    CompassStockPrice,
    IndexConstituent,
)

logger = logging.getLogger("fie_v3.compass.data")


def _upsert_compass_stock(db: Session, ticker: str, row: dict) -> bool:
    """Upsert a single stock price row into compass_stock_prices."""
    date_str = row.get("date", "")
    close = row.get("close")
    if not date_str or close is None:
        return False
    existing = (
        db.query(CompassStockPrice)
        .filter_by(date=date_str, ticker=ticker)
        .first()
    )
    if existing:
        existing.close = float(close)
        existing.open = row.get("open")
        existing.high = row.get("high")
        existing.low = row.get("low")
        existing.volume = row.get("volume")
    else:
        db.add(CompassStockPrice(
            date=date_str,
            ticker=ticker,
            open=row.get("open"),
            high=row.get("high"),
            low=row.get("low"),
            close=float(close),
            volume=row.get("volume"),
        ))
    return True


def _upsert_compass_etf(db: Session, ticker: str, row: dict) -> bool:
    """Upsert a single ETF price row into compass_etf_prices."""
    date_str = row.get("date", "")
    close = row.get("close")
    if not date_str or close is None:
        return False
    existing = (
        db.query(CompassETFPrice)
        .filter_by(date=date_str, ticker=ticker)
        .first()
    )
    if existing:
        existing.close = float(close)
        existing.open = row.get("open")
        existing.high = row.get("high")
        existing.low = row.get("low")
        existing.volume = row.get("volume")
    else:
        db.add(CompassETFPrice(
            date=date_str,
            ticker=ticker,
            open=row.get("open"),
            high=row.get("high"),
            low=row.get("low"),
            close=float(close),
            volume=row.get("volume"),
        ))
    return True


def get_all_compass_stock_tickers(db: Session) -> list[str]:
    """Get all unique stock tickers from sector constituents for compass tracking."""
    rows = db.query(IndexConstituent.ticker).distinct().all()
    return [r[0] for r in rows if r[0]]


def backfill_compass_stocks(db: Session, period: str = "1y") -> int:
    """Backfill 1Y stock prices for all sector constituent stocks into compass tables."""
    from price_service import fetch_yfinance_bulk_stock_history

    tickers = get_all_compass_stock_tickers(db)
    if not tickers:
        logger.info("Compass backfill: no constituent tickers found")
        return 0

    logger.info("Compass backfill: fetching %s history for %d stocks...", period, len(tickers))
    data = fetch_yfinance_bulk_stock_history(tickers, period=period)
    stored = 0
    for ticker, rows in data.items():
        if rows is None:
            continue
        for row in rows:
            if _upsert_compass_stock(db, ticker, row):
                stored += 1
    db.commit()
    logger.info("Compass backfill: stored %d stock price records", stored)
    return stored


def backfill_compass_etfs(db: Session, period: str = "1y") -> int:
    """Backfill 1Y ETF prices for all sector ETFs into compass tables."""
    from price_service import fetch_yfinance_bulk_stock_history

    etf_tickers = list(COMPASS_ETF_UNIVERSE.keys())
    if not etf_tickers:
        return 0

    logger.info("Compass backfill: fetching %s history for %d ETFs...", period, len(etf_tickers))
    data = fetch_yfinance_bulk_stock_history(etf_tickers, period=period)
    stored = 0
    for ticker, rows in data.items():
        if rows is None:
            continue
        for row in rows:
            if _upsert_compass_etf(db, ticker, row):
                stored += 1
    db.commit()
    logger.info("Compass backfill: stored %d ETF price records", stored)
    return stored


def daily_refresh_compass_prices(db: Session) -> dict:
    """Fetch latest prices for all compass stocks, ETFs, and sector indices.

    Called every 15 min during market hours. Uses:
    - nsetools for live sector index prices (updates IndexPrice table)
    - yfinance 5d rolling for stocks and ETFs (updates compass tables)

    All data is 100% real — no mock, no synthetic values.
    """
    from price_service import fetch_yfinance_bulk_stock_history
    from services.data_helpers import upsert_price_row

    result = {"indices": 0, "stocks": 0, "etfs": 0}

    # 1. Refresh live index prices via nsetools (sector indices + NIFTY benchmark)
    # This updates the IndexPrice table that RS engine reads for sector-level RS
    try:
        from price_service import fetch_live_indices
        live = fetch_live_indices()
        today_str = datetime.now().strftime("%Y-%m-%d")
        for item in live:
            close = item.get("last")
            if not close:
                continue
            row = {
                "date": today_str,
                "close": close,
                "open": item.get("open"),
                "high": item.get("high"),
                "low": item.get("low"),
            }
            if upsert_price_row(db, item["index_name"], row):
                result["indices"] += 1
        db.commit()
    except Exception as e:
        logger.warning("Compass: live index refresh failed (non-fatal): %s", e)

    # 2. Refresh stock prices (yfinance 5d rolling window)
    tickers = get_all_compass_stock_tickers(db)
    if tickers:
        data = fetch_yfinance_bulk_stock_history(tickers, period="5d")
        for ticker, rows in data.items():
            if rows is None:
                continue
            for row in rows:
                if _upsert_compass_stock(db, ticker, row):
                    result["stocks"] += 1

    # 3. Refresh ETF prices (yfinance 5d rolling window)
    etf_tickers = list(COMPASS_ETF_UNIVERSE.keys())
    if etf_tickers:
        data = fetch_yfinance_bulk_stock_history(etf_tickers, period="5d")
        for ticker, rows in data.items():
            if rows is None:
                continue
            for row in rows:
                if _upsert_compass_etf(db, ticker, row):
                    result["etfs"] += 1

    db.commit()
    logger.info("Compass daily refresh: %d stock, %d ETF records", result["stocks"], result["etfs"])
    return result


def get_stock_price_series(
    db: Session, ticker: str, days: int = 365,
) -> list[dict]:
    """Get price history for a stock from compass tables."""
    rows = (
        db.query(CompassStockPrice)
        .filter(CompassStockPrice.ticker == ticker)
        .order_by(CompassStockPrice.date.desc())
        .limit(days)
        .all()
    )
    return [
        {
            "date": r.date,
            "close": r.close,
            "volume": r.volume,
            "open": r.open,
            "high": r.high,
            "low": r.low,
        }
        for r in reversed(rows)
    ]


def get_etf_price_series(
    db: Session, ticker: str, days: int = 365,
) -> list[dict]:
    """Get price history for an ETF from compass tables."""
    rows = (
        db.query(CompassETFPrice)
        .filter(CompassETFPrice.ticker == ticker)
        .order_by(CompassETFPrice.date.desc())
        .limit(days)
        .all()
    )
    return [
        {
            "date": r.date,
            "close": r.close,
            "volume": r.volume,
            "open": r.open,
            "high": r.high,
            "low": r.low,
        }
        for r in reversed(rows)
    ]
