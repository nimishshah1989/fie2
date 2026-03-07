"""
FIE v3 — Alert Routes
TradingView webhook ingestion, alert CRUD, FM actions, performance tracking, actionables.
"""

import asyncio
import json
import logging
import threading
import types
from datetime import datetime
from typing import Optional, Any

from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import desc

from models import (
    get_db, IndexPrice, SessionLocal,
    TradingViewAlert, AlertAction, AlertStatus, ActionPriority,
)
from services.claude_service import (
    ANTHROPIC_API_KEY, analyze_chart_vision, analyze_text_only,
)
from services.telegram_service import TELEGRAM_ENABLED, send_alert_card

logger = logging.getLogger("fie_v3.alerts")
router = APIRouter()


# ─── Webhook Parsing Helpers ──────────────────────────────────────

def _sf(v):
    """Safe float conversion."""
    if v is None: return None
    s = str(v).strip()
    if "{{" in s or s.lower() in ("null", "nan", "none", ""): return None
    try: return float(s)
    except Exception: return None

def _cs(v, default=""):
    """Clean string — strip template vars and junk."""
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


# ─── Alert Serialization ─────────────────────────────────────────

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
            "ratio_numerator_ticker":   ac.ratio_numerator_ticker,
            "ratio_denominator_ticker": ac.ratio_denominator_ticker,
            "priority":       ac.priority.value if ac.priority else None,
            "has_chart":      bool(ac.chart_image_b64),
            "chart_analysis": json.loads(ac.chart_analysis) if ac.chart_analysis else None,
            "decision_at":    (ac.decision_at.isoformat() + "Z") if ac.decision_at else None,
            "fm_notes":       ac.fm_notes,
            "entry_price_low":  ac.entry_price_low,
            "entry_price_high": ac.entry_price_high,
            "stop_loss":        ac.stop_loss,
            "target_price":     ac.target_price,
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
        "received_at":      (a.received_at.isoformat() + "Z") if a.received_at else None,
        "action":           action,
    }


# ─── Pydantic Models ─────────────────────────────────────────────

class WebhookPayload(BaseModel):
    """Validates TradingView webhook input after JSON parsing.

    TradingView sends flexible payloads with varying field names, so we allow
    extra fields and use lenient types. The _cs()/_sf() helpers still handle
    template variable cleanup after validation.
    """
    model_config = ConfigDict(extra="allow")

    # ticker is the only truly required field — defaults to empty string
    # if absent so we can return a 400 with a clear message
    ticker: Optional[str] = Field(None, max_length=50)
    exchange: Optional[str] = Field(None, max_length=50)
    interval: Optional[str] = Field(None, max_length=20)

    # TradingView uses both "time"/"timenow" and "time_utc"/"timenow_utc"
    time: Optional[str] = Field(None, max_length=50)
    time_utc: Optional[str] = Field(None, max_length=50)
    timenow: Optional[str] = Field(None, max_length=50)

    # Price fields — accept Any because TradingView may send strings or numbers
    open: Optional[Any] = None
    high: Optional[Any] = None
    low: Optional[Any] = None
    close: Optional[Any] = None
    price_open: Optional[Any] = None
    price_high: Optional[Any] = None
    price_low: Optional[Any] = None
    price_at_alert: Optional[Any] = None
    volume: Optional[Any] = None

    # Alert metadata
    data: Optional[str] = Field(None, max_length=5000)
    alert_message: Optional[str] = Field(None, max_length=5000)
    alert_name: Optional[str] = Field(None, max_length=200)
    signal_direction: Optional[str] = Field(None, max_length=20)
    strategy_action: Optional[str] = Field(None, max_length=20)

    @field_validator("ticker", mode="before")
    @classmethod
    def clean_ticker(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        # Reject unresolved TradingView template variables
        if "{{" in s or s.lower() in ("null", "none", ""):
            return None
        return s[:50]


def _validate_webhook_payload(data: dict) -> WebhookPayload:
    """Parse and validate webhook dict. Raises HTTPException on failure."""
    try:
        payload = WebhookPayload.model_validate(data)
    except Exception as exc:
        logger.warning("Webhook validation failed: %s", exc)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid webhook payload: {exc}",
        )
    return payload


