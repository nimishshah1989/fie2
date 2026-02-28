"""
FIE v3 — FastAPI Server
Jhaveri Intelligence Platform
"""

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json, os, logging, csv, io, subprocess, threading
from pathlib import Path
from datetime import datetime, date as date_type, timedelta
from typing import Optional, List, Dict
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc, func as sa_func
from fastapi.responses import FileResponse, StreamingResponse

from models import (
    init_db, get_db, SessionLocal,
    TradingViewAlert, AlertAction, AlertStatus, ActionPriority, IndexPrice,
    ModelPortfolio, PortfolioHolding, PortfolioTransaction, PortfolioNAV,
    PortfolioStatus, TransactionType,
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

def _background_nse_history_fetch():
    """Background thread: fetch full 1Y daily history from NSE API for all indices."""
    import threading
    logger.info("Background NSE history fetch starting (thread: %s)...", threading.current_thread().name)
    try:
        from price_service import fetch_historical_indices_nse_sync
        db = SessionLocal()
        hist_data = fetch_historical_indices_nse_sync(period="1y")
        stored = 0
        for idx_name, rows in hist_data.items():
            for row in rows:
                if _upsert_price_row(db, idx_name, row):
                    stored += 1
        db.commit()
        db.close()
        logger.info("Background NSE history: stored %d records across %d indices", stored, len(hist_data))
    except Exception as e:
        logger.warning("Background NSE history fetch failed (non-fatal): %s", e)


@app.on_event("startup")
async def startup():
    init_db()
    # Phase 1 (fast, ~5s): nsetools reference points for all 135+ indices
    try:
        from price_service import fetch_historical_indices
        db = SessionLocal()
        from sqlalchemy import func as sqlfunc2
        latest = db.query(sqlfunc2.max(IndexPrice.date)).scalar()
        needs_backfill = (
            latest is None
            or (datetime.now() - datetime.strptime(latest, "%Y-%m-%d")).days > 2
        )
        if needs_backfill:
            logger.info("Startup: storing nsetools reference points for all NSE indices...")
            hist_data = fetch_historical_indices(period="1y")
            stored = 0
            for idx_name, rows in hist_data.items():
                for row in rows:
                    if _upsert_price_row(db, idx_name, row):
                        stored += 1
            db.commit()
            logger.info("Startup: stored %d reference records for %d indices", stored, len(hist_data))
        else:
            logger.info("Historical data is recent (latest=%s), skipping backfill", latest)
        db.close()
    except Exception as e:
        logger.warning("Startup reference fetch failed (non-fatal): %s", e)

    # Phase 2 (background thread): try NSE historical API for full daily data
    # This does NOT block the server — runs in background
    import threading
    bg_thread = threading.Thread(target=_background_nse_history_fetch, daemon=True, name="nse-history")
    bg_thread.start()
    logger.info("Startup complete — NSE history fetch running in background")


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
            "ratio_numerator_ticker":   ac.ratio_numerator_ticker,
            "ratio_denominator_ticker": ac.ratio_denominator_ticker,
            "priority":       ac.priority.value if ac.priority else None,
            "has_chart":      bool(ac.chart_image_b64),
            "chart_analysis": json.loads(ac.chart_analysis) if ac.chart_analysis else None,
            "decision_at":    ac.decision_at.isoformat() if ac.decision_at else None,
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
    ratio_numerator_ticker:   Optional[str] = None
    ratio_denominator_ticker: Optional[str] = None
    priority:        Optional[str] = None
    chart_image_b64: Optional[str] = None
    fm_notes:        Optional[str] = None
    entry_price_low:  Optional[float] = None
    entry_price_high: Optional[float] = None
    stop_loss:        Optional[float] = None
    target_price:     Optional[float] = None


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

    # Trade parameters
    action.entry_price_low  = req.entry_price_low
    action.entry_price_high = req.entry_price_high
    action.stop_loss        = req.stop_loss
    action.target_price     = req.target_price

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

    # On approval, fetch 12M history for this stock (for performance tracking)
    if decision == AlertStatus.APPROVED and alert.ticker and alert.ticker != "UNKNOWN":
        try:
            from price_service import fetch_stock_history
            rows = fetch_stock_history(alert.ticker, "1y")
            for row in rows:
                if not row.get("close"):
                    continue
                existing = db.query(IndexPrice).filter_by(
                    date=row["date"], index_name=alert.ticker
                ).first()
                if not existing:
                    db.add(IndexPrice(
                        date=row["date"], index_name=alert.ticker,
                        close_price=row["close"], open_price=row.get("open"),
                        high_price=row.get("high"), low_price=row.get("low"),
                        volume=row.get("volume"),
                    ))
            db.commit()
            logger.info("Stored 12M history for %s (%d rows)", alert.ticker, len(rows))
        except Exception as e:
            logger.warning("Stock history fetch for %s failed: %s", alert.ticker, e)

    return {"success": True, "alert_id": alert_id}


class UpdateActionRequest(BaseModel):
    action_call:     Optional[str] = None
    priority:        Optional[str] = None
    fm_notes:        Optional[str] = None
    entry_price_low:  Optional[float] = None
    entry_price_high: Optional[float] = None
    stop_loss:        Optional[float] = None
    target_price:     Optional[float] = None


@app.put("/api/alerts/{alert_id}/action")
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


# ─── Market Indices ────────────────────────────────────

@app.get("/api/market/indices")
async def market_indices():
    from price_service import get_live_price
    indices = ["NIFTY", "SENSEX", "BANKNIFTY", "NIFTYIT", "NIFTYPHARMA", "NIFTYFMCG"]
    results = {}
    for idx in indices:
        try:
            data = get_live_price(idx)
            results[idx] = data
        except Exception:
            results[idx] = {"current_price": None}
    return results


# ─── Index EOD Storage ────────────────────────────────

def _upsert_price_row(db, idx_name, row):
    """Upsert a single IndexPrice row."""
    if not row.get("close"):
        return False
    existing = db.query(IndexPrice).filter_by(
        date=row["date"], index_name=idx_name
    ).first()
    if existing:
        existing.close_price = row["close"]
        existing.open_price  = row.get("open")
        existing.high_price  = row.get("high")
        existing.low_price   = row.get("low")
        existing.volume      = row.get("volume")
        existing.fetched_at  = datetime.now()
    else:
        db.add(IndexPrice(
            date=row["date"], index_name=idx_name,
            close_price=row["close"], open_price=row.get("open"),
            high_price=row.get("high"), low_price=row.get("low"),
            volume=row.get("volume"),
        ))
    return True


@app.post("/api/indices/fetch-eod")
async def fetch_eod(db: Session = Depends(get_db)):
    """Fetch EOD data for all NSE indices and store in DB."""
    from price_service import fetch_all_index_eod

    data = fetch_all_index_eod(period="5d")
    stored = 0
    for idx_name, rows in data.items():
        for row in rows:
            if _upsert_price_row(db, idx_name, row):
                stored += 1
    db.commit()
    return {"success": True, "stored": stored, "indices": len(data)}


@app.post("/api/indices/fetch-historical")
async def fetch_historical(db: Session = Depends(get_db)):
    """Fetch 1Y historical data from NSE API for all indices + today's live from nsetools."""
    from price_service import fetch_historical_indices_nse_sync, fetch_live_indices

    # 1. Fetch 1Y history from NSE historical API
    hist_data = fetch_historical_indices_nse_sync(period="1y")
    stored = 0
    for idx_name, rows in hist_data.items():
        for row in rows:
            if _upsert_price_row(db, idx_name, row):
                stored += 1

    # 2. Store today's live data from nsetools for ALL 135+ indices
    today_str = datetime.now().strftime("%Y-%m-%d")
    live = fetch_live_indices()
    live_stored = 0
    for item in live:
        close = item.get("last")
        if not close:
            continue
        row = {
            "date": today_str, "close": close,
            "open": item.get("open"), "high": item.get("high"),
            "low": item.get("low"), "volume": None,
        }
        if _upsert_price_row(db, item["index_name"], row):
            live_stored += 1

    db.commit()
    logger.info("Historical fetch: %d historical records + %d live records", stored, live_stored)
    return {"success": True, "stored_historical": stored, "stored_live": live_stored, "indices": len(hist_data)}


@app.post("/api/indices/bulk-upload")
async def bulk_upload_indices(request: Request, db: Session = Depends(get_db)):
    """Accept bulk historical index data (from local backfill script running on India IP)."""
    body = await request.json()
    data = body.get("data", {})
    if not data:
        return {"success": False, "error": "No data provided"}

    stored = 0
    indices_count = 0
    for idx_name, rows in data.items():
        if not rows:
            continue
        indices_count += 1
        for row in rows:
            if _upsert_price_row(db, idx_name, row):
                stored += 1

    db.commit()
    logger.info("Bulk upload: %d records across %d indices", stored, indices_count)
    return {"success": True, "stored": stored, "indices": indices_count}


@app.post("/api/stocks/fetch-history")
async def fetch_stock_history_endpoint(db: Session = Depends(get_db)):
    """Fetch 12M history for all stocks in the alert database."""
    from price_service import fetch_stock_history

    tickers = [
        r[0] for r in db.query(TradingViewAlert.ticker)
        .filter(TradingViewAlert.status == AlertStatus.APPROVED)
        .distinct().all()
        if r[0] and r[0] != "UNKNOWN"
    ]

    stored = 0
    for ticker in tickers:
        rows = fetch_stock_history(ticker, "1y")
        for row in rows:
            if _upsert_price_row(db, ticker, row):
                stored += 1

    db.commit()
    return {"success": True, "stored": stored, "tickers": len(tickers)}


@app.get("/api/indices/latest")
async def indices_latest(base: str = "NIFTY", db: Session = Depends(get_db)):
    """Return latest index prices with ratio vs base, recommendations, and period returns."""
    from sqlalchemy import func as sqlfunc

    latest_date = db.query(sqlfunc.max(IndexPrice.date)).scalar()
    if not latest_date:
        return {"date": None, "base": base, "indices": [], "message": "No EOD data. Call POST /api/indices/fetch-eod first."}

    base_row = db.query(IndexPrice).filter_by(date=latest_date, index_name=base).first()
    base_close = base_row.close_price if base_row else None

    all_rows = db.query(IndexPrice).filter_by(date=latest_date).order_by(IndexPrice.index_name).all()

    def _get_period_return(idx_name, days):
        """Get return over N calendar days from stored data."""
        from datetime import timedelta as td
        target = (datetime.strptime(latest_date, "%Y-%m-%d") - td(days=days)).strftime("%Y-%m-%d")
        old = (
            db.query(IndexPrice)
            .filter(IndexPrice.index_name == idx_name, IndexPrice.date <= target)
            .order_by(desc(IndexPrice.date))
            .first()
        )
        if not old or not old.close_price:
            return None
        curr = db.query(IndexPrice).filter_by(date=latest_date, index_name=idx_name).first()
        if not curr or not curr.close_price:
            return None
        return round(((curr.close_price - old.close_price) / old.close_price) * 100, 2)

    results = []
    for row in all_rows:
        close = row.close_price
        ratio = round(close / base_close, 4) if (close and base_close and base_close > 0) else None

        if ratio is not None and row.index_name != base:
            if ratio > 1.05:
                signal = "STRONG OW"
            elif ratio > 1.0:
                signal = "OVERWEIGHT"
            elif ratio < 0.95:
                signal = "STRONG UW"
            elif ratio < 1.0:
                signal = "UNDERWEIGHT"
            else:
                signal = "NEUTRAL"
        else:
            signal = "BASE" if row.index_name == base else "NEUTRAL"

        prev_row = (
            db.query(IndexPrice)
            .filter(IndexPrice.index_name == row.index_name, IndexPrice.date < latest_date)
            .order_by(desc(IndexPrice.date))
            .first()
        )
        chg_pct = None
        if prev_row and prev_row.close_price and close:
            chg_pct = round(((close - prev_row.close_price) / prev_row.close_price) * 100, 2)

        periods = {}
        for label, days in [("1d", 1), ("1w", 7), ("1m", 30), ("3m", 90), ("6m", 180), ("12m", 365)]:
            periods[label] = _get_period_return(row.index_name, days)

        results.append({
            "index_name": row.index_name,
            "close": close,
            "change_pct": chg_pct,
            "ratio": ratio,
            "signal": signal,
            **periods,
        })

    return {"date": latest_date, "base": base, "indices": results}


# ─── Live NSE Indices (via nsetools) ─────────────────

@app.get("/api/indices/live")
async def indices_live(base: str = "NIFTY", db: Session = Depends(get_db)):
    """Return real-time live index data from NSE with ratio-based period returns."""
    from price_service import fetch_live_indices
    from datetime import timedelta
    from sqlalchemy import func as sqlfunc

    try:
        data = fetch_live_indices()
        if not data:
            return {"success": False, "indices": [], "error": "No data from NSE"}

        # Find base index
        base_close = None
        base_item = {}
        for item in data:
            if item["index_name"] == base:
                base_close = item.get("last")
                base_item = item
                break

        # Pre-load historical prices for ratio return computation (optimized: 7 queries total)
        period_map = {"1d": 1, "1w": 7, "1m": 30, "3m": 90, "6m": 180, "12m": 365}
        # Max allowed gap between target date and closest DB date
        max_gap = {"1d": 5, "1w": 10, "1m": 15, "3m": 45, "6m": 45, "12m": 45}
        historical_dates = {}
        for pk, days in period_map.items():
            target = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            closest = db.query(sqlfunc.max(IndexPrice.date)).filter(IndexPrice.date <= target).scalar()
            if closest:
                # Only use if within acceptable range of target
                gap = (datetime.strptime(target, "%Y-%m-%d") - datetime.strptime(closest, "%Y-%m-%d")).days
                if gap <= max_gap.get(pk, 30):
                    historical_dates[pk] = closest

        # Load all prices at those dates in one query
        unique_dates = list(set(historical_dates.values()))
        date_price_map = {}
        if unique_dates:
            all_rows = db.query(IndexPrice).filter(IndexPrice.date.in_(unique_dates)).all()
            for r in all_rows:
                if r.date not in date_price_map:
                    date_price_map[r.date] = {}
                if r.close_price:
                    date_price_map[r.date][r.index_name] = r.close_price

        historical_prices = {}
        for pk, d in historical_dates.items():
            historical_prices[pk] = date_price_map.get(d, {})

        # nsetools fallback field map for ratio computation
        nse_ref_fields = {
            "1d": "previousClose",
            "1w": "oneWeekAgoVal",
            "1m": "oneMonthAgoVal",
            "12m": "oneYearAgoVal",
        }

        # Enrich each item
        for item in data:
            close = item.get("last")
            idx_name = item["index_name"]

            # Ratio and signal
            if close and base_close and base_close > 0 and idx_name != base:
                ratio = round(close / base_close, 4)
                item["ratio"] = ratio
                if ratio > 1.05:
                    item["signal"] = "STRONG OW"
                elif ratio > 1.0:
                    item["signal"] = "OVERWEIGHT"
                elif ratio < 0.95:
                    item["signal"] = "STRONG UW"
                elif ratio < 1.0:
                    item["signal"] = "UNDERWEIGHT"
                else:
                    item["signal"] = "NEUTRAL"
            elif idx_name == base:
                item["ratio"] = 1.0
                item["signal"] = "BASE"
            else:
                item["ratio"] = None
                item["signal"] = "NEUTRAL"

            # Ratio-based period returns
            ratio_returns = {}
            ratio_today = (close / base_close) if (close and base_close and base_close > 0) else None

            if idx_name == base:
                for pk in period_map:
                    ratio_returns[pk] = 0.0
            elif ratio_today:
                for pk in period_map:
                    # Try DB historical data first
                    old_prices = historical_prices.get(pk, {})
                    old_idx = old_prices.get(idx_name)
                    old_base = old_prices.get(base)

                    if old_idx and old_base and old_base > 0:
                        ratio_old = old_idx / old_base
                        if ratio_old > 0:
                            ratio_returns[pk] = round(((ratio_today / ratio_old) - 1) * 100, 2)
                    else:
                        # Fallback: use nsetools reference values
                        ref_key = nse_ref_fields.get(pk)
                        if ref_key:
                            old_idx_val = item.get(ref_key)
                            old_base_val = base_item.get(ref_key)
                            if old_idx_val and old_base_val and old_base_val > 0:
                                ratio_old = old_idx_val / old_base_val
                                if ratio_old > 0:
                                    ratio_returns[pk] = round(((ratio_today / ratio_old) - 1) * 100, 2)

            item["ratio_returns"] = ratio_returns

            # Index's own period returns (not ratio-based)
            index_returns = {}
            pct_chg = item.get("percentChange")
            if pct_chg is not None:
                try:
                    index_returns["1d"] = round(float(pct_chg), 2)
                except (ValueError, TypeError):
                    pass
            # Compute from historical data for all periods
            if close:
                for pk in period_map:
                    old_prices = historical_prices.get(pk, {})
                    old_idx = old_prices.get(idx_name)
                    if old_idx and old_idx > 0:
                        index_returns[pk] = round(((close / old_idx) - 1) * 100, 2)
                    elif pk not in index_returns:
                        # Fallback: use nsetools reference values
                        ref_key = nse_ref_fields.get(pk)
                        if ref_key:
                            old_val = item.get(ref_key)
                            if old_val and old_val > 0:
                                index_returns[pk] = round(((close / old_val) - 1) * 100, 2)
            item["index_returns"] = index_returns

        return {
            "success": True, "count": len(data), "base": base,
            "indices": data, "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("Live indices fetch error: %s", e)
        return {"success": False, "indices": [], "error": str(e)}


# ─── Performance ──────────────────────────────────────

@app.get("/api/performance")
async def performance(db: Session = Depends(get_db)):
    from price_service import get_live_price, compute_returns

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

        # For ratio trades, compute ratio-based returns
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

        ret = compute_returns(entry_price, curr_price, direction) if entry_price and curr_price else {}

        days_since = None
        if a.received_at:
            days_since = (datetime.now() - a.received_at).days

        results.append({
            **_serialize(a),
            "trigger_price": entry_price,
            "entry_price": entry_price,
            "current_price": curr_price,
            "return_pct": ret.get("return_pct"),
            "return_abs": ret.get("return_absolute"),
            "days_since": days_since,
            "is_ratio_trade": is_ratio,
            "ratio_data": ratio_data,
        })
    return {"performance": results}


@app.get("/api/actionables")
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
        # Only consider alerts with at least one of SL/TP set
        if sl is None and tp is None:
            continue

        # Determine entry price: midpoint of range, or price_at_alert
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

        # Fetch current live price
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

        # Check if SL or TP has been hit
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

        # Calculate P&L
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
            "stop_loss": sl,
            "target_price": tp,
            "pnl_pct": pnl_pct,
            "pnl_abs": pnl_abs,
            "days_since": days_since,
            "is_ratio_trade": is_ratio,
        })
    return {"actionables": results}


