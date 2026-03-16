"""
FIE v3 — Mutual Fund SIP Simulator Router
Simulates enhanced SIP strategy based on market breadth signals.
"""

import logging
from datetime import date, timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger("fie_v3.simulator")

router = APIRouter(prefix="/api/simulator", tags=["simulator"])

# ─── Top 25 MF Schemes by AUM (AMFI codes) ───────────────
TOP_FUNDS = [
    {"code": "119598", "name": "SBI Bluechip Fund - Direct Growth", "category": "Large Cap"},
    {"code": "120503", "name": "HDFC Flexi Cap Fund - Direct Growth", "category": "Flexi Cap"},
    {"code": "120505", "name": "HDFC Mid-Cap Opportunities Fund - Direct Growth", "category": "Mid Cap"},
    {"code": "118989", "name": "Parag Parikh Flexi Cap Fund - Direct Growth", "category": "Flexi Cap"},
    {"code": "120586", "name": "ICICI Pru Bluechip Fund - Direct Growth", "category": "Large Cap"},
    {"code": "120587", "name": "ICICI Pru Balanced Advantage Fund - Direct Growth", "category": "BAF"},
    {"code": "125497", "name": "Nippon India Small Cap Fund - Direct Growth", "category": "Small Cap"},
    {"code": "120847", "name": "SBI Small Cap Fund - Direct Growth", "category": "Small Cap"},
    {"code": "118834", "name": "Axis Bluechip Fund - Direct Growth", "category": "Large Cap"},
    {"code": "119364", "name": "Mirae Asset Large Cap Fund - Direct Growth", "category": "Large Cap"},
    {"code": "120716", "name": "Kotak Flexicap Fund - Direct Growth", "category": "Flexi Cap"},
    {"code": "120578", "name": "HDFC Balanced Advantage Fund - Direct Growth", "category": "BAF"},
    {"code": "122639", "name": "HDFC Small Cap Fund - Direct Growth", "category": "Small Cap"},
    {"code": "125354", "name": "Nippon India Large Cap Fund - Direct Growth", "category": "Large Cap"},
    {"code": "119062", "name": "Axis Small Cap Fund - Direct Growth", "category": "Small Cap"},
    {"code": "120837", "name": "SBI Equity Hybrid Fund - Direct Growth", "category": "Hybrid"},
    {"code": "118825", "name": "Axis Midcap Fund - Direct Growth", "category": "Mid Cap"},
    {"code": "120179", "name": "DSP Small Cap Fund - Direct Growth", "category": "Small Cap"},
    {"code": "135856", "name": "Quant Small Cap Fund - Direct Growth", "category": "Small Cap"},
    {"code": "120594", "name": "ICICI Pru Equity & Debt Fund - Direct Growth", "category": "Hybrid"},
    {"code": "118668", "name": "UTI Nifty 50 Index Fund - Direct Growth", "category": "Index"},
    {"code": "147622", "name": "Motilal Oswal Midcap Fund - Direct Growth", "category": "Mid Cap"},
    {"code": "120823", "name": "SBI Large & Midcap Fund - Direct Growth", "category": "Large & Mid Cap"},
    {"code": "118632", "name": "HDFC Top 100 Fund - Direct Growth", "category": "Large Cap"},
    {"code": "120684", "name": "Kotak Emerging Equity Fund - Direct Growth", "category": "Mid Cap"},
]

# ─── Breadth Metrics (maps to StockSentiment columns) ───
SHORT_TERM_METRICS = [
    {"key": "above_10ema", "label": "Above 10 EMA (Daily)", "column": "above_10ema"},
    {"key": "above_21ema", "label": "Above 21 EMA (Daily)", "column": "above_21ema"},
    {"key": "above_50ema", "label": "Above 50 EMA (Daily)", "column": "above_50ema"},
    {"key": "hit_52w_high", "label": "Hitting 52-Week High", "column": "hit_52w_high"},
    {"key": "hit_52w_low", "label": "Hitting 52-Week Low", "column": "hit_52w_low"},
    {"key": "macd_bull_cross", "label": "MACD Bullish Cross (5D)", "column": "macd_bull_cross"},
    {"key": "daily_rsi_gt60", "label": "Daily RSI > 60", "column": "rsi_daily", "threshold_type": "gt", "threshold_value": 60},
]

