"""
Compass Lab — Simulation Sweep Orchestrator
Runs thousands of parameter combinations against historical data,
extracts regime-optimal configs and conditional rules.

Runs as a background daemon: full sweeps every 6 hours, focused sweeps hourly.
"""

import json
import logging
import threading
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
from sqlalchemy.orm import Session

from models import (
    CompassDecisionLog,
    CompassDiscoveredRule,
    CompassLabRun,
    CompassRegimeConfig,
    get_db,
)
from services.compass_simulator import (
    REGIME_NAMES,
    SimParams,
    SimResult,
    generate_focused_grid,
    generate_param_grid,
    simulate,
)

logger = logging.getLogger("fie_v3.compass.lab")

# ─── Lab State ───────────────────────────────────────────────

_lab_thread: Optional[threading.Thread] = None
_lab_running = False
_lab_status = {
    "running": False,
    "last_sweep": None,
    "last_sweep_type": None,
    "combos_tested_total": 0,
    "active_regime_configs": {},
    "discovered_rules_count": 0,
    "next_sweep": None,
}
_lab_lock = threading.Lock()


def get_lab_status() -> dict:
    with _lab_lock:
        return dict(_lab_status)


# ─── Worker function (runs in subprocess) ────────────────────

def _run_single_simulation(args: tuple) -> dict:
    """Worker function for ProcessPoolExecutor. Must be top-level for pickling."""
    prices, benchmark, sector_keys, params_dict = args
    params = SimParams(**params_dict)
    result = simulate(prices, benchmark, sector_keys, params)
    return result.to_dict()


# ─── Sweep Runner ────────────────────────────────────────────

def run_sweep(
    prices: np.ndarray,
    benchmark: np.ndarray,
    sector_keys: list[str],
    param_grid: list[SimParams],
    max_workers: int = 2,
    batch_size: int = 100,
) -> list[dict]:
    """
    Run simulation sweep across all parameter combinations.
    Uses ProcessPoolExecutor for parallelism.

    Returns list of SimResult dicts sorted by Sortino ratio.
    """
    total = len(param_grid)
    logger.info("Starting sweep: %d combinations, %d workers", total, max_workers)

    results = []
    start_time = time.time()

    # Prepare args — pass params as dicts for pickling
    all_args = [
        (prices, benchmark, sector_keys, p.to_dict())
        for p in param_grid
    ]

    # Process in batches to manage memory
    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch_args = all_args[batch_start:batch_end]

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_run_single_simulation, args): i for i, args in enumerate(batch_args)}
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                except Exception as e:
                    logger.warning("Simulation failed: %s", e)

        elapsed = time.time() - start_time
        done = len(results)
        rate = done / elapsed if elapsed > 0 else 0
        remaining = (total - done) / rate if rate > 0 else 0
        logger.info(
            "Sweep progress: %d/%d (%.0f/s, ~%.0f min remaining)",
            done, total, rate, remaining / 60,
        )

    # Sort by Sortino ratio (best risk-adjusted returns first)
    results.sort(key=lambda x: x.get("sortino", 0), reverse=True)

    elapsed = time.time() - start_time
    logger.info(
        "Sweep complete: %d results in %.1f min (%.1f sims/sec)",
        len(results), elapsed / 60, len(results) / elapsed if elapsed > 0 else 0,
    )
    return results


# ─── Regime Config Extraction ────────────────────────────────

