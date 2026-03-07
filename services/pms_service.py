"""
FIE v3 — PMS Service
Time-weighted return (TWR) computation, risk/return metrics,
drawdown detection, monthly returns, and portfolio summary.
Excel parsing is in services/pms_parser.py.
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from models import PmsNavDaily, PortfolioMetric, DrawdownEvent

# Re-export parsers so existing imports still work
from services.pms_parser import parse_nav_excel, parse_transaction_excel  # noqa: F401

logger = logging.getLogger("fie_v3.pms_service")

# Risk-free rate for India (7% annualized, per RBI benchmark)
RISK_FREE_RATE = 0.07
TRADING_DAYS_PER_YEAR = 252

# Base value for TWR unit_nav series — represents 100% of corpus invested
TWR_BASE_VALUE = 100.0


# ═══════════════════════════════════════════════════════════
#  TIME-WEIGHTED RETURN (TWR) — UNIT NAV
# ═══════════════════════════════════════════════════════════

def compute_twr_unit_nav(portfolio_id: int, db: Session) -> int:
    """Compute TWR-adjusted unit NAV for a portfolio.

    Uses corpus changes to detect capital inflows/outflows.
    For each day with a corpus change, the daily return is adjusted
    so that the cash flow does not inflate/deflate the return.

    On inception day: if NAV differs from corpus (pre-existing gain/loss),
    unit_nav captures this as 100 * (NAV / corpus). This matches the
    SEBI TWRR convention where TWR tracks return on invested capital.

    Returns count of records updated.
    """
    rows = (
        db.query(PmsNavDaily)
        .filter(PmsNavDaily.portfolio_id == portfolio_id)
        .order_by(PmsNavDaily.date)
        .all()
    )
    if not rows:
        return 0

    # Day 0: capture any pre-existing gain/loss relative to corpus
    # If NAV > corpus on inception, the portfolio already had gains
    # before our data begins — the broker's TWRR includes this.
    nav_0 = rows[0].nav
    corpus_0 = rows[0].corpus
    if corpus_0 and corpus_0 > 0 and nav_0 > 0:
        rows[0].unit_nav = round(TWR_BASE_VALUE * (nav_0 / corpus_0), 6)
    else:
        rows[0].unit_nav = TWR_BASE_VALUE
    count = 1

    for i in range(1, len(rows)):
        prev_nav = rows[i - 1].nav
        curr_nav = rows[i].nav
        prev_corpus = rows[i - 1].corpus
        curr_corpus = rows[i].corpus

        if prev_nav <= 0:
            rows[i].unit_nav = rows[i - 1].unit_nav
            count += 1
            continue

        # Detect capital flow from corpus change
        cash_flow = 0.0
        if prev_corpus is not None and curr_corpus is not None:
            cash_flow = curr_corpus - prev_corpus

        # Adjusted denominator: previous NAV + any cash inflow that day
        # This neutralizes the effect of capital additions/withdrawals
        adjusted_prev = prev_nav + cash_flow

        if adjusted_prev <= 0:
            # Defensive: if corpus withdrawal exceeded NAV, carry forward
            rows[i].unit_nav = rows[i - 1].unit_nav
        else:
            daily_return = curr_nav / adjusted_prev
            rows[i].unit_nav = round(rows[i - 1].unit_nav * daily_return, 6)
        count += 1

    db.commit()
    logger.info("Computed TWR unit_nav for %d days, portfolio %d (final: %.2f)",
                count, portfolio_id, rows[-1].unit_nav)
    return count


# ═══════════════════════════════════════════════════════════
#  RISK / RETURN METRICS (uses unit_nav for TWR accuracy)
# ═══════════════════════════════════════════════════════════

def calculate_risk_metrics(
    nav_series: pd.Series,
    dates: pd.Series,
    base_value: Optional[float] = None,
) -> dict:
    """Compute risk/return metrics from a unit NAV time series.

    Args:
        nav_series: pd.Series of unit NAV values (TWR-adjusted, sorted by date)
        dates: pd.Series of corresponding dates
        base_value: If provided, use this as the denominator for return and CAGR
                    instead of nav_series[0]. Used for SI metrics where
                    unit_nav[0] may be > 100 due to pre-inception gains,
                    but the CAGR should be measured from 100 (the corpus base).

    Returns:
        dict with return_pct, cagr_pct, volatility_pct, max_drawdown_pct,
        sharpe_ratio, sortino_ratio, calmar_ratio
    """
    if len(nav_series) < 2:
        return {}

    start_nav = float(nav_series.iloc[0])
    end_nav = float(nav_series.iloc[-1])
    start_date = dates.iloc[0]
    end_date = dates.iloc[-1]

    # Use base_value for return computation if provided (SI metrics)
    return_base = base_value if base_value is not None else start_nav
    if return_base <= 0:
        return_base = start_nav

    # Total return (relative to base)
    total_return_pct = ((end_nav / return_base) - 1) * 100

    # CAGR (relative to base)
    years = (end_date - start_date).days / 365.25
    cagr_pct = ((end_nav / return_base) ** (1 / years) - 1) * 100 if years > 0 else 0.0

    # Daily returns (these use actual unit_nav values, not base)
    daily_returns = nav_series.pct_change().dropna()

    # Annualized volatility
    volatility_pct = float(daily_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR) * 100)

    # Max drawdown
    running_max = nav_series.cummax()
    drawdowns = (nav_series - running_max) / running_max
    max_drawdown_pct = float(drawdowns.min() * 100)

    # Sharpe ratio (7% risk-free for India)
    daily_rf = RISK_FREE_RATE / TRADING_DAYS_PER_YEAR
    excess_returns = daily_returns - daily_rf
    sharpe = float(excess_returns.mean() / excess_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)) \
        if excess_returns.std() > 0 else 0.0

    # Sortino ratio (downside deviation only)
    downside = daily_returns[daily_returns < daily_rf] - daily_rf
    downside_std = float(np.sqrt((downside ** 2).mean())) if len(downside) > 0 else 0.0
    sortino = float((daily_returns.mean() - daily_rf) / downside_std * np.sqrt(TRADING_DAYS_PER_YEAR)) \
        if downside_std > 0 else 0.0

    # Calmar ratio (CAGR / |max drawdown|)
    calmar = float(cagr_pct / abs(max_drawdown_pct)) if max_drawdown_pct != 0 else 0.0

    return {
        'start_date': start_date,
        'end_date': end_date,
        'start_nav': round(start_nav, 4),
        'end_nav': round(end_nav, 4),
        'absolute_return': round(end_nav - start_nav, 4),
        'return_pct': round(total_return_pct, 2),
        'cagr_pct': round(cagr_pct, 2),
        'volatility_pct': round(volatility_pct, 2),
        'max_drawdown_pct': round(max_drawdown_pct, 2),
        'sharpe_ratio': round(sharpe, 2),
        'sortino_ratio': round(sortino, 2),
        'calmar_ratio': round(calmar, 2),
    }


# Period definitions: name -> calendar months lookback
# Broker uses calendar dates (e.g., 1Y = Mar 6 2025 -> Mar 6 2026), NOT trading days
PERIOD_MONTHS = {
    '1M': 1, '3M': 3, '6M': 6,
    '1Y': 12, '2Y': 24, '3Y': 36, '4Y': 48, '5Y': 60,
}


def _find_closest_idx(dates: pd.Series, target_date) -> int:
    """Find index of closest date on or after target_date in sorted date series."""
    from datetime import date as date_type
    if isinstance(target_date, str):
        target_date = date_type.fromisoformat(target_date)
    for i, d in enumerate(dates):
        if d >= target_date:
            return i
    return len(dates) - 1


def recalculate_portfolio_metrics(portfolio_id: int, db: Session) -> int:
    """Recompute TWR unit_nav, then all period metrics using calendar dates.

    Uses calendar-date lookback (not trading-day counts) to match
    broker's SEBI TWRR convention: 1Y = today minus 1 calendar year.

    For SI (Since Inception) metrics, CAGR is computed relative to
    TWR_BASE_VALUE (100) to capture any day-0 NAV/corpus gain.
    """
    from dateutil.relativedelta import relativedelta

    # Step 1: recompute TWR unit_nav from raw NAV + corpus
    compute_twr_unit_nav(portfolio_id, db)

    # Step 2: load unit_nav series for metric computation
    rows = (
        db.query(PmsNavDaily)
        .filter(PmsNavDaily.portfolio_id == portfolio_id)
        .order_by(PmsNavDaily.date)
        .all()
    )
    if len(rows) < 2:
        return 0

    # Use unit_nav for all metrics (TWR-adjusted)
    nav_values = pd.Series([r.unit_nav for r in rows])
    nav_dates = pd.Series([r.date for r in rows])
    today = rows[-1].date

    # Delete existing metrics for today
    db.query(PortfolioMetric).filter(
        PortfolioMetric.portfolio_id == portfolio_id,
        PortfolioMetric.as_of_date == today,
    ).delete()

    count = 0
    for period_name, months in PERIOD_MONTHS.items():
        cutoff_date = today - relativedelta(months=months)
        # Find first data point on or after the cutoff date
        start_idx = _find_closest_idx(nav_dates, cutoff_date)
        if start_idx >= len(nav_values) - 1:
            continue  # not enough data for this period
        subset_nav = nav_values.iloc[start_idx:].reset_index(drop=True)
        subset_dates = nav_dates.iloc[start_idx:].reset_index(drop=True)
        if len(subset_nav) < 2:
            continue
        # Sub-periods use actual unit_nav values (no base override)
        metrics = calculate_risk_metrics(subset_nav, subset_dates)
        if not metrics:
            continue
        db.add(PortfolioMetric(
            portfolio_id=portfolio_id, as_of_date=today,
            period=period_name, **metrics,
        ))
        count += 1

    # Since inception (SI): CAGR relative to base 100 (corpus baseline)
    # This captures any pre-existing gain on day 0 when NAV > corpus
    si_metrics = calculate_risk_metrics(
        nav_values, nav_dates, base_value=TWR_BASE_VALUE,
    )
    if si_metrics:
        db.add(PortfolioMetric(
            portfolio_id=portfolio_id, as_of_date=today,
            period='SI', **si_metrics,
        ))
        count += 1

    db.commit()
    logger.info("Stored %d TWR metrics for portfolio %d as of %s", count, portfolio_id, today)
    return count


def detect_drawdown_events(portfolio_id: int, db: Session) -> int:
    """Identify peak-to-trough drawdown events using unit_nav. Returns count."""
    rows = (
        db.query(PmsNavDaily)
        .filter(PmsNavDaily.portfolio_id == portfolio_id)
        .order_by(PmsNavDaily.date)
        .all()
    )
    if len(rows) < 2:
        return 0

    # Use unit_nav (TWR-adjusted) for drawdown detection
    navs = [r.unit_nav if r.unit_nav else r.nav for r in rows]
    dates = [r.date for r in rows]

    db.query(DrawdownEvent).filter(DrawdownEvent.portfolio_id == portfolio_id).delete()

    events = []
    peak_idx = 0
    trough_idx = 0
    in_drawdown = False

    for i in range(1, len(navs)):
        if navs[i] >= navs[peak_idx]:
            if in_drawdown:
                dd_pct = ((navs[trough_idx] - navs[peak_idx]) / navs[peak_idx]) * 100
                if abs(dd_pct) >= 2.0:
                    events.append(DrawdownEvent(
                        portfolio_id=portfolio_id,
                        peak_date=dates[peak_idx], peak_nav=navs[peak_idx],
                        trough_date=dates[trough_idx], trough_nav=navs[trough_idx],
                        drawdown_pct=round(dd_pct, 2),
                        duration_days=(dates[trough_idx] - dates[peak_idx]).days,
                        recovery_date=dates[i],
                        recovery_days=(dates[i] - dates[trough_idx]).days,
                        status='recovered',
                    ))
                in_drawdown = False
            peak_idx = i
            trough_idx = i
        elif navs[i] < navs[trough_idx]:
            trough_idx = i
            in_drawdown = True

    if in_drawdown:
        dd_pct = ((navs[trough_idx] - navs[peak_idx]) / navs[peak_idx]) * 100
        if abs(dd_pct) >= 2.0:
            events.append(DrawdownEvent(
                portfolio_id=portfolio_id,
                peak_date=dates[peak_idx], peak_nav=navs[peak_idx],
                trough_date=dates[trough_idx], trough_nav=navs[trough_idx],
                drawdown_pct=round(dd_pct, 2),
                duration_days=(dates[trough_idx] - dates[peak_idx]).days,
                status='underwater',
            ))

    db.add_all(events)
    db.commit()
    logger.info("Detected %d drawdown events for portfolio %d", len(events), portfolio_id)
    return len(events)


def compute_monthly_returns(portfolio_id: int, db: Session) -> list[dict]:
    """Compute month-over-month returns using TWR unit_nav."""
    rows = (
        db.query(PmsNavDaily)
        .filter(PmsNavDaily.portfolio_id == portfolio_id)
        .order_by(PmsNavDaily.date)
        .all()
    )
    if len(rows) < 2:
        return []

    # Use unit_nav for accurate TWR monthly returns
    df = pd.DataFrame([{
        'date': r.date,
        'nav': r.unit_nav if r.unit_nav else r.nav,
    } for r in rows])
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')

    monthly = df['nav'].resample('ME').last().dropna()
    monthly_returns = monthly.pct_change().dropna() * 100

    return [
        {'year': idx.year, 'month': idx.month, 'return_pct': round(float(val), 2)}
        for idx, val in monthly_returns.items()
        if np.isfinite(val)
    ]


def compute_enhanced_risk_metrics(
    portfolio_id: int,
    db: Session,
    benchmark_name: str = "NIFTY",
) -> dict:
    """Compute advanced risk management metrics: Ulcer Index, capture ratios,
    beta, information ratio, positive/negative month stats, cash utilisation.

    These metrics demonstrate active risk management quality.
    """
    from models import IndexPrice

    rows = (
        db.query(PmsNavDaily)
        .filter(PmsNavDaily.portfolio_id == portfolio_id)
        .order_by(PmsNavDaily.date)
        .all()
    )
    if len(rows) < 30:
        return {}

    # Build portfolio unit_nav series
    nav_vals = pd.Series([r.unit_nav if r.unit_nav else r.nav for r in rows])
    nav_dates = [r.date for r in rows]
    daily_returns = nav_vals.pct_change().dropna()

    # ── Ulcer Index (measures depth + duration of drawdowns) ──
    running_max = nav_vals.cummax()
    dd_pct = ((nav_vals - running_max) / running_max * 100)
    ulcer_index = round(float(np.sqrt((dd_pct ** 2).mean())), 2)

    # ── Monthly return stats ──
    df = pd.DataFrame({'date': nav_dates, 'nav': nav_vals.values})
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')
    monthly_nav = df['nav'].resample('ME').last().dropna()
    monthly_returns = monthly_nav.pct_change().dropna() * 100

    positive_months = int((monthly_returns > 0).sum())
    negative_months = int((monthly_returns <= 0).sum())
    total_months = positive_months + negative_months
    hit_rate_monthly = round(positive_months / total_months * 100, 1) if total_months > 0 else 0.0
    best_month = round(float(monthly_returns.max()), 2) if len(monthly_returns) > 0 else 0.0
    worst_month = round(float(monthly_returns.min()), 2) if len(monthly_returns) > 0 else 0.0
    avg_positive_month = round(float(monthly_returns[monthly_returns > 0].mean()), 2) if positive_months > 0 else 0.0
    avg_negative_month = round(float(monthly_returns[monthly_returns <= 0].mean()), 2) if negative_months > 0 else 0.0

    # Max consecutive losing months
    max_consecutive_loss = 0
    current_streak = 0
    for ret in monthly_returns:
        if ret <= 0:
            current_streak += 1
            max_consecutive_loss = max(max_consecutive_loss, current_streak)
        else:
            current_streak = 0

    # ── Benchmark comparison metrics ──
    start_str = str(nav_dates[0])
    end_str = str(nav_dates[-1])
    benchmark_rows = (
        db.query(IndexPrice)
        .filter(
            IndexPrice.index_name == benchmark_name,
            IndexPrice.date >= start_str,
            IndexPrice.date <= end_str,
        )
        .order_by(IndexPrice.date)
        .all()
    )

    up_capture = None
    down_capture = None
    beta = None
    information_ratio = None
    correlation = None
    benchmark_ulcer_index = None

    if len(benchmark_rows) > 30:
        # Build benchmark return series aligned to portfolio dates
        bench_map = {str(r.date): r.close_price for r in benchmark_rows}
        bench_df = pd.DataFrame({'date': nav_dates, 'nav': nav_vals.values})
        bench_prices = []
        for d in nav_dates:
            bench_prices.append(bench_map.get(str(d), None))
        bench_df['bench'] = bench_prices
        bench_df = bench_df.dropna(subset=['bench'])

        if len(bench_df) > 30:
            port_rets = bench_df['nav'].pct_change().dropna()
            bench_rets = bench_df['bench'].pct_change().dropna()

            # Align lengths
            min_len = min(len(port_rets), len(bench_rets))
            port_rets = port_rets.iloc[:min_len].reset_index(drop=True)
            bench_rets = bench_rets.iloc[:min_len].reset_index(drop=True)

            # Up/Down capture ratios
            up_mask = bench_rets > 0
            down_mask = bench_rets < 0
            if up_mask.sum() > 5:
                up_capture = round(float(port_rets[up_mask].mean() / bench_rets[up_mask].mean() * 100), 1)
            if down_mask.sum() > 5:
                down_capture = round(float(port_rets[down_mask].mean() / bench_rets[down_mask].mean() * 100), 1)

            # Beta and correlation
            bench_var = bench_rets.var()
            if bench_var > 0:
                cov = port_rets.cov(bench_rets)
                beta = round(float(cov / bench_var), 2)
                corr = port_rets.corr(bench_rets)
                correlation = round(float(corr), 2) if np.isfinite(corr) else None

            # Information ratio (annualized excess return / tracking error)
            excess = port_rets - bench_rets
            tracking_error = float(excess.std() * np.sqrt(TRADING_DAYS_PER_YEAR))
            if tracking_error > 0:
                ann_excess = float(excess.mean() * TRADING_DAYS_PER_YEAR)
                information_ratio = round(ann_excess / tracking_error, 2)

            # Benchmark Ulcer Index
            bench_nav = bench_df['bench']
            bench_running_max = bench_nav.cummax()
            bench_dd_pct = ((bench_nav - bench_running_max) / bench_running_max * 100)
            benchmark_ulcer_index = round(float(np.sqrt((bench_dd_pct ** 2).mean())), 2)

    # ── Cash allocation stats (as % of NAV, not corpus) ──
    cash_pcts = []
    for r in rows:
        if r.nav and r.nav > 0:
            cash = (r.cash_equivalent or 0) + (r.bank_balance or 0)
            cash_pcts.append(cash / r.nav * 100)
    avg_cash_pct = round(float(np.mean(cash_pcts)), 1) if cash_pcts else None
    max_cash_pct = round(float(np.max(cash_pcts)), 1) if cash_pcts else None
    current_cash_pct = round(cash_pcts[-1], 1) if cash_pcts else None

    return {
        'ulcer_index': ulcer_index,
        'positive_months': positive_months,
        'negative_months': negative_months,
        'total_months': total_months,
        'hit_rate_monthly': hit_rate_monthly,
        'best_month_pct': best_month,
        'worst_month_pct': worst_month,
        'avg_positive_month_pct': avg_positive_month,
        'avg_negative_month_pct': avg_negative_month,
        'max_consecutive_loss_months': max_consecutive_loss,
        'up_capture_ratio': up_capture,
        'down_capture_ratio': down_capture,
        'beta': beta,
        'correlation': correlation,
        'information_ratio': information_ratio,
        'benchmark_ulcer_index': benchmark_ulcer_index,
        'avg_cash_pct': avg_cash_pct,
        'max_cash_pct': max_cash_pct,
        'current_cash_pct': current_cash_pct,
    }


def get_pms_summary(portfolio_id: int, db: Session) -> Optional[dict]:
    """Get quick summary: latest NAV, corpus, unit_nav, and key SI metrics."""
    latest = (
        db.query(PmsNavDaily)
        .filter(PmsNavDaily.portfolio_id == portfolio_id)
        .order_by(PmsNavDaily.date.desc())
        .first()
    )
    if not latest:
        return None

    first = (
        db.query(PmsNavDaily)
        .filter(PmsNavDaily.portfolio_id == portfolio_id)
        .order_by(PmsNavDaily.date)
        .first()
    )

    nav_count = (
        db.query(PmsNavDaily)
        .filter(PmsNavDaily.portfolio_id == portfolio_id)
        .count()
    )

    si_metric = (
        db.query(PortfolioMetric)
        .filter(PortfolioMetric.portfolio_id == portfolio_id, PortfolioMetric.period == 'SI')
        .order_by(PortfolioMetric.as_of_date.desc())
        .first()
    )

    return {
        'latest_date': str(latest.date),
        'latest_nav': latest.nav,
        'latest_unit_nav': latest.unit_nav,
        'latest_corpus': latest.corpus,
        'latest_equity_holding': latest.equity_holding,
        'latest_etf_investment': latest.etf_investment,
        'latest_bank_balance': latest.bank_balance,
        'latest_liquidity_pct': latest.liquidity_pct,
        'latest_high_water_mark': latest.high_water_mark,
        'first_date': str(first.date) if first else None,
        'first_nav': first.nav if first else None,
        'first_unit_nav': first.unit_nav if first else None,
        'total_days': nav_count,
        'cagr_pct': si_metric.cagr_pct if si_metric else None,
        'max_drawdown_pct': si_metric.max_drawdown_pct if si_metric else None,
        'sharpe_ratio': si_metric.sharpe_ratio if si_metric else None,
        'sortino_ratio': si_metric.sortino_ratio if si_metric else None,
        'calmar_ratio': si_metric.calmar_ratio if si_metric else None,
        'return_pct': si_metric.return_pct if si_metric else None,
        'volatility_pct': si_metric.volatility_pct if si_metric else None,
    }
