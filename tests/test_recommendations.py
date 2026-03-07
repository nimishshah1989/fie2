"""
Tests for FIE v3 — Sector Recommendation Engine (routers/recommendations.py)

Covers the sectors listing endpoint, generate endpoint with various
parameter combinations, validation, and edge cases.
"""

import pytest
from unittest.mock import patch
from models import IndexPrice, IndexConstituent


# ─── Helpers ────────────────────────────────────────────────

def _seed_index_prices(db_session, index_name, prices_by_date):
    """Seed IndexPrice rows for a given index/ticker.
    prices_by_date: dict of {"YYYY-MM-DD": close_price}
    """
    for date_str, close in prices_by_date.items():
        db_session.add(IndexPrice(
            date=date_str, index_name=index_name, close_price=close,
        ))
    db_session.commit()


def _seed_constituents(db_session, index_display_name, stocks):
    """Seed IndexConstituent rows.
    stocks: list of {"ticker": "SYM", "company_name": "Name", "weight_pct": 10.0, "last_price": 500.0}
    """
    for stock in stocks:
        db_session.add(IndexConstituent(
            index_name=index_display_name,
            ticker=stock["ticker"],
            company_name=stock.get("company_name", stock["ticker"]),
            weight_pct=stock.get("weight_pct"),
            last_price=stock.get("last_price"),
        ))
    db_session.commit()


# ─── GET /api/recommendations/sectors ──────────────────────


class TestGetSectors:
    """Tests for GET /api/recommendations/sectors endpoint."""

    def test_should_return_sector_list(self, client):
        response = client.get("/api/recommendations/sectors")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "sectors" in data
        assert len(data["sectors"]) > 0

    def test_should_include_sector_keys_and_display_names(self, client):
        response = client.get("/api/recommendations/sectors")
        sectors = response.json()["sectors"]
        # Verify structure of each sector entry
        for sector in sectors:
            assert "key" in sector
            assert "display_name" in sector
            assert "etfs" in sector
            assert isinstance(sector["etfs"], list)

    def test_should_include_known_sectors(self, client):
        response = client.get("/api/recommendations/sectors")
        keys = [s["key"] for s in response.json()["sectors"]]
        assert "BANKNIFTY" in keys
        assert "NIFTYIT" in keys
        assert "NIFTYPHARMA" in keys

    def test_should_include_periods(self, client):
        response = client.get("/api/recommendations/sectors")
        data = response.json()
        assert "periods" in data
        assert set(data["periods"]) == {"1w", "1m", "3m", "6m", "12m"}

    def test_should_include_period_labels(self, client):
        response = client.get("/api/recommendations/sectors")
        labels = response.json()["period_labels"]
        assert labels["1w"] == "1W"
        assert labels["1m"] == "1M"
        assert labels["3m"] == "3M"
        assert labels["6m"] == "6M"
        assert labels["12m"] == "12M"

    def test_should_map_etfs_for_sectors_that_have_them(self, client):
        response = client.get("/api/recommendations/sectors")
        sectors = response.json()["sectors"]
        bank_sector = [s for s in sectors if s["key"] == "BANKNIFTY"][0]
        assert "BANKBEES" in bank_sector["etfs"]
        it_sector = [s for s in sectors if s["key"] == "NIFTYIT"][0]
        assert "ITBEES" in it_sector["etfs"]

    def test_sectors_without_etf_should_have_empty_list(self, client):
        """Sectors like NIFTYREALTY have no ETF mapping."""
        response = client.get("/api/recommendations/sectors")
        sectors = response.json()["sectors"]
        realty = [s for s in sectors if s["key"] == "NIFTYREALTY"]
        if realty:
            assert realty[0]["etfs"] == []


# ─── POST /api/recommendations/generate ───────────────────


