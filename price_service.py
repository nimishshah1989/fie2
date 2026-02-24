import yfinance as yf
import logging
from sqlalchemy.orm import Session
from datetime import datetime

logger = logging.getLogger(__name__)

# Comprehensive NSE/BSE Index Ticker Map
NSE_TICKER_MAP = {
    "NIFTY": "^NSEI",
    "NIFTY50": "^NSEI",
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
    "NIFTY500": "^CRSLDX",
    "NIFTYINFRA": "^CNXINFRA",
    "NIFTYMEDIA": "^CNXMEDIA",
    "NIFTYCPSE": "NIFTYCPSE.NS",
    "NIFTYFINSERVICE": "NIFTYFINSERVICE.NS",
    "NIFTYHEALTHCARE": "NIFTYHEALTHCARE.NS",
    "NIFTYCONSUMER": "NIFTYCONSUMER.NS",
    "NIFTYCOMMODITIES": "NIFTYCOMMODITIES.NS",
    "FINNIFTY": "^NSEFIN",
    "MIDCPNIFTY": "^NSEMDCP50",
    "SENSEX": "^BSESN",
    # BSE Indices
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
}

def normalize_ticker(ticker: str) -> str:
    if not ticker:
        return ""
    clean = ticker.upper().strip()
    if clean in NSE_TICKER_MAP:
        return NSE_TICKER_MAP[clean]
    if not clean.startswith("^") and not clean.endswith(".NS") and not clean.endswith(".BO"):
        return f"{clean}.NS"
    return clean

def get_live_price(ticker: str) -> dict:
    """Fetches the absolute latest live/EOD price from market data."""
    yf_ticker = normalize_ticker(ticker)
    try:
        data = yf.Ticker(yf_ticker)
        hist = data.history(period="5d")
        if hist.empty:
            # Try BSE as fallback
            if yf_ticker.endswith(".NS"):
                bse_ticker = yf_ticker.replace(".NS", ".BO")
                data = yf.Ticker(bse_ticker)
                hist = data.history(period="5d")
            if hist.empty:
                return {"current_price": None, "error": "No market data"}
        return {"current_price": float(hist["Close"].iloc[-1])}
    except Exception as e:
        logger.error(f"Price fetch error for {ticker}: {e}")
        return {"current_price": None, "error": str(e)}

def update_all_performance(db: Session) -> int:
    from models import AlertPerformance
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
            perf.return_pct = ((curr_price - perf.reference_price) / perf.reference_price) * 100
            
            # Track high/low since
            if perf.high_since is None or curr_price > perf.high_since:
                perf.high_since = curr_price
            if perf.low_since is None or curr_price < perf.low_since:
                perf.low_since = curr_price
            
            # Max drawdown from high
            if perf.high_since and perf.high_since > 0:
                dd = ((curr_price - perf.high_since) / perf.high_since) * 100
                if perf.max_drawdown is None or dd < perf.max_drawdown:
                    perf.max_drawdown = dd
            
            perf.snapshot_date = datetime.now()
            updated += 1
    db.commit()
    return updated