class ActionRequest(BaseModel):
    alert_id:        int
    decision:        str
    action_call:     Optional[str] = None
    is_ratio:        Optional[bool] = False
    ratio_long:      Optional[str] = None
    ratio_short:     Optional[str] = None
    ratio_numerator_ticker:   Optional[str] = None
    ratio_denominator_ticker: Optional[str] = None
    priority:        Optional[str] = None
    chart_image_b64: Optional[str] = None
    fm_notes:        Optional[str] = None
    entry_price_low:  Optional[float] = None
    entry_price_high: Optional[float] = None
    stop_loss:        Optional[float] = None
    target_price:     Optional[float] = None


class UpdateActionRequest(BaseModel):
    action_call:     Optional[str] = None
    priority:        Optional[str] = None
    fm_notes:        Optional[str] = None
    entry_price_low:  Optional[float] = None
    entry_price_high: Optional[float] = None
    stop_loss:        Optional[float] = None
    target_price:     Optional[float] = None


# ─── Webhook Endpoint ─────────────────────────────────────────────

@router.post("/webhook/tradingview")
@router.post("/webhook/tradingview/")
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        body = (await request.body()).decode("utf-8")
        logger.info("WEBHOOK: %s", body[:300])
        try:
            data = json.loads(body)
        except Exception:
            data = {"data": body}

        # Validate payload structure and field constraints
        _validate_webhook_payload(data)

        ticker     = _cs(data.get("ticker"))
        exchange   = _cs(data.get("exchange"))
        interval   = _cs(data.get("interval"))
        time_val   = _cs(data.get("time")) or _cs(data.get("time_utc"))
        timenow    = _cs(data.get("timenow"))
        # Support both TradingView native keys (open/high/low/close)
        # and prefixed keys (price_open/price_high/price_low/price_at_alert)
        o          = _sf(data.get("open")) or _sf(data.get("price_open"))
        h          = _sf(data.get("high")) or _sf(data.get("price_high"))
        l          = _sf(data.get("low")) or _sf(data.get("price_low"))
        c          = _sf(data.get("close")) or _sf(data.get("price_at_alert"))
        v          = _sf(data.get("volume"))
        # Support both "data" (legacy) and "alert_message" keys
        alert_data = _cs(data.get("data")) or _cs(data.get("alert_message"))

        # Resolve signal: explicit field -> strategy.order.action -> text inference
        _SIG_MAP = {"buy": "BULLISH", "sell": "BEARISH", "long": "BULLISH", "short": "BEARISH"}
        explicit_sig = _cs(data.get("signal_direction")).upper()
        strategy_action = _cs(data.get("strategy_action"))  # from {{strategy.order.action}}
        if explicit_sig in ("BULLISH", "BEARISH", "NEUTRAL"):
            sig = explicit_sig
        elif strategy_action and strategy_action.lower() in _SIG_MAP:
            sig = _SIG_MAP[strategy_action.lower()]
        else:
            sig = _infer_signal(alert_data)

        # Use explicit alert_name if provided (skip placeholder values)
        explicit_name = _cs(data.get("alert_name"))
        alert_name = explicit_name if explicit_name and explicit_name.lower() not in _JUNK and "your_" not in explicit_name.lower() else _parse_alert_name(alert_data, ticker)

        price_at = _sf(data.get("price_at_alert")) or c
        alert = TradingViewAlert(
            ticker=ticker or "UNKNOWN", exchange=exchange, interval=interval,
            time_utc=time_val, timenow_utc=timenow,
            price_open=o, price_high=h, price_low=l, price_close=c,
            price_at_alert=price_at, volume=v, alert_data=alert_data,
            alert_name=alert_name, signal_direction=sig,
            raw_payload=data, status=AlertStatus.PENDING,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        logger.info("Alert #%d — %s @ %s | %s", alert.id, ticker, c, sig)
        return {"success": True, "alert_id": alert.id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Webhook error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ─── Alert CRUD ───────────────────────────────────────────────────

@router.get("/api/alerts")
async def get_alerts(status: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    q = db.query(TradingViewAlert).order_by(desc(TradingViewAlert.received_at))
    if status and status != "All":
        try:
            q = q.filter(TradingViewAlert.status == AlertStatus(status))
        except Exception:
            pass
    return {"alerts": [_serialize(a) for a in q.limit(limit).all()]}


@router.get("/api/alerts/{alert_id}")
async def get_alert(alert_id: int, db: Session = Depends(get_db)):
    a = db.query(TradingViewAlert).filter(TradingViewAlert.id == alert_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Not found")
    return _serialize(a)


# ─── Background Claude Analysis ──────────────────────────────────

def _background_claude_analysis(
    action_id: int, chart_b64: Optional[str], alert_snapshot: dict
):
    """Run Claude analysis + stock history fetch in a background thread."""
    try:
        db = SessionLocal()
        alert_ns = types.SimpleNamespace(**alert_snapshot)

        # Claude analysis
        if chart_b64:
            analysis = asyncio.run(analyze_chart_vision(chart_b64, alert_ns))
        else:
            analysis = asyncio.run(analyze_text_only(alert_ns))

        action = db.query(AlertAction).filter_by(id=action_id).first()
        if action:
            action.chart_analysis = json.dumps(analysis)
            db.commit()
            logger.info("Background Claude analysis stored for action %d", action_id)

        # Fetch 12M stock history
        ticker = alert_snapshot.get("ticker")
        if ticker and ticker != "UNKNOWN":
            from price_service import fetch_stock_history
            from services.data_helpers import upsert_price_row
            rows = fetch_stock_history(ticker, "1y")
            for row in rows:
                upsert_price_row(db, ticker, row)
            db.commit()
            logger.info("Background stock history: %s — %d rows", ticker, len(rows))

        db.close()
    except Exception as e:
        logger.warning("Background Claude analysis failed for action %d: %s", action_id, e)


def _background_telegram_notify(alert_id: int, alert_snapshot: dict, action_snapshot: dict):
    """Wait for Claude analysis (up to 60s), then send full card to Telegram."""
    import time
    try:
        db = SessionLocal()
        action = db.query(AlertAction).filter_by(alert_id=alert_id).first()

        # Poll for Claude analysis to arrive (12 x 5s = 60s max)
        for _ in range(12):
            if action and action.chart_analysis:
                break
            time.sleep(5)
            db.refresh(action) if action else None

        # Build action dict with latest analysis
        telegram_action = dict(action_snapshot)
        if action and action.chart_analysis:
            telegram_action["chart_analysis"] = action.chart_analysis

        asyncio.run(send_alert_card(alert_snapshot, telegram_action))
        logger.info("Telegram notification sent for alert #%d", alert_id)
        db.close()
    except Exception as exc:
        logger.warning("Telegram notify failed for alert #%d: %s", alert_id, exc)


@router.post("/api/alerts/{alert_id}/action")
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
    action.ratio_numerator_ticker   = req.ratio_numerator_ticker
    action.ratio_denominator_ticker = req.ratio_denominator_ticker

    if req.priority:
        try:
            action.priority = ActionPriority(req.priority)
        except Exception:
            action.priority = None

    if req.chart_image_b64:
        action.chart_image_b64 = req.chart_image_b64
    if req.fm_notes:
        action.fm_notes = req.fm_notes

    action.entry_price_low  = req.entry_price_low
    action.entry_price_high = req.entry_price_high
    action.stop_loss        = req.stop_loss
    action.target_price     = req.target_price

    alert.status = decision
    db.commit()
    db.refresh(action)

    # Spawn background thread for Claude analysis + stock history on APPROVED
    if decision == AlertStatus.APPROVED:
        alert_snapshot = {
            "ticker": alert.ticker, "interval": alert.interval,
            "price_at_alert": alert.price_at_alert, "price_close": alert.price_close,
            "signal_direction": alert.signal_direction, "alert_name": alert.alert_name,
            "alert_data": alert.alert_data, "price_open": alert.price_open,
            "price_high": alert.price_high, "price_low": alert.price_low,
            "volume": alert.volume, "exchange": alert.exchange,
        }
        if ANTHROPIC_API_KEY:
            threading.Thread(
                target=_background_claude_analysis,
                args=(action.id, req.chart_image_b64, alert_snapshot),
                daemon=True, name=f"claude-analysis-{alert_id}",
            ).start()

        if TELEGRAM_ENABLED:
            action_snapshot = {
                "action_call": action.action_call,
                "chart_image_b64": req.chart_image_b64,
                "fm_notes": action.fm_notes,
                "entry_price_low": action.entry_price_low,
                "entry_price_high": action.entry_price_high,
                "stop_loss": action.stop_loss,
                "target_price": action.target_price,
                "decision_at": (action.decision_at.isoformat() + "Z") if action.decision_at else None,
            }
            threading.Thread(
                target=_background_telegram_notify,
                args=(alert_id, alert_snapshot, action_snapshot),
                daemon=True, name=f"telegram-{alert_id}",
            ).start()

    return {"success": True, "alert_id": alert_id}


@router.put("/api/alerts/{alert_id}/action")
async def update_action(alert_id: int, req: UpdateActionRequest, db: Session = Depends(get_db)):
    alert = db.query(TradingViewAlert).filter(TradingViewAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    action = db.query(AlertAction).filter_by(alert_id=alert_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="No action found for this alert")

    if req.action_call is not None:
        action.action_call = req.action_call
    if req.priority is not None:
        try:
            action.priority = ActionPriority(req.priority)
        except Exception:
            pass
    if req.fm_notes is not None:
        action.fm_notes = req.fm_notes
    if req.entry_price_low is not None:
        action.entry_price_low = req.entry_price_low
    if req.entry_price_high is not None:
        action.entry_price_high = req.entry_price_high
    if req.stop_loss is not None:
        action.stop_loss = req.stop_loss
    if req.target_price is not None:
        action.target_price = req.target_price

    action.updated_at = datetime.now()
    db.commit()
    return {"success": True, "alert_id": alert_id}


@router.delete("/api/alerts/all")
async def delete_all_alerts(db: Session = Depends(get_db)):
    """Batch delete ALL alerts and their actions. Use with caution."""
    actions_deleted = db.query(AlertAction).delete()
    alerts_deleted = db.query(TradingViewAlert).delete()
    db.commit()
    logger.info("Batch delete: %d actions, %d alerts", actions_deleted, alerts_deleted)
    return {"success": True, "deleted_count": alerts_deleted}


@router.delete("/api/alerts/{alert_id}")
async def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(TradingViewAlert).filter(TradingViewAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Not found")
    db.query(AlertAction).filter_by(alert_id=alert_id).delete()
    db.delete(alert)
    db.commit()
    return {"success": True}


@router.get("/api/alerts/{alert_id}/chart")
async def get_chart(alert_id: int, db: Session = Depends(get_db)):
    action = db.query(AlertAction).filter_by(alert_id=alert_id).first()
    if not action or not action.chart_image_b64:
        raise HTTPException(status_code=404, detail="No chart image found")
    return {"chart_image_b64": action.chart_image_b64}


# ─── Performance Tracking ────────────────────────────────────────

@router.get("/api/performance")
async def performance(db: Session = Depends(get_db)):
    from price_service import get_live_price

    approved = (
        db.query(TradingViewAlert)
        .filter(TradingViewAlert.status == AlertStatus.APPROVED)
        .order_by(desc(TradingViewAlert.received_at))
        .all()
    )
    results = []
    for a in approved:
        entry_price = a.price_at_alert or a.price_close
        direction = a.signal_direction or "BULLISH"

        action_obj = a.action
        is_ratio = action_obj.is_ratio if action_obj else False
        ratio_num_ticker = action_obj.ratio_numerator_ticker if action_obj else None
        ratio_den_ticker = action_obj.ratio_denominator_ticker if action_obj else None

        curr_price = None
        ratio_data = None

        if is_ratio and ratio_num_ticker and ratio_den_ticker:
            num_live = get_live_price(ratio_num_ticker)
            den_live = get_live_price(ratio_den_ticker)
            num_price = num_live.get("current_price")
            den_price = den_live.get("current_price")
            if num_price and den_price and den_price > 0:
                curr_price = round(num_price / den_price, 4)
            ratio_data = {
                "numerator_ticker": ratio_num_ticker,
                "denominator_ticker": ratio_den_ticker,
                "numerator_price": num_price,
                "denominator_price": den_price,
            }
        else:
            live = get_live_price(a.ticker or "")
            curr_price = live.get("current_price")

        if not entry_price or not curr_price:
            results.append({
                **_serialize(a),
                "trigger_price": a.price_at_alert, "entry_price": entry_price,
                "current_price": curr_price, "return_pct": None, "return_abs": None,
                "days_since": None, "is_ratio_trade": is_ratio, "ratio_data": ratio_data,
            })
            continue

        mult = -1.0 if direction == "BEARISH" else 1.0
        return_abs = round(mult * (curr_price - entry_price), 2)
        return_pct = round(mult * ((curr_price / entry_price) - 1) * 100, 2) if entry_price > 0 else None

        days_since = None
        if a.received_at:
            days_since = (datetime.now() - a.received_at).days

        results.append({
            **_serialize(a),
            "trigger_price": a.price_at_alert, "entry_price": entry_price,
            "current_price": curr_price, "return_pct": return_pct, "return_abs": return_abs,
            "days_since": days_since, "is_ratio_trade": is_ratio, "ratio_data": ratio_data,
        })
    return {"performance": results}


# ─── Actionables (SL/TP triggered alerts) ────────────────────────

@router.get("/api/actionables")
async def actionables(db: Session = Depends(get_db)):
    """Return approved alerts where current price has hit stop_loss or target_price."""
    from price_service import get_live_price

    approved = (
        db.query(TradingViewAlert)
        .filter(TradingViewAlert.status == AlertStatus.APPROVED)
        .order_by(desc(TradingViewAlert.received_at))
        .all()
    )
    results = []
    for a in approved:
        action_obj = a.action
        if not action_obj:
            continue
        sl = action_obj.stop_loss
        tp = action_obj.target_price
        if sl is None and tp is None:
            continue

        entry_low = action_obj.entry_price_low
        entry_high = action_obj.entry_price_high
        if entry_low is not None and entry_high is not None:
            entry_price = (entry_low + entry_high) / 2.0
        elif entry_low is not None:
            entry_price = entry_low
        elif entry_high is not None:
            entry_price = entry_high
        else:
            entry_price = a.price_at_alert or a.price_close

        if not entry_price or entry_price <= 0:
            continue

        is_ratio = action_obj.is_ratio if action_obj else False
        ratio_num = action_obj.ratio_numerator_ticker
        ratio_den = action_obj.ratio_denominator_ticker

        curr_price = None
        if is_ratio and ratio_num and ratio_den:
            num_live = get_live_price(ratio_num)
            den_live = get_live_price(ratio_den)
            np_ = num_live.get("current_price")
            dp_ = den_live.get("current_price")
            if np_ and dp_ and dp_ > 0:
                curr_price = round(np_ / dp_, 4)
        else:
            live = get_live_price(a.ticker or "")
            curr_price = live.get("current_price")

        if curr_price is None:
            continue

        direction = (a.signal_direction or "BULLISH").upper()
        is_bullish = direction != "BEARISH"

        trigger_type = None
        if is_bullish:
            if sl is not None and curr_price <= sl:
                trigger_type = "SL_HIT"
            elif tp is not None and curr_price >= tp:
                trigger_type = "TP_HIT"
        else:
            if sl is not None and curr_price >= sl:
                trigger_type = "SL_HIT"
            elif tp is not None and curr_price <= tp:
                trigger_type = "TP_HIT"

        if trigger_type is None:
            continue

        if trigger_type == "TP_HIT" and tp is not None:
            pnl_price = tp
        elif trigger_type == "SL_HIT" and sl is not None:
            pnl_price = sl
        else:
            pnl_price = curr_price

        mult = -1.0 if not is_bullish else 1.0
        pnl_abs = round(mult * (pnl_price - entry_price), 2)
        pnl_pct = round(mult * ((pnl_price - entry_price) / entry_price) * 100, 2)

        days_since = None
        if a.received_at:
            days_since = (datetime.now() - a.received_at).days

        results.append({
            **_serialize(a),
            "trigger_type": trigger_type,
            "entry_price": round(entry_price, 2),
            "current_price": curr_price,
            "stop_loss": sl, "target_price": tp,
            "pnl_pct": pnl_pct, "pnl_abs": pnl_abs,
            "days_since": days_since, "is_ratio_trade": is_ratio,
        })
    return {"actionables": results}
