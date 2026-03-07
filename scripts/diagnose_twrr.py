"""
FIE v3 — TWRR Diagnostic Script
Compares our TWR unit_nav computation against broker's official SEBI TWRR figures.

Tests multiple TWR methods:
  1. Our current method (corpus-change adjusted)
  2. Off-by-one variant (apply cash flow to next day)
  3. Daily linking with geometric chain
  4. Modified Dietz for cross-check

Also checks calendar-date vs trading-day period alignment.

Usage:
    python3 scripts/diagnose_twrr.py
"""

import os
import sys
from pathlib import Path
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import math

# Add parent dir to path so we can import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env if dotenv is available
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / "fie2.env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Try .env
        env_path2 = Path(__file__).parent.parent / ".env"
        if env_path2.exists():
            load_dotenv(env_path2)
except ImportError:
    pass

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import pandas as pd
import numpy as np


# ============================================================
# DB CONNECTION
# ============================================================

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    # Fallback: read from fie2.env manually
    env_file = Path(__file__).parent.parent / "fie2.env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("DATABASE_URL="):
                DATABASE_URL = line.split("=", 1)[1].strip()
                break

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found. Set it in environment or fie2.env")
    sys.exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)


# ============================================================
# BROKER'S OFFICIAL TWRR VALUES (from SEBI Performance Report)
# ============================================================

# BJ53 — Momentum Leaders, inception 28-Sep-2020, as on 6-Mar-2026
BROKER_BJ53 = {
    '1M':  1.29,    # absolute (not annualized)
    '3M':  7.60,    # absolute
    '6M':  18.27,   # absolute
    '1Y':  28.59,   # annualized CAGR
    '2Y':  12.62,   # annualized CAGR
    '3Y':  25.51,   # annualized CAGR
    '4Y':  24.03,   # annualized CAGR
    '5Y':  22.69,   # annualized CAGR
    'SI':  36.15,   # annualized CAGR (inception 28-Sep-2020)
}

# JR100PASS — Passive, inception 02-Aug-2021, as on 6-Mar-2026
BROKER_JR100 = {
    '1M':  0.65,
    '3M':  6.29,
    '6M':  19.16,
    '1Y':  34.92,
    '2Y':  21.49,
    '3Y':  19.32,
    '4Y':  15.38,
    '5Y':  0.00,    # not applicable (inception < 5Y ago)
    'SI':  13.55,
}

# Broker's "Relative Performance [Weighted]" dates for BJ53
# SI: 28-Sep-2020 -> 6-Mar-2026
# 5Y: 5-Mar-2021 -> 6-Mar-2026
# 3Y: 6-Mar-2023 -> 6-Mar-2026
# 1Y: 6-Mar-2025 -> 6-Mar-2026
# 6M: 5-Sep-2025 -> 6-Mar-2026

# Broker's "Relative Performance [Weighted]" dates for JR100PASS
# SI: 2-Aug-2021 -> 6-Mar-2026
# 3Y: 6-Mar-2023 -> 6-Mar-2026
# 1Y: 6-Mar-2025 -> 6-Mar-2026
# 6M: 5-Sep-2025 -> 6-Mar-2026


# ============================================================
# PORTFOLIO CONFIG
# ============================================================

PORTFOLIOS = [
    {
        'id': 4,
        'name': 'BJ53 — Momentum Leaders',
        'ucc': 'BJ53',
        'inception_date': date(2020, 9, 28),
        'as_on_date': date(2026, 3, 6),
        'broker_twrr': BROKER_BJ53,
    },
    {
        'id': 5,
        'name': 'JR100PASS — Passive',
        'ucc': 'JR100PASS',
        'inception_date': date(2021, 8, 2),
        'as_on_date': date(2026, 3, 6),
        'broker_twrr': BROKER_JR100,
    },
]


# ============================================================
# HELPER: find closest available date
# ============================================================

def find_closest_date(target: date, available_dates: list[date], direction: str = 'both') -> date:
    """Find the closest date in available_dates to target.
    direction: 'before' (<=), 'after' (>=), 'both' (nearest).
    """
    if target in available_dates:
        return target
    before = [d for d in available_dates if d <= target]
    after = [d for d in available_dates if d >= target]
    if direction == 'before':
        return max(before) if before else min(available_dates)
    if direction == 'after':
        return min(after) if after else max(available_dates)
    # both — pick nearest
    candidates = []
    if before:
        candidates.append(max(before))
    if after:
        candidates.append(min(after))
    return min(candidates, key=lambda d: abs((d - target).days))


