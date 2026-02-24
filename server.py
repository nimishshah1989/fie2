from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
import json
import os

from models import (
    init_db, get_db,
    TradingViewAlert, AlertAction, AlertPerformance, AlertStatus, ActionCall,
    SignalDirection, AlertType
)
from price_service import update_all_performance, get_live_price

app = FastAPI(title="JHAVERI FIE Engine")

# Fully open CORS to prevent security rejections
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=False, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

class ActionRequest(BaseModel):
    alert_id: int
    decision: str 
    primary_call: Optional[str] = None
    conviction: Optional[str] = "MEDIUM"
    fm_rationale_text: Optional[str] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    chart_image_b64: Optional[str] = None

@app.on_event("startup")
async def startup():
    init_db()

# ═══════════════════════════════════════════════════════
# 🔥 MASTER WEBHOOK PROCESSOR 🔥
# Safely scrubs TradingView data and writes to DB
# ═══════════════════════════════════════════════════════
async def process_webhook(request: Request, db: Session):
    try:
        body_bytes = await request.body()
        body_str = body_bytes.decode("utf-8")
        
        try:
            data = json.loads(body_str)
        except:
            data = {"message": body_str}

        def safe_float(k):
            v = data.get(k)
            if v is None: return None
            v_str = str(v).strip().lower()
            if v_str in ("null", "nan", "none", "", "n/a") or "{{" in v_str: return None
            try: return float(v)
            except: return None

        def safe_date(k):
            v = data.get(k)
            if not v: return None
            v_str = str(v).strip()
            if "{{" in v_str: return None 
            try:
                from dateutil import parser
                return parser.parse(v_str)
            except:
                return None
                
        def clean_str(k, default=""):
            v = str(data.get(k, default)).strip()
            if "{{" in v: return default
            return v

        signal_dir = SignalDirection.NEUTRAL
        if data.get("signal") and str(data.get("signal")).upper() in ["BULLISH", "BEARISH", "NEUTRAL"]:
            signal_dir = SignalDirection(str(data.get("signal")).upper())

        alert = TradingViewAlert(
            ticker=clean_str("ticker", "UNKNOWN"),
            exchange=clean_str("exchange", ""),
            interval=clean_str("interval", ""),
            price_at_alert=safe_float("close") or safe_float("price"),
            volume=safe_float("volume"),
            time_utc=safe_date("time") or safe_date("timenow") or datetime.utcnow(),
            alert_name=clean_str("alert_name", "Manual Alert"),
            alert_message=str(data.get("message", body_str))[:500],
            signal_direction=signal_dir,
            alert_type=AlertType.ABSOLUTE,
            status=AlertStatus.PENDING,
            processed=True,
            raw_payload=data
        )
        
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return JSONResponse(status_code=200, content={"success": True, "alert_id": alert.id})
        
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/webhook/tradingview")
@app.post("/webhook/tradingview/")
async def explicit_webhook(request: Request, db: Session = Depends(get_db)):
    return await process_webhook(request, db)

# ═══════════════════════════════════════════════════════
# REST API LOGIC
# ═══════════════════════════════════════════════════════
def _serialize_alert(a, db=None):
    action_data = None
    if a.action:
        action_data = {
            "call": a.action.primary_call.value if a.action.primary_call else None,
            "conviction": a.action.conviction,
            "remarks": a.action.fm_remarks,
            "has_chart": bool(a.action.chart_image_b64),
            "decision_at": a.action.decision_at.isoformat() if a.action.decision_at else None,
        }

    perf_data = None
    if db:
        perf = db.query(AlertPerformance).filter_by(alert_id=a.id, is_primary=True).first()
        if perf:
            perf_data = {
                "reference_price": perf.reference_price,
                "current_price": perf.current_price,
                "return_pct": perf.return_pct,
                "max_drawdown": perf.max_drawdown,
                "last_updated": perf.snapshot_date.isoformat() if perf.snapshot_date else None,
            }

    return {
        "id": a.id,
        "ticker": a.ticker or "—",
        "exchange": a.exchange or "—",
        "price_at_alert": a.price_at_alert,
        "volume": a.volume,
        "alert_name": a.alert_name or "System Trigger",
        "alert_message": a.alert_message,
        "signal_direction": a.signal_direction.value if a.signal_direction else "NEUTRAL",
        "status": a.status.value if a.status else "PENDING",
        "received_at": a.received_at.isoformat() if a.received_at else None,
        "asset_class": a.asset_class or "—",
        "action": action_data,
        "performance": perf_data,
    }

