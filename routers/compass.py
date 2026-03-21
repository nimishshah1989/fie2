"""
Sector Compass — API Router
Endpoints for sector RS scores, stock drill-down, ETFs, and model portfolio.
Completely independent from existing pulse/sentiment/recommendations routes.

Data is 100% real — fetched from yfinance + NSE API. No mock data.
RS scores are cached for 15 minutes, then recomputed from fresh prices.
"""

import logging
import time
import threading
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import get_db

logger = logging.getLogger("fie_v3.compass")

router = APIRouter(prefix="/api/compass", tags=["compass"])

# ─── 15-Minute Cache ──────────────────────────────────────
# RS computation is CPU-intensive (reads hundreds of price rows).
# Cache results for 15 min to avoid redundant computation on each request.
# Cache is keyed by (base, period). Refresh clears the cache.

_rs_cache: dict[str, dict] = {}
_rs_cache_lock = threading.Lock()
CACHE_TTL_SECONDS = 900  # 15 minutes


def _cache_key(prefix: str, base: str, period: str) -> str:
    return f"{prefix}:{base}:{period}"


def _get_cached(key: str) -> Optional[list]:
    with _rs_cache_lock:
        entry = _rs_cache.get(key)
        if entry and (time.time() - entry["ts"]) < CACHE_TTL_SECONDS:
            return entry["data"]
    return None


def _set_cached(key: str, data: list) -> None:
    with _rs_cache_lock:
        _rs_cache[key] = {"data": data, "ts": time.time()}


def _clear_cache() -> None:
    with _rs_cache_lock:
        _rs_cache.clear()


# ─── Response Models ──────────────────────────────────────

class SectorRSResponse(BaseModel):
    sector_key: str
    display_name: str
    rs_score: float
    rs_momentum: float
    relative_return: float
    volume_signal: Optional[str] = None
    quadrant: str
    action: str
    etfs: list[str] = []
    category: str = ""
    pe_ratio: Optional[float] = None
    last_updated: Optional[str] = None


class StockRSResponse(BaseModel):
    ticker: str
    company_name: str
    rs_score: float
    rs_momentum: float
    relative_return: float
    volume_signal: Optional[str] = None
    quadrant: str
    action: str
    weight_pct: Optional[float] = None
    stop_loss_pct: Optional[float] = None
    pe_ratio: Optional[float] = None


class ETFRSResponse(BaseModel):
    ticker: str
    parent_sector: Optional[str] = None
    sector_name: Optional[str] = None
    rs_score: float
    rs_momentum: float
    relative_return: float
    volume_signal: Optional[str] = None
    quadrant: str
    action: str


class PositionResponse(BaseModel):
    sector_key: str
    sector_name: str
    instrument_id: str
    instrument_type: str
    entry_date: str
    entry_price: float
    current_price: Optional[float] = None
    weight_pct: Optional[float] = None
    stop_loss: Optional[float] = None
    trailing_stop: Optional[float] = None
    pnl_pct: Optional[float] = None
    status: str


class TradeResponse(BaseModel):
    trade_date: str
    sector_key: str
    sector_name: str
    instrument_id: str
    instrument_type: str
    side: str
    price: float
    value: Optional[float] = None
    reason: Optional[str] = None
    quadrant: Optional[str] = None
    rs_score: Optional[float] = None


class NAVResponse(BaseModel):
    date: str
    nav: float
    benchmark_nav: Optional[float] = None
    fm_nav: Optional[float] = None
    cash_pct: Optional[float] = None
    num_positions: Optional[int] = None


# ─── Endpoints ────────────────────────────────────────────

@router.get("/sectors", response_model=list[SectorRSResponse])
def get_sector_scores(
    base: str = Query("NIFTY", description="Benchmark index"),
    period: str = Query("3M", description="Period: 1M, 3M, 6M, 12M"),
    db: Session = Depends(get_db),
):
    """Get RS scores for all sector indices. Cached 15 min, then recomputed from real prices."""
    from datetime import datetime
    from services.compass_rs import compute_sector_rs_scores

    if period not in ("1M", "3M", "6M", "12M"):
        raise HTTPException(400, "Invalid period. Use 1M, 3M, 6M, or 12M")

    key = _cache_key("sectors", base, period)
    cached = _get_cached(key)
    if cached is not None:
        return cached

    scores = compute_sector_rs_scores(db, base_index=base, period_key=period)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for s in scores:
        s["last_updated"] = now
    _set_cached(key, scores)
    return scores


