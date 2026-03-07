"""
FIE v3 — PMS Service
Risk/return metric calculations, drawdown detection,
monthly returns, and portfolio summary queries.
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


# ═══════════════════════════════════════════════════════════
#  RISK / RETURN METRICS
# ═══════════════════════════════════════════════════════════

def calculate_risk_metrics(nav_series: pd.Series, dates: pd.Series) -> dict:
    """Compute risk/return metrics from a NAV time series.

    Args:
        nav_series: pd.Series of NAV values (sorted by date)
        dates: pd.Series of corresponding dates

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

    # Total return
    total_return_pct = ((end_nav / start_nav) - 1) * 100

    # CAGR
    years = (end_date - start_date).days / 365.25
    cagr_pct = ((end_nav / start_nav) ** (1 / years) - 1) * 100 if years > 0 else 0.0

    # Daily returns
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


# Period definitions: name → trading days lookback
PERIOD_DAYS = {
    '1M': 21,
    '3M': 63,
    '6M': 126,
    '1Y': 252,
    '3Y': 756,
    '5Y': 1260,
}


def recalculate_portfolio_metrics(portfolio_id: int, db: Session) -> int:
    """Recompute all period metrics for a portfolio. Returns count of metrics stored."""
    rows = (
        db.query(PmsNavDaily)
        .filter(PmsNavDaily.portfolio_id == portfolio_id)
        .order_by(PmsNavDaily.date)
        .all()
    )
    if len(rows) < 2:
        return 0

    nav_values = pd.Series([r.nav for r in rows])
    nav_dates = pd.Series([r.date for r in rows])
    today = rows[-1].date

    # Delete existing metrics for today
    db.query(PortfolioMetric).filter(
        PortfolioMetric.portfolio_id == portfolio_id,
        PortfolioMetric.as_of_date == today,
    ).delete()

    count = 0
    # Period-based metrics
    for period_name, trading_days in PERIOD_DAYS.items():
        if len(nav_values) < trading_days:
            continue
        subset_nav = nav_values.iloc[-trading_days:]
        subset_dates = nav_dates.iloc[-trading_days:]
        metrics = calculate_risk_metrics(subset_nav.reset_index(drop=True),
                                         subset_dates.reset_index(drop=True))
        if not metrics:
            continue
        db.add(PortfolioMetric(
            portfolio_id=portfolio_id,
            as_of_date=today,
            period=period_name,
            **metrics,
        ))
        count += 1

    # Since inception (SI)
    si_metrics = calculate_risk_metrics(nav_values, nav_dates)
    if si_metrics:
        db.add(PortfolioMetric(
            portfolio_id=portfolio_id,
            as_of_date=today,
            period='SI',
            **si_metrics,
        ))
        count += 1

    db.commit()
    logger.info("Stored %d metrics for portfolio %d as of %s", count, portfolio_id, today)
    return count


def detect_drawdown_events(portfolio_id: int, db: Session) -> int:
    """Identify peak-to-trough drawdown events. Returns count of events."""
    rows = (
        db.query(PmsNavDaily)
        .filter(PmsNavDaily.portfolio_id == portfolio_id)
        .order_by(PmsNavDaily.date)
        .all()
    )
    if len(rows) < 2:
        return 0

    navs = [r.nav for r in rows]
    dates = [r.date for r in rows]

    # Delete existing events
    db.query(DrawdownEvent).filter(DrawdownEvent.portfolio_id == portfolio_id).delete()

    events = []
    peak_idx = 0
    trough_idx = 0
    in_drawdown = False

    for i in range(1, len(navs)):
        if navs[i] >= navs[peak_idx]:
            # New high — if we were in a drawdown, it has recovered
            if in_drawdown:
                dd_pct = ((navs[trough_idx] - navs[peak_idx]) / navs[peak_idx]) * 100
                # Only record meaningful drawdowns (> 2%)
                if abs(dd_pct) >= 2.0:
                    events.append(DrawdownEvent(
                        portfolio_id=portfolio_id,
                        peak_date=dates[peak_idx],
                        peak_nav=navs[peak_idx],
                        trough_date=dates[trough_idx],
                        trough_nav=navs[trough_idx],
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

    # If still in a drawdown at end of series
    if in_drawdown:
        dd_pct = ((navs[trough_idx] - navs[peak_idx]) / navs[peak_idx]) * 100
        if abs(dd_pct) >= 2.0:
            events.append(DrawdownEvent(
                portfolio_id=portfolio_id,
                peak_date=dates[peak_idx],
                peak_nav=navs[peak_idx],
                trough_date=dates[trough_idx],
                trough_nav=navs[trough_idx],
                drawdown_pct=round(dd_pct, 2),
                duration_days=(dates[trough_idx] - dates[peak_idx]).days,
                status='underwater',
            ))

    db.add_all(events)
    db.commit()
    logger.info("Detected %d drawdown events for portfolio %d", len(events), portfolio_id)
    return len(events)


def compute_monthly_returns(portfolio_id: int, db: Session) -> list[dict]:
    """Compute month-over-month NAV returns for calendar heatmap."""
    rows = (
        db.query(PmsNavDaily)
        .filter(PmsNavDaily.portfolio_id == portfolio_id)
        .order_by(PmsNavDaily.date)
        .all()
    )
    if len(rows) < 2:
        return []

    df = pd.DataFrame([{'date': r.date, 'nav': r.nav} for r in rows])
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')

    # Get last NAV of each month
    monthly = df['nav'].resample('ME').last().dropna()
    monthly_returns = monthly.pct_change().dropna() * 100

    return [
        {
            'year': idx.year,
            'month': idx.month,
            'return_pct': round(float(val), 2),
        }
        for idx, val in monthly_returns.items()
    ]


def get_pms_summary(portfolio_id: int, db: Session) -> Optional[dict]:
    """Get quick summary: latest NAV, corpus, and key SI metrics."""
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

    # Get SI metrics
    si_metric = (
        db.query(PortfolioMetric)
        .filter(
            PortfolioMetric.portfolio_id == portfolio_id,
            PortfolioMetric.period == 'SI',
        )
        .order_by(PortfolioMetric.as_of_date.desc())
        .first()
    )

    return {
        'latest_date': str(latest.date),
        'latest_nav': latest.nav,
        'latest_corpus': latest.corpus,
        'latest_equity_holding': latest.equity_holding,
        'latest_etf_investment': latest.etf_investment,
        'latest_bank_balance': latest.bank_balance,
        'latest_liquidity_pct': latest.liquidity_pct,
        'latest_high_water_mark': latest.high_water_mark,
        'first_date': str(first.date) if first else None,
        'first_nav': first.nav if first else None,
        'total_days': nav_count,
        'cagr_pct': si_metric.cagr_pct if si_metric else None,
        'max_drawdown_pct': si_metric.max_drawdown_pct if si_metric else None,
        'sharpe_ratio': si_metric.sharpe_ratio if si_metric else None,
        'sortino_ratio': si_metric.sortino_ratio if si_metric else None,
        'calmar_ratio': si_metric.calmar_ratio if si_metric else None,
        'return_pct': si_metric.return_pct if si_metric else None,
        'volatility_pct': si_metric.volatility_pct if si_metric else None,
    }
