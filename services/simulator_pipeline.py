"""
FIE v3 — Simulator Data Pipeline
Runs at startup + EOD to pre-compute all simulator data.
Steps: StockSentiment→BreadthDaily→ThresholdFlags, MF NAV cache, batch pre-compute.
"""

import asyncio
import json
import logging
from datetime import date, datetime

import httpx
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from models import (
    BreadthDaily, BreadthThresholdFlag, MfNavHistory,
    SessionLocal, SimulatorCache, StockSentiment,
)

logger = logging.getLogger("fie_v3.simulator_pipeline")

BREADTH_METRICS = [
    "above_10ema", "above_21ema", "above_50ema", "above_200ema",
    "golden_cross", "macd_bull_cross", "hit_52w_low", "hit_52w_high",
    "roc_positive", "above_prev_month_high",
]
STANDARD_THRESHOLDS = [25, 50, 75, 100, 125]
TOP_FUND_CODES = [
    "119598", "120503", "120505", "118989", "120586", "120587",
    "125497", "120847", "118834", "119364", "120716", "120578",
    "122639", "125354", "119062", "120837", "118825", "120179",
    "135856", "120594", "118668", "147622", "120823", "118632", "120684",
]


def aggregate_breadth(db: Session) -> int:
    """Aggregate per-stock booleans into daily breadth counts."""
    dates = [r[0] for r in db.query(StockSentiment.date).distinct().all()]
    if not dates:
        logger.warning("Breadth: no StockSentiment data")
        return 0

    existing_keys = {(r.date, r.metric) for r in db.query(BreadthDaily.date, BreadthDaily.metric).all()}
    total_per_date = dict(
        db.query(StockSentiment.date, sa_func.count(StockSentiment.id))
        .group_by(StockSentiment.date).all()
    )

    total = 0
    for metric in BREADTH_METRICS:
        col = getattr(StockSentiment, metric, None)
        if col is None:
            continue
        true_counts = dict(
            db.query(StockSentiment.date, sa_func.count(StockSentiment.id))
            .filter(col == True).group_by(StockSentiment.date).all()  # noqa: E712
        )
        batch = []
        for dt in dates:
            tc, tot = true_counts.get(dt, 0), total_per_date.get(dt, 0)
            if tot == 0:
                continue
            if (dt, metric) in existing_keys:
                db.query(BreadthDaily).filter(
                    BreadthDaily.date == dt, BreadthDaily.metric == metric
                ).update({"count": tc, "total": tot})
            else:
                batch.append(BreadthDaily(date=dt, metric=metric, count=tc, total=tot))
            total += 1
        if batch:
            db.add_all(batch)
        db.commit()
    logger.info("Breadth: aggregated %d records across %d metrics", total, len(BREADTH_METRICS))
    return total


def compute_threshold_flags(db: Session) -> int:
    """Pre-compute trigger flags for each breadth row × standard threshold."""
    breadth_rows = db.query(BreadthDaily).all()
    if not breadth_rows:
        return 0

    existing = {
        (r.date, r.metric, r.threshold)
        for r in db.query(
            BreadthThresholdFlag.date, BreadthThresholdFlag.metric, BreadthThresholdFlag.threshold
        ).all()
    }

    total, batch = 0, []
    for row in breadth_rows:
        for thresh in STANDARD_THRESHOLDS:
            triggered = row.count <= thresh
            key = (row.date, row.metric, thresh)
            if key in existing:
                db.query(BreadthThresholdFlag).filter(
                    BreadthThresholdFlag.date == row.date,
                    BreadthThresholdFlag.metric == row.metric,
                    BreadthThresholdFlag.threshold == thresh,
                ).update({"triggered": triggered, "count": row.count})
            else:
                batch.append(BreadthThresholdFlag(
                    date=row.date, metric=row.metric,
                    threshold=thresh, triggered=triggered, count=row.count,
                ))
            total += 1
            if len(batch) >= 1000:
                db.add_all(batch)
                db.commit()
                batch = []
    if batch:
        db.add_all(batch)
    db.commit()
    logger.info("Flags: %d computed (%d rows × %d thresholds)", total, len(breadth_rows), len(STANDARD_THRESHOLDS))
    return total


async def _fetch_single_nav(client: httpx.AsyncClient, fund_code: str) -> list[dict]:
    """Fetch NAV history for a single fund from mfapi.in."""
    try:
        resp = await client.get(f"https://api.mfapi.in/mf/{fund_code}")
        resp.raise_for_status()
        entries = []
        for entry in resp.json().get("data", []):
            try:
                parts = entry["date"].split("-")
                entries.append({"date": f"{parts[2]}-{parts[1]}-{parts[0]}", "nav": float(entry["nav"])})
            except (ValueError, KeyError, IndexError):
                continue
        return entries
    except Exception as e:
        logger.error("NAV fetch failed for %s: %s", fund_code, e)
        return []


