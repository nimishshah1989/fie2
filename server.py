"""
FIE v3 — FastAPI Server (Orchestrator)
Jhaveri Intelligence Platform

Slim orchestrator: app setup, middleware, router mounting,
background backfill, scheduled jobs, and static file serving.
All endpoint logic lives in routers/ and services/.
"""

import logging
import os
import threading
from datetime import datetime
from pathlib import Path

from middleware.logging import setup_logging

# ─── Structured Logging ──────────────────────────────────
# Must be configured before any logger is used
_fie_environment = os.getenv("FIE_ENVIRONMENT", "production")
setup_logging(_fie_environment)
logger = logging.getLogger("fie_v3")

# ─── Sentry Error Tracking ──────────────────────────────
import sentry_sdk

_sentry_dsn = os.getenv("SENTRY_DSN", "")
if _sentry_dsn:
    sentry_sdk.init(
        dsn=_sentry_dsn,
        environment=os.getenv("FIE_ENVIRONMENT", "production"),
        traces_sample_rate=0.1,  # 10% of requests for performance monitoring
        profiles_sample_rate=0.1,
        send_default_pii=False,  # Don't send PII (financial data protection)
    )
    logger.info("Sentry initialized for environment: %s", os.getenv("FIE_ENVIRONMENT", "production"))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from middleware.security import (
    RequestLoggingMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from models import (
    AlertStatus,
    IndexConstituent,
    IndexPrice,
    SessionLocal,
    TradingViewAlert,
    init_db,
)

# ─── Routers ─────────────────────────────────────────────
from routers import alerts, baskets, health, indices, pms, portfolios, recommendations, sentiment, simulator
from services.data_helpers import get_all_portfolio_tickers_with_inception, upsert_price_row

# ═══════════════════════════════════════════════════════════
#  APP SETUP
# ═══════════════════════════════════════════════════════════

app = FastAPI(
    title="JHAVERI FIE v3",
    version="3.1",
    description="Jhaveri Intelligence Platform — Indian market intelligence, portfolio tracking, and trading alert management API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ─── Environment Validation ─────────────────────────────
_env = os.getenv("FIE_ENVIRONMENT", "production")
logger.info("FIE v3 starting in %s mode", _env)
if _env == "production" and not os.getenv("FIE_API_KEY", ""):
    logger.warning("PRODUCTION mode without FIE_API_KEY — API endpoints are unprotected")

# ─── Rate Limiting ───────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─── Request Logging Middleware ──────────────────────────
app.add_middleware(RequestLoggingMiddleware)

# ─── Security Middleware ─────────────────────────────────
app.add_middleware(RequestSizeLimitMiddleware, max_size=10 * 1024 * 1024)  # 10MB
app.add_middleware(SecurityHeadersMiddleware)

# ─── CORS ─────────────────────────────────────────────────
# Restrict to known frontends; add more origins as needed
# Added AFTER security middleware so CORS runs first (LIFO order)
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
] or [
    "http://localhost:3000",
    "http://localhost:8000",
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
app.include_router(baskets.router)
app.include_router(recommendations.router)
app.include_router(pms.router)
app.include_router(sentiment.router)
app.include_router(simulator.router)


# ═══════════════════════════════════════════════════════════
#  BACKGROUND BACKFILL
# ═══════════════════════════════════════════════════════════

def _background_yfinance_backfill():
    """Background thread: fetch actual daily history via yfinance for indices, ETFs, and portfolio instruments."""
    logger.info("Background yfinance backfill starting (thread: %s)...", threading.current_thread().name)
    db = None
    try:
        from price_service import (
            NSE_ETF_UNIVERSE,
            NSE_INDEX_KEYS,
            fetch_yfinance_bulk_history,
            fetch_yfinance_bulk_stock_history,
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

        # 1b. NSE API historical backfill — direct from nseindia.com
        # Covers ALL 79 tracked indices including those without yfinance symbols
        # (Housing, Tourism, EV, Railways, Capital Markets, etc.)
        try:
            from price_service import fetch_historical_indices_nse_sync
            logger.info("Backfill: fetching 1Y history from NSE API for all tracked indices...")
            nse_hist = fetch_historical_indices_nse_sync()
            nse_stored = 0
            tracked = set(NSE_INDEX_KEYS)
            for idx_name, rows in nse_hist.items():
                if idx_name not in tracked:
                    continue  # skip untracked indices (may have long names exceeding DB column)
                for row in rows:
                    if upsert_price_row(db, idx_name, row):
                        nse_stored += 1
            db.commit()
            logger.info("Backfill: stored %d NSE API historical records across %d indices", nse_stored, len(nse_hist))
        except Exception as e:
            logger.warning("NSE API historical backfill failed (non-fatal): %s", e)

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
        # Include both APPROVED and PENDING so FM can review pending alerts with price context
        alert_tickers = [
            r[0] for r in db.query(TradingViewAlert.ticker)
            .filter(TradingViewAlert.status.in_([AlertStatus.APPROVED, AlertStatus.PENDING]))
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

        # 5. Microbasket constituent prices + NAV computation
        try:
            from models import BasketStatus, Microbasket
            from services.basket_service import (
                backfill_basket_nav,
                get_all_basket_constituent_tickers,
            )

            basket_tickers = get_all_basket_constituent_tickers(db)
            # Deduplicate against already-fetched tickers
            already_fetched = set(t.upper() for t in (ticker_inception or {}).keys())
            already_fetched.update(t.upper() for t in etf_tickers)
            already_fetched.update(t.upper() for t in new_alert_tickers)
            new_basket_tickers = [t for t in basket_tickers if t.upper() not in already_fetched]

            if new_basket_tickers:
                logger.info("Backfill: fetching 1Y history for %d basket constituent tickers...", len(new_basket_tickers))
                basket_data = fetch_yfinance_bulk_stock_history(new_basket_tickers, period="1y")
                bkt_stored = 0
                for ticker, rows in basket_data.items():
                    for row in rows:
                        if upsert_price_row(db, ticker, row):
                            bkt_stored += 1
                db.commit()
                logger.info("Backfill: stored %d basket constituent records", bkt_stored)

            # Compute NAV series for all active baskets
            active_baskets = db.query(Microbasket).filter(Microbasket.status == BasketStatus.ACTIVE).all()
            for basket in active_baskets:
                backfill_basket_nav(basket, db, days=365)
        except Exception as e:
            logger.warning("Basket backfill step failed (non-fatal): %s", e)

        # 6. Sector index constituents — refresh from NSE + fetch 1Y price history
        # This populates IndexConstituent AND backfills stock prices so the
        # recommendation engine can compute stock-vs-sector ratio returns.
        try:
            from routers.recommendations import refresh_sector_constituents
            constituent_count = refresh_sector_constituents(db)
            logger.info("Backfill: refreshed %d sector constituent records from NSE", constituent_count)

            # Fetch 1Y history for all constituent tickers (deduplicated)
            all_constituent_tickers = [
                r[0] for r in db.query(IndexConstituent.ticker).distinct().all() if r[0]
            ]
            already_fetched = set(t.upper() for t in (ticker_inception or {}).keys())
            already_fetched.update(t.upper() for t in etf_tickers)
            already_fetched.update(t.upper() for t in new_alert_tickers)
            new_constituent_tickers = [t for t in all_constituent_tickers if t.upper() not in already_fetched]

            if new_constituent_tickers:
                logger.info("Backfill: fetching 1Y history for %d sector constituent stocks...", len(new_constituent_tickers))
                constituent_data = fetch_yfinance_bulk_stock_history(new_constituent_tickers, period="1y")
                cst_stored = 0
                for ticker, rows in constituent_data.items():
                    for row in rows:
                        if upsert_price_row(db, ticker, row):
                            cst_stored += 1
                db.commit()
                logger.info("Backfill: stored %d sector constituent price records across %d tickers",
                            cst_stored, len(constituent_data))
        except Exception as e:
            logger.warning("Sector constituent backfill step failed (non-fatal): %s", e)

        # 7. Nifty 500 constituents — for Sentiment Indicators breadth computation
        # Fetches from NSE API (works on Mumbai EC2). Non-fatal if API is unavailable.
        try:
            from price_service import fetch_nse_index_constituents
            nifty500_items = fetch_nse_index_constituents("NIFTY 500")
            if nifty500_items:
                nifty500_stored = 0
                for item in nifty500_items:
                    symbol = item.get("symbol", "").strip()
                    if not symbol:
                        continue
                    existing = (
                        db.query(IndexConstituent)
                        .filter(
                            IndexConstituent.index_name == "NIFTY 500",
                            IndexConstituent.ticker == symbol,
                        )
                        .first()
                    )
                    if existing:
                        existing.last_price = item.get("last_price")
                        existing.fetched_at = datetime.now()
                    else:
                        db.add(IndexConstituent(
                            index_name="NIFTY 500",
                            ticker=symbol,
                            company_name=item.get("company_name"),
                            weight_pct=item.get("weight"),
                            last_price=item.get("last_price"),
                        ))
                    nifty500_stored += 1
                db.commit()
                logger.info("Backfill: stored/updated %d Nifty 500 constituent records", nifty500_stored)

                # Fetch 1Y price history for Nifty 500 stocks not already covered
                nifty500_tickers = [item["symbol"] for item in nifty500_items if item.get("symbol")]
                all_covered = set(t.upper() for t in all_constituent_tickers)
                all_covered.update(t.upper() for t in (ticker_inception or {}).keys())
                all_covered.update(t.upper() for t in etf_tickers)
                new_nifty500_tickers = [t for t in nifty500_tickers if t.upper() not in all_covered]
                if new_nifty500_tickers:
                    logger.info("Backfill: fetching 1Y history for %d Nifty 500 stocks...", len(new_nifty500_tickers))
                    n500_data = fetch_yfinance_bulk_stock_history(new_nifty500_tickers, period="1y")
                    n500_stored = 0
                    for ticker, rows in n500_data.items():
                        for row in rows:
                            if upsert_price_row(db, ticker, row):
                                n500_stored += 1
                    db.commit()
                    logger.info("Backfill: stored %d Nifty 500 stock price records", n500_stored)
            else:
                logger.info("Backfill: Nifty 500 constituent fetch returned 0 items (NSE API may be unavailable)")
        except Exception as e:
            logger.warning("Nifty 500 constituent backfill step failed (non-fatal): %s", e)

        # 8. Per-stock sentiment scoring
        try:
            from services.stock_sentiment import compute_and_store_stock_sentiment
            stock_count = compute_and_store_stock_sentiment(db)
            logger.info("Per-stock sentiment: computed for %d stocks", stock_count)
        except Exception as e:
            logger.warning("Per-stock sentiment failed (non-fatal): %s", e)

        # 9. Backfill sentiment history (20 weeks) — skips dates already computed
        try:
            from services.sentiment_engine import backfill_sentiment_history
            filled = backfill_sentiment_history(db, weeks=20)
            logger.info("Sentiment history backfill: %d new snapshots", filled)
        except Exception as e:
            logger.warning("Sentiment history backfill failed (non-fatal): %s", e)

        logger.info("Background yfinance backfill complete")
    except Exception as e:
        logger.warning("Background yfinance backfill failed (non-fatal): %s", e)
    finally:
        if db:
            db.close()


# ═══════════════════════════════════════════════════════════
#  SCHEDULED EOD JOB
# ═══════════════════════════════════════════════════════════

def _scheduled_eod_fetch():
    """Background job: store ALL nsetools indices + ETFs + portfolio stocks daily."""
    from price_service import (
        NSE_ETF_UNIVERSE,
        NSE_INDEX_KEYS,
        fetch_live_indices,
        fetch_yfinance_bulk_history,
        fetch_yfinance_bulk_stock_history,
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

        # 1c. NSE API historical — refresh recent history from NSE for all tracked indices
        nse_eod_stored = 0
        try:
            from price_service import fetch_historical_indices_nse_sync
            nse_eod = fetch_historical_indices_nse_sync()
            tracked = set(NSE_INDEX_KEYS)
            for idx_name, rows in nse_eod.items():
                if idx_name not in tracked:
                    continue
                for row in rows:
                    if upsert_price_row(db, idx_name, row):
                        nse_eod_stored += 1
            db.commit()
            logger.info("EOD: stored %d NSE API historical records", nse_eod_stored)
        except Exception as e:
            logger.warning("EOD NSE API historical refresh failed (non-fatal): %s", e)

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
        # Include both APPROVED and PENDING so FM can review pending alerts with price context
        alert_tickers = [
            r[0] for r in db.query(TradingViewAlert.ticker)
            .filter(TradingViewAlert.status.in_([AlertStatus.APPROVED, AlertStatus.PENDING]))
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

        # 5. Compute today's basket NAVs from constituent prices
        basket_nav_count = 0
        try:
            from services.basket_service import (
                compute_today_basket_navs,
                get_all_basket_constituent_tickers,
            )
            # Fetch basket constituent prices that aren't already covered
            basket_tickers = get_all_basket_constituent_tickers(db)
            covered.update(t.upper() for t in new_alert_tickers)
            new_basket_tickers = [t for t in basket_tickers if t.upper() not in covered]
            if new_basket_tickers:
                bkt_data = fetch_yfinance_bulk_stock_history(new_basket_tickers, period="5d")
                for ticker, rows in bkt_data.items():
                    for row in rows:
                        upsert_price_row(db, ticker, row)

            basket_nav_count = compute_today_basket_navs(db)
        except Exception as e:
            logger.warning("Basket EOD step failed (non-fatal): %s", e)

        # 6. Refresh sector index constituents for recommendation engine
        constituent_count = 0
        constituent_price_count = 0
        try:
            from routers.recommendations import refresh_sector_constituents
            constituent_count = refresh_sector_constituents(db)

            # Fetch recent prices for all constituent tickers so stock-vs-sector ratios work
            all_constituent_tickers = [
                r[0] for r in db.query(IndexConstituent.ticker).distinct().all() if r[0]
            ]
            new_constituent_tickers = [t for t in all_constituent_tickers if t.upper() not in covered]
            if new_constituent_tickers:
                cst_data = fetch_yfinance_bulk_stock_history(new_constituent_tickers, period="5d")
                for ticker, rows in cst_data.items():
                    for row in rows:
                        if upsert_price_row(db, ticker, row):
                            constituent_price_count += 1
        except Exception as e:
            logger.warning("Constituent refresh step failed (non-fatal): %s", e)

        # 7. Refresh Nifty 500 constituents + recent prices for Sentiment Indicators
        try:
            from price_service import fetch_nse_index_constituents
            nifty500_items = fetch_nse_index_constituents("NIFTY 500")
            if nifty500_items:
                for item in nifty500_items:
                    symbol = item.get("symbol", "").strip()
                    if not symbol:
                        continue
                    existing = (
                        db.query(IndexConstituent)
                        .filter(IndexConstituent.index_name == "NIFTY 500",
                                IndexConstituent.ticker == symbol)
                        .first()
                    )
                    if existing:
                        existing.last_price = item.get("last_price")
                        existing.fetched_at = datetime.now()
                    else:
                        db.add(IndexConstituent(
                            index_name="NIFTY 500", ticker=symbol,
                            company_name=item.get("company_name"),
                            weight_pct=item.get("weight"),
                            last_price=item.get("last_price"),
                        ))
                nifty500_tickers = [i["symbol"] for i in nifty500_items if i.get("symbol")]
                new_n500 = [t for t in nifty500_tickers if t.upper() not in covered]
                if new_n500:
                    n500_data = fetch_yfinance_bulk_stock_history(new_n500, period="5d")
                    for ticker, rows in n500_data.items():
                        for row in rows:
                            upsert_price_row(db, ticker, row)
        except Exception as e:
            logger.warning("Nifty 500 EOD constituent refresh failed (non-fatal): %s", e)

        db.commit()
        logger.info(
            "Scheduled EOD: %d nsetools + %d yf-fallback + %d nse-api index, %d ETF, %d stock, %d alert, %d basket NAV, %d constituent records",
            idx_stored, yf_idx_stored, nse_eod_stored, etf_stored, stk_stored, alert_stored, basket_nav_count, constituent_count,
        )

        # 8. Per-stock sentiment scoring (after all prices committed)
        try:
            from services.stock_sentiment import compute_and_store_stock_sentiment
            stock_count = compute_and_store_stock_sentiment(db)
            logger.info("Per-stock sentiment: computed for %d stocks", stock_count)
        except Exception as e:
            logger.warning("Per-stock sentiment failed (non-fatal): %s", e)

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
        import pytz
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        scheduler = BackgroundScheduler()
        ist = pytz.timezone("Asia/Kolkata")
        scheduler.add_job(
            _scheduled_eod_fetch,
            CronTrigger(hour=15, minute=30, timezone=ist),
            id="daily_eod_fetch",
            replace_existing=True,
        )
        # Sentiment refresh runs 5 min after EOD once prices are stored
        def _eod_sentiment_refresh():
            import asyncio

            from models import SessionLocal as _SL
            from routers.sentiment import refresh_sentiment as _refresh
            db = _SL()
            try:
                asyncio.run(_refresh(db))
            except Exception as _e:
                logger.warning("EOD sentiment refresh failed: %s", _e)
            finally:
                db.close()

        scheduler.add_job(
            _eod_sentiment_refresh,
            CronTrigger(hour=15, minute=35, timezone=ist),
            id="daily_sentiment_refresh",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("APScheduler started — daily EOD fetch at 3:30 PM IST, sentiment refresh at 3:35 PM IST")
    except Exception as e:
        logger.warning("APScheduler not available: %s (install apscheduler)", e)


# ═══════════════════════════════════════════════════════════
#  STATIC FRONTEND (Next.js export)
# ═══════════════════════════════════════════════════════════

_frontend_dir = Path(__file__).parent / "web" / "out"
if _frontend_dir.is_dir():
    for _page in ("pulse", "approved", "trade", "performance", "portfolios", "actionables", "docs", "microbaskets", "recommendations", "sentiment"):
        _html = _frontend_dir / f"{_page}.html"
        if _html.is_file():
            def _make_page_handler(path: Path):
                async def _handler():
                    return FileResponse(path, media_type="text/html")
                return _handler
            app.add_api_route(f"/{_page}", _make_page_handler(_html), methods=["GET", "HEAD"])

    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
