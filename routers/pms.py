"""
FIE v3 — PMS Router
Upload PMS Excel files, query NAV history, metrics, drawdowns, transactions,
win/loss analysis.
"""

import logging
from collections import defaultdict
from datetime import date, timedelta

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import desc
from sqlalchemy.orm import Session

from models import (
    DrawdownEvent,
    IndexPrice,
    ModelPortfolio,
    PmsNavDaily,
    PmsTransaction,
    PortfolioMetric,
    get_db,
)
from services.pms_service import (
    calculate_risk_metrics,
    compute_enhanced_risk_metrics,
    compute_monthly_returns,
    detect_drawdown_events,
    get_pms_summary,
    parse_nav_excel,
    parse_transaction_excel,
    recalculate_portfolio_metrics,
)

logger = logging.getLogger("fie_v3.pms")
router = APIRouter(prefix="/api/pms", tags=["PMS"])

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


# ═══════════════════════════════════════════════════════════
#  UPLOAD
# ═══════════════════════════════════════════════════════════

@router.post(
    "/upload",
    summary="Upload PMS Excel files",
    description="Upload PMS NAV report and (optionally) transaction log Excel files (.xlsx). Parses the UCC-specific data, upserts NAV records, replaces transaction history, and recalculates metrics and drawdowns.",
)
async def upload_pms_files(
    portfolio_id: int = Form(...),
    nav_file: UploadFile = File(...),
    transaction_file: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    """Upload PMS NAV report and (optionally) transaction log Excel files."""
    # Validate portfolio exists and is PMS type
    portfolio = db.query(ModelPortfolio).filter(ModelPortfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    if not portfolio.ucc_code:
        raise HTTPException(status_code=400, detail="Portfolio has no UCC code configured")

    # Validate file types
    if nav_file and not nav_file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="NAV file must be .xlsx")
    if transaction_file and not transaction_file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Transaction file must be .xlsx")

    ucc = portfolio.ucc_code.strip()
    result = {"status": "ok", "new_nav_records": 0, "new_transactions": 0, "date_range": {}}

    # Parse and store NAV data
    try:
        nav_bytes = await nav_file.read()
        if len(nav_bytes) > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail="NAV file too large (max 10MB)")
        nav_df = parse_nav_excel(nav_bytes, ucc)
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("NAV parse error for portfolio %d: %s", portfolio_id, e)
        raise HTTPException(status_code=400, detail="Invalid NAV file format. Ensure it is a valid .xlsx file.")

    # Upsert NAV records (skip existing dates)
    existing_dates = set(
        r[0] for r in db.query(PmsNavDaily.date)
        .filter(PmsNavDaily.portfolio_id == portfolio_id).all()
    )

    nav_count = 0
    for _, row in nav_df.iterrows():
        if row['date'] in existing_dates:
            continue
        db.add(PmsNavDaily(
            portfolio_id=portfolio_id,
            date=row['date'],
            corpus=row.get('corpus') if not _is_nan(row.get('corpus')) else None,
            equity_holding=row.get('equity_holding') if not _is_nan(row.get('equity_holding')) else None,
            etf_investment=row.get('etf_investment') if not _is_nan(row.get('etf_investment')) else None,
            cash_equivalent=row.get('cash_equivalent') if not _is_nan(row.get('cash_equivalent')) else None,
            bank_balance=row.get('bank_balance') if not _is_nan(row.get('bank_balance')) else None,
            nav=row['nav'],
            liquidity_pct=row.get('liquidity_pct') if not _is_nan(row.get('liquidity_pct')) else None,
            high_water_mark=row.get('high_water_mark') if not _is_nan(row.get('high_water_mark')) else None,
        ))
        nav_count += 1
    db.commit()
    result["new_nav_records"] = nav_count

    if len(nav_df) > 0:
        result["date_range"] = {
            "start": str(nav_df['date'].iloc[0]),
            "end": str(nav_df['date'].iloc[-1]),
        }

    # Parse and store transactions
    if transaction_file:
        try:
            txn_bytes = await transaction_file.read()
            if len(txn_bytes) > MAX_UPLOAD_SIZE:
                result["transaction_error"] = "Transaction file too large (max 10MB)"
                txn_bytes = None
            txn_df = parse_transaction_excel(txn_bytes, ucc) if txn_bytes else None
        except Exception as e:
            logger.warning("Transaction file parse error for portfolio %d: %s", portfolio_id, e)
            result["transaction_error"] = "Invalid transaction file format"
            txn_df = None

        if txn_df is not None and not txn_df.empty:
            # Delete existing transactions for this portfolio and re-insert
            db.query(PmsTransaction).filter(
                PmsTransaction.portfolio_id == portfolio_id
            ).delete()

            txn_count = 0
            for _, row in txn_df.iterrows():
                db.add(PmsTransaction(
                    portfolio_id=portfolio_id,
                    date=row['date'],
                    script=row['script'],
                    exchange=row.get('exchange', ''),
                    stno=row.get('stno', ''),
                    buy_qty=_nan_to_none(row.get('buy_qty')),
                    buy_rate=_nan_to_none(row.get('buy_rate')),
                    buy_gst=_nan_to_none(row.get('buy_gst')),
                    buy_other_charges=_nan_to_none(row.get('buy_other_charges')),
                    buy_stt=_nan_to_none(row.get('buy_stt')),
                    buy_cost_rate=_nan_to_none(row.get('buy_cost_rate')),
                    buy_amt_with_cost=_nan_to_none(row.get('buy_amt_with_cost')),
                    buy_amt_without_stt=_nan_to_none(row.get('buy_amt_without_stt')),
                    sale_qty=_nan_to_none(row.get('sale_qty')),
                    sale_rate=_nan_to_none(row.get('sale_rate')),
                    sale_gst=_nan_to_none(row.get('sale_gst')),
                    sale_stt=_nan_to_none(row.get('sale_stt')),
                    sale_other_charges=_nan_to_none(row.get('sale_other_charges')),
                    sale_cost_rate=_nan_to_none(row.get('sale_cost_rate')),
                    sale_amt_with_cost=_nan_to_none(row.get('sale_amt_with_cost')),
                    sale_amt_without_stt=_nan_to_none(row.get('sale_amt_without_stt')),
                ))
                txn_count += 1
            db.commit()
            result["new_transactions"] = txn_count

    # Recalculate metrics and drawdowns
    try:
        recalculate_portfolio_metrics(portfolio_id, db)
        detect_drawdown_events(portfolio_id, db)
    except Exception as e:
        logger.warning("Metrics recalculation failed: %s", e)

    # Update portfolio type if not already PMS
    if portfolio.portfolio_type != 'pms':
        portfolio.portfolio_type = 'pms'
        db.commit()

    return result


