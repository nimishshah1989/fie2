"""
FIE v3 — Per-Stock Technical Metric Computation
Pure functions for computing 22 technical indicators on a single stock.
No DB access — receives price data as arguments, returns metric dicts.

Layers (22 metrics total):
  1. Short-Term (0.20) — above_10ema, above_21ema, rsi_daily>50, close>prev_day_high
  2. Broad Trend (0.30) — above_50ema, above_200ema, golden_cross,
                           above_prev_month_high, rsi_weekly>50
  3. A/D proxy  (0.25) — above_20sma, close_near_high, vol_above_avg
  4. Momentum   (0.15) — macd_bull_cross, roc_positive, momentum_positive, adx>25
  5. Extremes   (0.10) — hit_52w_high, hit_52w_low (bearish), bollinger_above_mid, mfi>50

Used by stock_sentiment.py for per-stock scoring.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from services.technical import (
    compute_adx,
    compute_ema,
    compute_ema_series,
    compute_mfi,
    compute_rsi,
    resample_to_weekly,
)

# Layer weights matching sentiment_engine.py
LAYER_WEIGHTS = {
    "short_term": 0.20,
    "broad_trend": 0.30,
    "adv_decline": 0.25,
    "momentum": 0.15,
    "extremes": 0.10,
}

# Zone thresholds: Bear(<30), Weak(<45), Neutral(<55), Bullish(<70), Strong(>=70)
ZONE_THRESHOLDS = [
    (30, "Bear"), (45, "Weak"), (55, "Neutral"), (70, "Bullish"), (101, "Strong"),
]

# Minimum trading days required for meaningful metrics
MIN_TRADING_DAYS = 50


def score_to_zone(score: float) -> str:
    """Convert a composite score (0-100) to a zone label."""
    return next(lbl for thr, lbl in ZONE_THRESHOLDS if score < thr)


def compute_single_stock_sentiment(
    ticker: str,
    rows: list,
    sector_index: Optional[str] = None,
) -> Optional[dict]:
    """
    Compute 22 per-stock metrics across 5 layers for a single stock.

    Args:
        ticker: Stock symbol.
        rows: IndexPrice rows sorted by date ascending (need close_price,
              high_price, low_price, volume attributes).
        sector_index: Optional sector display name (e.g. "NIFTY BANK").

    Returns:
        dict with ticker, composite_score, zone, and metric flags,
        or None if insufficient data (< MIN_TRADING_DAYS days).
    """
    if len(rows) < MIN_TRADING_DAYS:
        return None

    closes = [r.close_price for r in rows]
    highs = [r.high_price or r.close_price for r in rows]
    lows = [r.low_price or r.close_price for r in rows]
    volumes = [r.volume or 0 for r in rows]
    dates = [r.date for r in rows]
    today = date.today()
    lc = closes[-1]

    # Layer 1: Short-Term (4 metrics)
    l1, short_flags = _compute_short_term(closes, highs, lc)

    # Layer 2: Broad Trend (5 metrics)
    l2, broad_flags = _compute_broad_trend(closes, highs, dates, lc)

    # Layer 3: A/D proxy (3 metrics)
    l3 = _compute_ad_proxy(closes, highs, lows, volumes, lc)

    # Layer 4: Momentum (4 metrics)
    l4, mom_flags = _compute_momentum(closes, highs, lows, lc)

    # Layer 5: Extremes (4 metrics, hit_52w_low subtracts)
    l5, ext_flags = _compute_extremes(
        closes, highs, lows, volumes, dates, lc, today, broad_flags["above_20sma"],
    )

    # Composite: weighted sum of layer pass rates * 100
    layer_data = [(l1, 4), (l2, 5), (l3, 3), (l4, 4), (l5, 3)]
    composite = round(sum(
        (passed / max(total, 1)) * 100.0 * weight
        for (passed, total), weight in zip(layer_data, LAYER_WEIGHTS.values())
    ), 1)
    zone = score_to_zone(composite)

    return {
        "ticker": ticker,
        "composite_score": composite,
        "zone": zone,
        "above_10ema": short_flags["above_10ema"],
        "above_21ema": short_flags["above_21ema"],
        "above_50ema": broad_flags["above_50ema"],
        "above_200ema": broad_flags["above_200ema"],
        "golden_cross": broad_flags["golden_cross"],
        "rsi_daily": short_flags["rsi_daily"],
        "rsi_weekly": broad_flags["rsi_weekly"],
        "macd_bull_cross": mom_flags["macd_bull_cross"],
        "hit_52w_high": ext_flags["hit_52w_high"],
        "hit_52w_low": ext_flags["hit_52w_low"],
        "roc_positive": mom_flags["roc_positive"],
        "above_prev_month_high": broad_flags["above_prev_month_high"],
    }


def _compute_short_term(closes, highs, lc):
    """Layer 1: Short-Term (4 metrics)."""
    ema10 = compute_ema(closes, 10)
    above_10ema = ema10 is not None and lc > ema10

    ema21 = compute_ema(closes, 21)
    above_21ema = ema21 is not None and lc > ema21

    daily_rsi = compute_rsi(closes, 14)
    rsi_daily_above_50 = daily_rsi is not None and daily_rsi > 50

    # Close > previous day's High
    price_above_prev_high = len(highs) >= 2 and lc > highs[-2]

    passed = sum([above_10ema, above_21ema, rsi_daily_above_50, price_above_prev_high])
    flags = {
        "above_10ema": above_10ema,
        "above_21ema": above_21ema,
        "rsi_daily": round(daily_rsi, 2) if daily_rsi is not None else None,
    }
    return passed, flags


def _compute_broad_trend(closes, highs, dates, lc):
    """Layer 2: Broad Trend (5 metrics)."""
    ema50 = compute_ema(closes, 50)
    above_50ema = ema50 is not None and lc > ema50

    ema200 = compute_ema(closes, 200)
    above_200ema = ema200 is not None and lc > ema200

    # Golden cross: 50-day SMA > 200-day SMA
    sma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None
    sma200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else None
    golden_cross = sma50 is not None and sma200 is not None and sma50 > sma200

    # Above prev month high: close > max high in last 20 trading days (excl today)
    above_prev_month_high = False
    if len(highs) > 20:
        prev_20d_highs = highs[-21:-1]
        above_prev_month_high = lc > max(prev_20d_highs)

    # Weekly RSI > 50
    dcp = list(zip(dates, closes))
    wc = [c for _, c in resample_to_weekly(dcp)]
    weekly_rsi = compute_rsi(wc, 14) if len(wc) >= 15 else None
    rsi_weekly_above_50 = weekly_rsi is not None and weekly_rsi > 50

    # above_20sma passed through for Layer 5 (bollinger_above_mid)
    sma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
    above_20sma = sma20 is not None and lc > sma20

    passed = sum([
        above_50ema, above_200ema, golden_cross,
        above_prev_month_high, rsi_weekly_above_50,
    ])
    flags = {
        "above_50ema": above_50ema,
        "above_200ema": above_200ema,
        "golden_cross": golden_cross,
        "above_prev_month_high": above_prev_month_high,
        "rsi_weekly": round(weekly_rsi, 2) if weekly_rsi is not None else None,
        "above_20sma": above_20sma,
    }
    return passed, flags


def _compute_ad_proxy(closes, highs, lows, volumes, lc):
    """Layer 3: A/D proxy (3 metrics)."""
    # above_20sma
    sma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
    above_20sma = sma20 is not None and lc > sma20

    # close_near_high: (Close - Low) / (High - Low) > 0.7 for today's bar
    hl_range = highs[-1] - lows[-1]
    close_near_high = hl_range > 0 and ((lc - lows[-1]) / hl_range) > 0.7

    # Volume > 20-day average
    vol_above_avg = False
    if len(volumes) >= 20:
        avg_vol = sum(volumes[-20:]) / 20
        vol_above_avg = avg_vol > 0 and volumes[-1] > 0 and volumes[-1] > avg_vol

    return sum([above_20sma, close_near_high, vol_above_avg])


def _compute_momentum(closes, highs, lows, lc):
    """Layer 4: Momentum (4 metrics)."""
    # MACD: MACD line > Signal line (12,26,9)
    e12s = compute_ema_series(closes, 12)
    e26s = compute_ema_series(closes, 26)
    macd_bull_cross = False
    if len(e12s) >= 26 and len(e26s) >= 26:
        macd_line = [
            (a - b) if (a is not None and b is not None) else None
            for a, b in zip(e12s, e26s)
        ]
        valid = [v for v in macd_line if v is not None]
        if len(valid) >= 9:
            sig = compute_ema(valid, 9)
            macd_bull_cross = sig is not None and valid[-1] > sig

    # 10-day Rate of Change > 0
    roc_positive = len(closes) >= 11 and closes[-11] > 0 and (closes[-1] / closes[-11] - 1) > 0

    # Momentum positive: Close > Close 10 days ago
    momentum_positive = len(closes) >= 11 and closes[-1] > closes[-11]

    # ADX(14) > 25 (trending market)
    adx_val = compute_adx(highs, lows, closes, 14)
    adx_above_25 = adx_val is not None and adx_val > 25

    passed = sum([macd_bull_cross, roc_positive, momentum_positive, adx_above_25])
    flags = {"macd_bull_cross": macd_bull_cross, "roc_positive": roc_positive}
    return passed, flags


def _compute_extremes(closes, highs, lows, volumes, dates, lc, today, above_20sma):
    """Layer 5: Extremes (4 metrics, hit_52w_low subtracts)."""
    cutoff_52w = (today - timedelta(days=365)).isoformat()
    yr = [(d, h, lo) for d, h, lo in zip(dates, highs, lows) if d >= cutoff_52w]

    hit_52w_high = False
    hit_52w_low = False
    if yr:
        max_52w = max(h for _, h, _ in yr)
        min_52w = min(lo for _, _, lo in yr)
        if max_52w > 0:
            hit_52w_high = lc >= max_52w * 0.98  # within 2%
        if min_52w > 0:
            hit_52w_low = lc <= min_52w * 1.02   # within 2%

    # Bollinger above mid = Close > 20-day SMA (same as above_20sma)
    bollinger_above_mid = above_20sma

    # MFI(14) > 50
    mfi_val = compute_mfi(highs, lows, closes, volumes, 14)
    mfi_above_50 = mfi_val is not None and mfi_val > 50

    # Bullish metrics count, bearish (hit_52w_low) subtracts
    bull_count = sum([hit_52w_high, bollinger_above_mid, mfi_above_50])
    passed = max(0, bull_count - (1 if hit_52w_low else 0))
    # Effective max = 3 bullish metrics (bearish subtracts)

    flags = {"hit_52w_high": hit_52w_high, "hit_52w_low": hit_52w_low}
    return passed, flags
