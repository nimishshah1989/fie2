"""
FIE — Price Service
Robust live price fetching for NSE/BSE indices and Indian market instruments.
Primary: nsetools for NSE indices (135+ indices directly from NSE).
Historical: NSE website API for index history (all NSE indices).
Fallback: yfinance for individual stocks, BSE, commodities, currencies.
"""

import logging
import time
from datetime import date as date_type
from datetime import datetime, timedelta
from urllib.parse import quote

logger = logging.getLogger(__name__)

# ─── Yahoo Finance Ticker Map ──────────────────────────
NSE_TICKER_MAP = {
    # ─── NSE Broad Market ───
    "NIFTY":            "^NSEI",
    "NIFTY50":          "^NSEI",
    "NIFTY100":         "^CNX100",
    "NIFTY200":         "^CNX200",
    "NIFTY500":         "^CRSLDX",
    "NIFTYNEXT50":      "^NSMIDCP",
    "NIFTYMIDCAP":      "^NSEMDCP50",
    "NIFTYMIDCAP50":    "^NSEMDCP50",
    "MIDCPNIFTY":       "^NSEMDCP50",
    "NIFTYSMALLCAP":    "^CNXSC",
    # ─── NSE Sectoral ───
    "BANKNIFTY":        "^NSEBANK",
    "NIFTYBANK":        "^NSEBANK",
    "NIFTYIT":          "^CNXIT",
    "NIFTYPHARMA":      "^CNXPHARMA",
    "NIFTYFMCG":        "^CNXFMCG",
    "NIFTYAUTO":        "^CNXAUTO",
    "NIFTYMETAL":       "^CNXMETAL",
    "NIFTYREALTY":      "^CNXREALTY",
    "NIFTYENERGY":      "^CNXENERGY",
    "NIFTYPSUBANK":     "^CNXPSUBANK",
    "NIFTYPVTBANK":     "NIFTY_PVT_BANK.NS",
    "NIFTYINFRA":       "^CNXINFRA",
    "NIFTYMEDIA":       "^CNXMEDIA",
    "NIFTYFINSERVICE":  "NIFTY_FIN_SERVICE.NS",
    "FINNIFTY":         "NIFTY_FIN_SERVICE.NS",
    "NIFTYMNC":         "^CNXMNC",
    "NIFTYPSE":         "^CNXPSE",
    "NIFTYSERVICE":     "^CNXSERVICE",
    "NIFTYCONSUMPTION": "^CNXCONSUM",
    "NIFTYCOMMODITIES": "^CNXCMDT",
    "NIFTYDIVOPPS50":   "^CNXDIVOP",
    # ─── NSE Thematic (live price, limited history) ───
    "NIFTYCPSE":        "NIFTY_CPSE.NS",
    "NIFTYHEALTHCARE":  "NIFTY_HEALTHCARE.NS",
    "NIFTYCONSUMER":    "NIFTY_CONSR_DURBL.NS",
    # ─── India VIX ───
    "INDIAVIX":         "^INDIAVIX",
    # ─── BSE ───
    "SENSEX":           "^BSESN",
    "BSE500":           "BSE-500.BO",
    "BSEIT":            "BSE-IT.BO",
    "BSEBANK":          "BSE-BANKEX.BO",
    # ─── Commodities ───
    "GOLD":             "GC=F",
    "SILVER":           "SI=F",
    "CRUDEOIL":         "CL=F",
    "CRUDE":            "CL=F",
    "NATURALGAS":       "NG=F",
    "COPPER":           "HG=F",
    # ─── Currency ───
    "USDINR":           "USDINR=X",
    "EURINR":           "EURINR=X",
    "GBPINR":           "GBPINR=X",
}

FALLBACK_MAP = {
    "^NSEI":    ["NIFTY_50.NS"],
    "^NSEBANK": ["BANKBEES.NS"],
    "^CNXIT":   ["NIFTYIT.NS"],
    "^BSESN":   ["^BSESN"],
}

# ─── NSE Index Keys for EOD Fetch ────────────────────────
# All tracked instruments for yfinance backfill + pulse page display
NSE_INDEX_KEYS = [
    # Broad Market
    "NIFTY", "NIFTY100", "NIFTY200", "NIFTY500", "NIFTYNEXT50",
    "MIDCPNIFTY", "NIFTYMIDCAP100", "NIFTYMIDCAP150",
    "NIFTYSMALLCAP50", "NIFTYSMALLCAP100", "NIFTYSMALLCAP250",
    "NIFTYMIDSMALL400", "NIFTYLARGEMIDCAP250", "NIFTYMICROCAP250",
    "NIFTYTOTALMARKET", "NIFTY500MULTICAP",
    # Sectoral
    "BANKNIFTY", "NIFTYIT", "NIFTYPHARMA", "NIFTYFMCG", "NIFTYAUTO",
    "NIFTYMETAL", "NIFTYREALTY", "NIFTYENERGY", "NIFTYPSUBANK", "NIFTYPVTBANK",
    "NIFTYINFRA", "NIFTYMEDIA", "FINNIFTY", "NIFTYFINSERVICE",
    "NIFTYMNC", "NIFTYPSE", "NIFTYSERVICE",
    "NIFTYCONSUMERDURABLES", "NIFTYOILGAS", "NIFTYCHEMICALS",
    # Thematic
    "NIFTYHEALTHCARE", "NIFTYCONSUMPTION", "NIFTYCOMMODITIES",
    "NIFTYINDIAMFG", "NIFTYINDIADEFENCE", "NIFTYINDIGITAL",
    "NIFTYCPSE", "NIFTY100QUALITY30", "NIFTYDIVOPPS50",
    # BSE
    "SENSEX", "BSE500",
    # Commodities & Currency
    "GOLD", "SILVER", "CRUDEOIL", "COPPER", "USDINR",
]

