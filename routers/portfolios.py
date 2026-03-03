"""
FIE v3 — Portfolio Routes
CRUD, transactions, holdings with live prices, NAV, performance, allocation,
CSV export, and bulk import.
"""

import csv
import io
import logging
import threading
from datetime import date as date_type, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import desc, func as sa_func
from sqlalchemy.orm import Session

from models import (
    get_db, SessionLocal, IndexPrice,
    ModelPortfolio, PortfolioHolding, PortfolioTransaction, PortfolioNAV,
    PortfolioStatus, TransactionType,
)
from services.portfolio_service import (
    get_live_prices, compute_xirr, compute_max_drawdown,
    compute_nav_for_portfolio, empty_totals,
)

logger = logging.getLogger("fie_v3.portfolios")
router = APIRouter()


# ─── Pydantic Request Models ────────────────────────────

class CreatePortfolioRequest(BaseModel):
    name: str
    description: Optional[str] = None
    benchmark: Optional[str] = "NIFTY"
    inception_date: Optional[str] = None


class UpdatePortfolioRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    benchmark: Optional[str] = None


class CreateTransactionRequest(BaseModel):
    ticker: str
    txn_type: str
    quantity: int
    price: float
    txn_date: str
    notes: Optional[str] = None
    exchange: Optional[str] = "NSE"
    sector: Optional[str] = None


# ─── Portfolio CRUD ──────────────────────────────────────

@router.post("/api/portfolios")
async def create_portfolio(req: CreatePortfolioRequest, db: Session = Depends(get_db)):
    portfolio = ModelPortfolio(
        name=req.name, description=req.description, benchmark=req.benchmark or "NIFTY",
        inception_date=req.inception_date or date_type.today().strftime("%Y-%m-%d"),
    )
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return {"success": True, "id": portfolio.id, "name": portfolio.name}