# ═══════════════════════════════════════════════════════════
#  NAV HISTORY (with NIFTY 50 benchmark)
# ═══════════════════════════════════════════════════════════

@router.get(
    "/{portfolio_id}/nav",
    summary="PMS NAV history",
    description="Returns daily NAV time series with normalized NIFTY 50 benchmark overlay (base 100). Supports period filtering: 1M, 3M, 6M, 1Y, 3Y, 5Y, or all.",
)
def get_nav_history(
    portfolio_id: int,
    period: str = "all",
    db: Session = Depends(get_db),
):
    """Return NAV time series with normalized NIFTY 50 benchmark, optionally filtered by period."""
    query = db.query(PmsNavDaily).filter(PmsNavDaily.portfolio_id == portfolio_id)

    if period != "all":
        days_map = {'1M': 30, '3M': 90, '6M': 180, '1Y': 365, '3Y': 1095, '5Y': 1825}
        days = days_map.get(period.upper())
        if days:
            cutoff = date.today() - timedelta(days=days)
            query = query.filter(PmsNavDaily.date >= cutoff)

    rows = query.order_by(PmsNavDaily.date).all()

    # Build NIFTY 50 benchmark lookup over the same date range
    nifty_map = {}
    if rows:
        start_date = rows[0].date
        end_date = rows[-1].date
        nifty_rows = (
            db.query(IndexPrice)
            .filter(
                IndexPrice.index_name == "NIFTY",
                IndexPrice.date >= str(start_date),
                IndexPrice.date <= str(end_date),
            )
            .order_by(IndexPrice.date)
            .all()
        )
        for nr in nifty_rows:
            nifty_map[nr.date] = nr.close_price

    # Find NIFTY 50 close price on the portfolio's first data point date
    # Use the earliest available NIFTY data at or after the start date as fallback
    nifty_start_close = None
    if rows and nifty_map:
        first_date_str = str(rows[0].date)
        # Try exact date match first, then find closest available
        if first_date_str in nifty_map:
            nifty_start_close = nifty_map[first_date_str]
        else:
            # Find the first available NIFTY date from our fetched data
            for nr_date in sorted(nifty_map.keys()):
                if nr_date >= first_date_str:
                    nifty_start_close = nifty_map[nr_date]
                    break

    nav_history = []
    for r in rows:
        # Normalize NIFTY 50 to base 100 from portfolio start date
        date_str = str(r.date)
        benchmark_nav = None
        if nifty_start_close and nifty_start_close > 0:
            nifty_close = nifty_map.get(date_str)
            if nifty_close is not None:
                benchmark_nav = round((nifty_close / nifty_start_close) * 100, 2)

        nav_history.append({
            "date": date_str,
            "nav": r.nav,
            "unit_nav": r.unit_nav,
            "corpus": r.corpus,
            "equity_holding": r.equity_holding,
            "etf_investment": r.etf_investment,
            "cash_equivalent": r.cash_equivalent,
            "bank_balance": r.bank_balance,
            "liquidity_pct": r.liquidity_pct,
            "high_water_mark": r.high_water_mark,
            "benchmark_nav": benchmark_nav,
        })

    return {
        "portfolio_id": portfolio_id,
        "count": len(rows),
        "nav_history": nav_history,
    }


