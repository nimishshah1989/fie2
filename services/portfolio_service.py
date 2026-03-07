"""
FIE v3 — Portfolio Business Logic Service
Live price fetching, NAV computation, XIRR, drawdown, and allocation helpers.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from cachetools import TTLCache
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from models import (
    IndexPrice,
    PortfolioHolding,
    PortfolioNAV,
    PortfolioTransaction,
    TransactionType,
)

logger = logging.getLogger("fie_v3.portfolio")


# ─── Yahoo Finance Symbol Map (portfolio-specific overrides) ────────
YAHOO_SYMBOL_MAP: Dict[str, Optional[str]] = {
    "LIQUIDCASE": "LIQUIDCASE.NS",
    "CPSEETF": "CPSEETF.NS",
    "METALETF": "METALIETF.NS",
    "SENSEXETF": "SENSEXIETF.NS",
    "MASPTOP50": "MASPTOP50.NS",
    "NETFMID150": "MID150BEES.NS",
    "GROWWDEFNC": "GROWWDEFNC.NS",
    "FMCGIETF": "FMCGIETF.NS",
    "OIL ETF": "OILIETF.NS",
    "NIPPONAMC - NETFAUTO": "NETFAUTO.NS",
}


def get_yahoo_symbol(ticker: str) -> Optional[str]:
    """Map a portfolio ticker to its Yahoo Finance symbol.
    Returns None for microbasket tickers (MB_*) — they use basket NAV, not Yahoo."""
    if ticker.upper().startswith("MB_"):
        return None
    if ticker in YAHOO_SYMBOL_MAP:
        return YAHOO_SYMBOL_MAP[ticker]
    return f"{ticker}.NS"


# ─── Live Price Fetching (httpx + TTLCache) ────────────────────────

_http_client: Optional[httpx.Client] = None

# TTLCache automatically evicts entries after 60s and caps at 500 entries,
# replacing the previous unbounded dict + manual timestamp tracking
_price_cache: TTLCache = TTLCache(maxsize=500, ttl=60)


def _get_http_client() -> httpx.Client:
    """Lazy-init a persistent HTTP client for Yahoo Finance."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.Client(
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
    return _http_client


def fetch_live_price(yf_symbol: str) -> Optional[Dict]:
    """Fetch live price from Yahoo Finance with 60s TTL cache."""
    # TTLCache handles expiry automatically — no manual timestamp check needed
    cached = _price_cache.get(yf_symbol)
    if cached is not None:
        return cached

    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_symbol}"
        f"?interval=1d&range=2d"
    )
    try:
        resp = _get_http_client().get(url)
        if resp.status_code != 200:
            return None
        data = resp.json()
        meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
        current_price = meta.get("regularMarketPrice")
        prev_close = meta.get("previousClose") or meta.get("chartPreviousClose")
        if not current_price:
            return None

        change_pct = None
        if prev_close and prev_close > 0:
            change_pct = round(((current_price / prev_close) - 1) * 100, 2)

        market_time = meta.get("regularMarketTime")
        market_time_str = None
        if market_time:
            try:
                from datetime import timezone
                dt = datetime.fromtimestamp(market_time, tz=timezone.utc)
                market_time_str = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                pass

        price_data = {
            "current_price": current_price,
            "change_pct": change_pct,
            "yf_symbol": yf_symbol,
            "market_time": market_time_str,
        }
        _price_cache[yf_symbol] = price_data
        return price_data
    except Exception as exc:
        logger.debug("Price fetch failed for %s: %s", yf_symbol, exc)
        return None


def get_live_prices(tickers: List[str], overrides: Optional[Dict[str, str]] = None) -> Dict[str, Dict]:
    """Fetch live prices for multiple tickers in parallel (max 8 concurrent).
    overrides: {ticker: yf_symbol} — per-holding overrides from FM, checked first.
    Handles MB_ (microbasket) tickers by computing live basket values.
    Returns dict keyed by ticker -> price data dict. Tickers not found are absent."""
    ticker_to_yf: Dict[str, str] = {}
    basket_tickers: List[str] = []
    override_map = overrides or {}

    for ticker in tickers:
        if ticker.upper().startswith("MB_"):
            basket_tickers.append(ticker.upper())
        else:
            # Priority: per-holding override -> YAHOO_SYMBOL_MAP -> default .NS
            if ticker in override_map and override_map[ticker]:
                ticker_to_yf[ticker] = override_map[ticker]
            else:
                yf_sym = get_yahoo_symbol(ticker)
                if yf_sym:
                    ticker_to_yf[ticker] = yf_sym

    prices: Dict[str, Dict] = {}

    # Fetch regular Yahoo Finance prices
    if ticker_to_yf:
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_ticker = {
                executor.submit(fetch_live_price, yf_sym): ticker
                for ticker, yf_sym in ticker_to_yf.items()
            }
            for future in as_completed(future_to_ticker, timeout=20):
                ticker = future_to_ticker[future]
                try:
                    data = future.result()
                    if data:
                        prices[ticker] = data
                except Exception as exc:
                    logger.debug("Parallel price fetch failed for %s: %s", ticker, exc)

    # Fetch microbasket live prices
    if basket_tickers:
        try:
            from models import BasketStatus, Microbasket, SessionLocal
            from services.basket_service import compute_basket_live_value

            db = SessionLocal()
            for slug in basket_tickers:
                basket = db.query(Microbasket).filter(
                    Microbasket.slug == slug,
                    Microbasket.status == BasketStatus.ACTIVE,
                ).first()
                if basket and basket.constituents:
                    live_data = compute_basket_live_value(basket.constituents)
                    if live_data:
                        prices[slug] = {
                            "current_price": live_data["current_price"],
                            "change_pct": None,
                            "yf_symbol": slug,
                        }
            db.close()
        except Exception as exc:
            logger.debug("Basket live price fetch failed: %s", exc)

    return prices


