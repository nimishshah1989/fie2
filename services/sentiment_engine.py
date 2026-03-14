"""
FIE v3 — Sentiment Computation Engine
Computes 26 breadth indicators across 5 layers for the Nifty 500 universe.
All data sourced from the local IndexPrice DB — no live fetching required.
"""

import logging
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from models import IndexConstituent, IndexPrice
from services.technical import (
    compute_ema,
    compute_ema_series,
    compute_rsi,
    prev_month_range,
    prev_quarter_range,
    prev_year_range,
    resample_to_monthly,
    resample_to_weekly,
)

logger = logging.getLogger("fie_v3.sentiment_engine")

LAYER_WEIGHTS = {
    "short_term": 0.20, "broad_trend": 0.30, "adv_decline": 0.25,
    "momentum": 0.15, "extremes": 0.10,
}


def _layer_score(metrics: list[dict]) -> float:
    """Average of indicator scores in a layer, normalized 0-100."""
    scores = []
    for m in metrics:
        pct, thr = m["pct"], m.get("threshold", 50)
        if m.get("invert"):
            pct, thr = 100 - pct, 100 - thr
        scores.append(min(100.0, max(0.0, (pct / max(thr, 1)) * 60 + max(0, pct - thr) * 2)))
    return round(sum(scores) / len(scores), 1) if scores else 0.0


def _pct(count: int, total: int) -> float:
    return round((count / total) * 100, 1) if total else 0.0


def _m(key: str, label: str, count: int, total: int, **kw) -> dict:
    """Build a single metric dict with count/total/pct."""
    return {"key": key, "label": label, "count": count, "total": total, "pct": _pct(count, total), **kw}


