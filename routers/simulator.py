"""
FIE v3 — Mutual Fund SIP Simulator Router
Simulates enhanced SIP strategy based on market breadth signals.
Uses BreadthDaily table for aggregate Nifty 500 EMA counts.
"""

import logging
from datetime import date, timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
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

# ─── Default Strategies ───────────────────────────────────
DEFAULT_STRATEGIES = [
    {
        "id": "strategy_1",
        "label": "21 EMA Breadth ≤ 75 → 1x Top-Up",
        "description": "No. of Nifty 500 stocks trading above 21 EMA (Daily) less than 75 → 1 extra SIP",
        "metric": "above_21ema",
        "threshold": 75,
        "multiplier": 1,
    },
    {
        "id": "strategy_2",
        "label": "200 EMA Breadth ≤ 100 → 2x Top-Up",
        "description": "No. of Nifty 500 stocks trading above 200 EMA (Daily) less than 100 → 2 extra SIP",
        "metric": "above_200ema",
        "threshold": 100,
        "multiplier": 2,
    },
]

COOLOFF_DAYS = 30  # 1 month cool-off after a top-up


class SimulationRequest(BaseModel):
    fund_code: str
    metric_key: str
    stock_threshold: int
    sip_amount: float = 10000
    multiplier: float = 2.0
    start_date: str  # YYYY-MM-DD
    duration_months: Optional[int] = None
    sip_day: int = 1
    cooloff_days: int = COOLOFF_DAYS


class SimulationResult(BaseModel):
    fund_name: str
    metric_label: str
    regular_total_invested: float
    regular_current_value: float
    regular_units: float
    regular_xirr: Optional[float]
    enhanced_total_invested: float
    enhanced_current_value: float
    enhanced_units: float
    enhanced_xirr: Optional[float]
    alpha_value: float
    alpha_pct: float
    extra_invested: float
    num_triggers: int
    total_sip_count: int
    cooloff_skips: int
    timeline: list[dict]
    trigger_dates: list[str]


class BatchSummaryRow(BaseModel):
    fund_code: str
    fund_name: str
    category: str
    strategy_id: str
    period_label: str
    period_months: Optional[int]
    regular_invested: float
    regular_value: float
    regular_xirr: Optional[float]
    enhanced_invested: float
    enhanced_value: float
    enhanced_xirr: Optional[float]
    incremental_return_abs: float
    incremental_return_pct: float
    incremental_xirr: Optional[float]
    num_triggers: int
    cooloff_skips: int
    total_sips: int


# ─── NAV Cache ─────────────────────────────────────────────
_nav_cache: dict[str, dict[str, float]] = {}


async def fetch_nav_history(fund_code: str) -> dict[str, float]:
    """Fetch historical NAV from MFAPI. Returns {date_str: nav}."""
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
            parts = entry["date"].split("-")
            iso_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
            nav_map[iso_date] = float(entry["nav"])
        except (ValueError, KeyError, IndexError):
            continue

    _nav_cache[fund_code] = nav_map
    logger.info("Fetched %d NAV entries for fund %s", len(nav_map), fund_code)
    return nav_map


# ─── Breadth Cache ─────────────────────────────────────────
_breadth_cache: dict[str, dict[str, dict]] = {}


def fetch_breadth_from_db(metric: str) -> dict[str, dict]:
    """Fetch breadth data from BreadthDaily table. Returns {date_str: {count, total}}."""
    if metric in _breadth_cache:
        return _breadth_cache[metric]

    from models import BreadthDaily, SessionLocal

    db = SessionLocal()
    try:
        rows = db.query(BreadthDaily).filter(BreadthDaily.metric == metric).all()
        result: dict[str, dict] = {}
        for r in rows:
            result[r.date] = {"count": r.count, "total": r.total}
        _breadth_cache[metric] = result
        logger.info("Loaded %d breadth records for metric '%s'", len(result), metric)
        return result
    finally:
        db.close()


