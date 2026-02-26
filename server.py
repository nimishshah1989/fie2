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
# WEBHOOK HELPERS
# ═══════════════════════════════════════════════════════

def _sf(v):
    """Safe float — ignores TradingView unfilled {{}} placeholders."""
    if v is None: return None
    s = str(v).strip()
    if "{{" in s or s.lower() in ("null", "nan", "none", ""): return None
    try: return float(s)
    except: return None

def _cs(v, default=""):
    """Safe string — strips whitespace and rejects TV placeholders."""
    if v is None: return default
    s = str(v).strip()
    return default if ("{{" in s or s.lower() in ("none", "null", "")) else s


# ─── Signal inference — multi-word phrases checked first (weighted 2×)
# to avoid single-word false draws like "crossed above resistance" scoring
# bull=1 (above) vs bear=1 (resistance) = NEUTRAL when it should be BULLISH.

_BULLISH_PHRASES = [
    "crossed above", "golden cross", "oversold bounce", "reversal up",
    "higher high", "higher low", "breakout above", "buy signal",
]
_BEARISH_PHRASES = [
    "crossed below", "death cross", "overbought reversal", "reversal down",
    "lower high", "lower low", "breakdown below", "sell signal",
]
_BULLISH_WORDS = [
    "bullish", "buy", "long", "breakout", "uptrend", "oversold",
    "accumulate", "above", "support", "bottom", "recovery",
]
_BEARISH_WORDS = [
    "bearish", "sell", "short", "breakdown", "downtrend", "overbought",
    "distribute", "below", "resistance", "top", "correction",
]
_JUNK = {"null", "none", "n/a", "your_alert_name", "your_alert_name_here", ""}


def _infer_signal(text: str) -> str:
    if not text: return "NEUTRAL"
    t = text.lower()
    bull = sum(2 for p in _BULLISH_PHRASES if p in t)
    bear = sum(2 for p in _BEARISH_PHRASES if p in t)
    bull += sum(1 for w in _BULLISH_WORDS if w in t)
    bear += sum(1 for w in _BEARISH_WORDS if w in t)
    if bull > bear: return "BULLISH"
    if bear > bull: return "BEARISH"
    return "NEUTRAL"


def _parse_alert_name(data_text: str, ticker: str) -> str:
    """Extract clean alert name: first non-junk line → first sentence → ticker fallback."""
    fallback = f"{ticker} Alert" if ticker else "Alert"
    if not data_text or data_text.strip().lower() in _JUNK:
        return fallback
    first_line = data_text.split("\n")[0].strip()
    if first_line and first_line.lower() not in _JUNK:
        name = first_line.split(".")[0].strip()
        return name[:80] if name else fallback
    return fallback