@app.get("/api/alerts")
async def get_alerts(status: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(TradingViewAlert).order_by(desc(TradingViewAlert.received_at))
    if status and status != "All":
        query = query.filter(TradingViewAlert.status == status)
    results = [_serialize_alert(a, db) for a in query.limit(limit).all()]
    return {"alerts": results}

@app.post("/api/alerts/{alert_id}/action")
async def take_action(alert_id: int, req: ActionRequest, db: Session = Depends(get_db)):
    alert = db.query(TradingViewAlert).filter(TradingViewAlert.id == alert_id).first()
    if not alert: raise HTTPException(status_code=404)

    decision_map = {"APPROVED": AlertStatus.APPROVED, "DENIED": AlertStatus.DENIED, "REVIEW_LATER": AlertStatus.REVIEW_LATER}
    decision = decision_map.get(req.decision, AlertStatus.DENIED)

    action = db.query(AlertAction).filter_by(alert_id=alert_id).first() or AlertAction(alert_id=alert_id)
    action.decision = decision
    action.decision_at = datetime.now()
    action.primary_ticker = alert.ticker
    action.conviction = req.conviction

    if req.primary_call:
        try: action.primary_call = ActionCall(req.primary_call)
        except: action.primary_call = None
    
    if req.fm_rationale_text: action.fm_remarks = req.fm_rationale_text
    if req.chart_image_b64: action.chart_image_b64 = req.chart_image_b64

    if not action.id: db.add(action)
    alert.status = decision

    if decision == AlertStatus.APPROVED:
        existing_perf = db.query(AlertPerformance).filter_by(alert_id=alert.id).first()
        if not existing_perf:
            db.add(AlertPerformance(
                alert_id=alert.id, ticker=alert.ticker, is_primary=True,
                reference_price=alert.price_at_alert or 0.0, reference_date=datetime.now()
            ))

    db.commit()
    return {"success": True}

@app.delete("/api/alerts/{alert_id}")
async def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(TradingViewAlert).filter(TradingViewAlert.id == alert_id).first()
    if not alert: raise HTTPException(status_code=404)
    db.query(AlertAction).filter_by(alert_id=alert_id).delete()
    db.query(AlertPerformance).filter_by(alert_id=alert_id).delete()
    db.delete(alert)
    db.commit()
    return {"success": True}

@app.get("/api/performance")
async def get_performance(db: Session = Depends(get_db)):
    records = db.query(AlertPerformance, TradingViewAlert).join(TradingViewAlert).order_by(desc(AlertPerformance.reference_date)).all()
    return {"performance": [{
        "id": p.id, "alert_id": p.alert_id, "ticker": p.ticker, "alert_name": a.alert_name,
        "reference_price": p.reference_price, "current_price": p.current_price,
        "return_pct": p.return_pct, "max_drawdown": p.max_drawdown,
        "last_updated": p.snapshot_date.isoformat() if p.snapshot_date else None,
        "action_call": a.action.primary_call.value if a.action and a.action.primary_call else None,
        "conviction": a.action.conviction if a.action else None,
    } for p, a in records]}

@app.post("/api/performance/refresh")
async def refresh_performance(db: Session = Depends(get_db)):
    updated = update_all_performance(db)
    return {"success": True, "updated_count": updated}

@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    total = db.query(TradingViewAlert).count()
    pending = db.query(TradingViewAlert).filter(TradingViewAlert.status == AlertStatus.PENDING).count()
    return {"total_alerts": total, "pending": pending}

@app.get("/api/master")
async def get_master_alerts(limit: int = 200, status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(TradingViewAlert).order_by(desc(TradingViewAlert.received_at))
    if status and status != "All": query = query.filter(TradingViewAlert.status == status)
    results = [_serialize_alert(a, db) for a in query.limit(limit).all()]
    return {"alerts": results}

@app.get("/api/alerts/{alert_id}/chart")
async def get_alert_chart(alert_id: int, db: Session = Depends(get_db)):
    action = db.query(AlertAction).filter_by(alert_id=alert_id).first()
    if not action or not action.chart_image_b64: raise HTTPException(status_code=404)
    return {"chart_image_b64": action.chart_image_b64}


# ═══════════════════════════════════════════════════════
# 🔥 STREAMLIT REVERSE PROXY (INTERCEPTS ALL WEBHOOKS) 🔥
# ═══════════════════════════════════════════════════════
import httpx
import subprocess
import sys
import asyncio
from starlette.websockets import WebSocket, WebSocketDisconnect

STREAMLIT_INTERNAL_PORT = 8501
STREAMLIT_BASE = f"http://127.0.0.1:{STREAMLIT_INTERNAL_PORT}"
_streamlit_proc = None
_proxy_client = None

def _start_streamlit():
    global _streamlit_proc
    cmd = [
        sys.executable, "-m", "streamlit", "run", "dashboard.py",
        "--server.port", str(STREAMLIT_INTERNAL_PORT),
        "--server.address", "127.0.0.1",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false",
    ]
    _streamlit_proc = subprocess.Popen(cmd)

@app.on_event("startup")
async def startup_proxy():
    global _proxy_client
    _proxy_client = httpx.AsyncClient(base_url=STREAMLIT_BASE, timeout=30.0)
    _start_streamlit()

@app.on_event("shutdown")
async def shutdown_proxy():
    global _streamlit_proc, _proxy_client
    if _streamlit_proc: _streamlit_proc.terminate()
    if _proxy_client: await _proxy_client.aclose()

@app.websocket("/_stcore/stream")
async def ws_proxy(websocket: WebSocket):
    await websocket.accept()
    import websockets as ws_lib
    ws_url = f"ws://127.0.0.1:{STREAMLIT_INTERNAL_PORT}/_stcore/stream"
    try:
        async with ws_lib.connect(ws_url) as remote:
            async def client_to_streamlit():
                try:
                    while True:
                        data = await websocket.receive_text()
                        await remote.send(data)
                except: pass
            async def streamlit_to_client():
                try:
                    async for msg in remote:
                        if isinstance(msg, str): await websocket.send_text(msg)
                        else: await websocket.send_bytes(msg)
                except: pass
            await asyncio.gather(client_to_streamlit(), streamlit_to_client())
    except: pass
    finally:
        try: await websocket.close()
        except: pass

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_streamlit(request: Request, path: str = "", db: Session = Depends(get_db)):
    # 🚨 CRITICAL INTERCEPT 🚨
    # If the URL contains "webhook" anywhere, forcefully route it to the database!
    # It is physically impossible for Streamlit to block it now.
    if "webhook" in path.lower():
        return await process_webhook(request, db)

    url = f"/{path}"
    if request.url.query: url += f"?{request.url.query}"
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)
    body = await request.body()
    try:
        resp = await _proxy_client.request(method=request.method, url=url, headers=headers, content=body)
        skip = {"content-encoding", "transfer-encoding", "connection", "content-length"}
        resp_headers = {k: v for k, v in resp.headers.items() if k.lower() not in skip}
        return Response(content=resp.content, status_code=resp.status_code, headers=resp_headers)
    except:
        return Response(content="Dashboard loading...", status_code=502)