# Category map for pulse page tab grouping
NSE_INDEX_CATEGORIES: dict = {
    # Broad Market
    "NIFTY": "broad", "NIFTY100": "broad", "NIFTY200": "broad",
    "NIFTY500": "broad", "NIFTYNEXT50": "broad", "MIDCPNIFTY": "broad",
    "NIFTYMIDCAP100": "broad", "NIFTYMIDCAP150": "broad",
    "NIFTYSMALLCAP50": "broad", "NIFTYSMALLCAP100": "broad",
    "NIFTYSMALLCAP250": "broad", "NIFTYMIDSMALL400": "broad",
    "NIFTYLARGEMIDCAP250": "broad", "NIFTYMICROCAP250": "broad",
    "NIFTYTOTALMARKET": "broad", "NIFTY500MULTICAP": "broad",
    # Sectoral
    "BANKNIFTY": "sectoral", "NIFTYIT": "sectoral", "NIFTYPHARMA": "sectoral",
    "NIFTYFMCG": "sectoral", "NIFTYAUTO": "sectoral", "NIFTYMETAL": "sectoral",
    "NIFTYREALTY": "sectoral", "NIFTYENERGY": "sectoral", "NIFTYPSUBANK": "sectoral",
    "NIFTYPVTBANK": "sectoral", "NIFTYINFRA": "sectoral", "NIFTYMEDIA": "sectoral",
    "FINNIFTY": "sectoral", "NIFTYFINSERVICE": "sectoral",
    "NIFTYMNC": "sectoral", "NIFTYPSE": "sectoral", "NIFTYSERVICE": "sectoral",
    "NIFTYCONSUMERDURABLES": "sectoral", "NIFTYOILGAS": "sectoral",
    "NIFTYCHEMICALS": "sectoral",
    # Thematic
    "NIFTYHEALTHCARE": "thematic", "NIFTYCONSUMPTION": "thematic",
    "NIFTYCOMMODITIES": "thematic", "NIFTYINDIAMFG": "thematic",
    "NIFTYINDIADEFENCE": "thematic", "NIFTYINDIGITAL": "thematic",
    "NIFTYCPSE": "thematic", "NIFTY100QUALITY30": "thematic", "NIFTYDIVOPPS50": "thematic",
    # BSE & Global
    "SENSEX": "global", "BSE500": "global",
    "GOLD": "global", "SILVER": "global", "CRUDEOIL": "global",
    "COPPER": "global", "USDINR": "global",
}

# Non-nsetools instruments — served from DB prices on pulse page (BSE & Global tab)
NON_NSETOOLS_KEYS = ["SENSEX", "BSE500", "GOLD", "SILVER", "CRUDEOIL", "COPPER", "USDINR"]

# ─── ETF Universe for EOD Tracking ──────────────────────
NSE_ETF_UNIVERSE = {
    # Broad Market
    "NIFTYBEES": "NIFTYBEES.NS",
    "JUNIORBEES": "JUNIORBEES.NS",
    "BANKBEES": "BANKBEES.NS",
    # Sector
    "ITBEES": "ITBEES.NS",
    "PHARMABEES": "PHARMABEES.NS",
    "PSUBNKBEES": "PSUBNKBEES.NS",
    # Commodity
    "GOLDBEES": "GOLDBEES.NS",
    "SILVERBEES": "SILVERBEES.NS",
    # Portfolio-held ETFs
    "CPSEETF": "CPSEETF.NS",
    "LIQUIDCASE": "LIQUIDCASE.NS",
    "SENSEXETF": "SENSEXIETF.NS",
    "MASPTOP50": "MASPTOP50.NS",
    "NETFMID150": "MID150BEES.NS",
    "FMCGIETF": "FMCGIETF.NS",
    "OILIETF": "OILIETF.NS",
    "NETFAUTO": "NETFAUTO.NS",
    "METALIETF": "METALIETF.NS",
}

