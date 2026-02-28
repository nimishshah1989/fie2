"""
Portfolio Server — Jhaveri Intelligence Platform
Standalone FastAPI app for Model Portfolio Management.
Runs on port 8001, shares DB with main server.
"""

import logging
import csv
import io
import json
import subprocess
import threading
from datetime import datetime, date as date_type, timedelta
from typing import Optional, List, Dict

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from portfolio_models import (
    init_portfolio_db, ModelPortfolio, PortfolioHolding,
    PortfolioTransaction, PortfolioNAV,
    PortfolioStatus, TransactionType,
)
from models import SessionLocal, IndexPrice

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ─── FastAPI App ───────────────────────────────────────

app = FastAPI(title="JIP Portfolio Server", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Live Prices via curl + Yahoo Finance ────────────

# Ticker-to-Yahoo-symbol map (same as backfill_nav.py)
YAHOO_SYMBOL_MAP: Dict[str, Optional[str]] = {
    "LIQUIDCASE": "LIQUIDBEES.NS",
    "CPSEETF": "CPSEETF.NS",
    "METALETF": "METALIETF.NS",
    "SENSEXETF": "SENSEXETF.NS",
    "MASPTOP50": "MASPTOP50.NS",
    "NETFMID150": "NETFMID150.NS",
    "GROWWDEFNC": None,
    "FMCGIETF": "FMCGIETF.NS",
    "OIL ETF": "OILIETF.NS",
    "NIPPONAMC - NETFAUTO": "NETFAUTO.NS",
}


def _get_yahoo_symbol(ticker: str) -> Optional[str]:
    if ticker in YAHOO_SYMBOL_MAP:
        return YAHOO_SYMBOL_MAP[ticker]
    return f"{ticker}.NS"


def _fetch_live_price_curl(yf_symbol: str) -> Optional[Dict]:
    """Fetch current price from Yahoo Finance using curl (bypasses Python SSL issues)."""
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_symbol}"
        f"?interval=1d&range=2d"
    )
    try:
        result = subprocess.run(
            ["curl", "-s", url, "-H", "User-Agent: Mozilla/5.0"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
        current_price = meta.get("regularMarketPrice")
        prev_close = meta.get("previousClose") or meta.get("chartPreviousClose")

        if not current_price:
            return None

        change_pct = None
        if prev_close and prev_close > 0:
            change_pct = round(((current_price / prev_close) - 1) * 100, 2)

        return {"current_price": current_price, "change_pct": change_pct}
    except Exception as exc:
        logger.debug("curl price fetch failed for %s: %s", yf_symbol, exc)
        return None


def get_live_prices(tickers: List[str]) -> Dict[str, Dict]:
    """
    Fetch live prices for a list of portfolio tickers via Yahoo Finance curl.
    Returns: {ticker: {"current_price": float, "change_pct": float}}
    """
    prices: Dict[str, Dict] = {}
    for ticker in tickers:
        yf_sym = _get_yahoo_symbol(ticker)
        if not yf_sym:
            continue
        data = _fetch_live_price_curl(yf_sym)
        if data:
            prices[ticker] = data
    return prices


# ─── Pydantic Models ──────────────────────────────────

class CreatePortfolioRequest(BaseModel):
    name: str
    description: Optional[str] = None
    benchmark: Optional[str] = "NIFTY"

class UpdatePortfolioRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    benchmark: Optional[str] = None

class CreateTransactionRequest(BaseModel):
    ticker: str
    txn_type: str  # "BUY" or "SELL"
    quantity: int
    price: float
    txn_date: str  # "YYYY-MM-DD"
    notes: Optional[str] = None
    exchange: Optional[str] = "NSE"
    sector: Optional[str] = None


# ─── Health ────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "portfolio", "version": "1.0"}


# ─── Portfolio CRUD ────────────────────────────────────

@app.post("/api/portfolios")
async def create_portfolio(req: CreatePortfolioRequest, db: Session = Depends(get_db)):
    portfolio = ModelPortfolio(
        name=req.name,
        description=req.description,
        benchmark=req.benchmark or "NIFTY",
    )
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return {"success": True, "id": portfolio.id, "name": portfolio.name}


@app.get("/api/portfolios")
async def list_portfolios(db: Session = Depends(get_db)):
    portfolios = (
        db.query(ModelPortfolio)
        .filter(ModelPortfolio.status == PortfolioStatus.ACTIVE)
        .order_by(desc(ModelPortfolio.updated_at))
        .all()
    )

    results = []
    for p in portfolios:
        holdings = (
            db.query(PortfolioHolding)
            .filter(PortfolioHolding.portfolio_id == p.id, PortfolioHolding.quantity > 0)
            .all()
        )
        total_invested = sum(h.total_cost for h in holdings)

        # Get live prices for summary
        current_value = total_invested  # default fallback
        tickers = [h.ticker for h in holdings if h.ticker]
        if tickers:
            prices = get_live_prices(tickers)
            if prices:
                current_value = 0.0
                for h in holdings:
                    cp = prices.get(h.ticker, {}).get("current_price")
                    if cp:
                        current_value += h.quantity * cp
                    else:
                        current_value += h.total_cost

        # Cumulative realized P&L
        realized = (
            db.query(func.sum(PortfolioTransaction.realized_pnl))
            .filter(
                PortfolioTransaction.portfolio_id == p.id,
                PortfolioTransaction.txn_type == TransactionType.SELL,
            )
            .scalar()
        ) or 0.0

        total_return = (current_value - total_invested) + realized
        total_return_pct = (total_return / total_invested * 100) if total_invested > 0 else 0.0

        results.append({
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "benchmark": p.benchmark,
            "status": p.status.value if p.status else "ACTIVE",
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "num_holdings": len([h for h in holdings if h.quantity > 0]),
            "total_invested": round(total_invested, 2),
            "current_value": round(current_value, 2),
            "realized_pnl": round(realized, 2),
            "total_return_pct": round(total_return_pct, 2),
        })

    return {"success": True, "portfolios": results}


@app.get("/api/portfolios/{portfolio_id}")
async def get_portfolio(portfolio_id: int, db: Session = Depends(get_db)):
    p = db.query(ModelPortfolio).filter(ModelPortfolio.id == portfolio_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "benchmark": p.benchmark,
        "status": p.status.value if p.status else "ACTIVE",
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


@app.put("/api/portfolios/{portfolio_id}")
async def update_portfolio(
    portfolio_id: int, req: UpdatePortfolioRequest, db: Session = Depends(get_db)
):
    p = db.query(ModelPortfolio).filter(ModelPortfolio.id == portfolio_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    if req.name is not None:
        p.name = req.name
    if req.description is not None:
        p.description = req.description
    if req.benchmark is not None:
        p.benchmark = req.benchmark

    db.commit()
    return {"success": True, "id": p.id}


@app.delete("/api/portfolios/{portfolio_id}")
async def archive_portfolio(portfolio_id: int, db: Session = Depends(get_db)):
    p = db.query(ModelPortfolio).filter(ModelPortfolio.id == portfolio_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    p.status = PortfolioStatus.ARCHIVED
    db.commit()
    return {"success": True, "id": p.id, "status": "ARCHIVED"}


# ─── Transactions ──────────────────────────────────────

@app.post("/api/portfolios/{portfolio_id}/transactions")
async def create_transaction(
    portfolio_id: int, req: CreateTransactionRequest, db: Session = Depends(get_db)
):
    # Validate portfolio exists
    portfolio = db.query(ModelPortfolio).filter(ModelPortfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Validate inputs
    if req.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")
    if req.price <= 0:
        raise HTTPException(status_code=400, detail="Price must be positive")

    ticker = req.ticker.upper().strip()
    txn_type_str = req.txn_type.upper().strip()
    if txn_type_str not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="txn_type must be BUY or SELL")

    txn_type = TransactionType.BUY if txn_type_str == "BUY" else TransactionType.SELL
    total_value = req.quantity * req.price

    # Find existing holding
    holding = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.portfolio_id == portfolio_id, PortfolioHolding.ticker == ticker)
        .first()
    )

    realized_pnl = None
    realized_pnl_pct = None
    cost_basis_at_sell = None

    if txn_type == TransactionType.BUY:
        if holding:
            # Update existing holding with weighted average cost
            new_qty = holding.quantity + req.quantity
            new_total_cost = holding.total_cost + total_value
            holding.quantity = new_qty
            holding.total_cost = new_total_cost
            holding.avg_cost = new_total_cost / new_qty if new_qty > 0 else 0.0
            if req.sector:
                holding.sector = req.sector
        else:
            # Create new holding
            holding = PortfolioHolding(
                portfolio_id=portfolio_id,
                ticker=ticker,
                exchange=req.exchange or "NSE",
                quantity=req.quantity,
                avg_cost=req.price,
                total_cost=total_value,
                sector=req.sector,
            )
            db.add(holding)

        # Fetch 1Y stock history in background for NAV computation
        _background_fetch_stock_history(ticker)

    elif txn_type == TransactionType.SELL:
        if not holding or holding.quantity <= 0:
            raise HTTPException(status_code=400, detail=f"No holding for {ticker} to sell")
        if req.quantity > holding.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot sell {req.quantity}, only {holding.quantity} held"
            )

        # Calculate realized P&L
        cost_basis_at_sell = holding.avg_cost
        realized_pnl = (req.price - holding.avg_cost) * req.quantity
        realized_pnl_pct = ((req.price / holding.avg_cost) - 1) * 100 if holding.avg_cost > 0 else 0.0

        # Update holding
        new_qty = holding.quantity - req.quantity
        if new_qty == 0:
            # Fully exited — remove holding
            db.delete(holding)
        else:
            holding.quantity = new_qty
            holding.total_cost = new_qty * holding.avg_cost

    # Create transaction record
    txn = PortfolioTransaction(
        portfolio_id=portfolio_id,
        ticker=ticker,
        exchange=req.exchange or "NSE",
        txn_type=txn_type,
        quantity=req.quantity,
        price=req.price,
        total_value=total_value,
        txn_date=req.txn_date,
        notes=req.notes,
        realized_pnl=realized_pnl,
        realized_pnl_pct=round(realized_pnl_pct, 2) if realized_pnl_pct is not None else None,
        cost_basis_at_sell=cost_basis_at_sell,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    result = {
        "success": True,
        "transaction_id": txn.id,
        "txn_type": txn_type_str,
        "ticker": ticker,
        "quantity": req.quantity,
        "price": req.price,
        "total_value": total_value,
    }
    if realized_pnl is not None:
        result["realized_pnl"] = round(realized_pnl, 2)
        result["realized_pnl_pct"] = round(realized_pnl_pct, 2)

    return result


@app.get("/api/portfolios/{portfolio_id}/transactions")
async def list_transactions(
    portfolio_id: int,
    txn_type: Optional[str] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    query = (
        db.query(PortfolioTransaction)
        .filter(PortfolioTransaction.portfolio_id == portfolio_id)
    )
    if txn_type and txn_type.upper() in ("BUY", "SELL"):
        query = query.filter(
            PortfolioTransaction.txn_type == TransactionType(txn_type.upper())
        )

    txns = query.order_by(desc(PortfolioTransaction.txn_date)).limit(limit).all()

    return {
        "success": True,
        "transactions": [
            {
                "id": t.id,
                "ticker": t.ticker,
                "exchange": t.exchange,
                "txn_type": t.txn_type.value if t.txn_type else None,
                "quantity": t.quantity,
                "price": t.price,
                "total_value": t.total_value,
                "txn_date": t.txn_date,
                "notes": t.notes,
                "realized_pnl": t.realized_pnl,
                "realized_pnl_pct": t.realized_pnl_pct,
                "cost_basis_at_sell": t.cost_basis_at_sell,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in txns
        ],
    }


# ─── Holdings (with Live Prices) ──────────────────────

@app.get("/api/portfolios/{portfolio_id}/holdings")
async def list_holdings(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = db.query(ModelPortfolio).filter(ModelPortfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    holdings = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.portfolio_id == portfolio_id, PortfolioHolding.quantity > 0)
        .order_by(desc(PortfolioHolding.total_cost))
        .all()
    )

    if not holdings:
        return {"success": True, "holdings": [], "totals": _empty_totals()}

    # Batch fetch live prices via curl
    tickers = [h.ticker for h in holdings]
    prices = get_live_prices(tickers)

    # Build response with P&L
    total_invested = 0.0
    total_current = 0.0
    rows = []

    for h in holdings:
        price_data = prices.get(h.ticker, {})
        current_price = price_data.get("current_price")
        day_change_pct = price_data.get("change_pct")

        current_value = (h.quantity * current_price) if current_price else None
        unrealized_pnl = (current_value - h.total_cost) if current_value else None
        unrealized_pnl_pct = (
            ((current_price / h.avg_cost) - 1) * 100
            if current_price and h.avg_cost > 0
            else None
        )

        total_invested += h.total_cost
        if current_value:
            total_current += current_value
        else:
            total_current += h.total_cost  # fallback

        rows.append({
            "id": h.id,
            "ticker": h.ticker,
            "exchange": h.exchange,
            "sector": h.sector,
            "quantity": h.quantity,
            "avg_cost": round(h.avg_cost, 2),
            "total_cost": round(h.total_cost, 2),
            "current_price": round(current_price, 2) if current_price else None,
            "current_value": round(current_value, 2) if current_value else None,
            "unrealized_pnl": round(unrealized_pnl, 2) if unrealized_pnl is not None else None,
            "unrealized_pnl_pct": round(unrealized_pnl_pct, 2) if unrealized_pnl_pct is not None else None,
            "day_change_pct": round(day_change_pct, 2) if day_change_pct is not None else None,
            "weight_pct": None,  # filled below
        })

    # Calculate weights
    for row in rows:
        cv = row["current_value"] or row["total_cost"]
        row["weight_pct"] = round((cv / total_current) * 100, 2) if total_current > 0 else 0.0

    # Realized P&L
    realized_total = (
        db.query(func.sum(PortfolioTransaction.realized_pnl))
        .filter(
            PortfolioTransaction.portfolio_id == portfolio_id,
            PortfolioTransaction.txn_type == TransactionType.SELL,
        )
        .scalar()
    ) or 0.0

    totals = {
        "total_invested": round(total_invested, 2),
        "current_value": round(total_current, 2),
        "unrealized_pnl": round(total_current - total_invested, 2),
        "unrealized_pnl_pct": round(
            ((total_current - total_invested) / total_invested) * 100, 2
        ) if total_invested > 0 else 0.0,
        "realized_pnl": round(realized_total, 2),
        "num_holdings": len(rows),
    }

    return {"success": True, "holdings": rows, "totals": totals}


def _empty_totals():
    return {
        "total_invested": 0.0,
        "current_value": 0.0,
        "unrealized_pnl": 0.0,
        "unrealized_pnl_pct": 0.0,
        "realized_pnl": 0.0,
        "num_holdings": 0,
    }


# ─── NAV Computation ──────────────────────────────────

def _compute_nav_for_portfolio(portfolio_id: int, date_str: str, db: Session):
    """Compute and store daily NAV snapshot for a portfolio."""
    holdings = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.portfolio_id == portfolio_id, PortfolioHolding.quantity > 0)
        .all()
    )

    if not holdings:
        return None

    total_value = 0.0
    total_cost = 0.0

    for h in holdings:
        # Look up latest close price from IndexPrice table
        price_row = (
            db.query(IndexPrice)
            .filter(IndexPrice.index_name == h.ticker, IndexPrice.date <= date_str)
            .order_by(desc(IndexPrice.date))
            .first()
        )
        close = price_row.close_price if price_row and price_row.close_price else h.avg_cost
        total_value += h.quantity * close
        total_cost += h.quantity * h.avg_cost

    # Cumulative realized P&L up to this date
    realized_sum = (
        db.query(func.sum(PortfolioTransaction.realized_pnl))
        .filter(
            PortfolioTransaction.portfolio_id == portfolio_id,
            PortfolioTransaction.txn_type == TransactionType.SELL,
            PortfolioTransaction.txn_date <= date_str,
        )
        .scalar()
    ) or 0.0

    # Upsert NAV row
    nav = (
        db.query(PortfolioNAV)
        .filter(PortfolioNAV.portfolio_id == portfolio_id, PortfolioNAV.date == date_str)
        .first()
    )
    if not nav:
        nav = PortfolioNAV(portfolio_id=portfolio_id, date=date_str)
        db.add(nav)

    nav.total_value = round(total_value, 2)
    nav.total_cost = round(total_cost, 2)
    nav.unrealized_pnl = round(total_value - total_cost, 2)
    nav.realized_pnl_cumulative = round(realized_sum, 2)
    nav.num_holdings = len([h for h in holdings if h.quantity > 0])
    nav.computed_at = datetime.now()

    db.commit()
    return nav


@app.post("/api/portfolios/{portfolio_id}/compute-nav")
async def compute_nav(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = db.query(ModelPortfolio).filter(ModelPortfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    today_str = date_type.today().strftime("%Y-%m-%d")
    nav = _compute_nav_for_portfolio(portfolio_id, today_str, db)

    if nav:
        return {
            "success": True,
            "date": today_str,
            "total_value": nav.total_value,
            "total_cost": nav.total_cost,
            "unrealized_pnl": nav.unrealized_pnl,
        }
    return {"success": True, "message": "No holdings to compute NAV for"}


@app.post("/api/portfolios/compute-nav")
async def compute_nav_all(db: Session = Depends(get_db)):
    """Compute NAV for all active portfolios."""
    portfolios = (
        db.query(ModelPortfolio)
        .filter(ModelPortfolio.status == PortfolioStatus.ACTIVE)
        .all()
    )
    today_str = date_type.today().strftime("%Y-%m-%d")
    computed = 0
    for p in portfolios:
        nav = _compute_nav_for_portfolio(p.id, today_str, db)
        if nav:
            computed += 1

    return {"success": True, "computed": computed, "date": today_str}


# ─── NAV History (for Charts) ─────────────────────────

PERIOD_DAYS = {
    "1m": 30, "3m": 90, "6m": 180, "1y": 365, "ytd": None, "all": None,
}

@app.get("/api/portfolios/{portfolio_id}/nav-history")
async def get_nav_history(
    portfolio_id: int, period: str = "all", db: Session = Depends(get_db)
):
    portfolio = db.query(ModelPortfolio).filter(ModelPortfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    query = (
        db.query(PortfolioNAV)
        .filter(PortfolioNAV.portfolio_id == portfolio_id)
    )

    # Apply period filter
    pk = period.lower()
    if pk == "ytd":
        year_start = f"{date_type.today().year}-01-01"
        query = query.filter(PortfolioNAV.date >= year_start)
    elif pk in PERIOD_DAYS and PERIOD_DAYS[pk] is not None:
        cutoff = (date_type.today() - timedelta(days=PERIOD_DAYS[pk])).strftime("%Y-%m-%d")
        query = query.filter(PortfolioNAV.date >= cutoff)

    nav_rows = query.order_by(PortfolioNAV.date).all()

    # Get benchmark data for the same date range
    benchmark_data = {}
    if nav_rows and portfolio.benchmark:
        benchmark_key = portfolio.benchmark
        dates = [n.date for n in nav_rows]
        if dates:
            bench_rows = (
                db.query(IndexPrice)
                .filter(
                    IndexPrice.index_name == benchmark_key,
                    IndexPrice.date >= dates[0],
                    IndexPrice.date <= dates[-1],
                )
                .order_by(IndexPrice.date)
                .all()
            )
            for br in bench_rows:
                benchmark_data[br.date] = br.close_price

    # Normalize benchmark to portfolio start value
    first_value = nav_rows[0].total_value if nav_rows else 1.0
    first_bench = None
    for n in nav_rows:
        bv = benchmark_data.get(n.date)
        if bv and first_bench is None:
            first_bench = bv
        break

    result = []
    for n in nav_rows:
        bv_raw = benchmark_data.get(n.date)
        benchmark_normalized = None
        if bv_raw and first_bench and first_bench > 0:
            benchmark_normalized = round((bv_raw / first_bench) * first_value, 2)

        result.append({
            "date": n.date,
            "total_value": n.total_value,
            "total_cost": n.total_cost,
            "unrealized_pnl": n.unrealized_pnl,
            "benchmark_value": benchmark_normalized,
        })

    return {"success": True, "nav_history": result, "period": period}


# ─── Performance Metrics ──────────────────────────────

def _compute_xirr(cashflows):
    """
    Compute XIRR using Newton-Raphson. No scipy required.
    cashflows: list of (date, amount) where buys are negative, sells/current value positive.
    Returns rate as percentage, or None on failure.
    """
    if not cashflows or len(cashflows) < 2:
        return None

    t0 = cashflows[0][0]
    days = [(d - t0).days / 365.0 for d, _ in cashflows]
    amounts = [a for _, a in cashflows]

    # Newton-Raphson
    rate = 0.1  # initial guess: 10%
    for _ in range(100):
        npv = sum(a / (1 + rate) ** t for a, t in zip(amounts, days))
        dnpv = sum(-t * a / (1 + rate) ** (t + 1) for a, t in zip(amounts, days))
        if abs(dnpv) < 1e-12:
            break
        new_rate = rate - npv / dnpv
        if abs(new_rate - rate) < 1e-8:
            return round(new_rate * 100, 2)
        rate = new_rate
        # Guard against divergence
        if rate < -0.99 or rate > 100:
            return None

    return round(rate * 100, 2)


def _compute_max_drawdown(values):
    """Compute max drawdown from a list of portfolio values. Returns negative percentage."""
    if len(values) < 2:
        return None
    peak = values[0]
    max_dd = 0.0
    for val in values:
        if val > peak:
            peak = val
        dd = (val - peak) / peak if peak > 0 else 0
        if dd < max_dd:
            max_dd = dd
    return round(max_dd * 100, 2)


@app.get("/api/portfolios/{portfolio_id}/performance")
async def get_performance(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = db.query(ModelPortfolio).filter(ModelPortfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Current holdings
    holdings = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.portfolio_id == portfolio_id, PortfolioHolding.quantity > 0)
        .all()
    )
    total_invested = sum(h.total_cost for h in holdings)

    # Live prices for current value
    current_value = total_invested
    tickers = [h.ticker for h in holdings if h.ticker]
    if tickers:
        prices = get_live_prices(tickers)
        if prices:
            current_value = 0.0
            for h in holdings:
                cp = prices.get(h.ticker, {}).get("current_price")
                current_value += (h.quantity * cp) if cp else h.total_cost

    # Realized P&L
    realized_pnl = (
        db.query(func.sum(PortfolioTransaction.realized_pnl))
        .filter(
            PortfolioTransaction.portfolio_id == portfolio_id,
            PortfolioTransaction.txn_type == TransactionType.SELL,
        )
        .scalar()
    ) or 0.0

    unrealized_pnl = current_value - total_invested
    total_return = unrealized_pnl + realized_pnl
    total_return_pct = (total_return / total_invested * 100) if total_invested > 0 else 0.0

    # XIRR: build cashflow list from all transactions
    txns = (
        db.query(PortfolioTransaction)
        .filter(PortfolioTransaction.portfolio_id == portfolio_id)
        .order_by(PortfolioTransaction.txn_date)
        .all()
    )
    cashflows = []
    for t in txns:
        try:
            d = datetime.strptime(t.txn_date, "%Y-%m-%d").date()
        except ValueError:
            continue
        if t.txn_type == TransactionType.BUY:
            cashflows.append((d, -t.total_value))
        else:
            cashflows.append((d, t.total_value))

    # Add current portfolio value as final positive cashflow
    if current_value > 0 and cashflows:
        cashflows.append((date_type.today(), current_value))

    xirr = _compute_xirr(cashflows)

    # CAGR from first transaction to today
    cagr = None
    if txns and total_invested > 0:
        try:
            first_date = datetime.strptime(txns[0].txn_date, "%Y-%m-%d").date()
            days_elapsed = (date_type.today() - first_date).days
            if days_elapsed > 0:
                years = days_elapsed / 365.0
                end_value = current_value + realized_pnl
                cagr = round(((end_value / total_invested) ** (1 / years) - 1) * 100, 2)
        except (ValueError, ZeroDivisionError):
            pass

    # Max drawdown from NAV history
    nav_values = (
        db.query(PortfolioNAV.total_value)
        .filter(PortfolioNAV.portfolio_id == portfolio_id)
        .order_by(PortfolioNAV.date)
        .all()
    )
    max_drawdown = _compute_max_drawdown([v[0] for v in nav_values]) if nav_values else None

    # Benchmark return
    benchmark_return_pct = None
    alpha = None
    if portfolio.benchmark and txns:
        try:
            first_date_str = txns[0].txn_date
            today_str = date_type.today().strftime("%Y-%m-%d")
            bench_start = (
                db.query(IndexPrice)
                .filter(IndexPrice.index_name == portfolio.benchmark, IndexPrice.date >= first_date_str)
                .order_by(IndexPrice.date)
                .first()
            )
            bench_end = (
                db.query(IndexPrice)
                .filter(IndexPrice.index_name == portfolio.benchmark, IndexPrice.date <= today_str)
                .order_by(desc(IndexPrice.date))
                .first()
            )
            if bench_start and bench_end and bench_start.close_price and bench_start.close_price > 0:
                benchmark_return_pct = round(
                    ((bench_end.close_price / bench_start.close_price) - 1) * 100, 2
                )
                alpha = round(total_return_pct - benchmark_return_pct, 2)
        except Exception:
            pass

    return {
        "success": True,
        "performance": {
            "total_invested": round(total_invested, 2),
            "current_value": round(current_value, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "unrealized_pnl_pct": round(
                (unrealized_pnl / total_invested * 100), 2
            ) if total_invested > 0 else 0.0,
            "realized_pnl": round(realized_pnl, 2),
            "total_return": round(total_return, 2),
            "total_return_pct": round(total_return_pct, 2),
            "xirr": xirr,
            "cagr": cagr,
            "max_drawdown": max_drawdown,
            "benchmark_return_pct": benchmark_return_pct,
            "alpha": alpha,
        },
    }


# ─── Allocation ────────────────────────────────────────

@app.get("/api/portfolios/{portfolio_id}/allocation")
async def get_allocation(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = db.query(ModelPortfolio).filter(ModelPortfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    holdings = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.portfolio_id == portfolio_id, PortfolioHolding.quantity > 0)
        .all()
    )

    if not holdings:
        return {"success": True, "by_stock": [], "by_sector": []}

    # Get live prices via curl
    tickers = [h.ticker for h in holdings]
    prices = get_live_prices(tickers)

    # Build stock allocation
    stock_items = []
    sector_map = {}
    total_value = 0.0

    for h in holdings:
        cp = prices.get(h.ticker, {}).get("current_price")
        value = (h.quantity * cp) if cp else h.total_cost
        total_value += value
        stock_items.append({"label": h.ticker, "value": round(value, 2), "sector": h.sector or "Other"})

        sector = h.sector or "Other"
        sector_map[sector] = sector_map.get(sector, 0) + value

    # Add percentages
    by_stock = [
        {
            "label": s["label"],
            "value": s["value"],
            "pct": round((s["value"] / total_value) * 100, 2) if total_value > 0 else 0,
        }
        for s in sorted(stock_items, key=lambda x: x["value"], reverse=True)
    ]

    by_sector = [
        {
            "label": sector,
            "value": round(val, 2),
            "pct": round((val / total_value) * 100, 2) if total_value > 0 else 0,
        }
        for sector, val in sorted(sector_map.items(), key=lambda x: x[1], reverse=True)
    ]

    return {"success": True, "by_stock": by_stock, "by_sector": by_sector}


# ─── CSV Export ────────────────────────────────────────

@app.get("/api/portfolios/{portfolio_id}/export/holdings")
async def export_holdings_csv(portfolio_id: int, db: Session = Depends(get_db)):
    holdings = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.portfolio_id == portfolio_id, PortfolioHolding.quantity > 0)
        .order_by(desc(PortfolioHolding.total_cost))
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Ticker", "Exchange", "Sector", "Quantity", "Avg Cost", "Total Cost"])
    for h in holdings:
        writer.writerow([h.ticker, h.exchange, h.sector or "", h.quantity, h.avg_cost, h.total_cost])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=holdings_portfolio_{portfolio_id}.csv"},
    )


@app.get("/api/portfolios/{portfolio_id}/export/transactions")
async def export_transactions_csv(portfolio_id: int, db: Session = Depends(get_db)):
    txns = (
        db.query(PortfolioTransaction)
        .filter(PortfolioTransaction.portfolio_id == portfolio_id)
        .order_by(desc(PortfolioTransaction.txn_date))
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Type", "Ticker", "Quantity", "Price", "Total Value", "Realized P&L", "Notes"])
    for t in txns:
        writer.writerow([
            t.txn_date,
            t.txn_type.value if t.txn_type else "",
            t.ticker,
            t.quantity,
            t.price,
            t.total_value,
            t.realized_pnl or "",
            t.notes or "",
        ])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=transactions_portfolio_{portfolio_id}.csv"},
    )


# ─── Background Helpers ───────────────────────────────

def _background_fetch_stock_history(ticker: str):
    """Fetch 1Y stock history in background thread and store in IndexPrice."""
    def _fetch():
        try:
            from price_service import fetch_stock_history
            rows = fetch_stock_history(ticker, "1y")
            if not rows:
                return

            db = SessionLocal()
            stored = 0
            for row in rows:
                if not row.get("close"):
                    continue
                existing = db.query(IndexPrice).filter_by(
                    date=row["date"], index_name=ticker
                ).first()
                if existing:
                    existing.close_price = row["close"]
                    existing.open_price = row.get("open")
                    existing.high_price = row.get("high")
                    existing.low_price = row.get("low")
                    existing.volume = row.get("volume")
                    existing.fetched_at = datetime.now()
                else:
                    db.add(IndexPrice(
                        date=row["date"], index_name=ticker,
                        close_price=row["close"], open_price=row.get("open"),
                        high_price=row.get("high"), low_price=row.get("low"),
                        volume=row.get("volume"),
                    ))
                stored += 1
            db.commit()
            db.close()
            logger.info("Background stock history: %s — stored %d rows", ticker, stored)
        except Exception as e:
            logger.warning("Background stock history fetch failed for %s: %s", ticker, e)

    thread = threading.Thread(target=_fetch, daemon=True)
    thread.start()


# ─── Startup ──────────────────────────────────────────

@app.on_event("startup")
async def startup():
    init_portfolio_db()
    logger.info("Portfolio server started on port 8001")

    # Schedule daily NAV computation
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        import pytz

        def _daily_nav_compute():
            db = SessionLocal()
            today_str = date_type.today().strftime("%Y-%m-%d")
            portfolios = db.query(ModelPortfolio).filter(
                ModelPortfolio.status == PortfolioStatus.ACTIVE
            ).all()
            for p in portfolios:
                _compute_nav_for_portfolio(p.id, today_str, db)
            db.close()
            logger.info("Daily NAV computed for %d portfolios", len(portfolios))

        scheduler = BackgroundScheduler()
        ist = pytz.timezone("Asia/Kolkata")
        scheduler.add_job(
            _daily_nav_compute,
            CronTrigger(hour=15, minute=35, timezone=ist),
            id="daily_portfolio_nav",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("APScheduler: daily NAV computation at 3:35 PM IST")
    except Exception as e:
        logger.warning("APScheduler not available: %s", e)
