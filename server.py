"""
FIE Phase 1 — FastAPI Backend Server
Webhook endpoint for TradingView + REST API for Dashboard
"""

from fastapi import FastAPI, Request, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_, text
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
from price_service import (
    get_live_price, update_all_performance, compute_returns, normalize_ticker_for_yfinance
)
from ai_engine import generate_technical_summary, synthesize_fm_rationale

# ─── Setup ─────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FIE Phase 1 — TradingView Alert Intelligence",
    version="2.0.0",
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
    decision: str                           
    primary_call: Optional[str] = None      
    primary_notes: Optional[str] = None
    primary_target_price: Optional[float] = None
    primary_stop_loss: Optional[float] = None
    secondary_call: Optional[str] = None    
    secondary_notes: Optional[str] = None
    secondary_target_price: Optional[float] = None
    secondary_stop_loss: Optional[float] = None
    conviction: Optional[str] = "MEDIUM"    
    fm_remarks: Optional[str] = None
    fm_rationale_text: Optional[str] = None
    fm_rationale_audio: Optional[str] = None
    chart_image_b64: Optional[str] = None  # NEW: For chart attachments

# ─── Startup & Auto-Migration ──────────────────────────
@app.on_event("startup")
async def startup():
    init_db()
    # Safely inject the new column for chart images without destroying the existing DB
    db = SessionLocal()
    try:
        db.execute(text("ALTER TABLE alert_actions ADD COLUMN chart_image_b64 TEXT"))
        db.commit()
        logger.info("Database migrated: Added chart_image_b64")
    except Exception:
        db.rollback() # Column likely already exists
    finally:
        db.close()
    logger.info("🚀 FIE Phase 1 Backend Started")

# ═══════════════════════════════════════════════════════
# WEBHOOK ENDPOINT
# ═══════════════════════════════════════════════════════

@app.post("/webhook/tradingview")
async def receive_tradingview_alert(request: Request, db: Session = Depends(get_db)):
    try:
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
        
        parsed = parse_webhook_payload(raw_data)
        
        # AI Processing
        ai_summary = generate_technical_summary(
            ticker=parsed.get("ticker", "Unknown"),
            price=parsed.get("price_at_alert", 0.0),
            indicators=parsed.get("indicator_values", {}),
            alert_message=parsed.get("alert_message", "")
        )
        
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
            alert_name=parsed["alert_name"] or "System Trigger",
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
            signal_summary=ai_summary, 
            sector=parsed["sector"],
            asset_class=parsed["asset_class"],
            raw_payload=parsed["raw_payload"],
            status=AlertStatus.PENDING,
            processed=True,
        )
        
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return JSONResponse(status_code=200, content={"success": True, "alert_id": alert.id})
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

# ═══════════════════════════════════════════════════════
# DASHBOARD API ROUTES
# ═══════════════════════════════════════════════════════

@app.get("/api/alerts")
async def get_alerts(
    status: Optional[str] = None, alert_type: Optional[str] = None, sector: Optional[str] = None,
    signal_direction: Optional[str] = None, ticker: Optional[str] = None, search: Optional[str] = None,
    limit: int = Query(default=200, le=500), offset: int = 0, db: Session = Depends(get_db)
):
    query = db.query(TradingViewAlert).order_by(desc(TradingViewAlert.received_at))
    if status and status != "All": query = query.filter(TradingViewAlert.status == status)
    if alert_type and alert_type != "All": query = query.filter(TradingViewAlert.alert_type == alert_type)
    if sector and sector != "All": query = query.filter(TradingViewAlert.sector == sector)
    if signal_direction and signal_direction != "All": query = query.filter(TradingViewAlert.signal_direction == signal_direction)
    if search:
        query = query.filter(or_(
            TradingViewAlert.ticker.ilike(f"%{search}%"),
            TradingViewAlert.alert_name.ilike(f"%{search}%")
        ))
    
    total = query.count()
    alerts = query.offset(offset).limit(limit).all()
    
    results = []
    for alert in alerts:
        action_data = None
        if alert.action:
            action_data = {
                "decision": alert.action.decision.value if alert.action.decision else None,
                "primary_call": alert.action.primary_call.value if alert.action.primary_call else None,
                "primary_ticker": alert.action.primary_ticker,
                "conviction": alert.action.conviction,
                "fm_remarks": alert.action.fm_remarks,
                "has_chart": bool(getattr(alert.action, 'chart_image_b64', None)),
                "decision_at": alert.action.decision_at.isoformat() if alert.action.decision_at else None,
            }
        results.append({
            "id": alert.id,
            "ticker": alert.ticker,
            "price_at_alert": alert.price_at_alert,
            "alert_name": alert.alert_name,
            "alert_message": alert.alert_message,
            "indicator_values": alert.indicator_values,
            "alert_type": alert.alert_type.value if alert.alert_type else None,
            "ratio_value": alert.ratio_value,
            "signal_direction": alert.signal_direction.value if alert.signal_direction else None,
            "signal_summary": alert.signal_summary,
            "sector": alert.sector,
            "status": alert.status.value if alert.status else None,
            "received_at": alert.received_at.isoformat() if alert.received_at else None,
            "action": action_data,
        })
    return {"total": total, "alerts": results}

