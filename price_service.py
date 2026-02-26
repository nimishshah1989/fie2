"""
FIE — Price Service
Robust live price fetching for NSE/BSE indices and Indian market instruments.
Primary: yfinance with comprehensive NSE/BSE ticker map and fallback strategies.
"""

import logging
from datetime import datetime, timedelta

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


def get_historical_price(ticker: str, target_date: datetime) -> float | None:
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


def update_all_performance(db) -> int:
    """Update all AlertPerformance records with current prices."""
    from models import AlertPerformance, TradingViewAlert

    records = db.query(AlertPerformance).all()
    updated = 0

    for perf in records:
        if not perf.ticker:
            continue
        price_data = get_live_price(perf.ticker)
        curr_price = price_data.get("current_price")

        if curr_price and perf.reference_price and perf.reference_price > 0:
            alert = db.query(TradingViewAlert).filter_by(id=perf.alert_id).first()
            direction = alert.signal_direction.value if (alert and alert.signal_direction) else "BULLISH"

            ret = compute_returns(perf.reference_price, curr_price, direction)
            perf.current_price    = curr_price
            perf.return_pct       = ret["return_pct"]
            perf.return_absolute  = ret["return_absolute"]

            if perf.high_since is None or curr_price > perf.high_since:
                perf.high_since = curr_price
            if perf.low_since is None or curr_price < perf.low_since:
                perf.low_since = curr_price

            if perf.high_since and perf.high_since > 0:
                dd = round(((curr_price - perf.high_since) / perf.high_since) * 100, 2)
                if perf.max_drawdown is None or dd < perf.max_drawdown:
                    perf.max_drawdown = dd

            perf.snapshot_date = datetime.now()
            updated += 1

    db.commit()
    return updated
