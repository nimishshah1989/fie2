"""
Sector Compass — RS Engine
3 simple indicators: RS Score, Momentum, Volume Trend.
No complex weights. No multi-timeframe composites. Intuitive and actionable.

RS Score: relative return ratio vs benchmark (% outperformance/underperformance)
Momentum: change in RS Score over 4 weeks (is strength improving or fading?)
Volume:   20d vs 60d average + price direction → accumulation/distribution
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from index_constants import (
    COMPASS_ETF_UNIVERSE,
    COMPASS_SECTOR_ETF_MAP,
    COMPASS_SECTOR_INDICES,
    ETF_ASSET_CLASS,
    NSE_DISPLAY_MAP,
    NSE_INDEX_CATEGORIES,
)
from models import (
    CompassAction,
    CompassETFPrice,
    CompassQuadrant,
    CompassRSScore,
    CompassStockPrice,
    CompassVolumeSignal,
    IndexConstituent,
    IndexPrice,
)

logger = logging.getLogger("fie_v3.compass.rs")

# Trading days approximation
TRADING_DAYS_4W = 20
TRADING_DAYS_3M = 63
PERIOD_DAYS_MAP = {
    "1M": 21,
    "3M": 63,
    "6M": 126,
    "12M": 252,
}


def _get_sector_category(sector_key: str) -> str:
    """Get category for a sector key from index constants."""
    return NSE_INDEX_CATEGORIES.get(sector_key, "thematic")


def _get_index_close_map(db: Session, index_key: str, days: int = 300) -> dict[str, float]:
    """Get date->close map for an index from IndexPrice table."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = (
        db.query(IndexPrice.date, IndexPrice.close_price)
        .filter(IndexPrice.index_name == index_key, IndexPrice.date >= cutoff)
        .order_by(IndexPrice.date)
        .all()
    )
    return {r.date: r.close_price for r in rows if r.close_price is not None}


def _get_stock_close_map(db: Session, ticker: str, days: int = 300) -> dict[str, float]:
    """Get date->close map for a stock from compass tables."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = (
        db.query(CompassStockPrice.date, CompassStockPrice.close)
        .filter(CompassStockPrice.ticker == ticker, CompassStockPrice.date >= cutoff)
        .order_by(CompassStockPrice.date)
        .all()
    )
    return {r.date: r.close for r in rows if r.close is not None}


def _get_stock_volume_series(db: Session, ticker: str, days: int = 80) -> list[dict]:
    """Get recent price+volume series for volume analysis."""
    cutoff = (datetime.now() - timedelta(days=days + 30)).strftime("%Y-%m-%d")
    rows = (
        db.query(CompassStockPrice.date, CompassStockPrice.close, CompassStockPrice.volume)
        .filter(CompassStockPrice.ticker == ticker, CompassStockPrice.date >= cutoff)
        .order_by(CompassStockPrice.date)
        .all()
    )
    return [{"date": r.date, "close": r.close, "volume": r.volume} for r in rows]


def _get_etf_close_map(db: Session, ticker: str, days: int = 300) -> dict[str, float]:
    """Get date->close map for an ETF from compass tables."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = (
        db.query(CompassETFPrice.date, CompassETFPrice.close)
        .filter(CompassETFPrice.ticker == ticker, CompassETFPrice.date >= cutoff)
        .order_by(CompassETFPrice.date)
        .all()
    )
    return {r.date: r.close for r in rows if r.close is not None}


def _compute_relative_return(
    asset_closes: dict[str, float],
    benchmark_closes: dict[str, float],
    period_days: int,
) -> Optional[float]:
    """
    Compute relative return of asset vs benchmark over period_days.
    Returns percentage excess return (asset_return - benchmark_return).
    """
    dates = sorted(asset_closes.keys())
    if len(dates) < period_days // 2:
        return None

    latest_date = dates[-1]
    target_idx = max(0, len(dates) - period_days)
    start_date = dates[target_idx]

    asset_now = asset_closes.get(latest_date)
    asset_then = asset_closes.get(start_date)
    bench_now = benchmark_closes.get(latest_date)
    bench_then = benchmark_closes.get(start_date)

    if not all([asset_now, asset_then, bench_now, bench_then]):
        return None
    if asset_then == 0 or bench_then == 0:
        return None

    asset_return = (asset_now / asset_then - 1) * 100
    bench_return = (bench_now / bench_then - 1) * 100
    return asset_return - bench_return


