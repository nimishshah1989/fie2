"""
FIE v3 — Index & Market Data Routes
EOD fetch, historical fetch, bulk upload, stock history, latest, and live indices.
"""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, Depends
from sqlalchemy import desc, func as sqlfunc
from sqlalchemy.orm import Session

from models import (
    get_db, IndexPrice, TradingViewAlert, AlertStatus,
)
from services.data_helpers import upsert_price_row

logger = logging.getLogger("fie_v3.indices")
router = APIRouter()


@router.post("/api/indices/fetch-eod")
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


@router.post("/api/indices/fetch-historical")
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


@router.post("/api/indices/bulk-upload")
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


@router.post("/api/stocks/fetch-history")
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


@router.get("/api/indices/latest")
async def indices_latest(base: str = "NIFTY", db: Session = Depends(get_db)):
    """Return latest index prices with ratio vs base, recommendations, and period returns."""
    latest_date = db.query(sqlfunc.max(IndexPrice.date)).scalar()
    if not latest_date:
        return {"date": None, "base": base, "indices": [],
                "message": "No EOD data. Call POST /api/indices/fetch-eod first."}

    base_row = db.query(IndexPrice).filter_by(date=latest_date, index_name=base).first()
    base_close = base_row.close_price if base_row else None

    all_rows = db.query(IndexPrice).filter_by(date=latest_date).order_by(IndexPrice.index_name).all()

    def _get_period_return(idx_name, days):
        target = (datetime.strptime(latest_date, "%Y-%m-%d") - timedelta(days=days)).strftime("%Y-%m-%d")
        old = (
            db.query(IndexPrice)
            .filter(IndexPrice.index_name == idx_name, IndexPrice.date <= target)
            .order_by(desc(IndexPrice.date))
            .first()
        )
        if not old or not old.close_price:
            return None
        curr = db.query(IndexPrice).filter_by(date=latest_date, index_name=idx_name).first()
        if not curr or not curr.close_price:
            return None
        return round(((curr.close_price - old.close_price) / old.close_price) * 100, 2)

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

        prev_row = (
            db.query(IndexPrice)
            .filter(IndexPrice.index_name == row.index_name, IndexPrice.date < latest_date)
            .order_by(desc(IndexPrice.date))
            .first()
        )
        chg_pct = None
        if prev_row and prev_row.close_price and close:
            chg_pct = round(((close - prev_row.close_price) / prev_row.close_price) * 100, 2)

        periods = {}
        for label, days in [("1d", 1), ("1w", 7), ("1m", 30), ("3m", 90), ("6m", 180), ("12m", 365)]:
            periods[label] = _get_period_return(row.index_name, days)

        results.append({
            "index_name": row.index_name,
            "close": close,
            "change_pct": chg_pct,
            "ratio": ratio,
            "signal": signal,
            **periods,
        })

    return {"date": latest_date, "base": base, "indices": results}


@router.get("/api/indices/live")
async def indices_live(base: str = "NIFTY", tracked_only: bool = True, db: Session = Depends(get_db)):
    """Return real-time live index data from NSE with ratio-based period returns.
    tracked_only=True (default) filters to only indices with yfinance historical data.
    Also includes non-nsetools instruments (BSE, commodities, currencies) from DB."""
    from price_service import fetch_live_indices, NSE_INDEX_KEYS, NON_NSETOOLS_KEYS, NSE_DISPLAY_MAP

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

            item["index_returns"] = index_returns

        return {
            "success": True, "count": len(data), "base": base,
            "indices": data, "timestamp": datetime.now().isoformat() + "Z",
        }
    except Exception as e:
        logger.error("Live indices fetch error: %s", e)
        return {"success": False, "indices": [], "error": str(e)}
