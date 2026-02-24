import yfinance as yf
import logging
from sqlalchemy.orm import Session
from datetime import datetime

logger = logging.getLogger(__name__)

# Map standard Indian tickers to Yahoo Finance tickers
NSE_TICKER_MAP = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "NIFTYIT": "^CNXIT",
    "NIFTYAUTO": "^CNXAUTO",
    "NIFTYFMCG": "^CNXFMCG",
    "NIFTYPHARMA": "^CNXPHARMA",
    "NIFTYMETAL": "^CNXMETAL",
    "NIFTYENERGY": "^CNXENERGY",
    "NIFTYINFRA": "^CNXINFRA",
    "NIFTYMIDCAP": "^NSEMDCP50",
    "SENSEX": "^BSESN"
}

def normalize_ticker_for_yfinance(ticker: str) -> str:
    """Converts local tickers to yfinance compatible tickers."""
    if not ticker: return ""
    clean_ticker = ticker.upper().strip()
    
    # Check if it's a known index
    if clean_ticker in NSE_TICKER_MAP:
        return NSE_TICKER_MAP[clean_ticker]
    
    # If it's a stock (e.g., RELIANCE) and doesn't have an extension, add .NS
    if not clean_ticker.startswith("^") and not clean_ticker.endswith(".NS") and not clean_ticker.endswith(".BO"):
        return f"{clean_ticker}.NS"
        
    return clean_ticker

def get_live_price(ticker: str) -> dict:
    """Fetches the absolute latest live/EOD price from market data."""
    yf_ticker = normalize_ticker_for_yfinance(ticker)
    
    try:
        data = yf.Ticker(yf_ticker)
        # Fast fetch for the last 1 day
        hist = data.history(period="1d")
        
        if hist.empty:
            return {"current_price": None, "error": "No data found"}
            
        current_price = float(hist["Close"].iloc[-1])
        return {
            "current_price": current_price,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to fetch price for {yf_ticker}: {e}")
        return {"current_price": None, "error": str(e)}

def update_all_performance(db: Session) -> int:
    """Called by the 'Sync Live Market Prices' button on the dashboard."""
    from models import AlertPerformance
    
    active_records = db.query(AlertPerformance).all()
    updated_count = 0
    
    for perf in active_records:
        if not perf.ticker: continue
        
        price_data = get_live_price(perf.ticker)
        curr_price = price_data.get("current_price")
        
        if curr_price and perf.reference_price:
            perf.current_price = curr_price
            
            # Calculate Return %
            if perf.is_primary:
                # If we bought (default assumption for absolute), price goes up = positive return
                perf.return_pct = ((curr_price - perf.reference_price) / perf.reference_price) * 100
                
            perf.snapshot_date = datetime.now()
            updated_count += 1
            
    db.commit()
    return updated_count