def _compute_volume_signal(price_volume: list[dict]) -> Optional[CompassVolumeSignal]:
    """
    Volume trend: 20d avg vs 60d avg + price direction.
    - Price up + Volume up → ACCUMULATION
    - Price up + Volume down → WEAK_RALLY
    - Price down + Volume up → DISTRIBUTION
    - Price down + Volume down → WEAK_DECLINE
    """
    if len(price_volume) < 60:
        return None

    recent = price_volume[-20:]
    older = price_volume[-60:]

    # Filter out None volumes
    recent_vols = [r["volume"] for r in recent if r.get("volume") is not None]
    older_vols = [r["volume"] for r in older if r.get("volume") is not None]

    if not recent_vols or not older_vols:
        return None

    avg_vol_20d = sum(recent_vols) / len(recent_vols)
    avg_vol_60d = sum(older_vols) / len(older_vols)

    # Price direction: compare last close to close 20 days ago
    price_now = price_volume[-1].get("close")
    price_20d = price_volume[-20].get("close") if len(price_volume) >= 20 else None

    if price_now is None or price_20d is None or price_20d == 0:
        return None

    price_rising = price_now > price_20d
    volume_rising = avg_vol_20d > avg_vol_60d

    if price_rising and volume_rising:
        return CompassVolumeSignal.ACCUMULATION
    elif price_rising and not volume_rising:
        return CompassVolumeSignal.WEAK_RALLY
    elif not price_rising and volume_rising:
        return CompassVolumeSignal.DISTRIBUTION
    else:
        return CompassVolumeSignal.WEAK_DECLINE


def _classify_quadrant(rs_score: float, momentum: float) -> CompassQuadrant:
    """
    Simple 2x2: RS Score centered at 0 (outperforming vs underperforming),
    Momentum centered at 0 (improving vs deteriorating).
    """
    if rs_score > 0 and momentum > 0:
        return CompassQuadrant.LEADING
    elif rs_score > 0 and momentum <= 0:
        return CompassQuadrant.WEAKENING
    elif rs_score <= 0 and momentum > 0:
        return CompassQuadrant.IMPROVING
    else:
        return CompassQuadrant.LAGGING


def _compute_absolute_return(
    asset_closes: dict[str, float], period_days: int,
) -> Optional[float]:
    """Compute absolute return of an asset over period_days (%)."""
    dates = sorted(asset_closes.keys())
    if len(dates) < period_days // 2:
        return None
    target_idx = max(0, len(dates) - period_days)
    price_now = asset_closes.get(dates[-1])
    price_then = asset_closes.get(dates[target_idx])
    if not price_now or not price_then or price_then == 0:
        return None
    return (price_now / price_then - 1) * 100


def _compute_market_regime(benchmark_closes: dict[str, float]) -> dict:
    """
    Assess market regime from benchmark price data.
    Returns regime info: trend, drawdown, distance from moving averages.
    """
    dates = sorted(benchmark_closes.keys())
    if len(dates) < 50:
        return {"regime": "UNKNOWN", "drawdown_pct": 0, "below_50dma": False}

    prices = [benchmark_closes[d] for d in dates]
    current = prices[-1]

    # 50-day moving average
    avg_50d = sum(prices[-50:]) / 50
    below_50dma = current < avg_50d

    # Drawdown from peak (last 252 days or available)
    lookback = prices[-min(252, len(prices)):]
    peak = max(lookback)
    drawdown_pct = (current / peak - 1) * 100

    # 3-month return
    idx_3m = max(0, len(prices) - 63)
    ret_3m = (current / prices[idx_3m] - 1) * 100

    # Classify regime
    if drawdown_pct < -15:
        regime = "BEAR"
    elif drawdown_pct < -8 or (below_50dma and ret_3m < -5):
        regime = "CORRECTION"
    elif below_50dma:
        regime = "CAUTIOUS"
    else:
        regime = "BULL"

    return {
        "regime": regime,
        "drawdown_pct": round(drawdown_pct, 1),
        "below_50dma": below_50dma,
        "ret_3m": round(ret_3m, 1),
    }


PE_ZONE_THRESHOLDS = {"VALUE": 15, "FAIR": 25, "STRETCHED": 40}


def _classify_pe_zone(pe_ratio: Optional[float]) -> Optional[str]:
    """Classify P/E into valuation zone: VALUE / FAIR / STRETCHED / EXPENSIVE."""
    if pe_ratio is None:
        return None
    if pe_ratio < PE_ZONE_THRESHOLDS["VALUE"]:
        return "VALUE"
    elif pe_ratio < PE_ZONE_THRESHOLDS["FAIR"]:
        return "FAIR"
    elif pe_ratio < PE_ZONE_THRESHOLDS["STRETCHED"]:
        return "STRETCHED"
    else:
        return "EXPENSIVE"