# ============================================================
# CALENDAR DATE PERIODS (matching broker convention)
# ============================================================

def get_calendar_period_dates(as_on: date) -> dict[str, date]:
    """Compute calendar-based period start dates like the broker uses.
    For 1M: same day last month. For 1Y: same day last year. Etc.
    The broker uses calendar dates, NOT trading day counts.
    """
    return {
        '1M':  as_on - relativedelta(months=1),
        '3M':  as_on - relativedelta(months=3),
        '6M':  as_on - relativedelta(months=6),
        '1Y':  as_on - relativedelta(years=1),
        '2Y':  as_on - relativedelta(years=2),
        '3Y':  as_on - relativedelta(years=3),
        '4Y':  as_on - relativedelta(years=4),
        '5Y':  as_on - relativedelta(years=5),
    }


# ============================================================
# METHOD 1: OUR CURRENT TWR (corpus-change based, same-day)
# ============================================================

def compute_twr_current(df: pd.DataFrame) -> pd.Series:
    """Our current method: unit_nav = 100 on day 0.
    For each subsequent day:
      cash_flow = corpus[i] - corpus[i-1]
      adjusted_prev = nav[i-1] + cash_flow
      daily_return = nav[i] / adjusted_prev
      unit_nav[i] = unit_nav[i-1] * daily_return
    """
    n = len(df)
    unit_nav = np.zeros(n)
    unit_nav[0] = 100.0

    for i in range(1, n):
        prev_nav = df['nav'].iloc[i - 1]
        curr_nav = df['nav'].iloc[i]
        prev_corpus = df['corpus'].iloc[i - 1]
        curr_corpus = df['corpus'].iloc[i]

        if prev_nav <= 0:
            unit_nav[i] = unit_nav[i - 1]
            continue

        cash_flow = 0.0
        if pd.notna(prev_corpus) and pd.notna(curr_corpus):
            cash_flow = curr_corpus - prev_corpus

        adjusted_prev = prev_nav + cash_flow
        if adjusted_prev <= 0:
            unit_nav[i] = unit_nav[i - 1]
        else:
            daily_return = curr_nav / adjusted_prev
            unit_nav[i] = unit_nav[i - 1] * daily_return

    return pd.Series(unit_nav, index=df.index)


# ============================================================
# METHOD 2: OFF-BY-ONE (apply cash flow to PREVIOUS day's NAV,
#            i.e., cash_flow detected from corpus change but
#            added to prev_nav BEFORE the return happens)
# ============================================================
# This is actually the same as Method 1. Let me instead test:
# cash_flow applies on the NEXT day (shift by 1).

def compute_twr_next_day_flow(df: pd.DataFrame) -> pd.Series:
    """Variant: detect corpus change between day i-1 and day i,
    but apply it as if the cash arrived at END of day i
    (i.e., don't adjust the denominator for that day's return,
    adjust the NEXT day's denominator instead).

    This means: on day i where corpus changed,
    daily_return[i] = nav[i] / nav[i-1]  (NO adjustment)
    But next day: adjusted_prev = nav[i] - cash_flow  (remove the cash)
    """
    n = len(df)
    unit_nav = np.zeros(n)
    unit_nav[0] = 100.0

    pending_cash_flow = 0.0  # cash flow to apply on next day

    for i in range(1, n):
        prev_nav = df['nav'].iloc[i - 1]
        curr_nav = df['nav'].iloc[i]
        prev_corpus = df['corpus'].iloc[i - 1]
        curr_corpus = df['corpus'].iloc[i]

        if prev_nav <= 0:
            unit_nav[i] = unit_nav[i - 1]
            continue

        # Detect cash flow on this day
        cash_flow = 0.0
        if pd.notna(prev_corpus) and pd.notna(curr_corpus):
            cash_flow = curr_corpus - prev_corpus

        # Apply PREVIOUS day's pending cash flow to adjust denominator
        adjusted_prev = prev_nav + pending_cash_flow
        pending_cash_flow = cash_flow  # save for next iteration

        if adjusted_prev <= 0:
            unit_nav[i] = unit_nav[i - 1]
        else:
            daily_return = curr_nav / adjusted_prev
            unit_nav[i] = unit_nav[i - 1] * daily_return

    return pd.Series(unit_nav, index=df.index)


