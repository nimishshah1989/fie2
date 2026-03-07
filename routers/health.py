"""
FIE v3 — Health & Status Routes
Server status, health checks, and basic market summary.
"""

import logging
import os
import sys
import time
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func as sa_func
from sqlalchemy import text
from sqlalchemy.orm import Session

from models import (
    IndexPrice,
    ModelPortfolio,
    PortfolioHolding,
    PortfolioNAV,
    TradingViewAlert,
    get_db,
)

logger = logging.getLogger("fie_v3.health")
router = APIRouter()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Track server start time for uptime reporting
_SERVER_START_TIME = datetime.utcnow()


@router.get(
    "/api/status",
    tags=["Health"],
    summary="Server status",
    description="Returns server version and feature flags (e.g. whether Claude analysis is enabled).",
)
async def server_status():
    return {
        "analysis_enabled": bool(ANTHROPIC_API_KEY),
        "version": "3.1",
    }


@router.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description="Returns system health including DB connectivity, data freshness, row counts, and uptime.",
)
async def health(db: Session = Depends(get_db)):
    """Health check with DB connectivity, data freshness, and system info."""
    from models import DATABASE_URL

    environment = os.getenv("FIE_ENVIRONMENT", "production")
    db_type = "postgresql" if "postgresql" in DATABASE_URL else "sqlite"

    # ── Database connectivity + latency ──────────────────
    db_status = "connected"
    db_latency_ms = 0.0
    try:
        db_start = time.perf_counter()
        db.execute(text("SELECT 1"))
        db_latency_ms = round((time.perf_counter() - db_start) * 1000, 2)
    except Exception as exc:
        db_status = "error"
        logger.error("Health check DB connectivity failed: %s", exc)
        return {
            "status": "degraded",
            "version": "3.1",
            "environment": environment,
            "db": {"status": "error", "error": str(exc), "type": db_type},
        }

    # ── Row counts ───────────────────────────────────────
    try:
        alert_count = db.query(sa_func.count(TradingViewAlert.id)).scalar() or 0
        portfolio_count = db.query(sa_func.count(ModelPortfolio.id)).scalar() or 0
        holding_count = db.query(sa_func.count(PortfolioHolding.id)).scalar() or 0
        nav_count = db.query(sa_func.count(PortfolioNAV.id)).scalar() or 0
    except Exception as exc:
        return {
            "status": "degraded",
            "version": "3.1",
            "environment": environment,
            "db": {"status": db_status, "latency_ms": db_latency_ms, "type": db_type},
            "error": str(exc),
        }

    # ── Data freshness — latest IndexPrice record ────────
    latest_price_date = None
    hours_since_update = None
    try:
        latest_row = (
            db.query(IndexPrice.date, IndexPrice.fetched_at)
            .order_by(IndexPrice.fetched_at.desc())
            .first()
        )
        if latest_row:
            latest_price_date = latest_row.date
            if latest_row.fetched_at:
                delta = datetime.utcnow() - latest_row.fetched_at
                hours_since_update = round(delta.total_seconds() / 3600, 1)
    except Exception as exc:
        logger.warning("Health check data freshness query failed: %s", exc)

    # ── System info ──────────────────────────────────────
    uptime_seconds = round((datetime.utcnow() - _SERVER_START_TIME).total_seconds())
    uptime_hours = round(uptime_seconds / 3600, 1)

    return {
        "status": "ok",
        "version": "3.1",
        "environment": environment,
        "db": {
            "status": db_status,
            "latency_ms": db_latency_ms,
            "type": db_type,
        },
        "data_freshness": {
            "latest_price_date": latest_price_date,
            "hours_since_update": hours_since_update,
        },
        "counts": {
            "alerts": alert_count,
            "portfolios": portfolio_count,
            "holdings": holding_count,
            "nav_rows": nav_count,
        },
        "system": {
            "python_version": sys.version.split()[0],
            "uptime_hours": uptime_hours,
            "uptime_seconds": uptime_seconds,
        },
    }


@router.get(
    "/api",
    tags=["Health"],
    summary="API root",
    description="Returns service name and running status. Useful as a quick ping.",
)
async def root():
    return {"service": "JHAVERI FIE v3", "status": "running"}


@router.get(
    "/api/market/indices",
    tags=["Health"],
    summary="Quick market indices summary",
    description="Returns live prices for key market indices (NIFTY, SENSEX, BANKNIFTY, NIFTYIT, NIFTYPHARMA, NIFTYFMCG).",
)
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
