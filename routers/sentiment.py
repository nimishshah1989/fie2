"""
FIE v3 — Sentiment Indicator Routes
Market breadth metrics across the Nifty 500 universe.
Computes EMA, RSI, 52-week highs/lows, and advance/decline stats.
All data sourced from the local IndexPrice DB — no live fetching required.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from models import IndexConstituent, IndexPrice, get_db
from services.technical import (
    compute_ema,
    compute_rsi,
    prev_month_range,
    prev_quarter_range,
    prev_year_range,
    resample_to_monthly,
)

logger = logging.getLogger("fie_v3.sentiment")
router = APIRouter()

# In-memory cache: (result_dict, computed_at)
_sentiment_cache: tuple[Optional[dict], Optional[datetime]] = (None, None)
CACHE_TTL_SECONDS = 900   # 15 minutes


def _cache_valid() -> bool:
    _, computed_at = _sentiment_cache
    if computed_at is None:
        return False
    return (datetime.now() - computed_at).total_seconds() < CACHE_TTL_SECONDS


# ─── Core Computation ──────────────────────────────────────

def compute_sentiment(db: Session) -> dict:
    """Compute all 11 breadth metrics for the Nifty 500 universe from DB prices."""
    today = date.today()
    today_str = today.isoformat()

    # Load Nifty 500 constituents
    constituents = (
        db.query(IndexConstituent)
        .filter(IndexConstituent.index_name == "NIFTY 500")
        .all()
    )
    tickers = [c.ticker for c in constituents]
    universe_size = len(tickers)

    if universe_size == 0:
        logger.warning("Sentiment: no Nifty 500 constituents found in DB")
        return _empty_result(0, today_str)

    logger.info("Sentiment: computing metrics for %d Nifty 500 stocks", universe_size)

    # Load last 520 calendar days of OHLCV for all tickers in one query
    cutoff = (today - timedelta(days=520)).isoformat()
    all_rows = (
        db.query(IndexPrice.index_name, IndexPrice.date, IndexPrice.close_price,
                 IndexPrice.high_price, IndexPrice.low_price)
        .filter(
            IndexPrice.index_name.in_(tickers),
            IndexPrice.date >= cutoff,
            IndexPrice.close_price.isnot(None),
        )
        .order_by(IndexPrice.index_name, IndexPrice.date)
        .all()
    )

    # Group by ticker
    price_map: dict[str, list] = {}
    for row in all_rows:
        if row.index_name not in price_map:
            price_map[row.index_name] = []
        price_map[row.index_name].append(row)

    # Absolute calendar period boundaries
    prev_month_start, prev_month_end = prev_month_range(today)
    prev_q_start, prev_q_end = prev_quarter_range(today)
    prev_year_start, prev_year_end = prev_year_range(today)

    # Counters
    above_10ema = above_21ema = above_200ema = 0
    hit_52w_high = hit_52w_low = 0
    above_12ema_monthly = 0
    rsi_above_50 = rsi_above_40 = 0
    above_prev_month_high = above_prev_quarter_high = above_prev_year_high = 0
    stocks_computed = 0

    for ticker in tickers:
        rows = price_map.get(ticker, [])
        if len(rows) < 22:   # need at least a month of data
            continue

        stocks_computed += 1
        closes = [r.close_price for r in rows]
        highs = [r.high_price for r in rows if r.high_price]
        lows = [r.low_price for r in rows if r.low_price]
        dates = [r.date for r in rows]
        latest_close = closes[-1]
        latest_date = dates[-1]

        # ── SHORT TERM TREND ──────────────────────────────

        # 10 EMA (daily)
        ema10 = compute_ema(closes, 10)
        if ema10 is not None and latest_close > ema10:
            above_10ema += 1

        # 21 EMA (daily)
        ema21 = compute_ema(closes, 21)
        if ema21 is not None and latest_close > ema21:
            above_21ema += 1

        # 52-week high/low (252 trading days ≈ 365 calendar days)
        cutoff_52w = (today - timedelta(days=365)).isoformat()
        recent_rows = [(d, c, h, l) for d, c, h, l in
                       zip(dates, closes,
                           [r.high_price or r.close_price for r in rows],
                           [r.low_price or r.close_price for r in rows])
                       if d >= cutoff_52w]
        if recent_rows and latest_date >= cutoff_52w:
            recent_highs = [h for _, _, h, _ in recent_rows if h]
            recent_lows = [l for _, _, _, l in recent_rows if l]
            if recent_highs:
                year_high = max(recent_highs)
                latest_high = rows[-1].high_price or latest_close
                if latest_high >= year_high * 0.999:   # within 0.1% tolerance
                    hit_52w_high += 1
            if recent_lows:
                year_low = min(recent_lows)
                latest_low = rows[-1].low_price or latest_close
                if latest_low <= year_low * 1.001:
                    hit_52w_low += 1

        # ── BROAD TREND ──────────────────────────────────

        # 200 EMA (daily)
        ema200 = compute_ema(closes, 200)
        if ema200 is not None and latest_close > ema200:
            above_200ema += 1

        # Monthly resampling — need at least 15 monthly bars for EMA(12) + RSI(14)
        date_close_pairs = list(zip(dates, closes))
        monthly = resample_to_monthly(date_close_pairs)
        monthly_closes = [c for _, c in monthly]
        latest_monthly_close = monthly_closes[-1] if monthly_closes else None

        # 12 EMA on monthly closes
        if len(monthly_closes) >= 13 and latest_monthly_close:
            ema12_monthly = compute_ema(monthly_closes, 12)
            if ema12_monthly is not None and latest_monthly_close > ema12_monthly:
                above_12ema_monthly += 1

        # Monthly RSI(14)
        if len(monthly_closes) >= 15:
            rsi_val = compute_rsi(monthly_closes, 14)
            if rsi_val is not None:
                if rsi_val > 50:
                    rsi_above_50 += 1
                if rsi_val > 40:
                    rsi_above_40 += 1

        # ── ADVANCE/DECLINE (absolute calendar periods) ──

        # Previous calendar month high
        month_rows = [r for r in rows
                      if prev_month_start.isoformat() <= r.date <= prev_month_end.isoformat()]
        if month_rows:
            month_high = max((r.high_price or r.close_price) for r in month_rows)
            if latest_close > month_high:
                above_prev_month_high += 1

        # Previous calendar quarter high
        q_rows = [r for r in rows
                  if prev_q_start.isoformat() <= r.date <= prev_q_end.isoformat()]
        if q_rows:
            q_high = max((r.high_price or r.close_price) for r in q_rows)
            if latest_close > q_high:
                above_prev_quarter_high += 1

        # Previous calendar year high
        year_rows = [r for r in rows
                     if prev_year_start.isoformat() <= r.date <= prev_year_end.isoformat()]
        if year_rows:
            year_high = max((r.high_price or r.close_price) for r in year_rows)
            if latest_close > year_high:
                above_prev_year_high += 1

    def _pct(count: int) -> float:
        if stocks_computed == 0:
            return 0.0
        return round((count / stocks_computed) * 100, 1)

    return {
        "universe": "NIFTY 500",
        "universe_size": universe_size,
        "stocks_computed": stocks_computed,
        "computed_at": datetime.now().isoformat() + "Z",
        "as_of_date": today_str,
        "short_term_trend": {
            "label": "Short Term Trend (Daily)",
            "metrics": [
                {
                    "key": "above_10ema",
                    "label": "Above 10 EMA (Daily)",
                    "count": above_10ema,
                    "total": stocks_computed,
                    "pct": _pct(above_10ema),
                },
                {
                    "key": "above_21ema",
                    "label": "Above 21 EMA (Daily)",
                    "count": above_21ema,
                    "total": stocks_computed,
                    "pct": _pct(above_21ema),
                },
                {
                    "key": "hit_52w_high",
                    "label": "Hitting 52-Week High",
                    "count": hit_52w_high,
                    "total": stocks_computed,
                    "pct": _pct(hit_52w_high),
                },
                {
                    "key": "hit_52w_low",
                    "label": "Hitting 52-Week Low",
                    "count": hit_52w_low,
                    "total": stocks_computed,
                    "pct": _pct(hit_52w_low),
                    "invert": True,   # high count = bearish
                },
            ],
        },
        "broad_trend": {
            "label": "Broad Trend (Monthly)",
            "metrics": [
                {
                    "key": "above_200ema",
                    "label": "Above 200 EMA (Daily)",
                    "count": above_200ema,
                    "total": stocks_computed,
                    "pct": _pct(above_200ema),
                },
                {
                    "key": "rsi_above_50",
                    "label": "Monthly RSI > 50",
                    "count": rsi_above_50,
                    "total": stocks_computed,
                    "pct": _pct(rsi_above_50),
                },
                {
                    "key": "rsi_above_40",
                    "label": "Monthly RSI > 40",
                    "count": rsi_above_40,
                    "total": stocks_computed,
                    "pct": _pct(rsi_above_40),
                },
                {
                    "key": "above_12ema_monthly",
                    "label": "Above 12 EMA (Monthly)",
                    "count": above_12ema_monthly,
                    "total": stocks_computed,
                    "pct": _pct(above_12ema_monthly),
                },
            ],
        },
        "advance_decline": {
            "label": "Advance / Decline",
            "period_note": "Absolute calendar periods (not rolling)",
            "periods": {
                "prev_month": f"{prev_month_start.strftime('%b %Y')}",
                "prev_quarter": f"{prev_q_start.strftime('%b')}–{prev_q_end.strftime('%b %Y')}",
                "prev_year": str(prev_year_start.year),
            },
            "metrics": [
                {
                    "key": "above_prev_month_high",
                    "label": f"Above Previous Month High ({prev_month_start.strftime('%b %Y')})",
                    "count": above_prev_month_high,
                    "total": stocks_computed,
                    "pct": _pct(above_prev_month_high),
                },
                {
                    "key": "above_prev_quarter_high",
                    "label": f"Above Previous Quarter High ({prev_q_start.strftime('%b')}–{prev_q_end.strftime('%b %Y')})",
                    "count": above_prev_quarter_high,
                    "total": stocks_computed,
                    "pct": _pct(above_prev_quarter_high),
                },
                {
                    "key": "above_prev_year_high",
                    "label": f"Above Previous Year High ({prev_year_start.year})",
                    "count": above_prev_year_high,
                    "total": stocks_computed,
                    "pct": _pct(above_prev_year_high),
                },
            ],
        },
    }


def _empty_result(universe_size: int, as_of_date: str) -> dict:
    return {
        "universe": "NIFTY 500",
        "universe_size": universe_size,
        "stocks_computed": 0,
        "computed_at": datetime.now().isoformat() + "Z",
        "as_of_date": as_of_date,
        "short_term_trend": {"label": "Short Term Trend (Daily)", "metrics": []},
        "broad_trend": {"label": "Broad Trend (Monthly)", "metrics": []},
        "advance_decline": {"label": "Advance / Decline", "metrics": []},
    }


# ─── Routes ─────────────────────────────────────────────

@router.get(
    "/api/sentiment",
    tags=["Sentiment"],
    summary="Market breadth indicators",
    description="Returns 11 market breadth metrics for the Nifty 500 universe including EMA crossovers, RSI levels, 52-week extremes, and advance/decline stats. Results are cached for 15 minutes.",
)
async def get_sentiment(db: Session = Depends(get_db)):
    """Return cached sentiment metrics, recomputing if cache is stale."""
    global _sentiment_cache

    if _cache_valid():
        cached_result, _ = _sentiment_cache
        return {"success": True, "cached": True, **cached_result}

    result = compute_sentiment(db)
    _sentiment_cache = (result, datetime.now())
    return {"success": True, "cached": False, **result}


@router.post(
    "/api/sentiment/refresh",
    tags=["Sentiment"],
    summary="Force refresh sentiment cache",
    description="Clears the sentiment cache and recomputes all metrics immediately. Use after EOD data is loaded.",
)
async def refresh_sentiment(db: Session = Depends(get_db)):
    """Force-recompute sentiment metrics and refresh the cache."""
    global _sentiment_cache

    result = compute_sentiment(db)
    _sentiment_cache = (result, datetime.now())
    return {
        "success": True,
        "cached": False,
        "message": f"Sentiment recomputed for {result['stocks_computed']} stocks",
        **result,
    }