# ============================================================
# METHOD 3: "True" TWR — split at each cash flow, compute
#            sub-period returns, chain them
# ============================================================

def compute_twr_true_linking(df: pd.DataFrame) -> pd.Series:
    """Standard TWR: identify cash flow dates, compute holding
    period returns between them, and geometrically link.

    On a cash flow day:
      - End the current sub-period with the NAV BEFORE the cash flow
      - The NAV before cash flow = curr_nav - cash_flow (the portfolio
        value excluding the new money)
      - sub_period_return = nav_before_flow / start_nav
      - Start new sub-period with start_nav = curr_nav (includes the cash)

    For the SEBI standard, the sub-period return on cash flow day is:
      R = (NAV_end_of_day_before_flow) / (NAV_start_of_subperiod) - 1
    Then:
      R_next_subperiod starts from NAV_after_flow
    """
    n = len(df)
    unit_nav = np.zeros(n)
    unit_nav[0] = 100.0

    # For each day, compute the cumulative TWR product
    cum_product = 1.0
    sub_period_start_nav = df['nav'].iloc[0]

    for i in range(1, n):
        prev_nav = df['nav'].iloc[i - 1]
        curr_nav = df['nav'].iloc[i]
        prev_corpus = df['corpus'].iloc[i - 1]
        curr_corpus = df['corpus'].iloc[i]

        cash_flow = 0.0
        if pd.notna(prev_corpus) and pd.notna(curr_corpus):
            cash_flow = curr_corpus - prev_corpus

        if abs(cash_flow) > 0.01 and sub_period_start_nav > 0:
            # End sub-period: value before cash flow = curr_nav - cash_flow
            nav_before_flow = curr_nav - cash_flow
            sub_return = nav_before_flow / sub_period_start_nav
            cum_product *= sub_return
            # Start new sub-period from curr_nav (which includes the cash)
            sub_period_start_nav = curr_nav

        # Compute unit_nav as cumulative product so far,
        # plus current sub-period's partial return
        if sub_period_start_nav > 0:
            current_sub_return = curr_nav / sub_period_start_nav
            unit_nav[i] = 100.0 * cum_product * current_sub_return
        else:
            unit_nav[i] = unit_nav[i - 1]

    return pd.Series(unit_nav, index=df.index)


# ============================================================
# METHOD 4: SEBI-standard daily TWR
# The SEBI/GIPS standard for TWR:
#   On each day WITHOUT cash flow: R_t = NAV_t / NAV_{t-1} - 1
#   On each day WITH cash flow: R_t = NAV_t / (NAV_{t-1} + CF_t) - 1
#     where CF_t is the external cash flow on day t
# Then: TWR = Product(1 + R_t) - 1
# This is actually our Method 1. But the question is WHEN the
# cash flow occurs (beginning vs end of day).
# ============================================================

def compute_twr_begin_of_day_flow(df: pd.DataFrame) -> pd.Series:
    """SEBI method: cash flow happens at BEGINNING of day.

    R_t = V_t / (V_{t-1} + CF_t)
    where CF_t = corpus_t - corpus_{t-1}

    This is identical to our Method 1.
    """
    return compute_twr_current(df)


