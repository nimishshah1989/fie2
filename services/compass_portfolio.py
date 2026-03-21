"""
Sector Compass — Model Portfolio Engine
Autonomous paper trading based on RS signals.

Rules:
- ENTRY: Sector enters LEADING + ACCUMULATION → buy sector ETF (or top 3 stocks)
- EXIT: Sector drops to LAGGING, or WEAKENING + DISTRIBUTION, or stop-loss hit
- Max 6 sectors. Equal weight. Rebalance weekly.
- Track NAV vs NIFTY and vs FM portfolio.
"""

import logging
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

# Model portfolio config
INITIAL_CAPITAL = Decimal("10000000")  # ₹1 Cr
MAX_POSITIONS = 6
SECTOR_STOP_LOSS_PCT = 8.0
STOCK_STOP_LOSS_PCT = 12.0
TRAILING_TRIGGER_PCT = 15.0
TRAILING_STOP_PCT = 10.0
MAX_WEAKENING_WEEKS = 4


def get_model_portfolio_state(db: Session) -> dict:
    """Get current model portfolio positions and metrics."""
    open_positions = (
        db.query(CompassModelState)
        .filter(CompassModelState.status == "OPEN")
        .all()
    )

    # Latest NAV
    latest_nav = (
        db.query(CompassModelNAV)
        .order_by(CompassModelNAV.date.desc())
        .first()
    )

    positions = []
    for p in open_positions:
        pnl_pct = None
        if p.entry_price and p.current_price and p.entry_price > 0:
            pnl_pct = round((p.current_price / p.entry_price - 1) * 100, 2)
        positions.append({
            "sector_key": p.sector_key,
            "sector_name": NSE_DISPLAY_MAP.get(p.sector_key, p.sector_key),
            "instrument_id": p.instrument_id,
            "instrument_type": p.instrument_type,
            "entry_date": p.entry_date,
            "entry_price": p.entry_price,
            "current_price": p.current_price,
            "weight_pct": p.weight_pct,
            "stop_loss": p.stop_loss,
            "trailing_stop": p.trailing_stop,
            "pnl_pct": pnl_pct,
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
        }

    return {
        "positions": positions,
        "num_open": len(open_positions),
        "max_positions": MAX_POSITIONS,
        "nav": nav_data,
        "initial_capital": float(INITIAL_CAPITAL),
    }


def get_trade_history(db: Session, limit: int = 50) -> list[dict]:
    """Get recent trade log."""
    trades = (
        db.query(CompassModelTrade)
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
        }
        for t in trades
    ]