# ─── APScheduler: Daily EOD Fetch ─────────────────────

def _scheduled_eod_fetch():
    """Background job: store ALL nsetools indices + alerted stock data daily."""
    from price_service import fetch_live_indices, fetch_stock_history
    from models import SessionLocal as SchedSession

    logger.info("Scheduled EOD fetch starting...")
    db = SchedSession()
    try:
        today_str = datetime.now().strftime("%Y-%m-%d")

        # 1. Store ALL live nsetools indices (135+)
        live = fetch_live_indices()
        idx_stored = 0
        for item in live:
            close = item.get("last")
            if not close:
                continue
            existing = db.query(IndexPrice).filter_by(
                date=today_str, index_name=item["index_name"]
            ).first()
            if existing:
                existing.close_price = close
                existing.open_price  = item.get("open")
                existing.high_price  = item.get("high")
                existing.low_price   = item.get("low")
                existing.fetched_at  = datetime.now()
            else:
                db.add(IndexPrice(
                    date=today_str, index_name=item["index_name"],
                    close_price=close, open_price=item.get("open"),
                    high_price=item.get("high"), low_price=item.get("low"),
                ))
            idx_stored += 1

        # 2. Fetch recent data for all alerted stocks
        tickers = [
            r[0] for r in db.query(TradingViewAlert.ticker)
            .filter(TradingViewAlert.status == AlertStatus.APPROVED)
            .distinct().all()
            if r[0] and r[0] != "UNKNOWN"
        ]
        stk_stored = 0
        for ticker in tickers:
            rows = fetch_stock_history(ticker, "5d")
            for row in rows:
                if not row.get("close"):
                    continue
                existing = db.query(IndexPrice).filter_by(
                    date=row["date"], index_name=ticker
                ).first()
                if not existing:
                    db.add(IndexPrice(
                        date=row["date"], index_name=ticker,
                        close_price=row["close"], open_price=row.get("open"),
                        high_price=row.get("high"), low_price=row.get("low"),
                        volume=row.get("volume"),
                    ))
                    stk_stored += 1

        db.commit()
        logger.info("Scheduled EOD: %d index records, %d stock records", idx_stored, stk_stored)
    except Exception as e:
        logger.error("Scheduled EOD fetch failed: %s", e)
        db.rollback()
    finally:
        db.close()


