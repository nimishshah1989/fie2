"""
FIE v3 -- Global Relative Strength Router
3-level drill-down: Global Index -> Sector -> Stock, all ratio-based RS.

Level 1: Global indices (S&P 500, FTSE, DAX, etc.) vs NIFTY
Level 2: Sector ETFs/indices within a market vs parent index
Level 3: Top stocks within a sector vs the sector ETF
"""

import logging
from datetime import datetime
from typing import Set

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from global_constants import (
    GLOBAL_CONSTITUENTS,
    GLOBAL_INDICES,
    GLOBAL_REGION_ORDER,
    GLOBAL_SECTOR_FLAT,
    GLOBAL_SECTOR_MAP,
)
from models import IndexPrice, get_db
from services.ratio_service import (
    batch_historical_prices,
    batch_latest_prices,
    compute_absolute_returns,
    compute_ratio_returns,
    get_signal,
    resolve_period_dates,
)

logger = logging.getLogger("fie_v3.global_pulse")
router = APIRouter()


# --- Level 1: Global Indices vs NIFTY ----------------------------------------

@router.get(
    "/api/global-pulse/indices",
    tags=["Global Pulse"],
    summary="Global indices with RS vs NIFTY",
    description="Returns all tracked global indices with ratio-based relative strength "
                "signals and period returns vs the selected base (default NIFTY 50).",
)
async def global_indices(base: str = "NIFTY50", db: Session = Depends(get_db)):
    """Level 1: All global indices with RS vs Indian benchmark."""
    try:
        base_key = base.upper()
        if base_key not in GLOBAL_INDICES:
            base_key = "NIFTY50"

        # Collect all tickers we need
        all_tickers: Set[str] = set(GLOBAL_INDICES.keys())

        # Resolve dates + fetch prices
        period_dates = resolve_period_dates(db)
        hist_dates = [d for d in period_dates.values() if d]
        latest = batch_latest_prices(db, all_tickers)
        hist = batch_historical_prices(db, hist_dates, all_tickers)

        base_price = latest.get(base_key)
        results = []
        for key, meta in GLOBAL_INDICES.items():
            price = latest.get(key)
            ratio = None
            signal = "NEUTRAL"
            if price and base_price and base_price > 0 and key != base_key:
                ratio = round(price / base_price, 4)
                signal = get_signal(ratio)
            elif key == base_key:
                ratio = 1.0
                signal = "BASE"

            ratio_rets = compute_ratio_returns(key, base_key, latest, period_dates, hist)
            abs_rets = compute_absolute_returns(key, latest, period_dates, hist)

            # Check if this market has sectors available
            has_sectors = key in GLOBAL_SECTOR_MAP and len(GLOBAL_SECTOR_MAP[key]) > 0

            results.append({
                "key": key,
                "name": meta["name"],
                "region": meta["region"],
                "currency": meta["currency"],
                "last": price,
                "ratio": ratio,
                "signal": signal,
                "ratio_returns": ratio_rets,
                "index_returns": abs_rets,
                "has_sectors": has_sectors,
                "sector_count": len(GLOBAL_SECTOR_MAP.get(key, {})),
            })

        # Sort by region order, then by ratio return (3m) descending
        region_rank = {r: i for i, r in enumerate(GLOBAL_REGION_ORDER)}
        results.sort(key=lambda x: (
            region_rank.get(x["region"], 99),
            -(x["ratio_returns"].get("3m", 0) or 0),
        ))

        return {
            "success": True,
            "count": len(results),
            "base": base_key,
            "base_name": GLOBAL_INDICES[base_key]["name"],
            "regions": GLOBAL_REGION_ORDER,
            "indices": results,
            "timestamp": datetime.now().isoformat() + "Z",
        }
    except Exception as e:
        logger.error("Global indices error: %s", e, exc_info=True)
        return {"success": False, "indices": [], "error": str(e)}


# --- Level 2: Sectors within a Market -----------------------------------------

