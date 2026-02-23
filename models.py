"""
FIE Phase 1 — FastAPI Backend Server
Webhook endpoint for TradingView + REST API for Dashboard
"""

from fastapi import FastAPI, Request, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional, List
import json
import logging
import os

from models import (
    init_db, get_db, SessionLocal,
    TradingViewAlert, AlertAction, AlertPerformance, InstrumentMap,
    AlertStatus, AlertType, ActionCall, SignalDirection
)
from webhook_parser import parse_webhook_payload, get_recommended_alert_template

# ─── Setup ─────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FIE Phase 1 — TradingView Alert Intelligence",
    description="Jhaveri Securities Financial Intelligence Engine",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Pydantic Models ──────────────────────────────────

class ActionRequest(BaseModel):
    alert_id: int
    decision: str                           # APPROVED or DENIED
    primary_call: Optional[str] = None      # BUY, SELL, HOLD, etc.
    primary_notes: Optional[str] = None
    primary_target_price: Optional[float] = None
    primary_stop_loss: Optional[float] = None
    secondary_call: Optional[str] = None    # For relative alerts
    secondary_notes: Optional[str] = None
    secondary_target_price: Optional[float] = None
    secondary_stop_loss: Optional[float] = None
    conviction: Optional[str] = "MEDIUM"    # HIGH, MEDIUM, LOW
    fm_remarks: Optional[str] = None


class AlertFilterParams(BaseModel):
    status: Optional[str] = None
    alert_type: Optional[str] = None
    sector: Optional[str] = None
    signal_direction: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    ticker: Optional[str] = None
    limit: int = 50
    offset: int = 0


# ─── Startup ───────────────────────────────────────────

@app.on_event("startup")
async def startup():
    init_db()
    logger.info("🚀 FIE Phase 1 Backend Started (With TradingView Heartbeat Enabled)")


# ═══════════════════════════════════════════════════════
# WEBHOOK ENDPOINT — TradingView sends alerts here
# ═══════════════════════════════════════════════════════

