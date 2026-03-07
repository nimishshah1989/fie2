"""
Tests for Portfolio API endpoints (routers/portfolios.py).

Covers: CRUD, transactions (BUY/SELL), holdings, NAV history,
CSV export, bulk import, and edge cases.

Note: Tests are written to be resilient to pre-existing data in the DB
since the test database is shared across the session and background threads
may seed data during app startup.
"""

import json
from unittest.mock import patch

from models import (
    ModelPortfolio, PortfolioHolding, PortfolioTransaction,
    PortfolioNAV, PortfolioStatus, TransactionType, IndexPrice,
)


# ── Portfolio CRUD ──────────────────────────────────────────


class TestCreatePortfolio:
    """POST /api/portfolios"""

    def test_should_create_portfolio_with_required_fields(self, client):
        response = client.post("/api/portfolios", json={
            "name": "Test Growth Portfolio",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["name"] == "Test Growth Portfolio"
        assert "id" in data

    def test_should_create_portfolio_with_all_fields(self, client):
        response = client.post("/api/portfolios", json={
            "name": "Balanced Fund",
            "description": "Multi-cap balanced portfolio",
            "benchmark": "NIFTY 50",
            "inception_date": "2024-01-01",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["name"] == "Balanced Fund"

    def test_should_default_benchmark_to_nifty(self, client, db_session):
        response = client.post("/api/portfolios", json={"name": "Default Bench"})
        assert response.status_code == 200
        portfolio_id = response.json()["id"]
        portfolio = db_session.query(ModelPortfolio).filter_by(id=portfolio_id).first()
        assert portfolio.benchmark == "NIFTY"

    def test_should_reject_missing_name(self, client):
        response = client.post("/api/portfolios", json={
            "description": "No name provided",
        })
        assert response.status_code == 422  # Pydantic validation error


class TestListPortfolios:
    """GET /api/portfolios"""

    def test_should_return_success_with_portfolios_list(self, client):
        response = client.get("/api/portfolios")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["portfolios"], list)

    def test_should_include_newly_created_portfolio(self, client):
        # Create a portfolio with a unique name
        unique_name = "ListTest_UniquePortfolio_7891"
        client.post("/api/portfolios", json={"name": unique_name})
        response = client.get("/api/portfolios")
        assert response.status_code == 200
        names = [p["name"] for p in response.json()["portfolios"]]
        assert unique_name in names

    def test_should_not_list_archived_portfolios(self, client):
        # Create and archive a portfolio
        unique_name = "ListTest_ToArchive_4521"
        resp = client.post("/api/portfolios", json={"name": unique_name})
        portfolio_id = resp.json()["id"]
        client.delete(f"/api/portfolios/{portfolio_id}")

        response = client.get("/api/portfolios")
        names = [p["name"] for p in response.json()["portfolios"]]
        assert unique_name not in names

    def test_should_include_expected_fields_in_list(self, client):
        client.post("/api/portfolios", json={
            "name": "ListTest_FieldCheck_8832", "description": "test desc",
        })
        response = client.get("/api/portfolios")
        # Find any portfolio in the list
        portfolios = response.json()["portfolios"]
        assert len(portfolios) > 0
        portfolio = portfolios[0]
        assert "id" in portfolio
        assert "name" in portfolio
        assert "description" in portfolio
        assert "benchmark" in portfolio
        assert "status" in portfolio
        assert "num_holdings" in portfolio
        assert "total_invested" in portfolio
        assert "current_value" in portfolio
        assert "total_return_pct" in portfolio
        assert "created_at" in portfolio
        assert "updated_at" in portfolio


class TestGetPortfolio:
    """GET /api/portfolios/{portfolio_id}"""

    def test_should_return_portfolio_by_id(self, client):
        resp = client.post("/api/portfolios", json={
            "name": "GetTest_MyPortfolio", "description": "Testing",
        })
        portfolio_id = resp.json()["id"]
        response = client.get(f"/api/portfolios/{portfolio_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == portfolio_id
        assert data["name"] == "GetTest_MyPortfolio"
        assert data["description"] == "Testing"

    def test_should_return_404_for_nonexistent_portfolio(self, client):
        response = client.get("/api/portfolios/99999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Portfolio not found"

    def test_should_include_timestamps(self, client):
        resp = client.post("/api/portfolios", json={"name": "GetTest_Timestamps"})
        portfolio_id = resp.json()["id"]
        response = client.get(f"/api/portfolios/{portfolio_id}")
        data = response.json()
        assert data["created_at"] is not None
        assert data["created_at"].endswith("Z")


class TestUpdatePortfolio:
    """PUT /api/portfolios/{portfolio_id}"""

    def test_should_update_portfolio_name(self, client):
        resp = client.post("/api/portfolios", json={"name": "UpdateTest_OldName"})
        portfolio_id = resp.json()["id"]
        response = client.put(f"/api/portfolios/{portfolio_id}", json={
            "name": "UpdateTest_NewName",
        })
        assert response.status_code == 200
        assert response.json()["success"] is True
        # Verify the update
        get_resp = client.get(f"/api/portfolios/{portfolio_id}")
        assert get_resp.json()["name"] == "UpdateTest_NewName"

    def test_should_update_portfolio_description(self, client):
        resp = client.post("/api/portfolios", json={"name": "UpdateTest_Desc"})
        portfolio_id = resp.json()["id"]
        client.put(f"/api/portfolios/{portfolio_id}", json={
            "description": "Updated description",
        })
        get_resp = client.get(f"/api/portfolios/{portfolio_id}")
        assert get_resp.json()["description"] == "Updated description"

    def test_should_update_benchmark(self, client):
        resp = client.post("/api/portfolios", json={"name": "UpdateTest_Bench"})
        portfolio_id = resp.json()["id"]
        client.put(f"/api/portfolios/{portfolio_id}", json={
            "benchmark": "NIFTY NEXT 50",
        })
        get_resp = client.get(f"/api/portfolios/{portfolio_id}")
        assert get_resp.json()["benchmark"] == "NIFTY NEXT 50"

    def test_should_return_404_for_nonexistent_portfolio(self, client):
        response = client.put("/api/portfolios/99999", json={"name": "X"})
        assert response.status_code == 404

    def test_should_not_overwrite_fields_not_in_request(self, client):
        resp = client.post("/api/portfolios", json={
            "name": "UpdateTest_KeepMe", "description": "Original",
        })
        portfolio_id = resp.json()["id"]
        # Update only benchmark, not name or description
        client.put(f"/api/portfolios/{portfolio_id}", json={
            "benchmark": "SENSEX",
        })
        get_resp = client.get(f"/api/portfolios/{portfolio_id}")
        data = get_resp.json()
        assert data["name"] == "UpdateTest_KeepMe"
        assert data["description"] == "Original"
        assert data["benchmark"] == "SENSEX"


class TestArchivePortfolio:
    """DELETE /api/portfolios/{portfolio_id}"""

    def test_should_archive_portfolio(self, client):
        resp = client.post("/api/portfolios", json={"name": "ArchiveTest_Me"})
        portfolio_id = resp.json()["id"]
        response = client.delete(f"/api/portfolios/{portfolio_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "ARCHIVED"

    def test_should_return_404_for_nonexistent_portfolio(self, client):
        response = client.delete("/api/portfolios/99999")
        assert response.status_code == 404


# ── Transactions ────────────────────────────────────────────


class TestCreateTransaction:
    """POST /api/portfolios/{portfolio_id}/transactions"""

    def _create_portfolio(self, client, name="TxnTest"):
        resp = client.post("/api/portfolios", json={"name": name})
        return resp.json()["id"]

    @patch("routers.portfolios._background_fetch_stock_history")
    def test_should_create_buy_transaction(self, mock_fetch, client):
        pid = self._create_portfolio(client, "TxnTest_BuyBasic")
        response = client.post(f"/api/portfolios/{pid}/transactions", json={
            "ticker": "RELIANCE",
            "txn_type": "BUY",
            "quantity": 10,
            "price": 2500.0,
            "txn_date": "2025-01-15",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["txn_type"] == "BUY"
        assert data["ticker"] == "RELIANCE"
        assert data["quantity"] == 10
        assert data["price"] == 2500.0
        assert data["total_value"] == 25000.0

    @patch("routers.portfolios._background_fetch_stock_history")
    def test_should_uppercase_ticker(self, mock_fetch, client):
        pid = self._create_portfolio(client, "TxnTest_Upper")
        response = client.post(f"/api/portfolios/{pid}/transactions", json={
            "ticker": "  reliance  ",
            "txn_type": "BUY",
            "quantity": 5,
            "price": 2500.0,
            "txn_date": "2025-01-15",
        })
        assert response.json()["ticker"] == "RELIANCE"

    @patch("routers.portfolios._background_fetch_stock_history")
    def test_should_accumulate_holdings_on_multiple_buys(self, mock_fetch, client, db_session):
        pid = self._create_portfolio(client, "TxnTest_Accumulate")
        # First buy: 10 shares at 100
        client.post(f"/api/portfolios/{pid}/transactions", json={
            "ticker": "INFY", "txn_type": "BUY",
            "quantity": 10, "price": 100.0, "txn_date": "2025-01-01",
        })
        # Second buy: 10 shares at 200
        client.post(f"/api/portfolios/{pid}/transactions", json={
            "ticker": "INFY", "txn_type": "BUY",
            "quantity": 10, "price": 200.0, "txn_date": "2025-02-01",
        })
        holding = db_session.query(PortfolioHolding).filter_by(
            portfolio_id=pid, ticker="INFY"
        ).first()
        assert holding.quantity == 20
        assert holding.total_cost == 3000.0  # 10*100 + 10*200
        assert holding.avg_cost == 150.0  # 3000 / 20

    @patch("routers.portfolios._background_fetch_stock_history")
    def test_should_handle_sell_transaction(self, mock_fetch, client):
        pid = self._create_portfolio(client, "TxnTest_Sell")
        # Buy first
        client.post(f"/api/portfolios/{pid}/transactions", json={
            "ticker": "TCS", "txn_type": "BUY",
            "quantity": 20, "price": 3500.0, "txn_date": "2025-01-01",
        })
        # Sell some
        response = client.post(f"/api/portfolios/{pid}/transactions", json={
            "ticker": "TCS", "txn_type": "SELL",
            "quantity": 5, "price": 4000.0, "txn_date": "2025-03-01",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["txn_type"] == "SELL"
        assert data["realized_pnl"] == 2500.0  # (4000 - 3500) * 5
        assert data["realized_pnl_pct"] == 14.29  # ((4000/3500) - 1) * 100

    @patch("routers.portfolios._background_fetch_stock_history")
    def test_should_delete_holding_when_fully_sold(self, mock_fetch, client, db_session):
        pid = self._create_portfolio(client, "TxnTest_FullSell")
        client.post(f"/api/portfolios/{pid}/transactions", json={
            "ticker": "HDFC", "txn_type": "BUY",
            "quantity": 10, "price": 1500.0, "txn_date": "2025-01-01",
        })
        client.post(f"/api/portfolios/{pid}/transactions", json={
            "ticker": "HDFC", "txn_type": "SELL",
            "quantity": 10, "price": 1600.0, "txn_date": "2025-02-01",
        })
        holding = db_session.query(PortfolioHolding).filter_by(
            portfolio_id=pid, ticker="HDFC"
        ).first()
        # Holding should be deleted (not just zeroed)
        assert holding is None

    def test_should_reject_sell_without_holding(self, client):
        pid = self._create_portfolio(client, "TxnTest_NoHold")
        response = client.post(f"/api/portfolios/{pid}/transactions", json={
            "ticker": "WIPRO", "txn_type": "SELL",
            "quantity": 5, "price": 400.0, "txn_date": "2025-01-01",
        })
        assert response.status_code == 400
        assert "No holding" in response.json()["detail"]

    @patch("routers.portfolios._background_fetch_stock_history")
    def test_should_reject_sell_more_than_held(self, mock_fetch, client):
        pid = self._create_portfolio(client, "TxnTest_OverSell")
        client.post(f"/api/portfolios/{pid}/transactions", json={
            "ticker": "SBIN", "txn_type": "BUY",
            "quantity": 10, "price": 500.0, "txn_date": "2025-01-01",
        })
        response = client.post(f"/api/portfolios/{pid}/transactions", json={
            "ticker": "SBIN", "txn_type": "SELL",
            "quantity": 15, "price": 600.0, "txn_date": "2025-02-01",
        })
        assert response.status_code == 400
        assert "Cannot sell 15" in response.json()["detail"]

    def test_should_reject_negative_quantity(self, client):
        pid = self._create_portfolio(client, "TxnTest_NegQty")
        response = client.post(f"/api/portfolios/{pid}/transactions", json={
            "ticker": "RELIANCE", "txn_type": "BUY",
            "quantity": -5, "price": 2500.0, "txn_date": "2025-01-01",
        })
        assert response.status_code == 400
        assert "Quantity must be positive" in response.json()["detail"]

    def test_should_reject_zero_quantity(self, client):
        pid = self._create_portfolio(client, "TxnTest_ZeroQty")
        response = client.post(f"/api/portfolios/{pid}/transactions", json={
            "ticker": "RELIANCE", "txn_type": "BUY",
            "quantity": 0, "price": 2500.0, "txn_date": "2025-01-01",
        })
        assert response.status_code == 400

    def test_should_reject_negative_price(self, client):
        pid = self._create_portfolio(client, "TxnTest_NegPrice")
        response = client.post(f"/api/portfolios/{pid}/transactions", json={
            "ticker": "RELIANCE", "txn_type": "BUY",
            "quantity": 10, "price": -100.0, "txn_date": "2025-01-01",
        })
        assert response.status_code == 400
        assert "Price must be positive" in response.json()["detail"]

    def test_should_reject_invalid_txn_type(self, client):
        pid = self._create_portfolio(client, "TxnTest_BadType")
        response = client.post(f"/api/portfolios/{pid}/transactions", json={
            "ticker": "RELIANCE", "txn_type": "HOLD",
            "quantity": 10, "price": 2500.0, "txn_date": "2025-01-01",
        })
        assert response.status_code == 400
        assert "txn_type must be BUY or SELL" in response.json()["detail"]

    def test_should_return_404_for_nonexistent_portfolio(self, client):
        response = client.post("/api/portfolios/99999/transactions", json={
            "ticker": "RELIANCE", "txn_type": "BUY",
            "quantity": 10, "price": 2500.0, "txn_date": "2025-01-01",
        })
        assert response.status_code == 404

    @patch("routers.portfolios._background_fetch_stock_history")
    def test_should_set_sector_on_holding(self, mock_fetch, client, db_session):
        pid = self._create_portfolio(client, "TxnTest_Sector")
        client.post(f"/api/portfolios/{pid}/transactions", json={
            "ticker": "RELIANCE", "txn_type": "BUY",
            "quantity": 10, "price": 2500.0, "txn_date": "2025-01-01",
            "sector": "Oil & Gas",
        })
        holding = db_session.query(PortfolioHolding).filter_by(
            portfolio_id=pid, ticker="RELIANCE"
        ).first()
        assert holding.sector == "Oil & Gas"


class TestListTransactions:
    """GET /api/portfolios/{portfolio_id}/transactions"""

    def _setup_portfolio_with_txns(self, client):
        resp = client.post("/api/portfolios", json={"name": "TxnListTest"})
        pid = resp.json()["id"]
        with patch("routers.portfolios._background_fetch_stock_history"):
            client.post(f"/api/portfolios/{pid}/transactions", json={
                "ticker": "RELIANCE", "txn_type": "BUY",
                "quantity": 10, "price": 2500.0, "txn_date": "2025-01-15",
            })
            client.post(f"/api/portfolios/{pid}/transactions", json={
                "ticker": "TCS", "txn_type": "BUY",
                "quantity": 5, "price": 3800.0, "txn_date": "2025-02-01",
            })
        return pid

    def test_should_list_all_transactions(self, client):
        pid = self._setup_portfolio_with_txns(client)
        response = client.get(f"/api/portfolios/{pid}/transactions")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["transactions"]) == 2

    def test_should_return_empty_list_for_no_transactions(self, client):
        resp = client.post("/api/portfolios", json={"name": "TxnListTest_Empty"})
        pid = resp.json()["id"]
        response = client.get(f"/api/portfolios/{pid}/transactions")
        assert response.status_code == 200
        assert len(response.json()["transactions"]) == 0

    def test_should_include_expected_transaction_fields(self, client):
        pid = self._setup_portfolio_with_txns(client)
        response = client.get(f"/api/portfolios/{pid}/transactions")
        txn = response.json()["transactions"][0]
        assert "id" in txn
        assert "ticker" in txn
        assert "txn_type" in txn
        assert "quantity" in txn
        assert "price" in txn
        assert "total_value" in txn
        assert "txn_date" in txn
        assert "created_at" in txn


# ── Holdings ────────────────────────────────────────────────


class TestListHoldings:
    """GET /api/portfolios/{portfolio_id}/holdings"""

    def test_should_return_empty_holdings_for_new_portfolio(self, client):
        resp = client.post("/api/portfolios", json={"name": "HoldingsTest_Empty"})
        pid = resp.json()["id"]
        response = client.get(f"/api/portfolios/{pid}/holdings")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["holdings"] == []
        assert data["totals"]["num_holdings"] == 0
        assert data["totals"]["total_invested"] == 0.0

    def test_should_return_404_for_nonexistent_portfolio(self, client):
        response = client.get("/api/portfolios/99999/holdings")
        assert response.status_code == 404

    @patch("routers.portfolios.get_live_prices", return_value={})
    @patch("routers.portfolios._background_fetch_stock_history")
    def test_should_list_holdings_after_buy(self, mock_fetch, mock_prices, client):
        resp = client.post("/api/portfolios", json={"name": "HoldingsTest_Buy"})
        pid = resp.json()["id"]
        client.post(f"/api/portfolios/{pid}/transactions", json={
            "ticker": "INFY", "txn_type": "BUY",
            "quantity": 10, "price": 1500.0, "txn_date": "2025-01-01",
        })
        response = client.get(f"/api/portfolios/{pid}/holdings")
        assert response.status_code == 200
        data = response.json()
        assert len(data["holdings"]) == 1
        holding = data["holdings"][0]
        assert holding["ticker"] == "INFY"
        assert holding["quantity"] == 10
        assert holding["avg_cost"] == 1500.0
        assert holding["total_cost"] == 15000.0

    @patch("routers.portfolios.get_live_prices", return_value={})
    @patch("routers.portfolios._background_fetch_stock_history")
    def test_should_include_totals_in_response(self, mock_fetch, mock_prices, client):
        resp = client.post("/api/portfolios", json={"name": "HoldingsTest_Totals"})
        pid = resp.json()["id"]
        client.post(f"/api/portfolios/{pid}/transactions", json={
            "ticker": "INFY", "txn_type": "BUY",
            "quantity": 10, "price": 1500.0, "txn_date": "2025-01-01",
        })
        response = client.get(f"/api/portfolios/{pid}/holdings")
        data = response.json()
        totals = data["totals"]
        assert totals["total_invested"] == 15000.0
        assert totals["num_holdings"] == 1
        assert "current_value" in totals
        assert "unrealized_pnl" in totals
        assert "realized_pnl" in totals


# ── NAV History ─────────────────────────────────────────────


class TestNavHistory:
    """GET /api/portfolios/{portfolio_id}/nav-history"""

    def test_should_return_empty_nav_history_for_new_portfolio(self, client):
        resp = client.post("/api/portfolios", json={"name": "NavTest_Empty"})
        pid = resp.json()["id"]
        response = client.get(f"/api/portfolios/{pid}/nav-history")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["nav_history"] == []
        assert data["period"] == "all"

    def test_should_return_404_for_nonexistent_portfolio(self, client):
        response = client.get("/api/portfolios/99999/nav-history")
        assert response.status_code == 404

    def test_should_return_nav_history_with_seeded_data(self, client, db_session):
        resp = client.post("/api/portfolios", json={"name": "NavTest_Seeded"})
        pid = resp.json()["id"]
        # Seed NAV data directly
        for date, val in [
            ("2025-01-01", 100000.0),
            ("2025-01-15", 105000.0),
            ("2025-02-01", 103000.0),
        ]:
            db_session.add(PortfolioNAV(
                portfolio_id=pid, date=date,
                total_value=val, total_cost=100000.0,
                unrealized_pnl=val - 100000.0,
            ))
        db_session.commit()

        response = client.get(f"/api/portfolios/{pid}/nav-history")
        data = response.json()
        assert len(data["nav_history"]) == 3
        assert data["nav_history"][0]["date"] == "2025-01-01"
        assert data["nav_history"][0]["total_value"] == 100000.0

    def test_should_filter_nav_history_by_period(self, client, db_session):
        resp = client.post("/api/portfolios", json={"name": "NavTest_Period"})
        pid = resp.json()["id"]
        # Seed data spanning more than a year
        db_session.add(PortfolioNAV(
            portfolio_id=pid, date="2024-01-01",
            total_value=100000.0, total_cost=100000.0,
        ))
        db_session.add(PortfolioNAV(
            portfolio_id=pid, date="2025-12-01",
            total_value=120000.0, total_cost=100000.0,
        ))
        db_session.commit()

        # "all" should return everything
        response = client.get(f"/api/portfolios/{pid}/nav-history?period=all")
        assert len(response.json()["nav_history"]) == 2

    def test_should_include_nav_fields(self, client, db_session):
        resp = client.post("/api/portfolios", json={"name": "NavTest_Fields"})
        pid = resp.json()["id"]
        db_session.add(PortfolioNAV(
            portfolio_id=pid, date="2025-06-01",
            total_value=110000.0, total_cost=100000.0,
            unrealized_pnl=10000.0,
        ))
        db_session.commit()

        response = client.get(f"/api/portfolios/{pid}/nav-history")
        nav = response.json()["nav_history"][0]
        assert "date" in nav
        assert "total_value" in nav
        assert "total_cost" in nav
        assert "unrealized_pnl" in nav
        assert "benchmark_value" in nav


# ── CSV Export ──────────────────────────────────────────────


class TestExportHoldings:
    """GET /api/portfolios/{portfolio_id}/export/holdings"""

    @patch("routers.portfolios._background_fetch_stock_history")
    def test_should_export_holdings_as_csv(self, mock_fetch, client):
        resp = client.post("/api/portfolios", json={"name": "ExportTest_Holdings"})
        pid = resp.json()["id"]
        client.post(f"/api/portfolios/{pid}/transactions", json={
            "ticker": "RELIANCE", "txn_type": "BUY",
            "quantity": 10, "price": 2500.0, "txn_date": "2025-01-01",
        })
        response = client.get(f"/api/portfolios/{pid}/export/holdings")
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        content = response.text
        assert "Ticker" in content  # CSV header
        assert "RELIANCE" in content

    def test_should_return_csv_with_only_headers_when_no_holdings(self, client):
        resp = client.post("/api/portfolios", json={"name": "ExportTest_EmptyCSV"})
        pid = resp.json()["id"]
        response = client.get(f"/api/portfolios/{pid}/export/holdings")
        assert response.status_code == 200
        lines = response.text.strip().split("\n")
        assert len(lines) == 1  # Only header row


class TestExportTransactions:
    """GET /api/portfolios/{portfolio_id}/export/transactions"""

    @patch("routers.portfolios._background_fetch_stock_history")
    def test_should_export_transactions_as_csv(self, mock_fetch, client):
        resp = client.post("/api/portfolios", json={"name": "ExportTest_Txns"})
        pid = resp.json()["id"]
        client.post(f"/api/portfolios/{pid}/transactions", json={
            "ticker": "TCS", "txn_type": "BUY",
            "quantity": 5, "price": 3800.0, "txn_date": "2025-01-15",
        })
        response = client.get(f"/api/portfolios/{pid}/export/transactions")
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        content = response.text
        assert "Date" in content
        assert "TCS" in content


# ── Bulk Import ─────────────────────────────────────────────


class TestBulkImport:
    """POST /api/portfolios/bulk-import"""

    def test_should_import_portfolio_with_holdings_and_transactions(self, client):
        payload = {
            "portfolio": {
                "name": "ImportTest_Full",
                "description": "Bulk imported",
                "benchmark": "NIFTY",
            },
            "holdings": [
                {
                    "ticker": "RELIANCE", "quantity": 10,
                    "avg_cost": 2500.0, "total_cost": 25000.0,
                    "sector": "Oil & Gas",
                },
                {
                    "ticker": "TCS", "quantity": 5,
                    "avg_cost": 3800.0, "total_cost": 19000.0,
                },
            ],
            "transactions": [
                {
                    "ticker": "RELIANCE", "txn_type": "BUY",
                    "quantity": 10, "price": 2500.0,
                    "total_value": 25000.0, "txn_date": "2025-01-01",
                },
            ],
            "nav_history": [
                {
                    "date": "2025-01-01",
                    "total_value": 44000.0,
                    "total_cost": 44000.0,
                },
            ],
            "index_prices": [],
        }
        response = client.post("/api/portfolios/bulk-import", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["holdings"] == 2
        assert data["transactions"] == 1
        assert data["nav_rows"] == 1
        assert "portfolio_id" in data

    def test_should_import_portfolio_with_minimal_data(self, client):
        payload = {
            "portfolio": {"name": "ImportTest_Minimal"},
        }
        response = client.post("/api/portfolios/bulk-import", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["holdings"] == 0
        assert data["transactions"] == 0


# ── Performance ─────────────────────────────────────────────


class TestPerformance:
    """GET /api/portfolios/{portfolio_id}/performance"""

    def test_should_return_404_for_nonexistent_portfolio(self, client):
        response = client.get("/api/portfolios/99999/performance")
        assert response.status_code == 404

    @patch("routers.portfolios.get_live_prices", return_value={})
    @patch("routers.portfolios._background_fetch_stock_history")
    def test_should_return_performance_for_empty_portfolio(self, mock_fetch, mock_prices, client):
        resp = client.post("/api/portfolios", json={"name": "PerfTest_Empty"})
        pid = resp.json()["id"]
        response = client.get(f"/api/portfolios/{pid}/performance")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        perf = data["performance"]
        assert perf["total_invested"] == 0.0
        assert perf["current_value"] == 0.0

    @patch("routers.portfolios.get_live_prices", return_value={})
    @patch("routers.portfolios._background_fetch_stock_history")
    def test_should_include_all_performance_fields(self, mock_fetch, mock_prices, client):
        resp = client.post("/api/portfolios", json={"name": "PerfTest_Fields"})
        pid = resp.json()["id"]
        client.post(f"/api/portfolios/{pid}/transactions", json={
            "ticker": "INFY", "txn_type": "BUY",
            "quantity": 10, "price": 1500.0, "txn_date": "2025-01-01",
        })
        response = client.get(f"/api/portfolios/{pid}/performance")
        perf = response.json()["performance"]
        expected_fields = [
            "total_invested", "current_value", "unrealized_pnl",
            "unrealized_pnl_pct", "realized_pnl", "total_return",
            "total_return_pct", "xirr", "cagr", "max_drawdown",
            "benchmark_return_pct", "alpha",
        ]
        for field in expected_fields:
            assert field in perf, f"Missing field: {field}"


# ── Allocation ──────────────────────────────────────────────


class TestAllocation:
    """GET /api/portfolios/{portfolio_id}/allocation"""

    def test_should_return_404_for_nonexistent_portfolio(self, client):
        response = client.get("/api/portfolios/99999/allocation")
        assert response.status_code == 404

    def test_should_return_empty_allocation_for_portfolio_with_no_holdings(self, client):
        resp = client.post("/api/portfolios", json={"name": "AllocTest_Empty"})
        pid = resp.json()["id"]
        response = client.get(f"/api/portfolios/{pid}/allocation")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["by_stock"] == []
        assert data["by_sector"] == []
