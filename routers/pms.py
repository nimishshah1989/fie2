"""
FIE v3 — PMS Router
Upload PMS Excel files, query NAV history, metrics, drawdowns, transactions,
win/loss analysis.
"""

import logging
from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import desc

from models import (
    get_db, ModelPortfolio, PmsNavDaily, PmsTransaction,
    PortfolioMetric, DrawdownEvent, IndexPrice,
)
from services.pms_service import (
    parse_nav_excel, parse_transaction_excel,
    recalculate_portfolio_metrics, detect_drawdown_events,
    compute_monthly_returns, get_pms_summary,
)

logger = logging.getLogger("fie_v3.pms")
router = APIRouter(prefix="/api/pms", tags=["pms"])

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


# ═══════════════════════════════════════════════════════════
#  UPLOAD
# ═══════════════════════════════════════════════════════════

@router.post("/upload")
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

@router.get("/{portfolio_id}/nav")
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
                IndexPrice.index_name == "NIFTY 50",
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
#  METRICS
# ═══════════════════════════════════════════════════════════

@router.get("/{portfolio_id}/metrics")
def get_metrics(portfolio_id: int, db: Session = Depends(get_db)):
    """Return risk/return metrics for all computed periods."""
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

    # Sort by period order
    period_order = {'1M': 0, '3M': 1, '6M': 2, '1Y': 3, '3Y': 4, '5Y': 5, 'SI': 6}
    latest_metrics.sort(key=lambda m: period_order.get(m.period, 99))

    return {
        "portfolio_id": portfolio_id,
        "as_of_date": str(latest_date),
        "metrics": [
            {
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
            }
            for m in latest_metrics
        ],
    }


# ═══════════════════════════════════════════════════════════
#  DRAWDOWNS
# ═══════════════════════════════════════════════════════════

@router.get("/{portfolio_id}/drawdowns")
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

@router.get("/{portfolio_id}/transactions")
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

@router.get("/{portfolio_id}/win-loss")
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

@router.get("/{portfolio_id}/monthly-returns")
def get_monthly_returns(portfolio_id: int, db: Session = Depends(get_db)):
    """Return monthly NAV returns for calendar heatmap."""
    returns = compute_monthly_returns(portfolio_id, db)
    return {"portfolio_id": portfolio_id, "monthly_returns": returns}


# ═══════════════════════════════════════════════════════════
#  SUMMARY
# ═══════════════════════════════════════════════════════════

@router.get("/{portfolio_id}/summary")
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
