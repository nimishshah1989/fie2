"""
FIE v3 — Sector Recommendation Engine Routes
Generates stock/ETF recommendations based on sector ratio performance vs base index.

Performance: All price lookups use batch queries. A full generate call
does ~15 DB queries regardless of sector/stock count (no N+1 patterns).
Fundamentals fetched via yfinance in parallel after DB work completes.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

import yfinance as yf
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from models import get_db, IndexPrice, IndexConstituent
from price_service import (
    SECTOR_INDICES_FOR_RECO, SECTOR_ETF_MAP,
    fetch_nse_index_constituents,
)

logger = logging.getLogger("fie_v3.recommendations")
router = APIRouter()


# ─── Pydantic Models ─────────────────────────────────────

class GenerateRequest(BaseModel):
    base: str = "NIFTY"
    period: str = "1m"                    # Single period (e.g. 1w, 1m, 3m, 6m, 12m)
    selected_sectors: List[str]           # Only checked sectors
    threshold: float = 5.0               # Single threshold for all sectors


# ─── Constants ────────────────────────────────────────────

PERIOD_MAP = {"1w": 7, "1m": 30, "3m": 90, "6m": 180, "12m": 365}
PERIOD_TOLERANCE = {"1w": 5, "1m": 10, "3m": 15, "6m": 15, "12m": 15}


# ─── Batch Helpers (no N+1) ───────────────────────────────

def _resolve_period_dates(db: Session) -> Dict[str, Optional[str]]:
    """Resolve all 5 period target dates to actual DB dates — 10 queries total, done once."""
    resolved = {}
    for pk, days in PERIOD_MAP.items():
        target_str = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        tol = PERIOD_TOLERANCE.get(pk, 15)
        target_dt = datetime.strptime(target_str, "%Y-%m-%d")

        before = db.query(sqlfunc.max(IndexPrice.date)).filter(IndexPrice.date <= target_str).scalar()
        after = db.query(sqlfunc.min(IndexPrice.date)).filter(IndexPrice.date >= target_str).scalar()

        best = None
        if before:
            gap = (target_dt - datetime.strptime(before, "%Y-%m-%d")).days
            if gap <= tol:
                best = before
        if after:
            gap_after = (datetime.strptime(after, "%Y-%m-%d") - target_dt).days
            if gap_after <= tol:
                if best is None:
                    best = after
                elif gap_after < abs((target_dt - datetime.strptime(best, "%Y-%m-%d")).days):
                    best = after
        resolved[pk] = best
    return resolved


def _batch_latest_prices(db: Session, tickers: Set[str]) -> Dict[str, float]:
    """Fetch latest close price for many tickers in one query.
    Returns {ticker: close_price}."""
    if not tickers:
        return {}
    # Subquery: max date per ticker
    subq = (
        db.query(IndexPrice.index_name, sqlfunc.max(IndexPrice.date).label("max_date"))
        .filter(IndexPrice.index_name.in_(tickers))
        .group_by(IndexPrice.index_name)
        .subquery()
    )
    rows = (
        db.query(IndexPrice.index_name, IndexPrice.close_price)
        .join(subq, (IndexPrice.index_name == subq.c.index_name) & (IndexPrice.date == subq.c.max_date))
        .all()
    )
    return {r[0]: r[1] for r in rows if r[1]}


def _batch_historical_prices(db: Session, dates: List[str], tickers: Set[str]) -> Dict[str, Dict[str, float]]:
    """Fetch prices at specific historical dates for many tickers in one query.
    Returns {date: {ticker: close_price}}."""
    if not dates or not tickers:
        return {}
    rows = (
        db.query(IndexPrice.date, IndexPrice.index_name, IndexPrice.close_price)
        .filter(IndexPrice.date.in_(dates), IndexPrice.index_name.in_(tickers))
        .all()
    )
    result: Dict[str, Dict[str, float]] = {}
    for date_str, ticker, price in rows:
        if price:
            result.setdefault(date_str, {})[ticker] = price
    return result


def _compute_ratio_returns_from_cache(
    ticker: str,
    base_key: str,
    latest_prices: Dict[str, float],
    period_dates: Dict[str, Optional[str]],
    hist_prices: Dict[str, Dict[str, float]],
) -> Dict[str, float]:
    """Compute ratio returns using pre-fetched price data. Zero DB queries."""
    current = latest_prices.get(ticker)
    base_current = latest_prices.get(base_key)
    if not current or not base_current or base_current <= 0:
        return {}

    ratio_today = current / base_current
    returns = {}
    for pk in PERIOD_MAP:
        hist_date = period_dates.get(pk)
        if not hist_date:
            continue
        date_prices = hist_prices.get(hist_date, {})
        old_ticker = date_prices.get(ticker)
        old_base = date_prices.get(base_key)
        if old_ticker and old_base and old_base > 0:
            ratio_old = old_ticker / old_base
            if ratio_old > 0:
                returns[pk] = round(((ratio_today / ratio_old) - 1) * 100, 2)
    return returns


# ─── Fundamentals Fetcher ─────────────────────────────────

def _fetch_fundamentals(tickers: List[str]) -> Dict[str, Dict]:
    """Fetch fundamental data for a list of NSE tickers via yfinance.

    Uses ThreadPoolExecutor(max_workers=8) for parallel fetching.
    Returns {ticker: {trailingPE, trailingEps, fiftyTwoWeekHigh, fiftyTwoWeekLow, marketCap}}.
    Graceful per-ticker failure — missing data returns None values.
    """
    if not tickers:
        return {}

    fundamentals: Dict[str, Dict] = {}
    fields = ["trailingPE", "trailingEps", "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "marketCap"]

    def _fetch_one(ticker: str) -> tuple:
        try:
            info = yf.Ticker(f"{ticker}.NS").info
            data = {field: info.get(field) for field in fields}
            return (ticker, data)
        except Exception as exc:
            logger.debug("Fundamentals fetch failed for %s: %s", ticker, exc)
            return (ticker, {field: None for field in fields})

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_fetch_one, t): t for t in tickers}
        for future in as_completed(futures, timeout=60):
            try:
                ticker, data = future.result(timeout=60)
                fundamentals[ticker] = data
            except Exception as exc:
                ticker = futures[future]
                logger.debug("Fundamentals future failed for %s: %s", ticker, exc)
                fundamentals[ticker] = {field: None for field in fields}

    return fundamentals


# ─── Endpoints ────────────────────────────────────────────

@router.get("/api/recommendations/sectors")
async def get_sectors(db: Session = Depends(get_db)):
    """Return sector list + period labels for the threshold input grid."""
    sectors = []
    for key, display_name in SECTOR_INDICES_FOR_RECO:
        etfs = SECTOR_ETF_MAP.get(key, [])
        sectors.append({
            "key": key,
            "display_name": display_name,
            "etfs": etfs,
        })

    return {
        "success": True,
        "sectors": sectors,
        "periods": list(PERIOD_MAP.keys()),
        "period_labels": {"1w": "1W", "1m": "1M", "3m": "3M", "6m": "6M", "12m": "12M"},
    }


@router.post("/api/recommendations/generate")
async def generate_recommendations(req: GenerateRequest, db: Session = Depends(get_db)):
    """Generate stock/ETF recommendations based on sector ratio thresholds.

    Optimized: pre-fetches all prices in batch queries, then computes
    ratio returns in-memory. Fundamentals fetched via yfinance after
    DB work. Total DB queries: ~15 regardless of input size.
    """
    try:
        base = req.base.upper()
        period = req.period.lower()
        threshold = req.threshold
        sector_lookup = {key: name for key, name in SECTOR_INDICES_FOR_RECO}

        # Validate period
        if period not in PERIOD_MAP:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid period '{period}'. Must be one of: {', '.join(PERIOD_MAP.keys())}",
            )

        # Filter to only valid selected sectors
        valid_sectors = [sk for sk in req.selected_sectors if sk in sector_lookup]
        if not valid_sectors:
            raise HTTPException(
                status_code=400,
                detail="No valid sectors selected. Check sector keys against /api/recommendations/sectors.",
            )

        # ── Step 1: Resolve period dates (10 queries, done once) ──
        period_dates = _resolve_period_dates(db)
        hist_dates = [d for d in period_dates.values() if d]

        # ── Step 2: Collect ALL tickers we'll need prices for ──
        all_tickers: Set[str] = {base}

        # Sector index keys
        for sector_key in valid_sectors:
            all_tickers.add(sector_key)

        # Pre-load ALL constituents for all selected sectors (1 query)
        requested_display_names = [sector_lookup[sk] for sk in valid_sectors]
        all_constituents: List[IndexConstituent] = []
        if requested_display_names:
            all_constituents = (
                db.query(IndexConstituent)
                .filter(IndexConstituent.index_name.in_(requested_display_names))
                .all()
            )

        # Group constituents by sector display name
        sector_constituents: Dict[str, List[IndexConstituent]] = {}
        for c in all_constituents:
            sector_constituents.setdefault(c.index_name, []).append(c)
            all_tickers.add(c.ticker)

        # ETF tickers
        for sector_key in valid_sectors:
            for etf in SECTOR_ETF_MAP.get(sector_key, []):
                all_tickers.add(etf)

        # ── Step 3: Batch-fetch all prices (2 queries) ──
        latest_prices = _batch_latest_prices(db, all_tickers)
        hist_prices = _batch_historical_prices(db, hist_dates, all_tickers)

        # ── Step 4: Compute sector ratio returns (in-memory) ──
        sector_ratios: Dict[str, Dict[str, float]] = {}
        for sector_key in valid_sectors:
            sector_ratios[sector_key] = _compute_ratio_returns_from_cache(
                sector_key, base, latest_prices, period_dates, hist_prices,
            )

        # ── Step 5: Assemble qualifying and non-qualifying sectors ──
        qualifying_sectors = []
        non_qualifying_sectors = []
        # Collect all stock tickers across qualifying sectors for fundamentals
        all_stock_tickers: List[str] = []

        for sector_key in valid_sectors:
            display_name = sector_lookup[sector_key]
            ratio_return = sector_ratios.get(sector_key, {}).get(period)
            qualifies = ratio_return is not None and ratio_return > threshold

            # ETF recommendations from cache
            etf_tickers = SECTOR_ETF_MAP.get(sector_key, [])
            recommended_etfs = [
                {"ticker": etf, "last_price": latest_prices.get(etf)}
                for etf in etf_tickers
            ]

            if qualifies:
                # Compute stock-vs-sector ratios for all constituents
                constituents = sector_constituents.get(display_name, [])
                top_stocks = []
                for c in constituents:
                    stock_ratio = _compute_ratio_returns_from_cache(
                        c.ticker, sector_key, latest_prices, period_dates, hist_prices,
                    )
                    top_stocks.append({
                        "ticker": c.ticker,
                        "name": c.company_name or c.ticker,
                        "ratio_return_vs_sector": stock_ratio.get(period),
                        "last_price": c.last_price,
                        "weight_pct": c.weight_pct,
                        # Fundamental placeholders — filled after batch fetch
                        "pe_ratio": None,
                        "eps": None,
                        "week_52_high": None,
                        "week_52_low": None,
                        "market_cap_cr": None,
                    })
                    all_stock_tickers.append(c.ticker)

                # Sort by ratio return descending, return ALL stocks
                top_stocks.sort(
                    key=lambda s: s["ratio_return_vs_sector"] if s["ratio_return_vs_sector"] is not None else -9999,
                    reverse=True,
                )

                qualifying_sectors.append({
                    "sector_key": sector_key,
                    "sector_name": display_name,
                    "ratio_return": ratio_return,
                    "qualifies": True,
                    "top_stocks": top_stocks,
                    "recommended_etfs": recommended_etfs,
                })
            else:
                non_qualifying_sectors.append({
                    "sector_key": sector_key,
                    "sector_name": display_name,
                    "ratio_return": ratio_return,
                    "qualifies": False,
                    "top_stocks": [],
                    "recommended_etfs": recommended_etfs,
                })

        # Sort qualifying sectors by ratio return descending
        qualifying_sectors.sort(
            key=lambda s: s["ratio_return"] if s["ratio_return"] is not None else -9999,
            reverse=True,
        )

        # ── Step 6: Batch-fetch fundamentals for all stock tickers ──
        if all_stock_tickers:
            # Deduplicate tickers
            unique_tickers = list(set(all_stock_tickers))
            fundamentals = _fetch_fundamentals(unique_tickers)

            # Merge fundamental data into each qualifying sector's stocks
            for sector in qualifying_sectors:
                for stock in sector["top_stocks"]:
                    fdata = fundamentals.get(stock["ticker"], {})
                    stock["pe_ratio"] = fdata.get("trailingPE")
                    stock["eps"] = fdata.get("trailingEps")
                    stock["week_52_high"] = fdata.get("fiftyTwoWeekHigh")
                    stock["week_52_low"] = fdata.get("fiftyTwoWeekLow")
                    raw_mcap = fdata.get("marketCap")
                    stock["market_cap_cr"] = round(raw_mcap / 1e7, 2) if raw_mcap else None

        return {
            "success": True,
            "base": base,
            "period": period,
            "threshold": threshold,
            "qualifying_sectors": qualifying_sectors,
            "non_qualifying_sectors": non_qualifying_sectors,
            "generated_at": datetime.now().isoformat(),
        }

    except HTTPException:
        # Re-raise HTTP exceptions as-is (validation errors etc.)
        raise
    except Exception as e:
        logger.error("Generate failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ─── Constituent Refresh ─────────────────────────────────

def refresh_sector_constituents(db: Session) -> int:
    """Fetch and store index constituents for all sector indices.
    Called during EOD scheduled job to keep constituent data fresh."""
    total_stored = 0

    for sector_key, display_name in SECTOR_INDICES_FOR_RECO:
        try:
            items = fetch_nse_index_constituents(display_name)
            if not items:
                continue

            for item in items:
                symbol = item.get("symbol", "").strip()
                if not symbol:
                    continue

                # Upsert constituent
                existing = (
                    db.query(IndexConstituent)
                    .filter(
                        IndexConstituent.index_name == display_name,
                        IndexConstituent.ticker == symbol,
                    )
                    .first()
                )
                if existing:
                    existing.company_name = item.get("company_name") or existing.company_name
                    existing.weight_pct = item.get("weight")
                    existing.last_price = item.get("last_price")
                    existing.fetched_at = datetime.now()
                else:
                    db.add(IndexConstituent(
                        index_name=display_name,
                        ticker=symbol,
                        company_name=item.get("company_name"),
                        weight_pct=item.get("weight"),
                        last_price=item.get("last_price"),
                    ))
                total_stored += 1

            db.commit()
            time.sleep(0.5)  # Rate limit between NSE API calls

        except Exception as e:
            logger.warning("Constituent refresh failed for %s: %s", display_name, e)
            db.rollback()

    logger.info("Constituent refresh: stored/updated %d records across %d sectors",
                total_stored, len(SECTOR_INDICES_FOR_RECO))
    return total_stored
