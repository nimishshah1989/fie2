"""
Compass Lab — Stateless NumPy Simulator
Replays the gate-based RS decision engine across historical price data.

No DB dependency. Pure math. Takes numpy arrays in, returns metrics out.
~5-8ms per simulation run (one parameter set across full history).

Usage:
    prices = np.array(...)          # shape (n_days, n_sectors)
    benchmark = np.array(...)       # shape (n_days,)
    params = SimParams(stop_loss_pct=8.0, ...)
    result = simulate(prices, benchmark, sector_keys, params)
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

logger = logging.getLogger("fie_v3.compass.simulator")

# ─── Period Lookback in Trading Days ─────────────────────────

PERIOD_DAYS = {"1M": 21, "2M": 42, "3M": 63, "6M": 126, "12M": 252}


# ─── Simulation Parameters ──────────────────────────────────

@dataclass(frozen=True)
class SimParams:
    """All tunable parameters for one simulation run."""
    rs_period: str = "3M"               # lookback for RS computation
    stop_loss_pct: float = 8.0          # exit if price drops this % from entry
    trailing_trigger_pct: float = 15.0  # activate trailing stop after this % gain
    trailing_stop_pct: float = 10.0     # trailing stop distance from peak
    max_positions: int = 6              # max simultaneous positions
    min_rs_entry: float = 0.0           # minimum RS score to consider BUY
    min_holding_days: int = 0           # minimum days before exit allowed
    regime_gate_strictness: str = "moderate"  # loose, moderate, strict

    def to_dict(self) -> dict:
        return {
            "rs_period": self.rs_period,
            "stop_loss_pct": self.stop_loss_pct,
            "trailing_trigger_pct": self.trailing_trigger_pct,
            "trailing_stop_pct": self.trailing_stop_pct,
            "max_positions": self.max_positions,
            "min_rs_entry": self.min_rs_entry,
            "min_holding_days": self.min_holding_days,
            "regime_gate_strictness": self.regime_gate_strictness,
        }

    def param_hash(self) -> str:
        """Unique hash for this parameter combination."""
        import hashlib
        s = "|".join(f"{k}={v}" for k, v in sorted(self.to_dict().items()))
        return hashlib.md5(s.encode()).hexdigest()[:12]


# ─── Simulation Result ──────────────────────────────────────

@dataclass
class RegimeMetrics:
    """Metrics for a specific market regime."""
    regime: str
    sharpe: float = 0.0
    sortino: float = 0.0
    win_rate: float = 0.0
    max_drawdown: float = 0.0
    n_trades: int = 0
    avg_gain: float = 0.0
    avg_loss: float = 0.0

    def to_dict(self) -> dict:
        return {
            "regime": self.regime, "sharpe": self.sharpe, "sortino": self.sortino,
            "win_rate": self.win_rate, "max_drawdown": self.max_drawdown,
            "n_trades": self.n_trades, "avg_gain": self.avg_gain, "avg_loss": self.avg_loss,
        }


@dataclass
class SimTrade:
    """One simulated trade."""
    day_idx: int
    sector_idx: int
    side: str           # BUY or SELL
    price: float
    regime: str
    rs_score: float
    momentum: float
    pnl_pct: float = 0.0
    holding_days: int = 0
    exit_reason: str = ""


@dataclass
class SimResult:
    """Complete output from one simulation run."""
    param_hash: str
    params: dict
    total_return: float = 0.0
    cagr: float = 0.0
    sharpe: float = 0.0
    sortino: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    avg_holding_days: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    regime_metrics: dict = field(default_factory=dict)  # regime_name → RegimeMetrics
    nav_curve: Optional[np.ndarray] = None
    trades: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "param_hash": self.param_hash,
            "params": self.params,
            "total_return": round(self.total_return, 2),
            "cagr": round(self.cagr, 2),
            "sharpe": round(self.sharpe, 3),
            "sortino": round(self.sortino, 3),
            "max_drawdown": round(self.max_drawdown, 2),
            "win_rate": round(self.win_rate, 1),
            "profit_factor": round(self.profit_factor, 2),
            "total_trades": self.total_trades,
            "avg_holding_days": round(self.avg_holding_days, 1),
            "avg_win": round(self.avg_win, 2),
            "avg_loss": round(self.avg_loss, 2),
            "regime_metrics": {k: v.to_dict() for k, v in self.regime_metrics.items()},
        }


# ─── Position Tracker (internal, per simulation) ────────────

@dataclass
class _Position:
    sector_idx: int
    entry_day: int
    entry_price: float
    stop_loss: float
    trailing_stop: float = 0.0
    highest_price: float = 0.0
    trailing_active: bool = False
    regime_at_entry: str = ""


# ─── Regime Detection (vectorized) ──────────────────────────

def detect_regimes_vectorized(benchmark: np.ndarray) -> np.ndarray:
    """
    Detect market regime for each day from benchmark prices.
    Returns array of regime codes: 0=BULL, 1=CAUTIOUS, 2=CORRECTION, 3=BEAR

    Fully vectorized using rolling computations.
    """
    n = len(benchmark)
    regimes = np.zeros(n, dtype=np.int8)

    if n < 50:
        return regimes

    # 50-day simple moving average (cumsum trick)
    cumsum = np.cumsum(benchmark)
    sma50 = np.full(n, np.nan)
    sma50[49:] = (cumsum[49:] - np.concatenate([[0], cumsum[:-50]])) / 50
    below_50dma = benchmark < sma50

    # Rolling 252-day peak (use stride trick for speed)
    rolling_peak = np.full(n, np.nan)
    for i in range(n):
        start = max(0, i - 251)
        rolling_peak[i] = np.max(benchmark[start:i + 1])

    # Drawdown from peak
    with np.errstate(divide='ignore', invalid='ignore'):
        drawdown_pct = np.where(rolling_peak > 0, (benchmark / rolling_peak - 1) * 100, 0)

    # 3-month (63 day) return
    ret_3m = np.full(n, 0.0)
    with np.errstate(divide='ignore', invalid='ignore'):
        ret_3m[63:] = np.where(
            benchmark[:-63] > 0,
            (benchmark[63:] / benchmark[:-63] - 1) * 100,
            0,
        )

    # Classify — vectorized boolean logic
    is_bear = drawdown_pct < -15
    is_correction = (~is_bear) & ((drawdown_pct < -8) | (below_50dma & (ret_3m < -5)))
    is_cautious = (~is_bear) & (~is_correction) & below_50dma

    regimes[is_bear] = 3
    regimes[is_correction] = 2
    regimes[is_cautious] = 1
    # BULL = 0 (default)

    # First 50 days: not enough data, assume BULL
    regimes[:50] = 0
    return regimes


REGIME_NAMES = {0: "BULL", 1: "CAUTIOUS", 2: "CORRECTION", 3: "BEAR"}
REGIME_CODES = {"BULL": 0, "CAUTIOUS": 1, "CORRECTION": 2, "BEAR": 3}


# ─── Gate Engine (stateless) ────────────────────────────────

def evaluate_gates(
    absolute_return: float,
    rs_score: float,
    momentum: float,
    regime_code: int,
    min_rs: float,
    strictness: str,
) -> str:
    """
    Gate-based decision: returns action string.
    Same logic as compass_rs._derive_action_gate but stateless.
    """
    g1 = absolute_return > 0
    g2 = rs_score > min_rs
    g3 = momentum > 0

    if g1 and g2 and g3:
        action = "BUY"
    elif g1 and g2 and not g3:
        action = "HOLD"
    elif g1 and not g2 and g3:
        action = "WATCH"
    elif g1 and not g2 and not g3:
        action = "AVOID"
    elif not g1 and g2 and g3:
        action = "WATCH"
    elif not g1 and g2 and not g3:
        action = "SELL"
    elif not g1 and not g2 and g3:
        action = "WATCH"
    else:
        action = "SELL"

    # Regime override
    if action == "BUY":
        if regime_code == 3:  # BEAR
            action = "HOLD"
        elif regime_code == 2:  # CORRECTION
            if strictness == "strict":
                action = "HOLD"
            # moderate: allow BUY in CORRECTION (default)
            # loose: allow BUY everywhere

    return action


# ─── Core Simulator ─────────────────────────────────────────

def simulate(
    prices: np.ndarray,
    benchmark: np.ndarray,
    sector_keys: list[str],
    params: SimParams,
) -> SimResult:
    """
    Replay gate engine across full price history with given parameters.

    Args:
        prices: shape (n_days, n_sectors) — daily close prices
        benchmark: shape (n_days,) — benchmark (NIFTY) daily closes
        sector_keys: list of sector key names, length = n_sectors
        params: simulation parameters

    Returns:
        SimResult with full metrics, NAV curve, and trade list
    """
    n_days, n_sectors = prices.shape
    lookback = PERIOD_DAYS.get(params.rs_period, 63)
    momentum_window = 20

    # Need at least lookback + momentum_window + 1 days
    min_days = lookback + momentum_window + 1
    if n_days < min_days:
        return SimResult(
            param_hash=params.param_hash(),
            params=params.to_dict(),
        )

    # Pre-compute regimes
    regimes = detect_regimes_vectorized(benchmark)

    # Pre-compute returns, RS scores, momentum — FULLY VECTORIZED
    # Sector returns: prices[i] / prices[i - lookback] - 1
    past_prices = prices[:-lookback]    # shape (n_days - lookback, n_sectors)
    curr_prices = prices[lookback:]     # shape (n_days - lookback, n_sectors)
    with np.errstate(divide='ignore', invalid='ignore'):
        sector_rets_block = np.where(past_prices > 0, (curr_prices / past_prices - 1) * 100, np.nan)

    sector_returns = np.full((n_days, n_sectors), np.nan)
    sector_returns[lookback:] = sector_rets_block

    # Benchmark returns
    past_bench = benchmark[:-lookback]
    curr_bench = benchmark[lookback:]
    with np.errstate(divide='ignore', invalid='ignore'):
        bench_rets_block = np.where(past_bench > 0, (curr_bench / past_bench - 1) * 100, np.nan)
    bench_returns = np.full(n_days, np.nan)
    bench_returns[lookback:] = bench_rets_block

    # RS = sector return - benchmark return (broadcast)
    rs_scores = sector_returns - bench_returns[:, np.newaxis]

    # Momentum = RS[day] - RS[day - 20]
    momentum = np.full((n_days, n_sectors), np.nan)
    momentum[lookback + momentum_window:] = (
        rs_scores[lookback + momentum_window:] - rs_scores[lookback:-momentum_window]
    )

    # ── Walk forward day by day ──────────────────────────────
    start_day = lookback + momentum_window
    positions: list[_Position] = []
    trades: list[SimTrade] = []
    nav_values: list[float] = []
    initial_capital = 1_000_000.0  # ₹10L notional
    cash = initial_capital
    position_value_at_entry: dict[int, float] = {}  # sector_idx → value allocated

    for day in range(start_day, n_days):
        regime = regimes[day]
        current_prices = prices[day]

        # ── Check exits first ────────────────────────────────
        to_remove = []
        for pos in positions:
            price_now = current_prices[pos.sector_idx]
            if price_now <= 0:
                continue

            holding_d = day - pos.entry_day
            exit_reason = ""

            # Stop-loss check
            if price_now <= pos.stop_loss:
                exit_reason = "STOP_LOSS"

            # Trailing stop
            if pos.trailing_active and price_now <= pos.trailing_stop:
                exit_reason = "TRAILING_STOP"

            # Signal-based exit: check if action is SELL or AVOID
            rs = rs_scores[day, pos.sector_idx]
            mom = momentum[day, pos.sector_idx]
            abs_ret = sector_returns[day, pos.sector_idx]
            if not np.isnan(rs) and not np.isnan(mom) and not np.isnan(abs_ret):
                action = evaluate_gates(
                    abs_ret, rs, mom, regime, params.min_rs_entry,
                    params.regime_gate_strictness,
                )
                if action in ("SELL", "AVOID") and holding_d >= params.min_holding_days:
                    exit_reason = "SELL_SIGNAL"

            if exit_reason:
                pnl_pct = (price_now / pos.entry_price - 1) * 100
                trades.append(SimTrade(
                    day_idx=day, sector_idx=pos.sector_idx, side="SELL",
                    price=price_now, regime=REGIME_NAMES[regime],
                    rs_score=rs if not np.isnan(rs) else 0,
                    momentum=mom if not np.isnan(mom) else 0,
                    pnl_pct=pnl_pct, holding_days=holding_d,
                    exit_reason=exit_reason,
                ))
                # Return capital + P&L
                allocated = position_value_at_entry.get(pos.sector_idx, initial_capital / params.max_positions)
                cash += allocated * (1 + pnl_pct / 100)
                to_remove.append(pos)
            else:
                # Update trailing stop
                if price_now > pos.highest_price:
                    pos.highest_price = price_now
                gain_pct = (price_now / pos.entry_price - 1) * 100
                if gain_pct >= params.trailing_trigger_pct:
                    pos.trailing_active = True
                    new_stop = pos.highest_price * (1 - params.trailing_stop_pct / 100)
                    if new_stop > pos.trailing_stop:
                        pos.trailing_stop = new_stop

        for pos in to_remove:
            positions.remove(pos)
            position_value_at_entry.pop(pos.sector_idx, None)

        # ── Check entries ────────────────────────────────────
        held_sectors = {p.sector_idx for p in positions}
        available_slots = params.max_positions - len(positions)

        if available_slots > 0:
            candidates = []
            for s in range(n_sectors):
                if s in held_sectors:
                    continue
                rs = rs_scores[day, s]
                mom = momentum[day, s]
                abs_ret = sector_returns[day, s]
                if np.isnan(rs) or np.isnan(mom) or np.isnan(abs_ret):
                    continue
                price_now = current_prices[s]
                if price_now <= 0:
                    continue

                action = evaluate_gates(
                    abs_ret, rs, mom, regime, params.min_rs_entry,
                    params.regime_gate_strictness,
                )
                if action == "BUY":
                    candidates.append((s, rs, mom, abs_ret, price_now))

            # Sort by RS score descending
            candidates.sort(key=lambda x: x[1], reverse=True)

            for s_idx, rs, mom, abs_ret, price_now in candidates[:available_slots]:
                if cash <= 0:
                    break
                # Equal allocation for simplicity in simulation
                alloc = min(cash, initial_capital / params.max_positions)
                stop = price_now * (1 - params.stop_loss_pct / 100)

                positions.append(_Position(
                    sector_idx=s_idx, entry_day=day, entry_price=price_now,
                    stop_loss=stop, highest_price=price_now,
                    regime_at_entry=REGIME_NAMES[regime],
                ))
                position_value_at_entry[s_idx] = alloc
                cash -= alloc

                trades.append(SimTrade(
                    day_idx=day, sector_idx=s_idx, side="BUY",
                    price=price_now, regime=REGIME_NAMES[regime],
                    rs_score=rs, momentum=mom,
                ))

        # ── Compute portfolio NAV ────────────────────────────
        port_value = cash
        for pos in positions:
            price_now = current_prices[pos.sector_idx]
            if price_now > 0:
                allocated = position_value_at_entry.get(pos.sector_idx, initial_capital / params.max_positions)
                pnl_ratio = price_now / pos.entry_price
                port_value += allocated * pnl_ratio
        nav = (port_value / initial_capital) * 100  # base 100
        nav_values.append(nav)

    # ── Compute aggregate metrics ────────────────────────────
    nav_arr = np.array(nav_values) if nav_values else np.array([100.0])
    sell_trades = [t for t in trades if t.side == "SELL"]

    result = SimResult(
        param_hash=params.param_hash(),
        params=params.to_dict(),
        total_trades=len(sell_trades),
        nav_curve=nav_arr,
        trades=trades,
    )

    if len(nav_arr) > 1:
        result.total_return = float(nav_arr[-1] / nav_arr[0] - 1) * 100

        # CAGR
        years = len(nav_arr) / 252
        if years > 0 and nav_arr[0] > 0 and nav_arr[-1] > 0:
            result.cagr = float((nav_arr[-1] / nav_arr[0]) ** (1 / years) - 1) * 100

        # Sharpe (daily returns annualized)
        daily_returns = np.diff(nav_arr) / nav_arr[:-1]
        if len(daily_returns) > 1 and np.std(daily_returns) > 0:
            result.sharpe = float(
                np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)
            )

        # Sortino (downside deviation only)
        downside = daily_returns[daily_returns < 0]
        if len(downside) > 1:
            downside_std = float(np.std(downside))
            if downside_std > 0:
                result.sortino = float(
                    np.mean(daily_returns) / downside_std * np.sqrt(252)
                )

        # Max drawdown
        peak = np.maximum.accumulate(nav_arr)
        drawdowns = (peak - nav_arr) / peak * 100
        result.max_drawdown = float(np.max(drawdowns))

    # Win rate, avg win/loss, profit factor
    if sell_trades:
        wins = [t for t in sell_trades if t.pnl_pct > 0]
        losses = [t for t in sell_trades if t.pnl_pct <= 0]
        result.win_rate = len(wins) / len(sell_trades) * 100

        if wins:
            result.avg_win = sum(t.pnl_pct for t in wins) / len(wins)
        if losses:
            result.avg_loss = sum(t.pnl_pct for t in losses) / len(losses)

        total_win = sum(t.pnl_pct for t in wins) if wins else 0
        total_loss = abs(sum(t.pnl_pct for t in losses)) if losses else 0
        result.profit_factor = total_win / total_loss if total_loss > 0 else float('inf')

        result.avg_holding_days = sum(t.holding_days for t in sell_trades) / len(sell_trades)

    # ── Per-regime metrics ───────────────────────────────────
    for regime_code, regime_name in REGIME_NAMES.items():
        regime_sells = [t for t in sell_trades if t.regime == regime_name]
        rm = RegimeMetrics(regime=regime_name, n_trades=len(regime_sells))

        if regime_sells:
            r_wins = [t for t in regime_sells if t.pnl_pct > 0]
            r_losses = [t for t in regime_sells if t.pnl_pct <= 0]
            rm.win_rate = len(r_wins) / len(regime_sells) * 100
            if r_wins:
                rm.avg_gain = sum(t.pnl_pct for t in r_wins) / len(r_wins)
            if r_losses:
                rm.avg_loss = sum(t.pnl_pct for t in r_losses) / len(r_losses)

            # Sharpe for regime trades (approximate — use trade P&L as returns)
            pnls = np.array([t.pnl_pct for t in regime_sells])
            if len(pnls) > 1 and np.std(pnls) > 0:
                rm.sharpe = float(np.mean(pnls) / np.std(pnls))
                downside_pnl = pnls[pnls < 0]
                if len(downside_pnl) > 0 and np.std(downside_pnl) > 0:
                    rm.sortino = float(np.mean(pnls) / np.std(downside_pnl))

        result.regime_metrics[regime_name] = rm

    return result


# ─── Parameter Grid Generation ──────────────────────────────

def generate_param_grid() -> list[SimParams]:
    """Generate all parameter combinations for full Lab sweep."""
    grid = []
    for rs_period in ["1M", "3M", "6M", "12M"]:
        for stop_loss in [5.0, 8.0, 10.0, 12.0, 15.0]:
            for trailing_trigger in [10.0, 15.0, 20.0, 25.0]:
                for trailing_stop in [5.0, 8.0, 10.0, 12.0]:
                    for max_pos in [3, 4, 5, 6, 8]:
                        for min_rs in [0.0, 2.0, 5.0, 8.0]:
                            for min_hold in [0, 5, 10, 20]:
                                for strictness in ["loose", "moderate", "strict"]:
                                    grid.append(SimParams(
                                        rs_period=rs_period,
                                        stop_loss_pct=stop_loss,
                                        trailing_trigger_pct=trailing_trigger,
                                        trailing_stop_pct=trailing_stop,
                                        max_positions=max_pos,
                                        min_rs_entry=min_rs,
                                        min_holding_days=min_hold,
                                        regime_gate_strictness=strictness,
                                    ))
    return grid


def generate_focused_grid(base_params: SimParams, variation: int = 1) -> list[SimParams]:
    """Generate focused grid around a known-good parameter set (hill-climbing).
    Always includes the base params themselves."""
    base = base_params.to_dict()
    seen = set()
    grid = []

    # Always include base params first
    grid.append(base_params)
    seen.add(base_params.param_hash())

    # Vary each numeric param by ±variation steps
    stop_losses = sorted(set(max(3, base["stop_loss_pct"] + d * 1.0) for d in range(-variation, variation + 1)))
    trailing_triggers = sorted(set(max(5, base["trailing_trigger_pct"] + d * 2.0) for d in range(-variation, variation + 1)))
    trailing_stops = sorted(set(max(3, base["trailing_stop_pct"] + d * 1.0) for d in range(-variation, variation + 1)))
    max_positions = sorted(set(max(2, base["max_positions"] + d) for d in range(-variation, variation + 1)))
    min_rs_vals = sorted(set(max(0, base["min_rs_entry"] + d * 1.0) for d in range(-variation, variation + 1)))

    for sl in stop_losses:
        for tt in trailing_triggers:
            for ts in trailing_stops:
                for mp in max_positions:
                    for mr in min_rs_vals:
                        p = SimParams(
                            rs_period=base["rs_period"],
                            stop_loss_pct=sl,
                            trailing_trigger_pct=tt,
                            trailing_stop_pct=ts,
                            max_positions=int(mp),
                            min_rs_entry=mr,
                            min_holding_days=base["min_holding_days"],
                            regime_gate_strictness=base["regime_gate_strictness"],
                        )
                        h = p.param_hash()
                        if h not in seen:
                            seen.add(h)
                            grid.append(p)
    return grid