BROAD_TREND_METRICS = [
    {"key": "above_200ema", "label": "Above 200 EMA (Daily)", "column": "above_200ema"},
    {"key": "golden_cross", "label": "Golden Cross (50 > 200 EMA)", "column": "golden_cross"},
    {"key": "weekly_rsi_gt50", "label": "Weekly RSI > 50", "column": "rsi_weekly", "threshold_type": "gt", "threshold_value": 50},
]


class SimulationRequest(BaseModel):
    fund_code: str
    metric_key: str
    stock_threshold: int  # trigger when count <= this
    sip_amount: float = 10000
    multiplier: float = 2.0
    start_date: str  # YYYY-MM-DD
    duration_months: Optional[int] = None  # None = till date
    sip_day: int = 1  # day of month for SIP


class SimulationResult(BaseModel):
    fund_name: str
    metric_label: str
    # Regular SIP
    regular_total_invested: float
    regular_current_value: float
    regular_units: float
    regular_xirr: Optional[float]
    # Enhanced SIP
    enhanced_total_invested: float
    enhanced_current_value: float
    enhanced_units: float
    enhanced_xirr: Optional[float]
    # Comparison
    alpha_value: float
    alpha_pct: float
    extra_invested: float
    num_triggers: int
    total_sip_count: int
    # Time series for chart
    timeline: list[dict]
    # Trigger dates
    trigger_dates: list[str]


# ─── NAV Cache ─────────────────────────────────────────────
_nav_cache: dict[str, dict[str, float]] = {}


async def fetch_nav_history(fund_code: str) -> dict[str, float]:
    """Fetch historical NAV from MFAPI (mfapi.in). Returns {date_str: nav}."""
    if fund_code in _nav_cache:
        return _nav_cache[fund_code]

    url = f"https://api.mfapi.in/mf/{fund_code}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error("Failed to fetch NAV for %s: %s", fund_code, e)
        raise HTTPException(status_code=502, detail=f"Failed to fetch NAV data: {e}")

    nav_map: dict[str, float] = {}
    for entry in data.get("data", []):
        try:
            # MFAPI returns dates as DD-MM-YYYY
            parts = entry["date"].split("-")
            iso_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
            nav_map[iso_date] = float(entry["nav"])
        except (ValueError, KeyError, IndexError):
            continue

    _nav_cache[fund_code] = nav_map
    logger.info("Fetched %d NAV entries for fund %s", len(nav_map), fund_code)
    return nav_map


async def fetch_breadth_history(metric_key: str) -> dict[str, dict]:
    """Fetch historical breadth data from sentiment API.
    Returns {date_str: {count, total}} for each date."""
    # Use the internal sentiment history endpoint
    from models import SessionLocal, StockSentiment
    from sqlalchemy import func as sqlfunc

    db = SessionLocal()
    try:
        all_metrics = SHORT_TERM_METRICS + BROAD_TREND_METRICS
        metric_info = next((m for m in all_metrics if m["key"] == metric_key), None)
        if not metric_info:
            return {}

        col_name = metric_info["column"]
        threshold_type = metric_info.get("threshold_type")
        threshold_value = metric_info.get("threshold_value")

        # Get all unique dates
        dates = db.query(StockSentiment.date).distinct().order_by(StockSentiment.date).all()
        result: dict[str, dict] = {}

        for (d,) in dates:
            total = db.query(sqlfunc.count(StockSentiment.id)).filter(
                StockSentiment.date == d
            ).scalar() or 0

            if threshold_type == "gt":
                # RSI-based: count where rsi > threshold
                count = db.query(sqlfunc.count(StockSentiment.id)).filter(
                    StockSentiment.date == d,
                    getattr(StockSentiment, col_name) > threshold_value,
                ).scalar() or 0
            else:
                # Boolean flag: count where flag = True
                count = db.query(sqlfunc.count(StockSentiment.id)).filter(
                    StockSentiment.date == d,
                    getattr(StockSentiment, col_name) == True,
                ).scalar() or 0

            result[d] = {"count": count, "total": total}

        return result
    finally:
        db.close()


