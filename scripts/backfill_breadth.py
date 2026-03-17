"""
Backfill BreadthDaily table with Nifty 500 EMA breadth counts.
Fetches OHLCV via yfinance, computes 21 EMA and 200 EMA,
stores daily aggregate counts of stocks above each EMA.

Usage: python3 scripts/backfill_breadth.py [--years 5]
"""

import argparse
import logging
import sys
import os

import pandas as pd
import yfinance as yf

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Base, BreadthDaily, SessionLocal, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backfill_breadth")

# ─── Nifty 500 constituents (top ~500 NSE symbols) ──────
# We fetch from NSE CSV or use a hardcoded fallback list
NIFTY500_URL = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"


def fetch_nifty500_symbols() -> list[str]:
    """Fetch Nifty 500 symbols from NSE. Falls back to Nifty 50+midcap if unavailable."""
    try:
        df = pd.read_csv(NIFTY500_URL)
        symbols = df["Symbol"].str.strip().tolist()
        logger.info("Fetched %d Nifty 500 symbols from NSE", len(symbols))
        return symbols
    except Exception as e:
        logger.warning("Failed to fetch Nifty 500 list: %s — using fallback", e)
        return _get_fallback_symbols()


def _get_fallback_symbols() -> list[str]:
    """Hardcoded top ~200 NSE symbols as fallback."""
    return [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR",
        "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK", "LT", "HCLTECH",
        "AXISBANK", "ASIANPAINT", "MARUTI", "SUNPHARMA", "TITAN",
        "BAJFINANCE", "DMART", "NTPC", "NESTLEIND", "ONGC", "TATAMOTORS",
        "M&M", "ULTRACEMCO", "POWERGRID", "WIPRO", "JSWSTEEL",
        "ADANIENT", "ADANIPORTS", "TATASTEEL", "HDFCLIFE", "BAJAJFINSV",
        "TECHM", "INDUSINDBK", "GRASIM", "CIPLA", "SBILIFE",
        "DIVISLAB", "DRREDDY", "BRITANNIA", "EICHERMOT", "APOLLOHOSP",
        "HINDALCO", "COALINDIA", "BPCL", "TATACONSUM", "HEROMOTOCO",
        "UPL", "DABUR", "PIDILITIND", "GODREJCP", "BERGEPAINT",
        "HAVELLS", "SIEMENS", "AMBUJACEM", "ACC", "DLF", "SRF",
        "MUTHOOTFIN", "TRENT", "INDIGO", "BANKBARODA", "PNB",
        "CANBK", "UNIONBANK", "IOB", "FEDERALBNK", "IDFCFIRSTB",
        "RBLBANK", "BANDHANBNK", "AUBANK", "CHOLAFIN", "BAJAJ-AUTO",
        "BIOCON", "LUPIN", "AUROPHARMA", "TORNTPHARM", "ALKEM",
        "LALPATHLAB", "METROPOLIS", "IPCALAB", "GLENMARK", "NATCOPHARMA",
        "PERSISTENT", "LTIM", "MPHASIS", "COFORGE", "LTTS",
        "TATAELXSI", "HAPPSTMNDS", "ZOMATO", "PAYTM", "NYKAA",
        "POLICYBZR", "DELHIVERY", "IRCTC", "PIIND", "ATUL",
        "DEEPAKNTR", "CLEAN", "FLUOROCHEM", "NAVINFLUOR",
        "LICI", "SBICARD", "MFSL", "ICICIGI", "ICICIPRULI",
        "HDFCAMC", "CAMS", "MCX", "BSE", "CDSL", "KPITTECH",
        "SONACOMS", "DIXON", "VOLTAS", "WHIRLPOOL", "CROMPTON",
        "BLUESTARCO", "POLYCAB", "KEI", "AFFLE", "ROUTE",
        "TATACHEM", "AARTI", "ALKYLAMINE", "GALAXYSURF",
        "MARICO", "COLPAL", "EMAMILTD", "TATAPOWER", "NHPC",
        "SJVN", "TORNTPOWER", "ADANIGREEN", "ADANIPOWER", "CESC",
        "HAL", "BEL", "BDL", "SOLARINDS", "COCHINSHIP",
        "MAZAGONDOCK", "GRINDWELL", "SCHAEFFLER", "TIMKEN",
        "SKFINDIA", "CUMMINSIND", "THERMAX", "ABB", "CGPOWER",
        "RECLTD", "PFC", "IREDA", "CANFINHOME", "LICHSGFIN",
        "MANAPPURAM", "MOTILALOFS", "IIFL", "ANGELONE",
        "MOTHERSON", "BALKRISIND", "MRF", "APOLLOTYRE", "CEATLTD",
        "JUBLFOOD", "DEVYANI", "SAPPHIRE", "PAGEIND", "RAYMOND",
        "OBEROIRLTY", "GODREJPROP", "PRESTIGE", "PHOENIXLTD",
        "SUNTV", "PVR", "PVRINOX", "ABCAPITAL", "ASTRAL",
        "SUPREMEIND", "FINOLEX", "RELAXO", "BATAINDIA", "CAMPUS",
        "EXIDEIND", "AMARAJABAT", "TVSMOTOR", "ESCORT", "ASHOKLEY",
        "BHARATFORG", "AIAENG", "CARBORUNIV", "NIACL", "GICRE",
        "STARHEALTH", "MAXHEALTH", "MEDANTA", "FORTIS", "RAINBOW",
        "KALYANKJIL", "TITAN", "RAJESHEXPO", "MAZDOCK", "MRPL",
        "IOC", "HINDPETRO", "GAIL", "PETRONET", "IGL",
        "MGL", "GSPL", "CONCOR", "RVNL", "IRFC",
    ]