# ─── NSE Display Name Map (nsetools returns these names) ────
# Maps our internal key -> NSE display name as returned by nsetools
NSE_DISPLAY_MAP = {
    # ── Broad Market ──
    "NIFTY":                "NIFTY 50",
    "NIFTY100":             "NIFTY 100",
    "NIFTY200":             "NIFTY 200",
    "NIFTY500":             "NIFTY 500",
    "NIFTYNEXT50":          "NIFTY NEXT 50",
    "MIDCPNIFTY":           "NIFTY MIDCAP 50",
    "NIFTYMIDCAP100":       "NIFTY MIDCAP 100",
    "NIFTYMIDCAP150":       "NIFTY MIDCAP 150",
    "NIFTYSMALLCAP":        "NIFTY SMALLCAP 250",
    "NIFTYSMALLCAP50":      "NIFTY SMALLCAP 50",
    "NIFTYSMALLCAP100":     "NIFTY SMALLCAP 100",
    "NIFTYSMALLCAP250":     "NIFTY SMALLCAP 250",
    "NIFTYMIDSMALL400":     "NIFTY MIDSMALLCAP 400",
    "NIFTYLARGEMIDCAP250":  "NIFTY LARGEMIDCAP 250",
    "NIFTYMICROCAP250":     "NIFTY MICROCAP 250",
    "NIFTYTOTALMARKET":     "NIFTY TOTAL MARKET",
    "NIFTY500MULTICAP":     "NIFTY500 MULTICAP 50:25:25",
    # ── Sectoral ──
    "BANKNIFTY":            "NIFTY BANK",
    "NIFTYIT":              "NIFTY IT",
    "NIFTYPHARMA":          "NIFTY PHARMA",
    "NIFTYFMCG":            "NIFTY FMCG",
    "NIFTYAUTO":            "NIFTY AUTO",
    "NIFTYMETAL":           "NIFTY METAL",
    "NIFTYREALTY":          "NIFTY REALTY",
    "NIFTYENERGY":          "NIFTY ENERGY",
    "NIFTYPSUBANK":         "NIFTY PSU BANK",
    "NIFTYPVTBANK":         "NIFTY PRIVATE BANK",
    "NIFTYINFRA":           "NIFTY INFRASTRUCTURE",
    "NIFTYMEDIA":           "NIFTY MEDIA",
    "FINNIFTY":             "NIFTY FINANCIAL SERVICES",
    "NIFTYFINSERVICE":      "NIFTY FINANCIAL SERVICES 25/50",
    "NIFTYMNC":             "NIFTY MNC",
    "NIFTYPSE":             "NIFTY PSE",
    "NIFTYSERVICE":         "NIFTY SERVICES SECTOR",
    "NIFTYCONSUMERDURABLES": "NIFTY CONSUMER DURABLES",
    "NIFTYOILGAS":          "NIFTY OIL & GAS",
    "NIFTYCHEMICALS":       "NIFTY CHEMICALS",
    # ── Thematic ──
    "NIFTYHEALTHCARE":      "NIFTY HEALTHCARE INDEX",
    "NIFTYCONSUMPTION":     "NIFTY INDIA CONSUMPTION",
    "NIFTYCOMMODITIES":     "NIFTY COMMODITIES",
    "NIFTYINDIAMFG":        "NIFTY INDIA MANUFACTURING",
    "NIFTYINDIADEFENCE":    "NIFTY INDIA DEFENCE",
    "NIFTYINDIGITAL":       "NIFTY INDIA DIGITAL",
    "NIFTYCPSE":            "NIFTY CPSE",
    "NIFTY100QUALITY30":    "NIFTY100 QUALITY 30",
    "NIFTYDIVOPPS50":       "NIFTY DIVIDEND OPPORTUNITIES 50",
    "INDIAVIX":             "INDIA VIX",
    # ── BSE & Global ──
    "SENSEX":               "SENSEX",
    "BSE500":               "BSE 500",
    "GOLD":                 "Gold (USD)",
    "SILVER":               "Silver (USD)",
    "CRUDEOIL":             "Crude Oil (USD)",
    "COPPER":               "Copper (USD)",
    "USDINR":               "USD/INR",
}

# Reverse map: NSE display name -> our internal key
_NSE_REVERSE_MAP = {}
for _k, _v in NSE_DISPLAY_MAP.items():
    _NSE_REVERSE_MAP[_v.upper()] = _k


# ─── Sector Indices for Recommendation Engine ────
# (internal_key, NSE display name for API calls)
SECTOR_INDICES_FOR_RECO = [
    ("BANKNIFTY", "NIFTY BANK"),
    ("NIFTYIT", "NIFTY IT"),
    ("NIFTYPHARMA", "NIFTY PHARMA"),
    ("NIFTYFMCG", "NIFTY FMCG"),
    ("NIFTYAUTO", "NIFTY AUTO"),
    ("NIFTYMETAL", "NIFTY METAL"),
    ("NIFTYREALTY", "NIFTY REALTY"),
    ("NIFTYENERGY", "NIFTY ENERGY"),
    ("NIFTYPSUBANK", "NIFTY PSU BANK"),
    ("NIFTYPVTBANK", "NIFTY PRIVATE BANK"),
    ("NIFTYINFRA", "NIFTY INFRASTRUCTURE"),
    ("NIFTYMEDIA", "NIFTY MEDIA"),
    ("FINNIFTY", "NIFTY FINANCIAL SERVICES"),
    ("NIFTYHEALTHCARE", "NIFTY HEALTHCARE INDEX"),
    ("NIFTYCONSUMER", "NIFTY CONSUMER DURABLES"),
]

SECTOR_ETF_MAP = {
    "BANKNIFTY": ["BANKBEES"],
    "NIFTYIT": ["ITBEES"],
    "NIFTYPHARMA": ["PHARMABEES"],
    "NIFTYPSUBANK": ["PSUBNKBEES"],
    "NIFTYFMCG": ["FMCGIETF"],
    "NIFTYMETAL": ["METALIETF"],
    "NIFTYAUTO": ["NETFAUTO"],
}


# ─── NSE Historical API (direct HTTP, no nselib dependency) ────

def _nse_session():
    """Create an HTTP session with NSE cookies for authenticated API access."""
    import requests
    session = requests.Session()
    _headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        session.get("https://www.nseindia.com", headers=_headers, timeout=10)
    except Exception as e:
        logger.warning("NSE session init failed: %s", e)
    return session, _headers


