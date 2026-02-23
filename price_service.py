"""
FIE Phase 1 — Price Tracking & Performance Service
Fetches live prices and computes returns for approved alerts.
"""

import yfinance as yf
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import (
    SessionLocal, TradingViewAlert, AlertAction, AlertPerformance,
    AlertStatus, InstrumentMap
)
import logging
import re

logger = logging.getLogger(__name__)

# ─── Ticker Normalization for yfinance ──────────────────

# Map common TradingView ticker formats to yfinance symbols
TICKER_MAP = {
    # NSE Indices
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
    "NIFTYMIDCAP": "^NSEMDCP50",
    "NIFTYSMALLCAP": "NIFTYSMLCAP250.NS",
    "NIFTY500": "^CRSLDX",
    "NIFTYMEDIA": "^CNXMEDIA",
    "NIFTYINFRA": "^CNXINFRA",
    "NIFTYPVTBANK": "^NIFPVTBNK",
    # BSE
    "SENSEX": "^BSESN",
    # Commodities
    "GOLD": "GC=F",
    "SILVER": "SI=F",
    "CRUDEOIL": "CL=F",
    # Currency
    "USDINR": "USDINR=X",
}


def normalize_ticker_for_yfinance(ticker: str) -> str:
    """Convert TradingView ticker format to yfinance compatible format"""
    if not ticker:
        return ticker
    
    ticker_upper = ticker.upper().strip()
    
    # Check direct mapping
    if ticker_upper in TICKER_MAP:
        return TICKER_MAP[ticker_upper]
    
    # If already has exchange suffix (.NS, .BO), return as-is
    if any(ticker.endswith(suffix) for suffix in [".NS", ".BO", ".BSE", "=F", "=X"]):
        return ticker
    
    # Check if it has NSE: or BSE: prefix (TradingView format)
    if ":" in ticker:
        exchange, symbol = ticker.split(":", 1)
        exchange = exchange.upper()
        if exchange == "NSE":
            return f"{symbol}.NS"
        elif exchange in ("BSE", "BOM"):
            return f"{symbol}.BO"
        return symbol
    
    # Default: assume NSE
    return f"{ticker_upper}.NS"


def get_live_price(ticker: str) -> dict:
    """
    Fetch current/latest price for a ticker.
    Returns dict with price, change, volume etc.
    """
    yf_ticker = normalize_ticker_for_yfinance(ticker)
    
    try:
        stock = yf.Ticker(yf_ticker)
        info = stock.fast_info
        
        result = {
            "ticker": ticker,
            "yf_ticker": yf_ticker,
            "current_price": None,
            "previous_close": None,
            "day_change": None,
            "day_change_pct": None,
            "day_high": None,
            "day_low": None,
            "volume": None,
            "last_updated": datetime.now().isoformat(),
            "success": True,
        }
        
        # Try fast_info first
        try:
            result["current_price"] = float(info.last_price) if hasattr(info, 'last_price') else None
            result["previous_close"] = float(info.previous_close) if hasattr(info, 'previous_close') else None
            result["day_high"] = float(info.day_high) if hasattr(info, 'day_high') else None
            result["day_low"] = float(info.day_low) if hasattr(info, 'day_low') else None
        except Exception:
            pass
        
        # Fallback: use history
        if result["current_price"] is None:
            hist = stock.history(period="5d")
            if not hist.empty:
                result["current_price"] = float(hist["Close"].iloc[-1])
                if len(hist) >= 2:
                    result["previous_close"] = float(hist["Close"].iloc[-2])
                result["day_high"] = float(hist["High"].iloc[-1])
                result["day_low"] = float(hist["Low"].iloc[-1])
                result["volume"] = int(hist["Volume"].iloc[-1])
        
        # Compute change
        if result["current_price"] and result["previous_close"]:
            result["day_change"] = result["current_price"] - result["previous_close"]
            result["day_change_pct"] = (result["day_change"] / result["previous_close"]) * 100
        
        return result
        
    except Exception as e:
        logger.warning(f"Failed to fetch price for {ticker} ({yf_ticker}): {e}")
        return {
            "ticker": ticker,
            "yf_ticker": yf_ticker,
            "current_price": None,
            "success": False,
            "error": str(e),
        }


def get_historical_prices(ticker: str, start_date: datetime, end_date: datetime = None) -> list:
    """Fetch historical OHLCV data"""
    yf_ticker = normalize_ticker_for_yfinance(ticker)
    
    try:
        stock = yf.Ticker(yf_ticker)
        if end_date is None:
            end_date = datetime.now()
        
        hist = stock.history(start=start_date, end=end_date)
        
        if hist.empty:
            return []
        
        records = []
        for date, row in hist.iterrows():
            records.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]),
            })
        
        return records
        
    except Exception as e:
        logger.warning(f"Failed to fetch history for {ticker}: {e}")
        return []


def compute_returns(reference_price: float, current_price: float) -> dict:
    """Compute return metrics"""
    if not reference_price or reference_price == 0:
        return {"return_absolute": 0, "return_pct": 0}
    
    return_abs = current_price - reference_price
    return_pct = (return_abs / reference_price) * 100
    
    return {
        "return_absolute": round(return_abs, 2),
        "return_pct": round(return_pct, 2),
    }


