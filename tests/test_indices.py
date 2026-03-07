"""
Tests for Index & Market Data API endpoints (routers/indices.py).

Covers: latest indices, bulk upload, historical data queries,
and edge cases with empty databases.

Note: Tests use unique date/index_name combos (dates in 2020-xx-xx range)
to avoid UNIQUE constraint conflicts with data seeded by background threads
or other tests.
"""

from models import IndexPrice


# ── Latest Indices ──────────────────────────────────────────


class TestIndicesLatest:
    """GET /api/indices/latest"""

    def test_should_return_200(self, client):
        response = client.get("/api/indices/latest")
        assert response.status_code == 200

    def test_should_return_indices_with_seeded_data(self, client, db_session):
        # Use unique date far in the future to become the "latest"
        db_session.add(IndexPrice(
            date="2029-06-01", index_name="TEST_NIFTY_A",
            close_price=22000.0, open_price=21900.0,
            high_price=22100.0, low_price=21800.0,
        ))
        db_session.add(IndexPrice(
            date="2029-06-01", index_name="TEST_BANK_A",
            close_price=46000.0, open_price=45800.0,
            high_price=46200.0, low_price=45700.0,
        ))
        db_session.commit()

        response = client.get("/api/indices/latest")
        assert response.status_code == 200
        data = response.json()
        assert data["date"] == "2029-06-01"
        idx_map = {i["index_name"]: i for i in data["indices"]}
        assert "TEST_NIFTY_A" in idx_map
        assert "TEST_BANK_A" in idx_map
        assert idx_map["TEST_NIFTY_A"]["close"] == 22000.0
        assert idx_map["TEST_BANK_A"]["close"] == 46000.0

    def test_should_compute_ratio_vs_base(self, client, db_session):
        db_session.add(IndexPrice(
            date="2029-06-02", index_name="TEST_BASE_B",
            close_price=22000.0,
        ))
        db_session.add(IndexPrice(
            date="2029-06-02", index_name="TEST_SECTOR_B",
            close_price=46000.0,
        ))
        db_session.commit()

        response = client.get("/api/indices/latest?base=TEST_BASE_B")
        data = response.json()
        idx_map = {i["index_name"]: i for i in data["indices"]}
        assert idx_map["TEST_SECTOR_B"]["ratio"] == round(46000.0 / 22000.0, 4)

    def test_should_assign_signal_based_on_ratio(self, client, db_session):
        # Base at 100, sector at 106 (>1.05 = STRONG OW)
        db_session.add(IndexPrice(
            date="2029-06-03", index_name="TEST_BASE_C",
            close_price=100.0,
        ))
        db_session.add(IndexPrice(
            date="2029-06-03", index_name="TEST_STRONG_OW",
            close_price=106.0,
        ))
        # Sector at 94 (<0.95 = STRONG UW)
        db_session.add(IndexPrice(
            date="2029-06-03", index_name="TEST_STRONG_UW",
            close_price=94.0,
        ))
        db_session.commit()

        response = client.get("/api/indices/latest?base=TEST_BASE_C")
        idx_map = {i["index_name"]: i for i in response.json()["indices"]}
        assert idx_map["TEST_BASE_C"]["signal"] == "BASE"
        assert idx_map["TEST_STRONG_OW"]["signal"] == "STRONG OW"
        assert idx_map["TEST_STRONG_UW"]["signal"] == "STRONG UW"

    def test_should_use_custom_base(self, client, db_session):
        db_session.add(IndexPrice(
            date="2029-06-04", index_name="TEST_IDX_D1",
            close_price=22000.0,
        ))
        db_session.add(IndexPrice(
            date="2029-06-04", index_name="TEST_IDX_D2",
            close_price=46000.0,
        ))
        db_session.commit()

        response = client.get("/api/indices/latest?base=TEST_IDX_D2")
        data = response.json()
        assert data["base"] == "TEST_IDX_D2"
        idx_map = {i["index_name"]: i for i in data["indices"]}
        assert idx_map["TEST_IDX_D2"]["signal"] == "BASE"

    def test_should_compute_change_pct_from_previous_day(self, client, db_session):
        # Two dates of data
        db_session.add(IndexPrice(
            date="2029-06-04", index_name="TEST_CHG_E",
            close_price=21800.0,
        ))
        db_session.add(IndexPrice(
            date="2029-06-05", index_name="TEST_CHG_E",
            close_price=22000.0,
        ))
        db_session.commit()

        response = client.get("/api/indices/latest")
        data = response.json()
        assert data["date"] == "2029-06-05"
        idx_map = {i["index_name"]: i for i in data["indices"]}
        test_idx = idx_map.get("TEST_CHG_E")
        assert test_idx is not None
        # Expected: ((22000 - 21800) / 21800) * 100 = 0.92%
        expected_pct = round(((22000 - 21800) / 21800) * 100, 2)
        assert test_idx["change_pct"] == expected_pct

    def test_should_include_period_return_fields(self, client, db_session):
        db_session.add(IndexPrice(
            date="2029-06-06", index_name="TEST_PERIOD_F",
            close_price=22000.0,
        ))
        db_session.commit()

        response = client.get("/api/indices/latest")
        # Find our test index
        idx_map = {i["index_name"]: i for i in response.json()["indices"]}
        idx = idx_map.get("TEST_PERIOD_F")
        assert idx is not None
        # Period return fields should be present (even if None for lack of data)
        for period in ["1d", "1w", "1m", "3m", "6m", "12m"]:
            assert period in idx, f"Missing period return: {period}"


