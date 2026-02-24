"""
FIE Phase 1 — FastAPI Backend Server
Webhook endpoint for TradingView + REST API for Dashboard
"""

from fastapi import FastAPI, Request, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
import json
import logging
import os

from models import (
    init_db, get_db,
    TradingViewAlert, AlertAction, AlertPerformance, InstrumentMap,
    AlertStatus, AlertType, SignalDirection
)
from webhook_parser import parse_webhook_payload, get_recommended_alert_template

# ─── Import the new AI Engine ──────────────────────────
from ai_engine import generate_technical_summary, synthesize_fm_rationale

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

@app.on_event("startup")
def on_startup():
    init_db()

# ─── Pydantic Models ──────────────────────────────────
class ActionRequest(BaseModel):
    alert_id: int
    decision: str                           # APPROVED or DENIED
    primary_call: Optional[str] = None
    primary_notes: Optional[str] = None
    primary_target_price: Optional[float] = None
    primary_stop_loss: Optional[float] = None
    secondary_call: Optional[str] = None
    secondary_notes: Optional[str] = None
    secondary_target_price: Optional[float] = None
    secondary_stop_loss: Optional[float] = None
    conviction: Optional[str] = None
    fm_remarks: Optional[str] = None
    # ── AI Rationale Fields ──
    fm_rationale_text: Optional[str] = None
    fm_rationale_audio: Optional[str] = None

# ─── Endpoints ─────────────────────────────────────────

@app.post("/webhook/tradingview")
async def receive_tradingview_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        payload_dict = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")

    # 1. Handle Daily Heartbeat for Performance Tracking
    if payload_dict.get("is_heartbeat", False):
        return {"status": "heartbeat processed"}

    # 2. Parse Webhook
    parsed = parse_webhook_payload(payload_dict)

    # 3. AI Processing: Generate Technical Summary from Raw Data
    ai_summary = generate_technical_summary(
        ticker=parsed.get("ticker", "Unknown"),
        price=parsed.get("price_at_alert", 0.0),
        indicators=parsed.get("indicator_values", {}),
        alert_message=parsed.get("alert_message", "No message provided")
    )

    # 4. Save Alert to Database
    alert = TradingViewAlert(
        ticker=parsed.get("ticker"),
        exchange=parsed.get("exchange"),
        interval=parsed.get("interval"),
        price_open=parsed.get("price_open"),
        price_high=parsed.get("price_high"),
        price_low=parsed.get("price_low"),
        price_close=parsed.get("price_close"),
        price_at_alert=parsed.get("price_at_alert"),
        volume=parsed.get("volume"),
        time_utc=parsed.get("time_utc"),
        timenow_utc=parsed.get("timenow_utc"),
        alert_name=parsed.get("alert_name"),
        alert_message=parsed.get("alert_message"),
        alert_condition=parsed.get("alert_condition"),
        indicator_values=parsed.get("indicator_values"),
        alert_type=parsed.get("alert_type"),
        numerator_ticker=parsed.get("numerator_ticker"),
        denominator_ticker=parsed.get("denominator_ticker"),
        numerator_price=parsed.get("numerator_price"),
        denominator_price=parsed.get("denominator_price"),
        ratio_value=parsed.get("ratio_value"),
        signal_direction=parsed.get("signal_direction"),
        signal_strength=parsed.get("signal_strength"),
        signal_summary=ai_summary, # <--- AI Summary injected here
        sector=parsed.get("sector"),
        asset_class=parsed.get("asset_class"),
        raw_payload=parsed.get("raw_payload"),
        status=AlertStatus.PENDING,
        processed=False,
    )

    db.add(alert)
    db.commit()
    db.refresh(alert)
    logger.info(f"📥 Webhook received & AI parsed: {alert.ticker} | ID: {alert.id}")

    return {"status": "success", "alert_id": alert.id, "message": "Alert logged."}


