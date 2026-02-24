import yfinance as yf
import logging
from sqlalchemy.orm import Session
from datetime import datetime

logger = logging.getLogger(__name__)

# The Translation Dictionary for Indian Indices
NSE_TICKER_MAP = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "NIFTYIT": "^CNXIT",
    "SENSEX": "^BSESN",
    "FINNIFTY": "^NSEFIN",
    "MIDCPNIFTY": "^NSEMDCP50"
}

def normalize_ticker(ticker: str) -> str:
    if not ticker: return ""
    clean = ticker.upper().strip()
    # Map indices
    if clean in NSE_TICKER_MAP:
        return NSE_TICKER_MAP[clean]
    # Map stocks (add .NS for National Stock Exchange)
    if not clean.startswith("^") and not clean.endswith(".NS") and not clean.endswith(".BO"):
        return f"{clean}.NS"
    return clean

def get_live_price(ticker: str) -> dict:
    """Fetches the absolute latest live/EOD price from market data."""
    yf_ticker = normalize_ticker(ticker)
    try:
        data = yf.Ticker(yf_ticker)
        hist = data.history(period="1d")
        if hist.empty:
            return {"current_price": None, "error": "No market data"}
        return {"current_price": float(hist["Close"].iloc[-1])}
    except Exception as e:
        return {"current_price": None, "error": str(e)}

def update_all_performance(db: Session) -> int:
    from models import AlertPerformance
    records = db.query(AlertPerformance).all()
    updated = 0
    for perf in records:
        if not perf.ticker: continue
        price_data = get_live_price(perf.ticker)
        curr_price = price_data.get("current_price")
        
        if curr_price and perf.reference_price and perf.reference_price > 0:
            perf.current_price = curr_price
            perf.return_pct = ((curr_price - perf.reference_price) / perf.reference_price) * 100
            perf.snapshot_date = datetime.now()
            updated += 1
    db.commit()
    return updated
