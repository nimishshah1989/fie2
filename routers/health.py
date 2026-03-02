"""
FIE v3 — Health & Status Routes
Server status, health checks, and basic market summary.
"""

import os
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from models import (
    get_db, TradingViewAlert, ModelPortfolio, PortfolioHolding, PortfolioNAV,
)

logger = logging.getLogger("fie_v3.health")
router = APIRouter()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


@router.get("/api/status")
async def server_status():
    return {
        "analysis_enabled": bool(ANTHROPIC_API_KEY),
        "version": "3.0",
    }


@router.get("/health")
async def health(db: Session = Depends(get_db)):
    """Health check with DB connectivity and row counts."""
    from models import DATABASE_URL
    db_type = "postgresql" if "postgresql" in DATABASE_URL else "sqlite"
    try:
        alert_count = db.query(sa_func.count(TradingViewAlert.id)).scalar() or 0
        portfolio_count = db.query(sa_func.count(ModelPortfolio.id)).scalar() or 0
        holding_count = db.query(sa_func.count(PortfolioHolding.id)).scalar() or 0
        nav_count = db.query(sa_func.count(PortfolioNAV.id)).scalar() or 0
    except Exception as exc:
        return {"status": "error", "version": "3.0", "db_type": db_type, "error": str(exc)}
    return {
        "status": "ok",
        "version": "3.0",
        "db_type": db_type,
        "counts": {
            "alerts": alert_count,
            "portfolios": portfolio_count,
            "holdings": holding_count,
            "nav_rows": nav_count,
        },
    }


@router.get("/api")
async def root():
    return {"service": "JHAVERI FIE v3", "status": "running"}


@router.get("/api/market/indices")
async def market_indices():
    """Quick summary of key market indices."""
    from price_service import get_live_price
    indices = ["NIFTY", "SENSEX", "BANKNIFTY", "NIFTYIT", "NIFTYPHARMA", "NIFTYFMCG"]
    results = {}
    for idx in indices:
        try:
            data = get_live_price(idx)
            results[idx] = data
        except Exception:
            results[idx] = {"current_price": None}
    return results