def compute_sentiment(db: Session) -> dict:
    """Compute all 26 breadth metrics for the Nifty 500 universe from DB prices."""
    today = date.today()
    today_str = today.isoformat()

    # Load Nifty 500 constituents (preferred), fallback to sector stocks
    n500 = db.query(IndexConstituent).filter(IndexConstituent.index_name == "NIFTY 500").all()
    if n500:
        constituents, universe_label = n500, "NIFTY 500"
    else:
        seen: set = set()
        constituents = []
        for c in db.query(IndexConstituent).all():
            if c.ticker not in seen:
                seen.add(c.ticker)
                constituents.append(c)
        universe_label = "Sector Universe"
        logger.info("Sentiment: NIFTY 500 not in DB, using %d sector stocks", len(constituents))

    tickers = [c.ticker for c in constituents]
    universe_size = len(tickers)
    if universe_size == 0:
        logger.warning("Sentiment: no constituents found")
        return _empty_result(0, today_str)

    logger.info("Sentiment: computing metrics for %d stocks", universe_size)

    # Load 520 calendar days of OHLCV in one batch query
    cutoff = (today - timedelta(days=520)).isoformat()
    all_price_rows = (
        db.query(IndexPrice.index_name, IndexPrice.date, IndexPrice.close_price,
                 IndexPrice.high_price, IndexPrice.low_price)
        .filter(IndexPrice.index_name.in_(tickers), IndexPrice.date >= cutoff,
                IndexPrice.close_price.isnot(None))
        .order_by(IndexPrice.index_name, IndexPrice.date).all()
    )
    price_map: dict[str, list] = {}
    for row in all_price_rows:
        price_map.setdefault(row.index_name, []).append(row)

    # Calendar period boundaries
    pm_start, pm_end = prev_month_range(today)
    pq_start, pq_end = prev_quarter_range(today)
    py_start, py_end = prev_year_range(today)
    pm_s, pm_e = pm_start.isoformat(), pm_end.isoformat()
    pq_s, pq_e = pq_start.isoformat(), pq_end.isoformat()
    py_s, py_e = py_start.isoformat(), py_end.isoformat()

    # Counters — short-term
    a10 = a21 = a50 = h52h = h52l = macd_bc = rsi_d60 = 0
    # Broad trend
    a200 = a12m = a26m = rsi50 = rsi40 = rsi_w50 = gc = 0
    # Advance-decline
    apmh = apqh = apyh = 0
    # Momentum
    n3mh = rocp = hh_hl = 0
    # Extremes
    rsi_ob = rsi_os = 0
    sc = 0

    for ticker in tickers:
        rows = price_map.get(ticker, [])
        if len(rows) < 22:
            continue
        sc += 1
        closes = [r.close_price for r in rows]
        dates = [r.date for r in rows]
        lc = closes[-1]

        # SHORT TERM
        ema10 = compute_ema(closes, 10)
        if ema10 is not None and lc > ema10:
            a10 += 1
        ema21 = compute_ema(closes, 21)
        if ema21 is not None and lc > ema21:
            a21 += 1
        ema50 = compute_ema(closes, 50)
        if ema50 is not None and lc > ema50:
            a50 += 1

        # 52-week high/low
        c52 = (today - timedelta(days=365)).isoformat()
        rr = [(d, r.high_price or r.close_price, r.low_price or r.close_price)
              for d, r in zip(dates, rows) if d >= c52]
        if rr:
            highs = [h for _, h, _ in rr if h]
            lows = [lo for _, _, lo in rr if lo]
            if highs and (rows[-1].high_price or lc) >= max(highs) * 0.999:
                h52h += 1
            if lows and (rows[-1].low_price or lc) <= min(lows) * 1.001:
                h52l += 1

        # MACD bullish cross in last 5 days
        e12s, e26s = compute_ema_series(closes, 12), compute_ema_series(closes, 26)
        if len(e12s) >= 5 and len(e26s) >= 5:
            hist = [(a - b) if (a is not None and b is not None) else None
                    for a, b in zip(e12s, e26s)]
            v = [h for h in hist[-5:] if h is not None]
            if len(v) >= 2 and v[-1] > 0 and any(x < 0 for x in v[:-1]):
                macd_bc += 1

        daily_rsi = compute_rsi(closes, 14)
        if daily_rsi is not None and daily_rsi > 60:
            rsi_d60 += 1

        # BROAD TREND
        ema200 = compute_ema(closes, 200)
        if ema200 is not None and lc > ema200:
            a200 += 1
        dcp = list(zip(dates, closes))
        monthly = resample_to_monthly(dcp)
        mc = [c for _, c in monthly]
        lmc = mc[-1] if mc else None
        if len(mc) >= 13 and lmc:
            e12m = compute_ema(mc, 12)
            if e12m is not None and lmc > e12m:
                a12m += 1
        if len(mc) >= 27 and lmc:
            e26m = compute_ema(mc, 26)
            if e26m is not None and lmc > e26m:
                a26m += 1
        if len(mc) >= 15:
            rv = compute_rsi(mc, 14)
            if rv is not None:
                if rv > 50:
                    rsi50 += 1
                if rv > 40:
                    rsi40 += 1
        wc = [c for _, c in resample_to_weekly(dcp)]
        if len(wc) >= 15:
            wr = compute_rsi(wc, 14)
            if wr is not None and wr > 50:
                rsi_w50 += 1
        if ema50 is not None and ema200 is not None and ema50 > ema200:
            gc += 1

        # ADVANCE/DECLINE
        mr = [r for r in rows if pm_s <= r.date <= pm_e]
        if mr and lc > max((r.high_price or r.close_price) for r in mr):
            apmh += 1
        qr = [r for r in rows if pq_s <= r.date <= pq_e]
        if qr and lc > max((r.high_price or r.close_price) for r in qr):
            apqh += 1
        yr = [r for r in rows if py_s <= r.date <= py_e]
        if yr and lc > max((r.high_price or r.close_price) for r in yr):
            apyh += 1

        # MOMENTUM
        c3m = (today - timedelta(days=90)).isoformat()
        r3h = [(r.high_price or r.close_price) for d, r in zip(dates, rows) if d >= c3m]
        if r3h and (rows[-1].high_price or lc) >= max(r3h) * 0.999:
            n3mh += 1
        if len(closes) >= 21 and closes[-21] > 0:
            if (closes[-1] / closes[-21] - 1) > 0:
                rocp += 1
        if len(rows) >= 10:
            l10h = [r.high_price or r.close_price for r in rows[-10:]]
            l10l = [r.low_price or r.close_price for r in rows[-10:]]
            if (all(l10h[i] >= l10h[i-1] for i in range(1, 10))
                    and all(l10l[i] >= l10l[i-1] for i in range(1, 10))):
                hh_hl += 1

        # EXTREMES
        if daily_rsi is not None and daily_rsi > 70:
            rsi_ob += 1
        if daily_rsi is not None and daily_rsi < 30:
            rsi_os += 1

    # Build result
    hlt = h52h + h52l
    hlp = round((h52h / hlt) * 100, 1) if hlt > 0 else 50.0
    ad = _compute_ad_ratio()

    result = {
        "universe": universe_label, "universe_size": universe_size,
        "stocks_computed": sc, "computed_at": datetime.now().isoformat() + "Z",
        "as_of_date": today_str,
        "short_term_trend": {"label": "Short Term Trend (Daily)", "metrics": [
            _m("above_10ema", "Above 10 EMA (Daily)", a10, sc),
            _m("above_21ema", "Above 21 EMA (Daily)", a21, sc),
            _m("above_50ema", "Above 50 EMA (Daily)", a50, sc),
            _m("hit_52w_high", "Hitting 52-Week High", h52h, sc),
            _m("hit_52w_low", "Hitting 52-Week Low", h52l, sc, invert=True),
            _m("macd_bull_cross", "MACD Bullish Cross (5D)", macd_bc, sc),
            _m("rsi_daily_gt60", "Daily RSI > 60", rsi_d60, sc),
        ]},
        "broad_trend": {"label": "Broad Trend (Monthly)", "metrics": [
            _m("above_200ema", "Above 200 EMA (Daily)", a200, sc),
            _m("above_12ema_monthly", "Above 12 EMA (Monthly)", a12m, sc),
            _m("above_26ema_monthly", "Above 26 EMA (Monthly)", a26m, sc),
            _m("rsi_above_50", "Monthly RSI > 50", rsi50, sc),
            _m("rsi_above_40", "Monthly RSI > 40", rsi40, sc),
            _m("rsi_weekly_gt50", "Weekly RSI > 50", rsi_w50, sc),
            _m("golden_cross", "Golden Cross (50 > 200 EMA)", gc, sc),
        ]},
        "advance_decline": {
            "label": "Advance / Decline",
            "period_note": "Absolute calendar periods (not rolling)",
            "periods": {
                "prev_month": pm_start.strftime("%b %Y"),
                "prev_quarter": f"{pq_start.strftime('%b')}--{pq_end.strftime('%b %Y')}",
                "prev_year": str(py_start.year),
            },
            "metrics": [
                _m("above_prev_month_high", f"Above Previous Month High ({pm_start.strftime('%b %Y')})", apmh, sc),
                _m("above_prev_quarter_high", f"Above Previous Quarter High ({pq_start.strftime('%b')}--{pq_end.strftime('%b %Y')})", apqh, sc),
                _m("above_prev_year_high", f"Above Previous Year High ({py_start.year})", apyh, sc),
                ad,
                {"key": "up_volume_ratio", "label": "Up Volume Ratio", "count": 0, "total": 0, "pct": 0.0, "placeholder": True},
            ],
        },
        "momentum": {"label": "Momentum", "metrics": [
            _m("new_3m_high", "At 3-Month High", n3mh, sc),
            _m("roc_positive", "20-Day ROC > 0", rocp, sc),
            _m("uptrend_hh_hl", "Higher Highs & Lows (10D)", hh_hl, sc),
        ]},
        "extremes": {"label": "Extremes", "metrics": [
            _m("rsi_overbought", "RSI > 70 (Overbought)", rsi_ob, sc),
            _m("rsi_oversold", "RSI < 30 (Oversold)", rsi_os, sc, invert=True),
            {"key": "hl_ratio", "label": "52W High/Low Ratio", "count": h52h, "total": hlt, "pct": hlp},
        ]},
    }

    # Composite Score
    ls = {
        "short_term": _layer_score(result["short_term_trend"]["metrics"]),
        "broad_trend": _layer_score(result["broad_trend"]["metrics"]),
        "adv_decline": _layer_score([m for m in result["advance_decline"]["metrics"] if not m.get("placeholder")]),
        "momentum": _layer_score(result["momentum"]["metrics"]),
        "extremes": _layer_score(result["extremes"]["metrics"]),
    }
    composite = round(sum(ls[k] * LAYER_WEIGHTS[k] for k in LAYER_WEIGHTS), 1)
    zone = next(lbl for thr, lbl in [(30, "Bear"), (45, "Weak"), (55, "Neutral"), (70, "Bullish"), (101, "Strong")] if composite < thr)
    result["composite_score"] = composite
    result["zone"] = zone
    result["layer_scores"] = ls
    return result


