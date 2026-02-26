"""
FIE — Price Service
Fetches live and historical prices for NSE/BSE indices and Indian market instruments.
Primary: yfinance (NSE/BSE indices, stocks, commodities, currency)
Secondary: nsetools for NSE-specific data
"""

import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ─── Yahoo Finance Ticker Map ──────────────────────────
# Maps internal FIE tickers → Yahoo Finance symbols
NSE_TICKER_MAP = {
    # NSE Broad
    "NIFTY": "^NSEI",
    "NIFTY50": "^NSEI",
    "NIFTY500": "^CRSLDX",
    "NIFTYNEXT50": "^NSMIDCP",
    "NIFTYMIDCAP": "^NSEMDCP50",
    "NIFTYSMALLCAP": "^CNXSC",
    # NSE Sectoral
    "BANKNIFTY": "^NSEBANK",
    "NIFTYBANK": "^NSEBANK",
    "NIFTYIT": "^CNXIT",
    "NIFTYPHARMA": "^CNXPHARMA",
    "NIFTYFMCG": "^CNXFMCG",
    "NIFTYAUTO": "^CNXAUTO",
    "NIFTYMETAL": "^CNXMETAL",
    "NIFTYREALTY": "^CNXREALTY",
    "NIFTYENERGY": "^CNXENERGY",
    "NIFTYPSUBANK": "^CNXPSUBANK",
    "NIFTYPVTBANK": "NIFTYPVTBANK.NS",
    "NIFTYINFRA": "^CNXINFRA",
    "NIFTYMEDIA": "^CNXMEDIA",
    "NIFTYCPSE": "NIFTYCPSE.NS",
    "NIFTYFINSERVICE": "NIFTY_FIN_SERVICE.NS",
    "FINNIFTY": "NIFTY_FIN_SERVICE.NS",
    "NIFTYHEALTHCARE": "NIFTYHEALTHCARE.NS",
    "NIFTYCONSUMER": "NIFTYCONSUMER.NS",
    "NIFTYCOMMODITIES": "NIFTYCOMMODITIES.NS",
    "MIDCPNIFTY": "^NSEMDCP50",
    # BSE
    "SENSEX": "^BSESN",
    "BSE500": "BSE-500.BO",
    "BSEIT": "BSE-IT.BO",
    "BSEBANK": "BSE-BANKEX.BO",
    "BSEFMCG": "BSE-FMCG.BO",
    "BSEHEALTHCARE": "BSE-HEALTHCARE.BO",
    "BSEAUTO": "BSE-AUTO.BO",
    "BSEMETAL": "BSE-METAL.BO",
    "BSEREALTY": "BSE-REALTY.BO",
    "BSEENERGY": "BSE-ENERGY.BO",
    "BSESMALLCAP": "BSE-SMLCAP.BO",
    "BSEMIDCAP": "BSE-MIDCAP.BO",
    # Commodities
    "GOLD": "GC=F",
    "SILVER": "SI=F",
    "CRUDEOIL": "CL=F",
    "CRUDE": "CL=F",
    "NATURALGAS": "NG=F",
    "COPPER": "HG=F",
    # Currency
    "USDINR": "USDINR=X",
    "EURINR": "EURINR=X",
    "GBPINR": "GBPINR=X",
    "JPYINR": "JPYINR=X",
}

FALLBACK_MAP = {
    "^NSEI": ["NIFTY_50.NS"],
    "^NSEBANK": ["BANKBEES.NS"],
    "^CNXIT": ["NIFTYIT.NS"],
    "^CNXPHARMA": ["PHARMABEES.NS"],
    "^BSESN": ["^BSESN"],
}