def _derive_action_gate(
    absolute_return: Optional[float],
    rs_score: float,
    momentum: float,
    volume_signal: Optional[CompassVolumeSignal],
    market_regime: dict,
) -> tuple[CompassAction, str]:
    """
    Gate-based decision engine. No weights, no scores.

    Three YES/NO gates:
      G1: Is it going up?        (absolute_return > 0)
      G2: Is it beating market?  (rs_score > 0)
      G3: Is it getting stronger? (momentum > 0)

    8 combinations → 5 actions (BUY, HOLD, WATCH variants, AVOID, SELL).
    Volume and market regime act as overrides, not scores.

    Returns (action, reason) where reason explains why.
    """
    g1 = (absolute_return or 0) > 0   # going up?
    g2 = rs_score > 0                 # beating market?
    g3 = momentum > 0                 # getting stronger?

    regime = market_regime.get("regime", "UNKNOWN")

    # ── 8 gate combinations ─────────────────────────────────
    if g1 and g2 and g3:
        # All three pass → BUY (subject to overrides)
        action = CompassAction.BUY
        reason = "Rising, outperforming, and strengthening"

    elif g1 and g2 and not g3:
        # Rising and outperforming but momentum fading
        action = CompassAction.HOLD
        reason = "Outperforming but momentum fading — tighten stops, no new entry"

    elif g1 and not g2 and g3:
        # Rising and gaining momentum but still lagging market
        action = CompassAction.WATCH_EMERGING
        reason = "Rising but lagging market. Watch for RS crossing above 0"

    elif g1 and not g2 and not g3:
        # Rising but underperforming and momentum fading
        action = CompassAction.AVOID
        reason = "Rising but underperforming with fading momentum"

    elif not g1 and g2 and g3:
        # Falling but outperforming market and strengthening
        action = CompassAction.WATCH_RELATIVE
        reason = "Outperforming but price still falling. Watch for absolute return turning positive"

    elif not g1 and g2 and not g3:
        # Falling, was outperforming, now losing edge
        action = CompassAction.SELL
        reason = "Falling and losing relative strength edge"

    elif not g1 and not g2 and g3:
        # Everything down but momentum just turned positive
        action = CompassAction.WATCH_EARLY
        reason = "Early reversal signal. Needs RS and price both turning positive"

    else:
        # not g1, not g2, not g3 — everything failing
        action = CompassAction.SELL
        reason = "Falling, underperforming, and weakening"

    # ── Volume override ─────────────────────────────────────
    if action == CompassAction.BUY and volume_signal == CompassVolumeSignal.DISTRIBUTION:
        action = CompassAction.HOLD
        reason = "All gates pass but smart money selling (distribution volume) — hold, don't add"

    # Add volume note to WATCH actions
    if action in (CompassAction.WATCH_EMERGING, CompassAction.WATCH_RELATIVE, CompassAction.WATCH_EARLY):
        if volume_signal == CompassVolumeSignal.ACCUMULATION:
            reason += ". Volume confirms accumulation — higher probability setup"

    # ── Market regime override ──────────────────────────────
    if regime == "BEAR" and action == CompassAction.BUY:
        action = CompassAction.HOLD
        reason = "All gates pass but market in BEAR regime — hold only, no new buys"

    if regime == "CORRECTION" and action == CompassAction.BUY:
        # In CORRECTION, BUY needs volume to NOT be DISTRIBUTION or WEAK_RALLY
        if volume_signal in (CompassVolumeSignal.DISTRIBUTION, CompassVolumeSignal.WEAK_RALLY):
            action = CompassAction.HOLD
            reason = "All gates pass but CORRECTION regime with weak/distribution volume — hold, wait for volume confirmation"

    return action, reason