def _compute_ad_ratio() -> dict:
    """Get daily advances/declines from nsetools for NIFTY 500."""
    try:
        from price_service import fetch_live_indices
        live = fetch_live_indices()
        q = next((i for i in live if i["index_name"] == "NIFTY500"), None)
        if q:
            adv, dec = q.get("advances") or 0, q.get("declines") or 0
            tot = adv + dec
            return {"key": "ad_ratio", "label": f"Daily A/D Ratio ({adv}:{dec})",
                    "count": adv, "total": tot, "pct": round((adv / tot) * 100, 1) if tot else 50.0}
    except Exception as e:
        logger.debug("A/D ratio fetch failed: %s", e)
    return {"key": "ad_ratio", "label": "Daily A/D Ratio", "count": 0, "total": 0, "pct": 50.0}


def _empty_result(universe_size: int, as_of_date: str) -> dict:
    return {
        "universe": "NIFTY 500", "universe_size": universe_size, "stocks_computed": 0,
        "computed_at": datetime.now().isoformat() + "Z", "as_of_date": as_of_date,
        "short_term_trend": {"label": "Short Term Trend (Daily)", "metrics": []},
        "broad_trend": {"label": "Broad Trend (Monthly)", "metrics": []},
        "advance_decline": {"label": "Advance / Decline", "metrics": []},
        "momentum": {"label": "Momentum", "metrics": []},
        "extremes": {"label": "Extremes", "metrics": []},
        "composite_score": 0.0, "zone": "Neutral",
        "layer_scores": {"short_term": 0, "broad_trend": 0, "adv_decline": 0, "momentum": 0, "extremes": 0},
    }