def _get_sip_dates(start: date, duration_months: Optional[int], sip_day: int) -> list[date]:
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


def _find_nav(nav_map: dict[str, float], target: date) -> tuple[str, float]:
    """Find closest NAV on or near target date."""
    for offset in range(6):
        d = (target + timedelta(days=offset)).isoformat()
        if d in nav_map:
            return d, nav_map[d]
    for offset in range(1, 4):
        d = (target - timedelta(days=offset)).isoformat()
        if d in nav_map:
            return d, nav_map[d]
    return "", 0.0


def _find_breadth(breadth: dict[str, dict], target: date) -> Optional[dict]:
    """Find breadth data on or near target date."""
    for offset in range(5):
        d = (target + timedelta(days=offset)).isoformat()
        if d in breadth:
            return breadth[d]
    for offset in range(1, 4):
        d = (target - timedelta(days=offset)).isoformat()
        if d in breadth:
            return breadth[d]
    return None


def _compute_xirr(cashflows: list[tuple[date, float]], final_value: float, final_date: date) -> Optional[float]:
    """XIRR via pyxirr if available, else Newton's method."""
    if not cashflows or final_value <= 0:
        return None
    try:
        import pyxirr
        dates = [d for d, _ in cashflows] + [final_date]
        amounts = [amt for _, amt in cashflows] + [final_value]
        result = pyxirr.xirr(dates, amounts)
        if result is not None:
            return round(result * 100, 2)
    except Exception:
        pass

    # Fallback: Newton's method
    flows = list(cashflows) + [(final_date, final_value)]
    def npv(rate: float) -> float:
        base = flows[0][0]
        return sum(amt / ((1 + rate) ** ((d - base).days / 365.25)) for d, amt in flows)

    rate = 0.1
    for _ in range(100):
        try:
            f = npv(rate)
            df = (npv(rate + 0.0001) - f) / 0.0001
            if abs(df) < 1e-12:
                break
            new_rate = rate - f / df
            if abs(new_rate - rate) < 1e-8:
                rate = new_rate
                break
            rate = max(-0.99, min(10, new_rate))
        except (ZeroDivisionError, OverflowError):
            return None
    return round(rate * 100, 2)