def _build_rich_reason(
    display_name: str,
    action: CompassAction,
    base_reason: str,
    rs_score: float,
    absolute_return: Optional[float],
    momentum: float,
    volume_signal: Optional[CompassVolumeSignal],
    pe_ratio: Optional[float],
    pe_zone: Optional[str],
    market_regime: str,
) -> str:
    """Build a sector-specific reason with actual numbers and P/E commentary."""
    abs_val = absolute_return if absolute_return is not None else 0
    parts: list[str] = []

    # Gate status with actual numbers
    g1_str = f"{'up' if abs_val > 0 else 'down'} {abs(round(abs_val, 1))}%"
    g2_str = f"{'outperforming' if rs_score > 0 else 'underperforming'} by {abs(round(rs_score, 1))}%"
    g3_str = f"momentum {'gaining' if momentum > 0 else 'fading'} ({'+' if momentum > 0 else ''}{round(momentum, 1)})"

    parts.append(f"{display_name} is {g1_str}, {g2_str} vs benchmark, {g3_str}.")

    # Volume context
    if volume_signal:
        vol_map = {
            CompassVolumeSignal.ACCUMULATION: "Volume shows accumulation (smart money buying)",
            CompassVolumeSignal.DISTRIBUTION: "Volume shows distribution (smart money selling)",
            CompassVolumeSignal.WEAK_RALLY: "Volume is thinning on the rise (weak rally)",
            CompassVolumeSignal.WEAK_DECLINE: "Volume is drying up on the decline (selling exhaustion)",
        }
        parts.append(vol_map.get(volume_signal, ""))

    # P/E commentary
    if pe_ratio is not None and pe_zone:
        pe_comments = {
            "VALUE": f"Trades at {pe_ratio:.0f}x P/E — in value territory, attractive entry if action confirms.",
            "FAIR": f"Trades at {pe_ratio:.0f}x P/E — fairly valued, no valuation edge.",
            "STRETCHED": f"Trades at {pe_ratio:.0f}x P/E — stretched valuations, limited upside margin.",
            "EXPENSIVE": f"Trades at {pe_ratio:.0f}x P/E — expensive, any weakness could correct sharply.",
        }
        parts.append(pe_comments.get(pe_zone, ""))

    # Market regime context (only if it's affecting the action)
    if market_regime == "BEAR":
        parts.append("Market is in BEAR regime — capital preservation priority.")
    elif market_regime == "CORRECTION":
        parts.append("Market in CORRECTION — selectivity required.")

    return " ".join(p for p in parts if p)


