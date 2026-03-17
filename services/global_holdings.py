"""
FIE v3 -- Dynamic ETF Holdings Fetcher
Periodically fetches top holdings of global sector ETFs via yfinance.
Stores them so the Global Pulse Level 3 drill-down has fresh stock lists.

Usage:
  from services.global_holdings import refresh_global_holdings
  count = refresh_global_holdings(db)
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List

import yfinance as yf
from sqlalchemy.orm import Session

from global_constants import GLOBAL_SECTOR_FLAT

logger = logging.getLogger("fie_v3.global_holdings")

# Max holdings to store per ETF
MAX_HOLDINGS_PER_ETF = 15


def _fetch_etf_holdings(symbol: str) -> List[Dict]:
    """Fetch top holdings for a single ETF via yfinance.
    Returns [{"ticker": "AAPL", "name": "Apple Inc.", "weight": 22.5}, ...]"""
    try:
        etf = yf.Ticker(symbol)

        # yfinance exposes holdings via .info or .get_holdings()
        # Try multiple approaches since yfinance API varies by version
        holdings = []

        # Approach 1: ETF info with top_holdings
        info = etf.info or {}
        # Some ETFs have holdings in .info
        if hasattr(etf, "major_holders"):
            pass  # Not useful for our case

        # Approach 2: Use funds_data if available (yfinance 0.2.30+)
        try:
            if hasattr(etf, "funds_data"):
                fd = etf.funds_data
                if hasattr(fd, "top_holdings") and fd.top_holdings is not None:
                    for idx, row in fd.top_holdings.iterrows():
                        ticker = str(idx).strip()
                        if not ticker or ticker == "nan":
                            continue
                        holdings.append({
                            "ticker": ticker,
                            "name": str(row.get("Name", row.get("holdingName", ticker))),
                            "weight": float(row.get("Holding Percent", row.get("holdingPercent", 0))) * 100
                            if float(row.get("Holding Percent", row.get("holdingPercent", 0))) < 1
                            else float(row.get("Holding Percent", row.get("holdingPercent", 0))),
                        })
        except Exception:
            pass

        # Approach 3: Use get_info() holdings key
        if not holdings:
            try:
                top = info.get("holdings", [])
                for h in top[:MAX_HOLDINGS_PER_ETF]:
                    holdings.append({
                        "ticker": h.get("symbol", h.get("ticker", "")),
                        "name": h.get("holdingName", h.get("shortName", "")),
                        "weight": h.get("holdingPercent", 0) * 100,
                    })
            except Exception:
                pass

        return holdings[:MAX_HOLDINGS_PER_ETF]

    except Exception as e:
        logger.debug("Holdings fetch failed for %s: %s", symbol, e)
        return []


def refresh_global_holdings(db: Session) -> int:
    """Fetch and store top holdings for all global sector ETFs.
    Returns total number of holdings stored/updated."""
    from models import IndexPrice  # noqa: avoid circular at module level

    total = 0
    sector_items = list(GLOBAL_SECTOR_FLAT.items())

    # Parallel fetch with 6 workers
    def _fetch_one(item):
        sec_key, sec_info = item
        symbol = sec_info["symbol"]
        holdings = _fetch_etf_holdings(symbol)
        return sec_key, holdings

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(_fetch_one, item): item for item in sector_items}
        for future in as_completed(futures, timeout=120):
            try:
                sec_key, holdings = future.result(timeout=30)
                if holdings:
                    # Store in the GLOBAL_CONSTITUENTS runtime cache
                    # This updates the in-memory dict so the API serves fresh data
                    from global_constants import GLOBAL_CONSTITUENTS
                    GLOBAL_CONSTITUENTS[sec_key] = [
                        {"ticker": h["ticker"], "name": h["name"]}
                        for h in holdings if h.get("ticker")
                    ]
                    total += len(holdings)
                    logger.debug("Holdings: %s -> %d stocks", sec_key, len(holdings))
            except Exception as e:
                sec_key = futures[future][0]
                logger.debug("Holdings future failed for %s: %s", sec_key, e)

    logger.info("Global holdings refresh: %d holdings across %d sectors", total, len(sector_items))
    return total