def extract_regime_configs(results: list[dict]) -> dict[str, dict]:
    """
    From sweep results, find the best parameter set for each market regime.
    Returns {regime_name: {params, evidence}}.
    """
    regime_best: dict[str, dict] = {}

    for regime_name in REGIME_NAMES.values():
        # Find results where this regime had enough trades
        candidates = []
        for r in results:
            rm = r.get("regime_metrics", {}).get(regime_name, {})
            n_trades = rm.get("n_trades", 0)
            if n_trades >= 10:  # need at least 10 trades in this regime
                candidates.append({
                    "params": r["params"],
                    "sortino": rm.get("sortino", 0),
                    "sharpe": rm.get("sharpe", 0),
                    "win_rate": rm.get("win_rate", 0),
                    "max_drawdown": r.get("max_drawdown", 0),
                    "n_trades": n_trades,
                    "avg_gain": rm.get("avg_gain", 0),
                    "avg_loss": rm.get("avg_loss", 0),
                })

        if not candidates:
            continue

        # Sort by Sortino within this regime
        candidates.sort(key=lambda x: x["sortino"], reverse=True)
        best = candidates[0]

        regime_best[regime_name] = {
            "params": best["params"],
            "evidence": {
                "sortino": best["sortino"],
                "sharpe": best["sharpe"],
                "win_rate": best["win_rate"],
                "max_drawdown": best["max_drawdown"],
                "n_trades": best["n_trades"],
            },
        }
        logger.info(
            "Best config for %s: Sortino=%.2f, WinRate=%.0f%%, n=%d | params=%s",
            regime_name, best["sortino"], best["win_rate"],
            best["n_trades"], best["params"],
        )

    return regime_best


def persist_regime_configs(db: Session, regime_configs: dict, lab_run_id: int) -> None:
    """Write regime-optimal configs to DB."""
    for regime_name, config in regime_configs.items():
        params = config["params"]
        evidence = config["evidence"]

        existing = db.query(CompassRegimeConfig).filter(
            CompassRegimeConfig.regime == regime_name
        ).first()

        values = {
            "regime": regime_name,
            "stop_loss_pct": params["stop_loss_pct"],
            "trailing_trigger_pct": params["trailing_trigger_pct"],
            "trailing_stop_pct": params["trailing_stop_pct"],
            "max_positions": params["max_positions"],
            "min_rs_entry": params["min_rs_entry"],
            "min_holding_days": params["min_holding_days"],
            "rs_period": params["rs_period"],
            "evidence_sharpe": evidence["sharpe"],
            "evidence_n_trades": evidence["n_trades"],
            "evidence_win_rate": evidence["win_rate"],
            "evidence_max_dd": evidence["max_drawdown"],
            "lab_run_id": lab_run_id,
        }

        if existing:
            for k, v in values.items():
                setattr(existing, k, v)
        else:
            db.add(CompassRegimeConfig(**values))

    db.commit()
    logger.info("Persisted %d regime configs", len(regime_configs))


# ─── Rule Discovery ─────────────────────────────────────────

