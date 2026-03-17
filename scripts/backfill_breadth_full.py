"""
Full Nifty 500 breadth backfill. Fetches all 500 stocks from NSE list.
Usage: python3 scripts/backfill_breadth_full.py
"""

import logging
import sys
import os

import pandas as pd
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import Base, BreadthDaily, SessionLocal, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backfill_breadth_full")

YEARS = 5


def fetch_nifty500() -> list[str]:
    import requests
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r = requests.get("https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
                         headers=headers, timeout=15)
        r.raise_for_status()
        from io import StringIO
        df = pd.read_csv(StringIO(r.text))
        symbols = df["Symbol"].str.strip().tolist()
        logger.info("Fetched %d Nifty 500 symbols from NSE", len(symbols))
        return symbols
    except Exception as e:
        logger.warning("NSE fetch failed: %s — using file fallback", e)
        # Fallback: read from saved file
        fpath = "/tmp/nifty500_symbols.txt"
        if os.path.exists(fpath):
            with open(fpath) as f:
                symbols = [s.strip() for s in f.readlines() if s.strip()]
            logger.info("Loaded %d symbols from fallback file", len(symbols))
            return symbols
        raise RuntimeError("Cannot get Nifty 500 list")


def download_all(symbols: list[str]) -> dict[str, pd.DataFrame]:
    tickers = [f"{s}.NS" for s in symbols]
    end = pd.Timestamp.now()
    start = end - pd.DateOffset(years=YEARS, months=6)

    all_data = {}
    batch_size = 100
    total_batches = (len(tickers) + batch_size - 1) // batch_size

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        bn = i // batch_size + 1
        logger.info("Batch %d/%d (%d tickers)...", bn, total_batches, len(batch))
        try:
            data = yf.download(batch, start=start, end=end, group_by="ticker", progress=False, threads=True)
            if isinstance(data.columns, pd.MultiIndex):
                for ticker in batch:
                    if ticker in data.columns.get_level_values(0):
                        try:
                            df = data[ticker][["Close"]].dropna()
                            if len(df) > 50:
                                all_data[ticker] = df
                        except Exception:
                            pass
            elif len(batch) == 1:
                df = data[["Close"]].dropna()
                if len(df) > 50:
                    all_data[batch[0]] = df
        except Exception as e:
            logger.warning("Batch %d failed: %s", bn, e)

    logger.info("Downloaded %d / %d tickers", len(all_data), len(tickers))
    return all_data


def compute_and_store(all_data: dict[str, pd.DataFrame]):
    # Compute EMAs
    ema_data = {}
    for ticker, df in all_data.items():
        close = df["Close"].squeeze()
        if len(close) < 210:
            continue
        ema_data[ticker] = {
            "close": close,
            "ema21": close.ewm(span=21, adjust=False).mean(),
            "ema200": close.ewm(span=200, adjust=False).mean(),
        }

    logger.info("Computed EMAs for %d stocks", len(ema_data))

    # Get all trading dates
    all_dates = set()
    for d in ema_data.values():
        all_dates.update(d["close"].index)
    cutoff = pd.Timestamp.now() - pd.DateOffset(years=YEARS)
    all_dates = sorted(d for d in all_dates if d >= cutoff)
    logger.info("Computing breadth for %d trading days across %d stocks...", len(all_dates), len(ema_data))

    rows = []
    for dt in all_dates:
        a21 = a200 = total = 0
        for data in ema_data.values():
            if dt not in data["close"].index:
                continue
            total += 1
            price = data["close"].loc[dt]
            e21 = data["ema21"].loc[dt] if dt in data["ema21"].index else None
            e200 = data["ema200"].loc[dt] if dt in data["ema200"].index else None
            if pd.notna(price):
                if pd.notna(e21) and price > e21:
                    a21 += 1
                if pd.notna(e200) and price > e200:
                    a200 += 1

        if total > 0:
            ds = dt.strftime("%Y-%m-%d")
            rows.append({"date": ds, "metric": "above_21ema", "count": a21, "total": total})
            rows.append({"date": ds, "metric": "above_200ema", "count": a200, "total": total})

    logger.info("Generated %d breadth rows", len(rows))

    # Store
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(BreadthDaily).delete()
        db.commit()
        batch_size = 1000
        for i in range(0, len(rows), batch_size):
            batch = [BreadthDaily(**r) for r in rows[i:i + batch_size]]
            db.add_all(batch)
            db.commit()
        logger.info("Stored %d breadth records", len(rows))
    finally:
        db.close()

    # Summary
    df = pd.DataFrame(rows)
    for m in ["above_21ema", "above_200ema"]:
        sub = df[df["metric"] == m]
        if len(sub) > 0:
            logger.info("%s: %d days, avg=%.0f, min=%d, max=%d, total_stocks=%d",
                        m, len(sub), sub["count"].mean(), sub["count"].min(), sub["count"].max(), sub["total"].iloc[-1])


if __name__ == "__main__":
    symbols = fetch_nifty500()
    all_data = download_all(symbols)
    if not all_data:
        logger.error("No data. Aborting.")
        sys.exit(1)
    compute_and_store(all_data)
    logger.info("Done!")
