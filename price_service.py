"""
FIE — Price Service
Robust live price fetching for NSE/BSE indices and Indian market instruments.
Primary: nsetools for NSE indices (135+ indices directly from NSE).
Fallback: yfinance for individual stocks, BSE, commodities, currencies.
"""

import logging
from datetime import datetime, timedelta, date as date_type

logger = logging.getLogger(__name__)

# ─── Yahoo Finance Ticker Map ──────────────────────────
NSE_TICKER_MAP = {
    # NSE Broad
    "NIFTY":          "^NSEI",
    "NIFTY50":        "^NSEI",
    "NIFTY500":       "^CRSLDX",
    "NIFTYNEXT50":    "^NSMIDCP",
    "NIFTYMIDCAP":    "^NSEMDCP50",
    "NIFTYSMALLCAP":  "^CNXSC",
    # NSE Sectoral
    "BANKNIFTY":      "^NSEBANK",
    "NIFTYBANK":      "^NSEBANK",
    "NIFTYIT":        "^CNXIT",
    "NIFTYPHARMA":    "^CNXPHARMA",
    "NIFTYFMCG":      "^CNXFMCG",
    "NIFTYAUTO":      "^CNXAUTO",
    "NIFTYMETAL":     "^CNXMETAL",
    "NIFTYREALTY":    "^CNXREALTY",
    "NIFTYENERGY":    "^CNXENERGY",
    "NIFTYPSUBANK":   "^CNXPSUBANK",
    "NIFTYPVTBANK":   "NIFTYPVTBANK.NS",
    "NIFTYMIDCAP50":  "^NSEMDCP50",
    "NIFTYINFRA":     "^CNXINFRA",
    "NIFTYMEDIA":     "^CNXMEDIA",
    "NIFTYCPSE":      "NIFTYCPSE.NS",
    "NIFTYFINSERVICE":"NIFTY_FIN_SERVICE.NS",
    "FINNIFTY":       "NIFTY_FIN_SERVICE.NS",
    "NIFTYHEALTHCARE":"NIFTYHEALTHCARE.NS",
    "NIFTYCONSUMER":  "NIFTYCONSUMER.NS",
    "NIFTYCOMMODITIES":"NIFTYCOMMODITIES.NS",
    "MIDCPNIFTY":     "^NSEMDCP50",
    # BSE
    "SENSEX":         "^BSESN",
    "BSE500":         "BSE-500.BO",
    "BSEIT":          "BSE-IT.BO",
    "BSEBANK":        "BSE-BANKEX.BO",
    # Commodities
    "GOLD":           "GC=F",
    "SILVER":         "SI=F",
    "CRUDEOIL":       "CL=F",
    "CRUDE":          "CL=F",
    "NATURALGAS":     "NG=F",
    "COPPER":         "HG=F",
    # Currency
    "USDINR":         "USDINR=X",
    "EURINR":         "EURINR=X",
    "GBPINR":         "GBPINR=X",
}

FALLBACK_MAP = {
    "^NSEI":    ["NIFTY_50.NS"],
    "^NSEBANK": ["BANKBEES.NS"],
    "^CNXIT":   ["NIFTYIT.NS"],
    "^BSESN":   ["^BSESN"],
}

# ─── NSE Index Keys for EOD Fetch ────────────────────────
NSE_INDEX_KEYS = [
    "NIFTY", "NIFTY500", "NIFTYNEXT50", "NIFTYMIDCAP", "NIFTYSMALLCAP",
    "BANKNIFTY", "NIFTYIT", "NIFTYPHARMA", "NIFTYFMCG", "NIFTYAUTO",
    "NIFTYMETAL", "NIFTYREALTY", "NIFTYENERGY", "NIFTYPSUBANK", "NIFTYPVTBANK",
    "NIFTYMIDCAP50", "NIFTYINFRA", "NIFTYMEDIA", "FINNIFTY",
    "NIFTYHEALTHCARE", "NIFTYCONSUMER", "NIFTYCOMMODITIES",
    "SENSEX", "BSE500",
    "GOLD", "SILVER", "CRUDEOIL",
    "USDINR",
]

# ─── NSE Display Name Map (nsetools returns these names) ────
# Maps our internal key -> NSE display name as returned by nsetools
NSE_DISPLAY_MAP = {
    "NIFTY":            "NIFTY 50",
    "NIFTY500":         "NIFTY 500",
    "NIFTYNEXT50":      "NIFTY NEXT 50",
    "NIFTYMIDCAP":      "NIFTY MIDCAP 150",
    "NIFTYSMALLCAP":    "NIFTY SMLCAP 250",
    "BANKNIFTY":        "NIFTY BANK",
    "NIFTYIT":          "NIFTY IT",
    "NIFTYPHARMA":      "NIFTY PHARMA",
    "NIFTYFMCG":        "NIFTY FMCG",
    "NIFTYAUTO":        "NIFTY AUTO",
    "NIFTYMETAL":       "NIFTY METAL",
    "NIFTYREALTY":      "NIFTY REALTY",
    "NIFTYENERGY":      "NIFTY ENERGY",
    "NIFTYPSUBANK":     "NIFTY PSU BANK",
    "NIFTYPVTBANK":     "NIFTY PVT BANK",
    "NIFTYMIDCAP50":    "NIFTY MIDCAP 50",
    "NIFTYINFRA":       "NIFTY INFRA",
    "NIFTYMEDIA":       "NIFTY MEDIA",
    "FINNIFTY":         "NIFTY FIN SERVICE",
    "NIFTYFINSERVICE":  "NIFTY FIN SERVICE",
    "NIFTYHEALTHCARE":  "NIFTY HEALTHCARE",
    "NIFTYCONSUMER":    "NIFTY CONSR DURBL",
    "NIFTYCOMMODITIES": "NIFTY COMMODITIES",
    "MIDCPNIFTY":       "NIFTY MIDCAP 50",
}