def _get_sip_dates(start: date, duration_months: Optional[int], sip_day: int) -> list[date]:
    """Generate monthly SIP dates from start until end."""
    end = date.today() if duration_months is None else _add_months(start, duration_months)
    dates = []
    current = start.replace(day=min(sip_day, 28))
    while current <= end:
        dates.append(current)
        current = _add_months(current, 1)
    return dates


def _add_months(d: date, months: int) -> date:
    month = d.month + months
    year = d.year + (month - 1) // 12
    month = ((month - 1) % 12) + 1
    day = min(d.day, 28)
    return date(year, month, day)


def _find_nav_date(nav_map: dict[str, float], target: date, max_lookforward: int = 5) -> tuple[str, float]:
    """Find the closest available NAV on or after the target date."""
    for offset in range(max_lookforward + 1):
        d = (target + timedelta(days=offset)).isoformat()
        if d in nav_map:
            return d, nav_map[d]
    # Try looking backward
    for offset in range(1, 4):
        d = (target - timedelta(days=offset)).isoformat()
        if d in nav_map:
            return d, nav_map[d]
    return "", 0.0


def _compute_xirr(cashflows: list[tuple[date, float]], final_value: float, final_date: date) -> Optional[float]:
    """Simple XIRR computation using Newton's method."""
    if not cashflows or final_value <= 0:
        return None

    flows = [(d, amt) for d, amt in cashflows]
    flows.append((final_date, final_value))

    def npv(rate: float) -> float:
        base_date = flows[0][0]
        total = 0.0
        for d, amt in flows:
            years = (d - base_date).days / 365.25
            total += amt / ((1 + rate) ** years)
        return total

    # Newton's method
    rate = 0.1
    for _ in range(100):
        try:
            f = npv(rate)
            # Numerical derivative
            h = 0.0001
            df = (npv(rate + h) - f) / h
            if abs(df) < 1e-12:
                break
            new_rate = rate - f / df
            if abs(new_rate - rate) < 1e-8:
                rate = new_rate
                break
            rate = new_rate
            # Guard against divergence
            if rate < -0.99:
                rate = -0.99
            if rate > 10:
                rate = 10
        except (ZeroDivisionError, OverflowError):
            return None

    return round(rate * 100, 2)


@router.get("/funds")
async def get_funds():
    """Return list of available mutual funds for simulation."""
    return {"success": True, "funds": TOP_FUNDS}


@router.get("/metrics")
async def get_metrics():
    """Return available breadth metrics for simulation."""
    short = [{"key": m["key"], "label": m["label"], "layer": "short_term"} for m in SHORT_TERM_METRICS]
    broad = [{"key": m["key"], "label": m["label"], "layer": "broad_trend"} for m in BROAD_TREND_METRICS]
    return {"success": True, "short_term": short, "broad_trend": broad}


