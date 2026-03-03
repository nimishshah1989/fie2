"""
FIE v3 — Sector Recommendation Engine Routes
Generates stock/ETF recommendations based on sector ratio performance vs base index.

Performance: All price lookups use batch queries. A full generate call
does ~15 DB queries regardless of sector/stock count (no N+1 patterns).
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from fastapi import APIRouter, Depends
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
    thresholds: Dict[str, Dict[str, float]]
    # thresholds shape: {"BANKNIFTY": {"1w": 2.0, "1m": 5.0, ...}, ...}


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
    ratio returns in-memory. Total DB queries: ~15 regardless of input size.
    """
    base = req.base.upper()
    sector_lookup = {key: name for key, name in SECTOR_INDICES_FOR_RECO}

    # ── Step 1: Resolve period dates (10 queries, done once) ──
    period_dates = _resolve_period_dates(db)
    hist_dates = [d for d in period_dates.values() if d]

    # ── Step 2: Collect ALL tickers we'll need prices for ──
    all_tickers: Set[str] = {base}

    # Sector index keys
    for sector_key in req.thresholds:
        if sector_key in sector_lookup:
            all_tickers.add(sector_key)

    # Pre-load ALL constituents for all requested sectors (1 query)
    requested_display_names = [
        sector_lookup[sk] for sk in req.thresholds if sk in sector_lookup
    ]
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
    for sector_key in req.thresholds:
        for etf in SECTOR_ETF_MAP.get(sector_key, []):
            all_tickers.add(etf)

    # ── Step 3: Batch-fetch all prices (2 queries) ──
    latest_prices = _batch_latest_prices(db, all_tickers)
    hist_prices = _batch_historical_prices(db, hist_dates, all_tickers)

    # ── Step 4: Compute sector ratio returns once per sector (in-memory) ──
    sector_ratios: Dict[str, Dict[str, float]] = {}
    for sector_key in req.thresholds:
        if sector_key in sector_lookup:
            sector_ratios[sector_key] = _compute_ratio_returns_from_cache(
                sector_key, base, latest_prices, period_dates, hist_prices,
            )

    # ── Step 5: Assemble results (zero additional queries) ──
    results: Dict[str, dict] = {}

    for period_key in PERIOD_MAP:
        qualifying = []

        for sector_key, threshold_dict in req.thresholds.items():
            threshold = threshold_dict.get(period_key)
            if threshold is None:
                continue

            display_name = sector_lookup.get(sector_key)
            if not display_name:
                continue

            ratio_return = sector_ratios.get(sector_key, {}).get(period_key)
            if ratio_return is None or ratio_return <= threshold:
                continue

            # Sector qualifies — compute stock-vs-sector ratios from cache
            constituents = sector_constituents.get(display_name, [])
            top_stocks = []
            for c in constituents:
                stock_ratio = _compute_ratio_returns_from_cache(
                    c.ticker, sector_key, latest_prices, period_dates, hist_prices,
                )
                top_stocks.append({
                    "ticker": c.ticker,
                    "name": c.company_name or c.ticker,
                    "ratio_return_vs_sector": stock_ratio.get(period_key),
                    "last_price": c.last_price,
                    "weight_pct": c.weight_pct,
                })

            # Sort by ratio return descending, pick top 3
            top_stocks.sort(
                key=lambda s: s["ratio_return_vs_sector"] if s["ratio_return_vs_sector"] is not None else -9999,
                reverse=True,
            )

            # ETF recommendations from cache
            etf_tickers = SECTOR_ETF_MAP.get(sector_key, [])
            recommended_etfs = [
                {"ticker": etf, "last_price": latest_prices.get(etf)}
                for etf in etf_tickers
            ]

            qualifying.append({
                "sector_key": sector_key,
                "sector_name": display_name,
                "ratio_return": ratio_return,
                "threshold": threshold,
                "top_stocks": top_stocks[:3],
                "recommended_etfs": recommended_etfs,
            })

        qualifying.sort(key=lambda s: s["ratio_return"], reverse=True)
        results[period_key] = {"qualifying_sectors": qualifying}

    return {
        "success": True,
        "base": base,
        "results": results,
        "generated_at": datetime.now().isoformat(),
    }


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
