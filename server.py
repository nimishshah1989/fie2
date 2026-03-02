"""
FIE v3 — FastAPI Server (Orchestrator)
Jhaveri Intelligence Platform

Slim orchestrator: app setup, middleware, router mounting,
background backfill, scheduled jobs, and static file serving.
All endpoint logic lives in routers/ and services/.
"""

import os
import logging
import threading
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import desc

from models import (
    init_db, SessionLocal,
    TradingViewAlert, AlertStatus, IndexPrice,
)
from services.data_helpers import upsert_price_row, get_all_portfolio_tickers_with_inception

# ─── Routers ─────────────────────────────────────────────
from routers import health, alerts, indices, portfolios

logger = logging.getLogger("fie_v3")
logging.basicConfig(level=logging.INFO)


# ═══════════════════════════════════════════════════════════
#  APP SETUP
# ═══════════════════════════════════════════════════════════

app = FastAPI(title="JHAVERI FIE v3", version="3.1")

# ─── CORS ─────────────────────────────────────────────────
# Restrict to known frontends; add more origins as needed
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
] or [
    "http://localhost:3000",
    "http://localhost:8000",
    "https://fie2-production.up.railway.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Optional API Key Auth ────────────────────────────────
# Set FIE_API_KEY env var to enable. Webhook is always open for TradingView.
FIE_API_KEY = os.getenv("FIE_API_KEY", "")

# Paths that don't require auth (webhook, health, static assets)
_PUBLIC_PATHS = {"/webhook/tradingview", "/webhook/tradingview/", "/health", "/api", "/api/status"}


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    if not FIE_API_KEY:
        return await call_next(request)

    path = request.url.path

    # Allow public paths, static assets, and non-API paths
    if path in _PUBLIC_PATHS or not path.startswith("/api") or path.startswith("/_next"):
        return await call_next(request)

    # Check API key in header or query param
    key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
    if key != FIE_API_KEY:
        return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})

    return await call_next(request)


# ─── Mount Routers ────────────────────────────────────────
app.include_router(health.router)
app.include_router(alerts.router)
app.include_router(indices.router)
app.include_router(portfolios.router)


# ═══════════════════════════════════════════════════════════
#  BACKGROUND BACKFILL
# ═══════════════════════════════════════════════════════════

def _background_yfinance_backfill():
    """Background thread: fetch actual daily history via yfinance for indices, ETFs, and portfolio instruments."""
    logger.info("Background yfinance backfill starting (thread: %s)...", threading.current_thread().name)
    try:
        from price_service import (
            fetch_yfinance_bulk_history, fetch_yfinance_bulk_stock_history,
            NSE_INDEX_KEYS, NSE_ETF_UNIVERSE,
        )
        db = SessionLocal()

        # 1. Indices — 1Y history via yfinance (27 tracked)
        logger.info("Backfill: fetching 1Y history for %d indices...", len(NSE_INDEX_KEYS))
        idx_data = fetch_yfinance_bulk_history(NSE_INDEX_KEYS, period="1y")
        idx_stored = 0
        for idx_name, rows in idx_data.items():
            for row in rows:
                if upsert_price_row(db, idx_name, row):
                    idx_stored += 1
        db.commit()
        logger.info("Backfill: stored %d index records across %d indices", idx_stored, len(idx_data))

        # 2. ETFs — 1Y history via yfinance (17 tracked)
        etf_tickers = list(NSE_ETF_UNIVERSE.keys())
        logger.info("Backfill: fetching 1Y history for %d ETFs...", len(etf_tickers))
        etf_data = fetch_yfinance_bulk_stock_history(etf_tickers, period="1y")
        etf_stored = 0
        for ticker, rows in etf_data.items():
            for row in rows:
                if upsert_price_row(db, ticker, row):
                    etf_stored += 1
        db.commit()
        logger.info("Backfill: stored %d ETF records across %d ETFs", etf_stored, len(etf_data))

        # 3. Portfolio instruments (stocks + ETFs) — from inception date via yfinance
        ticker_inception = get_all_portfolio_tickers_with_inception(db)
        if ticker_inception:
            earliest_start = min(ticker_inception.values())
            all_portfolio_tickers = list(ticker_inception.keys())
            logger.info("Backfill: fetching history from %s for %d portfolio instruments...",
                        earliest_start, len(all_portfolio_tickers))
            portfolio_data = fetch_yfinance_bulk_stock_history(
                all_portfolio_tickers, start=earliest_start,
            )
            ptf_stored = 0
            for ticker, rows in portfolio_data.items():
                for row in rows:
                    if upsert_price_row(db, ticker, row):
                        ptf_stored += 1
            db.commit()
            logger.info("Backfill: stored %d portfolio instrument records across %d tickers",
                        ptf_stored, len(portfolio_data))
        else:
            logger.info("Backfill: no portfolio instruments to fetch")

        # 4. Alert tickers — 1Y history (deduplicated against portfolio instruments)
        alert_tickers = [
            r[0] for r in db.query(TradingViewAlert.ticker)
            .filter(TradingViewAlert.status == AlertStatus.APPROVED)
            .distinct().all()
            if r[0] and r[0] != "UNKNOWN"
        ]
        covered = set(t.upper() for t in ticker_inception.keys()) if ticker_inception else set()
        covered.update(t.upper() for t in etf_tickers)
        new_alert_tickers = [t for t in alert_tickers if t.upper() not in covered]
        if new_alert_tickers:
            logger.info("Backfill: fetching 1Y history for %d alert tickers...", len(new_alert_tickers))
            alert_data = fetch_yfinance_bulk_stock_history(new_alert_tickers, period="1y")
            alert_stored = 0
            for ticker, rows in alert_data.items():
                for row in rows:
                    if upsert_price_row(db, ticker, row):
                        alert_stored += 1
            db.commit()
            logger.info("Backfill: stored %d alert records across %d tickers",
                        alert_stored, len(alert_data))

        db.close()
        logger.info("Background yfinance backfill complete")
    except Exception as e:
        logger.warning("Background yfinance backfill failed (non-fatal): %s", e)