# ═══════════════════════════════════════════════════════════
#  METRICS (portfolio + NIFTY benchmark side-by-side)
# ═══════════════════════════════════════════════════════════

def _load_nifty_series(db: Session) -> tuple[pd.Series, pd.Series]:
    """Load all NIFTY close prices from IndexPrice, return (nav_series, date_series).

    IndexPrice dates are stored as strings ("YYYY-MM-DD"). We convert them
    to datetime.date objects so they can be compared with PortfolioMetric dates.
    """
    nifty_rows = (
        db.query(IndexPrice)
        .filter(IndexPrice.index_name == "NIFTY")
        .order_by(IndexPrice.date)
        .all()
    )
    if not nifty_rows:
        return pd.Series(dtype=float), pd.Series(dtype=object)

    prices = []
    dates = []
    for row in nifty_rows:
        if row.close_price is None:
            continue
        # Convert string date to datetime.date for consistent comparison
        parsed_date = date.fromisoformat(row.date) if isinstance(row.date, str) else row.date
        dates.append(parsed_date)
        prices.append(row.close_price)

    return pd.Series(prices, dtype=float), pd.Series(dates)


def _benchmark_metrics_for_period(
    nifty_nav: pd.Series,
    nifty_dates: pd.Series,
    start_date: date,
    end_date: date,
) -> dict:
    """Slice NIFTY series to a date range and compute risk metrics.

    Returns a dict with benchmark_* keys, or empty dict if insufficient data.
    """
    if nifty_nav.empty or start_date is None or end_date is None:
        return {}

    # Find indices within the date range (inclusive)
    mask = (nifty_dates >= start_date) & (nifty_dates <= end_date)
    subset_nav = nifty_nav[mask].reset_index(drop=True)
    subset_dates = nifty_dates[mask].reset_index(drop=True)

    if len(subset_nav) < 2:
        return {}

    metrics = calculate_risk_metrics(subset_nav, subset_dates)
    if not metrics:
        return {}

    # Return with benchmark_ prefix (only the fields the frontend needs)
    return {
        "benchmark_return_pct": metrics.get("return_pct"),
        "benchmark_cagr_pct": metrics.get("cagr_pct"),
        "benchmark_volatility_pct": metrics.get("volatility_pct"),
        "benchmark_max_drawdown_pct": metrics.get("max_drawdown_pct"),
        "benchmark_sharpe_ratio": metrics.get("sharpe_ratio"),
        "benchmark_sortino_ratio": metrics.get("sortino_ratio"),
    }