def run_sim_core(
    nav_map: dict[str, float],
    breadth: dict[str, dict],
    sip_dates: list[date],
    sip_amount: float,
    multiplier: float,
    threshold: int,
    cooloff_days: int,
) -> dict:
    """Core simulation engine. Returns dict with all results."""
    reg_units = enh_units = reg_invested = enh_invested = 0.0
    reg_cashflows: list[tuple[date, float]] = []
    enh_cashflows: list[tuple[date, float]] = []
    timeline: list[dict] = []
    trigger_dates: list[str] = []
    num_triggers = 0
    cooloff_skips = 0
    last_trigger_date: Optional[date] = None

    for sip_date in sip_dates:
        nav_date_str, nav = _find_nav(nav_map, sip_date)
        if not nav_date_str or nav <= 0:
            continue

        bd = _find_breadth(breadth, sip_date)
        is_trigger = False
        breadth_count = None
        breadth_total = None
        in_cooloff = False

        if bd:
            breadth_count = bd["count"]
            breadth_total = bd["total"]
            signal_fires = breadth_count <= threshold

            if signal_fires:
                # Check cool-off: skip if within cooloff_days of last trigger
                if last_trigger_date and (sip_date - last_trigger_date).days < cooloff_days:
                    in_cooloff = True
                    cooloff_skips += 1
                else:
                    is_trigger = True

        # Regular SIP (always the same)
        reg_units += sip_amount / nav
        reg_invested += sip_amount
        reg_cashflows.append((sip_date, -sip_amount))

        # Enhanced SIP
        enh_amount = sip_amount
        if is_trigger:
            enh_amount += sip_amount * multiplier
            num_triggers += 1
            trigger_dates.append(sip_date.isoformat())
            last_trigger_date = sip_date

        enh_units += enh_amount / nav
        enh_invested += enh_amount
        enh_cashflows.append((sip_date, -enh_amount))

        timeline.append({
            "date": nav_date_str,
            "nav": round(nav, 4),
            "regular_invested": round(reg_invested, 2),
            "regular_value": round(reg_units * nav, 2),
            "enhanced_invested": round(enh_invested, 2),
            "enhanced_value": round(enh_units * nav, 2),
            "is_trigger": is_trigger,
            "in_cooloff": in_cooloff,
            "breadth_count": breadth_count,
            "breadth_total": breadth_total,
        })

    if not timeline:
        return None

    # Final valuation
    sorted_dates = sorted(nav_map.keys(), reverse=True)
    latest_nav_date = sorted_dates[0] if sorted_dates else timeline[-1]["date"]
    latest_nav = nav_map.get(latest_nav_date, timeline[-1]["nav"])
    final_date = date.fromisoformat(latest_nav_date)

    reg_final = round(reg_units * latest_nav, 2)
    enh_final = round(enh_units * latest_nav, 2)
    reg_xirr = _compute_xirr(reg_cashflows, reg_final, final_date)
    enh_xirr = _compute_xirr(enh_cashflows, enh_final, final_date)

    return {
        "reg_invested": round(reg_invested, 2),
        "reg_value": reg_final,
        "reg_units": round(reg_units, 4),
        "reg_xirr": reg_xirr,
        "enh_invested": round(enh_invested, 2),
        "enh_value": enh_final,
        "enh_units": round(enh_units, 4),
        "enh_xirr": enh_xirr,
        "alpha_value": round(enh_final - reg_final, 2),
        "alpha_pct": round(((enh_final / reg_final) - 1) * 100, 2) if reg_final > 0 else 0,
        "extra_invested": round(enh_invested - reg_invested, 2),
        "num_triggers": num_triggers,
        "cooloff_skips": cooloff_skips,
        "total_sips": len(timeline),
        "timeline": timeline,
        "trigger_dates": trigger_dates,
        "reg_cashflows": reg_cashflows,
        "enh_cashflows": enh_cashflows,
    }


# ─── Endpoints ─────────────────────────────────────────────

@router.get("/funds")
async def get_funds():
    return {"success": True, "funds": TOP_FUNDS}


@router.get("/metrics")
async def get_metrics():
    return {"success": True, "strategies": DEFAULT_STRATEGIES}


@router.post("/run")
async def run_simulation(req: SimulationRequest):
    """Run single simulation with custom parameters."""
    fund = next((f for f in TOP_FUNDS if f["code"] == req.fund_code), None)
    if not fund:
        raise HTTPException(status_code=400, detail="Invalid fund code")

    nav_map = await fetch_nav_history(req.fund_code)
    if not nav_map:
        raise HTTPException(status_code=502, detail="No NAV data available")

    breadth = fetch_breadth_from_db(req.metric_key)
    sip_dates = _get_sip_dates(date.fromisoformat(req.start_date), req.duration_months, req.sip_day)
    if not sip_dates:
        raise HTTPException(status_code=400, detail="No SIP dates in range")

    result = run_sim_core(nav_map, breadth, sip_dates, req.sip_amount, req.multiplier, req.stock_threshold, req.cooloff_days)
    if not result:
        raise HTTPException(status_code=400, detail="No valid SIP transactions")

    return {
        "success": True,
        "fund_name": fund["name"],
        "metric_label": req.metric_key,
        **{k: v for k, v in result.items() if k not in ("reg_cashflows", "enh_cashflows")},
    }