def download_prices(symbols: list[str], years: int) -> pd.DataFrame:
    """Download OHLCV data for all symbols using yfinance bulk download."""
    tickers = [f"{s}.NS" for s in symbols]
    end_date = pd.Timestamp.now()
    start_date = end_date - pd.DateOffset(years=years, months=6)  # extra buffer for 200 EMA warmup

    logger.info("Downloading %d tickers from %s to %s...", len(tickers), start_date.date(), end_date.date())

    # Download in batches of 50 to avoid timeouts
    all_data = {}
    batch_size = 50
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        logger.info("  Batch %d/%d (%d tickers)...", i // batch_size + 1, (len(tickers) + batch_size - 1) // batch_size, len(batch))
        try:
            data = yf.download(batch, start=start_date, end=end_date, group_by="ticker", progress=False, threads=True)
            if isinstance(data.columns, pd.MultiIndex):
                for ticker in batch:
                    if ticker in data.columns.get_level_values(0):
                        df = data[ticker][["Close"]].dropna()
                        if len(df) > 0:
                            all_data[ticker] = df
            elif len(batch) == 1:
                df = data[["Close"]].dropna()
                if len(df) > 0:
                    all_data[batch[0]] = df
        except Exception as e:
            logger.warning("  Batch %d failed: %s", i // batch_size + 1, e)

    logger.info("Downloaded close prices for %d / %d tickers", len(all_data), len(tickers))
    return all_data


def compute_breadth(all_data: dict[str, pd.DataFrame], years: int) -> pd.DataFrame:
    """Compute daily breadth counts: stocks above 21 EMA and 200 EMA."""
    # Get date range
    all_dates = set()
    for df in all_data.values():
        all_dates.update(df.index)
    all_dates = sorted(all_dates)

    cutoff = pd.Timestamp.now() - pd.DateOffset(years=years)
    all_dates = [d for d in all_dates if d >= cutoff]

    logger.info("Computing EMA breadth for %d trading days...", len(all_dates))

    # Pre-compute EMAs for all stocks
    ema_data = {}
    for ticker, df in all_data.items():
        close = df["Close"].squeeze()
        if len(close) < 200:
            continue
        ema21 = close.ewm(span=21, adjust=False).mean()
        ema200 = close.ewm(span=200, adjust=False).mean()
        ema_data[ticker] = {"close": close, "ema21": ema21, "ema200": ema200}

    logger.info("Computed EMAs for %d stocks", len(ema_data))

    rows = []
    for dt in all_dates:
        above_21 = 0
        above_200 = 0
        total = 0

        for ticker, data in ema_data.items():
            if dt not in data["close"].index:
                continue
            total += 1
            price = data["close"].loc[dt]
            if pd.notna(price) and pd.notna(data["ema21"].get(dt)):
                if price > data["ema21"].loc[dt]:
                    above_21 += 1
            if pd.notna(price) and pd.notna(data["ema200"].get(dt)):
                if price > data["ema200"].loc[dt]:
                    above_200 += 1

        if total > 0:
            date_str = dt.strftime("%Y-%m-%d")
            rows.append({"date": date_str, "metric": "above_21ema", "count": above_21, "total": total})
            rows.append({"date": date_str, "metric": "above_200ema", "count": above_200, "total": total})

    return pd.DataFrame(rows)


def store_breadth(breadth_df: pd.DataFrame):
    """Store breadth data in BreadthDaily table."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Clear existing data
        db.query(BreadthDaily).delete()
        db.commit()

        # Bulk insert
        records = []
        for _, row in breadth_df.iterrows():
            records.append(BreadthDaily(
                date=row["date"],
                metric=row["metric"],
                count=int(row["count"]),
                total=int(row["total"]),
            ))

        batch_size = 1000
        for i in range(0, len(records), batch_size):
            db.add_all(records[i:i + batch_size])
            db.commit()

        logger.info("Stored %d breadth records in BreadthDaily table", len(records))
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Backfill BreadthDaily table")
    parser.add_argument("--years", type=int, default=5, help="Years of data to backfill (default: 5)")
    args = parser.parse_args()

    symbols = fetch_nifty500_symbols()
    all_data = download_prices(symbols, args.years)

    if not all_data:
        logger.error("No price data downloaded. Aborting.")
        sys.exit(1)

    breadth_df = compute_breadth(all_data, args.years)
    logger.info("Computed %d breadth rows", len(breadth_df))

    store_breadth(breadth_df)
    logger.info("Backfill complete!")

    # Print summary
    for metric in ["above_21ema", "above_200ema"]:
        subset = breadth_df[breadth_df["metric"] == metric]
        if len(subset) > 0:
            logger.info(
                "%s: %d days, avg count=%d, min=%d, max=%d (total=%d)",
                metric, len(subset),
                int(subset["count"].mean()), int(subset["count"].min()),
                int(subset["count"].max()), int(subset["total"].iloc[0]),
            )


if __name__ == "__main__":
    main()
