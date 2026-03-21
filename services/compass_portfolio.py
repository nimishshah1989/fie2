"""
Sector Compass — Model Portfolio Engine
Autonomous paper trading based on RS signals.

3 Model Portfolios:
- ETF-only: trades sector ETFs (liquid, low cost)
- Stock+ETF blend: mixes top stocks from leading sectors + ETFs
- Stock-only: trades top constituent stocks from leading sectors

Rules:
- ENTRY: Sector RS Score > 0 + BUY/ACCUMULATE signal
- EXIT: Sector drops to LAGGING, or WEAKENING+DISTRIBUTION, or stop-loss
- Position sizing: inverse volatility (lower vol = bigger position)
- Tax awareness: prefer exiting LTCG positions over STCG when possible
- Risk: 8% sector stop, 12% stock stop, trailing stop after 15% gain
"""

import logging
import math
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from index_constants import COMPASS_SECTOR_ETF_MAP, NSE_DISPLAY_MAP
from models import (
    CompassAction,
    CompassModelNAV,
    CompassModelState,
    CompassModelTrade,
    CompassQuadrant,
    CompassVolumeSignal,
    IndexPrice,
    PortfolioNAV,
)

logger = logging.getLogger("fie_v3.compass.portfolio")

# Portfolio config
PORTFOLIO_TYPES = ("etf_only", "stock_etf", "stock_only")
INITIAL_CAPITAL = Decimal("10000000")  # ₹1 Cr per portfolio
MAX_POSITIONS = 6
SECTOR_STOP_LOSS_PCT = 8.0
STOCK_STOP_LOSS_PCT = 12.0
TRAILING_TRIGGER_PCT = 15.0
TRAILING_STOP_PCT = 10.0

# Tax config (India)
STCG_RATE = 0.20   # 20% for < 1 year
LTCG_RATE = 0.125  # 12.5% for >= 1 year (on gains above ₹1.25L exemption)
LTCG_EXEMPTION = 125000  # ₹1.25 lakh exemption per year
STCG_HOLDING_DAYS = 365  # < 365 days = short term


def get_model_portfolio_state(db: Session, portfolio_type: str = "etf_only") -> dict:
    """Get current model portfolio positions and metrics."""
    open_positions = (
        db.query(CompassModelState)
        .filter(CompassModelState.status == "OPEN", CompassModelState.portfolio_type == portfolio_type)
        .all()
    )

    latest_nav = (
        db.query(CompassModelNAV)
        .filter(CompassModelNAV.portfolio_type == portfolio_type)
        .order_by(CompassModelNAV.date.desc())
        .first()
    )

    positions = []
    for p in open_positions:
        pnl_pct = None
        if p.entry_price and p.current_price and p.entry_price > 0:
            pnl_pct = round((p.current_price / p.entry_price - 1) * 100, 2)
        holding_days = _compute_holding_days(p.entry_date)
        tax_type = "LTCG" if holding_days >= STCG_HOLDING_DAYS else "STCG"
        positions.append({
            "sector_key": p.sector_key,
            "sector_name": NSE_DISPLAY_MAP.get(p.sector_key, p.sector_key),
            "instrument_id": p.instrument_id,
            "instrument_type": p.instrument_type,
            "entry_date": p.entry_date,
            "entry_price": p.entry_price,
            "current_price": p.current_price,
            "weight_pct": p.weight_pct,
            "volatility": p.volatility,
            "stop_loss": p.stop_loss,
            "trailing_stop": p.trailing_stop,
            "pnl_pct": pnl_pct,
            "holding_days": holding_days,
            "tax_type": tax_type,
            "status": p.status,
        })

    nav_data = None
    if latest_nav:
        nav_data = {
            "date": latest_nav.date,
            "nav": latest_nav.nav,
            "benchmark_nav": latest_nav.benchmark_nav,
            "fm_nav": latest_nav.fm_nav,
            "cash_pct": latest_nav.cash_pct,
            "num_positions": latest_nav.num_positions,
            "total_value": latest_nav.total_value,
            "max_drawdown": latest_nav.max_drawdown,
        }

    return {
        "portfolio_type": portfolio_type,
        "positions": positions,
        "num_open": len(open_positions),
        "max_positions": MAX_POSITIONS,
        "nav": nav_data,
        "initial_capital": float(INITIAL_CAPITAL),
    }


