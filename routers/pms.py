"""
FIE v3 — PMS Router
Upload PMS Excel files, query NAV history, metrics, drawdowns, transactions.
"""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import desc

from models import (
    get_db, ModelPortfolio, PmsNavDaily, PmsTransaction,
    PortfolioMetric, DrawdownEvent,
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
#  NAV HISTORY
# ═══════════════════════════════════════════════════════════

@router.get("/{portfolio_id}/nav")
def get_nav_history(
    portfolio_id: int,
    period: str = "all",
    db: Session = Depends(get_db),
):
    """Return NAV time series, optionally filtered by period."""
    query = db.query(PmsNavDaily).filter(PmsNavDaily.portfolio_id == portfolio_id)

    if period != "all":
        days_map = {'1M': 30, '3M': 90, '6M': 180, '1Y': 365, '3Y': 1095, '5Y': 1825}
        days = days_map.get(period.upper())
        if days:
            cutoff = date.today() - timedelta(days=days)
            query = query.filter(PmsNavDaily.date >= cutoff)

    rows = query.order_by(PmsNavDaily.date).all()
    return {
        "portfolio_id": portfolio_id,
        "count": len(rows),
        "nav_history": [
            {
                "date": str(r.date),
                "nav": r.nav,
                "unit_nav": r.unit_nav,
                "corpus": r.corpus,
                "equity_holding": r.equity_holding,
                "etf_investment": r.etf_investment,
                "cash_equivalent": r.cash_equivalent,
                "bank_balance": r.bank_balance,
                "liquidity_pct": r.liquidity_pct,
                "high_water_mark": r.high_water_mark,
            }
            for r in rows
        ],
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
