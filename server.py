"""
FIE v3 — FastAPI Server
Jhaveri Intelligence Platform
"""

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json, os, logging
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


# ─── Webhook helpers ───────────────────────────────────

def _sf(v):
    if v is None: return None
    s = str(v).strip()
    if "{{" in s or s.lower() in ("null", "nan", "none", ""): return None
    try: return float(s)
    except: return None

def _cs(v, default=""):
    if v is None: return default
    s = str(v).strip()
    return default if ("{{" in s or s.lower() in ("none", "null", "")) else s

_BULLISH_PHRASES = ["crossed above", "golden cross", "oversold bounce", "reversal up",
                    "higher high", "higher low", "breakout above", "buy signal"]
_BEARISH_PHRASES = ["crossed below", "death cross", "overbought reversal", "reversal down",
                    "lower high", "lower low", "breakdown below", "sell signal"]
_BULLISH_WORDS   = ["bullish", "buy", "long", "breakout", "uptrend", "oversold",
                    "accumulate", "above", "support", "bottom", "recovery"]
_BEARISH_WORDS   = ["bearish", "sell", "short", "breakdown", "downtrend", "overbought",
                    "distribute", "below", "resistance", "top", "correction"]
_JUNK = {"null", "none", "n/a", "your_alert_name", "your_alert_name_here", ""}


def _infer_signal(text: str) -> str:
    if not text: return "NEUTRAL"
    t = text.lower()
    bull = sum(2 for p in _BULLISH_PHRASES if p in t) + sum(1 for w in _BULLISH_WORDS if w in t)
    bear = sum(2 for p in _BEARISH_PHRASES if p in t) + sum(1 for w in _BEARISH_WORDS if w in t)
    if bull > bear: return "BULLISH"
    if bear > bull: return "BEARISH"
    return "NEUTRAL"


def _parse_alert_name(data_text: str, ticker: str) -> str:
    fallback = (ticker + " Alert") if ticker else "Alert"
    if not data_text or data_text.strip().lower() in _JUNK:
        return fallback
    first_line = data_text.split("\n")[0].strip()
    if first_line and first_line.lower() not in _JUNK:
        name = first_line.split(".")[0].strip()
        return name[:80] if name else fallback
    return fallback


def _parse_bullets(raw_text: str) -> list:
    bullets = []
    for line in raw_text.strip().split("\n"):
        clean = line.strip().lstrip("•").lstrip("0123456789").lstrip(".").lstrip(")").strip()
        if clean:
            bullets.append(clean)
    result = bullets[:8]
    while len(result) < 8:
        result.append("—")
    return result


# ─── Startup ───────────────────────────────────────────

@app.on_event("startup")
async def startup():
    init_db()


# ─── Webhook ───────────────────────────────────────────

