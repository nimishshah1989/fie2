#!/usr/bin/env python3
"""
NSE Historical Data Backfill Script
====================================
Run this LOCALLY from an India IP to fetch 1Y historical index data
from NSE and upload to your Railway server.

Usage:
    python3 backfill_nse.py

This will:
1. Fetch all 135+ NSE index names from nsetools
2. For each index, fetch 1Y daily history from NSE historical API
3. Upload all data to Railway via POST /api/indices/bulk-upload

Requirements: pip install requests nsetools
"""

import requests
import time
import json
import sys
from datetime import datetime, timedelta, date
from urllib.parse import quote

# ─── Configuration ──────────────────────────────────────
RAILWAY_URL = "https://fie2-production.up.railway.app"
UPLOAD_ENDPOINT = f"{RAILWAY_URL}/api/indices/bulk-upload"
DAYS_OF_HISTORY = 365  # 1 year

# ─── NSE Session Handling ───────────────────────────────

_NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

_NSE_API_HEADERS = {
    **_NSE_HEADERS,
    "referer": "https://www.nseindia.com/",
    "Accept": "application/json, text/html, */*",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
}


def _safe_float(val):
    if val is None:
        return None
    try:
        if isinstance(val, str):
            val = val.replace(",", "").strip()
            if val in ("", "-", "\u2014"):
                return None
        return float(val)
    except (ValueError, TypeError):
        return None


def create_nse_session():
    """Create a requests session with NSE cookies."""
    session = requests.Session()
    print("  Creating NSE session...")
    resp = session.get("https://www.nseindia.com", headers=_NSE_HEADERS, timeout=10)
    print(f"  Session created (cookies: {len(session.cookies)})")
    return session


def get_all_nse_indices():
    """Get all NSE index names from nsetools."""
    from nsetools import Nse
    nse = Nse()
    quotes = nse.get_all_index_quote()
    if not quotes:
        print("ERROR: nsetools returned no data")
        sys.exit(1)

    indices = []
    for q in quotes:
        nse_name = str(q.get("index", "")).strip()
        if nse_name:
            # Build internal key using the same reverse map logic as price_service.py
            internal_key = nse_name  # default: use nse_name as-is
            # Common mappings
            REVERSE_MAP = {
                "NIFTY 50": "NIFTY",
                "NIFTY 500": "NIFTY500",
                "NIFTY NEXT 50": "NIFTYNEXT50",
                "NIFTY MIDCAP 150": "NIFTYMIDCAP",
                "NIFTY SMLCAP 250": "NIFTYSMALLCAP",
                "NIFTY BANK": "BANKNIFTY",
                "NIFTY IT": "NIFTYIT",
                "NIFTY PHARMA": "NIFTYPHARMA",
                "NIFTY FMCG": "NIFTYFMCG",
                "NIFTY AUTO": "NIFTYAUTO",
                "NIFTY METAL": "NIFTYMETAL",
                "NIFTY REALTY": "NIFTYREALTY",
                "NIFTY ENERGY": "NIFTYENERGY",
                "NIFTY PSU BANK": "NIFTYPSUBANK",
                "NIFTY PVT BANK": "NIFTYPVTBANK",
                "NIFTY MIDCAP 50": "NIFTYMIDCAP50",
                "NIFTY INFRA": "NIFTYINFRA",
                "NIFTY MEDIA": "NIFTYMEDIA",
                "NIFTY FIN SERVICE": "FINNIFTY",
                "NIFTY HEALTHCARE": "NIFTYHEALTHCARE",
                "NIFTY CONSR DURBL": "NIFTYCONSUMER",
                "NIFTY COMMODITIES": "NIFTYCOMMODITIES",
            }
            internal_key = REVERSE_MAP.get(nse_name.upper(), nse_name)
            indices.append({"nse_name": nse_name, "internal_key": internal_key})

    return indices


def _parse_nse_rows(data_items):
    """Parse NSE API response items into rows."""
    rows = []
    for item in data_items:
        row = {"open": None, "high": None, "low": None, "close": None, "volume": None, "date": None}
        for k, v in item.items():
            ku = k.upper()
            if "CLOSE" in ku and "INDEX" in ku:
                row["close"] = _safe_float(v)
            elif "OPEN" in ku and "INDEX" in ku:
                row["open"] = _safe_float(v)
            elif "HIGH" in ku and "INDEX" in ku:
                row["high"] = _safe_float(v)
            elif "LOW" in ku and "INDEX" in ku:
                row["low"] = _safe_float(v)
            elif "TIMESTAMP" in ku and not ku.startswith("HI"):
                raw = str(v).strip()
                # NSE returns dates like "12-JUN-2025"
                for fmt in ("%d-%b-%Y", "%d %b %Y", "%d-%m-%Y", "%Y-%m-%d"):
                    try:
                        row["date"] = datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        continue
            elif "TRADED" in ku:
                row["volume"] = _safe_float(v)

        if row["close"] and row["date"]:
            rows.append(row)
    return rows


