"""
FIE v3 — Mutual Fund SIP Simulator Router
All data pre-computed and served from DB. Simulation is pure math.

Data pipeline (runs at startup + EOD):
  StockSentiment → BreadthDaily → BreadthThresholdFlag
  mfapi.in (concurrent) → MfNavHistory
  Batch pre-computation → SimulatorCache
"""

import json
import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import (
    BreadthDaily,
    BreadthThresholdFlag,
    MfNavHistory,
    SimulatorCache,
    get_db,
)

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

# ─── All Breadth Metrics (from StockSentiment columns) ────
ALL_METRICS = [
    {"key": "above_10ema", "label": "Above 10 EMA", "description": "Stocks trading above 10-day EMA"},
    {"key": "above_21ema", "label": "Above 21 EMA", "description": "Stocks trading above 21-day EMA"},
    {"key": "above_50ema", "label": "Above 50 EMA", "description": "Stocks trading above 50-day EMA"},
    {"key": "above_200ema", "label": "Above 200 EMA", "description": "Stocks trading above 200-day EMA"},
    {"key": "golden_cross", "label": "Golden Cross", "description": "Stocks with 50 EMA above 200 EMA"},
    {"key": "macd_bull_cross", "label": "MACD Bullish", "description": "Stocks with bullish MACD crossover"},
    {"key": "hit_52w_low", "label": "Near 52W Low", "description": "Stocks near 52-week low"},
    {"key": "hit_52w_high", "label": "Near 52W High", "description": "Stocks near 52-week high"},
    {"key": "roc_positive", "label": "ROC Positive", "description": "Stocks with positive rate of change"},
    {"key": "above_prev_month_high", "label": "Above Prev Month High", "description": "Stocks above previous month high"},
]

STANDARD_THRESHOLDS = [25, 50, 75, 100, 125]

COOLOFF_DAYS = 30

# ─── Default Strategies for batch view ────────────────────
DEFAULT_STRATEGIES = [
    {
        "id": "strategy_1",
        "label": "21 EMA Breadth ≤ 75 → 1x Top-Up",
        "description": "Stocks above 21 EMA drops below 75 → 1 extra SIP",
        "metric": "above_21ema",
        "threshold": 75,
        "multiplier": 1,
    },
    {
        "id": "strategy_2",
        "label": "200 EMA Breadth ≤ 100 → 2x Top-Up",
        "description": "Stocks above 200 EMA drops below 100 → 2 extra SIP",
        "metric": "above_200ema",
        "threshold": 100,
        "multiplier": 2,
    },
]


# ─── Request/Response Models ──────────────────────────────

class SimulationRequest(BaseModel):
    fund_code: str
    metric_key: str
    stock_threshold: int
    sip_amount: float = 10000
    multiplier: float = 2.0
    start_date: str
    duration_months: Optional[int] = None
    sip_day: int = 1
    cooloff_days: int = COOLOFF_DAYS


# ─── Helpers ──────────────────────────────────────────────

def _add_months(d: date, months: int) -> date:
    month = d.month + months
    year = d.year + (month - 1) // 12
    month = ((month - 1) % 12) + 1
    return date(year, month, min(d.day, 28))


def _get_sip_dates(start: date, duration_months: Optional[int], sip_day: int) -> list[date]:
    end = date.today() if duration_months is None else _add_months(start, duration_months)
    dates = []
    current = start.replace(day=min(sip_day, 28))
    while current <= end:
        dates.append(current)
        current = _add_months(current, 1)
    return dates


def _find_nearest(data_map: dict[str, float], target: date) -> tuple[str, float]:
    """Find value on or near target date (±5 days)."""
    for offset in range(6):
        d = (target + timedelta(days=offset)).isoformat()
        if d in data_map:
            return d, data_map[d]
    for offset in range(1, 4):
        d = (target - timedelta(days=offset)).isoformat()
        if d in data_map:
            return d, data_map[d]
    return "", 0.0


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


def _load_nav_from_db(db: Session, fund_code: str) -> dict[str, float]:
    """Load NAV history from MfNavHistory table. Returns {date_str: nav}."""
    rows = db.query(MfNavHistory).filter(MfNavHistory.fund_code == fund_code).all()
    return {r.date: r.nav for r in rows}