def get_trade_history(db: Session, portfolio_type: str = "etf_only", limit: int = 50) -> list[dict]:
    """Get recent trade log for a portfolio type."""
    trades = (
        db.query(CompassModelTrade)
        .filter(CompassModelTrade.portfolio_type == portfolio_type)
        .order_by(CompassModelTrade.trade_date.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "trade_date": t.trade_date,
            "sector_key": t.sector_key,
            "sector_name": NSE_DISPLAY_MAP.get(t.sector_key, t.sector_key),
            "instrument_id": t.instrument_id,
            "instrument_type": t.instrument_type,
            "side": t.side,
            "price": t.price,
            "value": t.value,
            "reason": t.reason,
            "quadrant": t.quadrant.value if t.quadrant else None,
            "rs_score": t.rs_score,
            "pnl_pct": t.pnl_pct,
            "tax_impact": t.tax_impact,
        }
        for t in trades
    ]


def get_nav_history(db: Session, portfolio_type: str = "etf_only", days: int = 365) -> list[dict]:
    """Get model portfolio NAV history."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = (
        db.query(CompassModelNAV)
        .filter(CompassModelNAV.portfolio_type == portfolio_type, CompassModelNAV.date >= cutoff)
        .order_by(CompassModelNAV.date)
        .all()
    )
    return [
        {
            "date": r.date,
            "nav": r.nav,
            "benchmark_nav": r.benchmark_nav,
            "fm_nav": r.fm_nav,
            "cash_pct": r.cash_pct,
            "num_positions": r.num_positions,
            "max_drawdown": r.max_drawdown,
        }
        for r in rows
    ]


def get_performance_metrics(db: Session, portfolio_type: str = "etf_only") -> dict:
    """Compute model portfolio performance metrics."""
    nav_rows = (
        db.query(CompassModelNAV)
        .filter(CompassModelNAV.portfolio_type == portfolio_type)
        .order_by(CompassModelNAV.date)
        .all()
    )
    if not nav_rows:
        return {"status": "no_data", "portfolio_type": portfolio_type}

    navs = [r.nav for r in nav_rows]
    bench_navs = [r.benchmark_nav for r in nav_rows if r.benchmark_nav]

    total_return = (navs[-1] / navs[0] - 1) * 100 if navs[0] and navs[0] > 0 else 0
    bench_return = (bench_navs[-1] / bench_navs[0] - 1) * 100 if bench_navs and bench_navs[0] and bench_navs[0] > 0 else 0
    alpha_vs_nifty = total_return - bench_return

    # Max drawdown
    peak = navs[0]
    max_dd = 0
    for n in navs:
        if n > peak:
            peak = n
        dd = (peak - n) / peak * 100 if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd

    # Win rate from closed trades
    closed_trades = (
        db.query(CompassModelState)
        .filter(CompassModelState.status == "CLOSED", CompassModelState.portfolio_type == portfolio_type)
        .all()
    )
    wins = sum(1 for t in closed_trades if t.pnl_pct and t.pnl_pct > 0)
    total_closed = len(closed_trades)
    win_rate = (wins / total_closed * 100) if total_closed > 0 else 0

    # Average holding period
    holding_days = []
    for t in closed_trades:
        if t.holding_days:
            holding_days.append(t.holding_days)
        elif t.entry_date and t.exit_date:
            try:
                entry = datetime.strptime(t.entry_date, "%Y-%m-%d")
                exit_d = datetime.strptime(t.exit_date, "%Y-%m-%d")
                holding_days.append((exit_d - entry).days)
            except ValueError:
                pass
    avg_holding = sum(holding_days) / len(holding_days) if holding_days else 0

    # Total tax paid
    total_tax = sum(t.tax_impact or 0 for t in (
        db.query(CompassModelTrade)
        .filter(CompassModelTrade.portfolio_type == portfolio_type, CompassModelTrade.side == "SELL")
        .all()
    ))

    # FM comparison
    fm_navs = [r.fm_nav for r in nav_rows if r.fm_nav]
    fm_return = (fm_navs[-1] / fm_navs[0] - 1) * 100 if fm_navs and fm_navs[0] and fm_navs[0] > 0 else None
    alpha_vs_fm = (total_return - fm_return) if fm_return is not None else None

    return {
        "portfolio_type": portfolio_type,
        "total_return_pct": round(total_return, 2),
        "benchmark_return_pct": round(bench_return, 2),
        "alpha_vs_nifty": round(alpha_vs_nifty, 2),
        "alpha_vs_fm": round(alpha_vs_fm, 2) if alpha_vs_fm is not None else None,
        "max_drawdown_pct": round(max_dd, 2),
        "win_rate_pct": round(win_rate, 1),
        "total_trades": total_closed,
        "avg_holding_days": round(avg_holding, 0),
        "total_tax_paid": round(total_tax, 0),
        "start_date": nav_rows[0].date,
        "end_date": nav_rows[-1].date,
        "current_nav": navs[-1],
    }


def run_weekly_rebalance(db: Session, sector_scores: list[dict]) -> dict:
    """
    Weekly rebalance for ALL 3 portfolio types.
    Returns combined actions taken.
    """
    all_actions = {}
    for pt in PORTFOLIO_TYPES:
        actions = _rebalance_portfolio(db, sector_scores, pt)
        all_actions[pt] = actions
    return all_actions


def _rebalance_portfolio(db: Session, sector_scores: list[dict], portfolio_type: str) -> dict:
    """Rebalance a single portfolio type: check exits, then entries."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    actions_taken = {"entries": [], "exits": [], "stop_updates": []}

    score_map = {s["sector_key"]: s for s in sector_scores}

    # 1. Check exits
    open_positions = (
        db.query(CompassModelState)
        .filter(CompassModelState.status == "OPEN", CompassModelState.portfolio_type == portfolio_type)
        .all()
    )

    for pos in open_positions:
        sector_data = score_map.get(pos.sector_key)
        if not sector_data:
            continue

        should_exit = False
        exit_reason = ""

        # Exit rule 1: LAGGING quadrant
        if sector_data["quadrant"] == CompassQuadrant.LAGGING.value:
            should_exit = True
            exit_reason = "LAGGING_QUADRANT"

        # Exit rule 2: WEAKENING + DISTRIBUTION
        elif (sector_data["quadrant"] == CompassQuadrant.WEAKENING.value
              and sector_data.get("volume_signal") == CompassVolumeSignal.DISTRIBUTION.value):
            should_exit = True
            exit_reason = "WEAKENING+DISTRIBUTION"

        # Exit rule 3: stop-loss
        if pos.current_price and pos.stop_loss and pos.current_price <= pos.stop_loss:
            should_exit = True
            exit_reason = "STOP_LOSS"

        # Exit rule 4: trailing stop
        if pos.current_price and pos.trailing_stop and pos.current_price <= pos.trailing_stop:
            should_exit = True
            exit_reason = "TRAILING_STOP"

        if should_exit:
            _execute_exit(db, pos, exit_reason, sector_data, today_str, actions_taken)
        else:
            _update_trailing_stop(pos, actions_taken)

    # 2. Check entries
    current_open = (
        db.query(CompassModelState)
        .filter(CompassModelState.status == "OPEN", CompassModelState.portfolio_type == portfolio_type)
        .count()
    )
    available_slots = MAX_POSITIONS - current_open

    if available_slots > 0:
        held_sectors = {p.sector_key for p in open_positions if p.status == "OPEN"}
        buy_candidates = [
            s for s in sector_scores
            if s["action"] in (CompassAction.BUY.value, CompassAction.ACCUMULATE.value)
            and s["sector_key"] not in held_sectors
        ]
        buy_candidates.sort(key=lambda x: x["rs_score"], reverse=True)

        # Compute volatility-based weights for candidates
        vol_weights = _compute_volatility_weights(db, buy_candidates[:available_slots], portfolio_type)

        for candidate in buy_candidates[:available_slots]:
            _execute_entry(db, candidate, portfolio_type, vol_weights, today_str, actions_taken)

    db.commit()
    logger.info(
        "Rebalance [%s]: %d entries, %d exits, %d stop updates",
        portfolio_type, len(actions_taken["entries"]), len(actions_taken["exits"]),
        len(actions_taken["stop_updates"]),
    )
    return actions_taken