def discover_rules(results: list[dict]) -> list[dict]:
    """
    Analyze simulation results to discover conditional rules.
    Groups trades by (regime × parameter pattern) and finds
    conditions where win rate deviates significantly from baseline.
    """
    # Collect all trade outcomes across top-performing parameter sets
    # We only analyze top 100 results to focus on viable strategies
    top_results = results[:min(100, len(results))]
    if not top_results:
        return []

    # Compute baseline metrics from overall best result
    baseline = top_results[0]
    baseline_win = baseline.get("win_rate", 50)

    discovered = []

    # Rule 1: Regime-specific stop-loss effectiveness
    for regime_name in REGIME_NAMES.values():
        regime_results = []
        for r in top_results:
            rm = r.get("regime_metrics", {}).get(regime_name, {})
            if rm.get("n_trades", 0) >= 5:
                regime_results.append({
                    "params": r["params"],
                    "win_rate": rm["win_rate"],
                    "n_trades": rm["n_trades"],
                    "sortino": rm.get("sortino", 0),
                })

        if len(regime_results) < 5:
            continue

        # Find if tight stops work better in this regime
        tight_stop = [r for r in regime_results if r["params"]["stop_loss_pct"] <= 6]
        wide_stop = [r for r in regime_results if r["params"]["stop_loss_pct"] >= 12]

        if tight_stop and wide_stop:
            tight_wr = np.mean([r["win_rate"] for r in tight_stop])
            wide_wr = np.mean([r["win_rate"] for r in wide_stop])
            n_tight = sum(r["n_trades"] for r in tight_stop)
            n_wide = sum(r["n_trades"] for r in wide_stop)

            if abs(tight_wr - wide_wr) > 10 and min(n_tight, n_wide) >= 30:
                better = "tight" if tight_wr > wide_wr else "wide"
                discovered.append({
                    "condition": f"regime={regime_name} AND stop_loss={'<=6' if better == 'tight' else '>=12'}",
                    "condition_json": json.dumps({
                        "regime": regime_name,
                        "stop_loss_preference": better,
                    }),
                    "historical_n": n_tight if better == "tight" else n_wide,
                    "historical_win_rate": round(tight_wr if better == "tight" else wide_wr, 1),
                    "baseline_win_rate": round(baseline_win, 1),
                    "override_action": f"USE_{better.upper()}_STOPS",
                    "confidence": "HIGH" if min(n_tight, n_wide) >= 50 else "MEDIUM",
                })

        # Find if fewer positions work better in volatile regimes
        few_pos = [r for r in regime_results if r["params"]["max_positions"] <= 4]
        many_pos = [r for r in regime_results if r["params"]["max_positions"] >= 6]

        if few_pos and many_pos:
            few_sortino = np.mean([r["sortino"] for r in few_pos])
            many_sortino = np.mean([r["sortino"] for r in many_pos])

            if few_sortino > many_sortino * 1.3:
                discovered.append({
                    "condition": f"regime={regime_name} AND max_positions<=4",
                    "condition_json": json.dumps({
                        "regime": regime_name,
                        "max_positions_preference": "fewer",
                    }),
                    "historical_n": sum(r["n_trades"] for r in few_pos),
                    "historical_win_rate": round(np.mean([r["win_rate"] for r in few_pos]), 1),
                    "baseline_win_rate": round(baseline_win, 1),
                    "override_action": "REDUCE_POSITIONS",
                    "confidence": "MEDIUM",
                })

    # Rule 2: RS period effectiveness by regime
    for regime_name in REGIME_NAMES.values():
        period_stats: dict[str, list] = {}
        for r in top_results:
            rm = r.get("regime_metrics", {}).get(regime_name, {})
            if rm.get("n_trades", 0) >= 5:
                period = r["params"]["rs_period"]
                if period not in period_stats:
                    period_stats[period] = []
                period_stats[period].append(rm.get("sortino", 0))

        if len(period_stats) >= 2:
            best_period = max(period_stats.keys(), key=lambda p: np.mean(period_stats[p]))
            best_sortino = np.mean(period_stats[best_period])
            other_sortinos = [np.mean(v) for k, v in period_stats.items() if k != best_period]
            avg_other = np.mean(other_sortinos) if other_sortinos else 0

            if best_sortino > avg_other * 1.3 and best_sortino > 0.3:
                discovered.append({
                    "condition": f"regime={regime_name} AND rs_period={best_period}",
                    "condition_json": json.dumps({
                        "regime": regime_name,
                        "optimal_rs_period": best_period,
                    }),
                    "historical_n": sum(len(v) for v in period_stats.values()),
                    "historical_win_rate": round(best_sortino * 20 + 50, 1),  # approximate
                    "baseline_win_rate": round(baseline_win, 1),
                    "override_action": f"USE_{best_period}_LOOKBACK",
                    "confidence": "MEDIUM",
                })

    logger.info("Discovered %d rules from simulation data", len(discovered))
    return discovered


