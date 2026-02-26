"""
FIE v3 — FastAPI Server
Jhaveri Intelligence Platform
Simplified webhook (ticker/exchange/interval/OHLCV/time/data) + FM actions + Claude chart analysis
"""

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json, os, logging, base64, re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from models import (
    init_db, get_db,
    TradingViewAlert, AlertAction, AlertStatus, ActionPriority
)

logger = logging.getLogger("fie_v3")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="JHAVERI FIE v3")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=False,
    allow_methods=["*"], allow_headers=["*"]
)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


# ═══════════════════════════════════════════════════════
# WEBHOOK — accepts simplified TradingView payload
# ═══════════════════════════════════════════════════════

def _sf(v):
    """Safe float conversion — ignores TradingView unfilled {{}} placeholders."""
    if v is None: return None
    s = str(v).strip()
    if "{{" in s or s.lower() in ("null", "nan", "none", ""): return None
    try: return float(s)
    except: return None

def _cs(v, default=""):
    if v is None: return default
    s = str(v).strip()
    return default if ("{{" in s or s.lower() in ("none", "null", "")) else s

def _infer_signal(text: str) -> Optional[str]:
    t = text.lower()
    bull = ["buy", "bullish", "long", "breakout", "uptrend", "oversold", "accumulate"]
    bear = ["sell", "bearish", "short", "breakdown", "downtrend", "overbought", "distribute"]
    b = sum(1 for w in bull if w in t)
    s = sum(1 for w in bear if w in t)
    if b > s: return "BULLISH"
    if s > b: return "BEARISH"
    return "NEUTRAL"

def _parse_alert_name(data_text: str, ticker: str) -> str:
    """Try to extract a short alert name from the data string."""
    if not data_text:
        return ticker or "Alert"
    # First line or first sentence
    first = data_text.split("\n")[0].split(".")[0].strip()
    return first[:80] if first else (ticker or "Alert")


@app.on_event("startup")
async def startup():
    init_db()