@app.post("/webhook/tradingview")
async def receive_tradingview_alert(request: Request, db: Session = Depends(get_db)):
    """
    Receive webhook from TradingView.
    Handles both new alerts AND daily performance heartbeats.
    """
    try:
        # Read raw body
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            raw_data = await request.json()
        else:
            body = await request.body()
            raw_text = body.decode("utf-8")
            try:
                raw_data = json.loads(raw_text)
            except json.JSONDecodeError:
                raw_data = {"message": raw_text}
        
        logger.info(f"📥 Webhook received: {json.dumps(raw_data)[:200]}...")

        # ---------------------------------------------------------
        # 1. HEARTBEAT INTERCEPTION LOGIC (No yfinance needed)
        # ---------------------------------------------------------
        if raw_data.get("is_heartbeat") == True or str(raw_data.get("alert_name", "")).upper() == "HEARTBEAT":
            ticker = raw_data.get("ticker")
            current_price = raw_data.get("close")
            
            if ticker and current_price is not None:
                # Find all approved alerts matching this ticker (Absolute or Ratio)
                perfs = db.query(AlertPerformance).filter(AlertPerformance.ticker == ticker).all()
                updated = 0
                for perf in perfs:
                    try:
                        curr_p = float(current_price)
                        perf.current_price = curr_p
                        perf.snapshot_date = datetime.now()
                        
                        if perf.reference_price:
                            perf.return_absolute = perf.current_price - perf.reference_price
                            base_return = (perf.return_absolute / perf.reference_price) * 100
                            
                            # Look up the action to see if it was a SELL call
                            action = db.query(AlertAction).filter(AlertAction.alert_id == perf.alert_id).first()
                            
                            # If Fund Manager shorted/sold the asset, price dropping is a profit
                            if action and action.primary_call in [ActionCall.SELL, ActionCall.STRONG_SELL, ActionCall.REDUCE]:
                                perf.return_pct = -base_return 
                            else:
                                perf.return_pct = base_return
                                
                        updated += 1
                    except ValueError:
                        continue
                        
                db.commit()
                return JSONResponse(status_code=200, content={"success": True, "message": f"Heartbeat updated {updated} records for {ticker}"})

        # ---------------------------------------------------------
        # 2. NORMAL ALERT INGESTION
        # ---------------------------------------------------------
        parsed = parse_webhook_payload(raw_data)
        
        # Create alert record
        alert = TradingViewAlert(
            ticker=parsed["ticker"],
            exchange=parsed["exchange"],
            interval=parsed["interval"],
            price_open=parsed["price_open"],
            price_high=parsed["price_high"],
            price_low=parsed["price_low"],
            price_close=parsed["price_close"],
            price_at_alert=parsed["price_at_alert"],
            volume=parsed["volume"],
            time_utc=parsed["time_utc"],
            timenow_utc=parsed["timenow_utc"],
            alert_name=parsed["alert_name"],
            alert_message=parsed["alert_message"],
            alert_condition=parsed["alert_condition"],
            indicator_values=parsed["indicator_values"],
            alert_type=parsed["alert_type"],
            numerator_ticker=parsed["numerator_ticker"],
            denominator_ticker=parsed["denominator_ticker"],
            numerator_price=parsed["numerator_price"],
            denominator_price=parsed["denominator_price"],
            ratio_value=parsed["ratio_value"],
            signal_direction=parsed["signal_direction"],
            signal_strength=parsed["signal_strength"],
            signal_summary=parsed["signal_summary"],
            sector=parsed["sector"],
            asset_class=parsed["asset_class"],
            raw_payload=parsed["raw_payload"],
            status=AlertStatus.PENDING,
            processed=True,
        )
        
        db.add(alert)
        db.commit()
        db.refresh(alert)
        
        logger.info(f"✅ Alert #{alert.id} stored: {alert.ticker} - {alert.signal_direction}")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "alert_id": alert.id,
                "ticker": alert.ticker,
                "signal": alert.signal_direction.value if alert.signal_direction else None,
                "summary": alert.signal_summary,
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


# ═══════════════════════════════════════════════════════
# DASHBOARD API ROUTES
# ═══════════════════════════════════════════════════════