def _parse_nse_history_response(data_items):
    """Parse NSE historical API response items into standardized rows."""
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
                raw_date = str(v).strip()
                # NSE returns dates like "12-JUN-2025" (dd-MMM-YYYY)
                for fmt in ("%d-%b-%Y", "%d %b %Y", "%d-%m-%Y", "%Y-%m-%d"):
                    try:
                        row["date"] = datetime.strptime(raw_date, fmt).strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        continue
            elif "TRADED" in ku:
                row["volume"] = _safe_float(v)

        if row["close"] and row["date"]:
            rows.append(row)
    return rows


def fetch_nse_index_history(nse_display_name, days=365, _session=None):
    """
    Fetch historical daily data for a single NSE index from NSE's website API.
    NSE API returns max ~70-90 days per request, so we chunk into 90-day segments.
    nse_display_name: e.g., "NIFTY 50", "NIFTY BANK"
    days: number of days of history to fetch (default 365)
    Returns [{date, open, high, low, close, volume}, ...]
    """
    try:
        if _session:
            session, base_headers = _session
        else:
            session, base_headers = _nse_session()

        api_headers = {
            **base_headers,
            "referer": "https://www.nseindia.com/",
            "Accept": "application/json, text/html, */*",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
        }

        encoded_name = quote(nse_display_name)
        all_rows = []
        seen_dates = set()

        # Chunk into 90-day segments (NSE API limits per request)
        end = date_type.today()
        start = end - timedelta(days=days)
        chunk_start = start

        while chunk_start < end:
            chunk_end = min(chunk_start + timedelta(days=89), end)
            from_str = chunk_start.strftime("%d-%m-%Y")
            to_str = chunk_end.strftime("%d-%m-%Y")

            url = (
                f"https://www.nseindia.com/api/historicalOR/indicesHistory"
                f"?indexType={encoded_name}&from={from_str}&to={to_str}"
            )

            resp = session.get(url, headers=api_headers, timeout=15)
            if resp.status_code != 200:
                logger.debug("NSE history chunk returned %d for %s (%s-%s)",
                             resp.status_code, nse_display_name, from_str, to_str)
                chunk_start = chunk_end + timedelta(days=1)
                continue

            resp_json = resp.json()
            data_items = resp_json.get("data", [])

            if data_items:
                rows = _parse_nse_history_response(data_items)
                for r in rows:
                    if r["date"] not in seen_dates:
                        all_rows.append(r)
                        seen_dates.add(r["date"])

            chunk_start = chunk_end + timedelta(days=1)
            time.sleep(0.2)  # small delay between chunks

        if all_rows:
            logger.info("NSE history: %s — %d days fetched", nse_display_name, len(all_rows))
        else:
            logger.debug("NSE history: %s — 0 days (API returned no data)", nse_display_name)

        return all_rows

    except Exception as e:
        logger.debug("NSE history fetch failed for %s: %s", nse_display_name, e)
        return []


def _safe_float(val):
    """Safely convert a value to float (handles comma-formatted strings)."""
    if val is None:
        return None
    try:
        if isinstance(val, str):
            val = val.replace(",", "").strip()
            if val in ("", "-", "—"):
                return None
        return float(val)
    except (ValueError, TypeError):
        return None


def fetch_live_indices():
    """
    Fetch real-time live index data from NSE using nsetools.
    Returns list of dicts, one per index, with standardized keys.
    Each dict: {index_name, nse_name, last, open, high, low, previousClose,
                variation, percentChange, yearHigh, yearLow,
                perChange365d, perChange30d, oneWeekAgoVal, oneMonthAgoVal, oneYearAgoVal}
    """
    try:
        from nsetools import Nse
        nse = Nse()
        all_quotes = nse.get_all_index_quote()
        if not all_quotes:
            logger.warning("nsetools returned empty list")
            return []

        results = []
        for q in all_quotes:
            nse_name = str(q.get("index", "")).strip()
            internal_key = _NSE_REVERSE_MAP.get(nse_name.upper(), nse_name)

            results.append({
                "index_name":     internal_key,
                "nse_name":       nse_name,
                "last":           _safe_float(q.get("last")),
                "open":           _safe_float(q.get("open")),
                "high":           _safe_float(q.get("high")),
                "low":            _safe_float(q.get("low")),
                "previousClose":  _safe_float(q.get("previousClose")),
                "variation":      _safe_float(q.get("variation")),
                "percentChange":  _safe_float(q.get("percentChange")),
                "yearHigh":       _safe_float(q.get("yearHigh")),
                "yearLow":        _safe_float(q.get("yearLow")),
                "perChange365d":  _safe_float(q.get("perChange365d")),
                "perChange30d":   _safe_float(q.get("perChange30d")),
                "oneWeekAgoVal":  _safe_float(q.get("oneWeekAgoVal")),
                "oneMonthAgoVal": _safe_float(q.get("oneMonthAgoVal")),
                "oneYearAgoVal":  _safe_float(q.get("oneYearAgoVal")),
                "pe":             _safe_float(q.get("pe")),
                "pb":             _safe_float(q.get("pb")),
                "advances":       q.get("advances"),
                "declines":       q.get("declines"),
            })

        logger.info("nsetools: fetched %d live indices", len(results))
        return results

    except Exception as e:
        logger.error("nsetools fetch_live_indices failed: %s", e)
        return []