@app.on_event("startup")
async def start_scheduler():
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        import pytz

        scheduler = BackgroundScheduler()
        ist = pytz.timezone("Asia/Kolkata")
        scheduler.add_job(
            _scheduled_eod_fetch,
            CronTrigger(hour=15, minute=30, timezone=ist),
            id="daily_eod_fetch",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("APScheduler started — daily EOD fetch at 3:30 PM IST")
    except Exception as e:
        logger.warning("APScheduler not available: %s (install apscheduler)", e)


# ═══════════════════════════════════════════════════════════
#  MODEL PORTFOLIO ROUTES (integrated from portfolio_server.py)
# ═══════════════════════════════════════════════════════════

# ─── Live Prices via curl + Yahoo Finance ────────────

YAHOO_SYMBOL_MAP: Dict[str, Optional[str]] = {
    "LIQUIDCASE": "LIQUIDBEES.NS",
    "CPSEETF": "CPSEETF.NS",
    "METALETF": "METALIETF.NS",
    "SENSEXETF": "SENSEXETF.NS",
    "MASPTOP50": "MASPTOP50.NS",
    "NETFMID150": "NETFMID150.NS",
    "GROWWDEFNC": None,
    "FMCGIETF": "FMCGIETF.NS",
    "OIL ETF": "OILIETF.NS",
    "NIPPONAMC - NETFAUTO": "NETFAUTO.NS",
}


def _get_yahoo_symbol(ticker: str) -> Optional[str]:
    if ticker in YAHOO_SYMBOL_MAP:
        return YAHOO_SYMBOL_MAP[ticker]
    return f"{ticker}.NS"


def _fetch_live_price_curl(yf_symbol: str) -> Optional[Dict]:
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_symbol}"
        f"?interval=1d&range=2d"
    )
    try:
        result = subprocess.run(
            ["curl", "-s", url, "-H", "User-Agent: Mozilla/5.0"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
        current_price = meta.get("regularMarketPrice")
        prev_close = meta.get("previousClose") or meta.get("chartPreviousClose")
        if not current_price:
            return None
        change_pct = None
        if prev_close and prev_close > 0:
            change_pct = round(((current_price / prev_close) - 1) * 100, 2)
        return {"current_price": current_price, "change_pct": change_pct}
    except Exception as exc:
        logger.debug("curl price fetch failed for %s: %s", yf_symbol, exc)
        return None


def _portfolio_get_live_prices(tickers: List[str]) -> Dict[str, Dict]:
    prices: Dict[str, Dict] = {}
    for ticker in tickers:
        yf_sym = _get_yahoo_symbol(ticker)
        if not yf_sym:
            continue
        data = _fetch_live_price_curl(yf_sym)
        if data:
            prices[ticker] = data
    return prices


# ─── Portfolio Pydantic Models ────────────────────────

class CreatePortfolioRequest(BaseModel):
    name: str
    description: Optional[str] = None
    benchmark: Optional[str] = "NIFTY"

class UpdatePortfolioRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    benchmark: Optional[str] = None

class CreateTransactionRequest(BaseModel):
    ticker: str
    txn_type: str
    quantity: int
    price: float
    txn_date: str
    notes: Optional[str] = None
    exchange: Optional[str] = "NSE"
    sector: Optional[str] = None


# ─── Portfolio CRUD ───────────────────────────────────

@app.post("/api/portfolios")
async def create_portfolio(req: CreatePortfolioRequest, db: Session = Depends(get_db)):
    portfolio = ModelPortfolio(
        name=req.name, description=req.description, benchmark=req.benchmark or "NIFTY",
    )
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return {"success": True, "id": portfolio.id, "name": portfolio.name}


@app.get("/api/portfolios")
async def list_portfolios(db: Session = Depends(get_db)):
    portfolios = (
        db.query(ModelPortfolio)
        .filter(ModelPortfolio.status == PortfolioStatus.ACTIVE)
        .order_by(desc(ModelPortfolio.updated_at))
        .all()
    )
    results = []
    for p in portfolios:
        holdings = (
            db.query(PortfolioHolding)
            .filter(PortfolioHolding.portfolio_id == p.id, PortfolioHolding.quantity > 0)
            .all()
        )
        total_invested = sum(h.total_cost for h in holdings)
        current_value = total_invested
        tickers = [h.ticker for h in holdings if h.ticker]
        if tickers:
            prices = _portfolio_get_live_prices(tickers)
            if prices:
                current_value = 0.0
                for h in holdings:
                    cp = prices.get(h.ticker, {}).get("current_price")
                    current_value += (h.quantity * cp) if cp else h.total_cost

        realized = (
            db.query(sa_func.sum(PortfolioTransaction.realized_pnl))
            .filter(
                PortfolioTransaction.portfolio_id == p.id,
                PortfolioTransaction.txn_type == TransactionType.SELL,
            )
            .scalar()
        ) or 0.0

        total_return = (current_value - total_invested) + realized
        total_return_pct = (total_return / total_invested * 100) if total_invested > 0 else 0.0

        results.append({
            "id": p.id, "name": p.name, "description": p.description,
            "benchmark": p.benchmark,
            "status": p.status.value if p.status else "ACTIVE",
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "num_holdings": len([h for h in holdings if h.quantity > 0]),
            "total_invested": round(total_invested, 2),
            "current_value": round(current_value, 2),
            "realized_pnl": round(realized, 2),
            "total_return_pct": round(total_return_pct, 2),
        })
    return {"success": True, "portfolios": results}


@app.get("/api/portfolios/{portfolio_id}")
async def get_portfolio(portfolio_id: int, db: Session = Depends(get_db)):
    p = db.query(ModelPortfolio).filter(ModelPortfolio.id == portfolio_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return {
        "id": p.id, "name": p.name, "description": p.description,
        "benchmark": p.benchmark,
        "status": p.status.value if p.status else "ACTIVE",
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


@app.put("/api/portfolios/{portfolio_id}")
async def update_portfolio(
    portfolio_id: int, req: UpdatePortfolioRequest, db: Session = Depends(get_db)
):
    p = db.query(ModelPortfolio).filter(ModelPortfolio.id == portfolio_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if req.name is not None: p.name = req.name
    if req.description is not None: p.description = req.description
    if req.benchmark is not None: p.benchmark = req.benchmark
    db.commit()
    return {"success": True, "id": p.id}


@app.delete("/api/portfolios/{portfolio_id}")
async def archive_portfolio(portfolio_id: int, db: Session = Depends(get_db)):
    p = db.query(ModelPortfolio).filter(ModelPortfolio.id == portfolio_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    p.status = PortfolioStatus.ARCHIVED
    db.commit()
    return {"success": True, "id": p.id, "status": "ARCHIVED"}


# ─── Portfolio Transactions ──────────────────────────

@app.post("/api/portfolios/{portfolio_id}/transactions")
async def create_transaction(
    portfolio_id: int, req: CreateTransactionRequest, db: Session = Depends(get_db)
):
    portfolio = db.query(ModelPortfolio).filter(ModelPortfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if req.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")
    if req.price <= 0:
        raise HTTPException(status_code=400, detail="Price must be positive")

    ticker = req.ticker.upper().strip()
    txn_type_str = req.txn_type.upper().strip()
    if txn_type_str not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="txn_type must be BUY or SELL")

    txn_type = TransactionType.BUY if txn_type_str == "BUY" else TransactionType.SELL
    total_value = req.quantity * req.price

    holding = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.portfolio_id == portfolio_id, PortfolioHolding.ticker == ticker)
        .first()
    )

    realized_pnl = None
    realized_pnl_pct = None
    cost_basis_at_sell = None

    if txn_type == TransactionType.BUY:
        if holding:
            new_qty = holding.quantity + req.quantity
            new_total_cost = holding.total_cost + total_value
            holding.quantity = new_qty
            holding.total_cost = new_total_cost
            holding.avg_cost = new_total_cost / new_qty if new_qty > 0 else 0.0
            if req.sector: holding.sector = req.sector
        else:
            holding = PortfolioHolding(
                portfolio_id=portfolio_id, ticker=ticker,
                exchange=req.exchange or "NSE", quantity=req.quantity,
                avg_cost=req.price, total_cost=total_value, sector=req.sector,
            )
            db.add(holding)
        _background_fetch_stock_history(ticker)

    elif txn_type == TransactionType.SELL:
        if not holding or holding.quantity <= 0:
            raise HTTPException(status_code=400, detail=f"No holding for {ticker} to sell")
        if req.quantity > holding.quantity:
            raise HTTPException(status_code=400, detail=f"Cannot sell {req.quantity}, only {holding.quantity} held")
        cost_basis_at_sell = holding.avg_cost
        realized_pnl = (req.price - holding.avg_cost) * req.quantity
        realized_pnl_pct = ((req.price / holding.avg_cost) - 1) * 100 if holding.avg_cost > 0 else 0.0
        new_qty = holding.quantity - req.quantity
        if new_qty == 0:
            db.delete(holding)
        else:
            holding.quantity = new_qty
            holding.total_cost = new_qty * holding.avg_cost

    txn = PortfolioTransaction(
        portfolio_id=portfolio_id, ticker=ticker, exchange=req.exchange or "NSE",
        txn_type=txn_type, quantity=req.quantity, price=req.price,
        total_value=total_value, txn_date=req.txn_date, notes=req.notes,
        realized_pnl=realized_pnl,
        realized_pnl_pct=round(realized_pnl_pct, 2) if realized_pnl_pct is not None else None,
        cost_basis_at_sell=cost_basis_at_sell,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    result = {"success": True, "transaction_id": txn.id, "txn_type": txn_type_str,
              "ticker": ticker, "quantity": req.quantity, "price": req.price, "total_value": total_value}
    if realized_pnl is not None:
        result["realized_pnl"] = round(realized_pnl, 2)
        result["realized_pnl_pct"] = round(realized_pnl_pct, 2)
    return result


@app.get("/api/portfolios/{portfolio_id}/transactions")
async def list_transactions(
    portfolio_id: int, txn_type: Optional[str] = None, limit: int = 200, db: Session = Depends(get_db),
):
    query = db.query(PortfolioTransaction).filter(PortfolioTransaction.portfolio_id == portfolio_id)
    if txn_type and txn_type.upper() in ("BUY", "SELL"):
        query = query.filter(PortfolioTransaction.txn_type == TransactionType(txn_type.upper()))
    txns = query.order_by(desc(PortfolioTransaction.txn_date)).limit(limit).all()
    return {
        "success": True,
        "transactions": [{
            "id": t.id, "ticker": t.ticker, "exchange": t.exchange,
            "txn_type": t.txn_type.value if t.txn_type else None,
            "quantity": t.quantity, "price": t.price, "total_value": t.total_value,
            "txn_date": t.txn_date, "notes": t.notes,
            "realized_pnl": t.realized_pnl, "realized_pnl_pct": t.realized_pnl_pct,
            "cost_basis_at_sell": t.cost_basis_at_sell,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        } for t in txns],
    }


# ─── Portfolio Holdings (with Live Prices) ───────────

def _portfolio_empty_totals():
    return {"total_invested": 0.0, "current_value": 0.0, "unrealized_pnl": 0.0,
            "unrealized_pnl_pct": 0.0, "realized_pnl": 0.0, "num_holdings": 0}


@app.get("/api/portfolios/{portfolio_id}/holdings")
async def list_holdings(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = db.query(ModelPortfolio).filter(ModelPortfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    holdings = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.portfolio_id == portfolio_id, PortfolioHolding.quantity > 0)
        .order_by(desc(PortfolioHolding.total_cost))
        .all()
    )
    if not holdings:
        return {"success": True, "holdings": [], "totals": _portfolio_empty_totals()}

    tickers = [h.ticker for h in holdings]
    prices = _portfolio_get_live_prices(tickers)

    total_invested = 0.0
    total_current = 0.0
    rows = []
    for h in holdings:
        price_data = prices.get(h.ticker, {})
        current_price = price_data.get("current_price")
        day_change_pct = price_data.get("change_pct")
        current_value = (h.quantity * current_price) if current_price else None
        unrealized_pnl = (current_value - h.total_cost) if current_value else None
        unrealized_pnl_pct = (((current_price / h.avg_cost) - 1) * 100) if current_price and h.avg_cost > 0 else None
        total_invested += h.total_cost
        total_current += current_value if current_value else h.total_cost
        rows.append({
            "id": h.id, "ticker": h.ticker, "exchange": h.exchange, "sector": h.sector,
            "quantity": h.quantity, "avg_cost": round(h.avg_cost, 2), "total_cost": round(h.total_cost, 2),
            "current_price": round(current_price, 2) if current_price else None,
            "current_value": round(current_value, 2) if current_value else None,
            "unrealized_pnl": round(unrealized_pnl, 2) if unrealized_pnl is not None else None,
            "unrealized_pnl_pct": round(unrealized_pnl_pct, 2) if unrealized_pnl_pct is not None else None,
            "day_change_pct": round(day_change_pct, 2) if day_change_pct is not None else None,
            "weight_pct": None,
        })
    for row in rows:
        cv = row["current_value"] or row["total_cost"]
        row["weight_pct"] = round((cv / total_current) * 100, 2) if total_current > 0 else 0.0

    realized_total = (
        db.query(sa_func.sum(PortfolioTransaction.realized_pnl))
        .filter(PortfolioTransaction.portfolio_id == portfolio_id, PortfolioTransaction.txn_type == TransactionType.SELL)
        .scalar()
    ) or 0.0

    totals = {
        "total_invested": round(total_invested, 2), "current_value": round(total_current, 2),
        "unrealized_pnl": round(total_current - total_invested, 2),
        "unrealized_pnl_pct": round(((total_current - total_invested) / total_invested) * 100, 2) if total_invested > 0 else 0.0,
        "realized_pnl": round(realized_total, 2), "num_holdings": len(rows),
    }
    return {"success": True, "holdings": rows, "totals": totals}


# ─── Portfolio NAV Computation ───────────────────────

def _compute_nav_for_portfolio(portfolio_id: int, date_str: str, db: Session):
    holdings = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.portfolio_id == portfolio_id, PortfolioHolding.quantity > 0)
        .all()
    )
    if not holdings:
        return None
    total_value = 0.0
    total_cost = 0.0
    for h in holdings:
        price_row = (
            db.query(IndexPrice)
            .filter(IndexPrice.index_name == h.ticker, IndexPrice.date <= date_str)
            .order_by(desc(IndexPrice.date))
            .first()
        )
        close = price_row.close_price if price_row and price_row.close_price else h.avg_cost
        total_value += h.quantity * close
        total_cost += h.quantity * h.avg_cost

    realized_sum = (
        db.query(sa_func.sum(PortfolioTransaction.realized_pnl))
        .filter(
            PortfolioTransaction.portfolio_id == portfolio_id,
            PortfolioTransaction.txn_type == TransactionType.SELL,
            PortfolioTransaction.txn_date <= date_str,
        )
        .scalar()
    ) or 0.0

    nav = (
        db.query(PortfolioNAV)
        .filter(PortfolioNAV.portfolio_id == portfolio_id, PortfolioNAV.date == date_str)
        .first()
    )
    if not nav:
        nav = PortfolioNAV(portfolio_id=portfolio_id, date=date_str)
        db.add(nav)
    nav.total_value = round(total_value, 2)
    nav.total_cost = round(total_cost, 2)
    nav.unrealized_pnl = round(total_value - total_cost, 2)
    nav.realized_pnl_cumulative = round(realized_sum, 2)
    nav.num_holdings = len([h for h in holdings if h.quantity > 0])
    nav.computed_at = datetime.now()
    db.commit()
    return nav


@app.post("/api/portfolios/{portfolio_id}/compute-nav")
async def compute_nav(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = db.query(ModelPortfolio).filter(ModelPortfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    today_str = date_type.today().strftime("%Y-%m-%d")
    nav = _compute_nav_for_portfolio(portfolio_id, today_str, db)
    if nav:
        return {"success": True, "date": today_str, "total_value": nav.total_value,
                "total_cost": nav.total_cost, "unrealized_pnl": nav.unrealized_pnl}
    return {"success": True, "message": "No holdings to compute NAV for"}


@app.post("/api/portfolios/compute-nav")
async def compute_nav_all(db: Session = Depends(get_db)):
    portfolios = db.query(ModelPortfolio).filter(ModelPortfolio.status == PortfolioStatus.ACTIVE).all()
    today_str = date_type.today().strftime("%Y-%m-%d")
    computed = 0
    for p in portfolios:
        nav = _compute_nav_for_portfolio(p.id, today_str, db)
        if nav:
            computed += 1
    return {"success": True, "computed": computed, "date": today_str}


# ─── Portfolio NAV History (for Charts) ──────────────

_PERIOD_DAYS = {"1m": 30, "3m": 90, "6m": 180, "1y": 365, "ytd": None, "all": None}

@app.get("/api/portfolios/{portfolio_id}/nav-history")
async def get_nav_history(portfolio_id: int, period: str = "all", db: Session = Depends(get_db)):
    portfolio = db.query(ModelPortfolio).filter(ModelPortfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    query = db.query(PortfolioNAV).filter(PortfolioNAV.portfolio_id == portfolio_id)
    pk = period.lower()
    if pk == "ytd":
        query = query.filter(PortfolioNAV.date >= f"{date_type.today().year}-01-01")
    elif pk in _PERIOD_DAYS and _PERIOD_DAYS[pk] is not None:
        cutoff = (date_type.today() - timedelta(days=_PERIOD_DAYS[pk])).strftime("%Y-%m-%d")
        query = query.filter(PortfolioNAV.date >= cutoff)

    nav_rows = query.order_by(PortfolioNAV.date).all()

    benchmark_data = {}
    if nav_rows and portfolio.benchmark:
        dates = [n.date for n in nav_rows]
        if dates:
            bench_rows = (
                db.query(IndexPrice)
                .filter(IndexPrice.index_name == portfolio.benchmark, IndexPrice.date >= dates[0], IndexPrice.date <= dates[-1])
                .order_by(IndexPrice.date).all()
            )
            for br in bench_rows:
                benchmark_data[br.date] = br.close_price

    first_value = nav_rows[0].total_value if nav_rows else 1.0
    first_bench = None
    for n in nav_rows:
        bv = benchmark_data.get(n.date)
        if bv and first_bench is None:
            first_bench = bv
        break

    result = []
    for n in nav_rows:
        bv_raw = benchmark_data.get(n.date)
        benchmark_normalized = None
        if bv_raw and first_bench and first_bench > 0:
            benchmark_normalized = round((bv_raw / first_bench) * first_value, 2)
        result.append({
            "date": n.date, "total_value": n.total_value, "total_cost": n.total_cost,
            "unrealized_pnl": n.unrealized_pnl, "benchmark_value": benchmark_normalized,
        })
    return {"success": True, "nav_history": result, "period": period}


# ─── Portfolio Performance Metrics ───────────────────

def _compute_xirr(cashflows):
    if not cashflows or len(cashflows) < 2:
        return None
    t0 = cashflows[0][0]
    days = [(d - t0).days / 365.0 for d, _ in cashflows]
    amounts = [a for _, a in cashflows]
    rate = 0.1
    for _ in range(100):
        npv = sum(a / (1 + rate) ** t for a, t in zip(amounts, days))
        dnpv = sum(-t * a / (1 + rate) ** (t + 1) for a, t in zip(amounts, days))
        if abs(dnpv) < 1e-12:
            break
        new_rate = rate - npv / dnpv
        if abs(new_rate - rate) < 1e-8:
            return round(new_rate * 100, 2)
        rate = new_rate
        if rate < -0.99 or rate > 100:
            return None
    return round(rate * 100, 2)


def _compute_max_drawdown(values):
    if len(values) < 2:
        return None
    peak = values[0]
    max_dd = 0.0
    for val in values:
        if val > peak:
            peak = val
        dd = (val - peak) / peak if peak > 0 else 0
        if dd < max_dd:
            max_dd = dd
    return round(max_dd * 100, 2)


@app.get("/api/portfolios/{portfolio_id}/performance")
async def get_performance(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = db.query(ModelPortfolio).filter(ModelPortfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    holdings = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.portfolio_id == portfolio_id, PortfolioHolding.quantity > 0)
        .all()
    )
    total_invested = sum(h.total_cost for h in holdings)
    current_value = total_invested
    tickers = [h.ticker for h in holdings if h.ticker]
    if tickers:
        prices = _portfolio_get_live_prices(tickers)
        if prices:
            current_value = 0.0
            for h in holdings:
                cp = prices.get(h.ticker, {}).get("current_price")
                current_value += (h.quantity * cp) if cp else h.total_cost

    realized_pnl = (
        db.query(sa_func.sum(PortfolioTransaction.realized_pnl))
        .filter(PortfolioTransaction.portfolio_id == portfolio_id, PortfolioTransaction.txn_type == TransactionType.SELL)
        .scalar()
    ) or 0.0

    unrealized_pnl = current_value - total_invested
    total_return = unrealized_pnl + realized_pnl
    total_return_pct = (total_return / total_invested * 100) if total_invested > 0 else 0.0

    txns = (
        db.query(PortfolioTransaction).filter(PortfolioTransaction.portfolio_id == portfolio_id)
        .order_by(PortfolioTransaction.txn_date).all()
    )
    cashflows = []
    for t in txns:
        try:
            d = datetime.strptime(t.txn_date, "%Y-%m-%d").date()
        except ValueError:
            continue
        if t.txn_type == TransactionType.BUY:
            cashflows.append((d, -t.total_value))
        else:
            cashflows.append((d, t.total_value))
    if current_value > 0 and cashflows:
        cashflows.append((date_type.today(), current_value))
    xirr = _compute_xirr(cashflows)

    cagr = None
    if txns and total_invested > 0:
        try:
            first_date = datetime.strptime(txns[0].txn_date, "%Y-%m-%d").date()
            days_elapsed = (date_type.today() - first_date).days
            if days_elapsed > 0:
                years = days_elapsed / 365.0
                end_value = current_value + realized_pnl
                cagr = round(((end_value / total_invested) ** (1 / years) - 1) * 100, 2)
        except (ValueError, ZeroDivisionError):
            pass

    nav_values = (
        db.query(PortfolioNAV.total_value).filter(PortfolioNAV.portfolio_id == portfolio_id)
        .order_by(PortfolioNAV.date).all()
    )
    max_drawdown = _compute_max_drawdown([v[0] for v in nav_values]) if nav_values else None

    benchmark_return_pct = None
    alpha = None
    if portfolio.benchmark and txns:
        try:
            first_date_str = txns[0].txn_date
            today_str = date_type.today().strftime("%Y-%m-%d")
            bench_start = db.query(IndexPrice).filter(IndexPrice.index_name == portfolio.benchmark, IndexPrice.date >= first_date_str).order_by(IndexPrice.date).first()
            bench_end = db.query(IndexPrice).filter(IndexPrice.index_name == portfolio.benchmark, IndexPrice.date <= today_str).order_by(desc(IndexPrice.date)).first()
            if bench_start and bench_end and bench_start.close_price and bench_start.close_price > 0:
                benchmark_return_pct = round(((bench_end.close_price / bench_start.close_price) - 1) * 100, 2)
                alpha = round(total_return_pct - benchmark_return_pct, 2)
        except Exception:
            pass

    return {
        "success": True,
        "performance": {
            "total_invested": round(total_invested, 2), "current_value": round(current_value, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "unrealized_pnl_pct": round((unrealized_pnl / total_invested * 100), 2) if total_invested > 0 else 0.0,
            "realized_pnl": round(realized_pnl, 2), "total_return": round(total_return, 2),
            "total_return_pct": round(total_return_pct, 2), "xirr": xirr, "cagr": cagr,
            "max_drawdown": max_drawdown, "benchmark_return_pct": benchmark_return_pct, "alpha": alpha,
        },
    }


# ─── Portfolio Allocation ────────────────────────────

@app.get("/api/portfolios/{portfolio_id}/allocation")
async def get_allocation(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = db.query(ModelPortfolio).filter(ModelPortfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    holdings = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.portfolio_id == portfolio_id, PortfolioHolding.quantity > 0)
        .all()
    )
    if not holdings:
        return {"success": True, "by_stock": [], "by_sector": []}

    tickers = [h.ticker for h in holdings]
    prices = _portfolio_get_live_prices(tickers)
    stock_items = []
    sector_map = {}
    total_value = 0.0
    for h in holdings:
        cp = prices.get(h.ticker, {}).get("current_price")
        value = (h.quantity * cp) if cp else h.total_cost
        total_value += value
        stock_items.append({"label": h.ticker, "value": round(value, 2), "sector": h.sector or "Other"})
        sector = h.sector or "Other"
        sector_map[sector] = sector_map.get(sector, 0) + value

    by_stock = [{"label": s["label"], "value": s["value"],
                 "pct": round((s["value"] / total_value) * 100, 2) if total_value > 0 else 0}
                for s in sorted(stock_items, key=lambda x: x["value"], reverse=True)]
    by_sector = [{"label": sector, "value": round(val, 2),
                  "pct": round((val / total_value) * 100, 2) if total_value > 0 else 0}
                 for sector, val in sorted(sector_map.items(), key=lambda x: x[1], reverse=True)]
    return {"success": True, "by_stock": by_stock, "by_sector": by_sector}


# ─── Portfolio CSV Export ────────────────────────────

@app.get("/api/portfolios/{portfolio_id}/export/holdings")
async def export_holdings_csv(portfolio_id: int, db: Session = Depends(get_db)):
    holdings = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.portfolio_id == portfolio_id, PortfolioHolding.quantity > 0)
        .order_by(desc(PortfolioHolding.total_cost)).all()
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Ticker", "Exchange", "Sector", "Quantity", "Avg Cost", "Total Cost"])
    for h in holdings:
        writer.writerow([h.ticker, h.exchange, h.sector or "", h.quantity, h.avg_cost, h.total_cost])
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=holdings_portfolio_{portfolio_id}.csv"})


@app.get("/api/portfolios/{portfolio_id}/export/transactions")
async def export_transactions_csv(portfolio_id: int, db: Session = Depends(get_db)):
    txns = (
        db.query(PortfolioTransaction).filter(PortfolioTransaction.portfolio_id == portfolio_id)
        .order_by(desc(PortfolioTransaction.txn_date)).all()
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Type", "Ticker", "Quantity", "Price", "Total Value", "Realized P&L", "Notes"])
    for t in txns:
        writer.writerow([t.txn_date, t.txn_type.value if t.txn_type else "", t.ticker,
                         t.quantity, t.price, t.total_value, t.realized_pnl or "", t.notes or ""])
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=transactions_portfolio_{portfolio_id}.csv"})


# ─── Portfolio Background Helpers ────────────────────

def _background_fetch_stock_history(ticker: str):
    def _fetch():
        try:
            from price_service import fetch_stock_history
            rows = fetch_stock_history(ticker, "1y")
            if not rows:
                return
            db = SessionLocal()
            stored = 0
            for row in rows:
                if not row.get("close"):
                    continue
                existing = db.query(IndexPrice).filter_by(date=row["date"], index_name=ticker).first()
                if existing:
                    existing.close_price = row["close"]
                    existing.open_price = row.get("open")
                    existing.high_price = row.get("high")
                    existing.low_price = row.get("low")
                    existing.volume = row.get("volume")
                    existing.fetched_at = datetime.now()
                else:
                    db.add(IndexPrice(date=row["date"], index_name=ticker,
                        close_price=row["close"], open_price=row.get("open"),
                        high_price=row.get("high"), low_price=row.get("low"), volume=row.get("volume")))
                stored += 1
            db.commit()
            db.close()
            logger.info("Background stock history: %s — stored %d rows", ticker, stored)
        except Exception as e:
            logger.warning("Background stock history fetch failed for %s: %s", ticker, e)
    thread = threading.Thread(target=_fetch, daemon=True)
    thread.start()


# ─── Server Status ────────────────────────────────────

@app.get("/api/status")
async def server_status():
    return {
        "analysis_enabled": bool(ANTHROPIC_API_KEY),
        "version": "3.0",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.0"}

@app.get("/api")
async def root():
    return {"service": "JHAVERI FIE v3", "status": "running"}

# ─── Static Frontend (Next.js export) ────────────────
_frontend_dir = Path(__file__).parent / "web" / "out"
if _frontend_dir.is_dir():
    # Explicit page routes — Starlette StaticFiles incorrectly resolves
    # /pulse to the pulse/ directory (RSC payloads) instead of pulse.html
    for _page in ("pulse", "approved", "trade", "performance", "portfolios", "actionables"):
        _html = _frontend_dir / f"{_page}.html"
        if _html.is_file():
            def _make_page_handler(path: Path):
                async def _handler():
                    return FileResponse(path, media_type="text/html")
                return _handler
            app.add_api_route(f"/{_page}", _make_page_handler(_html), methods=["GET", "HEAD"])

    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
