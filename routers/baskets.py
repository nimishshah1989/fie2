"""
FIE v3 — Microbasket Routes
CRUD, CSV upload, and live data with ratio returns for custom stock baskets.
"""

import csv
import io
import logging
import threading
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from models import (
    BasketStatus,
    IndexPrice,
    Microbasket,
    MicrobasketConstituent,
    get_db,
)
from services.basket_service import (
    backfill_basket_nav,
    basket_slug,
    compute_basket_live_value,
    compute_constituent_units,
)
from services.data_helpers import upsert_price_row

logger = logging.getLogger("fie_v3.baskets")
router = APIRouter()


# ─── Pydantic Models ─────────────────────────────────────

class ConstituentPayload(BaseModel):
    ticker: str
    company_name: Optional[str] = None
    weight_pct: float = Field(gt=0, le=100)
    buy_price: Optional[float] = None
    quantity: Optional[int] = None


class CreateBasketRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    benchmark: Optional[str] = "NIFTY"
    portfolio_size: Optional[float] = None
    constituents: List[ConstituentPayload] = Field(min_length=1)


class UpdateBasketRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    benchmark: Optional[str] = None
    portfolio_size: Optional[float] = None
    constituents: Optional[List[ConstituentPayload]] = None


# ─── Background NAV Builder ──────────────────────────────

def _background_basket_build(basket_id: int):
    """Background thread: fetch constituent history + compute basket NAV series.
    Also auto-captures buy_price for constituents where it's NULL."""
    from models import SessionLocal
    from price_service import fetch_yfinance_bulk_stock_history
    from services.basket_service import compute_basket_value_from_db

    try:
        db = SessionLocal()
        basket = db.get(Microbasket, basket_id)
        if not basket:
            db.close()
            return

        # Fetch 1Y history for all constituents
        tickers = [c.ticker for c in basket.constituents]
        logger.info("Basket build: fetching 1Y history for %d tickers (%s)", len(tickers), basket.slug)
        stock_data = fetch_yfinance_bulk_stock_history(tickers, period="1y")
        stored = 0
        for ticker, rows in stock_data.items():
            for row in rows:
                if upsert_price_row(db, ticker, row):
                    stored += 1
        db.commit()
        logger.info("Basket build: stored %d constituent price records", stored)

        # Auto-capture buy_price for constituents where it's NULL
        null_buy = [c for c in basket.constituents if c.buy_price is None]
        if null_buy:
            # Batch-fetch latest price for each constituent from IndexPrice
            from sqlalchemy import func as sqlfunc
            null_tickers = [c.ticker for c in null_buy]
            subq = (
                db.query(
                    IndexPrice.index_name,
                    sqlfunc.max(IndexPrice.date).label("max_date"),
                )
                .filter(IndexPrice.index_name.in_(null_tickers))
                .group_by(IndexPrice.index_name)
                .subquery()
            )
            price_rows = (
                db.query(IndexPrice.index_name, IndexPrice.close_price)
                .join(subq, (IndexPrice.index_name == subq.c.index_name) & (IndexPrice.date == subq.c.max_date))
                .all()
            )
            price_map = {r[0]: r[1] for r in price_rows if r[1]}

            filled = 0
            for c in null_buy:
                latest_price = price_map.get(c.ticker)
                if latest_price:
                    c.buy_price = latest_price
                    filled += 1
            if filled:
                db.commit()
                logger.info("Basket build: auto-captured buy_price for %d/%d constituents", filled, len(null_buy))

        # Compute basket NAV series (1Y history)
        nav_count = backfill_basket_nav(basket, db, days=365)
        logger.info("Basket build: %s — %d NAV records computed", basket.slug, nav_count)

        # Compute today's NAV explicitly (creation day may not be in 1Y backfill range)
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_value = compute_basket_value_from_db(basket.constituents, today_str, db)
        if today_value is not None:
            row = {"date": today_str, "close": today_value, "open": None, "high": None, "low": None, "volume": None}
            if upsert_price_row(db, basket.slug, row):
                db.commit()
                logger.info("Basket build: stored today's NAV %.4f for %s", today_value, basket.slug)

        db.close()
    except Exception as e:
        logger.warning("Background basket build failed for basket %d: %s", basket_id, e)


