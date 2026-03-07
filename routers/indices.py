"""
FIE v3 — Index & Market Data Routes
EOD fetch, historical fetch, bulk upload, stock history, latest, and live indices.
"""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import desc
from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from models import (
    AlertStatus,
    IndexPrice,
    TradingViewAlert,
    get_db,
)
from services.data_helpers import upsert_price_row

logger = logging.getLogger("fie_v3.indices")
router = APIRouter()

# Currency pairs where rising price = weaker INR = negative for Indian investor
INVERTED_RETURN_KEYS = {"USDINR"}


@router.post(
    "/api/indices/fetch-eod",
    tags=["Market Data"],
    summary="Fetch EOD index data",
    description="Fetches end-of-day data for all NSE indices via yfinance (5-day window) and stores in the database. Typically triggered by the scheduled EOD job.",
)
async def fetch_eod(db: Session = Depends(get_db)):
    """Fetch EOD data for all NSE indices and store in DB."""
    from price_service import fetch_all_index_eod

    data = fetch_all_index_eod(period="5d")
    stored = 0
    for idx_name, rows in data.items():
        for row in rows:
            if upsert_price_row(db, idx_name, row):
                stored += 1
    db.commit()
    return {"success": True, "stored": stored, "indices": len(data)}


@router.post(
    "/api/indices/fetch-historical",
    tags=["Market Data"],
    summary="Fetch 1Y historical index data",
    description="Fetches 1-year historical data from NSE API for all tracked indices, plus today's live prices from nsetools. Used for initial backfill.",
)
async def fetch_historical(db: Session = Depends(get_db)):
    """Fetch 1Y historical data from NSE API for all indices + today's live from nsetools."""
    from price_service import fetch_historical_indices_nse_sync, fetch_live_indices

    hist_data = fetch_historical_indices_nse_sync(period="1y")
    stored = 0
    for idx_name, rows in hist_data.items():
        for row in rows:
            if upsert_price_row(db, idx_name, row):
                stored += 1

    today_str = datetime.now().strftime("%Y-%m-%d")
    live = fetch_live_indices()
    live_stored = 0
    for item in live:
        close = item.get("last")
        if not close:
            continue
        row = {
            "date": today_str, "close": close,
            "open": item.get("open"), "high": item.get("high"),
            "low": item.get("low"), "volume": None,
        }
        if upsert_price_row(db, item["index_name"], row):
            live_stored += 1

    db.commit()
    logger.info("Historical fetch: %d historical + %d live records", stored, live_stored)
    return {"success": True, "stored_historical": stored, "stored_live": live_stored, "indices": len(hist_data)}


@router.post(
    "/api/indices/bulk-upload",
    tags=["Market Data"],
    summary="Bulk upload index data",
    description="Accepts bulk historical index price data in JSON format. Used by the local backfill script running on an Indian IP to bypass NSE geoblocking.",
)
async def bulk_upload_indices(request: Request, db: Session = Depends(get_db)):
    """Accept bulk historical index data (from local backfill script running on India IP)."""
    body = await request.json()
    data = body.get("data", {})
    if not data:
        return {"success": False, "error": "No data provided"}

    stored = 0
    indices_count = 0
    for idx_name, rows in data.items():
        if not rows:
            continue
        indices_count += 1
        for row in rows:
            if upsert_price_row(db, idx_name, row):
                stored += 1

    db.commit()
    logger.info("Bulk upload: %d records across %d indices", stored, indices_count)
    return {"success": True, "stored": stored, "indices": indices_count}


@router.post(
    "/api/stocks/fetch-history",
    tags=["Market Data"],
    summary="Fetch stock price history",
    description="Fetches 12-month price history via yfinance for all approved alert tickers and stores in the database.",
)
async def fetch_stock_history_endpoint(db: Session = Depends(get_db)):
    """Fetch 12M history for all stocks in the alert database."""
    from price_service import fetch_stock_history

    tickers = [
        r[0] for r in db.query(TradingViewAlert.ticker)
        .filter(TradingViewAlert.status == AlertStatus.APPROVED)
        .distinct().all()
        if r[0] and r[0] != "UNKNOWN"
    ]

    stored = 0
    for ticker in tickers:
        rows = fetch_stock_history(ticker, "1y")
        for row in rows:
            if upsert_price_row(db, ticker, row):
                stored += 1

    db.commit()
    return {"success": True, "stored": stored, "tickers": len(tickers)}


