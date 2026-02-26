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
import logging

from models import (
    init_db, get_db,
    TradingViewAlert, AlertAction, AlertPerformance, AlertStatus, ActionCall,
    SignalDirection, AlertType
)
from price_service import update_all_performance, get_live_price
from ai_engine import generate_technical_summary

logger = logging.getLogger("fie")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="JHAVERI FIE Engine")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=False,
    allow_methods=["*"], allow_headers=["*"]
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
# WEBHOOK PROCESSOR — handles legacy + FIE Pine payloads
# ═══════════════════════════════════════════════════════

def _sf(v):
    if v is None: return None
    s = str(v).strip().lower()
    if s in ("null","nan","none","","n/a") or "{{" in s: return None
    try: return float(v)
    except: return None

def _cs(v, d=""):
    if v is None: return d
    t = str(v).strip()
    return d if ("{{" in t or t.lower() in ("none","null")) else t

def _parse_fie(data):
    p = data.get("price", {})
    indicators = {}
    for section_key in ("moving_averages","momentum","trend","volatility","volume_analysis","levels"):
        sec = data.get(section_key, {})
        for k, v in sec.items():
            if isinstance(v, (int, float, str, bool)):
                indicators[k] = v
    htf = data.get("htf", {})
    for k, v in htf.items():
        if isinstance(v, (int, float, str)):
            indicators[f"htf_{k}"] = v
    conf = data.get("confluence", {})
    for k, v in conf.items():
        if isinstance(v, (int, float, str)):
            indicators[f"confluence_{k}"] = v
    if p.get("candle_pattern"):
        indicators["candle_pattern"] = p["candle_pattern"]

    sig = str(data.get("signal","NEUTRAL")).upper()
    signal_dir = SignalDirection(sig) if sig in ("BULLISH","BEARISH","NEUTRAL") else SignalDirection.NEUTRAL
    at = str(data.get("alert_type","ABSOLUTE")).upper()

    mom = data.get("momentum", {})
    trend = data.get("trend", {})

    parts = []
    ticker = _cs(data.get("ticker"), "Unknown")
    alert_name = _cs(data.get("alert_name"), f"{ticker} Signal")
    parts.append(alert_name)
    if p.get("close"): parts.append(f"Price: {p['close']}")
    rsi = mom.get("rsi")
    if rsi is not None:
        rl = "OB" if float(rsi)>70 else "OS" if float(rsi)<30 else "N"
        parts.append(f"RSI:{rsi}({rl})")
    cb = conf.get("bias","")
    if cb: parts.append(f"Confluence:{cb}({conf.get('bull_score','')}B/{conf.get('bear_score','')}S)")
    std = trend.get("supertrend_dir","")
    if std: parts.append(f"ST:{std}")
    ht = htf.get("trend","")
    if ht: parts.append(f"HTF:{ht}")
    ma_a = data.get("moving_averages",{}).get("ma_alignment","")
    if ma_a: parts.append(f"MA:{ma_a}")
    cp = p.get("candle_pattern","NONE")
    if cp and cp != "NONE": parts.append(f"Pat:{cp}")
    summary = " | ".join(parts)
    cm = _cs(data.get("custom_message"), "")

    return {
        "ticker": ticker, "exchange": _cs(data.get("exchange")),
        "interval": _cs(data.get("interval")),
        "price_at_alert": _sf(p.get("close")) or _sf(data.get("close")),
        "price_open": _sf(p.get("open")), "price_high": _sf(p.get("high")),
        "price_low": _sf(p.get("low")), "price_close": _sf(p.get("close")),
        "volume": _sf(p.get("volume")) or _sf(data.get("volume")),
        "alert_name": alert_name, "alert_message": cm or summary,
        "signal_direction": signal_dir,
        "signal_strength": _sf(conf.get("signal_strength")),
        "signal_summary": summary,
        "alert_type": AlertType.RELATIVE if at=="RELATIVE" else AlertType.ABSOLUTE,
        "asset_class": _cs(data.get("asset_class"),"EQUITY"),
        "sector": _cs(data.get("sector")),
        "indicator_values": indicators, "raw_payload": data,
    }

