"""
FIE v3 — Sentiment Indicator Routes
Thin router — delegates computation to services/sentiment_engine.py.
"""

import copy
import logging
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from models import SentimentHistory, get_db
from services.sentiment_engine import compute_sentiment

logger = logging.getLogger("fie_v3.sentiment")
router = APIRouter()

# In-memory cache: (result_dict, computed_at)
_sentiment_cache: tuple[Optional[dict], Optional[datetime]] = (None, None)
CACHE_TTL_SECONDS = 900


def _cache_valid() -> bool:
    _, computed_at = _sentiment_cache
    if computed_at is None:
        return False
    return (datetime.now() - computed_at).total_seconds() < CACHE_TTL_SECONDS


def _strip_tickers(result: dict) -> dict:
    """Remove ticker lists from metrics for lean response.

    Operates on a deep copy so the original cache is not mutated.
    """
    out = copy.deepcopy(result)
    layer_keys = ("short_term_trend", "broad_trend", "advance_decline", "momentum", "extremes")
    for layer_key in layer_keys:
        layer = out.get(layer_key, {})
        for metric in layer.get("metrics", []):
            metric.pop("tickers", None)
    return out


def _save_snapshot(db: Session, result: dict) -> None:
    """Upsert today's sentiment snapshot into history table."""
    try:
        today_str = date.today().isoformat()
        existing = db.query(SentimentHistory).filter(
            SentimentHistory.snapshot_date == today_str
        ).first()

        layer_scores = result.get("layer_scores", {})

        if existing:
            existing.composite_score = result.get("composite_score", 0)
            existing.zone = result.get("zone", "Neutral")
            existing.layer_short = layer_scores.get("short_term", 0)
            existing.layer_broad = layer_scores.get("broad_trend", 0)
            existing.layer_ad = layer_scores.get("adv_decline", 0)
            existing.layer_momentum = layer_scores.get("momentum", 0)
            existing.layer_extremes = layer_scores.get("extremes", 0)
            existing.stocks_computed = result.get("stocks_computed", 0)
        else:
            snapshot = SentimentHistory(
                snapshot_date=today_str,
                composite_score=result.get("composite_score", 0),
                zone=result.get("zone", "Neutral"),
                layer_short=layer_scores.get("short_term", 0),
                layer_broad=layer_scores.get("broad_trend", 0),
                layer_ad=layer_scores.get("adv_decline", 0),
                layer_momentum=layer_scores.get("momentum", 0),
                layer_extremes=layer_scores.get("extremes", 0),
                stocks_computed=result.get("stocks_computed", 0),
            )
            db.add(snapshot)
        db.commit()
    except Exception as e:
        logger.warning("Failed to save sentiment snapshot: %s", e)
        db.rollback()


# ─── Routes ─────────────────────────────────────────────

@router.get(
    "/api/sentiment",
    tags=["Sentiment"],
    summary="Market breadth indicators",
    description="Returns 26 market breadth metrics with composite score for "
                "the Nifty 500 universe. Cached for 15 minutes. "
                "Pass include_tickers=true to get per-indicator stock lists.",
)
def get_sentiment(
    include_tickers: bool = Query(
        default=False,
        description="Include per-indicator stock ticker lists in response",
    ),
    db: Session = Depends(get_db),
):
    global _sentiment_cache

    if _cache_valid():
        cached_result, _ = _sentiment_cache
        out = cached_result if include_tickers else _strip_tickers(cached_result)
        return {"success": True, "cached": True, **out}

    result = compute_sentiment(db)
    _sentiment_cache = (result, datetime.now())
    _save_snapshot(db, result)
    out = result if include_tickers else _strip_tickers(result)
    return {"success": True, "cached": False, **out}


@router.post(
    "/api/sentiment/refresh",
    tags=["Sentiment"],
    summary="Force refresh sentiment cache",
    description="Clears the sentiment cache and recomputes all metrics immediately.",
)
def refresh_sentiment(
    include_tickers: bool = Query(
        default=False,
        description="Include per-indicator stock ticker lists in response",
    ),
    db: Session = Depends(get_db),
):
    global _sentiment_cache

    result = compute_sentiment(db)
    _sentiment_cache = (result, datetime.now())
    _save_snapshot(db, result)
    out = result if include_tickers else _strip_tickers(result)
    return {
        "success": True,
        "cached": False,
        "message": f"Sentiment recomputed for {result['stocks_computed']} stocks",
        **out,
    }


@router.get(
    "/api/sentiment/history",
    tags=["Sentiment"],
    summary="Sentiment composite history",
    description="Returns historical composite scores for the sentiment history chart.",
)
def get_sentiment_history(
    weeks: int = Query(default=20, ge=1, le=52),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(SentimentHistory)
        .order_by(SentimentHistory.snapshot_date.desc())
        .limit(weeks * 7)
        .all()
    )
    return {
        "success": True,
        "history": [
            {"date": r.snapshot_date, "score": r.composite_score, "zone": r.zone}
            for r in reversed(rows)
        ],
    }
