"""
Compass Autonomous Trader
Fully autonomous paper trading engine that uses Lab-derived configs.

Runs at 3:40 PM IST daily. Reads regime-optimal parameters from Lab,
applies discovered rules, executes trades, logs every decision.

No human in the loop. Monitoring only.
"""

import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from index_constants import COMPASS_SECTOR_ETF_MAP, NSE_DISPLAY_MAP
from models import (
    CompassAction,
    CompassDecisionLog,
    CompassDiscoveredRule,
    CompassModelNAV,
    CompassModelState,
    CompassModelTrade,
    CompassQuadrant,
    CompassRegimeConfig,
    CompassVolumeSignal,
    IndexPrice,
    PortfolioNAV,
)

logger = logging.getLogger("fie_v3.compass.trader")

# Fallback defaults when Lab hasn't run yet
FALLBACK_CONFIG = {
    "stop_loss_pct": 8.0,
    "trailing_trigger_pct": 15.0,
    "trailing_stop_pct": 10.0,
    "max_positions": 6,
    "min_rs_entry": 0.0,
    "min_holding_days": 0,
    "rs_period": "3M",
}

PORTFOLIO_TYPES = ("etf_only", "stock_etf", "stock_only")
INITIAL_CAPITAL = Decimal("10000000")  # ₹1 Cr

# Tax config
STCG_RATE = 0.20
LTCG_RATE = 0.125
LTCG_EXEMPTION = 125000
STCG_HOLDING_DAYS = 365


def run_autonomous_rebalance(db: Session) -> dict:
    """
    Main entry point. Called by scheduler at 3:40 PM IST.
    Fully autonomous — reads Lab configs, makes decisions, executes trades.
    """
    from services.compass_rs import compute_sector_rs_scores, persist_rs_scores
    from services.compass_data import daily_refresh_compass_prices
    from routers.compass import _clear_cache

    today_str = datetime.now().strftime("%Y-%m-%d")
    logger.info("=== Autonomous Rebalance Starting: %s ===", today_str)

    # 1. Refresh prices
    daily_refresh_compass_prices(db)

    # 2. Compute RS scores
    scores = compute_sector_rs_scores(db, base_index="NIFTY", period_key="3M")
    persist_rs_scores(db, scores, instrument_type="index")
    _clear_cache()

    # 3. Detect market regime
    regime = _detect_current_regime(scores)
    logger.info("Current regime: %s", regime)

    # 4. Load Lab config for current regime
    config = _load_regime_config(db, regime)
    logger.info("Active config: %s (source: %s)", config["params"], config["source"])

    # 5. Load discovered rules
    active_rules = _load_active_rules(db)

    # 6. Run rebalance for all 3 portfolio types
    all_results = {}
    for pt in PORTFOLIO_TYPES:
        result = _rebalance_portfolio(
            db, scores, pt, config["params"], regime, active_rules, today_str,
        )
        all_results[pt] = result

    # 7. Update NAV
    nav_results = _update_all_navs(db)

    logger.info("=== Autonomous Rebalance Complete ===")
    return {
        "date": today_str,
        "regime": regime,
        "config_source": config["source"],
        "portfolios": all_results,
        "nav": nav_results,
    }


def _detect_current_regime(scores: list[dict]) -> str:
    """Detect regime from computed scores (already includes market_regime)."""
    if not scores:
        return "UNKNOWN"
    # All scores carry the same market_regime
    regime = scores[0].get("market_regime", "UNKNOWN")
    return regime if regime in ("BULL", "CAUTIOUS", "CORRECTION", "BEAR") else "BULL"


def _load_regime_config(db: Session, regime: str) -> dict:
    """Load Lab-derived config for current regime. Fallback to defaults."""
    config = db.query(CompassRegimeConfig).filter(
        CompassRegimeConfig.regime == regime
    ).first()

    if config:
        return {
            "params": {
                "stop_loss_pct": config.stop_loss_pct,
                "trailing_trigger_pct": config.trailing_trigger_pct,
                "trailing_stop_pct": config.trailing_stop_pct,
                "max_positions": config.max_positions,
                "min_rs_entry": config.min_rs_entry,
                "min_holding_days": config.min_holding_days,
                "rs_period": config.rs_period,
            },
            "source": f"lab_run_{config.lab_run_id}",
            "evidence": {
                "sharpe": config.evidence_sharpe,
                "win_rate": config.evidence_win_rate,
                "n_trades": config.evidence_n_trades,
            },
        }

    return {"params": dict(FALLBACK_CONFIG), "source": "fallback_defaults", "evidence": {}}