def normalize_ticker(ticker: str) -> str:
    """Convert internal ticker to Yahoo Finance symbol."""
    if not ticker:
        return ""
    clean = ticker.upper().strip()
    if ":" in clean:
        clean = clean.split(":")[-1].strip()
    if clean in NSE_TICKER_MAP:
        return NSE_TICKER_MAP[clean]
    if clean.startswith("^") or "=" in clean or clean.endswith("=F"):
        return clean
    if not clean.endswith(".NS") and not clean.endswith(".BO"):
        return f"{clean}.NS"
    return clean

# Alias for server.py compatibility
normalize_ticker_for_yfinance = normalize_ticker


def _fetch_yfinance(yf_symbol: str, period: str = "5d") -> dict:
    """Core price fetch from Yahoo Finance."""
    try:
        import yfinance as yf
        hist = yf.Ticker(yf_symbol).history(period=period)
        if hist is None or hist.empty:
            return {"current_price": None}
        hist = hist.dropna(subset=["Close"])
        if hist.empty:
            return {"current_price": None}
        latest = hist.iloc[-1]
        curr = float(latest["Close"])
        prev = float(hist.iloc[-2]["Close"]) if len(hist) > 1 else None
        chg  = round(((curr - prev) / prev) * 100, 2) if prev else None
        return {
            "current_price": curr,
            "high":          float(latest["High"]) if "High" in latest else None,
            "low":           float(latest["Low"])  if "Low"  in latest else None,
            "volume":        float(latest["Volume"]) if "Volume" in latest else None,
            "prev_close":    prev,
            "change_pct":    chg,
            "open":          float(latest["Open"]) if "Open" in latest else None,
        }
    except Exception as e:
        logger.debug(f"yfinance error for {yf_symbol}: {e}")
        return {"current_price": None, "error": str(e)}


def get_live_price(ticker: str) -> dict:
    """
    Fetch latest price with multiple fallback strategies.
    1. yfinance primary symbol
    2. yfinance fallback symbols
    3. NSE/BSE swap (.NS <-> .BO)
    """
    yf_symbol = normalize_ticker(ticker)
    if not yf_symbol:
        return {"current_price": None, "error": "Empty ticker"}

    result = _fetch_yfinance(yf_symbol)
    if result.get("current_price"):
        return result

    if yf_symbol in FALLBACK_MAP:
        for alt in FALLBACK_MAP[yf_symbol]:
            result = _fetch_yfinance(alt)
            if result.get("current_price"):
                return result

    if yf_symbol.endswith(".NS"):
        result = _fetch_yfinance(yf_symbol.replace(".NS", ".BO"))
        if result.get("current_price"):
            return result
    elif yf_symbol.endswith(".BO"):
        result = _fetch_yfinance(yf_symbol.replace(".BO", ".NS"))
        if result.get("current_price"):
            return result

    logger.warning(f"No price data for {ticker} (tried: {yf_symbol})")
    return {"current_price": None, "error": f"No data for {ticker}"}