@app.get("/api/alerts")
async def get_alerts(
    status: Optional[str] = None,
    alert_type: Optional[str] = None,
    sector: Optional[str] = None,
    signal_direction: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    ticker: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Get alerts with filters"""
    query = db.query(TradingViewAlert).order_by(desc(TradingViewAlert.received_at))
    
    if status:
        query = query.filter(TradingViewAlert.status == status)
    if alert_type:
        query = query.filter(TradingViewAlert.alert_type == alert_type)
    if sector:
        query = query.filter(TradingViewAlert.sector == sector)
    if signal_direction:
        query = query.filter(TradingViewAlert.signal_direction == signal_direction)
    if ticker:
        query = query.filter(TradingViewAlert.ticker.ilike(f"%{ticker}%"))
    if date_from:
        query = query.filter(TradingViewAlert.received_at >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(TradingViewAlert.received_at <= datetime.fromisoformat(date_to))
    if search:
        query = query.filter(
            or_(
                TradingViewAlert.ticker.ilike(f"%{search}%"),
                TradingViewAlert.alert_name.ilike(f"%{search}%"),
                TradingViewAlert.signal_summary.ilike(f"%{search}%"),
                TradingViewAlert.sector.ilike(f"%{search}%"),
            )
        )
    
    total = query.count()
    alerts = query.offset(offset).limit(limit).all()
    
    results = []
    for alert in alerts:
        action_data = None
        if alert.action:
            action_data = {
                "id": alert.action.id,
                "decision": alert.action.decision.value if alert.action.decision else None,
                "primary_call": alert.action.primary_call.value if alert.action.primary_call else None,
                "primary_ticker": alert.action.primary_ticker,
                "primary_notes": alert.action.primary_notes,
                "primary_target_price": alert.action.primary_target_price,
                "primary_stop_loss": alert.action.primary_stop_loss,
                "secondary_call": alert.action.secondary_call.value if alert.action.secondary_call else None,
                "secondary_ticker": alert.action.secondary_ticker,
                "secondary_notes": alert.action.secondary_notes,
                "conviction": alert.action.conviction,
                "fm_remarks": alert.action.fm_remarks,
                "price_at_decision": alert.action.price_at_decision,
                "decision_at": alert.action.decision_at.isoformat() if alert.action.decision_at else None,
            }
        
        results.append({
            "id": alert.id,
            "ticker": alert.ticker,
            "exchange": alert.exchange,
            "interval": alert.interval,
            "price_at_alert": alert.price_at_alert,
            "price_open": alert.price_open,
            "price_high": alert.price_high,
            "price_low": alert.price_low,
            "price_close": alert.price_close,
            "volume": alert.volume,
            "alert_name": alert.alert_name,
            "alert_message": alert.alert_message,
            "alert_condition": alert.alert_condition,
            "indicator_values": alert.indicator_values,
            "alert_type": alert.alert_type.value if alert.alert_type else None,
            "numerator_ticker": alert.numerator_ticker,
            "denominator_ticker": alert.denominator_ticker,
            "numerator_price": alert.numerator_price,
            "denominator_price": alert.denominator_price,
            "ratio_value": alert.ratio_value,
            "signal_direction": alert.signal_direction.value if alert.signal_direction else None,
            "signal_strength": alert.signal_strength,
            "signal_summary": alert.signal_summary,
            "sector": alert.sector,
            "asset_class": alert.asset_class,
            "status": alert.status.value if alert.status else None,
            "received_at": alert.received_at.isoformat() if alert.received_at else None,
            "action": action_data,
        })
    
    return {"total": total, "alerts": results}


@app.get("/api/alerts/{alert_id}")
async def get_alert_detail(alert_id: int, db: Session = Depends(get_db)):
    """Get single alert with full details"""
    alert = db.query(TradingViewAlert).filter(TradingViewAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {
        "alert": {
            "id": alert.id,
            "ticker": alert.ticker,
            "exchange": alert.exchange,
            "interval": alert.interval,
            "price_at_alert": alert.price_at_alert,
            "price_open": alert.price_open,
            "price_high": alert.price_high,
            "price_low": alert.price_low,
            "price_close": alert.price_close,
            "volume": alert.volume,
            "alert_name": alert.alert_name,
            "alert_message": alert.alert_message,
            "alert_condition": alert.alert_condition,
            "indicator_values": alert.indicator_values,
            "alert_type": alert.alert_type.value if alert.alert_type else None,
            "numerator_ticker": alert.numerator_ticker,
            "denominator_ticker": alert.denominator_ticker,
            "numerator_price": alert.numerator_price,
            "denominator_price": alert.denominator_price,
            "ratio_value": alert.ratio_value,
            "signal_direction": alert.signal_direction.value if alert.signal_direction else None,
            "signal_strength": alert.signal_strength,
            "signal_summary": alert.signal_summary,
            "sector": alert.sector,
            "asset_class": alert.asset_class,
            "status": alert.status.value if alert.status else None,
            "received_at": alert.received_at.isoformat() if alert.received_at else None,
            "raw_payload": alert.raw_payload,
        }
    }


# ─── Take Action on Alert ─────────────────────────────

@app.post("/api/alerts/{alert_id}/action")
async def take_action(alert_id: int, action_req: ActionRequest, db: Session = Depends(get_db)):
    """Fund Manager takes action and system initializes performance tracking"""
    
    alert = db.query(TradingViewAlert).filter(TradingViewAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Use the alert price/ratio as the execution price (No yfinance needed)
    execution_price = alert.ratio_value if alert.alert_type == AlertType.RELATIVE else alert.price_at_alert
    secondary_price = alert.denominator_price if alert.alert_type == AlertType.RELATIVE else None
    
    # Create or update action
    existing_action = db.query(AlertAction).filter(AlertAction.alert_id == alert_id).first()
    
    if existing_action:
        action = existing_action
    else:
        action = AlertAction(alert_id=alert_id)
    
    # Map decision
    decision = AlertStatus.APPROVED if action_req.decision.upper() == "APPROVED" else AlertStatus.DENIED
    
    action.decision = decision
    action.decision_at = datetime.now()
    action.primary_call = ActionCall(action_req.primary_call) if action_req.primary_call else None
    
    # Critical update: Bind the primary ticker to the full ratio (e.g., GOLD/SENSEX)
    action.primary_ticker = alert.ticker
    action.primary_notes = action_req.primary_notes
    action.primary_target_price = action_req.primary_target_price
    action.primary_stop_loss = action_req.primary_stop_loss
    action.secondary_call = ActionCall(action_req.secondary_call) if action_req.secondary_call else None
    action.secondary_ticker = alert.denominator_ticker
    action.secondary_notes = action_req.secondary_notes
    action.secondary_target_price = action_req.secondary_target_price
    action.secondary_stop_loss = action_req.secondary_stop_loss
    action.conviction = action_req.conviction
    action.fm_remarks = action_req.fm_remarks
    action.price_at_decision = execution_price
    action.secondary_price_at_decision = secondary_price
    
    if not existing_action:
        db.add(action)
    
    # Update alert status
    alert.status = decision
    
    # ---------------------------------------------------------
    # 3. INITIALIZE PERFORMANCE TRACKER ON APPROVAL
    # ---------------------------------------------------------
    if decision == AlertStatus.APPROVED and execution_price is not None:
        perf = db.query(AlertPerformance).filter(
            AlertPerformance.alert_id == alert_id, 
            AlertPerformance.is_primary == True
        ).first()
        
        if not perf:
            perf = AlertPerformance(alert_id=alert_id, is_primary=True)
            db.add(perf)
        
        perf.ticker = alert.ticker # Tracks the ratio or stock directly
        perf.reference_price = execution_price
        perf.reference_date = datetime.now()
        perf.current_price = execution_price
        perf.return_absolute = 0.0
        perf.return_pct = 0.0
    
    db.commit()
    
    return {
        "success": True,
        "alert_id": alert_id,
        "decision": decision.value,
        "price_at_decision": execution_price,
    }


# ─── Performance Tracking ─────────────────────────────

@app.get("/api/performance")
async def get_performance(
    ticker: Optional[str] = None,
    sector: Optional[str] = None,
    call_type: Optional[str] = None,
    sort_by: str = "return_pct",
    sort_order: str = "desc",
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    """Get performance of all approved alerts"""
    
    query = (
        db.query(AlertPerformance, TradingViewAlert, AlertAction)
        .join(TradingViewAlert, AlertPerformance.alert_id == TradingViewAlert.id)
        .join(AlertAction, AlertAction.alert_id == TradingViewAlert.id)
        .filter(AlertAction.decision == AlertStatus.APPROVED)
        .filter(AlertPerformance.is_primary == True)
    )
    
    if ticker:
        query = query.filter(AlertPerformance.ticker.ilike(f"%{ticker}%"))
    if sector:
        query = query.filter(TradingViewAlert.sector == sector)
    if call_type:
        query = query.filter(AlertAction.primary_call == call_type)
    
    # Sorting
    sort_col = getattr(AlertPerformance, sort_by, AlertPerformance.return_pct)
    if sort_order == "desc":
        query = query.order_by(desc(sort_col))
    else:
        query = query.order_by(sort_col)
    
    records = query.limit(limit).all()
    
    results = []
    for perf, alert, action in records:
        results.append({
            "alert_id": alert.id,
            "ticker": perf.ticker,
            "alert_name": alert.alert_name,
            "sector": alert.sector,
            "signal_direction": alert.signal_direction.value if alert.signal_direction else None,
            "call": action.primary_call.value if action.primary_call else None,
            "conviction": action.conviction,
            "reference_price": perf.reference_price,
            "current_price": perf.current_price,
            "return_pct": perf.return_pct,
            "return_absolute": perf.return_absolute,
            "return_1d": perf.return_1d,
            "return_1w": perf.return_1w,
            "return_1m": perf.return_1m,
            "return_3m": perf.return_3m,
            "return_6m": perf.return_6m,
            "return_12m": perf.return_12m,
            "high_since": perf.high_since,
            "low_since": perf.low_since,
            "max_drawdown": perf.max_drawdown,
            "approved_at": action.decision_at.isoformat() if action.decision_at else None,
            "last_updated": perf.snapshot_date.isoformat() if perf.snapshot_date else None,
        })
    
    return {"total": len(results), "performance": results}


# ─── Dashboard Stats ───────────────────────────────────

@app.get("/api/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Summary statistics for dashboard header"""
    
    total_alerts = db.query(TradingViewAlert).count()
    pending = db.query(TradingViewAlert).filter(TradingViewAlert.status == AlertStatus.PENDING).count()
    approved = db.query(TradingViewAlert).filter(TradingViewAlert.status == AlertStatus.APPROVED).count()
    denied = db.query(TradingViewAlert).filter(TradingViewAlert.status == AlertStatus.DENIED).count()
    
    # Today's alerts
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_alerts = db.query(TradingViewAlert).filter(TradingViewAlert.received_at >= today_start).count()
    
    # Signal distribution
    bullish = db.query(TradingViewAlert).filter(TradingViewAlert.signal_direction == SignalDirection.BULLISH).count()
    bearish = db.query(TradingViewAlert).filter(TradingViewAlert.signal_direction == SignalDirection.BEARISH).count()
    
    # Average performance of approved alerts
    avg_return = db.query(func.avg(AlertPerformance.return_pct)).filter(AlertPerformance.is_primary == True).scalar()
    
    # Top performing approved alert
    top_performer = (
        db.query(AlertPerformance)
        .filter(AlertPerformance.is_primary == True)
        .order_by(desc(AlertPerformance.return_pct))
        .first()
    )
    
    # Worst performing
    worst_performer = (
        db.query(AlertPerformance)
        .filter(AlertPerformance.is_primary == True)
        .order_by(AlertPerformance.return_pct)
        .first()
    )
    
    # Sector-wise alert count
    sector_counts = (
        db.query(TradingViewAlert.sector, func.count(TradingViewAlert.id))
        .filter(TradingViewAlert.sector.isnot(None))
        .group_by(TradingViewAlert.sector)
        .all()
    )
    
    # Win rate (approved alerts with positive returns)
    total_with_perf = db.query(AlertPerformance).filter(AlertPerformance.is_primary == True, AlertPerformance.return_pct.isnot(None)).count()
    winners = db.query(AlertPerformance).filter(AlertPerformance.is_primary == True, AlertPerformance.return_pct > 0).count()
    win_rate = round((winners / total_with_perf * 100), 1) if total_with_perf > 0 else 0
    
    return {
        "total_alerts": total_alerts,
        "pending": pending,
        "approved": approved,
        "denied": denied,
        "today_alerts": today_alerts,
        "bullish_count": bullish,
        "bearish_count": bearish,
        "avg_return_pct": round(avg_return, 2) if avg_return else 0,
        "win_rate": win_rate,
        "top_performer": {
            "ticker": top_performer.ticker if top_performer else None,
            "return_pct": top_performer.return_pct if top_performer else None,
        },
        "worst_performer": {
            "ticker": worst_performer.ticker if worst_performer else None,
            "return_pct": worst_performer.return_pct if worst_performer else None,
        },
        "sector_distribution": {s: c for s, c in sector_counts},
    }


# ─── Sectors & Filters ────────────────────────────────

@app.get("/api/sectors")
async def get_sectors(db: Session = Depends(get_db)):
    """Get all unique sectors from alerts"""
    sectors = (
        db.query(TradingViewAlert.sector)
        .filter(TradingViewAlert.sector.isnot(None))
        .distinct()
        .all()
    )
    return {"sectors": [s[0] for s in sectors]}


@app.get("/api/instruments")
async def get_instruments(db: Session = Depends(get_db)):
    """Get instrument reference data"""
    instruments = db.query(InstrumentMap).all()
    return {
        "instruments": [
            {
                "ticker": i.ticker,
                "name": i.name,
                "sector": i.sector,
                "asset_class": i.asset_class,
                "exchange": i.exchange,
                "is_index": i.is_index,
            }
            for i in instruments
        ]
    }


# ─── Webhook Template ─────────────────────────────────

@app.get("/api/webhook-template")
async def webhook_template():
    """Get recommended TradingView alert message template"""
    return get_recommended_alert_template()


# ─── Test Endpoint ─────────────────────────────────────

@app.post("/api/test-alert")
async def send_test_alert(db: Session = Depends(get_db)):
    """Send a simulated TradingView alert for testing"""
    
    test_alerts = [
        {
            "ticker": "NIFTY",
            "exchange": "NSE",
            "interval": "1D",
            "open": 24150.30,
            "high": 24280.50,
            "low": 24050.75,
            "close": 24210.85,
            "volume": 285000000,
            "timenow": datetime.now().isoformat(),
            "alert_name": "Nifty 50 RSI Overbought",
            "signal": "BEARISH",
            "indicators": {
                "rsi": 73.5,
                "macd": 45.2,
                "ema_200": 23150.40,
                "adx": 28.3,
            },
            "message": "Nifty 50 RSI crossed above 70 - overbought zone. MACD histogram turning negative. Consider reducing exposure."
        },
        {
            "ticker": "NIFTYIT/NIFTY",
            "exchange": "NSE",
            "interval": "1D",
            "close": 1.42,
            "timenow": datetime.now().isoformat(),
            "alert_name": "IT vs Nifty Relative Strength",
            "numerator": "NIFTYIT",
            "denominator": "NIFTY",
            "numerator_price": 34520.60,
            "denominator_price": 24210.85,
            "ratio": 1.4259,
            "signal": "BULLISH",
            "indicators": {
                "relative_strength": 1.4259,
                "rsi": 62.1,
                "macd": 0.023,
            },
            "message": "IT sector outperforming Nifty. Relative strength ratio at 52-week high. IT allocation increase recommended."
        },
    ]
    
    created_ids = []
    for test_data in test_alerts:
        parsed = parse_webhook_payload(test_data)
        alert = TradingViewAlert(
            ticker=parsed["ticker"],
            exchange=parsed["exchange"],
            interval=parsed["interval"],
            price_open=parsed["price_open"],
            price_high=parsed["price_high"],
            price_low=parsed["price_low"],
            price_close=parsed["price_close"],
            price_at_alert=parsed["price_at_alert"],
            volume=parsed["volume"],
            time_utc=parsed["time_utc"],
            timenow_utc=parsed["timenow_utc"],
            alert_name=parsed["alert_name"],
            alert_message=parsed["alert_message"],
            alert_condition=parsed["alert_condition"],
            indicator_values=parsed["indicator_values"],
            alert_type=parsed["alert_type"],
            numerator_ticker=parsed["numerator_ticker"],
            denominator_ticker=parsed["denominator_ticker"],
            numerator_price=parsed["numerator_price"],
            denominator_price=parsed["denominator_price"],
            ratio_value=parsed["ratio_value"],
            signal_direction=parsed["signal_direction"],
            signal_strength=parsed["signal_strength"],
            signal_summary=parsed["signal_summary"],
            sector=parsed["sector"],
            asset_class=parsed["asset_class"],
            raw_payload=parsed["raw_payload"],
            status=AlertStatus.PENDING,
            processed=True,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        created_ids.append(alert.id)
    
    return {"success": True, "test_alerts_created": created_ids, "count": len(created_ids)}


# ─── Health Check ──────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "FIE Phase 1", "timestamp": datetime.now().isoformat()}


# ─── Run ───────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