def _load_active_rules(db: Session) -> list[dict]:
    """Load all AUTO_APPLIED rules from Lab."""
    rules = db.query(CompassDiscoveredRule).filter(
        CompassDiscoveredRule.status == "AUTO_APPLIED"
    ).all()

    return [
        {
            "id": r.id,
            "condition": r.condition,
            "condition_json": json.loads(r.condition_json) if r.condition_json else {},
            "override_action": r.override_action,
            "confidence": r.confidence,
            "historical_n": r.historical_n,
            "historical_win_rate": r.historical_win_rate,
        }
        for r in rules
    ]


def _apply_rules(
    action: str, regime: str, sector_data: dict, rules: list[dict],
) -> tuple[str, str]:
    """Apply discovered rules to modify action. Returns (modified_action, rule_applied)."""
    for rule in rules:
        cond = rule.get("condition_json", {})
        rule_regime = cond.get("regime")

        if rule_regime and rule_regime != regime:
            continue

        override = rule["override_action"]

        if override == "BLOCK_BUY" and action == "BUY":
            vol = sector_data.get("volume_signal")
            rule_vol = cond.get("volume")
            if rule_vol and vol != rule_vol:
                continue
            return "HOLD", f"Rule #{rule['id']}: {rule['condition']}"

        if override == "REDUCE_POSITIONS":
            # Handled at portfolio level, not per-sector
            pass

    return action, ""


def _find_historical_precedent(
    db: Session, regime: str, action: str, sector_key: str,
) -> tuple[int, float]:
    """
    Find how many similar past decisions exist and their win rate.
    Returns (n_similar, win_rate).
    """
    similar = db.query(CompassDecisionLog).filter(
        CompassDecisionLog.market_regime == regime,
        CompassDecisionLog.decision == action,
        CompassDecisionLog.was_correct.isnot(None),
    ).all()

    if not similar:
        return 0, 0.0

    correct = sum(1 for d in similar if d.was_correct)
    return len(similar), round(correct / len(similar) * 100, 1)


