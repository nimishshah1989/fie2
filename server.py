from fastapi import FastAPI, Request, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, text
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List
import json
import os
import base64

from models import (
    init_db, get_db, SessionLocal,
    TradingViewAlert, AlertAction, AlertPerformance, AlertStatus, ActionCall,
    SignalDirection, AlertType
)
from webhook_parser import parse_webhook_payload
from price_service import update_all_performance, get_live_price
from ai_engine import generate_technical_summary, synthesize_fm_rationale

app = FastAPI(title="JHAVERI FIE Engine")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


class ActionRequest(BaseModel):
    alert_id: int
    decision: str  # APPROVED, DENIED, REVIEW_LATER
    primary_call: Optional[str] = None
    conviction: Optional[str] = "MEDIUM"
    fm_rationale_text: Optional[str] = None
    fm_rationale_audio: Optional[str] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    chart_image_b64: Optional[str] = None


@app.on_event("startup")
async def startup():
    init_db()


# ═══════════════════════════════════════════════════════
# WEBHOOK RECEIVER
# ═══════════════════════════════════════════════════════

@app.post("/webhook/tradingview")
async def receive_tradingview_alert(request: Request, db: Session = Depends(get_db)):
    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            raw_data = await request.json()
        else:
            body = (await request.body()).decode("utf-8")
            try:
                raw_data = json.loads(body)
            except json.JSONDecodeError:
                raw_data = {"message": body}

        try:
            parsed = parse_webhook_payload(raw_data)
        except Exception as parse_err:
            import traceback
            traceback.print_exc()
            parsed = {
                "ticker": raw_data.get("ticker", raw_data.get("symbol", "UNKNOWN")) if isinstance(raw_data, dict) else "UNKNOWN",
                "exchange": raw_data.get("exchange") if isinstance(raw_data, dict) else None,
                "interval": raw_data.get("interval") if isinstance(raw_data, dict) else None,
                "price_at_alert": None,
                "alert_name": raw_data.get("alert_name", "System Trigger") if isinstance(raw_data, dict) else "System Trigger",
                "alert_message": str(raw_data)[:500],
                "indicator_values": {},
                "signal_direction": "NEUTRAL",
                "signal_strength": None,
                "sector": None,
                "asset_class": None,
                "alert_type": "ABSOLUTE",
            }

        try:
            clean_price = float(parsed.get("price_at_alert") or 0.0)
        except (ValueError, TypeError):
            clean_price = 0.0

        # Skip AI summary for now (Phase 2)
        ai_summary = parsed.get("signal_summary") or parsed.get("alert_message") or "Signal received"

        def safe_signal_dir(val):
            if val is None: return SignalDirection.NEUTRAL
            if isinstance(val, SignalDirection): return val
            try: return SignalDirection(str(val).upper())
            except (ValueError, KeyError): return SignalDirection.NEUTRAL

        def safe_alert_type(val):
            if val is None: return AlertType.ABSOLUTE
            if isinstance(val, AlertType): return val
            try: return AlertType(str(val).upper())
            except (ValueError, KeyError): return AlertType.ABSOLUTE

        alert = TradingViewAlert(
            ticker=parsed.get("ticker", "UNKNOWN"),
            exchange=parsed.get("exchange"),
            interval=parsed.get("interval"),
            price_at_alert=clean_price,
            price_open=parsed.get("price_open"),
            price_high=parsed.get("price_high"),
            price_low=parsed.get("price_low"),
            price_close=parsed.get("price_close"),
            volume=parsed.get("volume"),
            time_utc=parsed.get("time_utc"),
            timenow_utc=parsed.get("timenow_utc"),
            alert_name=parsed.get("alert_name") or "System Trigger",
            alert_message=parsed.get("alert_message"),
            alert_condition=parsed.get("alert_condition"),
            indicator_values=parsed.get("indicator_values"),
            alert_type=safe_alert_type(parsed.get("alert_type")),
            numerator_ticker=parsed.get("numerator_ticker"),
            denominator_ticker=parsed.get("denominator_ticker"),
            numerator_price=parsed.get("numerator_price"),
            denominator_price=parsed.get("denominator_price"),
            ratio_value=parsed.get("ratio_value"),
            signal_direction=safe_signal_dir(parsed.get("signal_direction")),
            signal_strength=parsed.get("signal_strength"),
            signal_summary=ai_summary,
            sector=parsed.get("sector"),
            asset_class=parsed.get("asset_class"),
            raw_payload=raw_data,
            status=AlertStatus.PENDING,
            processed=True
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return JSONResponse(status_code=200, content={"success": True, "alert_id": alert.id})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════════════
# ALERTS API
# ═══════════════════════════════════════════════════════

def _serialize_alert(a, db=None):
    """Serialize a TradingViewAlert to dict."""
    action_data = None
    if a.action:
        action_data = {
            "call": a.action.primary_call.value if a.action.primary_call else None,
            "conviction": a.action.conviction,
            "remarks": a.action.fm_remarks,
            "target_price": a.action.primary_target_price,
            "stop_loss": a.action.primary_stop_loss,
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
                "return_absolute": perf.return_absolute,
                "high_since": perf.high_since,
                "low_since": perf.low_since,
                "max_drawdown": perf.max_drawdown,
                "last_updated": perf.snapshot_date.isoformat() if perf.snapshot_date else None,
            }

    return {
        "id": a.id,
        "ticker": a.ticker or "—",
        "exchange": a.exchange or "—",
        "interval": a.interval or "—",
        "price_at_alert": a.price_at_alert,
        "price_open": a.price_open,
        "price_high": a.price_high,
        "price_low": a.price_low,
        "price_close": a.price_close,
        "volume": a.volume,
        "alert_name": a.alert_name or "System Trigger",
        "alert_message": a.alert_message,
        "alert_condition": a.alert_condition,
        "signal_direction": a.signal_direction.value if a.signal_direction else "NEUTRAL",
        "signal_strength": a.signal_strength,
        "signal_summary": a.signal_summary,
        "status": a.status.value if a.status else "PENDING",
        "received_at": a.received_at.isoformat() if a.received_at else None,
        "sector": a.sector or "—",
        "asset_class": a.asset_class or "—",
        "alert_type": a.alert_type.value if a.alert_type else "ABSOLUTE",
        "numerator_ticker": a.numerator_ticker,
        "denominator_ticker": a.denominator_ticker,
        "ratio_value": a.ratio_value,
        "indicator_values": a.indicator_values,
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


@app.get("/api/alerts/{alert_id}")
async def get_alert_detail(alert_id: int, db: Session = Depends(get_db)):
    a = db.query(TradingViewAlert).filter(TradingViewAlert.id == alert_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    result = _serialize_alert(a, db)
    # Include chart image for detail view
    if a.action and a.action.chart_image_b64:
        result["action"]["chart_image_b64"] = a.action.chart_image_b64
    # Include raw payload
    result["raw_payload"] = a.raw_payload
    return result


# ═══════════════════════════════════════════════════════
# FUND MANAGER ACTION
# ═══════════════════════════════════════════════════════

@app.post("/api/alerts/{alert_id}/action")
async def take_action(alert_id: int, req: ActionRequest, db: Session = Depends(get_db)):
    alert = db.query(TradingViewAlert).filter(TradingViewAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404)

    decision_map = {
        "APPROVED": AlertStatus.APPROVED,
        "DENIED": AlertStatus.DENIED,
        "REVIEW_LATER": AlertStatus.REVIEW_LATER,
    }
    decision = decision_map.get(req.decision, AlertStatus.DENIED)

    action = db.query(AlertAction).filter_by(alert_id=alert_id).first() or AlertAction(alert_id=alert_id)

    action.decision = decision
    action.decision_at = datetime.now()
    action.primary_ticker = alert.ticker
    action.conviction = req.conviction

    # Map primary_call to enum
    if req.primary_call:
        try:
            action.primary_call = ActionCall(req.primary_call)
        except (ValueError, KeyError):
            action.primary_call = None
    
    # Store FM remarks — just save as-is (no AI processing needed for MVP)
    if req.fm_rationale_text:
        action.fm_remarks = req.fm_rationale_text

    # Optional target / stop loss
    if req.target_price and req.target_price > 0:
        action.primary_target_price = req.target_price
    if req.stop_loss and req.stop_loss > 0:
        action.primary_stop_loss = req.stop_loss

    # Chart image
    if req.chart_image_b64:
        action.chart_image_b64 = req.chart_image_b64

    if not action.id:
        db.add(action)
    alert.status = decision

    # Create performance tracking for approved alerts
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
    if not alert:
        raise HTTPException(status_code=404)
    db.query(AlertAction).filter_by(alert_id=alert_id).delete()
    db.query(AlertPerformance).filter_by(alert_id=alert_id).delete()
    db.delete(alert)
    db.commit()
    return {"success": True}


# ═══════════════════════════════════════════════════════
# PERFORMANCE API
# ═══════════════════════════════════════════════════════

@app.get("/api/performance")
async def get_performance(db: Session = Depends(get_db)):
    records = db.query(AlertPerformance, TradingViewAlert).join(TradingViewAlert).order_by(desc(AlertPerformance.reference_date)).all()
    return {"performance": [{
        "id": p.id,
        "alert_id": p.alert_id,
        "ticker": p.ticker,
        "alert_name": a.alert_name,
        "reference_price": p.reference_price,
        "current_price": p.current_price,
        "return_pct": p.return_pct,
        "return_absolute": p.return_absolute,
        "high_since": p.high_since,
        "low_since": p.low_since,
        "max_drawdown": p.max_drawdown,
        "approved_at": p.reference_date.isoformat() if p.reference_date else None,
        "last_updated": p.snapshot_date.isoformat() if p.snapshot_date else None,
        "signal_direction": a.signal_direction.value if a.signal_direction else "NEUTRAL",
        "action_call": a.action.primary_call.value if a.action and a.action.primary_call else None,
        "conviction": a.action.conviction if a.action else None,
        "target_price": a.action.primary_target_price if a.action else None,
        "stop_loss": a.action.primary_stop_loss if a.action else None,
        "fm_remarks": a.action.fm_remarks if a.action else None,
        "has_chart": bool(a.action.chart_image_b64) if a.action else False,
    } for p, a in records]}


@app.post("/api/performance/refresh")
async def refresh_performance(db: Session = Depends(get_db)):
    updated = update_all_performance(db)
    return {"success": True, "updated_count": updated}


@app.get("/api/price/{ticker}")
async def get_price(ticker: str):
    """Get live price for a single ticker."""
    data = get_live_price(ticker)
    return data


# ═══════════════════════════════════════════════════════
# STATS API
# ═══════════════════════════════════════════════════════

@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    total = db.query(TradingViewAlert).count()
    pending = db.query(TradingViewAlert).filter(TradingViewAlert.status == AlertStatus.PENDING).count()
    approved = db.query(TradingViewAlert).filter(TradingViewAlert.status == AlertStatus.APPROVED).count()
    denied = db.query(TradingViewAlert).filter(TradingViewAlert.status == AlertStatus.DENIED).count()
    review = db.query(TradingViewAlert).filter(TradingViewAlert.status == AlertStatus.REVIEW_LATER).count()
    avg_return = db.query(func.avg(AlertPerformance.return_pct)).scalar() or 0.0

    # Signal intensity: count of alerts in last hour
    from datetime import timedelta
    recent_cutoff = datetime.now() - timedelta(hours=1)
    recent_count = db.query(TradingViewAlert).filter(
        TradingViewAlert.received_at >= recent_cutoff,
        TradingViewAlert.status == AlertStatus.PENDING
    ).count()
    
    # Bullish vs bearish pending
    bullish_pending = db.query(TradingViewAlert).filter(
        TradingViewAlert.status == AlertStatus.PENDING,
        TradingViewAlert.signal_direction == SignalDirection.BULLISH
    ).count()
    bearish_pending = db.query(TradingViewAlert).filter(
        TradingViewAlert.status == AlertStatus.PENDING,
        TradingViewAlert.signal_direction == SignalDirection.BEARISH
    ).count()

    return {
        "total_alerts": total,
        "pending": pending,
        "approved": approved,
        "denied": denied,
        "review_later": review,
        "avg_return_pct": round(float(avg_return), 2),
        "recent_intensity": recent_count,
        "bullish_pending": bullish_pending,
        "bearish_pending": bearish_pending,
    }


# ═══════════════════════════════════════════════════════
# MASTER DATABASE API
# ═══════════════════════════════════════════════════════

@app.get("/api/master")
async def get_master_alerts(
    limit: int = 200, offset: int = 0,
    status: Optional[str] = None, ticker: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(TradingViewAlert).order_by(desc(TradingViewAlert.received_at))
    if status and status != "All":
        query = query.filter(TradingViewAlert.status == status)
    if ticker:
        query = query.filter(TradingViewAlert.ticker.ilike(f"%{ticker}%"))
    total = query.count()
    alerts = query.offset(offset).limit(limit).all()
    results = [_serialize_alert(a, db) for a in alerts]
    return {"alerts": results, "total": total, "limit": limit, "offset": offset}


@app.get("/api/alerts/{alert_id}/chart")
async def get_alert_chart(alert_id: int, db: Session = Depends(get_db)):
    """Get chart image for an alert."""
    action = db.query(AlertAction).filter_by(alert_id=alert_id).first()
    if not action or not action.chart_image_b64:
        raise HTTPException(status_code=404, detail="No chart image")
    return {"chart_image_b64": action.chart_image_b64}


# ═══════════════════════════════════════════════════════
# STREAMLIT REVERSE PROXY
# ═══════════════════════════════════════════════════════
import httpx
import subprocess
import sys
import asyncio
from fastapi.responses import Response
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
        "--server.maxUploadSize", "10",
    ]
    _streamlit_proc = subprocess.Popen(cmd)
    print(f"[proxy] Streamlit started internally on port {STREAMLIT_INTERNAL_PORT}")

@app.on_event("startup")
async def startup_proxy():
    global _proxy_client
    _proxy_client = httpx.AsyncClient(base_url=STREAMLIT_BASE, timeout=30.0)
    _start_streamlit()
    for _ in range(30):
        try:
            r = await _proxy_client.get("/_stcore/health")
            if r.status_code == 200:
                print("[proxy] Streamlit is healthy")
                break
        except:
            pass
        await asyncio.sleep(1)

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
                except (WebSocketDisconnect, Exception): pass
            async def streamlit_to_client():
                try:
                    async for msg in remote:
                        if isinstance(msg, str):
                            await websocket.send_text(msg)
                        else:
                            await websocket.send_bytes(msg)
                except (WebSocketDisconnect, Exception): pass
            await asyncio.gather(client_to_streamlit(), streamlit_to_client())
    except Exception: pass
    finally:
        try: await websocket.close()
        except: pass

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_streamlit(request: Request, path: str = ""):
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
    except Exception as e:
        return Response(content=f"Dashboard loading... ({e})", status_code=502, media_type="text/plain")