def normalize_ticker(ticker: str) -> str:
    """Convert internal ticker to Yahoo Finance symbol."""
    if not ticker:
        return ""
    clean = ticker.upper().strip()
    # Remove exchange prefix (e.g. NSE:NIFTY → NIFTY)
    if ":" in clean:
        clean = clean.split(":")[-1].strip()
    if clean in NSE_TICKER_MAP:
        return NSE_TICKER_MAP[clean]
    # Already a YF symbol
    if clean.startswith("^") or "=" in clean or clean.endswith("=F"):
        return clean
    # Default: assume NSE stock
    if not clean.endswith(".NS") and not clean.endswith(".BO"):
        return f"{clean}.NS"
    return clean

# Keep old name for server.py compatibility
normalize_ticker_for_yfinance = normalize_ticker


def _fetch_yfinance(yf_symbol: str, period: str = "5d") -> dict:
    """Core price fetch from Yahoo Finance."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period=period)
        if hist is None or hist.empty:
            return {"current_price": None}
        latest = hist.iloc[-1]
        prev_close = float(hist.iloc[-2]["Close"]) if len(hist) > 1 else None
        curr = float(latest["Close"])
        chg_pct = round(((curr - prev_close) / prev_close) * 100, 2) if prev_close else None
        return {
            "current_price": curr,
            "high": float(latest["High"]) if "High" in latest else None,
            "low": float(latest["Low"]) if "Low" in latest else None,
            "volume": float(latest["Volume"]) if "Volume" in latest else None,
            "prev_close": prev_close,
            "change_pct": chg_pct,
            "open": float(latest["Open"]) if "Open" in latest else None,
        }
    except Exception as e:
        logger.debug(f"yfinance error for {yf_symbol}: {e}")
        return {"current_price": None, "error": str(e)}


def _fetch_nsetools(index_name: str) -> dict:
    """Try nsetools for NSE indices."""
    try:
        from nsetools import Nse
        nse = Nse()
        quotes = nse.get_all_index_quote()
        if not quotes:
            return {"current_price": None}
        for q in quotes:
            if q.get("index", "").lower() == index_name.lower():
                return {
                    "current_price": float(q.get("last", 0)) or None,
                    "prev_close": float(q.get("previousClose", 0)) or None,
                    "change_pct": float(q.get("percentChange", 0)) or None,
                    "high": float(q.get("high", 0)) or None,
                    "low": float(q.get("low", 0)) or None,
                    "year_high": float(q.get("yearHigh", 0)) or None,
                    "year_low": float(q.get("yearLow", 0)) or None,
                    "pe": q.get("pe"),
                }
        return {"current_price": None}
    except Exception as e:
        logger.debug(f"nsetools error for {index_name}: {e}")
        return {"current_price": None}


def get_live_price(ticker: str) -> dict:
    """
    Fetch latest price for a ticker with multiple fallback strategies.
    1. yfinance primary symbol
    2. yfinance fallback symbols
    3. NSE/BSE swap (.NS → .BO or vice versa)
    """
    yf_symbol = normalize_ticker(ticker)

    if not yf_symbol:
        return {"current_price": None, "error": "Empty ticker"}

    # Strategy 1: yfinance primary
    result = _fetch_yfinance(yf_symbol)
    if result.get("current_price"):
        return result

    # Strategy 2: yfinance fallbacks
    if yf_symbol in FALLBACK_MAP:
        for alt in FALLBACK_MAP[yf_symbol]:
            result = _fetch_yfinance(alt)
            if result.get("current_price"):
                return result

    # Strategy 3: NSE/BSE swap
    if yf_symbol.endswith(".NS"):
        result = _fetch_yfinance(yf_symbol.replace(".NS", ".BO"))
        if result.get("current_price"):
            return result
    elif yf_symbol.endswith(".BO"):
        result = _fetch_yfinance(yf_symbol.replace(".BO", ".NS"))
        if result.get("current_price"):
            return result

    logger.warning(f"No price data available for {ticker} (tried: {yf_symbol})")
    return {"current_price": None, "error": f"No data for {ticker}"}


def get_all_nse_indices() -> list:
    """
    Fetch all NSE index quotes via nsetools.
    Returns list of dicts with index name, last price, change%, etc.
    Falls back to yfinance for major indices if nsetools fails.
    """
    try:
        from nsetools import Nse
        nse = Nse()
        quotes = nse.get_all_index_quote()
        if quotes:
            result = []
            for q in quotes:
                try:
                    result.append({
                        "name": q.get("index", ""),
                        "current_price": float(q.get("last", 0) or 0) or None,
                        "prev_close": float(q.get("previousClose", 0) or 0) or None,
                        "change_pct": float(q.get("percentChange", 0) or 0) or None,
                        "high": float(q.get("high", 0) or 0) or None,
                        "low": float(q.get("low", 0) or 0) or None,
                        "open": float(q.get("open", 0) or 0) or None,
                        "year_high": float(q.get("yearHigh", 0) or 0) or None,
                        "year_low": float(q.get("yearLow", 0) or 0) or None,
                        "pe": q.get("pe"),
                        "source": "nsetools",
                    })
                except:
                    continue
            return result
    except Exception as e:
        logger.warning(f"nsetools get_all_index_quote failed: {e}")

    # Fallback: yfinance for major NSE indices
    logger.info("Falling back to yfinance for NSE index data")
    major = [
        ("NIFTY 50", "^NSEI"),
        ("NIFTY BANK", "^NSEBANK"),
        ("NIFTY IT", "^CNXIT"),
        ("NIFTY PHARMA", "^CNXPHARMA"),
        ("NIFTY AUTO", "^CNXAUTO"),
        ("NIFTY FMCG", "^CNXFMCG"),
        ("NIFTY METAL", "^CNXMETAL"),
        ("NIFTY REALTY", "^CNXREALTY"),
        ("NIFTY ENERGY", "^CNXENERGY"),
        ("NIFTY PSU BANK", "^CNXPSUBANK"),
        ("NIFTY MIDCAP 50", "^NSEMDCP50"),
        ("NIFTY SMALLCAP 100", "^CNXSC"),
    ]
    result = []
    for name, sym in major:
        d = _fetch_yfinance(sym)
        d["name"] = name
        d["source"] = "yfinance"
        result.append(d)
    return result


def get_historical_price(ticker: str, target_date: datetime) -> float | None:
    """
    Get closing price for a ticker on or near a specific date.
    Used for computing time-windowed returns (1d, 1w, 1m).
    """
    yf_symbol = normalize_ticker(ticker)
    if not yf_symbol:
        return None
    try:
        import yfinance as yf
        start = target_date - timedelta(days=5)
        end = target_date + timedelta(days=2)
        hist = yf.Ticker(yf_symbol).history(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))
        if hist.empty:
            return None
        # Find closest date
        hist.index = hist.index.tz_localize(None) if hist.index.tzinfo else hist.index
        target_naive = target_date.replace(tzinfo=None)
        diffs = abs(hist.index - target_naive)
        idx = diffs.argmin()
        return float(hist.iloc[idx]["Close"])
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
    return {
        "return_pct": ret_pct,
        "return_absolute": round(ret_abs, 2),
    }


def update_all_performance(db) -> int:
    """
    Update all AlertPerformance records with current prices.
    Called by POST /api/performance/refresh
    """
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
            direction = "BULLISH"
            if alert and alert.signal_direction:
                direction = alert.signal_direction.value

            ret = compute_returns(perf.reference_price, curr_price, direction)
            perf.current_price = curr_price
            perf.return_pct = ret["return_pct"]
            perf.return_absolute = ret["return_absolute"]

            # Track high/low since alert
            if perf.high_since is None or curr_price > perf.high_since:
                perf.high_since = curr_price
            if perf.low_since is None or curr_price < perf.low_since:
                perf.low_since = curr_price

            # Max drawdown from peak
            if perf.high_since and perf.high_since > 0:
                dd = round(((curr_price - perf.high_since) / perf.high_since) * 100, 2)
                if perf.max_drawdown is None or dd < perf.max_drawdown:
                    perf.max_drawdown = dd

            perf.snapshot_date = datetime.now()
            updated += 1

    db.commit()
    return updated