def _rebalance_portfolio(
    db: Session,
    sector_scores: list[dict],
    portfolio_type: str,
    config: dict,
    regime: str,
    rules: list[dict],
    today_str: str,
) -> dict:
    """Rebalance a single portfolio type using Lab-derived config."""
    actions_taken = {"entries": [], "exits": [], "decisions_logged": 0}
    score_map = {s["sector_key"]: s for s in sector_scores}
    max_positions = config["max_positions"]

    # Check if any rule reduces max positions for this regime
    for rule in rules:
        cond = rule.get("condition_json", {})
        if cond.get("regime") == regime and rule["override_action"] == "REDUCE_POSITIONS":
            max_positions = min(max_positions, 4)
            logger.info("Rule reduces max_positions to %d for %s", max_positions, regime)
            break

    # ── Check exits ──────────────────────────────────────────
    open_positions = (
        db.query(CompassModelState)
        .filter(CompassModelState.status == "OPEN", CompassModelState.portfolio_type == portfolio_type)
        .all()
    )

    for pos in open_positions:
        sector_data = score_map.get(pos.sector_key, {})
        if not sector_data:
            continue

        should_exit = False
        exit_reason = ""
        action = sector_data.get("action", "")

        # Apply Lab rules
        action, rule_note = _apply_rules(action, regime, sector_data, rules)

        holding_days = _compute_holding_days(pos.entry_date)

        # Respect minimum holding days from Lab config
        if holding_days < config["min_holding_days"]:
            _log_decision(
                db, today_str, portfolio_type, pos.sector_key, "HOLD",
                sector_data, regime, f"lab_config_{regime}",
                f"Min hold {config['min_holding_days']}d not met ({holding_days}d held)",
            )
            actions_taken["decisions_logged"] += 1
            continue

        # Exit rule 1: SELL or AVOID signal
        if action in (CompassAction.SELL.value, CompassAction.AVOID.value, "SELL", "AVOID"):
            should_exit = True
            exit_reason = "SELL_SIGNAL"

        # Exit rule 2: stop-loss (Lab-derived threshold)
        if pos.current_price and pos.entry_price and pos.entry_price > 0:
            loss_pct = (1 - pos.current_price / pos.entry_price) * 100
            if loss_pct >= config["stop_loss_pct"]:
                should_exit = True
                exit_reason = f"STOP_LOSS ({loss_pct:.1f}% >= {config['stop_loss_pct']}%)"

        # Exit rule 3: trailing stop
        if pos.current_price and pos.trailing_stop and pos.current_price <= pos.trailing_stop:
            should_exit = True
            exit_reason = "TRAILING_STOP"

        if should_exit:
            _execute_exit(db, pos, exit_reason, sector_data, today_str, actions_taken, config)
            _log_decision(
                db, today_str, portfolio_type, pos.sector_key, "SELL",
                sector_data, regime, f"lab_config_{regime}",
                f"EXIT: {exit_reason}" + (f" | {rule_note}" if rule_note else ""),
            )
        else:
            _update_trailing_stop(pos, config)
            _log_decision(
                db, today_str, portfolio_type, pos.sector_key, "HOLD",
                sector_data, regime, f"lab_config_{regime}",
                f"Holding (day {holding_days})" + (f" | {rule_note}" if rule_note else ""),
            )

        actions_taken["decisions_logged"] += 1

    # ── Check entries ────────────────────────────────────────
    current_open = (
        db.query(CompassModelState)
        .filter(CompassModelState.status == "OPEN", CompassModelState.portfolio_type == portfolio_type)
        .count()
    )
    available_slots = max_positions - current_open

    held_sectors = {p.sector_key for p in open_positions if p.status == "OPEN"}

    for s in sector_scores:
        sector_key = s["sector_key"]
        if sector_key in held_sectors:
            continue

        action = s.get("action", "")
        rs = s.get("rs_score", 0)

        # Check RS threshold from Lab config
        if rs < config["min_rs_entry"]:
            _log_decision(
                db, today_str, portfolio_type, sector_key, "SKIP",
                s, regime, f"lab_config_{regime}",
                f"RS {rs:.1f} below min {config['min_rs_entry']}",
            )
            actions_taken["decisions_logged"] += 1
            continue

        # Apply rules
        action, rule_note = _apply_rules(action, regime, s, rules)

        is_buy = action in (CompassAction.BUY.value, "BUY")

        if is_buy and available_slots > 0:
            success = _execute_entry(
                db, s, portfolio_type, config, today_str, actions_taken,
            )
            if success:
                available_slots -= 1
                held_sectors.add(sector_key)

            # Find historical precedent
            prec_n, prec_wr = _find_historical_precedent(db, regime, "BUY", sector_key)

            _log_decision(
                db, today_str, portfolio_type, sector_key,
                "BUY" if success else "SKIP",
                s, regime, f"lab_config_{regime}",
                f"{'ENTRY' if success else 'NO_PRICE'}: RS={rs:.1f}, slots={available_slots}"
                + (f" | Precedent: {prec_n} similar, {prec_wr}% won" if prec_n > 0 else "")
                + (f" | {rule_note}" if rule_note else ""),
                historical_n=prec_n,
                historical_wr=prec_wr,
            )
        else:
            decision = "SKIP" if not is_buy else "SKIP"
            reason = f"Signal={action}, RS={rs:.1f}"
            if is_buy and available_slots <= 0:
                reason = f"BUY signal but no slots (max={max_positions})"
            _log_decision(
                db, today_str, portfolio_type, sector_key, decision,
                s, regime, f"lab_config_{regime}", reason,
            )

        actions_taken["decisions_logged"] += 1

    db.commit()
    logger.info(
        "[%s] Rebalance: %d entries, %d exits, %d decisions logged",
        portfolio_type, len(actions_taken["entries"]),
        len(actions_taken["exits"]), actions_taken["decisions_logged"],
    )
    return actions_taken


