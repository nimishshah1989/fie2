"""
FIE v3 — Microbasket Business Logic Service
Basket NAV computation, backfill, live values, and ratio return helpers.
Basket daily NAV is stored in IndexPrice with index_name = "MB_{SLUG}",
reusing all existing ratio return infrastructure with zero changes.
"""

import logging
import math
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from models import IndexPrice, Microbasket, MicrobasketConstituent, BasketStatus
from services.data_helpers import upsert_price_row

logger = logging.getLogger("fie_v3.baskets")

MB_PREFIX = "MB_"


def basket_slug(name: str) -> str:
    """Generate a slug like 'MB_HEALTHCARE' from a basket name."""
    clean = re.sub(r"[^A-Z0-9]+", "_", name.upper().strip()).strip("_")
    return f"{MB_PREFIX}{clean}"


def is_basket_ticker(ticker: str) -> bool:
    """Check if a ticker represents a microbasket (starts with MB_)."""
    return ticker.upper().startswith(MB_PREFIX)


def compute_basket_value_from_db(
    constituents: List[MicrobasketConstituent],
    date_str: str,
    db: Session,
) -> Optional[float]:
    """Compute weighted basket value on a given date using DB prices.
    basket_value = sum(weight_pct/100 * close_price) for each constituent.
    Returns None if any constituent is missing price data for that date.
    """
    total = 0.0
    for c in constituents:
        price_row = (
            db.query(IndexPrice)
            .filter(IndexPrice.index_name == c.ticker, IndexPrice.date <= date_str)
            .order_by(desc(IndexPrice.date))
            .first()
        )
        if not price_row or not price_row.close_price:
            return None
        # Only use prices within 5 trading days of target
        row_date = datetime.strptime(price_row.date, "%Y-%m-%d")
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        if (target_date - row_date).days > 7:
            return None
        total += (c.weight_pct / 100.0) * price_row.close_price
    return round(total, 4) if total > 0 else None


def compute_basket_live_value(
    constituents: List[MicrobasketConstituent],
) -> Optional[Dict]:
    """Compute live basket value using Yahoo Finance prices.
    Returns {current_price, constituents: [{ticker, weight_pct, price, weighted_value}]}
    """
    from services.portfolio_service import fetch_live_price, get_yahoo_symbol

    total = 0.0
    details = []
    for c in constituents:
        yf_sym = get_yahoo_symbol(c.ticker)
        if not yf_sym:
            continue
        price_data = fetch_live_price(yf_sym)
        price = price_data.get("current_price") if price_data else None
        weighted = (c.weight_pct / 100.0) * price if price else 0.0
        total += weighted
        details.append({
            "ticker": c.ticker,
            "company_name": c.company_name,
            "weight_pct": c.weight_pct,
            "current_price": price,
            "weighted_value": round(weighted, 4) if price else None,
        })

    if total <= 0:
        return None

    return {
        "current_price": round(total, 4),
        "constituents": details,
    }


def backfill_basket_nav(
    basket: Microbasket,
    db: Session,
    days: int = 365,
) -> int:
    """Compute daily NAV for a basket over the past N days, store in IndexPrice.
    Returns count of records stored."""
    slug = basket.slug
    constituents = basket.constituents
    if not constituents:
        return 0

    stored = 0
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    current = start_date

    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        # Skip weekends
        if current.weekday() < 5:
            value = compute_basket_value_from_db(constituents, date_str, db)
            if value is not None:
                row = {"date": date_str, "close": value, "open": None, "high": None, "low": None, "volume": None}
                if upsert_price_row(db, slug, row):
                    stored += 1
        current += timedelta(days=1)

    if stored > 0:
        db.commit()
        logger.info("Basket backfill: %s — %d NAV records stored", slug, stored)
    return stored


def get_all_basket_constituent_tickers(db: Session) -> List[str]:
    """Return unique tickers across all active basket constituents."""
    rows = (
        db.query(MicrobasketConstituent.ticker)
        .join(Microbasket, MicrobasketConstituent.basket_id == Microbasket.id)
        .filter(Microbasket.status == BasketStatus.ACTIVE)
        .distinct()
        .all()
    )
    return [r[0] for r in rows if r[0]]


def compute_constituent_units(
    constituents: List[MicrobasketConstituent],
    portfolio_size: float,
    db: Session,
) -> List[Dict]:
    """Compute units per constituent based on portfolio size and latest prices.
    units = (weight_pct / 100) * portfolio_size / last_price
    Uses a single batch query for all constituent prices.
    """
    from sqlalchemy import func as sqlfunc

    # Batch-fetch latest prices for all tickers (1 query instead of N)
    tickers = [c.ticker for c in constituents]
    subq = (
        db.query(IndexPrice.index_name, sqlfunc.max(IndexPrice.date).label("max_date"))
        .filter(IndexPrice.index_name.in_(tickers))
        .group_by(IndexPrice.index_name)
        .subquery()
    )
    price_rows = (
        db.query(IndexPrice.index_name, IndexPrice.close_price)
        .join(subq, (IndexPrice.index_name == subq.c.index_name) & (IndexPrice.date == subq.c.max_date))
        .all()
    )
    price_map = {r[0]: r[1] for r in price_rows if r[1]}

    results = []
    for c in constituents:
        current_price = price_map.get(c.ticker)
        allocated_amount = (c.weight_pct / 100.0) * portfolio_size
        computed_units = None
        if current_price and current_price > 0:
            computed_units = math.floor(allocated_amount / current_price)

        results.append({
            "ticker": c.ticker,
            "company_name": c.company_name,
            "weight_pct": c.weight_pct,
            "current_price": current_price,
            "computed_units": computed_units,
            "allocated_amount": round(allocated_amount, 2),
        })
    return results


def compute_today_basket_navs(db: Session) -> int:
    """Compute today's NAV for all active baskets from constituent DB prices.
    Called by scheduled EOD job after constituent prices are fetched."""
    baskets = db.query(Microbasket).filter(Microbasket.status == BasketStatus.ACTIVE).all()
    if not baskets:
        return 0

    today_str = datetime.now().strftime("%Y-%m-%d")
    stored = 0
    for basket in baskets:
        value = compute_basket_value_from_db(basket.constituents, today_str, db)
        if value is not None:
            row = {"date": today_str, "close": value, "open": None, "high": None, "low": None, "volume": None}
            if upsert_price_row(db, basket.slug, row):
                stored += 1

    if stored > 0:
        db.commit()
        logger.info("Basket EOD: computed NAV for %d/%d active baskets", stored, len(baskets))
    return stored