def compute_period_returns(ticker: str, reference_price: float, reference_date: datetime) -> dict:
    """
    Compute period-wise returns (1D, 1W, 1M, 3M, 6M, 12M) since reference date.
    """
    now = datetime.now()
    yf_ticker = normalize_ticker_for_yfinance(ticker)
    
    result = {
        "return_1d": None,
        "return_1w": None,
        "return_1m": None,
        "return_3m": None,
        "return_6m": None,
        "return_12m": None,
        "current_price": None,
        "high_since": None,
        "low_since": None,
        "max_drawdown": None,
    }
    
    try:
        stock = yf.Ticker(yf_ticker)
        
        # Fetch history from reference date to now
        hist = stock.history(start=reference_date - timedelta(days=2), end=now)
        
        if hist.empty or reference_price == 0:
            return result
        
        current_price = float(hist["Close"].iloc[-1])
        result["current_price"] = current_price
        
        # High/Low since reference
        hist_since = hist[hist.index >= reference_date.strftime("%Y-%m-%d")]
        if not hist_since.empty:
            result["high_since"] = float(hist_since["High"].max())
            result["low_since"] = float(hist_since["Low"].min())
            
            # Max drawdown from peak
            running_max = hist_since["Close"].cummax()
            drawdown = (hist_since["Close"] - running_max) / running_max * 100
            result["max_drawdown"] = round(float(drawdown.min()), 2)
        
        # Period returns
        periods = {
            "return_1d": 1,
            "return_1w": 7,
            "return_1m": 30,
            "return_3m": 90,
            "return_6m": 180,
            "return_12m": 365,
        }
        
        for key, days in periods.items():
            target_date = now - timedelta(days=days)
            # Only compute if reference date is before this period
            if reference_date <= target_date:
                # Find closest price to target date
                period_hist = hist[hist.index >= target_date.strftime("%Y-%m-%d")]
                if not period_hist.empty:
                    period_start_price = float(period_hist["Close"].iloc[0])
                    result[key] = round((current_price - period_start_price) / period_start_price * 100, 2)
            else:
                # If approved less than this period ago, compute from reference
                days_since = (now - reference_date).days
                if days_since >= days:
                    result[key] = round((current_price - reference_price) / reference_price * 100, 2)
        
        return result
        
    except Exception as e:
        logger.warning(f"Failed to compute returns for {ticker}: {e}")
        return result


def update_all_performance(db: Session = None):
    """
    Update performance metrics for all approved alerts.
    Called by scheduler or manually.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        # Get all approved alerts
        approved_alerts = (
            db.query(TradingViewAlert)
            .join(AlertAction)
            .filter(AlertAction.decision == AlertStatus.APPROVED)
            .all()
        )
        
        updated = 0
        for alert in approved_alerts:
            action = alert.action
            if not action:
                continue
            
            # Update primary ticker performance
            primary_ticker = action.primary_ticker or alert.ticker
            if primary_ticker and action.price_at_decision:
                perf = _update_ticker_performance(
                    db, alert.id, primary_ticker,
                    action.price_at_decision,
                    action.decision_at,
                    is_primary=True
                )
                if perf:
                    updated += 1
            
            # Update secondary ticker performance (for relative alerts)
            if alert.alert_type == "RELATIVE" and action.secondary_ticker and action.secondary_price_at_decision:
                _update_ticker_performance(
                    db, alert.id, action.secondary_ticker,
                    action.secondary_price_at_decision,
                    action.decision_at,
                    is_primary=False
                )
        
        db.commit()
        logger.info(f"✅ Updated performance for {updated} alerts")
        return updated
        
    except Exception as e:
        logger.error(f"Error updating performance: {e}")
        db.rollback()
        return 0
    finally:
        if close_db:
            db.close()


def _update_ticker_performance(
    db: Session, alert_id: int, ticker: str,
    reference_price: float, reference_date: datetime,
    is_primary: bool = True
) -> AlertPerformance:
    """Update or create performance record for a ticker"""
    
    # Compute returns
    returns = compute_period_returns(ticker, reference_price, reference_date)
    
    if returns["current_price"] is None:
        return None
    
    # Find or create performance record
    perf = (
        db.query(AlertPerformance)
        .filter(
            AlertPerformance.alert_id == alert_id,
            AlertPerformance.ticker == ticker,
            AlertPerformance.is_primary == is_primary,
        )
        .first()
    )
    
    overall = compute_returns(reference_price, returns["current_price"])
    
    if perf is None:
        perf = AlertPerformance(
            alert_id=alert_id,
            ticker=ticker,
            is_primary=is_primary,
            reference_price=reference_price,
            reference_date=reference_date,
        )
        db.add(perf)
    
    # Update fields
    perf.current_price = returns["current_price"]
    perf.snapshot_date = datetime.now()
    perf.return_absolute = overall["return_absolute"]
    perf.return_pct = overall["return_pct"]
    perf.return_1d = returns["return_1d"]
    perf.return_1w = returns["return_1w"]
    perf.return_1m = returns["return_1m"]
    perf.return_3m = returns["return_3m"]
    perf.return_6m = returns["return_6m"]
    perf.return_12m = returns["return_12m"]
    perf.high_since = returns["high_since"]
    perf.low_since = returns["low_since"]
    perf.max_drawdown = returns["max_drawdown"]
    
    return perf
