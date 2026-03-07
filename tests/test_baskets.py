"""
Tests for FIE v3 — Microbasket API (routers/baskets.py)

Covers CRUD endpoints, validation, edge cases, and error paths
for the microbasket feature.
"""

import pytest
from unittest.mock import patch
from models import Microbasket, MicrobasketConstituent, BasketStatus, IndexPrice


# ─── Helpers ────────────────────────────────────────────────

def _valid_basket_payload(name="Test Basket", constituents=None):
    """Build a valid CreateBasketRequest-shaped dict."""
    if constituents is None:
        constituents = [
            {"ticker": "RELIANCE", "company_name": "Reliance Industries", "weight_pct": 50.0},
            {"ticker": "TCS", "company_name": "Tata Consultancy", "weight_pct": 50.0},
        ]
    return {
        "name": name,
        "description": "A test basket",
        "benchmark": "NIFTY",
        "portfolio_size": 100000.0,
        "constituents": constituents,
    }


def _seed_basket(db_session, name="Seeded Basket", status=BasketStatus.ACTIVE):
    """Insert a basket directly into the DB and return it."""
    from services.basket_service import basket_slug
    slug = basket_slug(name)
    basket = Microbasket(
        name=name, slug=slug, description="Seeded",
        benchmark="NIFTY", portfolio_size=50000.0, status=status,
    )
    db_session.add(basket)
    db_session.flush()
    db_session.add(MicrobasketConstituent(
        basket_id=basket.id, ticker="INFY", company_name="Infosys",
        weight_pct=60.0,
    ))
    db_session.add(MicrobasketConstituent(
        basket_id=basket.id, ticker="HDFCBANK", company_name="HDFC Bank",
        weight_pct=40.0,
    ))
    db_session.commit()
    db_session.refresh(basket)
    return basket


# ─── POST /api/baskets — Create ────────────────────────────


