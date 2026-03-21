"""
Compass Lab — Historical Price Data Loader
Downloads and caches NIFTY + sector index prices from yfinance.
Stores as compressed numpy arrays for fast simulator consumption.

Data is stored in data/compass_history/ as .npz files.
One-time download, then incremental daily appends.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import numpy as np

logger = logging.getLogger("fie_v3.compass.history")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "compass_history")
PRICES_FILE = os.path.join(DATA_DIR, "sector_prices.npz")
META_FILE = os.path.join(DATA_DIR, "metadata.npz")


def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def download_historical_prices(
    start_date: str = "2005-01-01",
    end_date: Optional[str] = None,
) -> dict:
    """
    Download NIFTY + all sector index prices from yfinance.
    Returns dict with 'prices' (n_days × n_sectors), 'benchmark' (n_days,),
    'dates' (n_days,), 'sector_keys' (n_sectors,).
    """
    import yfinance as yf
    from index_constants import COMPASS_SECTOR_INDICES, NSE_TICKER_MAP

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    _ensure_data_dir()

    # Build list of sectors with yfinance symbols
    sector_keys = []
    yf_symbols = []
    display_names = []

    for key, name in COMPASS_SECTOR_INDICES:
        yf_sym = NSE_TICKER_MAP.get(key)
        if yf_sym:
            sector_keys.append(key)
            yf_symbols.append(yf_sym)
            display_names.append(name)

    # Add NIFTY as benchmark
    nifty_sym = NSE_TICKER_MAP["NIFTY"]

    # Download all at once (batch download is faster)
    all_symbols = [nifty_sym] + yf_symbols
    logger.info(
        "Downloading %d symbols from %s to %s...",
        len(all_symbols), start_date, end_date,
    )

    data = yf.download(
        all_symbols,
        start=start_date,
        end=end_date,
        auto_adjust=True,
        progress=False,
        threads=True,
    )

    if data.empty:
        logger.error("No data returned from yfinance")
        return {}

    # Extract Close prices
    if len(all_symbols) == 1:
        # Single symbol: data is a simple DataFrame
        close_df = data[["Close"]]
        close_df.columns = [all_symbols[0]]
    else:
        close_df = data["Close"] if "Close" in data.columns.get_level_values(0) else data.xs("Close", axis=1, level=0)

    # Fill forward missing data (holidays differ between indices)
    close_df = close_df.ffill()

    # Extract benchmark (NIFTY)
    benchmark_series = close_df[nifty_sym].values.astype(np.float64)

    # Extract sector prices
    sector_prices = np.full((len(close_df), len(sector_keys)), np.nan)
    valid_sectors = []
    valid_indices = []

    for i, (key, sym) in enumerate(zip(sector_keys, yf_symbols)):
        if sym in close_df.columns:
            col = close_df[sym].values.astype(np.float64)
            if not np.all(np.isnan(col)):
                sector_prices[:, len(valid_sectors)] = col
                valid_sectors.append(key)
                valid_indices.append(i)

    # Trim to valid sectors only
    sector_prices = sector_prices[:, :len(valid_sectors)]

    # Get dates
    dates = np.array([d.strftime("%Y-%m-%d") for d in close_df.index])

    # Remove rows where benchmark is NaN
    valid_rows = ~np.isnan(benchmark_series)
    benchmark_series = benchmark_series[valid_rows]
    sector_prices = sector_prices[valid_rows]
    dates = dates[valid_rows]

    # Replace remaining NaNs in sector prices with 0 (sectors that started later)
    sector_prices = np.nan_to_num(sector_prices, nan=0.0)

    result = {
        "prices": sector_prices,
        "benchmark": benchmark_series,
        "dates": dates,
        "sector_keys": valid_sectors,
    }

    logger.info(
        "Downloaded: %d days × %d sectors, date range %s to %s",
        len(dates), len(valid_sectors), dates[0], dates[-1],
    )

    return result


def save_historical_data(data: dict) -> str:
    """Save downloaded data to compressed numpy file."""
    _ensure_data_dir()

    np.savez_compressed(
        PRICES_FILE,
        prices=data["prices"],
        benchmark=data["benchmark"],
        dates=data["dates"],
        sector_keys=data["sector_keys"],
    )

    size_mb = os.path.getsize(PRICES_FILE) / 1024 / 1024
    logger.info("Saved historical data: %.1f MB at %s", size_mb, PRICES_FILE)
    return PRICES_FILE


def load_historical_data() -> Optional[dict]:
    """Load cached historical data from disk."""
    if not os.path.exists(PRICES_FILE):
        return None

    data = np.load(PRICES_FILE, allow_pickle=True)
    result = {
        "prices": data["prices"],
        "benchmark": data["benchmark"],
        "dates": data["dates"].astype(str),
        "sector_keys": list(data["sector_keys"].astype(str)),
    }
    logger.info(
        "Loaded historical data: %d days × %d sectors (%s to %s)",
        len(result["dates"]), result["prices"].shape[1],
        result["dates"][0], result["dates"][-1],
    )
    return result


def update_historical_data() -> Optional[dict]:
    """
    Incrementally update historical data with latest prices.
    Downloads only missing days since last data point.
    """
    existing = load_historical_data()
    if existing is None:
        # Full download
        data = download_historical_prices()
        if data:
            save_historical_data(data)
        return data

    last_date = existing["dates"][-1]
    today = datetime.now().strftime("%Y-%m-%d")

    if last_date >= today:
        logger.info("Historical data already up to date: %s", last_date)
        return existing

    # Download from last_date - 5 days (overlap for safety)
    start = (datetime.strptime(last_date, "%Y-%m-%d") - timedelta(days=5)).strftime("%Y-%m-%d")
    new_data = download_historical_prices(start_date=start, end_date=today)
    if not new_data or len(new_data["dates"]) == 0:
        return existing

    # Merge: find where new data starts after existing data ends
    existing_dates_set = set(existing["dates"])
    new_mask = np.array([d not in existing_dates_set for d in new_data["dates"]])

    if not np.any(new_mask):
        logger.info("No new dates to append")
        return existing

    # Map sectors between existing and new
    existing_sectors = list(existing["sector_keys"])
    new_sectors = list(new_data["sector_keys"])

    # Only keep sectors that exist in both
    common_sectors = [s for s in existing_sectors if s in new_sectors]
    if not common_sectors:
        logger.warning("No common sectors between existing and new data")
        return existing

    # Build aligned arrays
    existing_sector_idx = [existing_sectors.index(s) for s in common_sectors]
    new_sector_idx = [new_sectors.index(s) for s in common_sectors]

    existing_prices = existing["prices"][:, existing_sector_idx]
    new_prices_filtered = new_data["prices"][new_mask][:, new_sector_idx]
    new_benchmark_filtered = new_data["benchmark"][new_mask]
    new_dates_filtered = new_data["dates"][new_mask]

    merged = {
        "prices": np.vstack([existing_prices, new_prices_filtered]),
        "benchmark": np.concatenate([existing["benchmark"], new_benchmark_filtered]),
        "dates": np.concatenate([existing["dates"], new_dates_filtered]),
        "sector_keys": common_sectors,
    }

    save_historical_data(merged)
    logger.info(
        "Updated historical data: %d → %d days, %s to %s",
        len(existing["dates"]), len(merged["dates"]),
        merged["dates"][0], merged["dates"][-1],
    )
    return merged


def get_data_summary() -> dict:
    """Get summary of cached historical data without loading full arrays."""
    if not os.path.exists(PRICES_FILE):
        return {"status": "no_data"}

    data = load_historical_data()
    if data is None:
        return {"status": "load_error"}

    return {
        "status": "ready",
        "n_days": len(data["dates"]),
        "n_sectors": data["prices"].shape[1],
        "date_range": f"{data['dates'][0]} to {data['dates'][-1]}",
        "sectors": data["sector_keys"],
        "file_size_mb": round(os.path.getsize(PRICES_FILE) / 1024 / 1024, 1),
    }