def compute_sector_rs_scores(
    db: Session,
    base_index: str = "NIFTY",
    period_key: str = "3M",
) -> list[dict]:
    """
    Compute RS scores for all sector indices vs base index.
    RS Score = relative return ratio: (sector_return / benchmark_return - 1) * 100
    Positive = outperforming benchmark. Negative = underperforming.
    Momentum = change in RS Score over 4 weeks.
    """
    period_days = PERIOD_DAYS_MAP.get(period_key, 63)
    benchmark_closes = _get_index_close_map(db, base_index, days=period_days + TRADING_DAYS_4W + 60)

    if not benchmark_closes:
        logger.warning("No benchmark data for %s", base_index)
        return []

    # Step 1: compute RS Score (relative return ratio) for all sectors
    sector_data: list[tuple[str, str, float]] = []  # (key, display_name, rs_score)
    for sector_key, display_name in COMPASS_SECTOR_INDICES:
        sector_closes = _get_index_close_map(db, sector_key, days=period_days + TRADING_DAYS_4W + 60)
        if not sector_closes:
            continue
        rel_return = _compute_relative_return(sector_closes, benchmark_closes, period_days)
        if rel_return is not None:
            sector_data.append((sector_key, display_name, rel_return))

    if not sector_data:
        return []

    # Step 2: compute momentum — RS Score 4 weeks ago vs now
    past_rs_map: dict[str, float] = {}
    for sector_key, display_name in COMPASS_SECTOR_INDICES:
        sector_closes = _get_index_close_map(db, sector_key, days=period_days + TRADING_DAYS_4W + 60)
        if not sector_closes:
            continue
        dates = sorted(sector_closes.keys())
        if len(dates) < TRADING_DAYS_4W + period_days // 2:
            continue

        shifted_closes = {d: sector_closes[d] for d in dates[:-TRADING_DAYS_4W]}
        bench_dates = sorted(benchmark_closes.keys())
        if len(bench_dates) > TRADING_DAYS_4W:
            shifted_bench = {d: benchmark_closes[d] for d in bench_dates[:-TRADING_DAYS_4W] if d in benchmark_closes}
        else:
            shifted_bench = benchmark_closes

        past_rel = _compute_relative_return(shifted_closes, shifted_bench, period_days)
        if past_rel is not None:
            past_rs_map[sector_key] = past_rel

    # Step 3: fetch P/E ratios (cached)
    pe_cache = _get_cached_sector_pe(db)

    # Step 4: market regime — is NIFTY in bull/bear/correction?
    market_regime = _compute_market_regime(benchmark_closes)
    logger.info("Market regime: %s (drawdown: %s%%, 3M: %s%%)",
                market_regime["regime"], market_regime["drawdown_pct"],
                market_regime.get("ret_3m", "?"))

    # Step 5: compute absolute returns for each sector
    # Reuse sector_closes from step 1 (already fetched with sufficient lookback)
    abs_return_map: dict[str, float] = {}
    for sector_key, display_name in COMPASS_SECTOR_INDICES:
        sector_closes = _get_index_close_map(db, sector_key, days=period_days + TRADING_DAYS_4W + 60)
        if sector_closes:
            abs_ret = _compute_absolute_return(sector_closes, period_days)
            if abs_ret is not None:
                abs_return_map[sector_key] = abs_ret
            else:
                logger.debug("Abs return None for %s: %d data points, period=%d",
                             sector_key, len(sector_closes), period_days)

    # Step 6: build results with gate-based decision engine
    results = []
    for sector_key, display_name, rs_score in sector_data:
        past_rs = past_rs_map.get(sector_key, rs_score)
        momentum = rs_score - past_rs

        # Volume signal from sector ETF
        etfs = COMPASS_SECTOR_ETF_MAP.get(sector_key, [])
        volume_signal = None
        if etfs:
            etf_vol_data = _get_etf_volume_series(db, etfs[0])
            if etf_vol_data and len(etf_vol_data) >= 60:
                volume_signal = _compute_volume_signal(etf_vol_data)

        quadrant = _classify_quadrant(rs_score, momentum)
        abs_return = abs_return_map.get(sector_key)
        pe_ratio = pe_cache.get(sector_key)
        action, base_reason = _derive_action_gate(abs_return, rs_score, momentum, volume_signal, market_regime)
        pe_zone = _classify_pe_zone(pe_ratio)
        rich_reason = _build_rich_reason(
            display_name, action, base_reason, rs_score, abs_return,
            momentum, volume_signal, pe_ratio, pe_zone, market_regime["regime"],
        )

        results.append({
            "sector_key": sector_key,
            "display_name": display_name,
            "rs_score": round(rs_score, 2),
            "rs_momentum": round(momentum, 2),
            "relative_return": round(rs_score, 2),
            "absolute_return": round(abs_return, 2) if abs_return is not None else None,
            "volume_signal": volume_signal.value if volume_signal else None,
            "quadrant": quadrant.value,
            "action": action.value,
            "action_reason": rich_reason,
            "pe_ratio": pe_ratio,
            "pe_zone": pe_zone,
            "etfs": etfs,
            "category": _get_sector_category(sector_key),
            "market_regime": market_regime["regime"],
        })

    return results


def _get_etf_volume_series(db: Session, ticker: str, days: int = 80) -> list[dict]:
    """Get recent price+volume series for an ETF."""
    cutoff = (datetime.now() - timedelta(days=days + 30)).strftime("%Y-%m-%d")
    rows = (
        db.query(CompassETFPrice.date, CompassETFPrice.close, CompassETFPrice.volume)
        .filter(CompassETFPrice.ticker == ticker, CompassETFPrice.date >= cutoff)
        .order_by(CompassETFPrice.date)
        .all()
    )
    return [{"date": r.date, "close": r.close, "volume": r.volume} for r in rows]