def persist_discovered_rules(db: Session, rules: list[dict], lab_run_id: int) -> None:
    """Write discovered rules to DB. Skip duplicates."""
    today = datetime.now().strftime("%Y-%m-%d")
    added = 0

    for rule in rules:
        # Check for existing rule with same condition
        existing = db.query(CompassDiscoveredRule).filter(
            CompassDiscoveredRule.condition == rule["condition"]
        ).first()

        if existing:
            # Update evidence
            existing.historical_n = rule["historical_n"]
            existing.historical_win_rate = rule["historical_win_rate"]
            existing.lab_run_id = lab_run_id
        else:
            db.add(CompassDiscoveredRule(
                discovered_date=today,
                condition=rule["condition"],
                condition_json=rule.get("condition_json"),
                historical_n=rule["historical_n"],
                historical_win_rate=rule["historical_win_rate"],
                baseline_win_rate=rule["baseline_win_rate"],
                override_action=rule["override_action"],
                confidence=rule["confidence"],
                status="AUTO_APPLIED" if rule["confidence"] == "HIGH" and rule["historical_n"] >= 30 else "MONITORING",
                lab_run_id=lab_run_id,
            ))
            added += 1

    db.commit()
    logger.info("Persisted rules: %d new, %d updated", added, len(rules) - added)


# ─── Full Lab Run ────────────────────────────────────────────

def run_full_lab_sweep(db: Session) -> dict:
    """
    Execute a full Lab sweep: download/load data, run simulations,
    extract configs, discover rules.
    """
    from services.compass_history import load_historical_data, update_historical_data

    # Load or download historical data
    data = load_historical_data()
    if data is None:
        logger.info("No cached data, downloading historical prices...")
        data = update_historical_data()
    if not data:
        return {"status": "error", "message": "No historical data available"}

    prices = data["prices"]
    benchmark = data["benchmark"]
    sector_keys = data["sector_keys"]

    # Record Lab run
    lab_run = CompassLabRun(
        run_type="FULL",
        status="RUNNING",
        data_start=data["dates"][0],
        data_end=data["dates"][-1],
    )
    db.add(lab_run)
    db.commit()

    try:
        # Generate parameter grid
        param_grid = generate_param_grid()

        # For first run or small server, use reduced grid
        # Full grid: 76,800 combos. Reduced: ~3,200 (skip some combos)
        if len(param_grid) > 10000:
            # Sample strategically: keep all rs_period × stop_loss × max_positions combos
            # but reduce trailing/holding variations
            reduced = []
            for p in param_grid:
                d = p.to_dict()
                # Keep every 4th trailing combo, every 2nd holding combo
                t_hash = hash((d["trailing_trigger_pct"], d["trailing_stop_pct"])) % 4
                h_hash = hash(d["min_holding_days"]) % 2
                if t_hash == 0 and h_hash == 0:
                    reduced.append(p)
            if reduced:
                param_grid = reduced
            logger.info("Reduced grid from 76800 to %d combos", len(param_grid))

        # Run sweep
        results = run_sweep(prices, benchmark, sector_keys, param_grid, max_workers=2)

        # Extract regime configs
        regime_configs = extract_regime_configs(results)
        if regime_configs:
            persist_regime_configs(db, regime_configs, lab_run.id)

        # Discover rules
        rules = discover_rules(results)
        if rules:
            persist_discovered_rules(db, rules, lab_run.id)

        # Update Lab run record
        lab_run.status = "COMPLETED"
        lab_run.completed_at = datetime.now()
        lab_run.combos_tested = len(results)
        lab_run.best_sharpe = results[0]["sharpe"] if results else None
        db.commit()

        # Update status
        with _lab_lock:
            _lab_status["last_sweep"] = datetime.now().isoformat()
            _lab_status["last_sweep_type"] = "FULL"
            _lab_status["combos_tested_total"] += len(results)
            _lab_status["active_regime_configs"] = {
                k: v["params"] for k, v in regime_configs.items()
            }
            _lab_status["discovered_rules_count"] = db.query(CompassDiscoveredRule).count()

        return {
            "status": "completed",
            "combos_tested": len(results),
            "regime_configs": {k: v["evidence"] for k, v in regime_configs.items()},
            "rules_discovered": len(rules),
            "best_sharpe": results[0]["sharpe"] if results else None,
            "data_range": f"{data['dates'][0]} to {data['dates'][-1]}",
        }

    except Exception as e:
        lab_run.status = "FAILED"
        lab_run.notes = str(e)[:500]
        db.commit()
        logger.error("Lab sweep failed: %s", e, exc_info=True)
        return {"status": "error", "message": str(e)}