@router.get("/sectors/{sector_key}/stocks", response_model=list[StockRSResponse])
def get_sector_stock_scores(
    sector_key: str,
    base: str = Query("NIFTY", description="Benchmark index"),
    period: str = Query("3M", description="Period: 1M, 3M, 6M, 12M"),
    db: Session = Depends(get_db),
):
    """Get RS scores for all stocks within a sector. Cached 15 min."""
    from services.compass_rs import compute_stock_rs_scores

    if period not in ("1M", "3M", "6M", "12M"):
        raise HTTPException(400, "Invalid period. Use 1M, 3M, 6M, or 12M")

    key = _cache_key(f"stocks:{sector_key}", base, period)
    cached = _get_cached(key)
    if cached is not None:
        return cached

    scores = compute_stock_rs_scores(db, sector_key=sector_key, base_index=base, period_key=period)
    if not scores:
        raise HTTPException(404, f"No data for sector {sector_key}")
    _set_cached(key, scores)
    return scores


@router.get("/etfs", response_model=list[ETFRSResponse])
def get_etf_scores(
    base: str = Query("NIFTY", description="Benchmark index"),
    period: str = Query("3M", description="Period: 1M, 3M, 6M, 12M"),
    db: Session = Depends(get_db),
):
    """Get RS scores for all sector ETFs. Cached 15 min."""
    from services.compass_rs import compute_etf_rs_scores

    if period not in ("1M", "3M", "6M", "12M"):
        raise HTTPException(400, "Invalid period. Use 1M, 3M, 6M, or 12M")

    key = _cache_key("etfs", base, period)
    cached = _get_cached(key)
    if cached is not None:
        return cached

    scores = compute_etf_rs_scores(db, base_index=base, period_key=period)
    _set_cached(key, scores)
    return scores


@router.get("/model-portfolio")
def get_model_portfolio(
    portfolio_type: str = Query("etf_only", description="etf_only, stock_etf, or stock_only"),
    db: Session = Depends(get_db),
):
    """Get current model portfolio positions and state."""
    from services.compass_portfolio import PORTFOLIO_TYPES, get_model_portfolio_state

    if portfolio_type not in PORTFOLIO_TYPES:
        raise HTTPException(400, f"Invalid portfolio_type. Use: {', '.join(PORTFOLIO_TYPES)}")
    return get_model_portfolio_state(db, portfolio_type=portfolio_type)


@router.get("/model-portfolio/trades")
def get_model_trades(
    portfolio_type: str = Query("etf_only"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Get model portfolio trade history."""
    from services.compass_portfolio import get_trade_history
    return get_trade_history(db, portfolio_type=portfolio_type, limit=limit)


@router.get("/model-portfolio/nav")
def get_model_nav(
    portfolio_type: str = Query("etf_only"),
    days: int = Query(365, ge=7, le=730),
    db: Session = Depends(get_db),
):
    """Get model portfolio NAV history."""
    from services.compass_portfolio import get_nav_history
    return get_nav_history(db, portfolio_type=portfolio_type, days=days)


@router.get("/model-portfolio/performance")
def get_model_performance(
    portfolio_type: str = Query("etf_only"),
    db: Session = Depends(get_db),
):
    """Get model portfolio performance metrics."""
    from services.compass_portfolio import get_performance_metrics
    return get_performance_metrics(db, portfolio_type=portfolio_type)


@router.post("/refresh")
def refresh_compass(db: Session = Depends(get_db)):
    """Force recompute RS scores and run model portfolio rebalance. Clears cache."""
    from services.compass_rs import compute_sector_rs_scores, persist_rs_scores
    from services.compass_portfolio import run_weekly_rebalance, update_model_nav

    # Clear all cached data — force fresh computation
    _clear_cache()

    # Compute sector RS
    sector_scores = compute_sector_rs_scores(db, base_index="NIFTY", period_key="3M")
    persist_rs_scores(db, sector_scores, instrument_type="index")

    # Run model portfolio rebalance
    rebalance = run_weekly_rebalance(db, sector_scores)

    # Update NAV
    nav = update_model_nav(db)

    return {
        "sectors_computed": len(sector_scores),
        "rebalance": rebalance,
        "nav": nav,
    }


@router.get("/history/{instrument_id}")
def get_rs_history(
    instrument_id: str,
    instrument_type: str = Query("index", description="index, etf, or stock"),
    days: int = Query(60, ge=7, le=365),
    db: Session = Depends(get_db),
):
    """Get RS score time-series for an instrument (for trailing dots on chart)."""
    from datetime import datetime, timedelta
    from models import CompassRSScore

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = (
        db.query(CompassRSScore)
        .filter(
            CompassRSScore.instrument_id == instrument_id,
            CompassRSScore.instrument_type == instrument_type,
            CompassRSScore.date >= cutoff,
        )
        .order_by(CompassRSScore.date)
        .all()
    )
    return [
        {
            "date": r.date,
            "rs_score": r.rs_score,
            "rs_momentum": r.rs_momentum,
            "quadrant": r.quadrant.value if r.quadrant else None,
            "action": r.action.value if r.action else None,
        }
        for r in rows
    ]