@app.post("/api/alerts/{alert_id}/action")
async def take_action(alert_id: int, action_req: ActionRequest, db: Session = Depends(get_db)):
    alert = db.query(TradingViewAlert).filter(TradingViewAlert.id == alert_id).first()
    if not alert: raise HTTPException(status_code=404, detail="Alert not found")
    
    current_price = alert.price_at_alert
    existing_action = db.query(AlertAction).filter(AlertAction.alert_id == alert_id).first()
    action = existing_action if existing_action else AlertAction(alert_id=alert_id)
    decision = AlertStatus.APPROVED if action_req.decision.upper() == "APPROVED" else AlertStatus.DENIED
    
    final_remarks = action_req.fm_remarks
    if action_req.fm_rationale_text or action_req.fm_rationale_audio:
        final_remarks = synthesize_fm_rationale(
            ticker=alert.ticker,
            call=action_req.primary_call or "ACTION",
            text_note=action_req.fm_rationale_text,
            audio_b64=action_req.fm_rationale_audio
        )
    
    action.decision = decision
    action.decision_at = datetime.now()
    action.primary_call = ActionCall(action_req.primary_call) if action_req.primary_call else None
    action.primary_ticker = alert.numerator_ticker or alert.ticker
    action.primary_target_price = action_req.primary_target_price
    action.primary_stop_loss = action_req.primary_stop_loss
    action.conviction = action_req.conviction
    action.fm_remarks = final_remarks
    action.price_at_decision = current_price
    
    # Save Image
    if hasattr(action, 'chart_image_b64'):
        action.chart_image_b64 = action_req.chart_image_b64
    
    if not existing_action: db.add(action)
    alert.status = decision
    
    if decision == AlertStatus.APPROVED and not db.query(AlertPerformance).filter_by(alert_id=alert.id).first():
        perf = AlertPerformance(
            alert_id=alert.id,
            ticker=alert.ticker,
            is_primary=True,
            reference_price=alert.price_at_alert or alert.ratio_value or 0.0,
            reference_date=datetime.utcnow()
        )
        db.add(perf)
        
    db.commit()
    return {"success": True}

@app.delete("/api/alerts/{alert_id}")
async def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(TradingViewAlert).filter(TradingViewAlert.id == alert_id).first()
    if not alert: return {"success": False}
    db.query(AlertPerformance).filter(AlertPerformance.alert_id == alert_id).delete()
    db.query(AlertAction).filter(AlertAction.alert_id == alert_id).delete()
    db.delete(alert)
    db.commit()
    return {"success": True}

@app.get("/api/performance")
async def get_performance(limit: int = 100, db: Session = Depends(get_db)):
    records = db.query(AlertPerformance, TradingViewAlert, AlertAction).join(TradingViewAlert, AlertPerformance.alert_id == TradingViewAlert.id).join(AlertAction, AlertAction.alert_id == TradingViewAlert.id).filter(AlertAction.decision == AlertStatus.APPROVED).limit(limit).all()
    results = []
    for perf, alert, action in records:
        results.append({
            "alert_id": alert.id, "ticker": perf.ticker, "sector": alert.sector,
            "call": action.primary_call.value if action.primary_call else None,
            "reference_price": perf.reference_price, "current_price": perf.current_price,
            "return_pct": perf.return_pct, "approved_at": action.decision_at.isoformat() if action.decision_at else None,
        })
    return {"total": len(results), "performance": results}

@app.post("/api/performance/refresh")
async def refresh_performance(db: Session = Depends(get_db)):
    updated = update_all_performance(db)
    return {"success": True, "updated_count": updated}

@app.get("/api/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        "total_alerts": db.query(TradingViewAlert).count(),
        "pending": db.query(TradingViewAlert).filter(TradingViewAlert.status == AlertStatus.PENDING).count(),
        "today_alerts": db.query(TradingViewAlert).filter(TradingViewAlert.received_at >= today_start).count(),
        "avg_return_pct": db.query(func.avg(AlertPerformance.return_pct)).filter(AlertPerformance.is_primary == True).scalar() or 0
    }

@app.get("/api/sectors")
async def get_sectors(db: Session = Depends(get_db)):
    sectors = db.query(TradingViewAlert.sector).filter(TradingViewAlert.sector.isnot(None)).distinct().all()
    return {"sectors": [s[0] for s in sectors]}

@app.get("/health")
async def health(): return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