@app.post("/webhook/tradingview")
@app.post("/webhook/tradingview/")
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        body = (await request.body()).decode("utf-8")
        logger.info("WEBHOOK: %s", body[:300])
        try:
            data = json.loads(body)
        except Exception:
            data = {"data": body}

        ticker     = _cs(data.get("ticker"))
        exchange   = _cs(data.get("exchange"))
        interval   = _cs(data.get("interval"))
        time_val   = _cs(data.get("time"))
        timenow    = _cs(data.get("timenow"))
        o          = _sf(data.get("open"))
        h          = _sf(data.get("high"))
        l          = _sf(data.get("low"))
        c          = _sf(data.get("close"))
        v          = _sf(data.get("volume"))
        alert_data = _cs(data.get("data"))

        sig        = _infer_signal(alert_data)
        alert_name = _parse_alert_name(alert_data, ticker)

        alert = TradingViewAlert(
            ticker           = ticker or "UNKNOWN",
            exchange         = exchange,
            interval         = interval,
            time_utc         = time_val,
            timenow_utc      = timenow,
            price_open       = o,
            price_high       = h,
            price_low        = l,
            price_close      = c,
            price_at_alert   = c,
            volume           = v,
            alert_data       = alert_data,
            alert_name       = alert_name,
            signal_direction = sig,
            raw_payload      = data,
            status           = AlertStatus.PENDING,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        logger.info("Alert #%d — %s @ %s | %s", alert.id, ticker, c, sig)
        return {"success": True, "alert_id": alert.id}

    except Exception as e:
        logger.error("Webhook error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ─── Serialization ─────────────────────────────────────

def _serialize(a: TradingViewAlert) -> dict:
    action = None
    if a.action:
        ac = a.action
        action = {
            "decision":       ac.decision.value,
            "action_call":    ac.action_call,
            "is_ratio":       ac.is_ratio,
            "ratio_long":     ac.ratio_long,
            "ratio_short":    ac.ratio_short,
            "priority":       ac.priority.value if ac.priority else None,
            "has_chart":      bool(ac.chart_image_b64),
            "chart_analysis": json.loads(ac.chart_analysis) if ac.chart_analysis else None,
            "decision_at":    ac.decision_at.isoformat() if ac.decision_at else None,
        }
    return {
        "id":               a.id,
        "ticker":           a.ticker or "—",
        "exchange":         a.exchange or "—",
        "interval":         a.interval or "—",
        "time_utc":         a.time_utc,
        "timenow_utc":      a.timenow_utc,
        "price_open":       a.price_open,
        "price_high":       a.price_high,
        "price_low":        a.price_low,
        "price_close":      a.price_close,
        "price_at_alert":   a.price_at_alert,
        "volume":           a.volume,
        "alert_data":       a.alert_data,
        "alert_name":       a.alert_name or a.ticker,
        "signal_direction": a.signal_direction or "NEUTRAL",
        "status":           a.status.value,
        "received_at":      a.received_at.isoformat() if a.received_at else None,
        "action":           action,
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
    decision:        str
    action_call:     Optional[str] = None
    is_ratio:        Optional[bool] = False
    ratio_long:      Optional[str] = None
    ratio_short:     Optional[str] = None
    priority:        Optional[str] = None
    chart_image_b64: Optional[str] = None


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

    # Always run Claude analysis on APPROVED
    # Vision analysis if chart uploaded, text-only otherwise
    if decision == AlertStatus.APPROVED and ANTHROPIC_API_KEY:
        if req.chart_image_b64:
            analysis = await _analyze_with_vision(req.chart_image_b64, alert)
        else:
            analysis = await _analyze_text_only(alert)
        action.chart_analysis = json.dumps(analysis)

    alert.status = decision
    db.commit()
    return {"success": True, "alert_id": alert_id}


# ─── Claude: vision (chart image) ─────────────────────

async def _analyze_with_vision(image_b64: str, alert: TradingViewAlert) -> list:
    import httpx

    media_type = "image/png"
    raw_b64 = image_b64
    if image_b64.startswith("data:"):
        header, raw_b64 = image_b64.split(",", 1)
        if "jpeg" in header or "jpg" in header:
            media_type = "image/jpeg"
        elif "webp" in header:
            media_type = "image/webp"

    ticker   = str(alert.ticker   or "this instrument")
    interval = str(alert.interval or "unknown")
    price    = str(alert.price_at_alert or alert.price_close or "N/A")
    sig      = str(alert.signal_direction or "")
    name     = str(alert.alert_name or ticker)

    prompt = "\n".join([
        "You are a senior technical analyst at an Indian wealth management firm.",
        "Fund manager uploaded a TradingView chart for: " + name + " (" + ticker + "),",
        "interval: " + interval + ", alert price: " + price + ", signal: " + sig + ".",
        "",
        "Provide exactly 8 concise institutional bullet points covering:",
        "1. Overall trend structure",
        "2. Key support and resistance levels",
        "3. Momentum (RSI/MACD if visible)",
        "4. Volume analysis",
        "5. Candlestick pattern at trigger candle",
        "6. Moving average alignment",
        "7. Confluence/confirmation factors",
        "8. Risk/reward and actionable insight for fund manager",
        "",
        "Rules: Each bullet under 20 words. No preamble. Return ONLY 8 lines each starting with •",
    ])

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-5",
                    "max_tokens": 600,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": raw_b64,
                            }},
                            {"type": "text", "text": prompt}
                        ]
                    }]
                }
            )
        if resp.status_code != 200:
            logger.error("Claude API %d: %s", resp.status_code, resp.text[:200])
            return ["Claude API error " + str(resp.status_code) + " — check key/credits."]
        return _parse_bullets(resp.json()["content"][0]["text"])
    except httpx.TimeoutException:
        return ["Chart analysis timed out — re-approve to retry."]
    except Exception as e:
        logger.error("Vision analysis failed: %s", e, exc_info=True)
        return ["Chart analysis error: " + str(e)[:80]]


# ─── Claude: text-only ─────────────────────────────────

async def _analyze_text_only(alert: TradingViewAlert) -> list:
    import httpx

    ticker   = str(alert.ticker   or "Unknown")
    interval = str(alert.interval or "unknown")
    price    = str(alert.price_at_alert or alert.price_close or "N/A")
    sig      = str(alert.signal_direction or "not specified")
    o        = str(alert.price_open)
    h        = str(alert.price_high)
    l        = str(alert.price_low)
    c        = str(alert.price_close)
    v        = str(alert.volume)
    msg      = str(alert.alert_data or "(no alert message)")

    prompt = "\n".join([
        "You are a senior technical analyst at an Indian wealth management firm.",
        "Analyse this TradingView alert and provide 8 concise institutional insights.",
        "",
        "Instrument: " + ticker + "  |  Interval: " + interval + "  |  Signal: " + sig,
        "Alert price: " + price + "  |  O: " + o + "  H: " + h + "  L: " + l + "  C: " + c + "  Vol: " + v,
        "Alert message: " + msg,
        "",
        "Cover: trend context, key levels from OHLCV, momentum, signal validity,",
        "risk considerations, position sizing thought, actionable insight for FM.",
        "",
        "Rules: Each bullet under 20 words. No preamble. Return ONLY 8 lines each starting with •",
    ])

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
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
        if resp.status_code != 200:
            return ["Claude API error " + str(resp.status_code)]
        return _parse_bullets(resp.json()["content"][0]["text"])
    except Exception as e:
        logger.error("Text analysis failed: %s", e)
        return ["Analysis error: " + str(e)[:80]]


# ─── Chart retrieval ───────────────────────────────────

@app.get("/api/alerts/{alert_id}/chart")
async def get_chart(alert_id: int, db: Session = Depends(get_db)):
    action = db.query(AlertAction).filter_by(alert_id=alert_id).first()
    if not action or not action.chart_image_b64:
        raise HTTPException(status_code=404, detail="No chart image found")
    return {"chart_image_b64": action.chart_image_b64}


@app.delete("/api/alerts/{alert_id}")
async def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(TradingViewAlert).filter(TradingViewAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Not found")
    db.query(AlertAction).filter_by(alert_id=alert_id).delete()
    db.delete(alert)
    db.commit()
    return {"success": True}


@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.0"}

@app.get("/")
async def root():
    return {"service": "JHAVERI FIE v3", "status": "running"}