@router.get(
    "/{portfolio_id}/metrics",
    summary="PMS risk/return metrics",
    description="Returns risk and return metrics for all computed periods (1M, 3M, 6M, 1Y, 2Y, 3Y, 4Y, 5Y, SI) with NIFTY 50 benchmark comparison. Includes CAGR, volatility, max drawdown, Sharpe ratio, Sortino ratio, and Calmar ratio.",
)
def get_metrics(portfolio_id: int, db: Session = Depends(get_db)):
    """Return risk/return metrics for all computed periods, with NIFTY benchmark."""
    rows = (
        db.query(PortfolioMetric)
        .filter(PortfolioMetric.portfolio_id == portfolio_id)
        .order_by(desc(PortfolioMetric.as_of_date))
        .all()
    )

    # Group by as_of_date, return latest set
    if not rows:
        return {"portfolio_id": portfolio_id, "metrics": []}

    latest_date = rows[0].as_of_date
    latest_metrics = [r for r in rows if r.as_of_date == latest_date]

    # Sort by period order (includes 2Y and 4Y)
    period_order = {
        '1M': 0, '3M': 1, '6M': 2, '1Y': 3,
        '2Y': 4, '3Y': 5, '4Y': 6, '5Y': 7, 'SI': 8,
    }
    latest_metrics.sort(key=lambda m: period_order.get(m.period, 99))

    # Load NIFTY price series once for all periods
    nifty_nav, nifty_dates = _load_nifty_series(db)

    metrics_list = []
    for m in latest_metrics:
        entry = {
            "period": m.period,
            "start_date": str(m.start_date) if m.start_date else None,
            "end_date": str(m.end_date) if m.end_date else None,
            "start_nav": m.start_nav,
            "end_nav": m.end_nav,
            "return_pct": m.return_pct,
            "cagr_pct": m.cagr_pct,
            "volatility_pct": m.volatility_pct,
            "max_drawdown_pct": m.max_drawdown_pct,
            "sharpe_ratio": m.sharpe_ratio,
            "sortino_ratio": m.sortino_ratio,
            "calmar_ratio": m.calmar_ratio,
            # Benchmark defaults (overwritten below if data available)
            "benchmark_return_pct": None,
            "benchmark_cagr_pct": None,
            "benchmark_volatility_pct": None,
            "benchmark_max_drawdown_pct": None,
            "benchmark_sharpe_ratio": None,
            "benchmark_sortino_ratio": None,
        }

        # Compute benchmark metrics over the same date range as the portfolio period
        if m.start_date and m.end_date and not nifty_nav.empty:
            bench = _benchmark_metrics_for_period(
                nifty_nav, nifty_dates, m.start_date, m.end_date,
            )
            entry.update(bench)

        metrics_list.append(entry)

    return {
        "portfolio_id": portfolio_id,
        "as_of_date": str(latest_date),
        "metrics": metrics_list,
    }


# ═══════════════════════════════════════════════════════════
#  DRAWDOWNS
# ═══════════════════════════════════════════════════════════

@router.get(
    "/{portfolio_id}/drawdowns",
    summary="PMS drawdown events",
    description="Returns all drawdown events sorted by severity. Includes peak/trough dates and NAV values, drawdown percentage, duration, recovery date, and current status (recovered/active).",
)
def get_drawdowns(portfolio_id: int, db: Session = Depends(get_db)):
    """Return drawdown events sorted by severity."""
    rows = (
        db.query(DrawdownEvent)
        .filter(DrawdownEvent.portfolio_id == portfolio_id)
        .order_by(DrawdownEvent.drawdown_pct)
        .all()
    )
    return {
        "portfolio_id": portfolio_id,
        "count": len(rows),
        "drawdowns": [
            {
                "peak_date": str(r.peak_date),
                "peak_nav": r.peak_nav,
                "trough_date": str(r.trough_date) if r.trough_date else None,
                "trough_nav": r.trough_nav,
                "drawdown_pct": r.drawdown_pct,
                "duration_days": r.duration_days,
                "recovery_date": str(r.recovery_date) if r.recovery_date else None,
                "recovery_days": r.recovery_days,
                "status": r.status,
            }
            for r in rows
        ],
    }


# ═══════════════════════════════════════════════════════════
#  TRANSACTIONS
# ═══════════════════════════════════════════════════════════