def compute_stock_rs_scores(
    db: Session,
    sector_key: str,
    base_index: str = "NIFTY",
    period_key: str = "3M",
) -> list[dict]:
    """
    Compute RS scores for all stocks within a sector.
    RS Score = relative return ratio vs SECTOR index (% outperformance).
    Positive = beating sector, negative = lagging sector.
    """
    period_days = PERIOD_DAYS_MAP.get(period_key, 63)
    display_name = NSE_DISPLAY_MAP.get(sector_key, sector_key)

    # Sector index as benchmark for stocks
    sector_closes = _get_index_close_map(db, sector_key, days=period_days + TRADING_DAYS_4W + 60)
    if not sector_closes:
        logger.warning("No sector data for %s", sector_key)
        return []

    # Get constituents
    constituents = (
        db.query(IndexConstituent)
        .filter(IndexConstituent.index_name == display_name)
        .all()
    )
    if not constituents:
        return []

    # Step 1: RS Score (relative return ratio) for each stock vs sector
    stock_data: list[tuple[str, str, float, Optional[float]]] = []
    for c in constituents:
        stock_closes = _get_stock_close_map(db, c.ticker, days=period_days + TRADING_DAYS_4W + 60)
        if not stock_closes:
            continue
        rel_return = _compute_relative_return(stock_closes, sector_closes, period_days)
        if rel_return is not None:
            stock_data.append((c.ticker, c.company_name or c.ticker, rel_return, c.weight_pct))

    if not stock_data:
        return []

    # Step 2: momentum (RS score 4 weeks ago vs now)
    past_rs_map: dict[str, float] = {}
    for c in constituents:
        stock_closes = _get_stock_close_map(db, c.ticker, days=period_days + TRADING_DAYS_4W + 60)
        if not stock_closes:
            continue
        dates = sorted(stock_closes.keys())
        if len(dates) < TRADING_DAYS_4W + period_days // 2:
            continue
        shifted_closes = {d: stock_closes[d] for d in dates[:-TRADING_DAYS_4W]}

        bench_dates = sorted(sector_closes.keys())
        if len(bench_dates) > TRADING_DAYS_4W:
            shifted_bench = {d: sector_closes[d] for d in bench_dates[:-TRADING_DAYS_4W]}
        else:
            shifted_bench = sector_closes

        past_rel = _compute_relative_return(shifted_closes, shifted_bench, period_days)
        if past_rel is not None:
            past_rs_map[c.ticker] = past_rel

    # Step 3: fetch P/E for stocks (threaded)
    stock_tickers = [t for t, _, _, _ in stock_data]
    pe_map = fetch_pe_ratios_for_stocks(stock_tickers)

    # Step 4: market regime + absolute returns for stocks
    benchmark_closes = _get_index_close_map(db, base_index, days=period_days + TRADING_DAYS_4W + 60)
    market_regime = _compute_market_regime(benchmark_closes) if benchmark_closes else {"regime": "UNKNOWN"}

    # Step 5: build results with gate-based engine
    results = []
    for ticker, name, rs_score, weight_pct in stock_data:
        past_rs = past_rs_map.get(ticker, rs_score)
        momentum = rs_score - past_rs

        vol_data = _get_stock_volume_series(db, ticker)
        volume_signal = _compute_volume_signal(vol_data) if vol_data else None

        stock_closes = _get_stock_close_map(db, ticker, days=period_days + 60)
        abs_return = _compute_absolute_return(stock_closes, period_days) if stock_closes else None

        quadrant = _classify_quadrant(rs_score, momentum)
        pe_ratio = pe_map.get(ticker)
        action, base_reason = _derive_action_gate(abs_return, rs_score, momentum, volume_signal, market_regime)
        pe_zone = _classify_pe_zone(pe_ratio)
        rich_reason = _build_rich_reason(
            name, action, base_reason, rs_score, abs_return,
            momentum, volume_signal, pe_ratio, pe_zone, market_regime["regime"],
        )

        results.append({
            "ticker": ticker,
            "company_name": name,
            "rs_score": round(rs_score, 2),
            "rs_momentum": round(momentum, 2),
            "relative_return": round(rs_score, 2),
            "absolute_return": round(abs_return, 2) if abs_return is not None else None,
            "volume_signal": volume_signal.value if volume_signal else None,
            "quadrant": quadrant.value,
            "action": action.value,
            "action_reason": rich_reason,
            "pe_ratio": pe_ratio,
            "pe_zone": pe_zone,
            "weight_pct": weight_pct,
        })

    results.sort(key=lambda x: x["rs_score"], reverse=True)
    return results


