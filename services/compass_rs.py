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


def _derive_action(
    quadrant: CompassQuadrant,
    volume_signal: Optional[CompassVolumeSignal],
) -> CompassAction:
    """
    Quadrant → Action signal. Simple 4-action model:
    - LEADING  → BUY  (outperforming + gaining momentum)
    - WEAKENING → HOLD (outperforming but momentum fading)
    - IMPROVING → WATCH (underperforming but momentum turning up)
    - LAGGING  → SELL (underperforming + losing momentum)
    """
    if quadrant == CompassQuadrant.LEADING:
        return CompassAction.BUY
    elif quadrant == CompassQuadrant.WEAKENING:
        return CompassAction.HOLD
    elif quadrant == CompassQuadrant.IMPROVING:
        return CompassAction.WATCH
    else:  # LAGGING
        return CompassAction.SELL


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

    # Step 4: build results
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
        action = _derive_action(quadrant, volume_signal)

        results.append({
            "sector_key": sector_key,
            "display_name": display_name,
            "rs_score": round(rs_score, 2),
            "rs_momentum": round(momentum, 2),
            "relative_return": round(rs_score, 2),  # same as rs_score now
            "volume_signal": volume_signal.value if volume_signal else None,
            "quadrant": quadrant.value,
            "action": action.value,
            "etfs": etfs,
            "category": _get_sector_category(sector_key),
            "pe_ratio": pe_cache.get(sector_key),
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

    # Step 4: build results
    results = []
    for ticker, name, rs_score, weight_pct in stock_data:
        past_rs = past_rs_map.get(ticker, rs_score)
        momentum = rs_score - past_rs

        vol_data = _get_stock_volume_series(db, ticker)
        volume_signal = _compute_volume_signal(vol_data) if vol_data else None

        quadrant = _classify_quadrant(rs_score, momentum)
        action = _derive_action(quadrant, volume_signal)

        stop_loss_pct = 12.0 if action == CompassAction.BUY else None

        results.append({
            "ticker": ticker,
            "company_name": name,
            "rs_score": round(rs_score, 2),
            "rs_momentum": round(momentum, 2),
            "relative_return": round(rs_score, 2),
            "volume_signal": volume_signal.value if volume_signal else None,
            "quadrant": quadrant.value,
            "action": action.value,
            "weight_pct": weight_pct,
            "stop_loss_pct": stop_loss_pct,
            "pe_ratio": pe_map.get(ticker),
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

    results = []
    for ticker, parent_sector, rs_score in etf_data:
        past_rs = past_rs_map.get(ticker, rs_score)
        momentum = rs_score - past_rs

        vol_data = _get_etf_volume_series(db, ticker)
        volume_signal = _compute_volume_signal(vol_data) if vol_data and len(vol_data) >= 60 else None

        quadrant = _classify_quadrant(rs_score, momentum)
        action = _derive_action(quadrant, volume_signal)

        results.append({
            "ticker": ticker,
            "parent_sector": parent_sector,
            "sector_name": NSE_DISPLAY_MAP.get(parent_sector, parent_sector) if parent_sector else None,
            "rs_score": round(rs_score, 2),
            "rs_momentum": round(momentum, 2),
            "relative_return": round(rs_score, 2),
            "volume_signal": volume_signal.value if volume_signal else None,
            "quadrant": quadrant.value,
            "action": action.value,
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