@router.get(
    "/api/global-pulse/sectors",
    tags=["Global Pulse"],
    summary="Sector ETFs within a global market",
    description="Returns sector ETFs/indices for the selected market with RS vs the "
                "parent index. Also shows RS vs NIFTY for cross-market comparison.",
)
async def global_sectors(
    market: str = "SP500", base: str = "NIFTY50", db: Session = Depends(get_db),
):
    """Level 2: Sectors within a selected global market."""
    try:
        market_key = market.upper()
        base_key = base.upper()

        sectors_map = GLOBAL_SECTOR_MAP.get(market_key, {})
        if not sectors_map:
            return {
                "success": True, "market": market_key, "sectors": [],
                "message": f"No sector data available for {market_key}",
            }

        parent_meta = GLOBAL_INDICES.get(market_key, {})

        # Collect all tickers: parent index + all sector ETFs + NIFTY base
        all_tickers: Set[str] = {market_key, base_key}
        for sec_key in sectors_map:
            all_tickers.add(sec_key)

        period_dates = resolve_period_dates(db)
        hist_dates = [d for d in period_dates.values() if d]
        latest = batch_latest_prices(db, all_tickers)
        hist = batch_historical_prices(db, hist_dates, all_tickers)

        parent_price = latest.get(market_key)
        results = []
        for sec_key, sec_meta in sectors_map.items():
            price = latest.get(sec_key)

            # RS vs parent index (primary)
            ratio_vs_parent = None
            signal_vs_parent = "NEUTRAL"
            if price and parent_price and parent_price > 0:
                ratio_vs_parent = round(price / parent_price, 4)
                signal_vs_parent = get_signal(ratio_vs_parent)

            ratio_rets_parent = compute_ratio_returns(
                sec_key, market_key, latest, period_dates, hist,
            )

            # RS vs NIFTY (secondary, for cross-market comparison)
            ratio_rets_nifty = compute_ratio_returns(
                sec_key, base_key, latest, period_dates, hist,
            )

            abs_rets = compute_absolute_returns(sec_key, latest, period_dates, hist)

            has_stocks = sec_key in GLOBAL_CONSTITUENTS and len(GLOBAL_CONSTITUENTS[sec_key]) > 0

            results.append({
                "key": sec_key,
                "name": sec_meta["name"],
                "symbol": sec_meta["symbol"],
                "last": price,
                "ratio_vs_parent": ratio_vs_parent,
                "signal": signal_vs_parent,
                "ratio_returns_vs_parent": ratio_rets_parent,
                "ratio_returns_vs_nifty": ratio_rets_nifty,
                "index_returns": abs_rets,
                "has_stocks": has_stocks,
                "stock_count": len(GLOBAL_CONSTITUENTS.get(sec_key, [])),
            })

        # Sort by ratio return vs parent (3m) descending
        results.sort(
            key=lambda x: -(x["ratio_returns_vs_parent"].get("3m", 0) or 0),
        )

        return {
            "success": True,
            "market": market_key,
            "market_name": parent_meta.get("name", market_key),
            "base": base_key,
            "sectors": results,
            "timestamp": datetime.now().isoformat() + "Z",
        }
    except Exception as e:
        logger.error("Global sectors error: %s", e, exc_info=True)
        return {"success": False, "sectors": [], "error": str(e)}


# --- Level 3: Stocks within a Sector -----------------------------------------

@router.get(
    "/api/global-pulse/stocks",
    tags=["Global Pulse"],
    summary="Top stocks within a global sector",
    description="Returns top constituent stocks for the selected sector ETF with RS "
                "vs the sector index. Stocks ranked by ratio return.",
)
async def global_stocks(sector: str = "SP500_TECH", db: Session = Depends(get_db)):
    """Level 3: Top stocks within a selected sector."""
    try:
        sector_key = sector.upper()

        constituents = GLOBAL_CONSTITUENTS.get(sector_key, [])
        sector_info = GLOBAL_SECTOR_FLAT.get(sector_key)
        if not constituents or not sector_info:
            return {
                "success": True, "sector": sector_key, "stocks": [],
                "message": f"No constituent data for {sector_key}",
            }

        parent_index = sector_info["parent_index"]
        parent_meta = GLOBAL_INDICES.get(parent_index, {})

        # Collect all tickers: sector ETF + all stocks + parent index
        all_tickers: Set[str] = {sector_key, parent_index}
        for stock in constituents:
            all_tickers.add(stock["ticker"])

        period_dates = resolve_period_dates(db)
        hist_dates = [d for d in period_dates.values() if d]
        latest = batch_latest_prices(db, all_tickers)
        hist = batch_historical_prices(db, hist_dates, all_tickers)

        sector_price = latest.get(sector_key)
        results = []
        for stock in constituents:
            ticker = stock["ticker"]
            price = latest.get(ticker)

            # RS vs sector ETF
            ratio_vs_sector = None
            signal = "NEUTRAL"
            if price and sector_price and sector_price > 0:
                ratio_vs_sector = round(price / sector_price, 4)
                signal = get_signal(ratio_vs_sector)

            ratio_rets = compute_ratio_returns(
                ticker, sector_key, latest, period_dates, hist,
            )
            abs_rets = compute_absolute_returns(ticker, latest, period_dates, hist)

            results.append({
                "ticker": ticker,
                "name": stock["name"],
                "last": price,
                "ratio_vs_sector": ratio_vs_sector,
                "signal": signal,
                "ratio_returns": ratio_rets,
                "index_returns": abs_rets,
            })

        # Sort by ratio return (3m) descending
        results.sort(
            key=lambda x: -(x["ratio_returns"].get("3m", 0) or 0),
        )

        return {
            "success": True,
            "sector": sector_key,
            "sector_name": sector_info["name"],
            "parent_index": parent_index,
            "parent_name": parent_meta.get("name", parent_index),
            "stocks": results,
            "timestamp": datetime.now().isoformat() + "Z",
        }
    except Exception as e:
        logger.error("Global stocks error: %s", e, exc_info=True)
        return {"success": False, "stocks": [], "error": str(e)}