def _parse_legacy(data):
    sig = str(data.get("signal","")).upper()
    sd = SignalDirection(sig) if sig in ("BULLISH","BEARISH","NEUTRAL") else SignalDirection.NEUTRAL
    return {
        "ticker": _cs(data.get("ticker"),"UNKNOWN"), "exchange": _cs(data.get("exchange")),
        "interval": _cs(data.get("interval")),
        "price_at_alert": _sf(data.get("close")) or _sf(data.get("price")),
        "price_open": None, "price_high": None, "price_low": None,
        "price_close": _sf(data.get("close")),
        "volume": _sf(data.get("volume")),
        "alert_name": _cs(data.get("alert_name"),"Manual Alert"),
        "alert_message": str(data.get("message",data.get("alert_message","")))[:500],
        "signal_direction": sd, "signal_strength": None, "signal_summary": None,
        "alert_type": AlertType.ABSOLUTE, "asset_class": None, "sector": None,
        "indicator_values": {}, "raw_payload": data,
    }

async def process_webhook(request: Request, db: Session):
    try:
        body = (await request.body()).decode("utf-8")
        logger.info(f"WEBHOOK RECEIVED: {body[:500]}")
        try: data = json.loads(body)
        except:
            logger.warning(f"Non-JSON webhook body: {body[:200]}")
            data = {"message": body}

        is_fie = bool(data.get("fie_version"))
        logger.info(f"Payload type: {'FIE Pine' if is_fie else 'Legacy'} | Keys: {list(data.keys())[:15]}")
        parsed = _parse_fie(data) if is_fie else _parse_legacy(data)
        logger.info(f"Parsed: ticker={parsed.get('ticker')} price={parsed.get('price_at_alert')} indicators={len(parsed.get('indicator_values',{}))}")

        if parsed.get("indicator_values"):
            try:
                ai = generate_technical_summary(parsed["ticker"], parsed.get("price_at_alert"), parsed["indicator_values"], parsed.get("alert_message",""))
                if ai and ai != parsed.get("alert_message"):
                    parsed["signal_summary"] = ai
            except Exception as e:
                logger.warning(f"AI enrichment failed: {e}")

        if not parsed.get("signal_summary"):
            parsed["signal_summary"] = parsed.get("alert_message") or "Signal received"

        alert = TradingViewAlert(
            ticker=parsed["ticker"], exchange=parsed["exchange"], interval=parsed["interval"],
            price_at_alert=parsed["price_at_alert"], price_open=parsed.get("price_open"),
            price_high=parsed.get("price_high"), price_low=parsed.get("price_low"),
            price_close=parsed.get("price_close"), volume=parsed["volume"],
            alert_name=parsed["alert_name"], alert_message=parsed["alert_message"],
            signal_direction=parsed["signal_direction"], signal_strength=parsed.get("signal_strength"),
            signal_summary=parsed.get("signal_summary"),
            alert_type=parsed.get("alert_type", AlertType.ABSOLUTE),
            asset_class=parsed.get("asset_class"), sector=parsed.get("sector"),
            indicator_values=parsed.get("indicator_values"),
            status=AlertStatus.PENDING, processed=True, raw_payload=parsed["raw_payload"],
        )
        db.add(alert); db.commit(); db.refresh(alert)
        logger.info(f"Alert #{alert.id}: {alert.ticker} / {alert.alert_name}")
        return JSONResponse(status_code=200, content={"success": True, "alert_id": alert.id})
    except Exception as e:
        db.rollback()
        logger.error(f"Webhook error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/webhook/tradingview")
@app.post("/webhook/tradingview/")
async def explicit_webhook(request: Request, db: Session = Depends(get_db)):
    return await process_webhook(request, db)