# ─── CRUD Endpoints ──────────────────────────────────────

@router.post(
    "/api/baskets",
    tags=["Microbaskets"],
    summary="Create microbasket",
    description="Creates a new microbasket with weighted constituents. Validates that weights sum to ~100%. Triggers background NAV computation after creation.",
)
async def create_basket(req: CreateBasketRequest, db: Session = Depends(get_db)):
    """Create a new microbasket with constituents."""
    slug = basket_slug(req.name)

    # Check uniqueness
    existing = db.query(Microbasket).filter(
        (Microbasket.name == req.name) | (Microbasket.slug == slug)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Basket '{req.name}' already exists")

    # Validate weights sum to ~100%
    total_weight = sum(c.weight_pct for c in req.constituents)
    if abs(total_weight - 100.0) > 1.0:
        raise HTTPException(
            status_code=400,
            detail=f"Constituent weights sum to {total_weight:.1f}%, must be ~100%"
        )

    # Auto-compute portfolio_size from price x quantity if not explicitly set
    effective_size = req.portfolio_size
    if not effective_size:
        computed = sum(
            (c.buy_price or 0) * (c.quantity or 0)
            for c in req.constituents
        )
        if computed > 0:
            effective_size = computed

    basket = Microbasket(
        name=req.name,
        slug=slug,
        description=req.description,
        benchmark=req.benchmark or "NIFTY",
        portfolio_size=effective_size,
    )
    db.add(basket)
    db.flush()

    for c in req.constituents:
        db.add(MicrobasketConstituent(
            basket_id=basket.id,
            ticker=c.ticker.upper().strip(),
            company_name=c.company_name,
            weight_pct=c.weight_pct,
            buy_price=c.buy_price,
            quantity=c.quantity,
        ))

    db.commit()
    db.refresh(basket)

    # Background: fetch constituent history + compute NAV series
    threading.Thread(
        target=_background_basket_build, args=(basket.id,),
        daemon=True, name=f"basket-build-{basket.id}",
    ).start()

    return {
        "success": True,
        "id": basket.id,
        "slug": basket.slug,
        "message": f"Basket '{basket.name}' created. NAV computation running in background.",
    }


@router.get(
    "/api/baskets",
    tags=["Microbaskets"],
    summary="List all baskets",
    description="Returns all active microbaskets with summary data including constituent count, latest NAV value, and creation date.",
)
async def list_baskets(db: Session = Depends(get_db)):
    """List all active baskets with summary data."""
    baskets = (
        db.query(Microbasket)
        .filter(Microbasket.status == BasketStatus.ACTIVE)
        .order_by(Microbasket.name)
        .all()
    )

    results = []
    for b in baskets:
        # Get latest NAV from IndexPrice
        latest_nav = (
            db.query(IndexPrice)
            .filter(IndexPrice.index_name == b.slug)
            .order_by(desc(IndexPrice.date))
            .first()
        )

        results.append({
            "id": b.id,
            "name": b.name,
            "slug": b.slug,
            "description": b.description,
            "benchmark": b.benchmark,
            "portfolio_size": b.portfolio_size,
            "num_constituents": len(b.constituents),
            "current_value": latest_nav.close_price if latest_nav else None,
            "value_date": latest_nav.date if latest_nav else None,
            "created_at": (b.created_at.isoformat() + "Z") if b.created_at else None,
        })

    return {"success": True, "baskets": results}


@router.get(
    "/api/baskets/live",
    tags=["Microbaskets"],
    summary="All baskets with live data and ratio returns",
    description="Returns all active baskets with live NAV values, day change, ratio returns vs base index, and absolute period returns. Mirrors the shape of /api/indices/live.",
)
async def baskets_live(base: str = "NIFTY", db: Session = Depends(get_db)):
    """All baskets with live values + ratio returns (mirrors /api/indices/live shape)."""
    baskets = (
        db.query(Microbasket)
        .filter(Microbasket.status == BasketStatus.ACTIVE)
        .order_by(Microbasket.name)
        .all()
    )

    if not baskets:
        return {"success": True, "count": 0, "base": base, "baskets": [], "timestamp": datetime.now().isoformat() + "Z"}

    # Compute live values for all baskets
    results = []
    period_map = {"1d": 1, "1w": 7, "1m": 30, "3m": 90, "6m": 180, "12m": 365}
    tolerance = {"1d": 5, "1w": 5, "1m": 10, "3m": 15, "6m": 15, "12m": 15}

    # Pre-load historical dates (same bidirectional lookup as indices.py)
    historical_dates = {}
    for pk, days in period_map.items():
        target = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        tol = tolerance.get(pk, 15)
        before = db.query(sqlfunc.max(IndexPrice.date)).filter(IndexPrice.date <= target).scalar()
        after = db.query(sqlfunc.min(IndexPrice.date)).filter(IndexPrice.date >= target).scalar()
        best = None
        if before:
            gap_before = (datetime.strptime(target, "%Y-%m-%d") - datetime.strptime(before, "%Y-%m-%d")).days
            if gap_before <= tol:
                best = before
        if after:
            gap_after = (datetime.strptime(after, "%Y-%m-%d") - datetime.strptime(target, "%Y-%m-%d")).days
            if gap_after <= tol:
                if best is None:
                    best = after
                else:
                    gap_best = abs((datetime.strptime(target, "%Y-%m-%d") - datetime.strptime(best, "%Y-%m-%d")).days)
                    if gap_after < gap_best:
                        best = after
        if best:
            historical_dates[pk] = best

    # Load all prices at historical dates
    unique_dates = list(set(historical_dates.values()))
    date_price_map: dict = {}
    if unique_dates:
        all_rows = db.query(IndexPrice).filter(IndexPrice.date.in_(unique_dates)).all()
        for r in all_rows:
            if r.date not in date_price_map:
                date_price_map[r.date] = {}
            if r.close_price:
                date_price_map[r.date][r.index_name] = r.close_price

    historical_prices = {}
    for pk, d in historical_dates.items():
        historical_prices[pk] = date_price_map.get(d, {})

    for b in baskets:
        slug = b.slug

        # Get latest NAV
        latest_nav = (
            db.query(IndexPrice)
            .filter(IndexPrice.index_name == slug)
            .order_by(desc(IndexPrice.date))
            .first()
        )
        close = latest_nav.close_price if latest_nav else None

        # Previous close for 1d change
        prev_nav = None
        if latest_nav:
            prev_nav = (
                db.query(IndexPrice)
                .filter(IndexPrice.index_name == slug, IndexPrice.date < latest_nav.date)
                .order_by(desc(IndexPrice.date))
                .first()
            )
        change_pct = None
        if prev_nav and prev_nav.close_price and close:
            change_pct = round(((close - prev_nav.close_price) / prev_nav.close_price) * 100, 2)

        # Get base close (latest available)
        base_latest = (
            db.query(IndexPrice)
            .filter(IndexPrice.index_name == base)
            .order_by(desc(IndexPrice.date))
            .first()
        )
        base_close = base_latest.close_price if base_latest else None

        # Ratio returns
        ratio_returns: dict = {}
        ratio_today = (close / base_close) if (close and base_close and base_close > 0) else None

        if ratio_today:
            for pk in period_map:
                old_prices = historical_prices.get(pk, {})
                old_idx = old_prices.get(slug)
                old_base = old_prices.get(base)
                if old_idx and old_base and old_base > 0:
                    ratio_old = old_idx / old_base
                    if ratio_old > 0:
                        ratio_returns[pk] = round(((ratio_today / ratio_old) - 1) * 100, 2)

        # Index (basket's own) returns
        index_returns: dict = {}
        if change_pct is not None:
            index_returns["1d"] = change_pct
        if close:
            for pk in period_map:
                if pk == "1d" and "1d" in index_returns:
                    continue
                old_prices = historical_prices.get(pk, {})
                old_idx = old_prices.get(slug)
                if old_idx and old_idx > 0:
                    index_returns[pk] = round(((close / old_idx) - 1) * 100, 2)

        # Enrich constituents with current_price, computed_units, allocated_amount
        portfolio_worth = None
        portfolio_cost = None
        if b.portfolio_size and b.portfolio_size > 0:
            constituents_data = compute_constituent_units(b.constituents, b.portfolio_size, db)
            # Also include buy_price and compute per-constituent P&L
            for cd, c in zip(constituents_data, b.constituents):
                cd["buy_price"] = c.buy_price
                cd["quantity"] = c.quantity
                units = cd.get("computed_units") or 0
                cur_price = cd.get("current_price") or 0
                buy = c.buy_price or 0
                cd["current_worth"] = round(units * cur_price, 2) if units and cur_price else None
                cd["cost_value"] = round(units * buy, 2) if units and buy else None
            stock_worth = sum((cd.get("current_worth") or 0) for cd in constituents_data)
            stock_cost = sum((cd.get("cost_value") or 0) for cd in constituents_data)
            # Unallocated cash = portfolio_size - stock_cost (from floor rounding of units)
            unallocated_cash = b.portfolio_size - stock_cost
            portfolio_cost = round(stock_cost, 2)
            # Total worth = stock value + idle cash
            portfolio_worth = round(stock_worth + unallocated_cash, 2) if stock_worth > 0 else None
        else:
            constituents_data = [
                {
                    "ticker": c.ticker,
                    "company_name": c.company_name,
                    "weight_pct": c.weight_pct,
                    "buy_price": c.buy_price,
                    "quantity": c.quantity,
                }
                for c in b.constituents
            ]

        results.append({
            "id": b.id,
            "name": b.name,
            "slug": slug,
            "description": b.description,
            "benchmark": b.benchmark,
            "portfolio_size": b.portfolio_size,
            "portfolio_worth": portfolio_worth,
            "portfolio_cost": portfolio_cost,
            "num_constituents": len(b.constituents),
            "current_value": close,
            "value_date": latest_nav.date if latest_nav else None,
            "change_pct": change_pct,
            "ratio_returns": ratio_returns,
            "index_returns": index_returns,
            "constituents": constituents_data,
        })

    return {
        "success": True,
        "count": len(results),
        "base": base,
        "baskets": results,
        "timestamp": datetime.now().isoformat() + "Z",
    }


@router.get(
    "/api/baskets/{basket_id}",
    tags=["Microbaskets"],
    summary="Get basket detail",
    description="Returns full basket detail with constituents, live prices, and computed units (if portfolio_size is set). Includes price availability warnings per constituent.",
)
async def get_basket_detail(basket_id: int, db: Session = Depends(get_db)):
    """Get basket detail with constituents and live prices."""
    basket = db.get(Microbasket, basket_id)
    if not basket:
        raise HTTPException(status_code=404, detail="Basket not found")

    # Compute live value with per-constituent prices
    live_data = compute_basket_live_value(basket.constituents)

    # If portfolio_size is set, compute units per constituent from DB prices
    if basket.portfolio_size and basket.portfolio_size > 0:
        constituents = compute_constituent_units(basket.constituents, basket.portfolio_size, db)
    elif live_data and live_data.get("constituents"):
        constituents = live_data["constituents"]
    else:
        constituents = [
            {
                "ticker": c.ticker,
                "company_name": c.company_name,
                "weight_pct": c.weight_pct,
                "current_price": None,
                "weighted_value": None,
            }
            for c in basket.constituents
        ]

    # Add price_available flag and warnings per constituent
    warnings = []
    for c in constituents:
        has_price = c.get("current_price") is not None
        c["price_available"] = has_price
        if not has_price:
            warnings.append(f"{c['ticker']}: no market price found — check ticker")

    result = {
        "id": basket.id,
        "name": basket.name,
        "slug": basket.slug,
        "description": basket.description,
        "benchmark": basket.benchmark,
        "portfolio_size": basket.portfolio_size,
        "status": basket.status.value,
        "current_value": live_data["current_price"] if live_data else None,
        "num_constituents": len(basket.constituents),
        "constituents": constituents,
        "created_at": (basket.created_at.isoformat() + "Z") if basket.created_at else None,
        "updated_at": (basket.updated_at.isoformat() + "Z") if basket.updated_at else None,
    }
    if warnings:
        result["warnings"] = warnings
    return result


@router.put(
    "/api/baskets/{basket_id}",
    tags=["Microbaskets"],
    summary="Update basket",
    description="Update basket name, description, benchmark, portfolio size, or replace constituents. If constituents are changed, triggers background NAV recomputation.",
)
async def update_basket(basket_id: int, req: UpdateBasketRequest, db: Session = Depends(get_db)):
    """Update basket name, description, benchmark, or constituents."""
    basket = db.get(Microbasket, basket_id)
    if not basket:
        raise HTTPException(status_code=404, detail="Basket not found")

    if req.name and req.name != basket.name:
        new_slug = basket_slug(req.name)
        existing = db.query(Microbasket).filter(
            Microbasket.id != basket_id,
            (Microbasket.name == req.name) | (Microbasket.slug == new_slug),
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Basket name '{req.name}' already taken")
        old_slug = basket.slug
        basket.name = req.name
        basket.slug = new_slug
        # Migrate historical NAV records to new slug
        if old_slug != new_slug:
            db.query(IndexPrice).filter(IndexPrice.index_name == old_slug).update(
                {IndexPrice.index_name: new_slug}
            )

    if req.description is not None:
        basket.description = req.description
    if req.benchmark is not None:
        basket.benchmark = req.benchmark
    if req.portfolio_size is not None:
        basket.portfolio_size = req.portfolio_size if req.portfolio_size > 0 else None

    if req.constituents is not None:
        total_weight = sum(c.weight_pct for c in req.constituents)
        if abs(total_weight - 100.0) > 1.0:
            raise HTTPException(
                status_code=400,
                detail=f"Constituent weights sum to {total_weight:.1f}%, must be ~100%"
            )
        # Replace all constituents
        db.query(MicrobasketConstituent).filter(
            MicrobasketConstituent.basket_id == basket_id
        ).delete()
        for c in req.constituents:
            db.add(MicrobasketConstituent(
                basket_id=basket_id,
                ticker=c.ticker.upper().strip(),
                company_name=c.company_name,
                weight_pct=c.weight_pct,
                buy_price=c.buy_price,
                quantity=c.quantity,
            ))

    db.commit()

    # Rebuild NAV if constituents changed
    if req.constituents is not None:
        threading.Thread(
            target=_background_basket_build, args=(basket_id,),
            daemon=True, name=f"basket-rebuild-{basket_id}",
        ).start()

    return {"success": True, "message": f"Basket '{basket.name}' updated"}


@router.delete(
    "/api/baskets/{basket_id}",
    tags=["Microbaskets"],
    summary="Archive basket",
    description="Soft-delete (archive) a basket. Historical NAV data is preserved.",
)
async def archive_basket(basket_id: int, db: Session = Depends(get_db)):
    """Soft-delete (archive) a basket."""
    basket = db.get(Microbasket, basket_id)
    if not basket:
        raise HTTPException(status_code=404, detail="Basket not found")

    basket.status = BasketStatus.ARCHIVED
    db.commit()
    return {"success": True, "message": f"Basket '{basket.name}' archived"}


@router.post(
    "/api/baskets/csv-upload",
    tags=["Microbaskets"],
    summary="Upload baskets via CSV",
    description="Parse a CSV file and create multiple baskets. CSV format: basket_name, ticker, company_name, weight(%), price, quantity. Groups rows by basket_name, validates each basket, and reports per-basket results.",
)
async def upload_baskets_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Parse CSV and create multiple baskets.
    CSV format: basket_name, ticker, company_name, weight(%), price, quantity
    Groups rows by basket_name, validates each basket, reports per-basket results.
    Price x Quantity per stock = starting reference NAV (auto-computed as portfolio_size).
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    # Group rows by basket_name
    baskets_map: dict = {}
    row_count = 0
    for row in reader:
        row_count += 1
        name = (row.get("basket_name") or "").strip()
        ticker = (row.get("ticker") or "").strip().upper()
        company = (row.get("company_name") or "").strip()
        weight_str = (row.get("weight") or row.get("weight(%)") or row.get("weight_pct") or "").strip()
        price_str = (row.get("price") or row.get("buy_price") or "").strip()
        qty_str = (row.get("quantity") or row.get("qty") or "").strip()

        if not name or not ticker or not weight_str:
            continue

        try:
            weight = float(weight_str.replace("%", ""))
        except ValueError:
            continue

        buy_price = None
        if price_str:
            try:
                buy_price = float(price_str)
            except ValueError:
                pass

        quantity = None
        if qty_str:
            try:
                quantity = int(float(qty_str))
            except ValueError:
                pass

        if name not in baskets_map:
            baskets_map[name] = []
        baskets_map[name].append({
            "ticker": ticker,
            "company_name": company or None,
            "weight_pct": weight,
            "buy_price": buy_price,
            "quantity": quantity,
        })

    if not baskets_map:
        raise HTTPException(status_code=400, detail="No valid basket data found in CSV")

    results = []
    for name, constituents in baskets_map.items():
        total_weight = sum(c["weight_pct"] for c in constituents)
        if abs(total_weight - 100.0) > 1.0:
            results.append({
                "basket_name": name,
                "success": False,
                "error": f"Weights sum to {total_weight:.1f}%, must be ~100%",
            })
            continue

        slug = basket_slug(name)
        existing = db.query(Microbasket).filter(
            (Microbasket.name == name) | (Microbasket.slug == slug)
        ).first()
        if existing:
            results.append({
                "basket_name": name,
                "success": False,
                "error": f"Basket '{name}' already exists",
            })
            continue

        # Auto-compute portfolio_size from price x quantity
        computed_size = sum(
            (c.get("buy_price") or 0) * (c.get("quantity") or 0)
            for c in constituents
        )
        portfolio_size = computed_size if computed_size > 0 else None

        basket = Microbasket(
            name=name, slug=slug, description=None, benchmark="NIFTY",
            portfolio_size=portfolio_size,
        )
        db.add(basket)
        db.flush()

        for c in constituents:
            db.add(MicrobasketConstituent(
                basket_id=basket.id,
                ticker=c["ticker"],
                company_name=c["company_name"],
                weight_pct=c["weight_pct"],
                buy_price=c.get("buy_price"),
                quantity=c.get("quantity"),
            ))

        db.commit()

        # Background build
        threading.Thread(
            target=_background_basket_build, args=(basket.id,),
            daemon=True, name=f"basket-csv-{basket.id}",
        ).start()

        results.append({
            "basket_name": name,
            "success": True,
            "id": basket.id,
            "slug": basket.slug,
            "num_constituents": len(constituents),
        })

    return {
        "success": True,
        "rows_parsed": row_count,
        "baskets_found": len(baskets_map),
        "results": results,
    }