class TestGenerateRecommendations:
    """Tests for POST /api/recommendations/generate endpoint."""

    def test_should_reject_invalid_period(self, client):
        response = client.post("/api/recommendations/generate", json={
            "base": "NIFTY",
            "period": "2y",
            "selected_sectors": ["BANKNIFTY"],
            "threshold": 5.0,
            "top_n": 5,
        })
        assert response.status_code == 400
        assert "invalid period" in response.json()["detail"].lower()

    def test_should_reject_no_valid_sectors(self, client):
        response = client.post("/api/recommendations/generate", json={
            "base": "NIFTY",
            "period": "1m",
            "selected_sectors": ["FAKE_SECTOR", "ANOTHER_FAKE"],
            "threshold": 5.0,
            "top_n": 5,
        })
        assert response.status_code == 400
        assert "no valid sectors" in response.json()["detail"].lower()

    def test_should_reject_empty_selected_sectors(self, client):
        """Pydantic should accept an empty list, but the endpoint validates it."""
        response = client.post("/api/recommendations/generate", json={
            "base": "NIFTY",
            "period": "1m",
            "selected_sectors": [],
            "threshold": 5.0,
            "top_n": 5,
        })
        assert response.status_code == 400

    @patch("routers.recommendations._fetch_fundamentals", return_value={})
    def test_should_return_non_qualifying_when_ratio_below_threshold(
        self, mock_fundamentals, client, db_session
    ):
        """Sectors whose ratio return is below threshold should be non-qualifying."""
        # Seed prices: sector return close to base (ratio ~ 0)
        today = "2026-03-07"
        month_ago = "2026-02-05"
        _seed_index_prices(db_session, "NIFTY", {today: 22000.0, month_ago: 21000.0})
        _seed_index_prices(db_session, "BANKNIFTY", {today: 48000.0, month_ago: 47000.0})

        response = client.post("/api/recommendations/generate", json={
            "base": "NIFTY",
            "period": "1m",
            "selected_sectors": ["BANKNIFTY"],
            "threshold": 50.0,  # Very high threshold
            "top_n": 5,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["qualifying_sectors"]) == 0
        assert len(data["non_qualifying_sectors"]) == 1
        assert data["non_qualifying_sectors"][0]["sector_key"] == "BANKNIFTY"
        assert data["non_qualifying_sectors"][0]["qualifies"] is False

    @patch("routers.recommendations._fetch_fundamentals", return_value={})
    def test_should_return_qualifying_when_ratio_above_threshold(
        self, mock_fundamentals, client, db_session
    ):
        """Sectors whose ratio return exceeds threshold should be qualifying."""
        today = "2026-03-07"
        month_ago = "2026-02-05"
        # NIFTY flat, IT sector up 20%
        _seed_index_prices(db_session, "NIFTY", {today: 22000.0, month_ago: 22000.0})
        _seed_index_prices(db_session, "NIFTYIT", {today: 36000.0, month_ago: 30000.0})

        # Seed constituents for NIFTY IT
        _seed_constituents(db_session, "NIFTY IT", [
            {"ticker": "TCS", "company_name": "Tata Consultancy", "weight_pct": 30.0, "last_price": 3500.0},
            {"ticker": "INFY", "company_name": "Infosys", "weight_pct": 25.0, "last_price": 1500.0},
        ])
        # Seed stock prices
        _seed_index_prices(db_session, "TCS", {today: 3500.0, month_ago: 2800.0})
        _seed_index_prices(db_session, "INFY", {today: 1500.0, month_ago: 1400.0})

        response = client.post("/api/recommendations/generate", json={
            "base": "NIFTY",
            "period": "1m",
            "selected_sectors": ["NIFTYIT"],
            "threshold": 5.0,
            "top_n": 5,
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data["qualifying_sectors"]) == 1
        sector = data["qualifying_sectors"][0]
        assert sector["sector_key"] == "NIFTYIT"
        assert sector["qualifies"] is True
        assert sector["ratio_return"] is not None
        assert sector["ratio_return"] > 5.0
        assert len(sector["top_stocks"]) <= 5

    @patch("routers.recommendations._fetch_fundamentals", return_value={})
    def test_should_clamp_top_n_to_max_10(self, mock_fundamentals, client, db_session):
        """top_n should be clamped to 10 even if a higher value is provided."""
        today = "2026-03-07"
        month_ago = "2026-02-05"
        _seed_index_prices(db_session, "NIFTY", {today: 22000.0, month_ago: 22000.0})
        _seed_index_prices(db_session, "NIFTYIT", {today: 36000.0, month_ago: 30000.0})

        response = client.post("/api/recommendations/generate", json={
            "base": "NIFTY",
            "period": "1m",
            "selected_sectors": ["NIFTYIT"],
            "threshold": 5.0,
            "top_n": 50,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["top_n"] == 10

    @patch("routers.recommendations._fetch_fundamentals", return_value={})
    def test_should_clamp_top_n_to_min_1(self, mock_fundamentals, client, db_session):
        """top_n should be at least 1 even if 0 is provided."""
        today = "2026-03-07"
        month_ago = "2026-02-05"
        _seed_index_prices(db_session, "NIFTY", {today: 22000.0, month_ago: 22000.0})
        _seed_index_prices(db_session, "NIFTYIT", {today: 36000.0, month_ago: 30000.0})

        response = client.post("/api/recommendations/generate", json={
            "base": "NIFTY",
            "period": "1m",
            "selected_sectors": ["NIFTYIT"],
            "threshold": 5.0,
            "top_n": 0,
        })
        assert response.status_code == 200
        assert response.json()["top_n"] == 1

    @patch("routers.recommendations._fetch_fundamentals", return_value={})
    def test_should_include_etf_recommendations(self, mock_fundamentals, client, db_session):
        """Qualifying and non-qualifying sectors should include ETF data."""
        today = "2026-03-07"
        month_ago = "2026-02-05"
        _seed_index_prices(db_session, "NIFTY", {today: 22000.0, month_ago: 22000.0})
        _seed_index_prices(db_session, "BANKNIFTY", {today: 48000.0, month_ago: 47000.0})

        response = client.post("/api/recommendations/generate", json={
            "base": "NIFTY",
            "period": "1m",
            "selected_sectors": ["BANKNIFTY"],
            "threshold": 0.0,  # Low threshold so it qualifies
            "top_n": 5,
        })
        assert response.status_code == 200
        data = response.json()
        # BANKNIFTY should have BANKBEES as ETF
        all_sectors = data["qualifying_sectors"] + data["non_qualifying_sectors"]
        bank = [s for s in all_sectors if s["sector_key"] == "BANKNIFTY"][0]
        etf_tickers = [e["ticker"] for e in bank["recommended_etfs"]]
        assert "BANKBEES" in etf_tickers

    @patch("routers.recommendations._fetch_fundamentals", return_value={})
    def test_should_filter_only_valid_selected_sectors(self, mock_fundamentals, client, db_session):
        """Invalid sector keys should be silently filtered out."""
        today = "2026-03-07"
        month_ago = "2026-02-05"
        _seed_index_prices(db_session, "NIFTY", {today: 22000.0, month_ago: 22000.0})
        _seed_index_prices(db_session, "BANKNIFTY", {today: 48000.0, month_ago: 47000.0})

        response = client.post("/api/recommendations/generate", json={
            "base": "NIFTY",
            "period": "1m",
            "selected_sectors": ["BANKNIFTY", "INVALID_SECTOR"],
            "threshold": 5.0,
            "top_n": 5,
        })
        assert response.status_code == 200
        data = response.json()
        all_sector_keys = (
            [s["sector_key"] for s in data["qualifying_sectors"]]
            + [s["sector_key"] for s in data["non_qualifying_sectors"]]
        )
        assert "BANKNIFTY" in all_sector_keys
        assert "INVALID_SECTOR" not in all_sector_keys

    @patch("routers.recommendations._fetch_fundamentals", return_value={})
    def test_should_return_response_structure(self, mock_fundamentals, client, db_session):
        """Verify the full response structure of the generate endpoint."""
        today = "2026-03-07"
        month_ago = "2026-02-05"
        _seed_index_prices(db_session, "NIFTY", {today: 22000.0, month_ago: 22000.0})
        _seed_index_prices(db_session, "BANKNIFTY", {today: 48000.0, month_ago: 47000.0})

        response = client.post("/api/recommendations/generate", json={
            "base": "NIFTY",
            "period": "1m",
            "selected_sectors": ["BANKNIFTY"],
            "threshold": 5.0,
            "top_n": 5,
        })
        data = response.json()
        assert "success" in data
        assert "base" in data
        assert "period" in data
        assert "threshold" in data
        assert "top_n" in data
        assert "qualifying_sectors" in data
        assert "non_qualifying_sectors" in data
        assert "generated_at" in data
        assert data["generated_at"].endswith("Z")

    @patch("routers.recommendations._fetch_fundamentals", return_value={})
    def test_should_uppercase_base(self, mock_fundamentals, client, db_session):
        """Base index parameter should be uppercased."""
        today = "2026-03-07"
        month_ago = "2026-02-05"
        _seed_index_prices(db_session, "NIFTY", {today: 22000.0, month_ago: 22000.0})
        _seed_index_prices(db_session, "BANKNIFTY", {today: 48000.0, month_ago: 47000.0})

        response = client.post("/api/recommendations/generate", json={
            "base": "nifty",
            "period": "1m",
            "selected_sectors": ["BANKNIFTY"],
            "threshold": 5.0,
            "top_n": 5,
        })
        assert response.status_code == 200
        assert response.json()["base"] == "NIFTY"

    @patch("routers.recommendations._fetch_fundamentals", return_value={})
    def test_should_handle_no_price_data_gracefully(self, mock_fundamentals, client, db_session):
        """When there is no historical price data, ratio returns should be empty."""
        response = client.post("/api/recommendations/generate", json={
            "base": "NIFTY",
            "period": "1m",
            "selected_sectors": ["NIFTYPHARMA"],
            "threshold": 5.0,
            "top_n": 5,
        })
        assert response.status_code == 200
        data = response.json()
        # NIFTYPHARMA should be non-qualifying since there are no prices
        assert len(data["non_qualifying_sectors"]) == 1
        pharma = data["non_qualifying_sectors"][0]
        assert pharma["ratio_return"] is None

    @patch("routers.recommendations._fetch_fundamentals", return_value={})
    def test_qualifying_sectors_sorted_by_ratio_return_descending(
        self, mock_fundamentals, client, db_session
    ):
        """Qualifying sectors should be sorted by ratio_return in descending order."""
        today = "2026-03-07"
        month_ago = "2026-02-05"
        # Base stays flat
        _seed_index_prices(db_session, "NIFTY", {today: 22000.0, month_ago: 22000.0})
        # IT up 20%, PHARMA up 10%
        _seed_index_prices(db_session, "NIFTYIT", {today: 36000.0, month_ago: 30000.0})
        _seed_index_prices(db_session, "NIFTYPHARMA", {today: 16500.0, month_ago: 15000.0})

        response = client.post("/api/recommendations/generate", json={
            "base": "NIFTY",
            "period": "1m",
            "selected_sectors": ["NIFTYIT", "NIFTYPHARMA"],
            "threshold": 1.0,
            "top_n": 3,
        })
        assert response.status_code == 200
        qualifying = response.json()["qualifying_sectors"]
        if len(qualifying) >= 2:
            assert qualifying[0]["ratio_return"] >= qualifying[1]["ratio_return"]


# ─── Batch Helper Unit Tests ──────────────────────────────


class TestBatchHelpers:
    """Tests for the internal batch price helper functions used by the recommendation engine."""

    def test_batch_latest_prices_returns_latest(self, db_session):
        """_batch_latest_prices should return the most recent price per ticker."""
        from routers.recommendations import _batch_latest_prices

        _seed_index_prices(db_session, "TCS", {
            "2026-03-05": 3400.0,
            "2026-03-06": 3450.0,
            "2026-03-07": 3500.0,
        })
        result = _batch_latest_prices(db_session, {"TCS"})
        assert result["TCS"] == 3500.0

    def test_batch_latest_prices_empty_set(self, db_session):
        """Passing empty set should return empty dict."""
        from routers.recommendations import _batch_latest_prices
        result = _batch_latest_prices(db_session, set())
        assert result == {}

    def test_batch_historical_prices_returns_correct_prices(self, db_session):
        """_batch_historical_prices should return prices at specified dates."""
        from routers.recommendations import _batch_historical_prices

        _seed_index_prices(db_session, "TCS", {
            "2026-02-05": 3000.0,
            "2026-03-07": 3500.0,
        })
        result = _batch_historical_prices(db_session, ["2026-02-05"], {"TCS"})
        assert result["2026-02-05"]["TCS"] == 3000.0

    def test_batch_historical_prices_empty_inputs(self, db_session):
        """Empty dates or tickers should return empty dict."""
        from routers.recommendations import _batch_historical_prices
        assert _batch_historical_prices(db_session, [], {"TCS"}) == {}
        assert _batch_historical_prices(db_session, ["2026-01-01"], set()) == {}

    def test_compute_ratio_returns_from_cache(self):
        """Ratio return computation should work correctly with pre-fetched data."""
        from routers.recommendations import _compute_ratio_returns_from_cache

        latest = {"NIFTYIT": 36000.0, "NIFTY": 22000.0}
        period_dates = {"1m": "2026-02-05"}
        hist = {"2026-02-05": {"NIFTYIT": 30000.0, "NIFTY": 22000.0}}

        result = _compute_ratio_returns_from_cache(
            "NIFTYIT", "NIFTY", latest, period_dates, hist,
        )
        # ratio_today = 36000/22000 = 1.6364
        # ratio_old = 30000/22000 = 1.3636
        # return = ((1.6364/1.3636) - 1) * 100 = 20.0%
        assert "1m" in result
        assert abs(result["1m"] - 20.0) < 0.1

    def test_compute_ratio_returns_missing_current_price(self):
        """Should return empty dict when current price is missing."""
        from routers.recommendations import _compute_ratio_returns_from_cache

        result = _compute_ratio_returns_from_cache(
            "NIFTYIT", "NIFTY",
            {},  # no latest prices
            {"1m": "2026-02-05"},
            {"2026-02-05": {"NIFTYIT": 30000.0, "NIFTY": 22000.0}},
        )
        assert result == {}

    def test_compute_ratio_returns_zero_base(self):
        """Should return empty dict when base price is zero."""
        from routers.recommendations import _compute_ratio_returns_from_cache

        result = _compute_ratio_returns_from_cache(
            "NIFTYIT", "NIFTY",
            {"NIFTYIT": 36000.0, "NIFTY": 0.0},
            {"1m": "2026-02-05"},
            {"2026-02-05": {"NIFTYIT": 30000.0, "NIFTY": 22000.0}},
        )
        assert result == {}