# ═══════════════════════════════════════════════════════
# REST API
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
            "target_price": a.action.primary_target_price,
            "stop_loss": a.action.primary_stop_loss,
        }
    perf_data = None
    if db:
        perf = db.query(AlertPerformance).filter_by(alert_id=a.id, is_primary=True).first()
        if perf:
            perf_data = {"reference_price": perf.reference_price, "current_price": perf.current_price,
                         "return_pct": perf.return_pct, "max_drawdown": perf.max_drawdown,
                         "last_updated": perf.snapshot_date.isoformat() if perf.snapshot_date else None}

    ind = a.indicator_values or {}
    return {
        "id": a.id, "ticker": a.ticker or "—", "exchange": a.exchange or "—",
        "interval": a.interval or "—",
        "price_at_alert": a.price_at_alert, "volume": a.volume,
        "alert_name": a.alert_name or "",
        "alert_message": a.alert_message,
        "signal_direction": a.signal_direction.value if a.signal_direction else "NEUTRAL",
        "signal_strength": a.signal_strength, "signal_summary": a.signal_summary,
        "status": a.status.value if a.status else "PENDING",
        "received_at": a.received_at.isoformat() if a.received_at else None,
        "asset_class": a.asset_class or "—", "sector": a.sector or "—",
        "action": action_data, "performance": perf_data,
        "indicators": {
            "rsi": ind.get("rsi"), "macd_hist": ind.get("macd_hist"),
            "macd_line": ind.get("macd_line"), "macd_signal": ind.get("macd_signal"),
            "supertrend_dir": ind.get("supertrend_dir"),
            "adx": ind.get("adx"), "di_plus": ind.get("di_plus"), "di_minus": ind.get("di_minus"),
            "bb_pctb": ind.get("bb_pctb"), "vol_ratio": ind.get("vol_ratio"),
            "vol_spike": ind.get("vol_spike"),
            "ma_alignment": ind.get("ma_alignment"),
            "ema_9": ind.get("ema_9"), "ema_20": ind.get("ema_20"),
            "ema_50": ind.get("ema_50"), "ema_200": ind.get("ema_200"),
            "vwap": ind.get("vwap"),
            "candle_pattern": ind.get("candle_pattern"),
            "confluence_bias": ind.get("confluence_bias"),
            "confluence_bull_score": ind.get("confluence_bull_score"),
            "confluence_bear_score": ind.get("confluence_bear_score"),
            "confluence_net_score": ind.get("confluence_net_score"),
            "htf_trend": ind.get("htf_trend"), "htf_rsi": ind.get("htf_rsi"),
            "atr_pct": ind.get("atr_pct"), "atr": ind.get("atr"),
            "dist_vwap_pct": ind.get("dist_vwap_pct"),
            "stoch_k": ind.get("stoch_k"), "stoch_d": ind.get("stoch_d"),
            "cci": ind.get("cci"), "mfi": ind.get("mfi"),
            "pivot_pp": ind.get("pivot_pp"),
            "high_20": ind.get("high_20"), "low_20": ind.get("low_20"),
        } if ind else None,
    }