def _log_decision(
    db: Session,
    date: str,
    portfolio_type: str,
    sector_key: str,
    decision: str,
    sector_data: dict,
    regime: str,
    config_name: str,
    reason: str,
    historical_n: int = 0,
    historical_wr: float = 0.0,
) -> None:
    """Log a decision to the audit trail."""
    abs_ret = sector_data.get("absolute_return")
    rs = sector_data.get("rs_score", 0)
    mom = sector_data.get("rs_momentum", 0)

    db.add(CompassDecisionLog(
        date=date,
        portfolio_type=portfolio_type,
        sector_key=sector_key,
        decision=decision,
        gate_g1=(abs_ret or 0) > 0 if abs_ret is not None else None,
        gate_g2=rs > 0,
        gate_g3=mom > 0,
        rs_score=rs,
        momentum=mom,
        absolute_return=abs_ret,
        volume_signal=sector_data.get("volume_signal"),
        market_regime=regime,
        pe_ratio=sector_data.get("pe_ratio"),
        pe_zone=sector_data.get("pe_zone"),
        regime_config=config_name,
        reason_text=reason,
        historical_precedent_n=historical_n if historical_n > 0 else None,
        historical_precedent_win=historical_wr if historical_n > 0 else None,
    ))


def _execute_exit(
    db: Session, pos: CompassModelState, exit_reason: str,
    sector_data: dict, today_str: str, actions_taken: dict, config: dict,
) -> None:
    """Execute an exit trade with tax computation."""
    exit_price = pos.current_price or pos.entry_price
    pnl_pct = ((exit_price / pos.entry_price) - 1) * 100 if pos.entry_price > 0 else 0

    holding_days = _compute_holding_days(pos.entry_date)
    tax_type = "LTCG" if holding_days >= STCG_HOLDING_DAYS else "STCG"

    gain_amount = (exit_price - pos.entry_price) * (pos.quantity or 1)
    tax_impact = 0.0
    if gain_amount > 0:
        max_pos = config.get("max_positions", 6)
        if tax_type == "STCG":
            tax_impact = gain_amount * STCG_RATE
        else:
            taxable = max(0, gain_amount - LTCG_EXEMPTION / max_pos)
            tax_impact = taxable * LTCG_RATE

    pos.status = "CLOSED"
    pos.exit_date = today_str
    pos.exit_price = exit_price
    pos.exit_reason = exit_reason
    pos.pnl_pct = round(pnl_pct, 2)
    pos.holding_days = holding_days
    pos.tax_type = tax_type

    quadrant_val = sector_data.get("quadrant")
    if isinstance(quadrant_val, str):
        try:
            quadrant_val = CompassQuadrant(quadrant_val)
        except ValueError:
            quadrant_val = None

    db.add(CompassModelTrade(
        portfolio_type=pos.portfolio_type,
        trade_date=today_str,
        sector_key=pos.sector_key,
        instrument_id=pos.instrument_id,
        instrument_type=pos.instrument_type,
        side="SELL",
        price=exit_price,
        quantity=pos.quantity,
        value=exit_price * (pos.quantity or 1),
        reason=exit_reason,
        quadrant=quadrant_val,
        rs_score=sector_data.get("rs_score"),
        pnl_pct=round(pnl_pct, 2),
        tax_impact=round(tax_impact, 2),
    ))
    actions_taken["exits"].append({
        "sector": pos.sector_key,
        "reason": exit_reason,
        "pnl_pct": round(pnl_pct, 2),
    })