# ─── Financial Calculations ──────────────────────────────────────────

def compute_xirr(cashflows) -> Optional[float]:
    """Compute XIRR using Newton-Raphson method. cashflows = [(date, amount), ...]"""
    if not cashflows or len(cashflows) < 2:
        return None
    t0 = cashflows[0][0]
    days = [(d - t0).days / 365.0 for d, _ in cashflows]
    amounts = [a for _, a in cashflows]
    rate = 0.1
    for _ in range(100):
        npv = sum(a / (1 + rate) ** t for a, t in zip(amounts, days))
        dnpv = sum(-t * a / (1 + rate) ** (t + 1) for a, t in zip(amounts, days))
        if abs(dnpv) < 1e-12:
            break
        new_rate = rate - npv / dnpv
        if abs(new_rate - rate) < 1e-8:
            return round(new_rate * 100, 2)
        rate = new_rate
        if rate < -0.99 or rate > 100:
            return None
    return round(rate * 100, 2)


def compute_max_drawdown(values) -> Optional[float]:
    """Compute maximum drawdown from a list of portfolio values."""
    if len(values) < 2:
        return None
    peak = values[0]
    max_dd = 0.0
    for val in values:
        if val > peak:
            peak = val
        dd = (val - peak) / peak if peak > 0 else 0
        if dd < max_dd:
            max_dd = dd
    return round(max_dd * 100, 2)


# ─── NAV Computation ────────────────────────────────────────────────

def compute_nav_for_portfolio(portfolio_id: int, date_str: str, db: Session):
    """Compute and store NAV snapshot for a portfolio on a given date.
    Uses batch query to fetch latest prices for all holdings (eliminates N+1)."""
    holdings = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.portfolio_id == portfolio_id, PortfolioHolding.quantity > 0)
        .all()
    )
    if not holdings:
        return None

    # Batch-fetch latest price for each holding ticker on or before date_str
    # instead of querying inside a loop (N+1 -> 1 query)
    tickers = [h.ticker for h in holdings]
    subq = (
        db.query(
            IndexPrice.index_name,
            sa_func.max(IndexPrice.date).label("max_date"),
        )
        .filter(IndexPrice.index_name.in_(tickers), IndexPrice.date <= date_str)
        .group_by(IndexPrice.index_name)
        .subquery()
    )
    price_rows = (
        db.query(IndexPrice.index_name, IndexPrice.close_price)
        .join(subq, (IndexPrice.index_name == subq.c.index_name) & (IndexPrice.date == subq.c.max_date))
        .all()
    )
    price_map = {r[0]: r[1] for r in price_rows if r[1]}

    total_value = 0.0
    total_cost = 0.0
    for h in holdings:
        close = price_map.get(h.ticker) or h.avg_cost
        total_value += h.quantity * close
        total_cost += h.quantity * h.avg_cost

    realized_sum = (
        db.query(sa_func.sum(PortfolioTransaction.realized_pnl))
        .filter(
            PortfolioTransaction.portfolio_id == portfolio_id,
            PortfolioTransaction.txn_type == TransactionType.SELL,
            PortfolioTransaction.txn_date <= date_str,
        )
        .scalar()
    ) or 0.0

    nav = (
        db.query(PortfolioNAV)
        .filter(PortfolioNAV.portfolio_id == portfolio_id, PortfolioNAV.date == date_str)
        .first()
    )
    if not nav:
        nav = PortfolioNAV(portfolio_id=portfolio_id, date=date_str)
        db.add(nav)

    nav.total_value = round(total_value, 2)
    nav.total_cost = round(total_cost, 2)
    nav.unrealized_pnl = round(total_value - total_cost, 2)
    nav.realized_pnl_cumulative = round(realized_sum, 2)
    nav.num_holdings = len([h for h in holdings if h.quantity > 0])
    nav.computed_at = datetime.now()
    db.commit()
    return nav


def empty_totals() -> dict:
    """Return empty portfolio totals structure."""
    return {
        "total_invested": 0.0, "current_value": 0.0, "unrealized_pnl": 0.0,
        "unrealized_pnl_pct": 0.0, "realized_pnl": 0.0, "num_holdings": 0,
    }