class TestCreateBasket:
    """Tests for POST /api/baskets endpoint."""

    @patch("routers.baskets.threading.Thread")
    def test_should_create_basket_with_valid_payload(self, mock_thread, client):
        payload = _valid_basket_payload()
        response = client.post("/api/baskets", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["slug"] == "MB_TEST_BASKET"
        assert "id" in data
        assert "NAV computation running" in data["message"]

    @patch("routers.baskets.threading.Thread")
    def test_should_reject_duplicate_basket_name(self, mock_thread, client, db_session):
        _seed_basket(db_session, name="Duplicate Me")
        payload = _valid_basket_payload(name="Duplicate Me")
        response = client.post("/api/baskets", json=payload)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_should_reject_empty_name(self, client):
        payload = _valid_basket_payload(name="")
        response = client.post("/api/baskets", json=payload)
        assert response.status_code == 422  # Pydantic validation

    def test_should_reject_empty_constituents(self, client):
        payload = _valid_basket_payload()
        payload["constituents"] = []
        response = client.post("/api/baskets", json=payload)
        assert response.status_code == 422  # min_length=1

    @patch("routers.baskets.threading.Thread")
    def test_should_reject_weights_not_summing_to_100(self, mock_thread, client):
        payload = _valid_basket_payload(constituents=[
            {"ticker": "RELIANCE", "weight_pct": 30.0},
            {"ticker": "TCS", "weight_pct": 30.0},
        ])
        response = client.post("/api/baskets", json=payload)
        assert response.status_code == 400
        assert "weights sum to" in response.json()["detail"].lower()

    @patch("routers.baskets.threading.Thread")
    def test_should_accept_weights_within_1pct_tolerance(self, mock_thread, client):
        """Weights that sum to 99.5 or 100.5 should be accepted (tolerance = 1.0)."""
        payload = _valid_basket_payload(name="Tolerance OK", constituents=[
            {"ticker": "RELIANCE", "weight_pct": 50.5},
            {"ticker": "TCS", "weight_pct": 49.0},
        ])
        response = client.post("/api/baskets", json=payload)
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_should_reject_weight_pct_zero_or_negative(self, client):
        payload = _valid_basket_payload(constituents=[
            {"ticker": "RELIANCE", "weight_pct": 0.0},
            {"ticker": "TCS", "weight_pct": 100.0},
        ])
        response = client.post("/api/baskets", json=payload)
        assert response.status_code == 422  # Pydantic gt=0

    def test_should_reject_weight_pct_above_100(self, client):
        payload = _valid_basket_payload(constituents=[
            {"ticker": "RELIANCE", "weight_pct": 101.0},
        ])
        response = client.post("/api/baskets", json=payload)
        assert response.status_code == 422  # Pydantic le=100

    @patch("routers.baskets.threading.Thread")
    def test_should_auto_compute_portfolio_size_from_price_and_quantity(self, mock_thread, client):
        """When portfolio_size is not set, it should be computed from buy_price * quantity."""
        payload = {
            "name": "Auto Size",
            "constituents": [
                {"ticker": "RELIANCE", "weight_pct": 60.0, "buy_price": 2500.0, "quantity": 10},
                {"ticker": "TCS", "weight_pct": 40.0, "buy_price": 3500.0, "quantity": 5},
            ],
        }
        response = client.post("/api/baskets", json=payload)
        assert response.status_code == 200
        # 2500*10 + 3500*5 = 25000 + 17500 = 42500
        # Verify via GET
        basket_id = response.json()["id"]
        detail_resp = client.get(f"/api/baskets/{basket_id}")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["portfolio_size"] == 42500.0

    @patch("routers.baskets.threading.Thread")
    def test_should_uppercase_ticker(self, mock_thread, client):
        """Tickers should be uppercased and stripped."""
        payload = _valid_basket_payload(name="Upper Test", constituents=[
            {"ticker": "  reliance  ", "weight_pct": 50.0},
            {"ticker": " tcs ", "weight_pct": 50.0},
        ])
        response = client.post("/api/baskets", json=payload)
        assert response.status_code == 200
        basket_id = response.json()["id"]
        detail = client.get(f"/api/baskets/{basket_id}").json()
        tickers = [c["ticker"] for c in detail["constituents"]]
        assert "RELIANCE" in tickers
        assert "TCS" in tickers

    @patch("routers.baskets.threading.Thread")
    def test_should_default_benchmark_to_nifty(self, mock_thread, client):
        payload = _valid_basket_payload(name="Default Benchmark")
        del payload["benchmark"]
        response = client.post("/api/baskets", json=payload)
        assert response.status_code == 200
        basket_id = response.json()["id"]
        detail = client.get(f"/api/baskets/{basket_id}").json()
        assert detail["benchmark"] == "NIFTY"


# ─── GET /api/baskets — List ───────────────────────────────


class TestListBaskets:
    """Tests for GET /api/baskets endpoint."""

    def test_should_return_empty_list_when_no_baskets(self, client):
        response = client.get("/api/baskets")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["baskets"] == []

    def test_should_return_active_baskets_only(self, client, db_session):
        _seed_basket(db_session, name="Active Basket", status=BasketStatus.ACTIVE)
        _seed_basket(db_session, name="Archived Basket", status=BasketStatus.ARCHIVED)
        response = client.get("/api/baskets")
        data = response.json()
        assert data["success"] is True
        names = [b["name"] for b in data["baskets"]]
        assert "Active Basket" in names
        assert "Archived Basket" not in names

    def test_should_include_basket_metadata(self, client, db_session):
        _seed_basket(db_session, name="Meta Basket")
        response = client.get("/api/baskets")
        basket = response.json()["baskets"][0]
        assert "id" in basket
        assert "name" in basket
        assert "slug" in basket
        assert "num_constituents" in basket
        assert basket["num_constituents"] == 2  # INFY + HDFCBANK
        assert "created_at" in basket
        assert basket["benchmark"] == "NIFTY"

    def test_should_include_current_value_when_nav_exists(self, client, db_session):
        basket = _seed_basket(db_session, name="NAV Basket")
        # Seed a NAV row in IndexPrice
        db_session.add(IndexPrice(
            date="2026-03-07", index_name=basket.slug,
            close_price=105.50,
        ))
        db_session.commit()
        response = client.get("/api/baskets")
        b = [x for x in response.json()["baskets"] if x["name"] == "NAV Basket"][0]
        assert b["current_value"] == 105.50
        assert b["value_date"] == "2026-03-07"


# ─── GET /api/baskets/{id} — Detail ───────────────────────


class TestGetBasketDetail:
    """Tests for GET /api/baskets/{basket_id} endpoint."""

    @patch("routers.baskets.compute_basket_live_value", return_value=None)
    def test_should_return_basket_detail(self, mock_live, client, db_session):
        basket = _seed_basket(db_session, name="Detail Basket")
        response = client.get(f"/api/baskets/{basket.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Detail Basket"
        assert data["slug"] == "MB_DETAIL_BASKET"
        assert data["num_constituents"] == 2
        assert data["status"] == "ACTIVE"
        assert "constituents" in data
        tickers = [c["ticker"] for c in data["constituents"]]
        assert "INFY" in tickers
        assert "HDFCBANK" in tickers

    def test_should_return_404_for_nonexistent_basket(self, client):
        response = client.get("/api/baskets/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch("routers.baskets.compute_basket_live_value", return_value=None)
    def test_should_include_portfolio_size(self, mock_live, client, db_session):
        basket = _seed_basket(db_session, name="Size Basket")
        response = client.get(f"/api/baskets/{basket.id}")
        data = response.json()
        assert data["portfolio_size"] == 50000.0

    @patch("routers.baskets.compute_basket_live_value", return_value=None)
    def test_should_include_warnings_when_no_price(self, mock_live, client, db_session):
        """When live prices are unavailable, warnings should be included."""
        basket = _seed_basket(db_session, name="Warn Basket")
        response = client.get(f"/api/baskets/{basket.id}")
        data = response.json()
        # Since compute_basket_live_value returns None, all constituents have no price
        assert "warnings" in data
        assert len(data["warnings"]) == 2  # Both INFY and HDFCBANK


# ─── PUT /api/baskets/{id} — Update ───────────────────────


class TestUpdateBasket:
    """Tests for PUT /api/baskets/{basket_id} endpoint."""

    def test_should_update_basket_name(self, client, db_session):
        basket = _seed_basket(db_session, name="Old Name")
        response = client.put(f"/api/baskets/{basket.id}", json={
            "name": "New Name",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "New Name" in data["message"]

    def test_should_update_description(self, client, db_session):
        basket = _seed_basket(db_session, name="Desc Basket")
        response = client.put(f"/api/baskets/{basket.id}", json={
            "description": "Updated description",
        })
        assert response.status_code == 200

    def test_should_update_benchmark(self, client, db_session):
        basket = _seed_basket(db_session, name="Bench Basket")
        response = client.put(f"/api/baskets/{basket.id}", json={
            "benchmark": "BANKNIFTY",
        })
        assert response.status_code == 200

    def test_should_return_404_for_nonexistent_basket(self, client):
        response = client.put("/api/baskets/99999", json={"name": "X"})
        assert response.status_code == 404

    def test_should_reject_duplicate_name_on_update(self, client, db_session):
        _seed_basket(db_session, name="Existing A")
        basket_b = _seed_basket(db_session, name="Existing B")
        response = client.put(f"/api/baskets/{basket_b.id}", json={
            "name": "Existing A",
        })
        assert response.status_code == 400
        assert "already taken" in response.json()["detail"]

    @patch("routers.baskets.threading.Thread")
    def test_should_replace_constituents_when_provided(self, mock_thread, client, db_session):
        basket = _seed_basket(db_session, name="Replace Basket")
        response = client.put(f"/api/baskets/{basket.id}", json={
            "constituents": [
                {"ticker": "RELIANCE", "weight_pct": 70.0},
                {"ticker": "SBIN", "weight_pct": 30.0},
            ],
        })
        assert response.status_code == 200

    @patch("routers.baskets.threading.Thread")
    def test_should_reject_invalid_constituent_weights_on_update(self, mock_thread, client, db_session):
        basket = _seed_basket(db_session, name="Bad Weight Basket")
        response = client.put(f"/api/baskets/{basket.id}", json={
            "constituents": [
                {"ticker": "RELIANCE", "weight_pct": 20.0},
                {"ticker": "SBIN", "weight_pct": 20.0},
            ],
        })
        assert response.status_code == 400
        assert "weights sum to" in response.json()["detail"].lower()

    def test_should_clear_portfolio_size_when_set_to_zero(self, client, db_session):
        basket = _seed_basket(db_session, name="Clear Size Basket")
        response = client.put(f"/api/baskets/{basket.id}", json={
            "portfolio_size": 0,
        })
        assert response.status_code == 200

    def test_should_migrate_nav_records_on_rename(self, client, db_session):
        """Renaming a basket should update IndexPrice records to the new slug."""
        basket = _seed_basket(db_session, name="OldSlug Basket")
        old_slug = basket.slug
        # Seed NAV record with old slug
        db_session.add(IndexPrice(
            date="2026-03-01", index_name=old_slug, close_price=100.0,
        ))
        db_session.commit()

        response = client.put(f"/api/baskets/{basket.id}", json={
            "name": "NewSlug Basket",
        })
        assert response.status_code == 200

        # Verify the old slug's NAV is gone and new slug's NAV exists
        from services.basket_service import basket_slug
        new_slug = basket_slug("NewSlug Basket")
        old_nav = db_session.query(IndexPrice).filter_by(
            index_name=old_slug, date="2026-03-01"
        ).first()
        new_nav = db_session.query(IndexPrice).filter_by(
            index_name=new_slug, date="2026-03-01"
        ).first()
        assert old_nav is None
        assert new_nav is not None
        assert new_nav.close_price == 100.0


# ─── DELETE /api/baskets/{id} — Archive ────────────────────


class TestArchiveBasket:
    """Tests for DELETE /api/baskets/{basket_id} endpoint."""

    def test_should_archive_basket(self, client, db_session):
        basket = _seed_basket(db_session, name="To Archive")
        response = client.delete(f"/api/baskets/{basket.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "archived" in data["message"].lower()

    def test_should_return_404_for_nonexistent_basket(self, client):
        response = client.delete("/api/baskets/99999")
        assert response.status_code == 404

    def test_archived_basket_not_listed(self, client, db_session):
        basket = _seed_basket(db_session, name="Soon Archived")
        client.delete(f"/api/baskets/{basket.id}")
        response = client.get("/api/baskets")
        names = [b["name"] for b in response.json()["baskets"]]
        assert "Soon Archived" not in names


# ─── GET /api/baskets/live — Live values ───────────────────


class TestBasketsLive:
    """Tests for GET /api/baskets/live endpoint."""

    def test_should_return_empty_when_no_active_baskets(self, client):
        response = client.get("/api/baskets/live")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["count"] == 0
        assert data["baskets"] == []

    def test_should_include_timestamp(self, client):
        response = client.get("/api/baskets/live")
        data = response.json()
        assert "timestamp" in data
        assert data["timestamp"].endswith("Z")

    def test_should_accept_base_parameter(self, client, db_session):
        _seed_basket(db_session, name="Live Base Basket")
        response = client.get("/api/baskets/live?base=BANKNIFTY")
        assert response.status_code == 200
        assert response.json()["base"] == "BANKNIFTY"

    def test_should_return_basket_data_with_ratio_returns(self, client, db_session):
        basket = _seed_basket(db_session, name="Live Basket")
        # Seed some NAV data for the basket
        db_session.add(IndexPrice(
            date="2026-03-07", index_name=basket.slug, close_price=110.0,
        ))
        db_session.add(IndexPrice(
            date="2026-03-06", index_name=basket.slug, close_price=105.0,
        ))
        db_session.commit()

        response = client.get("/api/baskets/live")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1
        live_basket = [b for b in data["baskets"] if b["name"] == "Live Basket"][0]
        assert live_basket["current_value"] == 110.0
        assert "ratio_returns" in live_basket
        assert "index_returns" in live_basket
        assert "constituents" in live_basket