def get_batch_prices(tickers: list) -> dict:
    """Fetch prices for multiple tickers efficiently via yfinance batch download."""
    if not tickers:
        return {}
    try:
        import yfinance as yf
        symbols = {t: normalize_ticker(t) for t in tickers}
        unique_syms = list(set(symbols.values()))
        raw = yf.download(
            tickers=" ".join(unique_syms),
            period="5d",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        results = {}
        for ticker, sym in symbols.items():
            try:
                closes = raw["Close"][sym].dropna() if len(unique_syms) > 1 else raw["Close"].dropna()
                if closes.empty:
                    results[ticker] = {"current_price": None}
                    continue
                curr = float(closes.iloc[-1])
                prev = float(closes.iloc[-2]) if len(closes) > 1 else None
                results[ticker] = {
                    "current_price": curr,
                    "prev_close": prev,
                    "change_pct": round(((curr - prev) / prev) * 100, 2) if prev else None,
                }
            except:
                results[ticker] = {"current_price": None}
        return results
    except Exception as e:
        logger.error(f"Batch price fetch error: {e}")
        return {t: get_live_price(t) for t in tickers}


def get_historical_price(ticker: str, target_date: datetime):
    """Get closing price for a ticker on or near a specific date."""
    yf_symbol = normalize_ticker(ticker)
    if not yf_symbol:
        return None
    try:
        import yfinance as yf
        start = target_date - timedelta(days=5)
        end   = target_date + timedelta(days=2)
        hist = yf.Ticker(yf_symbol).history(
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d")
        )
        if hist.empty:
            return None
        hist.index = hist.index.tz_localize(None) if hist.index.tzinfo else hist.index
        target_naive = target_date.replace(tzinfo=None)
        diffs = abs(hist.index - target_naive)
        return float(hist.iloc[diffs.argmin()]["Close"])
    except Exception as e:
        logger.debug(f"Historical price error for {ticker} on {target_date}: {e}")
        return None


def compute_returns(alert_price: float, current_price: float, direction: str = "BULLISH") -> dict:
    """Compute return metrics for an alert position."""
    if not alert_price or not current_price or alert_price <= 0:
        return {"return_pct": None, "return_absolute": None}
    mult = -1.0 if direction == "BEARISH" else 1.0
    ret_abs = mult * (current_price - alert_price)
    ret_pct = round(mult * ((current_price - alert_price) / alert_price) * 100, 2)
    return {"return_pct": ret_pct, "return_absolute": round(ret_abs, 2)}


def fetch_historical_indices_nse_sync(period: str = "1y") -> dict:
    """
    Fetch historical daily data from NSE website API for all NSE indices.
    Called as a background task AFTER startup (does NOT block the server).
    Returns {index_name: [{date, open, high, low, close, volume}, ...]}
    """
    period_days = {"1y": 365, "6m": 180, "3m": 90, "1m": 30, "1w": 7, "5d": 5}
    days = period_days.get(period, 365)
    results = {}

    try:
        live = fetch_live_indices()
        if not live:
            logger.warning("NSE background: no live data to build index list")
            return results

        session_tuple = _nse_session()
        fetched_count = 0

        for i, item in enumerate(live):
            idx_name = item["index_name"]
            nse_name = item.get("nse_name")
            if not nse_name:
                continue

            try:
                rows = fetch_nse_index_history(nse_name, days=days, _session=session_tuple)
                if rows:
                    results[idx_name] = rows
                    fetched_count += 1

                # Rate limit
                time.sleep(0.5)

                # Re-establish session every 25 requests
                if (i + 1) % 25 == 0:
                    session_tuple = _nse_session()
                    time.sleep(1)

            except Exception as e:
                logger.debug("NSE bg history error for %s: %s", nse_name, e)

        logger.info("NSE background fetch: %d/%d indices got data", fetched_count, len(live))
    except Exception as e:
        logger.warning("NSE background fetch failed: %s", e)

    return results


def fetch_stock_history(ticker: str, period: str = "1y") -> list:
    """
    Fetch historical daily data for a single stock.
    Returns [{date, open, high, low, close, volume}, ...]
    """
    try:
        import yfinance as yf
        yf_sym = normalize_ticker(ticker)
        if not yf_sym:
            return []

        hist = yf.Ticker(yf_sym).history(period=period)
        if hist is None or hist.empty:
            return []

        rows = []
        for dt, row in hist.iterrows():
            c = row.get("Close")
            if c is None or (isinstance(c, float) and c != c):
                continue
            rows.append({
                "date":   dt.strftime("%Y-%m-%d"),
                "open":   float(row["Open"])   if row.get("Open")   else None,
                "high":   float(row["High"])   if row.get("High")   else None,
                "low":    float(row["Low"])    if row.get("Low")    else None,
                "close":  float(c),
                "volume": float(row["Volume"]) if row.get("Volume") else None,
            })
        logger.info("Stock history: %s (%s) — %d days", ticker, yf_sym, len(rows))
        return rows
    except Exception as e:
        logger.debug("Stock history error for %s: %s", ticker, e)
        return []


def fetch_yfinance_index_history(index_key: str, period: str = "2y") -> list:
    """
    Fetch historical daily data for a single index via yfinance.
    Uses NSE_TICKER_MAP to resolve the yfinance symbol.
    Returns [{date, open, high, low, close, volume}, ...]
    """
    try:
        import yfinance as yf
        yf_sym = NSE_TICKER_MAP.get(index_key.upper())
        if not yf_sym:
            logger.debug("No yfinance symbol for index key: %s", index_key)
            return []

        hist = yf.Ticker(yf_sym).history(period=period)
        if hist is None or hist.empty:
            return []

        rows = []
        for dt, row in hist.iterrows():
            c = row.get("Close")
            if c is None or (isinstance(c, float) and c != c):
                continue
            rows.append({
                "date":   dt.strftime("%Y-%m-%d"),
                "open":   float(row["Open"])   if row.get("Open")   else None,
                "high":   float(row["High"])   if row.get("High")   else None,
                "low":    float(row["Low"])    if row.get("Low")    else None,
                "close":  float(c),
                "volume": float(row["Volume"]) if row.get("Volume") else None,
            })
        logger.info("yfinance index history: %s (%s) — %d days", index_key, yf_sym, len(rows))
        return rows
    except Exception as e:
        logger.debug("yfinance index history error for %s: %s", index_key, e)
        return []


def _yf_download_with_retry(tickers: str, max_retries: int = 3, **kwargs):  # -> pd.DataFrame
    """Wrapper around yf.download() with retry logic for rate limits."""
    import yfinance as yf

    for attempt in range(max_retries):
        try:
            raw = yf.download(tickers=tickers, **kwargs)
            return raw
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "rate" in err_str or "too many" in err_str:
                delay = 5 * (attempt + 1)
                logger.warning("yfinance rate limited (attempt %d/%d), retrying in %ds...", attempt + 1, max_retries, delay)
                time.sleep(delay)
            else:
                raise
    # Final attempt without catching
    return yf.download(tickers=tickers, **kwargs)


def fetch_yfinance_bulk_history(index_keys: list, period: str = "2y", start: str = None, end: str = None) -> dict:
    """
    Batch-fetch historical data for multiple indices via yf.download().
    Chunks into groups of 30 to avoid rate limits.
    When start is provided, uses start/end instead of period.
    Returns {index_key: [{date, open, high, low, close, volume}, ...]}
    """
    import pandas as pd

    results = {}
    if not index_keys:
        return results

    # Build symbol -> key mapping (only keys with known yfinance symbols)
    sym_to_key = {}
    for key in index_keys:
        yf_sym = NSE_TICKER_MAP.get(key.upper())
        if yf_sym:
            sym_to_key[yf_sym] = key

    if not sym_to_key:
        return results

    all_symbols = list(sym_to_key.keys())
    chunk_size = 30

    # Build download kwargs (start/end or period)
    dl_kwargs = {"auto_adjust": True, "progress": False, "threads": True}
    if start:
        dl_kwargs["start"] = start
        if end:
            dl_kwargs["end"] = end
    else:
        dl_kwargs["period"] = period

    for i in range(0, len(all_symbols), chunk_size):
        chunk = all_symbols[i:i + chunk_size]
        try:
            raw = _yf_download_with_retry(" ".join(chunk), **dl_kwargs)
            if raw is None or raw.empty:
                continue

            multi = len(chunk) > 1
            for yf_sym in chunk:
                key = sym_to_key[yf_sym]
                try:
                    if multi:
                        closes = raw["Close"][yf_sym].dropna()
                        opens  = raw["Open"][yf_sym].dropna()
                        highs  = raw["High"][yf_sym].dropna()
                        lows   = raw["Low"][yf_sym].dropna()
                        vols   = raw["Volume"][yf_sym].dropna() if "Volume" in raw.columns.get_level_values(0) else pd.Series()
                    else:
                        closes = raw["Close"].dropna()
                        opens  = raw["Open"].dropna()
                        highs  = raw["High"].dropna()
                        lows   = raw["Low"].dropna()
                        vols   = raw["Volume"].dropna() if "Volume" in raw.columns else pd.Series()

                    if closes.empty:
                        continue

                    rows = []
                    for dt in closes.index:
                        rows.append({
                            "date":   dt.strftime("%Y-%m-%d"),
                            "open":   float(opens.get(dt, 0)) if dt in opens.index else None,
                            "high":   float(highs.get(dt, 0)) if dt in highs.index else None,
                            "low":    float(lows.get(dt, 0))  if dt in lows.index  else None,
                            "close":  float(closes[dt]),
                            "volume": float(vols.get(dt, 0))  if not vols.empty and dt in vols.index else None,
                        })
                    results[key] = rows
                except Exception as e:
                    logger.debug("yfinance bulk parse error for %s (%s): %s", key, yf_sym, e)

            # Delay between chunks to avoid rate limiting
            if i + chunk_size < len(all_symbols):
                time.sleep(2)

        except Exception as e:
            logger.warning("yfinance bulk download error (chunk %d): %s", i // chunk_size, e)

    logger.info("yfinance bulk history: %d/%d indices fetched", len(results), len(index_keys))
    return results


def fetch_yfinance_bulk_stock_history(tickers: list, period: str = "2y", start: str = None, end: str = None) -> dict:
    """
    Batch-fetch historical data for stocks/ETFs via yf.download().
    Uses normalize_ticker() to convert to Yahoo symbols (appends .NS).
    Chunks into groups of 30 to avoid rate limits.
    When start is provided, uses start/end instead of period.
    Returns {ticker: [{date, open, high, low, close, volume}, ...]}
    """
    import pandas as pd

    results = {}
    if not tickers:
        return results

    # Build symbol -> ticker mapping
    sym_to_ticker = {}
    for ticker in tickers:
        yf_sym = normalize_ticker(ticker)
        if yf_sym:
            sym_to_ticker[yf_sym] = ticker

    if not sym_to_ticker:
        return results

    all_symbols = list(sym_to_ticker.keys())
    chunk_size = 30

    # Build download kwargs (start/end or period)
    dl_kwargs = {"auto_adjust": True, "progress": False, "threads": True}
    if start:
        dl_kwargs["start"] = start
        if end:
            dl_kwargs["end"] = end
    else:
        dl_kwargs["period"] = period

    for i in range(0, len(all_symbols), chunk_size):
        chunk = all_symbols[i:i + chunk_size]
        try:
            raw = _yf_download_with_retry(" ".join(chunk), **dl_kwargs)
            if raw is None or raw.empty:
                continue

            multi = len(chunk) > 1
            for yf_sym in chunk:
                ticker = sym_to_ticker[yf_sym]
                try:
                    if multi:
                        closes = raw["Close"][yf_sym].dropna()
                        opens  = raw["Open"][yf_sym].dropna()
                        highs  = raw["High"][yf_sym].dropna()
                        lows   = raw["Low"][yf_sym].dropna()
                        vols   = raw["Volume"][yf_sym].dropna() if "Volume" in raw.columns.get_level_values(0) else pd.Series()
                    else:
                        closes = raw["Close"].dropna()
                        opens  = raw["Open"].dropna()
                        highs  = raw["High"].dropna()
                        lows   = raw["Low"].dropna()
                        vols   = raw["Volume"].dropna() if "Volume" in raw.columns else pd.Series()

                    if closes.empty:
                        continue

                    rows = []
                    for dt in closes.index:
                        rows.append({
                            "date":   dt.strftime("%Y-%m-%d"),
                            "open":   float(opens.get(dt, 0)) if dt in opens.index else None,
                            "high":   float(highs.get(dt, 0)) if dt in highs.index else None,
                            "low":    float(lows.get(dt, 0))  if dt in lows.index  else None,
                            "close":  float(closes[dt]),
                            "volume": float(vols.get(dt, 0))  if not vols.empty and dt in vols.index else None,
                        })
                    results[ticker] = rows
                except Exception as e:
                    logger.debug("yfinance bulk stock parse error for %s (%s): %s", ticker, yf_sym, e)

            if i + chunk_size < len(all_symbols):
                time.sleep(2)

        except Exception as e:
            logger.warning("yfinance bulk stock download error (chunk %d): %s", i // chunk_size, e)

    logger.info("yfinance bulk stock history: %d/%d tickers fetched", len(results), len(tickers))
    return results


def fetch_all_index_eod(period: str = "5d") -> dict:
    """
    Fetch EOD OHLCV data for all indices.
    Primary: nsetools (gets latest trading day for all 135+ NSE indices).
    Fallback: yfinance for commodities, currencies, BSE indices.
    Returns {index_name: [{date, open, high, low, close, volume}, ...]}
    """
    results = {}
    today_str = date_type.today().strftime("%Y-%m-%d")

    # ── Primary: nsetools for all NSE indices ──
    try:
        live = fetch_live_indices()
        for item in live:
            idx_name = item["index_name"]
            if item.get("last") is not None:
                results[idx_name] = [{
                    "date":   today_str,
                    "open":   item.get("open"),
                    "high":   item.get("high"),
                    "low":    item.get("low"),
                    "close":  item.get("last"),
                    "volume": None,
                }]
        logger.info("nsetools primary: got %d indices for EOD", len(results))
    except Exception as e:
        logger.warning("nsetools EOD primary failed: %s, falling back to yfinance", e)

    # ── Fallback: yfinance for non-NSE keys (commodities, BSE, currencies) ──
    non_nse_keys = ["GOLD", "SILVER", "CRUDEOIL", "USDINR", "SENSEX", "BSE500"]
    yf_keys = [k for k in non_nse_keys if k not in results and k in NSE_INDEX_KEYS]

    if yf_keys:
        try:
            import pandas as pd
            import yfinance as yf

            sym_map = {}
            for key in yf_keys:
                yf_sym = NSE_TICKER_MAP.get(key)
                if yf_sym and yf_sym not in sym_map:
                    sym_map[yf_sym] = key

            yf_symbols = list(sym_map.keys())
            if yf_symbols:
                raw = yf.download(
                    tickers=" ".join(yf_symbols),
                    period=period, auto_adjust=True, progress=False, threads=True,
                )
                multi = len(yf_symbols) > 1
                for yf_sym, idx_name in sym_map.items():
                    try:
                        if multi:
                            closes = raw["Close"][yf_sym].dropna()
                            opens  = raw["Open"][yf_sym].dropna()
                            highs  = raw["High"][yf_sym].dropna()
                            lows   = raw["Low"][yf_sym].dropna()
                            vols   = raw["Volume"][yf_sym].dropna() if "Volume" in raw.columns.get_level_values(0) else pd.Series()
                        else:
                            closes = raw["Close"].dropna()
                            opens  = raw["Open"].dropna()
                            highs  = raw["High"].dropna()
                            lows   = raw["Low"].dropna()
                            vols   = raw["Volume"].dropna() if "Volume" in raw.columns else pd.Series()
                        if closes.empty:
                            continue
                        rows = []
                        for dt in closes.index:
                            dt_str = dt.strftime("%Y-%m-%d")
                            rows.append({
                                "date":   dt_str,
                                "open":   float(opens.get(dt, 0)) if dt in opens.index else None,
                                "high":   float(highs.get(dt, 0)) if dt in highs.index else None,
                                "low":    float(lows.get(dt, 0))  if dt in lows.index  else None,
                                "close":  float(closes[dt]),
                                "volume": float(vols.get(dt, 0))  if not vols.empty and dt in vols.index else None,
                            })
                        results[idx_name] = rows
                    except Exception as e:
                        logger.debug("yf parse error %s (%s): %s", idx_name, yf_sym, e)
        except Exception as e:
            logger.error("yfinance fallback error: %s", e)

    return results


# ─── NSE Index Constituent Fetcher ────────────────────

def fetch_nse_index_constituents(index_display_name: str) -> list:
    """Fetch current constituents of an NSE index from NSE website API.
    index_display_name: e.g. "NIFTY BANK", "NIFTY IT"
    Returns list of {symbol, company_name, last_price, weight, ...}
    """
    try:
        session, headers = _nse_session()
        api_headers = {
            **headers,
            "referer": "https://www.nseindia.com/",
            "Accept": "application/json, text/html, */*",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
        }

        encoded_name = quote(index_display_name)
        url = f"https://www.nseindia.com/api/equity-stockIndices?index={encoded_name}"

        resp = session.get(url, headers=api_headers, timeout=15)
        if resp.status_code != 200:
            logger.warning("NSE constituents API returned %d for %s", resp.status_code, index_display_name)
            return []

        data = resp.json()
        items = data.get("data", [])
        results = []

        for item in items:
            symbol = item.get("symbol", "").strip()
            if not symbol or symbol == index_display_name:
                continue
            results.append({
                "symbol": symbol,
                "company_name": item.get("meta", {}).get("companyName") or item.get("companyName", ""),
                "last_price": _safe_float(item.get("lastPrice")),
                "weight": _safe_float(item.get("ffmc")) or _safe_float(item.get("weightage")),
                "change_pct": _safe_float(item.get("pChange")),
                "open": _safe_float(item.get("open")),
                "high": _safe_float(item.get("dayHigh")),
                "low": _safe_float(item.get("dayLow")),
            })

        logger.info("NSE constituents: %s — %d stocks fetched", index_display_name, len(results))
        return results

    except Exception as e:
        logger.warning("NSE constituent fetch failed for %s: %s", index_display_name, e)
        return []
