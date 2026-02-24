"""
FIE — Price Service
Robust live price fetching for NSE/BSE indices and Indian market instruments.
Uses yfinance as primary source with intelligent fallback.
"""

import yfinance as yf
import logging
import re
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ─── Comprehensive NSE/BSE Index Ticker Map ───────────────
# Maps our internal ticker names to Yahoo Finance symbols
NSE_TICKER_MAP = {
    # NSE Broad Indices
    "NIFTY": "^NSEI",
    "NIFTY50": "^NSEI",
    "NIFTY500": "^CRSLDX",
    "NIFTYNEXT50": "^NSMIDCP",
    # NSE Sector Indices
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
    "NIFTYMIDCAP": "^NSEMDCP50",
    "NIFTYSMALLCAP": "^CNXSC",
    "NIFTYINFRA": "^CNXINFRA",
    "NIFTYMEDIA": "^CNXMEDIA",
    "NIFTYCPSE": "NIFTYCPSE.NS",
    "NIFTYFINSERVICE": "NIFTY_FIN_SERVICE.NS",
    "FINNIFTY": "NIFTY_FIN_SERVICE.NS",
    "NIFTYHEALTHCARE": "NIFTYHEALTHCARE.NS",
    "NIFTYCONSUMER": "NIFTYCONSUMER.NS",
    "NIFTYCOMMODITIES": "NIFTYCOMMODITIES.NS",
    "MIDCPNIFTY": "^NSEMDCP50",
    # BSE Indices
    "SENSEX": "^BSESN",
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
    # Currency
    "USDINR": "USDINR=X",
    "EURINR": "EURINR=X",
    "GBPINR": "GBPINR=X",
}

# Alternate Yahoo Finance symbols to try if primary fails
FALLBACK_MAP = {
    "^NSEI": ["NIFTY_50.NS", "0P0001BKAG.BO"],
    "^NSEBANK": ["BANKNIFTY1!.NS", "BANKBEES.NS"],
    "^CNXIT": ["NIFTYIT.NS", "0P0001BKAI.BO"],
    "^CNXPHARMA": ["PHARMABEES.NS"],
    "^CNXFMCG": ["0P0001BK9V.BO"],
    "^CNXAUTO": ["0P0001BK9O.BO"],
    "^CNXMETAL": ["0P0001BKA7.BO"],
    "^BSESN": ["BSE-500.BO"],
}


def normalize_ticker(ticker: str) -> str:
    """Convert our internal ticker to Yahoo Finance symbol."""
    if not ticker:
        return ""
    clean = ticker.upper().strip()
    
    # Remove exchange suffix if present (e.g., "NIFTY:NSE" → "NIFTY")
    if ":" in clean:
        clean = clean.split(":")[0].strip()
    
    # Direct map lookup
    if clean in NSE_TICKER_MAP:
        return NSE_TICKER_MAP[clean]
    
    # Already a Yahoo Finance symbol
    if clean.startswith("^") or "=" in clean:
        return clean
    
    # If it looks like an NSE stock (no suffix), add .NS
    if not clean.endswith(".NS") and not clean.endswith(".BO"):
        return f"{clean}.NS"
    
    return clean


def get_live_price(ticker: str) -> dict:
    """Fetches the latest price with multiple fallback strategies."""
    yf_ticker = normalize_ticker(ticker)
    
    if not yf_ticker:
        return {"current_price": None, "high": None, "low": None, "volume": None, "error": "Empty ticker"}
    
    # Strategy 1: Direct fetch
    result = _fetch_price(yf_ticker)
    if result.get("current_price"):
        return result
    
    # Strategy 2: Try fallback symbols
    if yf_ticker in FALLBACK_MAP:
        for alt in FALLBACK_MAP[yf_ticker]:
            result = _fetch_price(alt)
            if result.get("current_price"):
                return result
    
    # Strategy 3: Try NSE/BSE swap
    if yf_ticker.endswith(".NS"):
        result = _fetch_price(yf_ticker.replace(".NS", ".BO"))
        if result.get("current_price"):
            return result
    elif yf_ticker.endswith(".BO"):
        result = _fetch_price(yf_ticker.replace(".BO", ".NS"))
        if result.get("current_price"):
            return result
    
    return {"current_price": None, "high": None, "low": None, "volume": None, "error": f"No data for {ticker}"}


def _fetch_price(yf_symbol: str) -> dict:
    """Core price fetch from Yahoo Finance."""
    try:
        data = yf.Ticker(yf_symbol)
        hist = data.history(period="5d")
        if hist.empty:
            return {"current_price": None}
        
        latest = hist.iloc[-1]
        return {
            "current_price": float(latest["Close"]),
            "high": float(latest["High"]) if "High" in latest else None,
            "low": float(latest["Low"]) if "Low" in latest else None,
            "volume": float(latest["Volume"]) if "Volume" in latest else None,
            "prev_close": float(hist.iloc[-2]["Close"]) if len(hist) > 1 else None,
            "change_pct": round(((float(latest["Close"]) - float(hist.iloc[-2]["Close"])) / float(hist.iloc[-2]["Close"])) * 100, 2) if len(hist) > 1 else None,
        }
    except Exception as e:
        logger.error(f"Price fetch error for {yf_symbol}: {e}")
        return {"current_price": None, "error": str(e)}


def get_batch_prices(tickers: list) -> dict:
    """Fetch prices for multiple tickers efficiently."""
    results = {}
    for ticker in tickers:
        results[ticker] = get_live_price(ticker)
    return results


def update_all_performance(db: Session) -> int:
    """Update performance metrics for all tracked positions."""
    from models import AlertPerformance, TradingViewAlert, AlertStatus
    
    # Get all performance records with their alerts
    records = db.query(AlertPerformance).all()
    updated = 0
    
    for perf in records:
        if not perf.ticker:
            continue
        
        price_data = get_live_price(perf.ticker)
        curr_price = price_data.get("current_price")
        
        if curr_price and perf.reference_price and perf.reference_price > 0:
            perf.current_price = curr_price
            perf.return_absolute = curr_price - perf.reference_price
            
            # Check if it's a SELL/SHORT direction — return calc is inverted
            alert = db.query(TradingViewAlert).filter_by(id=perf.alert_id).first()
            direction_multiplier = 1.0
            if alert and alert.signal_direction:
                if alert.signal_direction.value == "BEARISH":
                    direction_multiplier = -1.0
            
            perf.return_pct = round(
                direction_multiplier * ((curr_price - perf.reference_price) / perf.reference_price) * 100,
                2
            )
            perf.return_absolute = round(direction_multiplier * (curr_price - perf.reference_price), 2)
            
            # Track high/low since
            if perf.high_since is None or curr_price > perf.high_since:
                perf.high_since = curr_price
            if perf.low_since is None or curr_price < perf.low_since:
                perf.low_since = curr_price
            
            # Max drawdown from high
            if perf.high_since and perf.high_since > 0:
                dd = ((curr_price - perf.high_since) / perf.high_since) * 100
                if perf.max_drawdown is None or dd < perf.max_drawdown:
                    perf.max_drawdown = round(dd, 2)
            
            perf.snapshot_date = datetime.now()
            updated += 1
    
    db.commit()
    return updated