def compute_etf_rs_scores(
    db: Session,
    base_index: str = "NIFTY",
    period_key: str = "3M",
) -> list[dict]:
    """Compute RS scores for all sector ETFs vs NIFTY. RS = relative return ratio."""
    period_days = PERIOD_DAYS_MAP.get(period_key, 63)
    benchmark_closes = _get_index_close_map(db, base_index, days=period_days + TRADING_DAYS_4W + 60)

    if not benchmark_closes:
        return []

    # Step 1: current RS Score for each ETF
    etf_data: list[tuple[str, str, float]] = []
    for etf_ticker, yf_symbol in COMPASS_ETF_UNIVERSE.items():
        etf_closes = _get_etf_close_map(db, etf_ticker, days=period_days + TRADING_DAYS_4W + 60)
        if not etf_closes:
            continue
        rel_return = _compute_relative_return(etf_closes, benchmark_closes, period_days)
        if rel_return is not None:
            parent = None
            for sk, etfs in COMPASS_SECTOR_ETF_MAP.items():
                if etf_ticker in etfs:
                    parent = sk
                    break
            etf_data.append((etf_ticker, parent or "", rel_return))

    if not etf_data:
        return []

    # Step 2: compute momentum (RS 4 weeks ago)
    past_rs_map: dict[str, float] = {}
    for etf_ticker, yf_symbol in COMPASS_ETF_UNIVERSE.items():
        etf_closes = _get_etf_close_map(db, etf_ticker, days=period_days + TRADING_DAYS_4W + 60)
        if not etf_closes:
            continue
        dates = sorted(etf_closes.keys())
        if len(dates) < TRADING_DAYS_4W + period_days // 2:
            continue
        shifted_closes = {d: etf_closes[d] for d in dates[:-TRADING_DAYS_4W]}
        bench_dates = sorted(benchmark_closes.keys())
        if len(bench_dates) > TRADING_DAYS_4W:
            shifted_bench = {d: benchmark_closes[d] for d in bench_dates[:-TRADING_DAYS_4W] if d in benchmark_closes}
        else:
            shifted_bench = benchmark_closes
        past_rel = _compute_relative_return(shifted_closes, shifted_bench, period_days)
        if past_rel is not None:
            past_rs_map[etf_ticker] = past_rel

    market_regime = _compute_market_regime(benchmark_closes)

    results = []
    for ticker, parent_sector, rs_score in etf_data:
        past_rs = past_rs_map.get(ticker, rs_score)
        momentum = rs_score - past_rs

        vol_data = _get_etf_volume_series(db, ticker)
        volume_signal = _compute_volume_signal(vol_data) if vol_data and len(vol_data) >= 60 else None

        etf_closes = _get_etf_close_map(db, ticker, days=period_days + 60)
        abs_return = _compute_absolute_return(etf_closes, period_days) if etf_closes else None

        quadrant = _classify_quadrant(rs_score, momentum)
        action, base_reason = _derive_action_gate(abs_return, rs_score, momentum, volume_signal, market_regime)
        rich_reason = _build_rich_reason(
            ticker, action, base_reason, rs_score, abs_return,
            momentum, volume_signal, None, None, market_regime["regime"],
        )

        # Resolve display name: sector name > asset class > empty
        if parent_sector:
            sector_display = NSE_DISPLAY_MAP.get(parent_sector, parent_sector)
        else:
            sector_display = ETF_ASSET_CLASS.get(ticker)

        results.append({
            "ticker": ticker,
            "parent_sector": parent_sector,
            "sector_name": sector_display,
            "rs_score": round(rs_score, 2),
            "rs_momentum": round(momentum, 2),
            "relative_return": round(rs_score, 2),
            "absolute_return": round(abs_return, 2) if abs_return is not None else None,
            "volume_signal": volume_signal.value if volume_signal else None,
            "quadrant": quadrant.value,
            "action": action.value,
            "action_reason": rich_reason,
        })

    results.sort(key=lambda x: x["rs_score"], reverse=True)
    return results