def compute_twr_end_of_prev_day_flow(df: pd.DataFrame) -> pd.Series:
    """Variant: cash flow at END of previous day.

    On day where corpus changes: the cash was added at end of prev day.
    So prev day's ending value includes the cash.
    R_t = V_t / V_{t-1}  (no adjustment needed since cash is already in V_{t-1})

    But wait — that doesn't make sense because NAV already reflects
    the cash in the portfolio. The corpus change tells us external
    money came in. We need to REMOVE it from the return.

    If cash came at end of day i-1:
    V_{i-1}_before_cash = V_{i-1} - CF
    R_i = V_i / V_{i-1}  (cash already incorporated)

    Actually, we need to split differently:
    Sub-period 1: up to end of day i-1 BEFORE cash: R = V_{i-1} / V_start
    Sub-period 2: starts at V_{i-1} + CF = V_{i-1}_adjusted
    R_next = V_i / (V_{i-1} + CF)

    Hmm, this is still the same as Method 1. The timing doesn't matter
    if we use the formula R = V_t / (V_{t-1} + CF_t).

    Let me try a different interpretation: corpus change between day i-1
    and day i means cash flowed on day i-1 AFTER market close.
    So the denominator for day i should be (V_{i-1}), and the cash
    effect is already in V_{i-1} (because it was added after close).
    Wait, that also doesn't work because V_{i-1} is the NAV at close
    of day i-1 and if cash was added after close, V_{i-1} wouldn't
    reflect it, but corpus_{i} would.

    Actually, let's test: what if the corpus change happened on the SAME
    day but we should NOT adjust the prev NAV? Instead we should compute:
    R_t = (V_t - CF_t) / V_{t-1}
    i.e., remove the cash flow from today's NAV.
    """
    n = len(df)
    unit_nav = np.zeros(n)
    unit_nav[0] = 100.0

    for i in range(1, n):
        prev_nav = df['nav'].iloc[i - 1]
        curr_nav = df['nav'].iloc[i]
        prev_corpus = df['corpus'].iloc[i - 1]
        curr_corpus = df['corpus'].iloc[i]

        if prev_nav <= 0:
            unit_nav[i] = unit_nav[i - 1]
            continue

        cash_flow = 0.0
        if pd.notna(prev_corpus) and pd.notna(curr_corpus):
            cash_flow = curr_corpus - prev_corpus

        # Remove cash flow from today's nav (cash arrived today,
        # so today's return should exclude it)
        adjusted_curr = curr_nav - cash_flow
        daily_return = adjusted_curr / prev_nav

        unit_nav[i] = unit_nav[i - 1] * daily_return

    return pd.Series(unit_nav, index=df.index)


# ============================================================
# MODIFIED DIETZ (for cross-check)
# ============================================================

def compute_modified_dietz(df: pd.DataFrame, start_date: date, end_date: date) -> float:
    """Modified Dietz return for a specific period.
    R = (V_end - V_start - sum(CF)) / (V_start + sum(w_i * CF_i))
    where w_i = (D - d_i) / D, D = total days, d_i = day of cash flow
    """
    mask = (df['date'] >= start_date) & (df['date'] <= end_date)
    period = df[mask].copy()

    if len(period) < 2:
        return float('nan')

    v_start = period['nav'].iloc[0]
    v_end = period['nav'].iloc[-1]
    total_days = (end_date - start_date).days

    if total_days <= 0:
        return float('nan')

    # Identify cash flows
    cash_flows = []
    for i in range(1, len(period)):
        prev_corpus = period['corpus'].iloc[i - 1]
        curr_corpus = period['corpus'].iloc[i]
        if pd.notna(prev_corpus) and pd.notna(curr_corpus):
            cf = curr_corpus - prev_corpus
            if abs(cf) > 0.01:
                cf_date = period['date'].iloc[i]
                days_from_start = (cf_date - start_date).days
                weight = (total_days - days_from_start) / total_days
                cash_flows.append({'cf': cf, 'weight': weight, 'date': cf_date})

    sum_cf = sum(c['cf'] for c in cash_flows)
    weighted_cf = sum(c['cf'] * c['weight'] for c in cash_flows)

    denominator = v_start + weighted_cf
    if denominator <= 0:
        return float('nan')

    return (v_end - v_start - sum_cf) / denominator


# ============================================================
# RETURN COMPUTATION (absolute vs annualized)
# ============================================================

def compute_return(start_val: float, end_val: float, start_date: date,
                   end_date: date, annualize_threshold_years: float = 1.0) -> tuple[float, str]:
    """Compute return matching broker convention:
    - Periods < 1Y: absolute return %
    - Periods >= 1Y: CAGR (annualized) %
    Returns (return_pct, method_label)
    """
    if start_val <= 0:
        return (float('nan'), 'error')

    total_return = (end_val / start_val) - 1
    years = (end_date - start_date).days / 365.25

    if years < annualize_threshold_years:
        return (total_return * 100, 'absolute')

    if total_return <= -1:
        return (-100.0, 'cagr')

    cagr = ((end_val / start_val) ** (1 / years) - 1) * 100
    return (cagr, 'cagr')