@router.get("/batch")
async def batch_simulate(sip_amount: float = 10000, sip_day: int = 1):
    """Pre-compute both default strategies for all 25 funds across 1Y, 2Y, 3Y, Lifetime."""
    periods = [
        {"label": "1Y", "months": 12},
        {"label": "2Y", "months": 24},
        {"label": "3Y", "months": 36},
        {"label": "Lifetime", "months": None},
    ]

    # Pre-load breadth data for both metrics
    breadth_data = {}
    for strat in DEFAULT_STRATEGIES:
        breadth_data[strat["metric"]] = fetch_breadth_from_db(strat["metric"])

    results = []
    errors = []

    for fund in TOP_FUNDS:
        try:
            nav_map = await fetch_nav_history(fund["code"])
            if not nav_map:
                errors.append(f"No NAV for {fund['name']}")
                continue
        except Exception as e:
            errors.append(f"NAV fetch failed for {fund['name']}: {e}")
            continue

        # Determine earliest NAV date for lifetime
        earliest_nav = min(nav_map.keys())

        for strat in DEFAULT_STRATEGIES:
            breadth = breadth_data[strat["metric"]]

            for period in periods:
                if period["months"] is not None:
                    start = _add_months(date.today(), -period["months"])
                else:
                    # Lifetime: start from earliest NAV or earliest breadth
                    start = date.fromisoformat(earliest_nav)

                sip_dates = _get_sip_dates(start, period["months"], sip_day)
                if not sip_dates:
                    continue

                sim = run_sim_core(
                    nav_map, breadth, sip_dates, sip_amount,
                    strat["multiplier"], strat["threshold"], COOLOFF_DAYS,
                )
                if not sim:
                    continue

                # Incremental XIRR = enhanced XIRR - regular XIRR
                inc_xirr = None
                if sim["enh_xirr"] is not None and sim["reg_xirr"] is not None:
                    inc_xirr = round(sim["enh_xirr"] - sim["reg_xirr"], 2)

                # Incremental return = extra value gained per extra rupee invested
                inc_return_abs = sim["alpha_value"]
                inc_return_pct = sim["alpha_pct"]

                results.append(BatchSummaryRow(
                    fund_code=fund["code"],
                    fund_name=fund["name"],
                    category=fund["category"],
                    strategy_id=strat["id"],
                    period_label=period["label"],
                    period_months=period["months"],
                    regular_invested=sim["reg_invested"],
                    regular_value=sim["reg_value"],
                    regular_xirr=sim["reg_xirr"],
                    enhanced_invested=sim["enh_invested"],
                    enhanced_value=sim["enh_value"],
                    enhanced_xirr=sim["enh_xirr"],
                    incremental_return_abs=inc_return_abs,
                    incremental_return_pct=inc_return_pct,
                    incremental_xirr=inc_xirr,
                    num_triggers=sim["num_triggers"],
                    cooloff_skips=sim["cooloff_skips"],
                    total_sips=sim["total_sips"],
                ))

    return {
        "success": True,
        "strategies": DEFAULT_STRATEGIES,
        "results": [r.model_dump() for r in results],
        "errors": errors,
        "funds_count": len(TOP_FUNDS),
    }


@router.get("/breadth-status")
async def breadth_status():
    """Check if breadth data is available."""
    from models import BreadthDaily, SessionLocal
    db = SessionLocal()
    try:
        total = db.query(BreadthDaily).count()
        metrics = {}
        for metric in ["above_21ema", "above_200ema"]:
            count = db.query(BreadthDaily).filter(BreadthDaily.metric == metric).count()
            if count > 0:
                first = db.query(BreadthDaily).filter(BreadthDaily.metric == metric).order_by(BreadthDaily.date).first()
                last = db.query(BreadthDaily).filter(BreadthDaily.metric == metric).order_by(BreadthDaily.date.desc()).first()
                metrics[metric] = {"rows": count, "first_date": first.date, "last_date": last.date}
            else:
                metrics[metric] = {"rows": 0}
        return {"success": True, "total_rows": total, "metrics": metrics}
    finally:
        db.close()