@router.post("/run", response_model=SimulationResult)
async def run_simulation(req: SimulationRequest):
    """Run the SIP simulation comparing regular vs breadth-enhanced SIP."""
    # Validate fund
    fund = next((f for f in TOP_FUNDS if f["code"] == req.fund_code), None)
    if not fund:
        raise HTTPException(status_code=400, detail="Invalid fund code")

    # Validate metric
    all_metrics = SHORT_TERM_METRICS + BROAD_TREND_METRICS
    metric = next((m for m in all_metrics if m["key"] == req.metric_key), None)
    if not metric:
        raise HTTPException(status_code=400, detail="Invalid metric key")

    start = date.fromisoformat(req.start_date)

    # Fetch data
    nav_map = await fetch_nav_history(req.fund_code)
    if not nav_map:
        raise HTTPException(status_code=502, detail="No NAV data available")

    breadth = await fetch_breadth_history(req.metric_key)

    # Generate SIP dates
    sip_dates = _get_sip_dates(start, req.duration_months, req.sip_day)
    if not sip_dates:
        raise HTTPException(status_code=400, detail="No SIP dates in range")

    # Run simulation
    reg_units = 0.0
    enh_units = 0.0
    reg_invested = 0.0
    enh_invested = 0.0
    reg_cashflows: list[tuple[date, float]] = []
    enh_cashflows: list[tuple[date, float]] = []
    timeline: list[dict] = []
    trigger_dates: list[str] = []
    num_triggers = 0

    for sip_date in sip_dates:
        nav_date_str, nav = _find_nav_date(nav_map, sip_date)
        if not nav_date_str or nav <= 0:
            continue

        # Check if breadth condition triggers extra investment
        # Look for breadth data on or near the SIP date
        bd = None
        for offset in range(5):
            d_str = (sip_date + timedelta(days=offset)).isoformat()
            if d_str in breadth:
                bd = breadth[d_str]
                break
        if not bd:
            for offset in range(1, 4):
                d_str = (sip_date - timedelta(days=offset)).isoformat()
                if d_str in breadth:
                    bd = breadth[d_str]
                    break

        is_trigger = False
        breadth_count = None
        breadth_total = None
        if bd:
            breadth_count = bd["count"]
            breadth_total = bd["total"]
            is_trigger = breadth_count <= req.stock_threshold

        # Regular SIP
        reg_amount = req.sip_amount
        reg_new_units = reg_amount / nav
        reg_units += reg_new_units
        reg_invested += reg_amount
        reg_cashflows.append((sip_date, -reg_amount))

        # Enhanced SIP
        enh_amount = req.sip_amount
        if is_trigger:
            enh_amount += req.sip_amount * req.multiplier
            num_triggers += 1
            trigger_dates.append(sip_date.isoformat())

        enh_new_units = enh_amount / nav
        enh_units += enh_new_units
        enh_invested += enh_amount
        enh_cashflows.append((sip_date, -enh_amount))

        # Current value at this point (using this date's NAV)
        reg_value = reg_units * nav
        enh_value = enh_units * nav

        timeline.append({
            "date": nav_date_str,
            "nav": nav,
            "regular_invested": round(reg_invested, 2),
            "regular_value": round(reg_value, 2),
            "enhanced_invested": round(enh_invested, 2),
            "enhanced_value": round(enh_value, 2),
            "is_trigger": is_trigger,
            "breadth_count": breadth_count,
            "breadth_total": breadth_total,
        })

    if not timeline:
        raise HTTPException(status_code=400, detail="No valid SIP transactions could be processed")

    # Final valuation using latest NAV
    sorted_dates = sorted(nav_map.keys(), reverse=True)
    latest_nav_date = sorted_dates[0] if sorted_dates else timeline[-1]["date"]
    latest_nav = nav_map.get(latest_nav_date, timeline[-1]["nav"])
    final_date = date.fromisoformat(latest_nav_date)

    reg_final_value = round(reg_units * latest_nav, 2)
    enh_final_value = round(enh_units * latest_nav, 2)

    reg_xirr = _compute_xirr(reg_cashflows, reg_final_value, final_date)
    enh_xirr = _compute_xirr(enh_cashflows, enh_final_value, final_date)

    alpha_value = round(enh_final_value - reg_final_value, 2)
    alpha_pct = round(((enh_final_value / reg_final_value) - 1) * 100, 2) if reg_final_value > 0 else 0

    return SimulationResult(
        fund_name=fund["name"],
        metric_label=metric["label"],
        regular_total_invested=round(reg_invested, 2),
        regular_current_value=reg_final_value,
        regular_units=round(reg_units, 4),
        regular_xirr=reg_xirr,
        enhanced_total_invested=round(enh_invested, 2),
        enhanced_current_value=enh_final_value,
        enhanced_units=round(enh_units, 4),
        enhanced_xirr=enh_xirr,
        alpha_value=alpha_value,
        alpha_pct=alpha_pct,
        extra_invested=round(enh_invested - reg_invested, 2),
        num_triggers=num_triggers,
        total_sip_count=len(timeline),
        timeline=timeline,
        trigger_dates=trigger_dates,
    )