# ═══════════════════════════════════════════════════════════
#  SCHEDULED EOD JOB
# ═══════════════════════════════════════════════════════════

def _scheduled_eod_fetch():
    """Background job: store ALL nsetools indices + ETFs + portfolio stocks daily."""
    from price_service import (
        fetch_live_indices, fetch_yfinance_bulk_history,
        fetch_yfinance_bulk_stock_history,
        NSE_ETF_UNIVERSE, NSE_INDEX_KEYS,
    )
    from services.data_helpers import get_portfolio_tickers

    logger.info("Scheduled EOD fetch starting...")
    db = SessionLocal()
    try:
        today_str = datetime.now().strftime("%Y-%m-%d")

        # 1. Store ALL live nsetools indices (135+)
        live = fetch_live_indices()
        nsetools_names = set()
        idx_stored = 0
        for item in live:
            close = item.get("last")
            if not close:
                continue
            nsetools_names.add(item["index_name"])
            existing = db.query(IndexPrice).filter_by(
                date=today_str, index_name=item["index_name"]
            ).first()
            if existing:
                existing.close_price = close
                existing.open_price = item.get("open")
                existing.high_price = item.get("high")
                existing.low_price = item.get("low")
                existing.fetched_at = datetime.now()
            else:
                db.add(IndexPrice(
                    date=today_str, index_name=item["index_name"],
                    close_price=close, open_price=item.get("open"),
                    high_price=item.get("high"), low_price=item.get("low"),
                ))
            idx_stored += 1

        # 1b. yfinance fallback for tracked indices not covered by nsetools
        missed_keys = [k for k in NSE_INDEX_KEYS if k not in nsetools_names]
        yf_idx_stored = 0
        if missed_keys:
            yf_idx_data = fetch_yfinance_bulk_history(missed_keys, period="5d")
            for idx_name, rows in yf_idx_data.items():
                for row in rows:
                    if upsert_price_row(db, idx_name, row):
                        yf_idx_stored += 1

        # 2. Fetch recent ETF prices via yfinance
        etf_tickers = list(NSE_ETF_UNIVERSE.keys())
        etf_data = fetch_yfinance_bulk_stock_history(etf_tickers, period="5d")
        etf_stored = 0
        for ticker, rows in etf_data.items():
            for row in rows:
                if upsert_price_row(db, ticker, row):
                    etf_stored += 1

        # 3. Fetch recent portfolio stock prices via yfinance
        stock_tickers = get_portfolio_tickers(db)
        stk_stored = 0
        if stock_tickers:
            stock_data = fetch_yfinance_bulk_stock_history(stock_tickers, period="5d")
            for ticker, rows in stock_data.items():
                for row in rows:
                    if upsert_price_row(db, ticker, row):
                        stk_stored += 1

        # 4. Also fetch alerted stocks (deduplicated against portfolio + ETFs)
        alert_tickers = [
            r[0] for r in db.query(TradingViewAlert.ticker)
            .filter(TradingViewAlert.status == AlertStatus.APPROVED)
            .distinct().all()
            if r[0] and r[0] != "UNKNOWN"
        ]
        covered = set(t.upper() for t in stock_tickers)
        covered.update(t.upper() for t in etf_tickers)
        new_alert_tickers = [t for t in alert_tickers if t.upper() not in covered]
        alert_stored = 0
        if new_alert_tickers:
            alert_data = fetch_yfinance_bulk_stock_history(new_alert_tickers, period="5d")
            for ticker, rows in alert_data.items():
                for row in rows:
                    if upsert_price_row(db, ticker, row):
                        alert_stored += 1

        db.commit()
        logger.info(
            "Scheduled EOD: %d nsetools + %d yf-fallback index, %d ETF, %d stock, %d alert records",
            idx_stored, yf_idx_stored, etf_stored, stk_stored, alert_stored,
        )
    except Exception as e:
        logger.error("Scheduled EOD fetch failed: %s", e)
        db.rollback()
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
#  STARTUP & SCHEDULER
# ═══════════════════════════════════════════════════════════

@app.on_event("startup")
async def startup():
    init_db()
    bg_thread = threading.Thread(target=_background_yfinance_backfill, daemon=True, name="yfinance-backfill")
    bg_thread.start()
    logger.info("Startup complete — yfinance backfill running in background")


@app.on_event("startup")
async def start_scheduler():
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        import pytz

        scheduler = BackgroundScheduler()
        ist = pytz.timezone("Asia/Kolkata")
        scheduler.add_job(
            _scheduled_eod_fetch,
            CronTrigger(hour=15, minute=30, timezone=ist),
            id="daily_eod_fetch",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("APScheduler started — daily EOD fetch at 3:30 PM IST")
    except Exception as e:
        logger.warning("APScheduler not available: %s (install apscheduler)", e)


# ═══════════════════════════════════════════════════════════
#  STATIC FRONTEND (Next.js export)
# ═══════════════════════════════════════════════════════════

_frontend_dir = Path(__file__).parent / "web" / "out"
if _frontend_dir.is_dir():
    for _page in ("pulse", "approved", "trade", "performance", "portfolios", "actionables", "docs"):
        _html = _frontend_dir / f"{_page}.html"
        if _html.is_file():
            def _make_page_handler(path: Path):
                async def _handler():
                    return FileResponse(path, media_type="text/html")
                return _handler
            app.add_api_route(f"/{_page}", _make_page_handler(_html), methods=["GET", "HEAD"])

    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
