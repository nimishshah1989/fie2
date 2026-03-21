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
from models import init_db

# ─── Routers ─────────────────────────────────────────────
from routers import alerts, baskets, compass, health, indices, pms, portfolios, recommendations, sentiment
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
app.include_router(compass.router)


# ═══════════════════════════════════════════════════════════
#  STARTUP & SCHEDULER
# ═══════════════════════════════════════════════════════════

@app.on_event("startup")
async def startup():
    init_db()
    from services.backfill import run_startup_backfill

    bg_thread = threading.Thread(target=run_startup_backfill, daemon=True, name="yfinance-backfill")
    bg_thread.start()
    logger.info("Startup complete — backfill running in background")


@app.on_event("startup")
async def start_scheduler():
    try:
        import pytz
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        from services.eod_jobs import (
            compass_eod_rebalance,
            compass_intraday_refresh,
            eod_sentiment_refresh,
            scheduled_eod_fetch,
        )

        scheduler = BackgroundScheduler()
        ist = pytz.timezone("Asia/Kolkata")

        scheduler.add_job(
            scheduled_eod_fetch,
            CronTrigger(hour=15, minute=30, timezone=ist),
            id="daily_eod_fetch",
            replace_existing=True,
        )
        scheduler.add_job(
            eod_sentiment_refresh,
            CronTrigger(hour=15, minute=35, timezone=ist),
            id="daily_sentiment_refresh",
            replace_existing=True,
        )
        scheduler.add_job(
            compass_intraday_refresh,
            CronTrigger(minute="*/15", hour="9-15", day_of_week="mon-fri", timezone=ist),
            id="compass_intraday_refresh",
            replace_existing=True,
        )
        scheduler.add_job(
            compass_eod_rebalance,
            CronTrigger(hour=15, minute=40, timezone=ist),
            id="compass_eod_rebalance",
            replace_existing=True,
        )

        scheduler.start()
        logger.info(
            "APScheduler started — EOD 3:30, sentiment 3:35, compass EOD 3:40 PM IST, "
            "compass intraday every 15 min (9:15-3:45 Mon-Fri)"
        )
    except Exception as e:
        logger.warning("APScheduler not available: %s (install apscheduler)", e)


# ═══════════════════════════════════════════════════════════
#  STATIC FRONTEND (Next.js export)
# ═══════════════════════════════════════════════════════════

_frontend_dir = Path(__file__).parent / "web" / "out"
if _frontend_dir.is_dir():
    for _page in ("pulse", "approved", "trade", "performance", "portfolios", "actionables", "docs", "microbaskets", "recommendations", "sentiment", "compass"):
        _html = _frontend_dir / f"{_page}.html"
        if _html.is_file():
            def _make_page_handler(path: Path):
                async def _handler():
                    return FileResponse(path, media_type="text/html")
                return _handler
            app.add_api_route(f"/{_page}", _make_page_handler(_html), methods=["GET", "HEAD"])

    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