async def fetch_all_nav_concurrent() -> dict[str, list[dict]]:
    """Fetch NAV for all 25 funds concurrently."""
    async with httpx.AsyncClient(timeout=60) as client:
        async def _f(code: str) -> tuple[str, list[dict]]:
            return code, await _fetch_single_nav(client, code)
        results = await asyncio.gather(*[_f(c) for c in TOP_FUND_CODES])
        return dict(results)


def store_nav_data(db: Session, all_nav: dict[str, list[dict]]) -> int:
    """Store fetched NAV into MfNavHistory. Skips existing dates."""
    total = 0
    for fund_code, entries in all_nav.items():
        if not entries:
            continue
        existing = {r[0] for r in db.query(MfNavHistory.date).filter(MfNavHistory.fund_code == fund_code).all()}
        batch = [MfNavHistory(fund_code=fund_code, date=e["date"], nav=e["nav"])
                 for e in entries if e["date"] not in existing]
        total += len(batch)
        if batch:
            for i in range(0, len(batch), 500):
                db.add_all(batch[i:i+500])
                db.commit()
    logger.info("NAV: stored %d new records across %d funds", total, len(all_nav))
    return total


def precompute_batch(db: Session) -> bool:
    """Pre-compute default batch results and store in SimulatorCache."""
    from routers.simulator import (
        ALL_METRICS, DEFAULT_STRATEGIES, TOP_FUNDS,
        _add_months, _get_sip_dates, run_sim_core,
    )

    periods = [
        {"label": "1Y", "months": 12}, {"label": "2Y", "months": 24},
        {"label": "3Y", "months": 36}, {"label": "Lifetime", "months": None},
    ]
    results, errors = [], []

    for fund in TOP_FUNDS:
        nav_rows = db.query(MfNavHistory).filter(MfNavHistory.fund_code == fund["code"]).all()
        if not nav_rows:
            errors.append(f"No cached NAV for {fund['name']}")
            continue
        nav_map = {r.date: r.nav for r in nav_rows}
        earliest_nav = min(nav_map.keys())

        for strat in DEFAULT_STRATEGIES:
            brows = db.query(BreadthDaily).filter(BreadthDaily.metric == strat["metric"]).all()
            breadth_map = {r.date: r.count for r in brows}

            for period in periods:
                start = (_add_months(date.today(), -period["months"])
                         if period["months"] else date.fromisoformat(earliest_nav))
                sip_dates = _get_sip_dates(start, period["months"], 1)
                if not sip_dates:
                    continue
                sim = run_sim_core(nav_map, breadth_map, sip_dates, 10000,
                                   strat["multiplier"], strat["threshold"], 30)
                if not sim:
                    continue
                inc_xirr = (round(sim["enh_xirr"] - sim["reg_xirr"], 2)
                            if sim["enh_xirr"] is not None and sim["reg_xirr"] is not None else None)
                results.append({
                    "fund_code": fund["code"], "fund_name": fund["name"],
                    "category": fund["category"], "strategy_id": strat["id"],
                    "period_label": period["label"], "period_months": period["months"],
                    "regular_invested": sim["reg_invested"], "regular_value": sim["reg_value"],
                    "regular_xirr": sim["reg_xirr"], "enhanced_invested": sim["enh_invested"],
                    "enhanced_value": sim["enh_value"], "enhanced_xirr": sim["enh_xirr"],
                    "incremental_return_abs": sim["alpha_value"],
                    "incremental_return_pct": sim["alpha_pct"],
                    "incremental_xirr": inc_xirr,
                    "num_triggers": sim["num_triggers"], "cooloff_skips": sim["cooloff_skips"],
                    "total_sips": sim["total_sips"],
                })

    cache_data = {
        "success": True, "strategies": DEFAULT_STRATEGIES, "results": results,
        "errors": errors, "funds_count": len(TOP_FUNDS),
        "metrics": [{"key": m["key"], "label": m["label"]} for m in ALL_METRICS],
        "thresholds": STANDARD_THRESHOLDS,
    }
    existing = db.query(SimulatorCache).filter(SimulatorCache.cache_key == "batch_default").first()
    if existing:
        existing.data_json = json.dumps(cache_data)
        existing.computed_at = datetime.now()
    else:
        db.add(SimulatorCache(cache_key="batch_default", data_json=json.dumps(cache_data)))
    db.commit()
    logger.info("Batch: %d results, %d errors", len(results), len(errors))
    return True


def run_simulator_pipeline_sync():
    """Full pipeline for background thread (startup + EOD)."""
    db = SessionLocal()
    try:
        logger.info("Simulator pipeline starting...")
        aggregate_breadth(db)
        compute_threshold_flags(db)

        logger.info("Simulator pipeline: fetching MF NAV for %d funds...", len(TOP_FUND_CODES))
        loop = asyncio.new_event_loop()
        try:
            all_nav = loop.run_until_complete(fetch_all_nav_concurrent())
        finally:
            loop.close()
        store_nav_data(db, all_nav)

        precompute_batch(db)
        logger.info("Simulator pipeline: complete")
    except Exception as e:
        logger.error("Simulator pipeline failed: %s", e, exc_info=True)
        db.rollback()
    finally:
        db.close()
