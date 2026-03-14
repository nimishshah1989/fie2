"""
FIE v3 — Technical Indicator Helpers
Pure-Python EMA, RSI, ADX, MFI, and calendar-period boundary utilities.
No external dependencies — operates on lists of floats.
"""

import calendar
from datetime import date, datetime, timedelta
from typing import Optional

# ─── EMA ─────────────────────────────────────────────────

def compute_ema(closes: list, period: int) -> Optional[float]:
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


def compute_ema_series(closes: list, period: int) -> list:
    """
    Compute EMA for every point in the series.
    Indices < (period - 1) return None.
    """
    if not closes or period <= 0:
        return [None] * len(closes)
    k = 2.0 / (period + 1)
    result = [None] * (period - 1)
    seed = sum(closes[:period]) / period
    result.append(seed)
    ema = seed
    for price in closes[period:]:
        ema = price * k + ema * (1 - k)
        result.append(ema)
    return result


# ─── RSI (Wilder Smoothing) ──────────────────────────────

def compute_rsi(closes: list, period: int = 14) -> Optional[float]:
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


# ─── ADX (Average Directional Index) ────────────────────

def compute_adx(
    highs: list, lows: list, closes: list, period: int = 14,
) -> Optional[float]:
    """
    Compute ADX using Wilder smoothing on +DI/-DI/TR.
    Requires at least (2 * period) bars after the initial seed.
    Returns None if insufficient data.
    """
    n = len(closes)
    if n < period + 1:
        return None

    plus_dm_list = []
    minus_dm_list = []
    tr_list = []

    for i in range(1, n):
        high_diff = highs[i] - highs[i - 1]
        low_diff = lows[i - 1] - lows[i]

        plus_dm = max(high_diff, 0.0) if high_diff > low_diff else 0.0
        minus_dm = max(low_diff, 0.0) if low_diff > high_diff else 0.0

        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        plus_dm_list.append(plus_dm)
        minus_dm_list.append(minus_dm)
        tr_list.append(tr)

    if len(tr_list) < period:
        return None

    # Wilder smoothing seed
    smoothed_plus_dm = sum(plus_dm_list[:period])
    smoothed_minus_dm = sum(minus_dm_list[:period])
    smoothed_tr = sum(tr_list[:period])

    dx_values = []

    for i in range(period, len(tr_list)):
        smoothed_plus_dm = smoothed_plus_dm - (smoothed_plus_dm / period) + plus_dm_list[i]
        smoothed_minus_dm = smoothed_minus_dm - (smoothed_minus_dm / period) + minus_dm_list[i]
        smoothed_tr = smoothed_tr - (smoothed_tr / period) + tr_list[i]

        if smoothed_tr == 0:
            continue
        plus_di = (smoothed_plus_dm / smoothed_tr) * 100
        minus_di = (smoothed_minus_dm / smoothed_tr) * 100
        di_sum = plus_di + minus_di
        if di_sum == 0:
            continue
        dx = abs(plus_di - minus_di) / di_sum * 100
        dx_values.append(dx)

    if len(dx_values) < period:
        return None

    # ADX = Wilder-smoothed DX
    adx = sum(dx_values[:period]) / period
    for dx in dx_values[period:]:
        adx = (adx * (period - 1) + dx) / period

    return round(adx, 2)


# ─── MFI (Money Flow Index) ─────────────────────────────

def compute_mfi(
    highs: list, lows: list, closes: list,
    volumes: list, period: int = 14,
) -> Optional[float]:
    """
    Compute Money Flow Index (volume-weighted RSI variant).
    Returns None if insufficient data or zero-volume bars in the lookback.
    """
    n = len(closes)
    if n < period + 1:
        return None

    # Verify non-zero volume in the lookback window
    window_volumes = volumes[-(period + 1):]
    if not all(v and v > 0 for v in window_volumes):
        return None

    typical_prices = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
    raw_money_flows = [tp * v for tp, v in zip(typical_prices, volumes)]

    pos_flow = 0.0
    neg_flow = 0.0

    for i in range(n - period, n):
        if typical_prices[i] > typical_prices[i - 1]:
            pos_flow += raw_money_flows[i]
        elif typical_prices[i] < typical_prices[i - 1]:
            neg_flow += raw_money_flows[i]

    if neg_flow == 0:
        return 100.0
    mf_ratio = pos_flow / neg_flow
    return round(100 - (100 / (1 + mf_ratio)), 2)


# ─── Monthly Resampling ─────────────────────────────────

def resample_to_monthly(date_close_pairs: list) -> list:
    """
    Resample daily (date_str, close) pairs to monthly last-close.
    Returns list of (YYYY-MM, close) sorted ascending.
    """
    monthly: dict = {}
    for date_str, close in sorted(date_close_pairs):
        month_key = date_str[:7]   # "YYYY-MM"
        monthly[month_key] = close   # last value wins (latest day in month)
    return sorted(monthly.items())


# ─── Weekly Resampling ───────────────────────────────────

def resample_to_weekly(date_close_pairs: list) -> list:
    """Resample daily (date_str, close) pairs to weekly last-close (ISO week)."""
    weekly: dict = {}
    for date_str, close in sorted(date_close_pairs):
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        week_key = dt.strftime("%Y-W%W")
        weekly[week_key] = close
    return sorted(weekly.items())


# ─── Calendar Period Boundaries ──────────────────────────

def prev_month_range(ref: date) -> tuple:
    """Return (start, end) of the calendar month prior to ref's month."""
    first_of_this_month = ref.replace(day=1)
    end = first_of_this_month - timedelta(days=1)
    start = end.replace(day=1)
    return start, end


def prev_quarter_range(ref: date) -> tuple:
    """Return (start, end) of the calendar quarter prior to ref's quarter.
    Quarters: Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec.
    """
    q = (ref.month - 1) // 3    # 0-based current quarter index
    if q == 0:
        # We're in Q1 -- previous quarter is Q4 of last year
        start = date(ref.year - 1, 10, 1)
        end = date(ref.year - 1, 12, 31)
    else:
        start_month = (q - 1) * 3 + 1
        end_month = q * 3
        start = date(ref.year, start_month, 1)
        _, last_day = calendar.monthrange(ref.year, end_month)
        end = date(ref.year, end_month, last_day)
    return start, end


def prev_year_range(ref: date) -> tuple:
    """Return (start, end) of the calendar year prior to ref's year."""
    return date(ref.year - 1, 1, 1), date(ref.year - 1, 12, 31)