def _fetch_nav_on_demand(fund_code: str, db: Session) -> dict[str, float]:
    """Fetch NAV from mfapi.in on-demand, store in DB, return nav_map.
    Fallback when pipeline hasn't cached NAV yet (~1-2s)."""
    import httpx
    try:
        resp = httpx.get(f"https://api.mfapi.in/mf/{fund_code}", timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error("On-demand NAV fetch failed for %s: %s", fund_code, e)
        return {}

    nav_map: dict[str, float] = {}
    batch = []
    existing_dates = {r[0] for r in db.query(MfNavHistory.date).filter(
        MfNavHistory.fund_code == fund_code).all()}

    for entry in data.get("data", []):
        try:
            parts = entry["date"].split("-")
            iso_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
            nav_val = float(entry["nav"])
            nav_map[iso_date] = nav_val
            if iso_date not in existing_dates:
                batch.append(MfNavHistory(fund_code=fund_code, date=iso_date, nav=nav_val))
        except (ValueError, KeyError, IndexError):
            continue

    if batch:
        for i in range(0, len(batch), 500):
            db.add_all(batch[i:i+500])
        db.commit()
        logger.info("On-demand NAV: fetched %d entries for fund %s, cached %d new",
                     len(nav_map), fund_code, len(batch))
    return nav_map


def _load_breadth_from_db(db: Session, metric: str) -> dict[str, int]:
    """Load breadth counts from BreadthDaily. Returns {date_str: count}."""
    rows = db.query(BreadthDaily).filter(BreadthDaily.metric == metric).all()
    return {r.date: r.count for r in rows}


def _find_breadth_count(breadth_map: dict[str, int], target: date) -> Optional[int]:
    """Find breadth count on or near target date."""
    for offset in range(5):
        d = (target + timedelta(days=offset)).isoformat()
        if d in breadth_map:
            return breadth_map[d]
    for offset in range(1, 4):
        d = (target - timedelta(days=offset)).isoformat()
        if d in breadth_map:
            return breadth_map[d]
    return None


def run_sim_core(
    nav_map: dict[str, float],
    breadth_map: dict[str, int],
    sip_dates: list[date],
    sip_amount: float,
    multiplier: float,
    threshold: int,
    cooloff_days: int,
) -> Optional[dict]:
    """Core simulation engine. All data from DB, pure math."""
    reg_units = enh_units = reg_invested = enh_invested = 0.0
    reg_cashflows: list[tuple[date, float]] = []
    enh_cashflows: list[tuple[date, float]] = []
    timeline: list[dict] = []
    trigger_dates: list[str] = []
    num_triggers = cooloff_skips = 0
    last_trigger_date: Optional[date] = None

    for sip_date in sip_dates:
        nav_date_str, nav = _find_nearest(nav_map, sip_date)
        if not nav_date_str or nav <= 0:
            continue

        breadth_count = _find_breadth_count(breadth_map, sip_date)
        is_trigger = False
        in_cooloff = False

        if breadth_count is not None:
            if breadth_count <= threshold:
                if last_trigger_date and (sip_date - last_trigger_date).days < cooloff_days:
                    in_cooloff = True
                    cooloff_skips += 1
                else:
                    is_trigger = True

        reg_units += sip_amount / nav
        reg_invested += sip_amount
        reg_cashflows.append((sip_date, -sip_amount))

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
        })

    if not timeline:
        return None

    sorted_dates = sorted(nav_map.keys(), reverse=True)
    latest_nav_date = sorted_dates[0] if sorted_dates else timeline[-1]["date"]
    latest_nav = nav_map.get(latest_nav_date, timeline[-1]["nav"])
    final_date = date.fromisoformat(latest_nav_date)

    reg_final = round(reg_units * latest_nav, 2)
    enh_final = round(enh_units * latest_nav, 2)

    return {
        "reg_invested": round(reg_invested, 2),
        "reg_value": reg_final,
        "reg_units": round(reg_units, 4),
        "reg_xirr": _compute_xirr(reg_cashflows, reg_final, final_date),
        "enh_invested": round(enh_invested, 2),
        "enh_value": enh_final,
        "enh_units": round(enh_units, 4),
        "enh_xirr": _compute_xirr(enh_cashflows, enh_final, final_date),
        "alpha_value": round(enh_final - reg_final, 2),
        "alpha_pct": round(((enh_final / reg_final) - 1) * 100, 2) if reg_final > 0 else 0,
        "extra_invested": round(enh_invested - reg_invested, 2),
        "num_triggers": num_triggers,
        "cooloff_skips": cooloff_skips,
        "total_sips": len(timeline),
        "timeline": timeline,
        "trigger_dates": trigger_dates,
    }


