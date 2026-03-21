"""
Compass Lab — Monitoring API Endpoints
View Lab status, regime configs, discovered rules, decision log, experiments.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from models import (
    CompassDecisionLog,
    CompassDiscoveredRule,
    CompassLabRun,
    CompassRegimeConfig,
    get_db,
)

logger = logging.getLogger("fie_v3.compass.lab.api")

router = APIRouter(prefix="/api/compass/lab", tags=["compass-lab"])


@router.get("/status")
def get_lab_status():
    """Get current Lab daemon status."""
    from services.compass_lab import get_lab_status
    from services.compass_history import get_data_summary

    status = get_lab_status()
    data_summary = get_data_summary()
    return {**status, "historical_data": data_summary}


@router.get("/runs")
def get_lab_runs(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Get recent Lab sweep runs."""
    runs = (
        db.query(CompassLabRun)
        .order_by(CompassLabRun.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "run_type": r.run_type,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "combos_tested": r.combos_tested,
            "best_sharpe": r.best_sharpe,
            "data_range": f"{r.data_start} to {r.data_end}" if r.data_start else None,
            "notes": r.notes,
        }
        for r in runs
    ]


@router.get("/configs")
def get_regime_configs(db: Session = Depends(get_db)):
    """Get current Lab-derived regime configs."""
    configs = db.query(CompassRegimeConfig).all()

    if not configs:
        return {"status": "no_configs", "message": "Lab hasn't run yet. Configs will be generated after first sweep."}

    return [
        {
            "regime": c.regime,
            "params": {
                "stop_loss_pct": c.stop_loss_pct,
                "trailing_trigger_pct": c.trailing_trigger_pct,
                "trailing_stop_pct": c.trailing_stop_pct,
                "max_positions": c.max_positions,
                "min_rs_entry": c.min_rs_entry,
                "min_holding_days": c.min_holding_days,
                "rs_period": c.rs_period,
            },
            "evidence": {
                "sharpe": c.evidence_sharpe,
                "win_rate": c.evidence_win_rate,
                "n_trades": c.evidence_n_trades,
                "max_drawdown": c.evidence_max_dd,
            },
            "lab_run_id": c.lab_run_id,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in configs
    ]


@router.get("/rules")
def get_discovered_rules(
    status: Optional[str] = Query(None, description="Filter by status: AUTO_APPLIED, MONITORING, REJECTED"),
    db: Session = Depends(get_db),
):
    """Get discovered trading rules."""
    query = db.query(CompassDiscoveredRule)
    if status:
        query = query.filter(CompassDiscoveredRule.status == status)

    rules = query.order_by(CompassDiscoveredRule.id.desc()).all()
    return [
        {
            "id": r.id,
            "discovered_date": r.discovered_date,
            "condition": r.condition,
            "historical_n": r.historical_n,
            "historical_win_rate": r.historical_win_rate,
            "baseline_win_rate": r.baseline_win_rate,
            "override_action": r.override_action,
            "confidence": r.confidence,
            "status": r.status,
            "live_trades_since": r.live_trades_since,
            "live_win_rate": r.live_win_rate,
        }
        for r in rules
    ]


@router.post("/rules/{rule_id}/apply")
def apply_rule(rule_id: int, db: Session = Depends(get_db)):
    """Manually apply a discovered rule."""
    rule = db.query(CompassDiscoveredRule).filter(CompassDiscoveredRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "Rule not found")

    from datetime import datetime
    rule.status = "AUTO_APPLIED"
    rule.applied_date = datetime.now().strftime("%Y-%m-%d")
    db.commit()
    return {"status": "applied", "rule_id": rule_id}


@router.post("/rules/{rule_id}/reject")
def reject_rule(rule_id: int, db: Session = Depends(get_db)):
    """Reject a discovered rule."""
    rule = db.query(CompassDiscoveredRule).filter(CompassDiscoveredRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "Rule not found")

    rule.status = "REJECTED"
    db.commit()
    return {"status": "rejected", "rule_id": rule_id}


@router.get("/decisions")
def get_decision_log(
    portfolio_type: str = Query("etf_only"),
    limit: int = Query(50, ge=1, le=200),
    sector_key: Optional[str] = Query(None),
    decision: Optional[str] = Query(None, description="BUY, SELL, HOLD, SKIP"),
    db: Session = Depends(get_db),
):
    """Get autonomous trader decision log."""
    query = db.query(CompassDecisionLog).filter(
        CompassDecisionLog.portfolio_type == portfolio_type
    )
    if sector_key:
        query = query.filter(CompassDecisionLog.sector_key == sector_key)
    if decision:
        query = query.filter(CompassDecisionLog.decision == decision)

    decisions = query.order_by(CompassDecisionLog.id.desc()).limit(limit).all()
    return [
        {
            "id": d.id,
            "date": d.date,
            "sector_key": d.sector_key,
            "decision": d.decision,
            "gates": {"g1": d.gate_g1, "g2": d.gate_g2, "g3": d.gate_g3},
            "rs_score": d.rs_score,
            "momentum": d.momentum,
            "absolute_return": d.absolute_return,
            "volume_signal": d.volume_signal,
            "market_regime": d.market_regime,
            "pe_ratio": d.pe_ratio,
            "regime_config": d.regime_config,
            "reason": d.reason_text,
            "historical_precedent": {
                "n": d.historical_precedent_n,
                "win_rate": d.historical_precedent_win,
            } if d.historical_precedent_n else None,
            "outcomes": {
                "5d": d.outcome_5d_return,
                "20d": d.outcome_20d_return,
                "60d": d.outcome_60d_return,
                "was_correct": d.was_correct,
            },
        }
        for d in decisions
    ]


@router.get("/decisions/accuracy")
def get_decision_accuracy(
    portfolio_type: str = Query("etf_only"),
    db: Session = Depends(get_db),
):
    """Get decision accuracy stats — how often is the autonomous trader correct?"""
    all_decisions = db.query(CompassDecisionLog).filter(
        CompassDecisionLog.portfolio_type == portfolio_type,
        CompassDecisionLog.was_correct.isnot(None),
    ).all()

    if not all_decisions:
        return {"status": "no_data", "message": "No decisions with outcomes yet"}

    total = len(all_decisions)
    correct = sum(1 for d in all_decisions if d.was_correct)

    # Per-decision-type accuracy
    by_decision = {}
    for d in all_decisions:
        if d.decision not in by_decision:
            by_decision[d.decision] = {"total": 0, "correct": 0}
        by_decision[d.decision]["total"] += 1
        if d.was_correct:
            by_decision[d.decision]["correct"] += 1

    # Per-regime accuracy
    by_regime = {}
    for d in all_decisions:
        regime = d.market_regime or "UNKNOWN"
        if regime not in by_regime:
            by_regime[regime] = {"total": 0, "correct": 0}
        by_regime[regime]["total"] += 1
        if d.was_correct:
            by_regime[regime]["correct"] += 1

    return {
        "overall_accuracy": round(correct / total * 100, 1),
        "total_decisions": total,
        "correct_decisions": correct,
        "by_decision": {
            k: {**v, "accuracy": round(v["correct"] / v["total"] * 100, 1)}
            for k, v in by_decision.items()
        },
        "by_regime": {
            k: {**v, "accuracy": round(v["correct"] / v["total"] * 100, 1)}
            for k, v in by_regime.items()
        },
    }


@router.post("/sweep/trigger")
def trigger_sweep(
    sweep_type: str = Query("focused", description="full or focused"),
    db: Session = Depends(get_db),
):
    """Manually trigger a Lab sweep."""
    import threading
    from services.compass_lab import run_focused_sweep, run_full_lab_sweep

    def _run_in_bg():
        from models import SessionLocal
        bg_db = SessionLocal()
        try:
            if sweep_type == "full":
                run_full_lab_sweep(bg_db)
            else:
                run_focused_sweep(bg_db)
        finally:
            bg_db.close()

    t = threading.Thread(target=_run_in_bg, daemon=True, name="manual-sweep")
    t.start()
    return {"status": "started", "sweep_type": sweep_type}


@router.post("/backfill-history")
def trigger_history_backfill():
    """Trigger historical price data download for Lab simulations."""
    import threading

    def _download():
        from services.compass_history import download_historical_prices, save_historical_data
        data = download_historical_prices()
        if data:
            save_historical_data(data)

    t = threading.Thread(target=_download, daemon=True, name="history-backfill")
    t.start()
    return {"status": "started", "message": "Downloading 20+ years of historical prices..."}