# ============================================================
# MAIN DIAGNOSTIC
# ============================================================

def diagnose_portfolio(config: dict, db_session) -> None:
    portfolio_id = config['id']
    name = config['name']
    inception = config['inception_date']
    as_on = config['as_on_date']
    broker = config['broker_twrr']

    print(f"\n{'='*80}")
    print(f"  TWRR DIAGNOSTIC: {name}")
    print(f"  Portfolio ID: {portfolio_id}, Inception: {inception}, As On: {as_on}")
    print(f"{'='*80}")

    # Load data
    result = db_session.execute(text("""
        SELECT date, nav, corpus, equity_holding, etf_investment,
               cash_equivalent, bank_balance, unit_nav, liquidity_pct
        FROM pms_nav_daily
        WHERE portfolio_id = :pid
        ORDER BY date
    """), {'pid': portfolio_id})

    rows = result.fetchall()
    if not rows:
        print("  NO DATA FOUND!")
        return

    df = pd.DataFrame(rows, columns=[
        'date', 'nav', 'corpus', 'equity_holding', 'etf_investment',
        'cash_equivalent', 'bank_balance', 'unit_nav_db', 'liquidity_pct'
    ])
    df['date'] = pd.to_datetime(df['date']).dt.date

    print(f"\n  Data: {len(df)} days, {df['date'].iloc[0]} to {df['date'].iloc[-1]}")
    print(f"  First NAV: {df['nav'].iloc[0]:,.2f}")
    print(f"  Last NAV:  {df['nav'].iloc[-1]:,.2f}")
    print(f"  First corpus: {df['corpus'].iloc[0]:,.2f}")
    print(f"  Last corpus:  {df['corpus'].iloc[-1]:,.2f}")

    # Check: is last date = as_on date?
    last_date = df['date'].iloc[-1]
    if last_date != as_on:
        print(f"\n  WARNING: Last data date ({last_date}) != broker as_on date ({as_on})")
        print(f"  Using last available date: {last_date}")
        as_on = last_date

    # ── 1. Identify all corpus changes ──
    df['corpus_change'] = df['corpus'].diff()
    cash_flow_days = df[df['corpus_change'].abs() > 0.01].copy()
    print(f"\n  Corpus changes: {len(cash_flow_days)} days with cash flows")

    if len(cash_flow_days) > 0:
        print(f"\n  {'Date':<14} {'Cash Flow':>16} {'NAV Before':>16} {'NAV After':>16} {'Corpus After':>16}")
        print(f"  {'-'*14} {'-'*16} {'-'*16} {'-'*16} {'-'*16}")
        for _, row in cash_flow_days.iterrows():
            idx = df.index[df['date'] == row['date']].tolist()
            if idx:
                i = idx[0]
                prev_nav = df['nav'].iloc[i - 1] if i > 0 else 0
                print(f"  {row['date']}   {row['corpus_change']:>16,.2f} "
                      f"{prev_nav:>16,.2f} {row['nav']:>16,.2f} {row['corpus']:>16,.2f}")

    # ── 2. Compute TWR with all methods ──
    print(f"\n  Computing TWR with 5 methods...")

    methods = {
        'M1: Current (same-day CF adj)': compute_twr_current(df),
        'M2: Next-day CF application': compute_twr_next_day_flow(df),
        'M3: True linking (sub-periods)': compute_twr_true_linking(df),
        'M4: Remove CF from curr NAV': compute_twr_end_of_prev_day_flow(df),
    }

    # Store DB unit_nav for comparison
    if df['unit_nav_db'].notna().any():
        methods['DB: Stored unit_nav'] = df['unit_nav_db'].copy()

    # ── 3. Compute period returns using CALENDAR dates (like broker) ──
    available_dates = df['date'].tolist()
    calendar_starts = get_calendar_period_dates(as_on)

    # Add SI
    calendar_starts['SI'] = inception

    print(f"\n  Calendar period start dates (broker convention):")
    for period, start_dt in sorted(calendar_starts.items(), key=lambda x: x[0]):
        closest = find_closest_date(start_dt, available_dates, direction='after')
        print(f"    {period:>4}: target {start_dt}, closest available: {closest}")

    # ── 4. Compare all methods against broker for each period ──
    periods_to_check = ['1M', '3M', '6M', '1Y', '2Y', '3Y', '4Y', '5Y', 'SI']

    print(f"\n  {'':=<120}")
    print(f"  PERIOD RETURN COMPARISON (broker convention: <1Y absolute, >=1Y annualized CAGR)")
    print(f"  {'':=<120}")

    header = f"  {'Period':<6} {'Broker':>8}"
    for method_name in methods:
        short_name = method_name[:20]
        header += f" | {short_name:>20}"
    header += f" | {'Mod.Dietz':>10}"
    print(header)
    print(f"  {'-'*len(header)}")

    for period in periods_to_check:
        if period not in calendar_starts:
            continue

        broker_val = broker.get(period, None)
        if broker_val is None:
            continue

        target_start = calendar_starts[period]
        # Find closest available date ON OR AFTER the target
        start_dt = find_closest_date(target_start, available_dates, direction='after')
        end_dt = find_closest_date(as_on, available_dates, direction='before')

        # Determine if this period should be annualized
        years = (end_dt - start_dt).days / 365.25
        annualize = years >= 1.0

        row = f"  {period:<6} {broker_val:>8.2f}"

        for method_name, unit_series in methods.items():
            start_idx = df.index[df['date'] == start_dt].tolist()
            end_idx = df.index[df['date'] == end_dt].tolist()

            if not start_idx or not end_idx:
                row += f" | {'N/A':>20}"
                continue

            start_val = unit_series.iloc[start_idx[0]]
            end_val = unit_series.iloc[end_idx[0]]

            if pd.isna(start_val) or pd.isna(end_val) or start_val <= 0:
                row += f" | {'N/A':>20}"
                continue

            ret, method_label = compute_return(start_val, end_val, start_dt, end_dt)
            diff = ret - broker_val
            row += f" | {ret:>8.2f} ({diff:>+6.2f})"

        # Modified Dietz
        md_ret = compute_modified_dietz(df, start_dt, end_dt)
        if annualize and not math.isnan(md_ret) and md_ret > -1:
            # Annualize the Dietz return
            md_annual = ((1 + md_ret) ** (1 / years) - 1) * 100
            md_str = f"{md_annual:>8.2f}"
        elif not math.isnan(md_ret):
            md_str = f"{md_ret * 100:>8.2f}"
        else:
            md_str = "N/A"
        row += f" | {md_str:>10}"

        print(row)

    # ── 5. Also compute using TRADING DAY counts (our current approach) ──
    PERIOD_TRADING_DAYS = {
        '1M': 21, '3M': 63, '6M': 126,
        '1Y': 252, '3Y': 756, '5Y': 1260,
    }

    print(f"\n  {'':=<120}")
    print(f"  TRADING-DAY PERIOD COMPARISON (our current approach: N trading days lookback)")
    print(f"  {'':=<120}")

    header2 = f"  {'Period':<6} {'TDays':>6} {'Broker':>8}"
    for method_name in methods:
        short_name = method_name[:20]
        header2 += f" | {short_name:>20}"
    print(header2)
    print(f"  {'-'*len(header2)}")

    for period, trading_days in PERIOD_TRADING_DAYS.items():
        broker_val = broker.get(period, None)
        if broker_val is None:
            continue

        if len(df) < trading_days:
            print(f"  {period:<6} {trading_days:>6} {broker_val:>8.2f}  (insufficient data)")
            continue

        end_idx_num = len(df) - 1
        start_idx_num = max(0, end_idx_num - trading_days + 1)

        start_dt = df['date'].iloc[start_idx_num]
        end_dt = df['date'].iloc[end_idx_num]
        years = (end_dt - start_dt).days / 365.25

        row = f"  {period:<6} {trading_days:>6} {broker_val:>8.2f}"

        for method_name, unit_series in methods.items():
            start_val = unit_series.iloc[start_idx_num]
            end_val = unit_series.iloc[end_idx_num]

            if pd.isna(start_val) or pd.isna(end_val) or start_val <= 0:
                row += f" | {'N/A':>20}"
                continue

            ret, method_label = compute_return(start_val, end_val, start_dt, end_dt)
            diff = ret - broker_val
            row += f" | {ret:>8.2f} ({diff:>+6.2f})"

        print(row)
        # Show what dates we're using
        print(f"         dates: {start_dt} to {end_dt} ({(end_dt - start_dt).days} cal days, {years:.2f} years)")

    # ── 6. Detailed daily comparison around cash flow dates ──
    print(f"\n  {'':=<80}")
    print(f"  DAILY DETAIL AROUND CASH FLOW DATES (+-2 days)")
    print(f"  {'':=<80}")

    m1 = methods['M1: Current (same-day CF adj)']
    m3 = methods['M3: True linking (sub-periods)']
    m4 = methods['M4: Remove CF from curr NAV']

    for _, cf_row in cash_flow_days.head(15).iterrows():
        cf_date = cf_row['date']
        cf_idx_list = df.index[df['date'] == cf_date].tolist()
        if not cf_idx_list:
            continue
        cf_idx = cf_idx_list[0]

        start_i = max(0, cf_idx - 2)
        end_i = min(len(df) - 1, cf_idx + 2)

        print(f"\n  Cash flow on {cf_date}: {cf_row['corpus_change']:+,.2f}")
        print(f"  {'Date':<12} {'NAV':>14} {'Corpus':>14} {'Corp Chg':>12} "
              f"{'M1 UnitNAV':>12} {'M3 UnitNAV':>12} {'M4 UnitNAV':>12} "
              f"{'M1 DayRet':>10} {'M4 DayRet':>10}")

        for i in range(start_i, end_i + 1):
            d = df['date'].iloc[i]
            nav = df['nav'].iloc[i]
            corpus = df['corpus'].iloc[i]
            corp_chg = df['corpus_change'].iloc[i] if i > 0 else 0

            m1_val = m1.iloc[i]
            m3_val = m3.iloc[i]
            m4_val = m4.iloc[i]

            m1_day_ret = (m1.iloc[i] / m1.iloc[i - 1] - 1) * 100 if i > 0 and m1.iloc[i - 1] > 0 else 0
            m4_day_ret = (m4.iloc[i] / m4.iloc[i - 1] - 1) * 100 if i > 0 and m4.iloc[i - 1] > 0 else 0

            marker = " ***" if d == cf_date else ""
            print(f"  {d}   {nav:>14,.2f} {corpus:>14,.2f} {corp_chg:>12,.2f} "
                  f"{m1_val:>12.4f} {m3_val:>12.4f} {m4_val:>12.4f} "
                  f"{m1_day_ret:>10.4f} {m4_day_ret:>10.4f}{marker}")

    # ── 7. Summary: which method matches best? ──
    print(f"\n  {'':=<80}")
    print(f"  SUMMARY: BEST METHOD FIT")
    print(f"  {'':=<80}")

    for method_name, unit_series in methods.items():
        total_abs_error = 0
        count = 0

        for period in periods_to_check:
            if period not in calendar_starts:
                continue
            broker_val = broker.get(period, None)
            if broker_val is None or broker_val == 0.0:
                continue

            target_start = calendar_starts[period]
            start_dt = find_closest_date(target_start, available_dates, direction='after')
            end_dt = find_closest_date(as_on, available_dates, direction='before')

            start_idx = df.index[df['date'] == start_dt].tolist()
            end_idx = df.index[df['date'] == end_dt].tolist()

            if not start_idx or not end_idx:
                continue

            start_val = unit_series.iloc[start_idx[0]]
            end_val = unit_series.iloc[end_idx[0]]

            if pd.isna(start_val) or pd.isna(end_val) or start_val <= 0:
                continue

            ret, _ = compute_return(start_val, end_val, start_dt, end_dt)
            if not math.isnan(ret):
                total_abs_error += abs(ret - broker_val)
                count += 1

        if count > 0:
            avg_error = total_abs_error / count
            print(f"  {method_name:<40} avg |error|: {avg_error:>8.4f}%  (across {count} periods)")
        else:
            print(f"  {method_name:<40} no data")

    # ── 8. Check for data quality issues ──
    print(f"\n  {'':=<80}")
    print(f"  DATA QUALITY CHECKS")
    print(f"  {'':=<80}")

    # Check for duplicate dates
    dupes = df[df.duplicated(subset=['date'], keep=False)]
    if len(dupes) > 0:
        print(f"  WARNING: {len(dupes)} duplicate date entries!")

    # Check for gaps > 5 calendar days (excluding weekends/holidays)
    date_diffs = df['date'].diff().dropna()
    big_gaps = [(df['date'].iloc[i], (df['date'].iloc[i] - df['date'].iloc[i-1]).days)
                for i in range(1, len(df))
                if (df['date'].iloc[i] - df['date'].iloc[i-1]).days > 5]
    if big_gaps:
        print(f"  Gaps > 5 calendar days: {len(big_gaps)}")
        for gap_date, gap_days in big_gaps[:10]:
            print(f"    {gap_date}: {gap_days} day gap")

    # Check for negative NAV
    neg_nav = df[df['nav'] <= 0]
    if len(neg_nav) > 0:
        print(f"  WARNING: {len(neg_nav)} days with NAV <= 0!")

    # Check for very large daily NAV swings
    df['nav_pct_change'] = df['nav'].pct_change() * 100
    big_swings = df[df['nav_pct_change'].abs() > 10]
    if len(big_swings) > 0:
        print(f"  Days with >10% NAV change: {len(big_swings)}")
        for _, row in big_swings.iterrows():
            print(f"    {row['date']}: {row['nav_pct_change']:+.2f}% "
                  f"(NAV: {row['nav']:,.2f}, corpus change: {row['corpus_change']:+,.2f})")

    # ── 9. Final: show the stored DB unit_nav's implied CAGR ──
    if df['unit_nav_db'].notna().any():
        first_db_unit = df.loc[df['unit_nav_db'].first_valid_index(), 'unit_nav_db']
        last_db_unit = df.loc[df['unit_nav_db'].last_valid_index(), 'unit_nav_db']
        first_db_date = df.loc[df['unit_nav_db'].first_valid_index(), 'date']
        last_db_date = df.loc[df['unit_nav_db'].last_valid_index(), 'date']
        years = (last_db_date - first_db_date).days / 365.25
        if years > 0 and first_db_unit > 0:
            db_cagr = ((last_db_unit / first_db_unit) ** (1 / years) - 1) * 100
            print(f"\n  DB stored unit_nav SI CAGR: {db_cagr:.2f}% "
                  f"(unit_nav: {first_db_unit:.4f} -> {last_db_unit:.4f}, {years:.2f} years)")
            print(f"  Broker SI CAGR: {broker.get('SI', 'N/A')}%")
            print(f"  Gap: {db_cagr - broker.get('SI', 0):+.2f}%")


