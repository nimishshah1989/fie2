"""
FIE v3 — Per-Stock Sentiment Storage & Aggregation
Orchestrates per-stock scoring (via stock_metrics.py), stores results
in the stock_sentiment table, and provides sector-level aggregation queries.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from models import IndexConstituent, IndexPrice, StockSentiment
from services.stock_metrics import compute_single_stock_sentiment, score_to_zone

logger = logging.getLogger("fie_v3.stock_sentiment")

COMMIT_BATCH_SIZE = 100


def compute_and_store_stock_sentiment(db: Session) -> int:
    """Compute per-stock sentiment for all tracked stocks. Returns count processed."""
    today = date.today()
    today_str = today.isoformat()

    n500 = db.query(IndexConstituent).filter(IndexConstituent.index_name == "NIFTY 500").all()
    if n500:
        constituents = n500
    else:
        seen: set = set()
        constituents = []
        for c in db.query(IndexConstituent).all():
            if c.ticker not in seen:
                seen.add(c.ticker)
                constituents.append(c)
        logger.info("Stock sentiment: NIFTY 500 not in DB, using %d sector stocks", len(constituents))

    tickers = [c.ticker for c in constituents]
    total = len(tickers)
    if total == 0:
        logger.warning("Stock sentiment: no constituents found")
        return 0

    sector_map = _build_sector_map(db, tickers)

    cutoff = (today - timedelta(days=520)).isoformat()
    all_rows = (
        db.query(IndexPrice)
        .filter(IndexPrice.index_name.in_(tickers), IndexPrice.date >= cutoff,
                IndexPrice.close_price.isnot(None))
        .order_by(IndexPrice.index_name, IndexPrice.date).all()
    )
    price_map: dict = {}
    for row in all_rows:
        price_map.setdefault(row.index_name, []).append(row)

    logger.info("Stock sentiment: computing for %d stocks...", total)
    processed = 0
    for ticker in tickers:
        rows = price_map.get(ticker, [])
        sector = sector_map.get(ticker)
        result = compute_single_stock_sentiment(ticker, rows, sector_index=sector)
        if result is None:
            continue
        _upsert_stock_sentiment(db, ticker, today_str, sector, result)
        processed += 1
        if processed % COMMIT_BATCH_SIZE == 0:
            db.commit()
            logger.info("Stock sentiment: processed %d/%d stocks", processed, total)

    db.commit()
    logger.info("Stock sentiment: stored scores for %d/%d stocks", processed, total)
    return processed


def _upsert_stock_sentiment(
    db: Session, ticker: str, date_str: str,
    sector: Optional[str], result: dict,
) -> None:
    """Insert or update a single StockSentiment row."""
    existing = (
        db.query(StockSentiment)
        .filter(StockSentiment.date == date_str, StockSentiment.ticker == ticker)
        .first()
    )
    fields = {
        "composite_score": result["composite_score"], "zone": result["zone"],
        "sector_index": sector,
        "above_10ema": result["above_10ema"], "above_21ema": result["above_21ema"],
        "above_50ema": result["above_50ema"], "above_200ema": result["above_200ema"],
        "golden_cross": result["golden_cross"],
        "rsi_daily": result["rsi_daily"], "rsi_weekly": result["rsi_weekly"],
        "macd_bull_cross": result["macd_bull_cross"],
        "hit_52w_high": result["hit_52w_high"], "hit_52w_low": result["hit_52w_low"],
        "roc_positive": result["roc_positive"],
        "above_prev_month_high": result["above_prev_month_high"],
    }
    if existing:
        for key, val in fields.items():
            setattr(existing, key, val)
    else:
        db.add(StockSentiment(ticker=ticker, date=date_str, **fields))


def _build_sector_map(db: Session, tickers: list) -> dict:
    """Map ticker -> sector display name (first non-NIFTY-500 match)."""
    rows = (
        db.query(IndexConstituent.ticker, IndexConstituent.index_name)
        .filter(IndexConstituent.ticker.in_(tickers), IndexConstituent.index_name != "NIFTY 500")
        .all()
    )
    m: dict = {}
    for ticker, idx_name in rows:
        if ticker not in m:
            m[ticker] = idx_name
    return m


def _stock_to_dict(e: StockSentiment) -> dict:
    """Convert a StockSentiment row to a response dict."""
    return {
        "ticker": e.ticker, "composite_score": e.composite_score, "zone": e.zone,
        "rsi_daily": e.rsi_daily, "rsi_weekly": e.rsi_weekly,
        "above_10ema": e.above_10ema, "above_50ema": e.above_50ema,
        "above_200ema": e.above_200ema, "golden_cross": e.golden_cross,
        "macd_bull_cross": e.macd_bull_cross, "hit_52w_high": e.hit_52w_high,
        "hit_52w_low": e.hit_52w_low, "roc_positive": e.roc_positive,
        "above_prev_month_high": e.above_prev_month_high,
    }


def _get_latest_date(db: Session) -> Optional[str]:
    """Get the most recent date with stock sentiment data."""
    latest = db.query(StockSentiment.date).order_by(StockSentiment.date.desc()).first()
    return latest[0] if latest else None


def get_sector_sentiment(db: Session) -> list:
    """Aggregate per-stock scores by sector. Returns list sorted by avg score desc."""
    from index_constants import NSE_DISPLAY_MAP
    reverse_map = {v: k for k, v in NSE_DISPLAY_MAP.items()}

    latest_date_str = _get_latest_date(db)
    if not latest_date_str:
        return []

    entries = (
        db.query(StockSentiment)
        .filter(StockSentiment.date == latest_date_str, StockSentiment.sector_index.isnot(None))
        .order_by(StockSentiment.sector_index, StockSentiment.composite_score.desc())
        .all()
    )

    sectors: dict = {}
    for entry in entries:
        sectors.setdefault(entry.sector_index, []).append(entry)

    result = []
    for sector_name, stocks in sorted(sectors.items()):
        scores = [s.composite_score for s in stocks]
        avg = round(sum(scores) / len(scores), 1) if scores else 0.0
        bull = sum(1 for s in stocks if s.composite_score >= 55)
        bear = sum(1 for s in stocks if s.composite_score < 30)
        ss = sorted(stocks, key=lambda s: s.composite_score, reverse=True)
        result.append({
            "sector": sector_name,
            "sector_key": reverse_map.get(sector_name, sector_name.replace(" ", "").upper()),
            "avg_score": avg, "zone": score_to_zone(avg),
            "stock_count": len(stocks),
            "bullish_count": bull, "bearish_count": bear,
            "neutral_count": len(stocks) - bull - bear,
            "top_stocks": [{"ticker": s.ticker, "score": s.composite_score, "zone": s.zone} for s in ss[:5]],
            "bottom_stocks": [{"ticker": s.ticker, "score": s.composite_score, "zone": s.zone} for s in ss[-5:]],
        })

    result.sort(key=lambda s: s["avg_score"], reverse=True)
    return result


def get_stock_sentiment(db: Session, ticker: str) -> Optional[dict]:
    """Get latest sentiment for a single stock."""
    entry = (
        db.query(StockSentiment).filter(StockSentiment.ticker == ticker)
        .order_by(StockSentiment.date.desc()).first()
    )
    if not entry:
        return None
    return {
        "ticker": entry.ticker, "sector_index": entry.sector_index,
        "date": entry.date, "composite_score": entry.composite_score, "zone": entry.zone,
        "metrics": {
            "above_10ema": entry.above_10ema, "above_21ema": entry.above_21ema,
            "above_50ema": entry.above_50ema, "above_200ema": entry.above_200ema,
            "golden_cross": entry.golden_cross, "rsi_daily": entry.rsi_daily,
            "rsi_weekly": entry.rsi_weekly, "macd_bull_cross": entry.macd_bull_cross,
            "hit_52w_high": entry.hit_52w_high, "hit_52w_low": entry.hit_52w_low,
            "roc_positive": entry.roc_positive, "above_prev_month_high": entry.above_prev_month_high,
        },
    }


def get_sector_stocks(db: Session, sector_key: str) -> list:
    """Get per-stock sentiment for all stocks in a sector, sorted by score desc."""
    from index_constants import NSE_DISPLAY_MAP
    display_name = NSE_DISPLAY_MAP.get(sector_key.upper())
    if not display_name:
        return []
    latest_date_str = _get_latest_date(db)
    if not latest_date_str:
        return []
    entries = (
        db.query(StockSentiment)
        .filter(StockSentiment.date == latest_date_str, StockSentiment.sector_index == display_name)
        .order_by(StockSentiment.composite_score.desc()).all()
    )
    return [_stock_to_dict(e) for e in entries]