@router.get(
    "/{portfolio_id}/transactions",
    summary="PMS transactions",
    description="Returns PMS buy/sell transactions, optionally filtered by script name. Supports pagination via offset and limit.",
)
def get_transactions(
    portfolio_id: int,
    script: str = None,
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Return PMS transactions, optionally filtered by script."""
    query = db.query(PmsTransaction).filter(PmsTransaction.portfolio_id == portfolio_id)
    if script:
        query = query.filter(PmsTransaction.script == script.strip())

    total = query.count()
    rows = query.order_by(desc(PmsTransaction.date)).offset(offset).limit(limit).all()

    return {
        "portfolio_id": portfolio_id,
        "total": total,
        "transactions": [
            {
                "id": r.id,
                "date": str(r.date),
                "script": r.script,
                "exchange": r.exchange,
                "stno": r.stno,
                "buy_qty": r.buy_qty,
                "buy_rate": r.buy_rate,
                "buy_cost_rate": r.buy_cost_rate,
                "buy_amt_with_cost": r.buy_amt_with_cost,
                "sale_qty": r.sale_qty,
                "sale_rate": r.sale_rate,
                "sale_cost_rate": r.sale_cost_rate,
                "sale_amt_with_cost": r.sale_amt_with_cost,
            }
            for r in rows
        ],
    }


# ═══════════════════════════════════════════════════════════
#  WIN/LOSS ANALYSIS
# ═══════════════════════════════════════════════════════════

@router.get(
    "/{portfolio_id}/win-loss",
    summary="PMS win/loss analysis",
    description="Analyzes PMS transaction history to compute win/loss trading statistics. Groups trades by script, calculates P&L for scripts with sells, and returns win rate, profit factor, average win/loss, and best/worst trades.",
)
def get_win_loss(portfolio_id: int, db: Session = Depends(get_db)):
    """Analyze PMS transactions to compute win/loss trading statistics by script.

    Groups all buy and sell transactions by script. For scripts with any sells,
    computes P&L. A trade is a 'win' if total sell amount exceeds total buy amount.
    """
    txns = (
        db.query(PmsTransaction)
        .filter(PmsTransaction.portfolio_id == portfolio_id)
        .order_by(PmsTransaction.date)
        .all()
    )
    if not txns:
        raise HTTPException(status_code=404, detail="No transactions found for this portfolio")

    # Aggregate buy and sell amounts per script
    script_data = defaultdict(lambda: {"buy_amount": 0.0, "sell_amount": 0.0})

    for txn in txns:
        script = txn.script
        # Accumulate buy amounts — prefer buy_amt_with_cost (includes brokerage/costs)
        if txn.buy_qty and txn.buy_qty > 0:
            if txn.buy_amt_with_cost and txn.buy_amt_with_cost > 0:
                script_data[script]["buy_amount"] += txn.buy_amt_with_cost
            elif txn.buy_rate and txn.buy_rate > 0:
                script_data[script]["buy_amount"] += txn.buy_qty * txn.buy_rate

        # Accumulate sell amounts — prefer sale_amt_with_cost (net of costs)
        if txn.sale_qty and txn.sale_qty > 0:
            if txn.sale_amt_with_cost and txn.sale_amt_with_cost > 0:
                script_data[script]["sell_amount"] += txn.sale_amt_with_cost
            elif txn.sale_rate and txn.sale_rate > 0:
                script_data[script]["sell_amount"] += txn.sale_qty * txn.sale_rate

    # Only analyze scripts that have both buys and sells (completed or partial exits)
    trades = []
    for script, data in script_data.items():
        buy_amt = data["buy_amount"]
        sell_amt = data["sell_amount"]
        # Skip scripts with no sells (still open, no realized P&L)
        if sell_amt <= 0:
            continue
        pnl = sell_amt - buy_amt
        pnl_pct = ((sell_amt / buy_amt) - 1) * 100 if buy_amt > 0 else 0.0
        trades.append({
            "script": script,
            "buy_amount": round(buy_amt, 2),
            "sell_amount": round(sell_amt, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
        })

    # Sort by P&L descending (best trades first)
    trades.sort(key=lambda t: t["pnl"], reverse=True)

    winning = [t for t in trades if t["pnl"] > 0]
    losing = [t for t in trades if t["pnl"] <= 0]

    total_profit = sum(t["pnl"] for t in winning)
    total_loss = sum(t["pnl"] for t in losing)  # negative or zero values
    total_scripts_traded = len(trades)
    win_count = len(winning)
    loss_count = len(losing)
    win_rate = (win_count / total_scripts_traded * 100) if total_scripts_traded > 0 else 0.0

    # Profit factor = total_profit / |total_loss|. If no losses, return None.
    profit_factor = None
    if total_loss < 0:
        profit_factor = round(total_profit / abs(total_loss), 2)

    avg_win = round(total_profit / win_count, 2) if win_count > 0 else 0.0
    avg_loss = round(total_loss / loss_count, 2) if loss_count > 0 else 0.0

    best_trade = trades[0] if trades else None
    worst_trade = trades[-1] if trades else None

    return {
        "portfolio_id": portfolio_id,
        "total_scripts_traded": total_scripts_traded,
        "winning_trades": win_count,
        "losing_trades": loss_count,
        "win_rate_pct": round(win_rate, 2),
        "total_profit": round(total_profit, 2),
        "total_loss": round(total_loss, 2),
        "profit_factor": profit_factor,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "best_trade": {"script": best_trade["script"], "pnl": best_trade["pnl"]} if best_trade else None,
        "worst_trade": {"script": worst_trade["script"], "pnl": worst_trade["pnl"]} if worst_trade else None,
        "trades": trades,
    }


# ═══════════════════════════════════════════════════════════
#  MONTHLY RETURNS
# ═══════════════════════════════════════════════════════════

@router.get(
    "/{portfolio_id}/monthly-returns",
    summary="PMS monthly returns",
    description="Returns month-by-month NAV returns for calendar heatmap visualization. Each entry includes year, month, and return percentage.",
)
def get_monthly_returns(portfolio_id: int, db: Session = Depends(get_db)):
    """Return monthly NAV returns for calendar heatmap."""
    returns = compute_monthly_returns(portfolio_id, db)
    return {"portfolio_id": portfolio_id, "monthly_returns": returns}


# ═══════════════════════════════════════════════════════════
#  CURRENT HOLDINGS & ALLOCATION
# ═══════════════════════════════════════════════════════════

# Sector mapping for common PMS holdings (yfinance sector lookup is slow)
SCRIPT_SECTOR_MAP: dict[str, str] = {
    "GOLDBEES": "Gold ETF",
    "SILVERBEES": "Silver ETF",
    "LIQUIDCASE": "Cash & Liquid",
    "LIQUIDBEES": "Cash & Liquid",
    "NIFTYBEES": "Index ETF",
    "BANKBEES": "Index ETF",
    "ITBEES": "Index ETF",
    "JUNIORBEES": "Index ETF",
    "SETFNIF50": "Index ETF",
    "CPSE": "Index ETF",
    "MOM50": "Index ETF",
    "NETFNIF100": "Index ETF",
    "PHARMABEES": "Index ETF",
    "PSUBNKBEES": "Index ETF",
    "FMCGIETF": "Index ETF",
    "METALIETF": "Index ETF",
    "NETFAUTO": "Index ETF",
}


@router.get(
    "/{portfolio_id}/holdings",
    summary="PMS current holdings with allocation",
    description="Computes current holdings from net buy-sell transactions, fetches live prices, and returns stock-wise and sector-wise allocation with P&L. Includes cash and liquid positions from the latest NAV.",
)
def get_pms_holdings(portfolio_id: int, db: Session = Depends(get_db)):
    """Compute current holdings from net buy-sell transactions, fetch live prices,
    and return stock-wise and sector-wise allocation."""
    from price_service import get_batch_prices

    txns = (
        db.query(PmsTransaction)
        .filter(PmsTransaction.portfolio_id == portfolio_id)
        .all()
    )
    if not txns:
        return {"holdings": [], "by_stock": [], "by_sector": []}

    # Net quantity per script
    net_qty: dict[str, float] = defaultdict(float)
    avg_cost: dict[str, list] = defaultdict(list)
    for t in txns:
        if t.buy_qty and t.buy_qty > 0:
            net_qty[t.script] += t.buy_qty
            rate = t.buy_cost_rate or t.buy_rate or 0
            avg_cost[t.script].append((t.buy_qty, rate))
        if t.sale_qty and t.sale_qty > 0:
            net_qty[t.script] -= t.sale_qty

    # Filter to active holdings (qty > 0)
    active = {k: round(v, 2) for k, v in net_qty.items() if v > 0.5}
    if not active:
        return {"holdings": [], "by_stock": [], "by_sector": []}

    # Compute weighted average cost per script
    def weighted_avg(trades: list) -> float:
        total_qty = sum(q for q, _ in trades)
        if total_qty == 0:
            return 0
        return sum(q * r for q, r in trades) / total_qty

    # Fetch live prices
    prices = get_batch_prices(list(active.keys()))

    # Look up sectors via yfinance (with cache)
    sectors: dict[str, str] = {}
    unknown_scripts = []
    for script in active:
        if script in SCRIPT_SECTOR_MAP:
            sectors[script] = SCRIPT_SECTOR_MAP[script]
        else:
            unknown_scripts.append(script)

    if unknown_scripts:
        try:
            import yfinance as yf
            for script in unknown_scripts:
                try:
                    info = yf.Ticker(f"{script}.NS").info
                    sectors[script] = info.get("sector", "Other") or "Other"
                except Exception:
                    sectors[script] = "Other"
        except Exception:
            for s in unknown_scripts:
                sectors[s] = "Other"

    # Build holdings list
    holdings = []
    total_value = 0.0
    for script, qty in sorted(active.items()):
        price_data = prices.get(script, {})
        current_price = price_data.get("current_price")
        if not current_price:
            continue
        value = qty * current_price
        total_value += value
        cost = weighted_avg(avg_cost.get(script, []))
        holdings.append({
            "script": script,
            "qty": qty,
            "avg_cost": round(cost, 2),
            "current_price": round(current_price, 2),
            "value": round(value, 2),
            "pnl": round(value - qty * cost, 2),
            "pnl_pct": round(((current_price - cost) / cost * 100), 2) if cost > 0 else 0,
            "sector": sectors.get(script, "Other"),
        })

    # Compute allocation percentages
    for h in holdings:
        h["weight_pct"] = round(h["value"] / total_value * 100, 2) if total_value > 0 else 0

    # Also include cash/liquid position from latest NAV
    latest_nav = (
        db.query(PmsNavDaily)
        .filter(PmsNavDaily.portfolio_id == portfolio_id)
        .order_by(desc(PmsNavDaily.date))
        .first()
    )
    cash_value = 0.0
    if latest_nav:
        cash_value = (latest_nav.cash_equivalent or 0) + (latest_nav.bank_balance or 0)

    total_with_cash = total_value + cash_value

    # by_stock: top holdings by value
    # Merge LIQUIDCASE/LIQUIDBEES into the Cash & Liquid bucket
    LIQUID_SCRIPTS = {"LIQUIDCASE", "LIQUIDBEES"}
    liquid_value = sum(h["value"] for h in holdings if h["script"] in LIQUID_SCRIPTS)
    combined_cash = cash_value + liquid_value

    by_stock = []
    for h in sorted(holdings, key=lambda x: x["value"], reverse=True):
        if h["script"] in LIQUID_SCRIPTS:
            continue  # merged into Cash & Liquid below
        by_stock.append({
            "label": h["script"],
            "value": h["value"],
            "pct": round(h["value"] / total_with_cash * 100, 1) if total_with_cash > 0 else 0,
        })
    if combined_cash > 0:
        by_stock.append({
            "label": "Cash & Liquid",
            "value": round(combined_cash, 2),
            "pct": round(combined_cash / total_with_cash * 100, 1),
        })

    # by_sector: group by sector
    sector_values: dict[str, float] = defaultdict(float)
    for h in holdings:
        sector_values[h["sector"]] += h["value"]
    if cash_value > 0:
        sector_values["Cash & Liquid"] += cash_value

    by_sector = []
    for sector, val in sorted(sector_values.items(), key=lambda x: x[1], reverse=True):
        by_sector.append({
            "label": sector,
            "value": round(val, 2),
            "pct": round(val / total_with_cash * 100, 1) if total_with_cash > 0 else 0,
        })

    return {
        "holdings": holdings,
        "by_stock": by_stock,
        "by_sector": by_sector,
        "total_equity_value": round(total_value, 2),
        "cash_value": round(cash_value, 2),
        "total_value": round(total_with_cash, 2),
    }


# ═══════════════════════════════════════════════════════════
#  SECTOR ALLOCATION HISTORY
# ═══════════════════════════════════════════════════════════

@router.get(
    "/{portfolio_id}/sector-history",
    summary="PMS sector allocation history",
    description="Computes sector allocation at multiple historical points (today, 1M, 3M, 6M, 12M) using transaction replay and closest available prices. Returns allocation percentages per sector at each snapshot date.",
)
def get_sector_history(portfolio_id: int, db: Session = Depends(get_db)):
    """Compute sector allocation at multiple historical points (today, 1M, 3M, 6M, 12M).
    Uses transaction replay + closest available prices from IndexPrice table."""
    from dateutil.relativedelta import relativedelta

    txns = (
        db.query(PmsTransaction)
        .filter(PmsTransaction.portfolio_id == portfolio_id)
        .order_by(PmsTransaction.date)
        .all()
    )
    if not txns:
        return {"snapshots": [], "sectors": []}

    # Define snapshot dates
    today = date.today()
    snapshot_labels = ["Today", "1M", "3M", "6M", "12M"]
    snapshot_dates = [
        today,
        today - relativedelta(months=1),
        today - relativedelta(months=3),
        today - relativedelta(months=6),
        today - relativedelta(months=12),
    ]

    # Build sector map for all scripts ever traded
    all_scripts = set(t.script for t in txns)
    sectors: dict[str, str] = {}
    unknown = []
    for s in all_scripts:
        if s in SCRIPT_SECTOR_MAP:
            sectors[s] = SCRIPT_SECTOR_MAP[s]
        else:
            unknown.append(s)
    if unknown:
        try:
            import yfinance as yf
            for s in unknown:
                try:
                    info = yf.Ticker(f"{s}.NS").info
                    sectors[s] = info.get("sector", "Other") or "Other"
                except Exception:
                    sectors[s] = "Other"
        except Exception:
            for s in unknown:
                sectors[s] = "Other"

    # Collect all scripts that were ever held to fetch prices in bulk
    # For each snapshot date, compute net holdings up to that date
    snapshot_holdings: list[dict[str, float]] = []
    for snap_date in snapshot_dates:
        net_qty: dict[str, float] = defaultdict(float)
        for t in txns:
            if t.date > snap_date:
                break
            if t.buy_qty and t.buy_qty > 0:
                net_qty[t.script] += t.buy_qty
            if t.sale_qty and t.sale_qty > 0:
                net_qty[t.script] -= t.sale_qty
        active = {k: v for k, v in net_qty.items() if v > 0.5}
        snapshot_holdings.append(active)

    # Get all unique scripts across all snapshots
    all_active_scripts = set()
    for sh in snapshot_holdings:
        all_active_scripts.update(sh.keys())

    # Fetch prices: for today use live, for historical use IndexPrice closest date
    from price_service import get_batch_prices

    # Live prices for today
    live_prices = get_batch_prices(list(all_active_scripts)) if all_active_scripts else {}

    # Historical prices from IndexPrice (closest available date)
    def _get_price_on_date(script: str, target_date: date) -> float | None:
        row = (
            db.query(IndexPrice)
            .filter(
                IndexPrice.index_name == script,
                IndexPrice.date <= str(target_date),
            )
            .order_by(desc(IndexPrice.date))
            .first()
        )
        if row and row.close_price:
            return float(row.close_price)
        return None

    # Also get cash from PmsNavDaily for each snapshot
    def _get_cash_on_date(pid: int, target_date: date) -> float:
        nav_row = (
            db.query(PmsNavDaily)
            .filter(PmsNavDaily.portfolio_id == pid, PmsNavDaily.date <= target_date)
            .order_by(desc(PmsNavDaily.date))
            .first()
        )
        if nav_row:
            return (nav_row.cash_equivalent or 0) + (nav_row.bank_balance or 0)
        return 0.0

    # Compute sector allocation for each snapshot
    all_sectors_set: set[str] = set()
    snapshots = []
    for i, (label, snap_date, holdings) in enumerate(
        zip(snapshot_labels, snapshot_dates, snapshot_holdings)
    ):
        if not holdings:
            snapshots.append({"label": label, "date": str(snap_date), "sectors": {}})
            continue

        # Get prices
        sector_values: dict[str, float] = defaultdict(float)
        for script, qty in holdings.items():
            if i == 0:
                price = live_prices.get(script, {}).get("current_price")
            else:
                price = _get_price_on_date(script, snap_date)
                if not price:
                    price = live_prices.get(script, {}).get("current_price")
            if price:
                sector = sectors.get(script, "Other")
                sector_values[sector] += qty * price

        cash = _get_cash_on_date(portfolio_id, snap_date)
        if cash > 0:
            sector_values["Cash & Liquid"] += cash

        total = sum(sector_values.values())
        sector_pcts = {}
        for sec, val in sector_values.items():
            sector_pcts[sec] = round(val / total * 100, 1) if total > 0 else 0
            all_sectors_set.add(sec)

        snapshots.append({
            "label": label,
            "date": str(snap_date),
            "sectors": sector_pcts,
        })

    return {
        "snapshots": snapshots,
        "sectors": sorted(all_sectors_set),
    }


# ═══════════════════════════════════════════════════════════
#  RISK ANALYTICS (enhanced risk management metrics)
# ═══════════════════════════════════════════════════════════

@router.get(
    "/{portfolio_id}/risk-analytics",
    summary="PMS enhanced risk analytics",
    description="Enhanced risk management metrics including Ulcer Index, up/down capture ratios, beta, information ratio, monthly win/loss stats, and cash allocation analysis. Supports period filtering.",
)
def get_risk_analytics(portfolio_id: int, period: str = "all", db: Session = Depends(get_db)):
    """Enhanced risk management metrics: Ulcer Index, capture ratios, beta,
    information ratio, monthly stats, cash allocation analysis."""
    metrics = compute_enhanced_risk_metrics(portfolio_id, db, period=period)
    if not metrics:
        raise HTTPException(status_code=404, detail="Insufficient data for risk analytics")
    return {"portfolio_id": portfolio_id, "period": period, **metrics}


# ═══════════════════════════════════════════════════════════
#  SUMMARY
# ═══════════════════════════════════════════════════════════

@router.get(
    "/{portfolio_id}/summary",
    summary="PMS quick summary",
    description="Returns a quick summary of the PMS portfolio including latest NAV, corpus, key return metrics, and inception date.",
)
def get_summary(portfolio_id: int, db: Session = Depends(get_db)):
    """Quick summary: latest NAV, corpus, key metrics."""
    summary = get_pms_summary(portfolio_id, db)
    if not summary:
        raise HTTPException(status_code=404, detail="No PMS data for this portfolio")
    return {"portfolio_id": portfolio_id, **summary}


# ─── Helpers ──────────────────────────────────────────────

def _is_nan(value) -> bool:
    """Check if a value is NaN (works for float and numpy)."""
    try:
        import math
        return value is None or (isinstance(value, float) and math.isnan(value))
    except (TypeError, ValueError):
        return False


def _nan_to_none(value):
    """Convert NaN to None for DB storage."""
    return None if _is_nan(value) else value