def get_nav_history(db: Session, days: int = 365) -> list[dict]:
    """Get model portfolio NAV history."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = (
        db.query(CompassModelNAV)
        .filter(CompassModelNAV.date >= cutoff)
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
        }
        for r in rows
    ]


def get_performance_metrics(db: Session) -> dict:
    """Compute model portfolio performance metrics."""
    nav_rows = (
        db.query(CompassModelNAV)
        .order_by(CompassModelNAV.date)
        .all()
    )
    if not nav_rows:
        return {"status": "no_data"}

    navs = [r.nav for r in nav_rows]
    bench_navs = [r.benchmark_nav for r in nav_rows if r.benchmark_nav]

    # Total return
    total_return = (navs[-1] / navs[0] - 1) * 100 if navs[0] and navs[0] > 0 else 0

    # Alpha vs NIFTY
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
        .filter(CompassModelState.status == "CLOSED")
        .all()
    )
    wins = sum(1 for t in closed_trades if t.pnl_pct and t.pnl_pct > 0)
    total_closed = len(closed_trades)
    win_rate = (wins / total_closed * 100) if total_closed > 0 else 0

    # Average holding period
    holding_days = []
    for t in closed_trades:
        if t.entry_date and t.exit_date:
            try:
                entry = datetime.strptime(t.entry_date, "%Y-%m-%d")
                exit_d = datetime.strptime(t.exit_date, "%Y-%m-%d")
                holding_days.append((exit_d - entry).days)
            except ValueError:
                pass
    avg_holding = sum(holding_days) / len(holding_days) if holding_days else 0

    # FM comparison
    fm_navs = [r.fm_nav for r in nav_rows if r.fm_nav]
    fm_return = (fm_navs[-1] / fm_navs[0] - 1) * 100 if fm_navs and fm_navs[0] and fm_navs[0] > 0 else None
    alpha_vs_fm = (total_return - fm_return) if fm_return is not None else None

    return {
        "total_return_pct": round(total_return, 2),
        "benchmark_return_pct": round(bench_return, 2),
        "alpha_vs_nifty": round(alpha_vs_nifty, 2),
        "alpha_vs_fm": round(alpha_vs_fm, 2) if alpha_vs_fm is not None else None,
        "max_drawdown_pct": round(max_dd, 2),
        "win_rate_pct": round(win_rate, 1),
        "total_trades": total_closed,
        "avg_holding_days": round(avg_holding, 0),
        "start_date": nav_rows[0].date,
        "end_date": nav_rows[-1].date,
        "current_nav": navs[-1],
    }


def run_weekly_rebalance(db: Session, sector_scores: list[dict]) -> dict:
    """
    Weekly rebalance: check entry/exit signals, update stops, record trades.
    Called by scheduler or manual refresh.
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    actions_taken = {"entries": [], "exits": [], "stop_updates": []}

    # Build score lookup
    score_map = {s["sector_key"]: s for s in sector_scores}

    # 1. Check exits for existing positions
    open_positions = (
        db.query(CompassModelState)
        .filter(CompassModelState.status == "OPEN")
        .all()
    )

    for pos in open_positions:
        sector_data = score_map.get(pos.sector_key)
        if not sector_data:
            continue

        should_exit = False
        exit_reason = ""

        # Exit rule 1: sector dropped to LAGGING
        if sector_data["quadrant"] == CompassQuadrant.LAGGING.value:
            should_exit = True
            exit_reason = "LAGGING_QUADRANT"

        # Exit rule 2: WEAKENING + DISTRIBUTION
        elif (sector_data["quadrant"] == CompassQuadrant.WEAKENING.value
              and sector_data.get("volume_signal") == CompassVolumeSignal.DISTRIBUTION.value):
            should_exit = True
            exit_reason = "WEAKENING+DISTRIBUTION"

        # Exit rule 3: stop-loss hit
        if pos.current_price and pos.stop_loss and pos.current_price <= pos.stop_loss:
            should_exit = True
            exit_reason = "STOP_LOSS"

        # Exit rule 4: trailing stop hit
        if pos.current_price and pos.trailing_stop and pos.current_price <= pos.trailing_stop:
            should_exit = True
            exit_reason = "TRAILING_STOP"

        if should_exit:
            exit_price = pos.current_price or pos.entry_price
            pnl_pct = ((exit_price / pos.entry_price) - 1) * 100 if pos.entry_price > 0 else 0

            pos.status = "CLOSED"
            pos.exit_date = today_str
            pos.exit_price = exit_price
            pos.exit_reason = exit_reason
            pos.pnl_pct = round(pnl_pct, 2)

            db.add(CompassModelTrade(
                trade_date=today_str,
                sector_key=pos.sector_key,
                instrument_id=pos.instrument_id,
                instrument_type=pos.instrument_type,
                side="SELL",
                price=exit_price,
                value=exit_price * (pos.quantity or 1),
                reason=exit_reason,
                quadrant=sector_data["quadrant"],
                rs_score=sector_data["rs_score"],
            ))
            actions_taken["exits"].append({
                "sector": pos.sector_key,
                "reason": exit_reason,
                "pnl_pct": round(pnl_pct, 2),
            })
        else:
            # Update trailing stop if position has gained enough
            if pos.current_price and pos.entry_price and pos.entry_price > 0:
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

    # 2. Check entries — only if we have capacity
    current_open = (
        db.query(CompassModelState)
        .filter(CompassModelState.status == "OPEN")
        .count()
    )
    available_slots = MAX_POSITIONS - current_open

    if available_slots > 0:
        # Find sectors with BUY signal that we don't already hold
        held_sectors = {p.sector_key for p in open_positions if p.status == "OPEN"}
        buy_candidates = [
            s for s in sector_scores
            if s["action"] in (CompassAction.BUY.value, CompassAction.ACCUMULATE.value)
            and s["sector_key"] not in held_sectors
        ]
        # Sort by RS score descending — strongest first
        buy_candidates.sort(key=lambda x: x["rs_score"], reverse=True)

        for candidate in buy_candidates[:available_slots]:
            etfs = candidate.get("etfs", [])
            if etfs:
                instrument_id = etfs[0]
                instrument_type = "etf"
            else:
                instrument_id = candidate["sector_key"]
                instrument_type = "index"

            # Get current price
            entry_price = _get_latest_price(db, instrument_id, instrument_type)
            if not entry_price:
                continue

            stop_loss = round(entry_price * (1 - SECTOR_STOP_LOSS_PCT / 100), 2)

            db.add(CompassModelState(
                sector_key=candidate["sector_key"],
                instrument_id=instrument_id,
                instrument_type=instrument_type,
                entry_date=today_str,
                entry_price=entry_price,
                current_price=entry_price,
                quantity=1,
                weight_pct=round(100 / MAX_POSITIONS, 1),
                stop_loss=stop_loss,
                status="OPEN",
            ))

            db.add(CompassModelTrade(
                trade_date=today_str,
                sector_key=candidate["sector_key"],
                instrument_id=instrument_id,
                instrument_type=instrument_type,
                side="BUY",
                price=entry_price,
                value=entry_price,
                reason=f"{candidate['quadrant']}+{candidate.get('volume_signal', 'N/A')}",
                quadrant=candidate["quadrant"],
                rs_score=candidate["rs_score"],
            ))
            actions_taken["entries"].append({
                "sector": candidate["sector_key"],
                "instrument": instrument_id,
                "price": entry_price,
            })

    db.commit()
    logger.info(
        "Rebalance: %d entries, %d exits, %d stop updates",
        len(actions_taken["entries"]),
        len(actions_taken["exits"]),
        len(actions_taken["stop_updates"]),
    )
    return actions_taken