def run_focused_sweep(db: Session) -> dict:
    """
    Run focused sweep around current best configs (hill-climbing).
    Much faster than full sweep — tests ~500 combos.
    """
    from services.compass_history import load_historical_data

    data = load_historical_data()
    if not data:
        return {"status": "error", "message": "No historical data"}

    # Load current best configs
    configs = db.query(CompassRegimeConfig).all()
    if not configs:
        logger.info("No existing configs, running full sweep instead")
        return run_full_lab_sweep(db)

    prices = data["prices"]
    benchmark = data["benchmark"]
    sector_keys = data["sector_keys"]

    lab_run = CompassLabRun(run_type="FOCUSED", status="RUNNING",
                            data_start=data["dates"][0], data_end=data["dates"][-1])
    db.add(lab_run)
    db.commit()

    try:
        # Generate focused grid around each regime's best config
        all_params = []
        for config in configs:
            base = SimParams(
                rs_period=config.rs_period,
                stop_loss_pct=config.stop_loss_pct,
                trailing_trigger_pct=config.trailing_trigger_pct,
                trailing_stop_pct=config.trailing_stop_pct,
                max_positions=config.max_positions,
                min_rs_entry=config.min_rs_entry,
                min_holding_days=config.min_holding_days,
            )
            focused = generate_focused_grid(base, variation=1)
            all_params.extend(focused)

        # Deduplicate by param hash
        seen = set()
        unique_params = []
        for p in all_params:
            h = p.param_hash()
            if h not in seen:
                seen.add(h)
                unique_params.append(p)

        results = run_sweep(prices, benchmark, sector_keys, unique_params, max_workers=2)

        regime_configs = extract_regime_configs(results)
        if regime_configs:
            persist_regime_configs(db, regime_configs, lab_run.id)

        lab_run.status = "COMPLETED"
        lab_run.completed_at = datetime.now()
        lab_run.combos_tested = len(results)
        db.commit()

        with _lab_lock:
            _lab_status["last_sweep"] = datetime.now().isoformat()
            _lab_status["last_sweep_type"] = "FOCUSED"
            _lab_status["combos_tested_total"] += len(results)

        return {
            "status": "completed",
            "combos_tested": len(results),
            "type": "focused",
        }

    except Exception as e:
        lab_run.status = "FAILED"
        lab_run.notes = str(e)[:500]
        db.commit()
        logger.error("Focused sweep failed: %s", e, exc_info=True)
        return {"status": "error", "message": str(e)}


# ─── Background Daemon ───────────────────────────────────────