@router.get(
    "/api/indices/latest",
    tags=["Market Data"],
    summary="Latest index prices with period returns",
    description="Returns the most recent EOD index prices with ratio vs base index, recommendation signals, day change, and period returns (1d, 1w, 1m, 3m, 6m, 12m). Uses batch queries for performance.",
)
async def indices_latest(base: str = "NIFTY", db: Session = Depends(get_db)):
    """Return latest index prices with ratio vs base, recommendations, and period returns.
    Optimized: uses batch queries for period returns instead of per-index per-period queries."""
    latest_date = db.query(sqlfunc.max(IndexPrice.date)).scalar()
    if not latest_date:
        return {"date": None, "base": base, "indices": [],
                "message": "No EOD data. Call POST /api/indices/fetch-eod first."}

    base_row = db.query(IndexPrice).filter_by(date=latest_date, index_name=base).first()
    base_close = base_row.close_price if base_row else None

    all_rows = db.query(IndexPrice).filter_by(date=latest_date).order_by(IndexPrice.index_name).all()

    # Build current close map from latest date rows (already fetched, no extra query)
    current_close_map = {r.index_name: r.close_price for r in all_rows if r.close_price}

    # Batch-fetch previous close for all indices (1 query instead of N)
    prev_date = (
        db.query(sqlfunc.max(IndexPrice.date))
        .filter(IndexPrice.date < latest_date)
        .scalar()
    )
    prev_close_map: dict = {}
    if prev_date:
        prev_rows = db.query(IndexPrice).filter_by(date=prev_date).all()
        prev_close_map = {r.index_name: r.close_price for r in prev_rows if r.close_price}

    # Batch-fetch historical prices for period returns using bidirectional date lookup
    # Same approach as /api/indices/live — eliminates N*6 individual queries
    period_map = {"1d": 1, "1w": 7, "1m": 30, "3m": 90, "6m": 180, "12m": 365}
    tolerance = {"1d": 5, "1w": 5, "1m": 10, "3m": 15, "6m": 15, "12m": 15}

    historical_dates: dict = {}
    latest_dt = datetime.strptime(latest_date, "%Y-%m-%d")
    for pk, days in period_map.items():
        target = (latest_dt - timedelta(days=days)).strftime("%Y-%m-%d")
        tol = tolerance.get(pk, 15)

        before = db.query(sqlfunc.max(IndexPrice.date)).filter(IndexPrice.date <= target).scalar()
        after = db.query(sqlfunc.min(IndexPrice.date)).filter(IndexPrice.date >= target).scalar()

        best = None
        if before:
            gap_before = (datetime.strptime(target, "%Y-%m-%d") - datetime.strptime(before, "%Y-%m-%d")).days
            if gap_before <= tol:
                best = before
        if after:
            gap_after = (datetime.strptime(after, "%Y-%m-%d") - datetime.strptime(target, "%Y-%m-%d")).days
            if gap_after <= tol:
                if best is None:
                    best = after
                else:
                    gap_best = abs((datetime.strptime(target, "%Y-%m-%d") - datetime.strptime(best, "%Y-%m-%d")).days)
                    if gap_after < gap_best:
                        best = after
        if best:
            historical_dates[pk] = best

    # Load all prices at historical dates in one query
    unique_dates = list(set(historical_dates.values()))
    date_price_map: dict = {}
    if unique_dates:
        hist_rows = db.query(IndexPrice).filter(IndexPrice.date.in_(unique_dates)).all()
        for r in hist_rows:
            if r.date not in date_price_map:
                date_price_map[r.date] = {}
            if r.close_price:
                date_price_map[r.date][r.index_name] = r.close_price

    historical_prices: dict = {}
    for pk, d in historical_dates.items():
        historical_prices[pk] = date_price_map.get(d, {})

    results = []
    for row in all_rows:
        close = row.close_price
        ratio = round(close / base_close, 4) if (close and base_close and base_close > 0) else None

        if ratio is not None and row.index_name != base:
            if ratio > 1.05:
                signal = "STRONG OW"
            elif ratio > 1.0:
                signal = "OVERWEIGHT"
            elif ratio < 0.95:
                signal = "STRONG UW"
            elif ratio < 1.0:
                signal = "UNDERWEIGHT"
            else:
                signal = "NEUTRAL"
        else:
            signal = "BASE" if row.index_name == base else "NEUTRAL"

        # Previous day change from batch-loaded prev_close_map
        prev_close = prev_close_map.get(row.index_name)
        chg_pct = None
        if prev_close and prev_close > 0 and close:
            chg_pct = round(((close - prev_close) / prev_close) * 100, 2)

        # Invert change_pct for currency pairs (rising USDINR = weaker rupee = negative)
        if chg_pct is not None and row.index_name in INVERTED_RETURN_KEYS:
            chg_pct = round(-chg_pct, 2)

        # Period returns from batch-loaded historical prices
        periods = {}
        if close:
            for label in period_map:
                old_prices = historical_prices.get(label, {})
                old_close = old_prices.get(row.index_name)
                if old_close and old_close > 0:
                    ret = round(((close - old_close) / old_close) * 100, 2)
                    # Invert returns for currency pairs
                    if row.index_name in INVERTED_RETURN_KEYS:
                        ret = round(-ret, 2)
                    periods[label] = ret
                else:
                    periods[label] = None
        else:
            for label in period_map:
                periods[label] = None

        results.append({
            "index_name": row.index_name,
            "close": close,
            "change_pct": chg_pct,
            "ratio": ratio,
            "signal": signal,
            **periods,
        })

    return {"date": latest_date, "base": base, "indices": results}