# Reverse map: NSE display name -> our internal key
_NSE_REVERSE_MAP = {}
for _k, _v in NSE_DISPLAY_MAP.items():
    _NSE_REVERSE_MAP[_v.upper()] = _k


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


def fetch_historical_indices(period: str = "1y") -> dict:
    """
    Fetch historical daily OHLCV data for all indices.
    Strategy:
      1. Try yfinance batch download
      2. If batch fails, try individual ticker downloads
      3. Generate synthetic historical points from nsetools reference values
    Returns {index_name: [{date, open, high, low, close, volume}, ...]}
    """
    results = {}

    # Build unique symbol map: yf_symbol -> our internal key
    sym_map = {}
    for key in NSE_INDEX_KEYS:
        yf_sym = NSE_TICKER_MAP.get(key)
        if yf_sym and yf_sym not in sym_map:
            sym_map[yf_sym] = key

    # Strategy 1: yfinance batch download
    if sym_map:
        try:
            import yfinance as yf
            import pandas as pd

            yf_symbols = list(sym_map.keys())
            logger.info("Trying yfinance batch for %d indices (period=%s)", len(yf_symbols), period)

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
                        rows.append({
                            "date":   dt.strftime("%Y-%m-%d"),
                            "open":   float(opens[dt]) if dt in opens.index else None,
                            "high":   float(highs[dt]) if dt in highs.index else None,
                            "low":    float(lows[dt])  if dt in lows.index  else None,
                            "close":  float(closes[dt]),
                            "volume": float(vols[dt])  if not vols.empty and dt in vols.index else None,
                        })
                    results[idx_name] = rows
                    logger.info("Historical batch: %s — %d days", idx_name, len(rows))
                except Exception as e:
                    logger.debug("Batch parse error %s (%s): %s", idx_name, yf_sym, e)
        except Exception as e:
            logger.warning("yfinance batch failed: %s, trying individual", e)

    # Strategy 2: Individual ticker downloads for missing indices
    if sym_map and len(results) < len(sym_map):
        try:
            import yfinance as yf
            for yf_sym, idx_name in sym_map.items():
                if idx_name in results:
                    continue
                try:
                    hist = yf.Ticker(yf_sym).history(period=period)
                    if hist is not None and not hist.empty:
                        rows = []
                        for dt, row in hist.iterrows():
                            c = row.get("Close")
                            if c is None:
                                continue
                            rows.append({
                                "date":   dt.strftime("%Y-%m-%d"),
                                "open":   float(row["Open"])   if row.get("Open")   else None,
                                "high":   float(row["High"])   if row.get("High")   else None,
                                "low":    float(row["Low"])    if row.get("Low")    else None,
                                "close":  float(c),
                                "volume": float(row["Volume"]) if row.get("Volume") else None,
                            })
                        if rows:
                            results[idx_name] = rows
                            logger.info("Historical individual: %s — %d days", idx_name, len(rows))
                except Exception as e:
                    logger.debug("Individual fetch error %s: %s", idx_name, e)
        except Exception:
            pass

    # Strategy 3: Synthetic historical from nsetools reference values
    # This provides 1D, 1W, 1M, 12M reference points for ALL NSE indices
    try:
        live = fetch_live_indices()
        today = date_type.today()
        ref_fields = [
            ("previousClose",  1),
            ("oneWeekAgoVal",  7),
            ("oneMonthAgoVal", 30),
            ("oneYearAgoVal",  365),
        ]
        for item in live:
            idx_name = item["index_name"]
            if idx_name not in results:
                results[idx_name] = []
            existing_dates = {r["date"] for r in results.get(idx_name, [])}

            # Add today's data
            if item.get("last") and today.strftime("%Y-%m-%d") not in existing_dates:
                results[idx_name].append({
                    "date": today.strftime("%Y-%m-%d"),
                    "open": item.get("open"), "high": item.get("high"),
                    "low": item.get("low"), "close": item.get("last"),
                    "volume": None,
                })

            # Add synthetic historical points
            for field, days_ago in ref_fields:
                val = item.get(field)
                if val and val > 0:
                    ref_date = (today - timedelta(days=days_ago)).strftime("%Y-%m-%d")
                    if ref_date not in existing_dates:
                        results[idx_name].append({
                            "date": ref_date, "close": val,
                            "open": None, "high": None, "low": None, "volume": None,
                        })
        logger.info("Synthetic: added reference points for %d indices", len(live))
    except Exception as e:
        logger.warning("Synthetic historical failed: %s", e)

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
            import yfinance as yf
            import pandas as pd

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