def _execute_exit(
    db: Session, pos: CompassModelState, exit_reason: str,
    sector_data: dict, today_str: str, actions_taken: dict,
) -> None:
    """Execute an exit trade with tax computation."""
    exit_price = pos.current_price or pos.entry_price
    pnl_pct = ((exit_price / pos.entry_price) - 1) * 100 if pos.entry_price > 0 else 0

    holding_days = _compute_holding_days(pos.entry_date)
    tax_type = "LTCG" if holding_days >= STCG_HOLDING_DAYS else "STCG"

    # Compute tax impact
    gain_amount = (exit_price - pos.entry_price) * (pos.quantity or 1)
    tax_impact = 0.0
    if gain_amount > 0:
        if tax_type == "STCG":
            tax_impact = gain_amount * STCG_RATE
        else:
            taxable = max(0, gain_amount - LTCG_EXEMPTION / MAX_POSITIONS)
            tax_impact = taxable * LTCG_RATE

    pos.status = "CLOSED"
    pos.exit_date = today_str
    pos.exit_price = exit_price
    pos.exit_reason = exit_reason
    pos.pnl_pct = round(pnl_pct, 2)
    pos.holding_days = holding_days
    pos.tax_type = tax_type

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
        quadrant=sector_data["quadrant"],
        rs_score=sector_data["rs_score"],
        pnl_pct=round(pnl_pct, 2),
        tax_impact=round(tax_impact, 2),
    ))
    actions_taken["exits"].append({
        "sector": pos.sector_key,
        "reason": exit_reason,
        "pnl_pct": round(pnl_pct, 2),
        "tax_type": tax_type,
        "tax_impact": round(tax_impact, 2),
    })


