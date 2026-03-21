"""
Scheduled EOD jobs — daily price fetch, sentiment refresh, compass rebalance.
All functions are called by APScheduler from server.py.
"""

import asyncio
import logging
from datetime import datetime

from models import (
    AlertStatus,
    IndexConstituent,
    IndexPrice,
    SessionLocal,
    TradingViewAlert,
)
from services.data_helpers import get_portfolio_tickers, upsert_price_row

logger = logging.getLogger("fie_v3.eod_jobs")


def scheduled_eod_fetch() -> None:
    """Store ALL nsetools indices + ETFs + portfolio stocks + constituents daily."""
    from price_service import (
        NSE_ETF_UNIVERSE,
        NSE_INDEX_KEYS,
        fetch_live_indices,
        fetch_yfinance_bulk_history,
        fetch_yfinance_bulk_stock_history,
    )

    logger.info("Scheduled EOD fetch starting...")
    db = SessionLocal()
    try:
        today_str = datetime.now().strftime("%Y-%m-%d")

        # ── 1. Live nsetools indices (135+) ──────────────────────
        live = fetch_live_indices()
        nsetools_names = set()
        idx_stored = 0
        for item in live:
            close = item.get("last")
            if not close:
                continue
            nsetools_names.add(item["index_name"])
            existing = db.query(IndexPrice).filter_by(date=today_str, index_name=item["index_name"]).first()
            if existing:
                existing.close_price = close
                existing.open_price = item.get("open")
                existing.high_price = item.get("high")
                existing.low_price = item.get("low")
                existing.fetched_at = datetime.now()
            else:
                db.add(
                    IndexPrice(
                        date=today_str,
                        index_name=item["index_name"],
                        close_price=close,
                        open_price=item.get("open"),
                        high_price=item.get("high"),
                        low_price=item.get("low"),
                    )
                )
            idx_stored += 1

        # ── 1b. yfinance fallback for missed indices ─────────────
        missed_keys = [k for k in NSE_INDEX_KEYS if k not in nsetools_names]
        yf_idx_stored = 0
        if missed_keys:
            yf_idx_data = fetch_yfinance_bulk_history(missed_keys, period="5d")
            for idx_name, rows in yf_idx_data.items():
                for row in rows:
                    if upsert_price_row(db, idx_name, row):
                        yf_idx_stored += 1

        # ── 1c. NSE API historical refresh ───────────────────────
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
            logger.warning("EOD NSE API refresh failed (non-fatal): %s", e)

        # ── 2. ETF prices ────────────────────────────────────────
        etf_tickers = list(NSE_ETF_UNIVERSE.keys())
        etf_data = fetch_yfinance_bulk_stock_history(etf_tickers, period="5d")
        etf_stored = 0
        for ticker, rows in etf_data.items():
            for row in rows:
                if upsert_price_row(db, ticker, row):
                    etf_stored += 1

        # ── 3. Portfolio stock prices ────────────────────────────
        stock_tickers = get_portfolio_tickers(db)
        stk_stored = 0
        if stock_tickers:
            stock_data = fetch_yfinance_bulk_stock_history(stock_tickers, period="5d")
            for ticker, rows in stock_data.items():
                for row in rows:
                    if upsert_price_row(db, ticker, row):
                        stk_stored += 1

        # ── 4. Alert tickers ────────────────────────────────────
        alert_tickers = [
            r[0]
            for r in db.query(TradingViewAlert.ticker)
            .filter(TradingViewAlert.status.in_([AlertStatus.APPROVED, AlertStatus.PENDING]))
            .distinct()
            .all()
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

        # ── 5. Basket constituent prices + NAVs ──────────────────
        basket_nav_count = 0
        try:
            from services.basket_service import compute_today_basket_navs, get_all_basket_constituent_tickers

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

        # ── 6. Sector index constituents ─────────────────────────
        constituent_count = 0
        constituent_price_count = 0
        try:
            from routers.recommendations import refresh_sector_constituents

            constituent_count = refresh_sector_constituents(db)
            all_constituent_tickers = [r[0] for r in db.query(IndexConstituent.ticker).distinct().all() if r[0]]
            new_constituent_tickers = [t for t in all_constituent_tickers if t.upper() not in covered]
            if new_constituent_tickers:
                cst_data = fetch_yfinance_bulk_stock_history(new_constituent_tickers, period="5d")
                for ticker, rows in cst_data.items():
                    for row in rows:
                        if upsert_price_row(db, ticker, row):
                            constituent_price_count += 1
        except Exception as e:
            logger.warning("Constituent refresh step failed (non-fatal): %s", e)

        # ── 7. Nifty 500 constituents ────────────────────────────
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
                        .filter(IndexConstituent.index_name == "NIFTY 500", IndexConstituent.ticker == symbol)
                        .first()
                    )
                    if existing:
                        existing.last_price = item.get("last_price")
                        existing.fetched_at = datetime.now()
                    else:
                        db.add(
                            IndexConstituent(
                                index_name="NIFTY 500",
                                ticker=symbol,
                                company_name=item.get("company_name"),
                                weight_pct=item.get("weight"),
                                last_price=item.get("last_price"),
                            )
                        )
                nifty500_tickers = [i["symbol"] for i in nifty500_items if i.get("symbol")]
                new_n500 = [t for t in nifty500_tickers if t.upper() not in covered]
                if new_n500:
                    n500_data = fetch_yfinance_bulk_stock_history(new_n500, period="5d")
                    for ticker, rows in n500_data.items():
                        for row in rows:
                            upsert_price_row(db, ticker, row)
        except Exception as e:
            logger.warning("Nifty 500 EOD refresh failed (non-fatal): %s", e)

        db.commit()
        logger.info(
            "Scheduled EOD: %d nsetools + %d yf-fallback + %d nse-api index, %d ETF, %d stock, %d alert, %d basket NAV, %d constituent",
            idx_stored, yf_idx_stored, nse_eod_stored, etf_stored, stk_stored, alert_stored, basket_nav_count, constituent_count,
        )

        # ── 8. Per-stock sentiment ───────────────────────────────
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