@app.get("/api/alerts")
def get_alerts(
    status: Optional[str] = None,
    signal_direction: Optional[str] = None,
    alert_type: Optional[str] = None,
    sector: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    query = db.query(TradingViewAlert)

    if status and status != "All":
        query = query.filter(TradingViewAlert.status == status)
    if signal_direction and signal_direction != "All":
        query = query.filter(TradingViewAlert.signal_direction == signal_direction)
    if alert_type and alert_type != "All":
        query = query.filter(TradingViewAlert.alert_type == alert_type)
    if sector and sector != "All":
        query = query.filter(TradingViewAlert.sector == sector)
    if search:
        search_term = f"%{search}%"
        query = query.filter(or_(
            TradingViewAlert.ticker.ilike(search_term),
            TradingViewAlert.alert_name.ilike(search_term),
            TradingViewAlert.alert_message.ilike(search_term)
        ))

    alerts = query.order_by(desc(TradingViewAlert.received_at)).limit(limit).all()

    results = []
    for a in alerts:
        alert_dict = {c.name: getattr(a, c.name) for c in a.__table__.columns}
        if a.action:
            alert_dict["action"] = {c.name: getattr(a.action, c.name) for c in a.action.__table__.columns}
        results.append(alert_dict)

    return {"total": len(results), "alerts": results}


@app.post("/api/alerts/{alert_id}/action")
def action_alert(alert_id: int, payload: ActionRequest, db: Session = Depends(get_db)):
    alert = db.query(TradingViewAlert).filter(TradingViewAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert.status != AlertStatus.PENDING:
        raise HTTPException(status_code=400, detail="Alert already processed")

    # ── AI Processing: Synthesize the Fund Manager's voice/text rationale
    formal_view = synthesize_fm_rationale(
        ticker=alert.ticker,
        call=payload.primary_call or "ACTION",
        text_note=payload.fm_rationale_text,
        audio_b64=payload.fm_rationale_audio
    )

    # Use AI formalized view as remarks
    final_remarks = payload.fm_remarks if payload.fm_remarks else formal_view

    action = AlertAction(
        alert_id=alert.id,
        decision=payload.decision,
        primary_call=payload.primary_call,
        primary_notes=payload.primary_notes,
        primary_target_price=payload.primary_target_price,
        primary_stop_loss=payload.primary_stop_loss,
        secondary_call=payload.secondary_call,
        secondary_notes=payload.secondary_notes,
        secondary_target_price=payload.secondary_target_price,
        secondary_stop_loss=payload.secondary_stop_loss,
        conviction=payload.conviction,
        fm_remarks=final_remarks, # <--- AI View Injected
        price_at_decision=alert.price_at_alert,
    )

    db.add(action)
    alert.status = payload.decision
    alert.processed = True

    # Initialize Performance Tracking if Approved
    if payload.decision == "APPROVED":
        perf = AlertPerformance(
            alert_id=alert.id,
            ticker=alert.ticker or alert.numerator_ticker or "UNKNOWN",
            is_primary=True,
            reference_price=alert.price_at_alert or alert.ratio_value or 0.0,
            reference_date=datetime.utcnow()
        )
        db.add(perf)

    db.commit()
    return {"success": True, "action_id": action.id, "message": "Decision recorded."}


@app.delete("/api/alerts/{alert_id}")
def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(TradingViewAlert).filter(TradingViewAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert.action:
        db.delete(alert.action)
    for perf in alert.performance_records:
        db.delete(perf)

    db.delete(alert)
    db.commit()
    return {"success": True, "message": "Alert deleted"}


@app.get("/api/performance")
def get_performance(limit: int = 100, db: Session = Depends(get_db)):
    records = db.query(AlertPerformance).order_by(desc(AlertPerformance.snapshot_date)).limit(limit).all()
    results = []
    for p in records:
        alert = p.alert
        action = alert.action if alert else None
        results.append({
            "id": p.id,
            "alert_id": p.alert_id,
            "ticker": p.ticker,
            "reference_price": p.reference_price,
            "current_price": p.current_price,
            "return_pct": p.return_pct,
            "return_1d": p.return_1d,
            "return_1w": p.return_1w,
            "return_1m": p.return_1m,
            "max_drawdown": p.max_drawdown,
            "approved_at": action.created_at.isoformat() if action else None,
            "call": action.primary_call if action else "UNKNOWN",
            "conviction": action.conviction if action else "UNKNOWN",
            "sector": alert.sector if alert else "UNKNOWN"
        })
    return {"total": len(results), "performance": results}


@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    total_alerts = db.query(TradingViewAlert).count()
    today_alerts = db.query(TradingViewAlert).filter(TradingViewAlert.received_at >= today_start).count()
    pending = db.query(TradingViewAlert).filter(TradingViewAlert.status == AlertStatus.PENDING).count()
    approved = db.query(TradingViewAlert).filter(TradingViewAlert.status == AlertStatus.APPROVED).count()

    bullish = db.query(TradingViewAlert).filter(TradingViewAlert.signal_direction == SignalDirection.BULLISH).count()
    bearish = db.query(TradingViewAlert).filter(TradingViewAlert.signal_direction == SignalDirection.BEARISH).count()

    perfs = db.query(AlertPerformance).filter(AlertPerformance.return_pct != None).all()
    avg_return = sum(p.return_pct for p in perfs) / len(perfs) if perfs else 0.0
    winners = len([p for p in perfs if p.return_pct and p.return_pct > 0])
    win_rate = (winners / len(perfs) * 100) if perfs else 0.0

    top_perf = None
    if perfs:
        top_record = max(perfs, key=lambda x: x.return_pct or -999)
        top_perf = {
            "ticker": top_record.ticker,
            "return_pct": top_record.return_pct
        }

    return {
        "total_alerts": total_alerts,
        "today_alerts": today_alerts,
        "pending": pending,
        "approved": approved,
        "bullish_count": bullish,
        "bearish_count": bearish,
        "avg_return_pct": avg_return,
        "win_rate": win_rate,
        "top_performer": top_perf
    }


@app.get("/api/sectors")
def get_sectors(db: Session = Depends(get_db)):
    sectors = db.query(InstrumentMap.sector).filter(InstrumentMap.sector != None).distinct().all()
    return {"sectors": [s[0] for s in sectors if s[0]]}


@app.get("/api/webhook-template")
def get_template():
    return {
        "template": get_recommended_alert_template(AlertType.ABSOLUTE),
        "template_relative": get_recommended_alert_template(AlertType.RELATIVE)
    }


@app.post("/api/test-alert")
def create_test_alert(db: Session = Depends(get_db)):
    import random
    mock_alerts = [
        {
            "ticker": "RELIANCE", "exchange": "NSE", "interval": "1D", "price_at_alert": 2950.45,
            "alert_name": "RSI Oversold Bounce", "alert_message": "RSI crossed above 30 on daily.",
            "signal_direction": SignalDirection.BULLISH, "sector": "Energy", "asset_class": "EQUITY"
        },
        {
            "ticker": "HDFCBANK", "exchange": "NSE", "interval": "4H", "price_at_alert": 1420.10,
            "alert_name": "MACD Bearish Cross", "alert_message": "MACD line crossed below signal line.",
            "signal_direction": SignalDirection.BEARISH, "sector": "Banking", "asset_class": "EQUITY"
        }
    ]

    created_ids = []
    for m in mock_alerts:
        # Pass mock alerts through the AI summary generator
        ai_summary = generate_technical_summary(
            ticker=m["ticker"], price=m["price_at_alert"],
            indicators={}, alert_message=m["alert_message"]
        )
        alert = TradingViewAlert(
            **m,
            status=AlertStatus.PENDING,
            signal_summary=ai_summary,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        created_ids.append(alert.id)

    return {"success": True, "count": len(created_ids), "ids": created_ids}


@app.get("/health")
def health():
    return {"status": "healthy", "service": "FIE Phase 1 + AI Engine", "timestamp": datetime.utcnow().isoformat()}

# ─── Run ───────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