def _update_trailing_stop(pos: CompassModelState, actions_taken: dict) -> None:
    """Update trailing stop if position has gained enough."""
    if not (pos.current_price and pos.entry_price and pos.entry_price > 0):
        return
    gain_pct = (pos.current_price / pos.entry_price - 1) * 100
    if gain_pct >= TRAILING_TRIGGER_PCT:
        highest = max(pos.highest_since or pos.current_price, pos.current_price)
        pos.highest_since = highest
        new_trailing = highest * (1 - TRAILING_STOP_PCT / 100)
        if pos.trailing_stop is None or new_trailing > pos.trailing_stop:
            pos.trailing_stop = round(new_trailing, 2)
            actions_taken["stop_updates"].append({
                "sector": pos.sector_key,
                "trailing_stop": pos.trailing_stop,
            })


def _execute_entry(
    db: Session, candidate: dict, portfolio_type: str,
    vol_weights: dict, today_str: str, actions_taken: dict,
) -> None:
    """Execute an entry trade. Selects instrument based on portfolio type."""
    etfs = candidate.get("etfs", [])

    if portfolio_type == "etf_only":
        if not etfs:
            return  # skip sectors without ETFs
        instrument_id = etfs[0]
        instrument_type = "etf"
        stop_pct = SECTOR_STOP_LOSS_PCT
    elif portfolio_type == "stock_only":
        # Pick top stock from sector (will be implemented via stock RS)
        # For now use index as proxy
        instrument_id = candidate["sector_key"]
        instrument_type = "index"
        stop_pct = STOCK_STOP_LOSS_PCT
    else:  # stock_etf
        if etfs:
            instrument_id = etfs[0]
            instrument_type = "etf"
        else:
            instrument_id = candidate["sector_key"]
            instrument_type = "index"
        stop_pct = SECTOR_STOP_LOSS_PCT

    entry_price = _get_latest_price(db, instrument_id, instrument_type)
    if not entry_price:
        return

    stop_loss = round(entry_price * (1 - stop_pct / 100), 2)
    weight = vol_weights.get(candidate["sector_key"], round(100 / MAX_POSITIONS, 1))
    volatility = vol_weights.get(f"{candidate['sector_key']}_vol")

    db.add(CompassModelState(
        portfolio_type=portfolio_type,
        sector_key=candidate["sector_key"],
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
        sector_key=candidate["sector_key"],
        instrument_id=instrument_id,
        instrument_type=instrument_type,
        side="BUY",
        price=entry_price,
        quantity=1,
        value=entry_price,
        reason=f"{candidate['quadrant']}+{candidate.get('volume_signal', 'N/A')}",
        quadrant=candidate["quadrant"],
        rs_score=candidate["rs_score"],
    ))
    actions_taken["entries"].append({
        "sector": candidate["sector_key"],
        "instrument": instrument_id,
        "price": entry_price,
        "weight": weight,
    })


