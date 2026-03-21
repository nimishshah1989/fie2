"""
Startup backfill — fetches historical price data for all tracked instruments.
Runs once on app startup in a background thread.

Incremental: checks last date in DB per instrument, only fetches from there.
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from models import (
    AlertStatus,
    IndexConstituent,
    IndexPrice,
    SessionLocal,
    TradingViewAlert,
)
from services.data_helpers import get_all_portfolio_tickers_with_inception, upsert_price_row

logger = logging.getLogger("fie_v3.backfill")


def _get_last_price_date(db, instrument_name: str) -> Optional[str]:
    """Return the most recent date string we have for an instrument, or None."""
    row = (
        db.query(IndexPrice.date)
        .filter(IndexPrice.index_name == instrument_name)
        .order_by(IndexPrice.date.desc())
        .first()
    )
    return row[0] if row else None


def _incremental_period(db, tickers: List[str], default_period: str = "1y") -> Dict:
    """Determine start date for bulk fetch — use last known date if recent enough."""
    if not tickers:
        return {"period": default_period}

    # Sample a few tickers to find the most recent data
    sample = tickers[:5]
    latest_dates = []
    for t in sample:
        last = _get_last_price_date(db, t)
        if last:
            latest_dates.append(last)

    if not latest_dates:
        return {"period": default_period}

    # If we have data from within last 7 days, just fetch 10d
    most_recent = max(latest_dates)
    try:
        last_dt = datetime.strptime(most_recent, "%Y-%m-%d")
        days_ago = (datetime.now() - last_dt).days
        if days_ago <= 7:
            return {"period": "10d"}
        elif days_ago <= 35:
            return {"period": "1mo"}
        elif days_ago <= 95:
            return {"period": "3mo"}
        elif days_ago <= 190:
            return {"period": "6mo"}
    except (ValueError, TypeError):
        pass

    return {"period": default_period}


def run_startup_backfill() -> None:
    """Background thread: fetch historical data for indices, ETFs, portfolio instruments, etc."""
    logger.info("Background backfill starting (thread: %s)...", threading.current_thread().name)
    db = None
    try:
        from price_service import (
            NSE_ETF_UNIVERSE,
            NSE_INDEX_KEYS,
            fetch_yfinance_bulk_history,
            fetch_yfinance_bulk_stock_history,
        )

        db = SessionLocal()

        # ── 1. Indices via yfinance ──────────────────────────────
        idx_params = _incremental_period(db, list(NSE_INDEX_KEYS))
        logger.info("Backfill: fetching %s history for %d indices...", idx_params.get("period", "?"), len(NSE_INDEX_KEYS))
        idx_data = fetch_yfinance_bulk_history(NSE_INDEX_KEYS, **idx_params)
        idx_stored = 0
        for idx_name, rows in idx_data.items():
            for row in rows:
                if upsert_price_row(db, idx_name, row):
                    idx_stored += 1
        db.commit()
        logger.info("Backfill: stored %d index records across %d indices", idx_stored, len(idx_data))

        # ── 1b. NSE API historical ───────────────────────────────
        try:
            from price_service import fetch_historical_indices_nse_sync

            logger.info("Backfill: fetching history from NSE API for tracked indices...")
            nse_hist = fetch_historical_indices_nse_sync()
            nse_stored = 0
            tracked = set(NSE_INDEX_KEYS)
            for idx_name, rows in nse_hist.items():
                if idx_name not in tracked:
                    continue
                for row in rows:
                    if upsert_price_row(db, idx_name, row):
                        nse_stored += 1
            db.commit()
            logger.info("Backfill: stored %d NSE API records across %d indices", nse_stored, len(nse_hist))
        except Exception as e:
            logger.warning("NSE API historical backfill failed (non-fatal): %s", e)

        # ── 2. ETFs via yfinance ─────────────────────────────────
        etf_tickers = list(NSE_ETF_UNIVERSE.keys())
        etf_params = _incremental_period(db, etf_tickers)
        logger.info("Backfill: fetching %s history for %d ETFs...", etf_params.get("period", "?"), len(etf_tickers))
        etf_data = fetch_yfinance_bulk_stock_history(etf_tickers, **etf_params)
        etf_stored = 0
        for ticker, rows in etf_data.items():
            for row in rows:
                if upsert_price_row(db, ticker, row):
                    etf_stored += 1
        db.commit()
        logger.info("Backfill: stored %d ETF records across %d ETFs", etf_stored, len(etf_data))

        # ── 3. Portfolio instruments ─────────────────────────────
        ticker_inception = get_all_portfolio_tickers_with_inception(db)
        if ticker_inception:
            all_portfolio_tickers = list(ticker_inception.keys())
            ptf_params = _incremental_period(db, all_portfolio_tickers)
            # If incremental says short period, use it; otherwise use inception date
            if ptf_params.get("period") == "1y":
                earliest_start = min(ticker_inception.values())
                ptf_params = {"start": earliest_start}
            logger.info("Backfill: fetching history for %d portfolio instruments...", len(all_portfolio_tickers))
            portfolio_data = fetch_yfinance_bulk_stock_history(all_portfolio_tickers, **ptf_params)
            ptf_stored = 0
            for ticker, rows in portfolio_data.items():
                for row in rows:
                    if upsert_price_row(db, ticker, row):
                        ptf_stored += 1
            db.commit()
            logger.info("Backfill: stored %d portfolio records across %d tickers", ptf_stored, len(portfolio_data))
        else:
            logger.info("Backfill: no portfolio instruments to fetch")

        # ── 4. Alert tickers ─────────────────────────────────────
        alert_tickers = [
            r[0]
            for r in db.query(TradingViewAlert.ticker)
            .filter(TradingViewAlert.status.in_([AlertStatus.APPROVED, AlertStatus.PENDING]))
            .distinct()
            .all()
            if r[0] and r[0] != "UNKNOWN"
        ]
        covered = set(t.upper() for t in (ticker_inception or {}).keys())
        covered.update(t.upper() for t in etf_tickers)
        new_alert_tickers = [t for t in alert_tickers if t.upper() not in covered]
        if new_alert_tickers:
            alert_params = _incremental_period(db, new_alert_tickers)
            logger.info("Backfill: fetching %s history for %d alert tickers...", alert_params.get("period", "?"), len(new_alert_tickers))
            alert_data = fetch_yfinance_bulk_stock_history(new_alert_tickers, **alert_params)
            alert_stored = 0
            for ticker, rows in alert_data.items():
                for row in rows:
                    if upsert_price_row(db, ticker, row):
                        alert_stored += 1
            db.commit()
            logger.info("Backfill: stored %d alert records across %d tickers", alert_stored, len(alert_data))

        # ── 5. Basket constituents + NAV ─────────────────────────
        _backfill_baskets(db, etf_tickers, new_alert_tickers, ticker_inception)

        # ── 6. Sector index constituents ─────────────────────────
        all_constituent_tickers = _backfill_sector_constituents(db, etf_tickers, new_alert_tickers, ticker_inception)

        # ── 7. Nifty 500 constituents ────────────────────────────
        _backfill_nifty500(db, etf_tickers, all_constituent_tickers, ticker_inception)

        # ── 8. Per-stock sentiment ───────────────────────────────
        try:
            from services.stock_sentiment import compute_and_store_stock_sentiment

            stock_count = compute_and_store_stock_sentiment(db)
            logger.info("Per-stock sentiment: computed for %d stocks", stock_count)
        except Exception as e:
            logger.warning("Per-stock sentiment failed (non-fatal): %s", e)

        # ── 9. Sentiment history backfill ────────────────────────
        try:
            from services.sentiment_engine import backfill_sentiment_history

            filled = backfill_sentiment_history(db, weeks=20)
            logger.info("Sentiment history backfill: %d new snapshots", filled)
        except Exception as e:
            logger.warning("Sentiment history backfill failed (non-fatal): %s", e)

        # ── 10. Compass: stock + ETF prices + RS scores ──────────
        try:
            from services.compass_data import backfill_compass_etfs, backfill_compass_stocks
            from services.compass_portfolio import update_model_nav
            from services.compass_rs import compute_sector_rs_scores, persist_rs_scores

            logger.info("Compass backfill: starting stock + ETF price fetch...")
            compass_stocks = backfill_compass_stocks(db, period="1y")
            compass_etfs = backfill_compass_etfs(db, period="1y")
            logger.info("Compass backfill: %d stock + %d ETF records stored", compass_stocks, compass_etfs)

            scores = compute_sector_rs_scores(db, base_index="NIFTY", period_key="3M")
            if scores:
                persist_rs_scores(db, scores, instrument_type="index")
                update_model_nav(db)
                logger.info("Compass: initial RS scores computed for %d sectors", len(scores))
        except Exception as e:
            logger.warning("Compass backfill failed (non-fatal): %s", e)

        logger.info("Background backfill complete")
    except Exception as e:
        logger.warning("Background backfill failed (non-fatal): %s", e)
    finally:
        if db:
            db.close()


def _backfill_baskets(db, etf_tickers: list, alert_tickers: list, ticker_inception: Optional[dict]) -> None:
    """Fetch basket constituent prices and compute NAVs."""
    try:
        from price_service import fetch_yfinance_bulk_stock_history

        from models import BasketStatus, Microbasket
        from services.basket_service import backfill_basket_nav, get_all_basket_constituent_tickers

        basket_tickers = get_all_basket_constituent_tickers(db)
        already_fetched = set(t.upper() for t in (ticker_inception or {}).keys())
        already_fetched.update(t.upper() for t in etf_tickers)
        already_fetched.update(t.upper() for t in alert_tickers)
        new_basket_tickers = [t for t in basket_tickers if t.upper() not in already_fetched]

        if new_basket_tickers:
            bkt_params = _incremental_period(db, new_basket_tickers)
            logger.info("Backfill: fetching %s history for %d basket tickers...", bkt_params.get("period", "?"), len(new_basket_tickers))
            basket_data = fetch_yfinance_bulk_stock_history(new_basket_tickers, **bkt_params)
            bkt_stored = 0
            for ticker, rows in basket_data.items():
                for row in rows:
                    if upsert_price_row(db, ticker, row):
                        bkt_stored += 1
            db.commit()
            logger.info("Backfill: stored %d basket constituent records", bkt_stored)

        active_baskets = db.query(Microbasket).filter(Microbasket.status == BasketStatus.ACTIVE).all()
        for basket in active_baskets:
            backfill_basket_nav(basket, db, days=365)
    except Exception as e:
        logger.warning("Basket backfill step failed (non-fatal): %s", e)


def _backfill_sector_constituents(
    db, etf_tickers: list, alert_tickers: list, ticker_inception: Optional[dict],
) -> List[str]:
    """Refresh sector constituents from NSE + fetch price history. Returns all constituent tickers."""
    all_constituent_tickers: List[str] = []
    try:
        from price_service import fetch_yfinance_bulk_stock_history

        from routers.recommendations import refresh_sector_constituents

        constituent_count = refresh_sector_constituents(db)
        logger.info("Backfill: refreshed %d sector constituent records from NSE", constituent_count)

        all_constituent_tickers = [r[0] for r in db.query(IndexConstituent.ticker).distinct().all() if r[0]]
        already_fetched = set(t.upper() for t in (ticker_inception or {}).keys())
        already_fetched.update(t.upper() for t in etf_tickers)
        already_fetched.update(t.upper() for t in alert_tickers)
        new_tickers = [t for t in all_constituent_tickers if t.upper() not in already_fetched]

        if new_tickers:
            cst_params = _incremental_period(db, new_tickers)
            logger.info("Backfill: fetching %s history for %d constituent stocks...", cst_params.get("period", "?"), len(new_tickers))
            cst_data = fetch_yfinance_bulk_stock_history(new_tickers, **cst_params)
            cst_stored = 0
            for ticker, rows in cst_data.items():
                for row in rows:
                    if upsert_price_row(db, ticker, row):
                        cst_stored += 1
            db.commit()
            logger.info("Backfill: stored %d constituent price records across %d tickers", cst_stored, len(cst_data))
    except Exception as e:
        logger.warning("Sector constituent backfill failed (non-fatal): %s", e)

    return all_constituent_tickers


def _backfill_nifty500(
    db, etf_tickers: list, constituent_tickers: list, ticker_inception: Optional[dict],
) -> None:
    """Fetch Nifty 500 constituents from NSE + price history."""
    try:
        from price_service import fetch_nse_index_constituents, fetch_yfinance_bulk_stock_history

        nifty500_items = fetch_nse_index_constituents("NIFTY 500")
        if not nifty500_items:
            logger.info("Backfill: Nifty 500 fetch returned 0 items (NSE API may be unavailable)")
            return

        nifty500_stored = 0
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
            nifty500_stored += 1
        db.commit()
        logger.info("Backfill: stored/updated %d Nifty 500 constituent records", nifty500_stored)

        # Fetch prices for uncovered Nifty 500 tickers
        nifty500_tickers = [item["symbol"] for item in nifty500_items if item.get("symbol")]
        all_covered = set(t.upper() for t in constituent_tickers)
        all_covered.update(t.upper() for t in (ticker_inception or {}).keys())
        all_covered.update(t.upper() for t in etf_tickers)
        new_n500 = [t for t in nifty500_tickers if t.upper() not in all_covered]

        if new_n500:
            n500_params = _incremental_period(db, new_n500)
            logger.info("Backfill: fetching %s history for %d Nifty 500 stocks...", n500_params.get("period", "?"), len(new_n500))
            n500_data = fetch_yfinance_bulk_stock_history(new_n500, **n500_params)
            n500_stored = 0
            for ticker, rows in n500_data.items():
                for row in rows:
                    if upsert_price_row(db, ticker, row):
                        n500_stored += 1
            db.commit()
            logger.info("Backfill: stored %d Nifty 500 stock price records", n500_stored)
    except Exception as e:
        logger.warning("Nifty 500 constituent backfill failed (non-fatal): %s", e)