# ─── Endpoints ────────────────────────────────────────────

@router.get("/funds")
async def get_funds():
    return {"success": True, "funds": TOP_FUNDS}


@router.get("/metrics")
async def get_metrics():
    return {
        "success": True,
        "metrics": ALL_METRICS,
        "thresholds": STANDARD_THRESHOLDS,
        "strategies": DEFAULT_STRATEGIES,
    }


@router.post("/run")
async def run_simulation(req: SimulationRequest, db: Session = Depends(get_db)):
    """Run single simulation. Fetches NAV on-demand if not cached."""
    fund = next((f for f in TOP_FUNDS if f["code"] == req.fund_code), None)
    if not fund:
        raise HTTPException(status_code=400, detail="Invalid fund code")

    # Load NAV from DB, fallback to on-demand fetch from mfapi.in
    nav_map = _load_nav_from_db(db, req.fund_code)
    if not nav_map:
        nav_map = _fetch_nav_on_demand(req.fund_code, db)
        if not nav_map:
            raise HTTPException(status_code=404, detail="Could not fetch NAV data for this fund")

    # Load breadth — if empty, simulation runs without triggers (regular SIP only)
    breadth_map = _load_breadth_from_db(db, req.metric_key)
    no_breadth = len(breadth_map) == 0

    sip_dates = _get_sip_dates(
        date.fromisoformat(req.start_date),
        req.duration_months, req.sip_day,
    )
    if not sip_dates:
        raise HTTPException(status_code=400, detail="No SIP dates in range")

    result = run_sim_core(
        nav_map, breadth_map, sip_dates,
        req.sip_amount, req.multiplier, req.stock_threshold, req.cooloff_days,
    )
    if not result:
        raise HTTPException(status_code=400, detail="No valid SIP transactions found")

    resp = {
        "success": True,
        "fund_name": fund["name"],
        "metric_label": req.metric_key,
        **result,
    }
    if no_breadth:
        resp["warning"] = "Breadth data not yet available — showing regular SIP only. Top-ups will appear after pipeline runs."
    return resp


@router.get("/batch")
async def batch_results(db: Session = Depends(get_db)):
    """Serve pre-computed batch results from cache. Instant."""
    cached = db.query(SimulatorCache).filter(
        SimulatorCache.cache_key == "batch_default"
    ).first()

    if not cached:
        return {
            "success": False,
            "strategies": DEFAULT_STRATEGIES,
            "results": [],
            "errors": ["Batch results not yet computed. Data pipeline runs on startup."],
            "funds_count": len(TOP_FUNDS),
            "cached": False,
        }

    data = json.loads(cached.data_json)
    data["cached"] = True
    data["computed_at"] = cached.computed_at.isoformat() if cached.computed_at else None
    return data


@router.get("/breadth-status")
async def breadth_status(db: Session = Depends(get_db)):
    """Check breadth + NAV data availability."""
    total_breadth = db.query(BreadthDaily).count()
    total_nav = db.query(MfNavHistory).count()
    total_flags = db.query(BreadthThresholdFlag).count()

    metrics = {}
    for m in ALL_METRICS:
        key = m["key"]
        count = db.query(BreadthDaily).filter(BreadthDaily.metric == key).count()
        if count > 0:
            first = db.query(BreadthDaily).filter(BreadthDaily.metric == key).order_by(BreadthDaily.date).first()
            last = db.query(BreadthDaily).filter(BreadthDaily.metric == key).order_by(BreadthDaily.date.desc()).first()
            metrics[key] = {"rows": count, "first_date": first.date, "last_date": last.date}
        else:
            metrics[key] = {"rows": 0}

    fund_nav_counts = {}
    for f in TOP_FUNDS:
        cnt = db.query(MfNavHistory).filter(MfNavHistory.fund_code == f["code"]).count()
        if cnt > 0:
            fund_nav_counts[f["code"]] = cnt

    return {
        "success": True,
        "breadth_rows": total_breadth,
        "nav_rows": total_nav,
        "flag_rows": total_flags,
        "metrics": metrics,
        "funds_with_nav": len(fund_nav_counts),
        "fund_nav_counts": fund_nav_counts,
    }