def _compute_volatility_weights(
    db: Session, candidates: list[dict], portfolio_type: str,
) -> dict:
    """
    Inverse-volatility position sizing.
    Lower volatility → larger position. Ensures equal risk contribution.
    """
    from services.compass_rs import compute_annualized_volatility

    vols: dict[str, float] = {}
    for c in candidates:
        sector_key = c["sector_key"]
        closes = _get_sector_closes_for_vol(db, sector_key)
        vol = compute_annualized_volatility(closes) if closes else None
        if vol and vol > 0:
            vols[sector_key] = vol

    if not vols:
        # Fallback: equal weight
        equal = round(100 / MAX_POSITIONS, 1) if candidates else 0
        return {c["sector_key"]: equal for c in candidates}

    # Inverse volatility weighting
    inv_vols = {k: 1 / v for k, v in vols.items()}
    total_inv = sum(inv_vols.values())

    # Allocate proportionally within max allocated weight (capped so no single > 25%)
    max_weight = 25.0
    allocated_pct = min(100.0, len(candidates) * (100 / MAX_POSITIONS))

    result = {}
    for c in candidates:
        sk = c["sector_key"]
        if sk in inv_vols:
            raw_weight = (inv_vols[sk] / total_inv) * allocated_pct
            result[sk] = round(min(raw_weight, max_weight), 1)
            result[f"{sk}_vol"] = vols[sk]
        else:
            result[sk] = round(100 / MAX_POSITIONS, 1)

    return result


def _get_sector_closes_for_vol(db: Session, sector_key: str) -> dict:
    """Get last 90 days of sector index closes for volatility computation."""
    cutoff = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")
    rows = (
        db.query(IndexPrice.date, IndexPrice.close_price)
        .filter(IndexPrice.index_name == sector_key, IndexPrice.date >= cutoff)
        .order_by(IndexPrice.date)
        .all()
    )
    return {r.date: r.close_price for r in rows if r.close_price}


def update_model_nav(db: Session) -> dict:
    """Compute and store today's NAV for ALL 3 portfolio types."""
    result = {}
    for pt in PORTFOLIO_TYPES:
        nav = _compute_nav_for_portfolio(db, pt)
        if nav:
            result[pt] = nav
    return result