@router.get(
    "/api/indices/live",
    tags=["Market Data"],
    summary="Live index data with ratio returns",
    description="Returns real-time live index data from nsetools with ratio-based and absolute period returns. Includes non-nsetools instruments (BSE SENSEX, USDINR, GOLD) from DB. Use tracked_only=false to see all 135+ NSE indices.",
)
async def indices_live(base: str = "NIFTY", tracked_only: bool = True, db: Session = Depends(get_db)):
    """Return real-time live index data from NSE with ratio-based period returns.
    tracked_only=True (default) filters to only indices with yfinance historical data.
    Also includes non-nsetools instruments (BSE, commodities, currencies) from DB."""
    from price_service import NON_NSETOOLS_KEYS, NSE_DISPLAY_MAP, NSE_INDEX_KEYS, fetch_live_indices

    try:
        data = fetch_live_indices()
        if not data:
            data = []

        if tracked_only:
            tracked_set = set(k.upper() for k in NSE_INDEX_KEYS)
            data = [item for item in data if item["index_name"].upper() in tracked_set]

        # Append non-nsetools instruments (BSE, commodities, currencies) from latest DB prices
        nsetools_keys = set(item["index_name"].upper() for item in data)
        for key in NON_NSETOOLS_KEYS:
            if key.upper() in nsetools_keys:
                continue
            latest_row = (
                db.query(IndexPrice)
                .filter(IndexPrice.index_name == key)
                .order_by(desc(IndexPrice.date))
                .first()
            )
            if latest_row and latest_row.close_price:
                prev_row = (
                    db.query(IndexPrice)
                    .filter(IndexPrice.index_name == key, IndexPrice.date < latest_row.date)
                    .order_by(desc(IndexPrice.date))
                    .first()
                )
                pct_change = None
                if prev_row and prev_row.close_price:
                    pct_change = round(((latest_row.close_price - prev_row.close_price) / prev_row.close_price) * 100, 2)
                # Invert for currency pairs (rising USDINR = weaker rupee = negative)
                if pct_change is not None and key in INVERTED_RETURN_KEYS:
                    pct_change = round(-pct_change, 2)

                display_name = NSE_DISPLAY_MAP.get(key, key)
                data.append({
                    "index_name": key,
                    "nse_name": display_name,
                    "last": latest_row.close_price,
                    "open": latest_row.open_price,
                    "high": latest_row.high_price,
                    "low": latest_row.low_price,
                    "previousClose": prev_row.close_price if prev_row else None,
                    "variation": None,
                    "percentChange": pct_change,
                    "source": "db",
                })

        # Find base index
        base_close = None
        for item in data:
            if item["index_name"] == base:
                base_close = item.get("last")
                break

        # Pre-load historical prices — bidirectional closest-date lookup
        period_map = {"1d": 1, "1w": 7, "1m": 30, "3m": 90, "6m": 180, "12m": 365}
        tolerance = {"1d": 5, "1w": 5, "1m": 10, "3m": 15, "6m": 15, "12m": 15}

        historical_dates = {}
        for pk, days in period_map.items():
            target = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            tol = tolerance.get(pk, 15)

            before = db.query(sqlfunc.max(IndexPrice.date)).filter(IndexPrice.date <= target).scalar()
            after = db.query(sqlfunc.min(IndexPrice.date)).filter(IndexPrice.date >= target).scalar()

            best = None
            if before:
                gap_before = (datetime.strptime(target, "%Y-%m-%d") - datetime.strptime(before, "%Y-%m-%d")).days
                if gap_before <= tol:
                    best = before
            if after:
                gap_after = (datetime.strptime(after, "%Y-%m-%d") - datetime.strptime(target, "%Y-%m-%d")).days
                if gap_after <= tol:
                    if best is None:
                        best = after
                    else:
                        gap_best = abs((datetime.strptime(target, "%Y-%m-%d") - datetime.strptime(best, "%Y-%m-%d")).days)
                        if gap_after < gap_best:
                            best = after

            if best:
                historical_dates[pk] = best

        # Load all prices at those dates in one query
        unique_dates = list(set(historical_dates.values()))
        date_price_map = {}
        if unique_dates:
            all_rows = db.query(IndexPrice).filter(IndexPrice.date.in_(unique_dates)).all()
            for r in all_rows:
                if r.date not in date_price_map:
                    date_price_map[r.date] = {}
                if r.close_price:
                    date_price_map[r.date][r.index_name] = r.close_price

        historical_prices = {}
        for pk, d in historical_dates.items():
            historical_prices[pk] = date_price_map.get(d, {})

        # Enrich each item
        for item in data:
            close = item.get("last")
            idx_name = item["index_name"]

            # Ratio and signal
            if close and base_close and base_close > 0 and idx_name != base:
                ratio = round(close / base_close, 4)
                item["ratio"] = ratio
                if ratio > 1.05:
                    item["signal"] = "STRONG OW"
                elif ratio > 1.0:
                    item["signal"] = "OVERWEIGHT"
                elif ratio < 0.95:
                    item["signal"] = "STRONG UW"
                elif ratio < 1.0:
                    item["signal"] = "UNDERWEIGHT"
                else:
                    item["signal"] = "NEUTRAL"
            elif idx_name == base:
                item["ratio"] = 1.0
                item["signal"] = "BASE"
            else:
                item["ratio"] = None
                item["signal"] = "NEUTRAL"

            # Ratio-based period returns (DB-only, no interpolation)
            ratio_returns = {}
            ratio_today = (close / base_close) if (close and base_close and base_close > 0) else None

            if idx_name == base:
                for pk in period_map:
                    ratio_returns[pk] = 0.0
            elif ratio_today:
                for pk in period_map:
                    old_prices = historical_prices.get(pk, {})
                    old_idx = old_prices.get(idx_name)
                    old_base = old_prices.get(base)

                    if old_idx and old_base and old_base > 0:
                        ratio_old = old_idx / old_base
                        if ratio_old > 0:
                            ratio_returns[pk] = round(((ratio_today / ratio_old) - 1) * 100, 2)

            item["ratio_returns"] = ratio_returns

            # Index's own period returns (DB-only, no interpolation)
            index_returns = {}
            pct_chg = item.get("percentChange")
            if pct_chg is not None:
                try:
                    index_returns["1d"] = round(float(pct_chg), 2)
                except (ValueError, TypeError):
                    pass

            if close:
                for pk in period_map:
                    if pk == "1d" and "1d" in index_returns:
                        continue
                    old_prices = historical_prices.get(pk, {})
                    old_idx = old_prices.get(idx_name)
                    if old_idx and old_idx > 0:
                        index_returns[pk] = round(((close / old_idx) - 1) * 100, 2)

            # Invert returns for currency pairs (rising USDINR = weaker rupee = negative)
            if idx_name in INVERTED_RETURN_KEYS:
                index_returns = {k: round(-v, 2) for k, v in index_returns.items()}
                ratio_returns = {k: round(-v, 2) for k, v in ratio_returns.items()}
                item["ratio_returns"] = ratio_returns

            item["index_returns"] = index_returns

        return {
            "success": True, "count": len(data), "base": base,
            "indices": data, "timestamp": datetime.now().isoformat() + "Z",
        }
    except Exception as e:
        logger.error("Live indices fetch error: %s", e)
        return {"success": False, "indices": [], "error": str(e)}