def main():
    print("="*80)
    print("  FIE v3 — TWRR Diagnostic Tool")
    print("  Comparing our TWR computation against broker SEBI TWRR figures")
    print("="*80)

    db = Session()
    try:
        # Quick connectivity check
        result = db.execute(text("SELECT COUNT(*) FROM pms_nav_daily"))
        total_rows = result.scalar()
        print(f"\n  Connected to DB. Total pms_nav_daily rows: {total_rows}")

        # Check what portfolios exist
        result = db.execute(text("""
            SELECT mp.id, mp.name, mp.ucc_code, mp.inception_date, mp.portfolio_type,
                   COUNT(pn.id) as nav_count,
                   MIN(pn.date) as first_date, MAX(pn.date) as last_date
            FROM model_portfolios mp
            LEFT JOIN pms_nav_daily pn ON pn.portfolio_id = mp.id
            WHERE mp.portfolio_type = 'pms'
            GROUP BY mp.id, mp.name, mp.ucc_code, mp.inception_date, mp.portfolio_type
            ORDER BY mp.id
        """))
        portfolios = result.fetchall()
        print(f"\n  PMS portfolios in DB:")
        for p in portfolios:
            print(f"    ID {p[0]}: {p[1]} (UCC: {p[2]}, inception: {p[3]}, "
                  f"type: {p[4]}, {p[5]} NAV rows, {p[6]} to {p[7]})")

        for config in PORTFOLIOS:
            diagnose_portfolio(config, db)

    except Exception as exc:
        print(f"\n  ERROR: {exc}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

    print(f"\n{'='*80}")
    print("  Diagnostic complete.")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