@app.get("/api/alerts")
async def get_alerts(status: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    q = db.query(TradingViewAlert).order_by(desc(TradingViewAlert.received_at))
    if status and status != "All": q = q.filter(TradingViewAlert.status == status)
    return {"alerts": [_serialize_alert(a, db) for a in q.limit(limit).all()]}

@app.post("/api/alerts/{alert_id}/action")
async def take_action(alert_id: int, req: ActionRequest, db: Session = Depends(get_db)):
    alert = db.query(TradingViewAlert).filter(TradingViewAlert.id == alert_id).first()
    if not alert: raise HTTPException(status_code=404)
    dm = {"APPROVED": AlertStatus.APPROVED, "DENIED": AlertStatus.DENIED, "REVIEW_LATER": AlertStatus.REVIEW_LATER}
    decision = dm.get(req.decision, AlertStatus.DENIED)
    action = db.query(AlertAction).filter_by(alert_id=alert_id).first() or AlertAction(alert_id=alert_id)
    action.decision = decision; action.decision_at = datetime.now()
    action.primary_ticker = alert.ticker; action.conviction = req.conviction
    if req.primary_call:
        try: action.primary_call = ActionCall(req.primary_call)
        except: action.primary_call = None
    if req.fm_rationale_text: action.fm_remarks = req.fm_rationale_text
    if req.chart_image_b64: action.chart_image_b64 = req.chart_image_b64
    if req.target_price: action.primary_target_price = req.target_price
    if req.stop_loss: action.primary_stop_loss = req.stop_loss
    if not action.id: db.add(action)
    alert.status = decision
    if decision == AlertStatus.APPROVED:
        if not db.query(AlertPerformance).filter_by(alert_id=alert.id).first():
            db.add(AlertPerformance(alert_id=alert.id, ticker=alert.ticker, is_primary=True,
                                    reference_price=alert.price_at_alert or 0.0, reference_date=datetime.now()))
    db.commit()
    return {"success": True}

@app.delete("/api/alerts/{alert_id}")
async def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(TradingViewAlert).filter(TradingViewAlert.id == alert_id).first()
    if not alert: raise HTTPException(status_code=404)
    db.query(AlertAction).filter_by(alert_id=alert_id).delete()
    db.query(AlertPerformance).filter_by(alert_id=alert_id).delete()
    db.delete(alert); db.commit()
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
    return {"success": True, "updated_count": update_all_performance(db)}

@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    total = db.query(TradingViewAlert).count()
    pending = db.query(TradingViewAlert).filter(TradingViewAlert.status == AlertStatus.PENDING).count()
    return {"total_alerts": total, "pending": pending}

# ═══════════════════════════════════════════════════════════
# MARKET PULSE — Live index prices for dashboard
# ═══════════════════════════════════════════════════════════

MARKET_INSTRUMENTS = [
    # NSE Broad Market
    {"ticker": "NIFTY", "name": "Nifty 50", "category": "NSE Broad Market"},
    {"ticker": "BANKNIFTY", "name": "Bank Nifty", "category": "NSE Broad Market"},
    {"ticker": "NIFTY500", "name": "Nifty 500", "category": "NSE Broad Market"},
    {"ticker": "NIFTYMIDCAP", "name": "Nifty Midcap 150", "category": "NSE Broad Market"},
    {"ticker": "NIFTYSMALLCAP", "name": "Nifty Smallcap 250", "category": "NSE Broad Market"},
    {"ticker": "NIFTYNEXT50", "name": "Nifty Next 50", "category": "NSE Broad Market"},
    # NSE Sectoral
    {"ticker": "NIFTYIT", "name": "Nifty IT", "category": "NSE Sectoral"},
    {"ticker": "NIFTYPHARMA", "name": "Nifty Pharma", "category": "NSE Sectoral"},
    {"ticker": "NIFTYFMCG", "name": "Nifty FMCG", "category": "NSE Sectoral"},
    {"ticker": "NIFTYAUTO", "name": "Nifty Auto", "category": "NSE Sectoral"},
    {"ticker": "NIFTYMETAL", "name": "Nifty Metal", "category": "NSE Sectoral"},
    {"ticker": "NIFTYREALTY", "name": "Nifty Realty", "category": "NSE Sectoral"},
    {"ticker": "NIFTYENERGY", "name": "Nifty Energy", "category": "NSE Sectoral"},
    {"ticker": "NIFTYPSUBANK", "name": "Nifty PSU Bank", "category": "NSE Sectoral"},
    {"ticker": "NIFTYFINSERVICE", "name": "Nifty Fin Services", "category": "NSE Sectoral"},
    {"ticker": "NIFTYINFRA", "name": "Nifty Infra", "category": "NSE Sectoral"},
    {"ticker": "NIFTYMEDIA", "name": "Nifty Media", "category": "NSE Sectoral"},
    # BSE Indices
    {"ticker": "SENSEX", "name": "BSE Sensex", "category": "BSE Indices"},
    # Commodities
    {"ticker": "GOLD", "name": "Gold", "category": "Commodities"},
    {"ticker": "SILVER", "name": "Silver", "category": "Commodities"},
    {"ticker": "CRUDEOIL", "name": "Crude Oil", "category": "Commodities"},
    # Currency
    {"ticker": "USDINR", "name": "USD/INR", "category": "Currency"},
]

_market_cache = {"data": None, "updated_at": None}

@app.get("/api/market-pulse")
async def get_market_pulse():
    """Fetch live prices for all major NSE/BSE indices, commodities, and currencies."""
    import time as _time
    now = _time.time()
    # Cache for 60 seconds to avoid hammering Yahoo Finance
    if _market_cache["data"] and _market_cache["updated_at"] and (now - _market_cache["updated_at"]) < 60:
        return _market_cache["data"]
    
    results = []
    for inst in MARKET_INSTRUMENTS:
        try:
            price_data = get_live_price(inst["ticker"])
            results.append({
                "ticker": inst["ticker"],
                "name": inst["name"],
                "category": inst["category"],
                "current_price": price_data.get("current_price"),
                "prev_close": price_data.get("prev_close"),
                "change_pct": price_data.get("change_pct"),
                "high": price_data.get("high"),
                "low": price_data.get("low"),
                "volume": price_data.get("volume"),
            })
        except Exception as e:
            logger.warning(f"Market pulse error for {inst['ticker']}: {e}")
            results.append({
                "ticker": inst["ticker"], "name": inst["name"],
                "category": inst["category"], "current_price": None,
                "change_pct": None, "error": str(e),
            })
    
    ist_now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    response = {
        "indices": results,
        "updated_at": ist_now.strftime("%d-%b-%Y %I:%M:%S %p IST"),
        "count": len([r for r in results if r.get("current_price")]),
    }
    _market_cache["data"] = response
    _market_cache["updated_at"] = now
    return response

@app.get("/api/master")
async def get_master_alerts(limit: int = 200, status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(TradingViewAlert).order_by(desc(TradingViewAlert.received_at))
    if status and status != "All": q = q.filter(TradingViewAlert.status == status)
    return {"alerts": [_serialize_alert(a, db) for a in q.limit(limit).all()]}

@app.get("/api/debug/latest")
async def debug_latest(db: Session = Depends(get_db)):
    """Debug endpoint to see raw stored data for the last 5 alerts."""
    alerts = db.query(TradingViewAlert).order_by(desc(TradingViewAlert.received_at)).limit(5).all()
    return {"alerts": [{
        "id": a.id, "ticker": a.ticker, "exchange": a.exchange, "interval": a.interval,
        "price_at_alert": a.price_at_alert, "alert_name": a.alert_name,
        "alert_message": a.alert_message[:200] if a.alert_message else None,
        "signal_direction": a.signal_direction.value if a.signal_direction else None,
        "signal_summary": a.signal_summary[:200] if a.signal_summary else None,
        "indicator_values": a.indicator_values,
        "raw_payload_keys": list(a.raw_payload.keys()) if a.raw_payload else [],
        "raw_payload_sample": {k: v for k, v in list((a.raw_payload or {}).items())[:10]},
        "status": a.status.value if a.status else None,
        "received_at": a.received_at.isoformat() if a.received_at else None,
    } for a in alerts]}

@app.get("/api/alerts/{alert_id}/chart")
async def get_alert_chart(alert_id: int, db: Session = Depends(get_db)):
    action = db.query(AlertAction).filter_by(alert_id=alert_id).first()
    if not action or not action.chart_image_b64: raise HTTPException(status_code=404)
    return {"chart_image_b64": action.chart_image_b64}

# ═══════════════════════════════════════════════════════
# STREAMLIT REVERSE PROXY
# ═══════════════════════════════════════════════════════
import httpx, subprocess, sys, asyncio
from starlette.websockets import WebSocket

STREAMLIT_INTERNAL_PORT = 8501
STREAMLIT_BASE = f"http://127.0.0.1:{STREAMLIT_INTERNAL_PORT}"
_streamlit_proc = None
_proxy_client = None

def _start_streamlit():
    global _streamlit_proc
    _streamlit_proc = subprocess.Popen([
        sys.executable, "-m", "streamlit", "run", "dashboard.py",
        "--server.port", str(STREAMLIT_INTERNAL_PORT), "--server.address", "127.0.0.1",
        "--server.headless", "true", "--browser.gatherUsageStats", "false",
        "--server.enableCORS", "false", "--server.enableXsrfProtection", "false",
    ])

@app.on_event("startup")
async def startup_proxy():
    global _proxy_client
    _proxy_client = httpx.AsyncClient(base_url=STREAMLIT_BASE, timeout=30.0)
    _start_streamlit()

@app.on_event("shutdown")
async def shutdown_proxy():
    if _streamlit_proc: _streamlit_proc.terminate()
    if _proxy_client: await _proxy_client.aclose()

@app.websocket("/_stcore/stream")
async def ws_proxy(websocket: WebSocket):
    await websocket.accept()
    import websockets as ws_lib
    try:
        async with ws_lib.connect(f"ws://127.0.0.1:{STREAMLIT_INTERNAL_PORT}/_stcore/stream") as remote:
            async def c2s():
                try:
                    while True: await remote.send(await websocket.receive_text())
                except: pass
            async def s2c():
                try:
                    async for m in remote:
                        if isinstance(m, str): await websocket.send_text(m)
                        else: await websocket.send_bytes(m)
                except: pass
            await asyncio.gather(c2s(), s2c())
    except: pass
    finally:
        try: await websocket.close()
        except: pass

@app.api_route("/{path:path}", methods=["GET","POST","PUT","DELETE","PATCH","OPTIONS","HEAD"])
async def proxy_streamlit(request: Request, path: str = "", db: Session = Depends(get_db)):
    if "webhook" in path.lower(): return await process_webhook(request, db)
    url = f"/{path}"
    if request.url.query: url += f"?{request.url.query}"
    h = dict(request.headers); h.pop("host",None); h.pop("content-length",None)
    try:
        r = await _proxy_client.request(method=request.method, url=url, headers=h, content=await request.body())
        skip = {"content-encoding","transfer-encoding","connection","content-length"}
        return Response(content=r.content, status_code=r.status_code, headers={k:v for k,v in r.headers.items() if k.lower() not in skip})
    except:
        return Response(content="Dashboard loading...", status_code=502)
