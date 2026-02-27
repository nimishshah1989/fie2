"""
FIE v3 — FastAPI Server
Jhaveri Intelligence Platform
"""

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import json, os, logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from models import (
    init_db, get_db,
    TradingViewAlert, AlertAction, AlertStatus, ActionPriority, IndexPrice
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
            "ratio_numerator_ticker":   ac.ratio_numerator_ticker,
            "ratio_denominator_ticker": ac.ratio_denominator_ticker,
            "priority":       ac.priority.value if ac.priority else None,
            "has_chart":      bool(ac.chart_image_b64),
            "chart_analysis": json.loads(ac.chart_analysis) if ac.chart_analysis else None,
            "decision_at":    ac.decision_at.isoformat() if ac.decision_at else None,
            "fm_notes":       ac.fm_notes,
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
    """Fetch 12M historical data for all indices (yfinance) + today's live data (nsetools)."""
    from price_service import fetch_historical_indices, fetch_live_indices

    # 1. Fetch 12M history from yfinance for all mapped indices
    hist_data = fetch_historical_indices(period="1y")
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
    logger.info("Historical fetch: %d yfinance records + %d live nsetools records", stored, live_stored)
    return {"success": True, "stored_historical": stored, "stored_live": live_stored, "indices": len(hist_data)}


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
        max_gap = {"1d": 5, "1w": 10, "1m": 15, "3m": 20, "6m": 25, "12m": 45}
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
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