def eod_sentiment_refresh() -> None:
    """Refresh sentiment indicators 5 min after EOD prices are stored."""
    from routers.sentiment import refresh_sentiment

    db = SessionLocal()
    try:
        asyncio.run(refresh_sentiment(db))
    except Exception as e:
        logger.warning("EOD sentiment refresh failed: %s", e)
    finally:
        db.close()


def compass_intraday_refresh() -> None:
    """15-minute intraday refresh: latest prices → RS scores → clear cache."""
    db = SessionLocal()
    try:
        from routers.compass import _clear_cache
        from services.compass_data import daily_refresh_compass_prices
        from services.compass_rs import compute_sector_rs_scores, persist_rs_scores

        daily_refresh_compass_prices(db)
        scores = compute_sector_rs_scores(db, base_index="NIFTY", period_key="3M")
        persist_rs_scores(db, scores, instrument_type="index")
        _clear_cache()
        logger.info("Compass 15-min refresh: %d sectors scored", len(scores))
    except Exception as e:
        logger.warning("Compass 15-min refresh failed: %s", e)
    finally:
        db.close()


def compass_eod_rebalance() -> None:
    """EOD rebalance at 3:40 PM IST — compute RS, run portfolio trades, update NAV."""
    db = SessionLocal()
    try:
        from routers.compass import _clear_cache
        from services.compass_data import daily_refresh_compass_prices
        from services.compass_portfolio import run_weekly_rebalance, update_model_nav
        from services.compass_rs import compute_sector_rs_scores, persist_rs_scores

        daily_refresh_compass_prices(db)
        scores = compute_sector_rs_scores(db, base_index="NIFTY", period_key="3M")
        persist_rs_scores(db, scores, instrument_type="index")
        run_weekly_rebalance(db, scores)
        update_model_nav(db)
        _clear_cache()
        logger.info("Compass EOD rebalance: %d sectors scored", len(scores))
    except Exception as e:
        logger.warning("Compass EOD rebalance failed: %s", e)
    finally:
        db.close()