def fetch_index_history(session, nse_name, days=365):
    """Fetch historical daily data for one NSE index, chunked into 90-day segments."""
    end = date.today()
    start = end - timedelta(days=days)

    all_rows = []
    seen_dates = set()
    chunk_start = start

    try:
        while chunk_start < end:
            chunk_end = min(chunk_start + timedelta(days=89), end)
            from_str = chunk_start.strftime("%d-%m-%Y")
            to_str = chunk_end.strftime("%d-%m-%Y")

            encoded = quote(nse_name)
            url = (
                f"https://www.nseindia.com/api/historicalOR/indicesHistory"
                f"?indexType={encoded}&from={from_str}&to={to_str}"
            )

            resp = session.get(url, headers=_NSE_API_HEADERS, timeout=15)
            if resp.status_code != 200:
                chunk_start = chunk_end + timedelta(days=1)
                continue

            data_items = resp.json().get("data", [])
            if data_items:
                rows = _parse_nse_rows(data_items)
                for r in rows:
                    if r["date"] not in seen_dates:
                        all_rows.append(r)
                        seen_dates.add(r["date"])

            chunk_start = chunk_end + timedelta(days=1)
            time.sleep(0.15)  # rate limit between chunks

        if all_rows:
            return all_rows, None
        else:
            return None, "empty data across all chunks"

    except Exception as e:
        return None, str(e)


def upload_to_railway(all_data):
    """Upload all historical data to Railway server."""
    print(f"\nUploading {sum(len(v) for v in all_data.values())} records "
          f"for {len(all_data)} indices to Railway...")

    try:
        resp = requests.post(
            UPLOAD_ENDPOINT,
            json={"data": all_data},
            timeout=60,
        )
        if resp.status_code == 200:
            result = resp.json()
            print(f"  Upload SUCCESS: {result.get('stored', '?')} records stored, "
                  f"{result.get('indices', '?')} indices")
            return True
        else:
            print(f"  Upload FAILED: HTTP {resp.status_code}")
            print(f"  Response: {resp.text[:500]}")
            return False
    except Exception as e:
        print(f"  Upload ERROR: {e}")
        return False


def main():
    print("=" * 60)
    print("NSE Historical Data Backfill")
    print(f"Target: {RAILWAY_URL}")
    print(f"Period: {DAYS_OF_HISTORY} days")
    print("=" * 60)

    # Step 1: Get all NSE indices
    print("\n[1/3] Fetching NSE index list from nsetools...")
    indices = get_all_nse_indices()
    print(f"  Found {len(indices)} indices")

    # Step 2: Fetch historical data for each
    print(f"\n[2/3] Fetching {DAYS_OF_HISTORY}-day history from NSE API...")
    session = create_nse_session()
    all_data = {}
    success = 0
    failed = 0

    for i, idx in enumerate(indices):
        nse_name = idx["nse_name"]
        internal_key = idx["internal_key"]

        rows, error = fetch_index_history(session, nse_name, DAYS_OF_HISTORY)

        if rows:
            all_data[internal_key] = rows
            success += 1
            print(f"  [{i+1}/{len(indices)}] {nse_name} -> {internal_key}: {len(rows)} days")
        else:
            failed += 1
            print(f"  [{i+1}/{len(indices)}] {nse_name}: FAILED ({error})")

        # Rate limit
        time.sleep(0.3)

        # Re-establish session every 25 requests
        if (i + 1) % 25 == 0:
            session = create_nse_session()
            time.sleep(1)

    print(f"\n  Results: {success} succeeded, {failed} failed out of {len(indices)}")

    if not all_data:
        print("\nNo data fetched! Check your internet connection and IP (must be India).")
        sys.exit(1)

    # Step 3: Upload to Railway
    print(f"\n[3/3] Uploading to Railway...")
    ok = upload_to_railway(all_data)

    if ok:
        print("\n" + "=" * 60)
        print("DONE! 3M/6M data should now be available on the pulse page.")
        print("=" * 60)
    else:
        # Save locally as backup
        backup_file = "nse_historical_backup.json"
        with open(backup_file, "w") as f:
            json.dump(all_data, f)
        print(f"\nUpload failed. Data saved to {backup_file}")
        print(f"You can retry with: curl -X POST {UPLOAD_ENDPOINT} "
              f"-H 'Content-Type: application/json' -d @{backup_file}")


if __name__ == "__main__":
    main()
