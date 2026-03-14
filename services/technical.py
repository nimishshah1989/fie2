"""
FIE v3 — Technical Indicator Helpers
Pure-Python EMA, RSI, and calendar-period boundary utilities.
No external dependencies — operates on lists of floats.
"""

import calendar
from datetime import date, datetime, timedelta
from typing import Optional

# ─── EMA ─────────────────────────────────────────────────

def compute_ema(closes: list[float], period: int) -> Optional[float]:
    """
    Compute the most recent EMA value for a given period.
    Uses standard smoothing factor k = 2 / (N + 1).
    Returns None if fewer than `period` data points available.
    """
    if len(closes) < period:
        return None
    k = 2.0 / (period + 1)
    ema = sum(closes[:period]) / period   # seed: SMA of first N values
    for price in closes[period:]:
        ema = price * k + ema * (1 - k)
    return round(ema, 4)


def compute_ema_series(closes: list[float], period: int) -> list[Optional[float]]:
    """
    Compute EMA for every point in the series.
    Indices < (period - 1) return None.
    """
    if not closes or period <= 0:
        return [None] * len(closes)
    k = 2.0 / (period + 1)
    result: list[Optional[float]] = [None] * (period - 1)
    seed = sum(closes[:period]) / period
    result.append(seed)
    ema = seed
    for price in closes[period:]:
        ema = price * k + ema * (1 - k)
        result.append(ema)
    return result


# ─── RSI (Wilder Smoothing) ──────────────────────────────

def compute_rsi(closes: list[float], period: int = 14) -> Optional[float]:
    """
    Compute the most recent RSI using Wilder smoothing.
    Returns None if fewer than (period + 1) data points available.
    """
    if len(closes) < period + 1:
        return None

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [abs(min(d, 0.0)) for d in deltas]

    # Seed: simple average of first `period` changes
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    # Wilder smoothing for remaining values
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


# ─── Monthly Resampling ─────────────────────────────────

def resample_to_monthly(date_close_pairs: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """
    Resample daily (date_str, close) pairs to monthly last-close.
    Returns list of (YYYY-MM, close) sorted ascending.
    """
    monthly: dict[str, float] = {}
    for date_str, close in sorted(date_close_pairs):
        month_key = date_str[:7]   # "YYYY-MM"
        monthly[month_key] = close   # last value wins (latest day in month)
    return sorted(monthly.items())


# ─── Weekly Resampling ───────────────────────────────────

def resample_to_weekly(date_close_pairs: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """Resample daily (date_str, close) pairs to weekly last-close (ISO week)."""
    weekly: dict[str, float] = {}
    for date_str, close in sorted(date_close_pairs):
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        week_key = dt.strftime("%Y-W%W")
        weekly[week_key] = close
    return sorted(weekly.items())


# ─── Calendar Period Boundaries ──────────────────────────

def prev_month_range(ref: date) -> tuple[date, date]:
    """Return (start, end) of the calendar month prior to ref's month."""
    first_of_this_month = ref.replace(day=1)
    end = first_of_this_month - timedelta(days=1)
    start = end.replace(day=1)
    return start, end


def prev_quarter_range(ref: date) -> tuple[date, date]:
    """Return (start, end) of the calendar quarter prior to ref's quarter.
    Quarters: Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec.
    """
    q = (ref.month - 1) // 3    # 0-based current quarter index
    if q == 0:
        # We're in Q1 — previous quarter is Q4 of last year
        start = date(ref.year - 1, 10, 1)
        end = date(ref.year - 1, 12, 31)
    else:
        start_month = (q - 1) * 3 + 1
        end_month = q * 3
        start = date(ref.year, start_month, 1)
        _, last_day = calendar.monthrange(ref.year, end_month)
        end = date(ref.year, end_month, last_day)
    return start, end


def prev_year_range(ref: date) -> tuple[date, date]:
    """Return (start, end) of the calendar year prior to ref's year."""
    return date(ref.year - 1, 1, 1), date(ref.year - 1, 12, 31)