def _execute_entry(
    db: Session, candidate: dict, portfolio_type: str,
    config: dict, today_str: str, actions_taken: dict,
) -> bool:
    """Execute an entry trade. Returns True if successful."""
    sector_key = candidate["sector_key"]
    etfs = candidate.get("etfs", [])
    stop_pct = config["stop_loss_pct"]

    if portfolio_type == "etf_only":
        if not etfs:
            return False
        instrument_id = etfs[0]
        instrument_type = "etf"
    elif portfolio_type == "stock_only":
        instrument_id = sector_key
        instrument_type = "index"
    else:  # stock_etf
        if etfs:
            instrument_id = etfs[0]
            instrument_type = "etf"
        else:
            instrument_id = sector_key
            instrument_type = "index"

    entry_price = _get_latest_price(db, instrument_id, instrument_type)
    if not entry_price:
        logger.warning("No price for %s (%s), skipping entry", instrument_id, instrument_type)
        return False

    stop_loss = round(entry_price * (1 - stop_pct / 100), 2)
    max_pos = config.get("max_positions", 6)
    weight = round(100 / max_pos, 1)

    # Compute volatility for position sizing
    volatility = _compute_entry_volatility(db, sector_key)

    quadrant_val = candidate.get("quadrant")
    if isinstance(quadrant_val, str):
        try:
            quadrant_val = CompassQuadrant(quadrant_val)
        except ValueError:
            quadrant_val = None

    db.add(CompassModelState(
        portfolio_type=portfolio_type,
        sector_key=sector_key,
        instrument_id=instrument_id,
        instrument_type=instrument_type,
        entry_date=today_str,
        entry_price=entry_price,
        current_price=entry_price,
        quantity=1,
        weight_pct=weight,
        volatility=volatility,
        stop_loss=stop_loss,
        status="OPEN",
    ))

    db.add(CompassModelTrade(
        portfolio_type=portfolio_type,
        trade_date=today_str,
        sector_key=sector_key,
        instrument_id=instrument_id,
        instrument_type=instrument_type,
        side="BUY",
        price=entry_price,
        quantity=1,
        value=entry_price,
        reason=f"autonomous|regime={candidate.get('market_regime', 'UNKNOWN')}|RS={candidate.get('rs_score', 0):.1f}",
        quadrant=quadrant_val,
        rs_score=candidate.get("rs_score"),
    ))

    actions_taken["entries"].append({
        "sector": sector_key,
        "instrument": instrument_id,
        "price": entry_price,
        "stop_loss": stop_loss,
    })
    return True


def _update_trailing_stop(pos: CompassModelState, config: dict) -> None:
    """Update trailing stop using Lab-derived thresholds."""
    if not (pos.current_price and pos.entry_price and pos.entry_price > 0):
        return

    gain_pct = (pos.current_price / pos.entry_price - 1) * 100
    trigger = config.get("trailing_trigger_pct", 15.0)
    stop_pct = config.get("trailing_stop_pct", 10.0)

    if gain_pct >= trigger:
        highest = max(pos.highest_since or pos.current_price, pos.current_price)
        pos.highest_since = highest
        new_trailing = highest * (1 - stop_pct / 100)
        if pos.trailing_stop is None or new_trailing > pos.trailing_stop:
            pos.trailing_stop = round(new_trailing, 2)


def _compute_holding_days(entry_date_str: str) -> int:
    try:
        entry = datetime.strptime(entry_date_str, "%Y-%m-%d")
        return (datetime.now() - entry).days
    except (ValueError, TypeError):
        return 0


def _compute_entry_volatility(db: Session, sector_key: str) -> Optional[float]:
    """Compute annualized volatility at entry for position sizing."""
    from services.compass_rs import compute_annualized_volatility

    cutoff = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")
    rows = (
        db.query(IndexPrice.date, IndexPrice.close_price)
        .filter(IndexPrice.index_name == sector_key, IndexPrice.date >= cutoff)
        .order_by(IndexPrice.date)
        .all()
    )
    closes = {r.date: r.close_price for r in rows if r.close_price}
    return compute_annualized_volatility(closes) if closes else None


def _get_latest_price(db: Session, instrument_id: str, instrument_type: str) -> Optional[float]:
    """Get the most recent close price for an instrument."""
    from models import CompassETFPrice, CompassStockPrice

    if instrument_type == "etf":
        row = (
            db.query(CompassETFPrice)
            .filter(CompassETFPrice.ticker == instrument_id)
            .order_by(CompassETFPrice.date.desc())
            .first()
        )
        return row.close if row else None
    elif instrument_type == "stock":
        row = (
            db.query(CompassStockPrice)
            .filter(CompassStockPrice.ticker == instrument_id)
            .order_by(CompassStockPrice.date.desc())
            .first()
        )
        return row.close if row else None
    elif instrument_type == "index":
        row = (
            db.query(IndexPrice)
            .filter(IndexPrice.index_name == instrument_id)
            .order_by(IndexPrice.date.desc())
            .first()
        )
        return row.close_price if row else None
    return None


def _update_all_navs(db: Session) -> dict:
    """Compute and store today's NAV for all 3 portfolio types."""
    from services.compass_portfolio import _compute_nav_for_portfolio
    result = {}
    for pt in PORTFOLIO_TYPES:
        nav = _compute_nav_for_portfolio(db, pt)
        if nav:
            result[pt] = nav
    return result
