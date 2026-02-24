from fastapi import FastAPI, Request, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_, text
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
import json
import logging
import os

from models import (
    init_db, get_db, SessionLocal,
    TradingViewAlert, AlertAction, AlertPerformance, InstrumentMap,
    AlertStatus, AlertType, SignalDirection
)
from webhook_parser import parse_webhook_payload, get_recommended_alert_template
from price_service import get_live_price, update_all_performance
from ai_engine import generate_technical_summary, synthesize_fm_rationale

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="JHAVERI FIE Engine", version="2.1.0")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

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
    chart_image_b64: Optional[str] = None  

@app.on_event("startup")
async def startup():
    init_db()
    db = SessionLocal()
    try:
        db.execute(text("ALTER TABLE alert_actions ADD COLUMN chart_image_b64 TEXT"))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

@app.post("/webhook/tradingview")
async def receive_tradingview_alert(request: Request, db: Session = Depends(get_db)):
    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            raw_data = await request.json()
        else:
            raw_data = json.loads((await request.body()).decode("utf-8"))
        
        parsed = parse_webhook_payload(raw_data)
        
        ai_summary = generate_technical_summary(
            ticker=parsed.get("ticker", "Unknown"),
            price=parsed.get("price_at_alert", 0.0),
            indicators=parsed.get("indicator_values", {}),
            alert_message=parsed.get("alert_message", "")
        )
        
        alert = TradingViewAlert(
            ticker=parsed["ticker"], exchange=parsed["exchange"], interval=parsed["interval"],
            price_at_alert=parsed["price_at_alert"], alert_name=parsed["alert_name"] or "System Trigger",
            alert_message=parsed["alert_message"], indicator_values=parsed["indicator_values"],
            alert_type=parsed["alert_type"], signal_direction=parsed["signal_direction"],
            signal_summary=ai_summary, sector=parsed["sector"], status=AlertStatus.PENDING, processed=True
        )
        db.add(alert)
        db.commit()
        return JSONResponse(status_code=200, content={"success": True})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/alerts")
async def get_alerts(status: Optional[str] = None, limit: int = 200, db: Session = Depends(get_db)):
    query = db.query(TradingViewAlert).order_by(desc(TradingViewAlert.received_at))
    if status and status != "All": query = query.filter(TradingViewAlert.status == status)
    
    alerts = query.limit(limit).all()
    results = []
    for a in alerts:
        results.append({
            "id": a.id, "ticker": a.ticker, "price_at_alert": a.price_at_alert,
            "alert_name": a.alert_name, "signal_direction": a.signal_direction.value if a.signal_direction else None,
            "signal_summary": a.signal_summary, "status": a.status.value if a.status else None,
            "received_at": a.received_at.isoformat() if a.received_at else None,
            "interval": a.interval, "sector": a.sector
        })
    return {"alerts": results}

@app.post("/api/alerts/{alert_id}/action")
async def take_action(alert_id: int, req: ActionRequest, db: Session = Depends(get_db)):
    alert = db.query(TradingViewAlert).filter(TradingViewAlert.id == alert_id).first()
    if not alert: raise HTTPException(status_code=404)
    
    decision = AlertStatus.APPROVED if req.decision == "APPROVED" else AlertStatus.DENIED
    
    # Safe fallback for non-enum values
    action = db.query(AlertAction).filter_by(alert_id=alert_id).first() or AlertAction(alert_id=alert_id)
    action.decision = decision
    action.decision_at = datetime.now()
    action.primary_ticker = alert.ticker
    action.conviction = req.conviction
    
    # Store raw strings instead of forcing enums to prevent crashes
    action.primary_notes = req.primary_call 
    
    action.fm_remarks = synthesize_fm_rationale(
        ticker=alert.ticker, call=req.primary_call or "ACTION",
        text_note=req.fm_rationale_text, audio_b64=req.fm_rationale_audio
    ) if (req.fm_rationale_text or req.fm_rationale_audio) else req.fm_remarks
    
    if not action.id: db.add(action)
    alert.status = decision
    
    if decision == AlertStatus.APPROVED and not db.query(AlertPerformance).filter_by(alert_id=alert.id).first():
        db.add(AlertPerformance(alert_id=alert.id, ticker=alert.ticker, is_primary=True, reference_price=alert.price_at_alert or 0.0, reference_date=datetime.now()))
        
    db.commit()
    return {"success": True}

@app.delete("/api/alerts/{alert_id}")
async def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    db.query(TradingViewAlert).filter(TradingViewAlert.id == alert_id).delete()
    db.commit()
    return {"success": True}

@app.get("/api/performance")
async def get_performance(db: Session = Depends(get_db)):
    records = db.query(AlertPerformance, TradingViewAlert).join(TradingViewAlert).all()
    return {"performance": [{"ticker": p.ticker, "reference_price": p.reference_price, "current_price": p.current_price, "return_pct": p.return_pct, "approved_at": p.reference_date.isoformat()} for p, a in records]}

@app.post("/api/performance/refresh")
async def refresh_performance(db: Session = Depends(get_db)):
    updated = update_all_performance(db)
    return {"success": True, "updated_count": updated}

@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    return {
        "total_alerts": db.query(TradingViewAlert).count(),
        "pending": db.query(TradingViewAlert).filter(TradingViewAlert.status == AlertStatus.PENDING).count(),
        "avg_return_pct": db.query(func.avg(AlertPerformance.return_pct)).scalar() or 0
    }
