from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, text
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
import json
import os

from models import (
    init_db, get_db, SessionLocal,
    TradingViewAlert, AlertAction, AlertPerformance, AlertStatus
)
from webhook_parser import parse_webhook_payload
from price_service import update_all_performance
from ai_engine import generate_technical_summary, synthesize_fm_rationale

app = FastAPI(title="JHAVERI FIE Engine")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class ActionRequest(BaseModel):
    alert_id: int
    decision: str                           
    primary_call: Optional[str] = None      
    conviction: Optional[str] = "MEDIUM"    
    fm_rationale_text: Optional[str] = None
    fm_rationale_audio: Optional[str] = None

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
        
        # FIX: Force Price to Float to prevent NoneType errors
        try:
            clean_price = float(parsed.get("price_at_alert", 0.0))
        except (ValueError, TypeError):
            clean_price = 0.0

        ai_summary = generate_technical_summary(
            ticker=parsed.get("ticker", "Unknown"), price=clean_price,
            indicators=parsed.get("indicator_values", {}), alert_message=parsed.get("alert_message", "")
        )
        
        alert = TradingViewAlert(
            ticker=parsed.get("ticker", "UNKNOWN"), exchange=parsed.get("exchange"), interval=parsed.get("interval"),
            price_at_alert=clean_price, alert_name=parsed.get("alert_name", "System Trigger"),
            alert_message=parsed.get("alert_message"), indicator_values=parsed.get("indicator_values"),
            signal_direction=parsed.get("signal_direction", "NEUTRAL"), signal_summary=ai_summary, 
            sector=parsed.get("sector"), status=AlertStatus.PENDING, processed=True
        )
        db.add(alert)
        db.commit()
        return JSONResponse(status_code=200, content={"success": True})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/alerts")
async def get_alerts(status: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(TradingViewAlert).order_by(desc(TradingViewAlert.received_at))
    if status and status != "All": query = query.filter(TradingViewAlert.status == status)
    
    results = []
    for a in query.limit(limit).all():
        action_data = None
        if a.action:
            action_data = {
                "call": a.action.primary_call.value if a.action.primary_call else None,
                "conviction": a.action.conviction,
                "remarks": a.action.fm_remarks
            }
        results.append({
            "id": a.id, "ticker": a.ticker, "price_at_alert": a.price_at_alert,
            "alert_name": a.alert_name, "signal_direction": a.signal_direction.value if a.signal_direction else "NEUTRAL",
            "signal_summary": a.signal_summary, "status": a.status.value if a.status else "PENDING",
            "received_at": a.received_at.isoformat() if a.received_at else None,
            "interval": a.interval, "action": action_data
        })
    return {"alerts": results}

@app.post("/api/alerts/{alert_id}/action")
async def take_action(alert_id: int, req: ActionRequest, db: Session = Depends(get_db)):
    alert = db.query(TradingViewAlert).filter(TradingViewAlert.id == alert_id).first()
    if not alert: raise HTTPException(status_code=404)
    
    decision = AlertStatus.APPROVED if req.decision == "APPROVED" else AlertStatus.DENIED
    action = db.query(AlertAction).filter_by(alert_id=alert_id).first() or AlertAction(alert_id=alert_id)
    
    action.decision = decision
    action.decision_at = datetime.now()
    action.primary_ticker = alert.ticker
    action.conviction = req.conviction
    
    # Store Raw Strings Safely
    action.primary_notes = req.primary_call 
    
    # AI Voice/Text Processing
    action.fm_remarks = synthesize_fm_rationale(
        ticker=alert.ticker, call=req.primary_call or "ACTION",
        text_note=req.fm_rationale_text, audio_b64=req.fm_rationale_audio
    ) if (req.fm_rationale_text or req.fm_rationale_audio) else None
    
    if not action.id: db.add(action)
    alert.status = decision
    
    if decision == AlertStatus.APPROVED and not db.query(AlertPerformance).filter_by(alert_id=alert.id).first():
        db.add(AlertPerformance(alert_id=alert.id, ticker=alert.ticker, is_primary=True, reference_price=alert.price_at_alert or 0.0, reference_date=datetime.now()))
        
    db.commit()
    return {"success": True}

@app.get("/api/performance")
async def get_performance(db: Session = Depends(get_db)):
    records = db.query(AlertPerformance, TradingViewAlert).join(TradingViewAlert).order_by(desc(AlertPerformance.reference_date)).all()
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
        "avg_return_pct": db.query(func.avg(AlertPerformance.return_pct)).scalar() or 0.0
    }