def _compute_nav_for_portfolio(db: Session, portfolio_type: str) -> Optional[dict]:
    """Compute and store today's NAV for one portfolio type."""
    today_str = datetime.now().strftime("%Y-%m-%d")

    open_positions = (
        db.query(CompassModelState)
        .filter(CompassModelState.status == "OPEN", CompassModelState.portfolio_type == portfolio_type)
        .all()
    )

    # Update current prices
    for pos in open_positions:
        price = _get_latest_price(db, pos.instrument_id, pos.instrument_type)
        if price:
            pos.current_price = price

    # NAV computation (base 100)
    total_return = 0
    for pos in open_positions:
        if pos.entry_price and pos.current_price and pos.entry_price > 0:
            pos_return = (pos.current_price / pos.entry_price - 1)
            weight = (pos.weight_pct or (100 / MAX_POSITIONS)) / 100
            total_return += pos_return * weight

    # Include closed trade P&L
    closed = (
        db.query(CompassModelState)
        .filter(CompassModelState.status == "CLOSED", CompassModelState.portfolio_type == portfolio_type)
        .all()
    )
    closed_return = sum(
        (t.pnl_pct or 0) / 100 * ((t.weight_pct or (100 / MAX_POSITIONS)) / 100)
        for t in closed
    )

    nav = 100 * (1 + total_return + closed_return)

    # Benchmark NAV (NIFTY)
    nifty_closes = (
        db.query(IndexPrice.date, IndexPrice.close_price)
        .filter(IndexPrice.index_name == "NIFTY")
        .order_by(IndexPrice.date)
        .all()
    )
    benchmark_nav = None
    if nifty_closes and len(nifty_closes) >= 2:
        first_close = nifty_closes[0].close_price
        last_close = nifty_closes[-1].close_price
        if first_close and first_close > 0:
            benchmark_nav = round(100 * last_close / first_close, 2)

    # FM NAV
    fm_nav = None
    fm_latest = db.query(PortfolioNAV).filter(PortfolioNAV.portfolio_id == 1).order_by(PortfolioNAV.date.desc()).first()
    fm_first = db.query(PortfolioNAV).filter(PortfolioNAV.portfolio_id == 1).order_by(PortfolioNAV.date).first()
    if fm_latest and fm_first and fm_first.total_value and fm_first.total_value > 0:
        fm_nav = round(100 * fm_latest.total_value / fm_first.total_value, 2)

    cash_pct = max(0, 100 - sum((p.weight_pct or 0) for p in open_positions))

    # Max drawdown (running)
    all_navs = (
        db.query(CompassModelNAV.nav)
        .filter(CompassModelNAV.portfolio_type == portfolio_type)
        .order_by(CompassModelNAV.date)
        .all()
    )
    peak = 100
    max_dd = 0
    for row in all_navs:
        if row.nav > peak:
            peak = row.nav
        dd = (peak - row.nav) / peak * 100 if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
    # Include today
    if nav > peak:
        peak = nav
    dd_today = (peak - nav) / peak * 100 if peak > 0 else 0
    if dd_today > max_dd:
        max_dd = dd_today

    # Upsert
    existing_nav = (
        db.query(CompassModelNAV)
        .filter(CompassModelNAV.date == today_str, CompassModelNAV.portfolio_type == portfolio_type)
        .first()
    )
    nav_data = {
        "nav": round(nav, 2),
        "benchmark_nav": benchmark_nav,
        "fm_nav": fm_nav,
        "cash_pct": round(cash_pct, 1),
        "num_positions": len(open_positions),
        "total_value": round(float(INITIAL_CAPITAL) * nav / 100, 2),
        "max_drawdown": round(max_dd, 2),
    }

    if existing_nav:
        for k, v in nav_data.items():
            setattr(existing_nav, k, v)
    else:
        db.add(CompassModelNAV(
            portfolio_type=portfolio_type,
            date=today_str,
            **nav_data,
        ))

    db.commit()
    return {"portfolio_type": portfolio_type, **nav_data}


def _compute_holding_days(entry_date_str: str) -> int:
    """Compute days held from entry date to today."""
    try:
        entry = datetime.strptime(entry_date_str, "%Y-%m-%d")
        return (datetime.now() - entry).days
    except (ValueError, TypeError):
        return 0


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