@router.get("/api/portfolios")
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
        current_value = total_invested
        tickers = [h.ticker for h in holdings if h.ticker]
        if tickers:
            prices = get_live_prices(tickers)
            if prices:
                current_value = 0.0
                for h in holdings:
                    cp = prices.get(h.ticker, {}).get("current_price")
                    current_value += (h.quantity * cp) if cp else h.total_cost

        realized = (
            db.query(sa_func.sum(PortfolioTransaction.realized_pnl))
            .filter(
                PortfolioTransaction.portfolio_id == p.id,
                PortfolioTransaction.txn_type == TransactionType.SELL,
            )
            .scalar()
        ) or 0.0

        total_return = (current_value - total_invested) + realized
        total_return_pct = (total_return / total_invested * 100) if total_invested > 0 else 0.0

        results.append({
            "id": p.id, "name": p.name, "description": p.description,
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


@router.get("/api/portfolios/{portfolio_id}")
async def get_portfolio(portfolio_id: int, db: Session = Depends(get_db)):
    p = db.query(ModelPortfolio).filter(ModelPortfolio.id == portfolio_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return {
        "id": p.id, "name": p.name, "description": p.description,
        "benchmark": p.benchmark,
        "status": p.status.value if p.status else "ACTIVE",
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


@router.put("/api/portfolios/{portfolio_id}")
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


@router.delete("/api/portfolios/{portfolio_id}")
async def archive_portfolio(portfolio_id: int, db: Session = Depends(get_db)):
    p = db.query(ModelPortfolio).filter(ModelPortfolio.id == portfolio_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    p.status = PortfolioStatus.ARCHIVED
    db.commit()
    return {"success": True, "id": p.id, "status": "ARCHIVED"}


# ─── Transactions ────────────────────────────────────────

def _background_fetch_stock_history(ticker: str):
    """Fetch 1Y stock history in a background thread when a new stock is bought."""
    def _fetch():
        try:
            from price_service import fetch_stock_history
            from services.data_helpers import upsert_price_row
            rows = fetch_stock_history(ticker, "1y")
            if not rows:
                return
            db = SessionLocal()
            stored = 0
            for row in rows:
                if upsert_price_row(db, ticker, row):
                    stored += 1
            db.commit()
            db.close()
            logger.info("Background stock history: %s — stored %d rows", ticker, stored)
        except Exception as e:
            logger.warning("Background stock history fetch failed for %s: %s", ticker, e)
    thread = threading.Thread(target=_fetch, daemon=True)
    thread.start()


@router.post("/api/portfolios/{portfolio_id}/transactions")
async def create_transaction(
    portfolio_id: int, req: CreateTransactionRequest, db: Session = Depends(get_db)
):
    portfolio = db.query(ModelPortfolio).filter(ModelPortfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
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
            new_qty = holding.quantity + req.quantity
            new_total_cost = holding.total_cost + total_value
            holding.quantity = new_qty
            holding.total_cost = new_total_cost
            holding.avg_cost = new_total_cost / new_qty if new_qty > 0 else 0.0
            if req.sector:
                holding.sector = req.sector
        else:
            holding = PortfolioHolding(
                portfolio_id=portfolio_id, ticker=ticker,
                exchange=req.exchange or "NSE", quantity=req.quantity,
                avg_cost=req.price, total_cost=total_value, sector=req.sector,
            )
            db.add(holding)
        _background_fetch_stock_history(ticker)

    elif txn_type == TransactionType.SELL:
        if not holding or holding.quantity <= 0:
            raise HTTPException(status_code=400, detail=f"No holding for {ticker} to sell")
        if req.quantity > holding.quantity:
            raise HTTPException(status_code=400, detail=f"Cannot sell {req.quantity}, only {holding.quantity} held")
        cost_basis_at_sell = holding.avg_cost
        realized_pnl = (req.price - holding.avg_cost) * req.quantity
        realized_pnl_pct = ((req.price / holding.avg_cost) - 1) * 100 if holding.avg_cost > 0 else 0.0
        new_qty = holding.quantity - req.quantity
        if new_qty == 0:
            db.delete(holding)
        else:
            holding.quantity = new_qty
            holding.total_cost = new_qty * holding.avg_cost

    txn = PortfolioTransaction(
        portfolio_id=portfolio_id, ticker=ticker, exchange=req.exchange or "NSE",
        txn_type=txn_type, quantity=req.quantity, price=req.price,
        total_value=total_value, txn_date=req.txn_date, notes=req.notes,
        realized_pnl=realized_pnl,
        realized_pnl_pct=round(realized_pnl_pct, 2) if realized_pnl_pct is not None else None,
        cost_basis_at_sell=cost_basis_at_sell,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    result = {
        "success": True, "transaction_id": txn.id, "txn_type": txn_type_str,
        "ticker": ticker, "quantity": req.quantity, "price": req.price, "total_value": total_value,
    }
    if realized_pnl is not None:
        result["realized_pnl"] = round(realized_pnl, 2)
        result["realized_pnl_pct"] = round(realized_pnl_pct, 2)
    return result


@router.get("/api/portfolios/{portfolio_id}/transactions")
async def list_transactions(
    portfolio_id: int, txn_type: Optional[str] = None, limit: int = 200,
    db: Session = Depends(get_db),
):
    query = db.query(PortfolioTransaction).filter(PortfolioTransaction.portfolio_id == portfolio_id)
    if txn_type and txn_type.upper() in ("BUY", "SELL"):
        query = query.filter(PortfolioTransaction.txn_type == TransactionType(txn_type.upper()))
    txns = query.order_by(desc(PortfolioTransaction.txn_date)).limit(limit).all()
    return {
        "success": True,
        "transactions": [{
            "id": t.id, "ticker": t.ticker, "exchange": t.exchange,
            "txn_type": t.txn_type.value if t.txn_type else None,
            "quantity": t.quantity, "price": t.price, "total_value": t.total_value,
            "txn_date": t.txn_date, "notes": t.notes,
            "realized_pnl": t.realized_pnl, "realized_pnl_pct": t.realized_pnl_pct,
            "cost_basis_at_sell": t.cost_basis_at_sell,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        } for t in txns],
    }


# ─── Holdings (with Live Prices) ────────────────────────

@router.get("/api/portfolios/{portfolio_id}/holdings")
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
        return {"success": True, "holdings": [], "totals": empty_totals()}

    tickers = [h.ticker for h in holdings]
    overrides = {h.ticker: h.yf_symbol_override for h in holdings if h.yf_symbol_override}
    prices = get_live_prices(tickers, overrides=overrides)

    total_invested = 0.0
    total_current = 0.0
    rows = []
    market_times = []
    for h in holdings:
        price_data = prices.get(h.ticker, {})
        current_price = price_data.get("current_price")
        day_change_pct = price_data.get("change_pct")
        yf_symbol = price_data.get("yf_symbol")
        market_time = price_data.get("market_time")
        if market_time:
            market_times.append(market_time)
        current_value = (h.quantity * current_price) if current_price else None
        unrealized_pnl = (current_value - h.total_cost) if current_value else None
        unrealized_pnl_pct = (((current_price / h.avg_cost) - 1) * 100) if current_price and h.avg_cost > 0 else None
        total_invested += h.total_cost
        total_current += current_value if current_value else h.total_cost
        rows.append({
            "id": h.id, "ticker": h.ticker, "exchange": h.exchange, "sector": h.sector,
            "quantity": h.quantity, "avg_cost": round(h.avg_cost, 2), "total_cost": round(h.total_cost, 2),
            "current_price": round(current_price, 2) if current_price else None,
            "current_value": round(current_value, 2) if current_value else None,
            "unrealized_pnl": round(unrealized_pnl, 2) if unrealized_pnl is not None else None,
            "unrealized_pnl_pct": round(unrealized_pnl_pct, 2) if unrealized_pnl_pct is not None else None,
            "day_change_pct": round(day_change_pct, 2) if day_change_pct is not None else None,
            "weight_pct": None,
            "price_source": yf_symbol,
            "yf_symbol_override": h.yf_symbol_override,
        })
    for row in rows:
        cv = row["current_value"] or row["total_cost"]
        row["weight_pct"] = round((cv / total_current) * 100, 2) if total_current > 0 else 0.0

    realized_total = (
        db.query(sa_func.sum(PortfolioTransaction.realized_pnl))
        .filter(PortfolioTransaction.portfolio_id == portfolio_id, PortfolioTransaction.txn_type == TransactionType.SELL)
        .scalar()
    ) or 0.0

    prices_as_of = max(market_times) if market_times else None

    totals = {
        "total_invested": round(total_invested, 2), "current_value": round(total_current, 2),
        "unrealized_pnl": round(total_current - total_invested, 2),
        "unrealized_pnl_pct": round(((total_current - total_invested) / total_invested) * 100, 2) if total_invested > 0 else 0.0,
        "realized_pnl": round(realized_total, 2), "num_holdings": len(rows),
    }
    return {"success": True, "holdings": rows, "totals": totals, "prices_as_of": prices_as_of}


# ─── Symbol Override ────────────────────────────────────

class UpdateSymbolRequest(BaseModel):
    yf_symbol: Optional[str] = None


@router.put("/api/portfolios/{portfolio_id}/holdings/{holding_id}/symbol")
async def update_holding_symbol(
    portfolio_id: int, holding_id: int, req: UpdateSymbolRequest, db: Session = Depends(get_db)
):
    """Set or clear the Yahoo Finance symbol override for a holding."""
    holding = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.id == holding_id, PortfolioHolding.portfolio_id == portfolio_id)
        .first()
    )
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")

    holding.yf_symbol_override = req.yf_symbol.strip() if req.yf_symbol else None
    db.commit()
    return {
        "success": True,
        "holding_id": holding.id,
        "ticker": holding.ticker,
        "yf_symbol_override": holding.yf_symbol_override,
    }


# ─── NAV Computation ────────────────────────────────────

@router.post("/api/portfolios/{portfolio_id}/compute-nav")
async def compute_nav(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = db.query(ModelPortfolio).filter(ModelPortfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    today_str = date_type.today().strftime("%Y-%m-%d")
    nav = compute_nav_for_portfolio(portfolio_id, today_str, db)
    if nav:
        return {"success": True, "date": today_str, "total_value": nav.total_value,
                "total_cost": nav.total_cost, "unrealized_pnl": nav.unrealized_pnl}
    return {"success": True, "message": "No holdings to compute NAV for"}


@router.post("/api/portfolios/compute-nav")
async def compute_nav_all(db: Session = Depends(get_db)):
    portfolios = db.query(ModelPortfolio).filter(ModelPortfolio.status == PortfolioStatus.ACTIVE).all()
    today_str = date_type.today().strftime("%Y-%m-%d")
    computed = 0
    for p in portfolios:
        nav = compute_nav_for_portfolio(p.id, today_str, db)
        if nav:
            computed += 1
    return {"success": True, "computed": computed, "date": today_str}


# ─── NAV History (for Charts) ───────────────────────────

_PERIOD_DAYS = {"1m": 30, "3m": 90, "6m": 180, "1y": 365, "ytd": None, "all": None}


@router.get("/api/portfolios/{portfolio_id}/nav-history")
async def get_nav_history(portfolio_id: int, period: str = "all", db: Session = Depends(get_db)):
    portfolio = db.query(ModelPortfolio).filter(ModelPortfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    query = db.query(PortfolioNAV).filter(PortfolioNAV.portfolio_id == portfolio_id)
    pk = period.lower()
    if pk == "ytd":
        query = query.filter(PortfolioNAV.date >= f"{date_type.today().year}-01-01")
    elif pk in _PERIOD_DAYS and _PERIOD_DAYS[pk] is not None:
        cutoff = (date_type.today() - timedelta(days=_PERIOD_DAYS[pk])).strftime("%Y-%m-%d")
        query = query.filter(PortfolioNAV.date >= cutoff)

    nav_rows = query.order_by(PortfolioNAV.date).all()

    benchmark_data = {}
    if nav_rows and portfolio.benchmark:
        dates = [n.date for n in nav_rows]
        if dates:
            bench_rows = (
                db.query(IndexPrice)
                .filter(
                    IndexPrice.index_name == portfolio.benchmark,
                    IndexPrice.date >= dates[0],
                    IndexPrice.date <= dates[-1],
                )
                .order_by(IndexPrice.date).all()
            )
            for br in bench_rows:
                benchmark_data[br.date] = br.close_price

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
            "date": n.date, "total_value": n.total_value, "total_cost": n.total_cost,
            "unrealized_pnl": n.unrealized_pnl, "benchmark_value": benchmark_normalized,
        })
    return {"success": True, "nav_history": result, "period": period}


# ─── Performance Metrics ────────────────────────────────

@router.get("/api/portfolios/{portfolio_id}/performance")
async def get_performance(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = db.query(ModelPortfolio).filter(ModelPortfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    holdings = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.portfolio_id == portfolio_id, PortfolioHolding.quantity > 0)
        .all()
    )
    total_invested = sum(h.total_cost for h in holdings)
    current_value = total_invested
    tickers = [h.ticker for h in holdings if h.ticker]
    if tickers:
        prices = get_live_prices(tickers)
        if prices:
            current_value = 0.0
            for h in holdings:
                cp = prices.get(h.ticker, {}).get("current_price")
                current_value += (h.quantity * cp) if cp else h.total_cost

    realized_pnl = (
        db.query(sa_func.sum(PortfolioTransaction.realized_pnl))
        .filter(PortfolioTransaction.portfolio_id == portfolio_id, PortfolioTransaction.txn_type == TransactionType.SELL)
        .scalar()
    ) or 0.0

    unrealized_pnl = current_value - total_invested
    total_return = unrealized_pnl + realized_pnl
    total_return_pct = (total_return / total_invested * 100) if total_invested > 0 else 0.0

    txns = (
        db.query(PortfolioTransaction).filter(PortfolioTransaction.portfolio_id == portfolio_id)
        .order_by(PortfolioTransaction.txn_date).all()
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
    if current_value > 0 and cashflows:
        cashflows.append((date_type.today(), current_value))
    xirr = compute_xirr(cashflows)

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

    nav_values = (
        db.query(PortfolioNAV.total_value).filter(PortfolioNAV.portfolio_id == portfolio_id)
        .order_by(PortfolioNAV.date).all()
    )
    max_drawdown = compute_max_drawdown([v[0] for v in nav_values]) if nav_values else None

    benchmark_return_pct = None
    alpha = None
    if portfolio.benchmark and txns:
        try:
            first_date_str = txns[0].txn_date
            today_str = date_type.today().strftime("%Y-%m-%d")
            bench_start = (
                db.query(IndexPrice)
                .filter(IndexPrice.index_name == portfolio.benchmark, IndexPrice.date >= first_date_str)
                .order_by(IndexPrice.date).first()
            )
            bench_end = (
                db.query(IndexPrice)
                .filter(IndexPrice.index_name == portfolio.benchmark, IndexPrice.date <= today_str)
                .order_by(desc(IndexPrice.date)).first()
            )
            if bench_start and bench_end and bench_start.close_price and bench_start.close_price > 0:
                benchmark_return_pct = round(((bench_end.close_price / bench_start.close_price) - 1) * 100, 2)
                alpha = round(total_return_pct - benchmark_return_pct, 2)
        except Exception:
            pass

    return {
        "success": True,
        "performance": {
            "total_invested": round(total_invested, 2), "current_value": round(current_value, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "unrealized_pnl_pct": round((unrealized_pnl / total_invested * 100), 2) if total_invested > 0 else 0.0,
            "realized_pnl": round(realized_pnl, 2), "total_return": round(total_return, 2),
            "total_return_pct": round(total_return_pct, 2), "xirr": xirr, "cagr": cagr,
            "max_drawdown": max_drawdown, "benchmark_return_pct": benchmark_return_pct, "alpha": alpha,
        },
    }


# ─── Allocation ─────────────────────────────────────────

@router.get("/api/portfolios/{portfolio_id}/allocation")
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

    tickers = [h.ticker for h in holdings]
    prices = get_live_prices(tickers)
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

    by_stock = [{"label": s["label"], "value": s["value"],
                 "pct": round((s["value"] / total_value) * 100, 2) if total_value > 0 else 0}
                for s in sorted(stock_items, key=lambda x: x["value"], reverse=True)]
    by_sector = [{"label": sector, "value": round(val, 2),
                  "pct": round((val / total_value) * 100, 2) if total_value > 0 else 0}
                 for sector, val in sorted(sector_map.items(), key=lambda x: x[1], reverse=True)]
    return {"success": True, "by_stock": by_stock, "by_sector": by_sector}


# ─── CSV Export ──────────────────────────────────────────

@router.get("/api/portfolios/{portfolio_id}/export/holdings")
async def export_holdings_csv(portfolio_id: int, db: Session = Depends(get_db)):
    holdings = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.portfolio_id == portfolio_id, PortfolioHolding.quantity > 0)
        .order_by(desc(PortfolioHolding.total_cost)).all()
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Ticker", "Exchange", "Sector", "Quantity", "Avg Cost", "Total Cost"])
    for h in holdings:
        writer.writerow([h.ticker, h.exchange, h.sector or "", h.quantity, h.avg_cost, h.total_cost])
    output.seek(0)
    return StreamingResponse(
        output, media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=holdings_portfolio_{portfolio_id}.csv"},
    )


@router.get("/api/portfolios/{portfolio_id}/export/transactions")
async def export_transactions_csv(portfolio_id: int, db: Session = Depends(get_db)):
    txns = (
        db.query(PortfolioTransaction).filter(PortfolioTransaction.portfolio_id == portfolio_id)
        .order_by(desc(PortfolioTransaction.txn_date)).all()
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Type", "Ticker", "Quantity", "Price", "Total Value", "Realized P&L", "Notes"])
    for t in txns:
        writer.writerow([t.txn_date, t.txn_type.value if t.txn_type else "", t.ticker,
                         t.quantity, t.price, t.total_value, t.realized_pnl or "", t.notes or ""])
    output.seek(0)
    return StreamingResponse(
        output, media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=transactions_portfolio_{portfolio_id}.csv"},
    )


# ─── Bulk Import ────────────────────────────────────────

@router.post("/api/portfolios/bulk-import")
async def bulk_import_portfolio(request: Request, db: Session = Depends(get_db)):
    """Bulk import portfolio data: portfolio + holdings + transactions + NAV + index prices."""
    data = await request.json()

    p_data = data.get("portfolio", {})
    p = ModelPortfolio(
        name=p_data["name"], description=p_data.get("description"),
        benchmark=p_data.get("benchmark", "NIFTY"),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    pid = p.id

    for h in data.get("holdings", []):
        db.add(PortfolioHolding(
            portfolio_id=pid, ticker=h["ticker"], exchange=h.get("exchange", "NSE"),
            quantity=h["quantity"], avg_cost=h["avg_cost"], total_cost=h["total_cost"],
            sector=h.get("sector"),
        ))

    for t in data.get("transactions", []):
        tt = TransactionType.BUY if t["txn_type"] == "BUY" else TransactionType.SELL
        db.add(PortfolioTransaction(
            portfolio_id=pid, ticker=t["ticker"], exchange=t.get("exchange", "NSE"),
            txn_type=tt, quantity=t["quantity"], price=t["price"],
            total_value=t["total_value"], txn_date=t["txn_date"], notes=t.get("notes"),
            realized_pnl=t.get("realized_pnl"), realized_pnl_pct=t.get("realized_pnl_pct"),
            cost_basis_at_sell=t.get("cost_basis_at_sell"),
        ))

    for n in data.get("nav_history", []):
        db.add(PortfolioNAV(
            portfolio_id=pid, date=n["date"], total_value=n["total_value"],
            total_cost=n["total_cost"], unrealized_pnl=n.get("unrealized_pnl"),
            realized_pnl_cumulative=n.get("realized_pnl_cumulative"),
            num_holdings=n.get("num_holdings"),
        ))

    db.commit()

    idx_inserted = 0
    for ip in data.get("index_prices", []):
        existing = db.query(IndexPrice).filter_by(date=ip["date"], index_name=ip["index_name"]).first()
        if not existing:
            db.add(IndexPrice(
                date=ip["date"], index_name=ip["index_name"],
                close_price=ip.get("close_price"), open_price=ip.get("open_price"),
                high_price=ip.get("high_price"), low_price=ip.get("low_price"),
                volume=ip.get("volume"),
            ))
            idx_inserted += 1
    db.commit()

    return {
        "success": True, "portfolio_id": pid,
        "holdings": len(data.get("holdings", [])),
        "transactions": len(data.get("transactions", [])),
        "nav_rows": len(data.get("nav_history", [])),
        "index_prices_inserted": idx_inserted,
    }