def _lab_daemon_loop() -> None:
    """Background loop: full sweep every 6h, focused every 1h."""
    global _lab_running
    from models import SessionLocal

    FULL_SWEEP_INTERVAL = 6 * 3600    # 6 hours
    FOCUSED_SWEEP_INTERVAL = 3600     # 1 hour
    last_full = 0
    last_focused = 0

    logger.info("Lab daemon started")

    while _lab_running:
        now = time.time()

        try:
            db = SessionLocal()

            if now - last_full >= FULL_SWEEP_INTERVAL:
                logger.info("Starting scheduled full sweep...")
                with _lab_lock:
                    _lab_status["running"] = True
                result = run_full_lab_sweep(db)
                logger.info("Full sweep result: %s", result.get("status"))
                last_full = time.time()
                last_focused = time.time()  # reset focused timer too

            elif now - last_focused >= FOCUSED_SWEEP_INTERVAL:
                logger.info("Starting scheduled focused sweep...")
                with _lab_lock:
                    _lab_status["running"] = True
                result = run_focused_sweep(db)
                logger.info("Focused sweep result: %s", result.get("status"))
                last_focused = time.time()

            db.close()

        except Exception as e:
            logger.error("Lab daemon error: %s", e, exc_info=True)

        with _lab_lock:
            _lab_status["running"] = False
            next_focused = last_focused + FOCUSED_SWEEP_INTERVAL
            next_full = last_full + FULL_SWEEP_INTERVAL
            _lab_status["next_sweep"] = datetime.fromtimestamp(
                min(next_focused, next_full)
            ).isoformat()

        # Sleep in short intervals so we can stop cleanly
        for _ in range(60):  # check every second for 60 seconds
            if not _lab_running:
                break
            time.sleep(1)

    logger.info("Lab daemon stopped")


def start_lab_daemon() -> None:
    """Start the Lab background daemon thread."""
    global _lab_thread, _lab_running

    if _lab_thread and _lab_thread.is_alive():
        logger.info("Lab daemon already running")
        return

    _lab_running = True
    _lab_thread = threading.Thread(target=_lab_daemon_loop, daemon=True, name="compass-lab")
    _lab_thread.start()
    logger.info("Lab daemon thread started")


def stop_lab_daemon() -> None:
    """Stop the Lab background daemon."""
    global _lab_running
    _lab_running = False
    logger.info("Lab daemon stop requested")


# ─── Outcome Backfill (nightly job) ─────────────────────────

def backfill_decision_outcomes(db: Session) -> int:
    """
    Backfill outcome columns on DecisionLog entries.
    Checks 5d, 20d, 60d returns for past decisions.
    """
    from models import IndexPrice

    # Find decisions missing outcomes that are old enough
    pending = db.query(CompassDecisionLog).filter(
        CompassDecisionLog.outcome_5d_return.is_(None),
    ).all()

    updated = 0
    today = datetime.now()

    for decision in pending:
        decision_date = datetime.strptime(decision.date, "%Y-%m-%d")
        days_since = (today - decision_date).days

        if days_since < 5:
            continue

        # Get price on decision date and future dates
        prices = db.query(IndexPrice.date, IndexPrice.close_price).filter(
            IndexPrice.index_name == decision.sector_key,
            IndexPrice.date >= decision.date,
        ).order_by(IndexPrice.date).all()

        if len(prices) < 2:
            continue

        price_map = {p.date: p.close_price for p in prices if p.close_price}
        base_price = price_map.get(decision.date)
        if not base_price or base_price <= 0:
            continue

        dates_sorted = sorted(price_map.keys())
        def _get_return_at_offset(offset_days: int) -> Optional[float]:
            target = (decision_date + timedelta(days=offset_days)).strftime("%Y-%m-%d")
            # Find closest date
            for d in dates_sorted:
                if d >= target:
                    p = price_map.get(d)
                    if p and p > 0:
                        return round((p / base_price - 1) * 100, 2)
                    break
            return None

        if days_since >= 5:
            decision.outcome_5d_return = _get_return_at_offset(5)
        if days_since >= 20:
            decision.outcome_20d_return = _get_return_at_offset(20)
        if days_since >= 60:
            decision.outcome_60d_return = _get_return_at_offset(60)

        # Was decision correct?
        if decision.outcome_20d_return is not None:
            if decision.decision in ("BUY",):
                decision.was_correct = decision.outcome_20d_return > 0
            elif decision.decision in ("SELL", "AVOID"):
                decision.was_correct = decision.outcome_20d_return <= 0
            elif decision.decision in ("HOLD", "SKIP"):
                decision.was_correct = True  # neutral decisions are always "correct"

        updated += 1

    if updated:
        db.commit()
    logger.info("Backfilled outcomes for %d decisions", updated)
    return updated
