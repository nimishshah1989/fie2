"""
FIE v3 — Global Markets Router
Endpoints for global market indices + sector ETFs with relative performance.
Data source: yfinance (stored in IndexPrice table).
"""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from global_constants import (
    GLOBAL_MARKETS,
    get_all_global_keys,
    get_all_global_symbols,
    get_benchmark_for_key,
    get_global_display_map,
    get_key_to_market,
)
from models import IndexPrice, get_db
from services.data_helpers import upsert_price_row

logger = logging.getLogger("fie_v3.global_markets")
router = APIRouter()


@router.post(
    "/api/global-markets/backfill",
    tags=["Global Markets"],
    summary="Backfill 1Y global market data",
)
async def backfill_global(db: Session = Depends(get_db)):
    """Fetch 1Y history for all global benchmarks + sector ETFs via yfinance."""
    from price_service import fetch_yfinance_index_history

    symbols = get_all_global_symbols()
    stored = 0
    for key, yf_symbol in symbols.items():
        try:
            rows = fetch_yfinance_index_history(key, period="1y", yf_symbol_override=yf_symbol)
            for row in rows:
                if upsert_price_row(db, key, row):
                    stored += 1
        except Exception as e:
            logger.warning("Global backfill failed for %s (%s): %s", key, yf_symbol, e)

    db.commit()
    logger.info("Global markets backfill: stored %d records across %d instruments", stored, len(symbols))
    return {"success": True, "stored": stored, "instruments": len(symbols)}


def backfill_global_sync(db: Session) -> int:
    """Sync version for background thread startup backfill."""
    from price_service import fetch_yfinance_index_history

    symbols = get_all_global_symbols()
    stored = 0
    for key, yf_symbol in symbols.items():
        try:
            rows = fetch_yfinance_index_history(key, period="1y", yf_symbol_override=yf_symbol)
            for row in rows:
                if upsert_price_row(db, key, row):
                    stored += 1
        except Exception as e:
            logger.warning("Global backfill failed for %s (%s): %s", key, yf_symbol, e)

    db.commit()
    return stored


@router.get(
    "/api/global-markets/live",
    tags=["Global Markets"],
    summary="Global market data with relative sector performance",
)
async def global_markets_live(db: Session = Depends(get_db)):
    """Return global indices + sector ETFs with relative performance vs country benchmark.

    For each market:
      - benchmark: latest price + period returns
      - sector_etfs: latest price + period returns + relative performance vs benchmark
    """
    display_map = get_global_display_map()
    key_to_market = get_key_to_market()
    all_keys = get_all_global_keys()

    # Fetch latest price for each global instrument from DB
    latest_prices: dict[str, dict] = {}
    for key in all_keys:
        row = (
            db.query(IndexPrice)
            .filter(IndexPrice.index_name == key)
            .order_by(desc(IndexPrice.date))
            .first()
        )
        if row and row.close_price:
            latest_prices[key] = {
                "close": row.close_price,
                "date": row.date,
                "open": row.open_price,
                "high": row.high_price,
                "low": row.low_price,
            }

    # Batch-fetch historical prices for period returns
    period_map = {"1d": 1, "1w": 7, "1m": 30, "3m": 90, "6m": 180, "12m": 365}
    tolerance = {"1d": 5, "1w": 5, "1m": 10, "3m": 15, "6m": 15, "12m": 15}

    historical_prices: dict[str, dict[str, float]] = {}
    for pk, days in period_map.items():
        target_dt = datetime.now() - timedelta(days=days)
        tol = tolerance.get(pk, 15)
        range_start = (target_dt - timedelta(days=tol)).strftime("%Y-%m-%d")
        range_end = (target_dt + timedelta(days=tol)).strftime("%Y-%m-%d")

        rows = db.query(IndexPrice).filter(
            IndexPrice.index_name.in_(all_keys),
            IndexPrice.date >= range_start,
            IndexPrice.date <= range_end,
            IndexPrice.close_price.isnot(None),
        ).all()

        best: dict[str, tuple[float, int]] = {}
        for r in rows:
            gap = abs((datetime.strptime(r.date, "%Y-%m-%d") - target_dt).days)
            existing = best.get(r.index_name)
            if existing is None or gap < existing[1]:
                best[r.index_name] = (r.close_price, gap)

        historical_prices[pk] = {name: price for name, (price, _) in best.items()}

    # Previous close for daily change
    prev_closes: dict[str, float] = {}
    for key in all_keys:
        current = latest_prices.get(key)
        if not current:
            continue
        prev = (
            db.query(IndexPrice)
            .filter(IndexPrice.index_name == key, IndexPrice.date < current["date"])
            .order_by(desc(IndexPrice.date))
            .first()
        )
        if prev and prev.close_price:
            prev_closes[key] = prev.close_price

    def _build_instrument(key: str, is_benchmark: bool = False) -> dict:
        """Build response dict for a single instrument."""
        current = latest_prices.get(key)
        close = current["close"] if current else None
        date = current["date"] if current else None

        # Daily change
        prev_close = prev_closes.get(key)
        change_pct = None
        if close and prev_close and prev_close > 0:
            change_pct = round(((close - prev_close) / prev_close) * 100, 2)

        # Absolute period returns
        index_returns: dict[str, float | None] = {}
        if close:
            for pk in period_map:
                old = historical_prices.get(pk, {}).get(key)
                if old and old > 0:
                    index_returns[pk] = round(((close / old) - 1) * 100, 2)

        # Relative performance vs benchmark
        relative_returns: dict[str, float | None] = {}
        if not is_benchmark and close:
            bm_key = get_benchmark_for_key(key)
            bm_current = latest_prices.get(bm_key, {}).get("close") if bm_key else None
            if bm_current and bm_current > 0:
                for pk in period_map:
                    old_etf = historical_prices.get(pk, {}).get(key)
                    old_bm = historical_prices.get(pk, {}).get(bm_key) if bm_key else None
                    if old_etf and old_etf > 0 and old_bm and old_bm > 0:
                        etf_ret = (close / old_etf) - 1
                        bm_ret = (bm_current / old_bm) - 1
                        # Relative = ETF return - benchmark return
                        relative_returns[pk] = round((etf_ret - bm_ret) * 100, 2)

        return {
            "key": key,
            "name": display_map.get(key, key),
            "close": close,
            "date": date,
            "change_pct": change_pct,
            "index_returns": index_returns,
            "relative_returns": relative_returns,
        }

    # Build response grouped by market
    markets = []
    for market_key, market in GLOBAL_MARKETS.items():
        bm = market["benchmark"]
        bm_data = _build_instrument(bm["key"], is_benchmark=True)

        etfs = []
        for etf in market["sector_etfs"]:
            etf_data = _build_instrument(etf["key"], is_benchmark=False)
            etf_data["sector"] = etf["name"]
            etfs.append(etf_data)

        markets.append({
            "market_key": market_key,
            "name": market["name"],
            "flag": market["flag"],
            "benchmark": bm_data,
            "sector_etfs": etfs,
        })

    return {
        "success": True,
        "markets": markets,
        "timestamp": datetime.now().isoformat() + "Z",
    }