def compute_annualized_volatility(closes: dict[str, float], lookback: int = 60) -> Optional[float]:
    """Compute annualized volatility from daily close prices (std of log returns * sqrt(252))."""
    import math
    dates = sorted(closes.keys())
    if len(dates) < max(20, lookback // 2):
        return None
    recent = dates[-lookback:] if len(dates) >= lookback else dates
    prices = [closes[d] for d in recent]

    log_returns = []
    for i in range(1, len(prices)):
        if prices[i] > 0 and prices[i - 1] > 0:
            log_returns.append(math.log(prices[i] / prices[i - 1]))

    if len(log_returns) < 10:
        return None

    mean = sum(log_returns) / len(log_returns)
    variance = sum((r - mean) ** 2 for r in log_returns) / (len(log_returns) - 1)
    daily_vol = variance ** 0.5
    return round(daily_vol * (252 ** 0.5) * 100, 2)  # annualized, as %


def persist_rs_scores(db: Session, scores: list[dict], instrument_type: str, date_str: Optional[str] = None) -> int:
    """Save computed RS scores to compass_rs_scores table."""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    stored = 0
    for s in scores:
        inst_id = s.get("sector_key") or s.get("ticker", "")
        existing = (
            db.query(CompassRSScore)
            .filter_by(date=date_str, instrument_id=inst_id, instrument_type=instrument_type)
            .first()
        )
        if existing:
            existing.rs_score = s["rs_score"]
            existing.rs_momentum = s["rs_momentum"]
            existing.volume_signal = s.get("volume_signal")
            existing.quadrant = s["quadrant"]
            existing.action = s["action"]
            existing.relative_return = s.get("relative_return")
            existing.pe_ratio = s.get("pe_ratio")
            existing.stop_loss_pct = s.get("stop_loss_pct")
        else:
            db.add(CompassRSScore(
                date=date_str,
                instrument_id=inst_id,
                instrument_type=instrument_type,
                parent_sector=s.get("parent_sector"),
                rs_score=s["rs_score"],
                rs_momentum=s["rs_momentum"],
                volume_signal=s.get("volume_signal"),
                quadrant=s["quadrant"],
                action=s["action"],
                relative_return=s.get("relative_return"),
                pe_ratio=s.get("pe_ratio"),
                market_cap_cr=s.get("market_cap_cr"),
                stop_loss_pct=s.get("stop_loss_pct"),
            ))
        stored += 1

    db.commit()
    return stored


# ─── P/E Cache ────────────────────────────────────────
# P/E ratios from yfinance are slow (1 call per index).
# Cache for 24h so they only refresh once daily.
_pe_cache: dict[str, Optional[float]] = {}
_pe_cache_ts: float = 0
PE_CACHE_TTL = 86400  # 24 hours


def _get_cached_sector_pe(db: Session) -> dict[str, Optional[float]]:
    """Get P/E ratios for sector indices, cached for 24h."""
    import time
    global _pe_cache, _pe_cache_ts

    if _pe_cache and (time.time() - _pe_cache_ts) < PE_CACHE_TTL:
        return _pe_cache

    # Fetch in background — don't block if it fails
    try:
        sector_keys = [sk for sk, _ in COMPASS_SECTOR_INDICES]
        _pe_cache = fetch_pe_ratios_for_sectors(sector_keys)
        _pe_cache_ts = time.time()
        logger.info("P/E cache refreshed: %d sectors", len(_pe_cache))
    except Exception as e:
        logger.warning("P/E cache refresh failed: %s", e)

    return _pe_cache


def fetch_pe_ratios_for_sectors(sector_keys: list[str]) -> dict[str, Optional[float]]:
    """Fetch P/E ratios for sector indices via yfinance.

    Strategy: try index ticker first, then fall back to sector ETF's P/E.
    ETFs usually have trailingPE even when index tickers don't.
    """
    from index_constants import NSE_TICKER_MAP
    import yfinance as yf
    from concurrent.futures import ThreadPoolExecutor

    result: dict[str, Optional[float]] = {}

    def _fetch_pe(key: str) -> tuple[str, Optional[float]]:
        # Try 1: index ticker (e.g. ^CNXPHARMA)
        yf_symbol = NSE_TICKER_MAP.get(key)
        if yf_symbol:
            try:
                info = yf.Ticker(yf_symbol).info
                pe = info.get("trailingPE") or info.get("forwardPE")
                if pe:
                    return key, round(float(pe), 2)
            except Exception:
                pass

        # Try 2: sector ETF (e.g. PHARMABEES.NS)
        etfs = COMPASS_SECTOR_ETF_MAP.get(key, [])
        for etf_ticker in etfs:
            try:
                info = yf.Ticker(f"{etf_ticker}.NS").info
                pe = info.get("trailingPE") or info.get("forwardPE")
                if pe:
                    return key, round(float(pe), 2)
            except Exception:
                pass

        return key, None

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_fetch_pe, k) for k in sector_keys]
        for f in futures:
            key, pe = f.result()
            result[key] = pe

    return result


def fetch_pe_ratios_for_stocks(tickers: list[str]) -> dict[str, Optional[float]]:
    """Fetch P/E ratios for stocks via yfinance in batches."""
    import yfinance as yf
    from concurrent.futures import ThreadPoolExecutor

    result: dict[str, Optional[float]] = {}

    def _fetch_one(ticker: str) -> tuple[str, Optional[float]]:
        try:
            info = yf.Ticker(f"{ticker}.NS").info
            if info is None:
                return ticker, None
            pe = info.get("trailingPE") or info.get("forwardPE")
            return ticker, round(float(pe), 2) if pe else None
        except Exception:
            return ticker, None

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_fetch_one, t) for t in tickers]
        for f in futures:
            ticker, pe = f.result()
            result[ticker] = pe

    return result