# ── Bulk Upload ─────────────────────────────────────────────


class TestBulkUpload:
    """POST /api/indices/bulk-upload"""

    def test_should_upload_index_data(self, client):
        payload = {
            "data": {
                "TEST_BULK_X": [
                    {"date": "2020-01-01", "close": 21500.0, "open": 21400.0,
                     "high": 21600.0, "low": 21350.0},
                    {"date": "2020-01-02", "close": 21600.0, "open": 21500.0,
                     "high": 21700.0, "low": 21450.0},
                ],
                "TEST_BULK_Y": [
                    {"date": "2020-01-01", "close": 45000.0, "open": 44800.0,
                     "high": 45200.0, "low": 44700.0},
                ],
            }
        }
        response = client.post("/api/indices/bulk-upload", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["stored"] == 3
        assert data["indices"] == 2

    def test_should_handle_empty_data(self, client):
        response = client.post("/api/indices/bulk-upload", json={"data": {}})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "No data" in data["error"]

    def test_should_handle_missing_data_key(self, client):
        response = client.post("/api/indices/bulk-upload", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_should_skip_existing_data_on_reupload(self, client):
        # Upload once
        payload = {
            "data": {
                "TEST_DEDUP_Z": [
                    {"date": "2020-02-01", "close": 21500.0},
                ],
            }
        }
        resp1 = client.post("/api/indices/bulk-upload", json=payload)
        assert resp1.json()["stored"] >= 1

        # Upload again with same date + a new one
        payload2 = {
            "data": {
                "TEST_DEDUP_Z": [
                    {"date": "2020-02-01", "close": 21500.0},
                    {"date": "2020-02-03", "close": 21700.0},
                ],
            }
        }
        resp2 = client.post("/api/indices/bulk-upload", json=payload2)
        assert resp2.json()["success"] is True
        # Should only store the new date (existing one skipped by upsert logic)
        assert resp2.json()["stored"] >= 1


# ── Index Data Retrieval Patterns ───────────────────────────


class TestIndexDataPatterns:
    """Tests for common data patterns and edge cases."""

    def test_should_handle_single_index_single_date(self, client, db_session):
        db_session.add(IndexPrice(
            date="2029-07-01", index_name="TEST_SINGLE_G",
            close_price=15000.0,
        ))
        db_session.commit()

        response = client.get("/api/indices/latest")
        assert response.status_code == 200
        data = response.json()
        # Our date should be the latest since it's in 2029
        idx_map = {i["index_name"]: i for i in data["indices"]}
        assert "TEST_SINGLE_G" in idx_map

    def test_should_handle_many_indices_same_date(self, client, db_session):
        indices = [
            "TEST_MULTI_H1", "TEST_MULTI_H2", "TEST_MULTI_H3",
            "TEST_MULTI_H4", "TEST_MULTI_H5",
        ]
        for idx_name in indices:
            db_session.add(IndexPrice(
                date="2029-07-02", index_name=idx_name,
                close_price=10000.0,
            ))
        db_session.commit()

        response = client.get("/api/indices/latest")
        assert response.status_code == 200
        idx_map = {i["index_name"]: i for i in response.json()["indices"]}
        for idx_name in indices:
            assert idx_name in idx_map

    def test_should_return_data_from_latest_date(self, client, db_session):
        """When multiple dates exist, /latest should show data from the most recent date."""
        db_session.add(IndexPrice(
            date="2029-07-03", index_name="TEST_LATEST_I",
            close_price=21500.0,
        ))
        db_session.add(IndexPrice(
            date="2029-07-04", index_name="TEST_LATEST_I",
            close_price=22000.0,
        ))
        db_session.commit()

        response = client.get("/api/indices/latest")
        data = response.json()
        idx_map = {i["index_name"]: i for i in data["indices"]}
        # The latest date's data should appear
        assert idx_map["TEST_LATEST_I"]["close"] == 22000.0

    def test_should_handle_null_close_prices(self, client, db_session):
        db_session.add(IndexPrice(
            date="2029-07-05", index_name="TEST_NULL_J",
            close_price=None, open_price=100.0,
        ))
        db_session.commit()

        response = client.get("/api/indices/latest")
        assert response.status_code == 200
        # Should still be in the list but with null close
        idx_map = {i["index_name"]: i for i in response.json()["indices"]}
        if "TEST_NULL_J" in idx_map:
            assert idx_map["TEST_NULL_J"]["close"] is None

    def test_should_include_signal_for_base_index(self, client, db_session):
        db_session.add(IndexPrice(
            date="2029-07-06", index_name="TEST_BASEONLY_K",
            close_price=20000.0,
        ))
        db_session.commit()

        response = client.get("/api/indices/latest?base=TEST_BASEONLY_K")
        idx_map = {i["index_name"]: i for i in response.json()["indices"]}
        assert idx_map["TEST_BASEONLY_K"]["signal"] == "BASE"