# ═══════════════════════════════════════════════════════
# WEBHOOK ENDPOINT
# ═══════════════════════════════════════════════════════

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
            # Non-JSON body — treat whole body as the data/message field
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

        # "data" field = {{strategy.order.alert_message}}
        alert_data = _cs(data.get("data"))

        # price_at_alert = close (the candle close when alert fired)
        price_at_alert = c

        sig        = _infer_signal(alert_data)
        alert_name = _parse_alert_name(alert_data, ticker)

        alert = TradingViewAlert(
            ticker         = ticker or "UNKNOWN",
            exchange       = exchange,
            interval       = interval,
            time_utc       = time_val,
            timenow_utc    = timenow,
            price_open     = o,
            price_high     = h,
            price_low      = l,
            price_close    = c,
            price_at_alert = price_at_alert,
            volume         = v,
            alert_data     = alert_data,
            alert_name     = alert_name,
            signal_direction = sig,
            raw_payload    = data,
            status         = AlertStatus.PENDING,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        logger.info(f"Alert #{alert.id} — {ticker} @ {c} | {sig} | name='{alert_name}'")
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
        "price_at_alert":  a.price_at_alert,
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
    decision:        str                    # APPROVED | DENIED
    action_call:     Optional[str] = None   # BUY / SELL / RATIO / etc.
    is_ratio:        Optional[bool] = False
    ratio_long:      Optional[str] = None
    ratio_short:     Optional[str] = None
    priority:        Optional[str] = None   # IMMEDIATELY | WITHIN_A_WEEK | WITHIN_A_MONTH
    chart_image_b64: Optional[str] = None  # base64 image (with or without data: URI prefix)


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
        # Run Claude vision analysis — stored as JSON array of 8 bullet strings
        analysis = await _analyze_chart_with_claude(req.chart_image_b64, alert)
        action.chart_analysis = json.dumps(analysis)

    alert.status = decision
    db.commit()
    return {"success": True, "alert_id": alert_id}


# ─── Claude Chart Analysis ─────────────────────────────

async def _analyze_chart_with_claude(image_b64: str, alert: TradingViewAlert) -> list:
    """
    Sends the chart image to claude-sonnet-4-5 vision.
    Returns a list of 8 institutional-grade bullet point strings.
    Stored in alert_actions.chart_analysis as a JSON array.
    """
    if not ANTHROPIC_API_KEY:
        return ["Chart analysis unavailable — ANTHROPIC_API_KEY not configured."]

    import httpx

    # Strip data: URI prefix if present, and detect media type
    media_type = "image/png"
    raw_b64 = image_b64
    if image_b64.startswith("data:"):
        header, raw_b64 = image_b64.split(",", 1)
        if "jpeg" in header or "jpg" in header:
            media_type = "image/jpeg"
        elif "webp" in header:
            media_type = "image/webp"
        elif "gif" in header:
            media_type = "image/gif"

    ticker   = alert.ticker   or "this instrument"
    interval = alert.interval or "unknown timeframe"
    price    = alert.price_at_alert or alert.price_close or "N/A"
    sig      = alert.signal_direction or "NEUTRAL"
    name     = alert.alert_name or ticker

    prompt = (
        f"You are a senior technical analyst at an Indian wealth management firm. "
        f"The fund manager has uploaded a TradingView chart for: {name} ({ticker}), "
        f"interval: {interval}, alert trigger price: {price}, signal direction: {sig}.\n\n"
        f"Provide exactly 8 concise institutional-grade bullet points covering:\n"
        f"1. Overall trend structure (higher highs/lows, downtrend, range)\n"
        f"2. Key support and resistance levels visible on the chart\n"
        f"3. Momentum indicator interpretation (RSI, MACD — if visible)\n"
        f"4. Volume analysis (confirming or diverging)\n"
        f"5. Candlestick pattern at the alert trigger candle\n"
        f"6. Moving average alignment (EMA/SMA crossovers if visible)\n"
        f"7. Confluence or confirmation factors for the signal\n"
        f"8. Risk/reward observation and single actionable insight for the fund manager\n\n"
        f"Rules: Each bullet under 20 words. No preamble, no numbering, no headers. "
        f"Return ONLY the 8 lines, each starting with •"
    )

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
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": raw_b64,
                                }
                            },
                            {"type": "text", "text": prompt}
                        ]
                    }]
                }
            )

        if resp.status_code != 200:
            logger.error(f"Claude API {resp.status_code}: {resp.text[:200]}")
            return [f"Claude API error {resp.status_code} — check API key and credits."]

        data = resp.json()
        raw_text = data["content"][0]["text"].strip()
        # Parse bullet lines — strip leading •, numbers, or whitespace
        bullets = []
        for line in raw_text.split("\n"):
            clean = line.strip().lstrip("•").lstrip("0123456789").lstrip(".").lstrip(")").strip()
            if clean:
                bullets.append(clean)
        # Return exactly up to 8; pad with placeholder if Claude returned fewer
        result = bullets[:8]
        while len(result) < 8:
            result.append("—")
        return result

    except httpx.TimeoutException:
        logger.error("Claude API timeout after 45s")
        return ["Chart analysis timed out — try re-approving with the same image."]
    except Exception as e:
        logger.error(f"Claude chart analysis failed: {e}", exc_info=True)
        return [f"Chart analysis error: {str(e)[:100]}"]


# ─── Chart image retrieval ─────────────────────────────

@app.get("/api/alerts/{alert_id}/chart")
async def get_chart(alert_id: int, db: Session = Depends(get_db)):
    action = db.query(AlertAction).filter_by(alert_id=alert_id).first()
    if not action or not action.chart_image_b64:
        raise HTTPException(status_code=404, detail="No chart image found")
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