@app.post("/webhook/tradingview")
@app.post("/webhook/tradingview/")
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        body = (await request.body()).decode("utf-8")
        logger.info(f"WEBHOOK: {body[:300]}")

        try:
            data = json.loads(body)
        except Exception:
            data = {"data": body}

        ticker   = _cs(data.get("ticker"))
        exchange = _cs(data.get("exchange"))
        interval = _cs(data.get("interval"))
        time_val = _cs(data.get("time"))
        timenow  = _cs(data.get("timenow"))
        o = _sf(data.get("open"))
        h = _sf(data.get("high"))
        l = _sf(data.get("low"))
        c = _sf(data.get("close"))
        v = _sf(data.get("volume"))
        alert_data = _cs(data.get("data"))

        # Signal direction from data text
        sig = _infer_signal(alert_data) if alert_data else "NEUTRAL"
        alert_name = _parse_alert_name(alert_data, ticker)

        alert = TradingViewAlert(
            ticker=ticker or "UNKNOWN",
            exchange=exchange,
            interval=interval,
            time_utc=time_val,
            timenow_utc=timenow,
            price_open=o,
            price_high=h,
            price_low=l,
            price_close=c,
            volume=v,
            alert_data=alert_data,
            alert_name=alert_name,
            signal_direction=sig,
            raw_payload=data,
            status=AlertStatus.PENDING,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        logger.info(f"Alert #{alert.id} saved: {ticker} @ {c}")
        return {"success": True, "alert_id": alert.id}

    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════
# REST API
# ═══════════════════════════════════════════════════════

def _serialize(a: TradingViewAlert) -> dict:
    action = None
    if a.action:
        action = {
            "decision":     a.action.decision.value,
            "action_call":  a.action.action_call,
            "is_ratio":     a.action.is_ratio,
            "ratio_long":   a.action.ratio_long,
            "ratio_short":  a.action.ratio_short,
            "priority":     a.action.priority.value if a.action.priority else None,
            "has_chart":    bool(a.action.chart_image_b64),
            "chart_analysis": json.loads(a.action.chart_analysis) if a.action.chart_analysis else None,
            "decision_at":  a.action.decision_at.isoformat() if a.action.decision_at else None,
        }
    return {
        "id":              a.id,
        "ticker":          a.ticker or "—",
        "exchange":        a.exchange or "—",
        "interval":        a.interval or "—",
        "time_utc":        a.time_utc,
        "timenow_utc":     a.timenow_utc,
        "price_open":      a.price_open,
        "price_high":      a.price_high,
        "price_low":       a.price_low,
        "price_close":     a.price_close,
        "volume":          a.volume,
        "alert_data":      a.alert_data,
        "alert_name":      a.alert_name or a.ticker,
        "signal_direction": a.signal_direction or "NEUTRAL",
        "status":          a.status.value,
        "received_at":     a.received_at.isoformat() if a.received_at else None,
        "action":          action,
    }


@app.get("/api/alerts")
async def get_alerts(status: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    q = db.query(TradingViewAlert).order_by(desc(TradingViewAlert.received_at))
    if status and status != "All":
        try:
            q = q.filter(TradingViewAlert.status == AlertStatus(status))
        except Exception:
            pass
    return {"alerts": [_serialize(a) for a in q.limit(limit).all()]}


@app.get("/api/alerts/{alert_id}")
async def get_alert(alert_id: int, db: Session = Depends(get_db)):
    a = db.query(TradingViewAlert).filter(TradingViewAlert.id == alert_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Not found")
    return _serialize(a)


# ─── FM Action ─────────────────────────────────────────

class ActionRequest(BaseModel):
    alert_id:        int
    decision:        str                     # APPROVED | DENIED
    action_call:     Optional[str] = None    # BUY / SELL / RATIO / etc.
    is_ratio:        Optional[bool] = False
    ratio_long:      Optional[str] = None
    ratio_short:     Optional[str] = None
    priority:        Optional[str] = None    # IMMEDIATELY | WITHIN_A_WEEK | WITHIN_A_MONTH
    chart_image_b64: Optional[str] = None   # base64 encoded image


@app.post("/api/alerts/{alert_id}/action")
async def take_action(alert_id: int, req: ActionRequest, db: Session = Depends(get_db)):
    alert = db.query(TradingViewAlert).filter(TradingViewAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    decision_map = {"APPROVED": AlertStatus.APPROVED, "DENIED": AlertStatus.DENIED}
    decision = decision_map.get(req.decision, AlertStatus.DENIED)

    action = db.query(AlertAction).filter_by(alert_id=alert_id).first()
    if not action:
        action = AlertAction(alert_id=alert_id)
        db.add(action)

    action.decision    = decision
    action.decision_at = datetime.now()
    action.action_call = req.action_call
    action.is_ratio    = req.is_ratio or False
    action.ratio_long  = req.ratio_long
    action.ratio_short = req.ratio_short

    if req.priority:
        try:
            action.priority = ActionPriority(req.priority)
        except Exception:
            action.priority = None

    if req.chart_image_b64:
        action.chart_image_b64 = req.chart_image_b64
        # Trigger Claude analysis
        analysis = await _analyze_chart_with_claude(req.chart_image_b64, alert)
        action.chart_analysis = json.dumps(analysis)

    alert.status = decision
    db.commit()
    return {"success": True, "alert_id": alert_id}


async def _analyze_chart_with_claude(image_b64: str, alert: TradingViewAlert) -> list:
    """Call Anthropic API to analyze chart image and return 8 bullet points."""
    if not ANTHROPIC_API_KEY:
        return ["Chart analysis unavailable — ANTHROPIC_API_KEY not set."]

    import httpx

    # Determine media type from base64 header if present
    media_type = "image/png"
    if image_b64.startswith("data:"):
        header, image_b64 = image_b64.split(",", 1)
        if "jpeg" in header or "jpg" in header:
            media_type = "image/jpeg"
        elif "webp" in header:
            media_type = "image/webp"

    ticker   = alert.ticker or "this instrument"
    interval = alert.interval or "unknown"
    price    = alert.price_close or "N/A"
    signal   = alert.signal_direction or "NEUTRAL"

    prompt = f"""You are a senior technical analyst at an Indian wealth management firm. 
Analyze this TradingView chart for {ticker} on {interval} timeframe. Alert triggered at price {price}. Signal direction: {signal}.

Provide exactly 8 concise bullet points covering:
1. Overall trend / structure
2. Key support / resistance levels visible
3. Momentum interpretation (RSI/MACD if visible)
4. Volume analysis
5. Candlestick pattern at alert trigger
6. Moving average alignment
7. Confluence or confirmation factors
8. Risk/reward observation and actionable insight for fund manager

Each bullet must be under 15 words. No preamble. Return ONLY the 8 bullet points, one per line, starting each with a bullet "•"."""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-5",
                    "max_tokens": 500,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_b64,
                                }
                            },
                            {"type": "text", "text": prompt}
                        ]
                    }]
                }
            )
        data = resp.json()
        text = data["content"][0]["text"].strip()
        bullets = [line.strip().lstrip("•").strip() for line in text.split("\n") if line.strip()]
        return bullets[:8]
    except Exception as e:
        logger.error(f"Claude chart analysis failed: {e}")
        return [f"Chart analysis error: {str(e)[:80]}"]


# ─── Chart image retrieval ─────────────────────────────

@app.get("/api/alerts/{alert_id}/chart")
async def get_chart(alert_id: int, db: Session = Depends(get_db)):
    action = db.query(AlertAction).filter_by(alert_id=alert_id).first()
    if not action or not action.chart_image_b64:
        raise HTTPException(status_code=404, detail="No chart image")
    return {"chart_image_b64": action.chart_image_b64}


# ─── Delete alert ──────────────────────────────────────

@app.delete("/api/alerts/{alert_id}")
async def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(TradingViewAlert).filter(TradingViewAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Not found")
    db.query(AlertAction).filter_by(alert_id=alert_id).delete()
    db.delete(alert)
    db.commit()
    return {"success": True}


# ─── Health ────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.0"}

@app.get("/")
async def root():
    return {"service": "JHAVERI FIE v3", "status": "running"}