def update_model_nav(db: Session) -> Optional[dict]:
    """Compute and store today's model portfolio NAV."""
    today_str = datetime.now().strftime("%Y-%m-%d")

    open_positions = (
        db.query(CompassModelState)
        .filter(CompassModelState.status == "OPEN")
        .all()
    )

    # Update current prices for open positions
    for pos in open_positions:
        price = _get_latest_price(db, pos.instrument_id, pos.instrument_type)
        if price:
            pos.current_price = price

    # Compute NAV (base 100)
    first_nav = db.query(CompassModelNAV).order_by(CompassModelNAV.date).first()
    if first_nav:
        base_value = float(INITIAL_CAPITAL)
    else:
        base_value = float(INITIAL_CAPITAL)

    # Simple NAV: sum of position returns
    total_return = 0
    for pos in open_positions:
        if pos.entry_price and pos.current_price and pos.entry_price > 0:
            pos_return = (pos.current_price / pos.entry_price - 1)
            weight = (pos.weight_pct or (100 / MAX_POSITIONS)) / 100
            total_return += pos_return * weight

    # Include closed trade P&L
    closed = (
        db.query(CompassModelState)
        .filter(CompassModelState.status == "CLOSED")
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

    # FM NAV — try to get from existing portfolio NAV
    fm_nav = None
    fm_latest = (
        db.query(PortfolioNAV)
        .filter(PortfolioNAV.portfolio_id == 1)
        .order_by(PortfolioNAV.date.desc())
        .first()
    )
    fm_first = (
        db.query(PortfolioNAV)
        .filter(PortfolioNAV.portfolio_id == 1)
        .order_by(PortfolioNAV.date)
        .first()
    )
    if fm_latest and fm_first and fm_first.total_value and fm_first.total_value > 0:
        fm_nav = round(100 * fm_latest.total_value / fm_first.total_value, 2)

    cash_pct = max(0, 100 - sum((p.weight_pct or 0) for p in open_positions))

    # Upsert
    existing_nav = db.query(CompassModelNAV).filter_by(date=today_str).first()
    if existing_nav:
        existing_nav.nav = round(nav, 2)
        existing_nav.benchmark_nav = benchmark_nav
        existing_nav.fm_nav = fm_nav
        existing_nav.cash_pct = round(cash_pct, 1)
        existing_nav.num_positions = len(open_positions)
        existing_nav.total_value = round(float(INITIAL_CAPITAL) * nav / 100, 2)
    else:
        db.add(CompassModelNAV(
            date=today_str,
            nav=round(nav, 2),
            benchmark_nav=benchmark_nav,
            fm_nav=fm_nav,
            cash_pct=round(cash_pct, 1),
            num_positions=len(open_positions),
            total_value=round(float(INITIAL_CAPITAL) * nav / 100, 2),
        ))

    db.commit()
    return {"nav": round(nav, 2), "benchmark_nav": benchmark_nav, "fm_nav": fm_nav}


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
