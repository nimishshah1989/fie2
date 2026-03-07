"""
Tests for Alert API endpoints (routers/alerts.py).

Covers: webhook ingestion, alert CRUD, FM actions (approve/deny),
signal inference, chart retrieval, and edge cases.
"""




# ── Webhook Ingestion ───────────────────────────────────────


class TestWebhookIngestion:
    """POST /webhook/tradingview"""

    def test_should_ingest_valid_webhook_payload(self, client):
        payload = {
            "ticker": "RELIANCE",
            "exchange": "NSE",
            "interval": "1D",
            "time": "2025-03-07T15:30:00Z",
            "open": 2480.0,
            "high": 2520.0,
            "low": 2470.0,
            "close": 2510.0,
            "volume": 1234567,
            "data": "RELIANCE bullish breakout above resistance. RSI showing oversold bounce.",
        }
        response = client.post("/webhook/tradingview", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "alert_id" in data

    def test_should_ingest_minimal_payload(self, client):
        payload = {"ticker": "INFY"}
        response = client.post("/webhook/tradingview", json=payload)
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_should_handle_payload_with_prefixed_price_keys(self, client):
        payload = {
            "ticker": "TCS",
            "price_open": 3800.0,
            "price_high": 3850.0,
            "price_low": 3780.0,
            "price_at_alert": 3830.0,
        }
        response = client.post("/webhook/tradingview", json=payload)
        assert response.status_code == 200
        alert_id = response.json()["alert_id"]
        # Verify stored values
        alert_resp = client.get(f"/api/alerts/{alert_id}")
        alert = alert_resp.json()
        assert alert["price_open"] == 3800.0
        assert alert["price_at_alert"] == 3830.0

    def test_should_default_to_unknown_ticker_when_missing(self, client):
        payload = {"data": "Some alert data without a ticker"}
        response = client.post("/webhook/tradingview", json=payload)
        assert response.status_code == 200
        alert_id = response.json()["alert_id"]
        alert = client.get(f"/api/alerts/{alert_id}").json()
        assert alert["ticker"] == "UNKNOWN"

    def test_should_infer_bullish_signal_from_text(self, client):
        payload = {
            "ticker": "HDFCBANK",
            "data": "Golden cross detected. Price crossed above 200 DMA. Buy signal.",
        }
        response = client.post("/webhook/tradingview", json=payload)
        assert response.status_code == 200
        alert_id = response.json()["alert_id"]
        alert = client.get(f"/api/alerts/{alert_id}").json()
        assert alert["signal_direction"] == "BULLISH"

    def test_should_infer_bearish_signal_from_text(self, client):
        payload = {
            "ticker": "TATASTEEL",
            "data": "Death cross detected. Bearish breakdown below support. Sell signal.",
        }
        response = client.post("/webhook/tradingview", json=payload)
        assert response.status_code == 200
        alert_id = response.json()["alert_id"]
        alert = client.get(f"/api/alerts/{alert_id}").json()
        assert alert["signal_direction"] == "BEARISH"

    def test_should_use_explicit_signal_direction(self, client):
        payload = {
            "ticker": "SBIN",
            "signal_direction": "BEARISH",
            "data": "This text has bullish words but explicit signal should win.",
        }
        response = client.post("/webhook/tradingview", json=payload)
        assert response.status_code == 200
        alert_id = response.json()["alert_id"]
        alert = client.get(f"/api/alerts/{alert_id}").json()
        assert alert["signal_direction"] == "BEARISH"

    def test_should_use_strategy_action_for_signal(self, client):
        payload = {
            "ticker": "ICICIBANK",
            "strategy_action": "buy",
        }
        response = client.post("/webhook/tradingview", json=payload)
        assert response.status_code == 200
        alert_id = response.json()["alert_id"]
        alert = client.get(f"/api/alerts/{alert_id}").json()
        assert alert["signal_direction"] == "BULLISH"

    def test_should_default_to_neutral_signal(self, client):
        payload = {
            "ticker": "ITC",
            "data": "Price at 450. No clear direction.",
        }
        response = client.post("/webhook/tradingview", json=payload)
        assert response.status_code == 200
        alert_id = response.json()["alert_id"]
        alert = client.get(f"/api/alerts/{alert_id}").json()
        assert alert["signal_direction"] == "NEUTRAL"

    def test_should_handle_non_json_body(self, client):
        response = client.post(
            "/webhook/tradingview",
            content=b"Plain text alert data",
            headers={"content-type": "text/plain"},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_should_set_status_to_pending(self, client):
        payload = {"ticker": "WIPRO"}
        response = client.post("/webhook/tradingview", json=payload)
        alert_id = response.json()["alert_id"]
        alert = client.get(f"/api/alerts/{alert_id}").json()
        assert alert["status"] == "PENDING"

    def test_should_use_explicit_alert_name(self, client):
        payload = {
            "ticker": "AXISBANK",
            "alert_name": "Axis Bank RSI Crossover",
        }
        response = client.post("/webhook/tradingview", json=payload)
        alert_id = response.json()["alert_id"]
        alert = client.get(f"/api/alerts/{alert_id}").json()
        assert alert["alert_name"] == "Axis Bank RSI Crossover"

    def test_should_parse_alert_name_from_data(self, client):
        payload = {
            "ticker": "LT",
            "data": "L&T Momentum Breakout. Price surged above 3000.",
        }
        response = client.post("/webhook/tradingview", json=payload)
        alert_id = response.json()["alert_id"]
        alert = client.get(f"/api/alerts/{alert_id}").json()
        # Should use first line, split on "."
        assert alert["alert_name"] == "L&T Momentum Breakout"

    def test_should_handle_template_variables_in_ticker(self, client):
        payload = {
            "ticker": "{{ticker}}",
            "data": "Unresolved template",
        }
        response = client.post("/webhook/tradingview", json=payload)
        assert response.status_code == 200
        alert_id = response.json()["alert_id"]
        alert = client.get(f"/api/alerts/{alert_id}").json()
        # Template variable should be cleaned to UNKNOWN
        assert alert["ticker"] == "UNKNOWN"

    def test_should_handle_alert_message_key(self, client):
        payload = {
            "ticker": "BHARTIARTL",
            "alert_message": "Bharti Airtel crossed above 1500",
        }
        response = client.post("/webhook/tradingview", json=payload)
        assert response.status_code == 200
        alert_id = response.json()["alert_id"]
        alert = client.get(f"/api/alerts/{alert_id}").json()
        assert "crossed above" in alert["alert_data"]

    def test_should_handle_extra_fields_gracefully(self, client):
        """TradingView can send arbitrary extra fields. They should not cause errors."""
        payload = {
            "ticker": "SUNPHARMA",
            "custom_field": "some value",
            "another_extra": 42,
        }
        response = client.post("/webhook/tradingview", json=payload)
        assert response.status_code == 200

    def test_should_support_trailing_slash_url(self, client):
        payload = {"ticker": "KOTAKBANK"}
        response = client.post("/webhook/tradingview/", json=payload)
        assert response.status_code == 200
        assert response.json()["success"] is True


# ── Alert CRUD ──────────────────────────────────────────────


class TestListAlerts:
    """GET /api/alerts"""

    def _create_alert(self, client, ticker="RELIANCE", data=None):
        payload = {"ticker": ticker}
        if data:
            payload["data"] = data
        resp = client.post("/webhook/tradingview", json=payload)
        return resp.json()["alert_id"]

    def test_should_return_empty_alerts_list(self, client):
        response = client.get("/api/alerts")
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        # May have alerts from other tests, but structure should be correct
        assert isinstance(data["alerts"], list)

    def test_should_list_alerts_after_webhook(self, client):
        self._create_alert(client, "RELIANCE")
        self._create_alert(client, "TCS")
        response = client.get("/api/alerts")
        assert response.status_code == 200
        tickers = [a["ticker"] for a in response.json()["alerts"]]
        assert "RELIANCE" in tickers
        assert "TCS" in tickers

    def test_should_filter_alerts_by_status(self, client, db_session):
        alert_id = self._create_alert(client, "FILTERSTATUS")
        # All new alerts are PENDING
        response = client.get("/api/alerts?status=PENDING")
        assert response.status_code == 200
        pending_tickers = [a["ticker"] for a in response.json()["alerts"]]
        assert "FILTERSTATUS" in pending_tickers

        # APPROVED filter should not include this alert
        response = client.get("/api/alerts?status=APPROVED")
        approved_tickers = [a["ticker"] for a in response.json()["alerts"]]
        assert "FILTERSTATUS" not in approved_tickers

    def test_should_return_all_when_status_is_All(self, client):
        self._create_alert(client, "ALLFILTER")
        response = client.get("/api/alerts?status=All")
        assert response.status_code == 200
        tickers = [a["ticker"] for a in response.json()["alerts"]]
        assert "ALLFILTER" in tickers

    def test_should_respect_limit_parameter(self, client):
        for i in range(5):
            self._create_alert(client, f"LIMIT{i}")
        response = client.get("/api/alerts?limit=2")
        assert response.status_code == 200
        assert len(response.json()["alerts"]) <= 2

    def test_should_include_expected_fields_in_alert(self, client):
        self._create_alert(client, "FIELDCHECK")
        response = client.get("/api/alerts")
        alert = response.json()["alerts"][0]
        expected_fields = [
            "id", "ticker", "exchange", "interval",
            "price_close", "price_at_alert", "volume",
            "alert_data", "alert_name", "signal_direction",
            "status", "received_at", "action",
        ]
        for field in expected_fields:
            assert field in alert, f"Missing field: {field}"


class TestGetAlert:
    """GET /api/alerts/{alert_id}"""

    def test_should_return_alert_by_id(self, client):
        resp = client.post("/webhook/tradingview", json={
            "ticker": "BAJFINANCE", "data": "Test alert",
        })
        alert_id = resp.json()["alert_id"]
        response = client.get(f"/api/alerts/{alert_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == alert_id
        assert data["ticker"] == "BAJFINANCE"

    def test_should_return_404_for_nonexistent_alert(self, client):
        response = client.get("/api/alerts/99999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Not found"


# ── FM Actions ──────────────────────────────────────────────


class TestAlertAction:
    """POST /api/alerts/{alert_id}/action"""

    def _create_alert(self, client, ticker="TESTSTOCK"):
        resp = client.post("/webhook/tradingview", json={
            "ticker": ticker, "close": 100.0,
        })
        return resp.json()["alert_id"]

    def test_should_approve_alert(self, client):
        alert_id = self._create_alert(client)
        response = client.post(f"/api/alerts/{alert_id}/action", json={
            "alert_id": alert_id,
            "decision": "APPROVED",
            "action_call": "BUY",
        })
        assert response.status_code == 200
        assert response.json()["success"] is True
        # Verify status changed
        alert = client.get(f"/api/alerts/{alert_id}").json()
        assert alert["status"] == "APPROVED"
        assert alert["action"]["decision"] == "APPROVED"
        assert alert["action"]["action_call"] == "BUY"

    def test_should_deny_alert(self, client):
        alert_id = self._create_alert(client)
        response = client.post(f"/api/alerts/{alert_id}/action", json={
            "alert_id": alert_id,
            "decision": "DENIED",
        })
        assert response.status_code == 200
        alert = client.get(f"/api/alerts/{alert_id}").json()
        assert alert["status"] == "DENIED"

    def test_should_set_trade_parameters(self, client):
        alert_id = self._create_alert(client)
        response = client.post(f"/api/alerts/{alert_id}/action", json={
            "alert_id": alert_id,
            "decision": "APPROVED",
            "action_call": "BUY",
            "entry_price_low": 95.0,
            "entry_price_high": 105.0,
            "stop_loss": 85.0,
            "target_price": 130.0,
        })
        assert response.status_code == 200
        alert = client.get(f"/api/alerts/{alert_id}").json()
        action = alert["action"]
        assert action["entry_price_low"] == 95.0
        assert action["entry_price_high"] == 105.0
        assert action["stop_loss"] == 85.0
        assert action["target_price"] == 130.0

    def test_should_set_priority(self, client):
        alert_id = self._create_alert(client)
        response = client.post(f"/api/alerts/{alert_id}/action", json={
            "alert_id": alert_id,
            "decision": "APPROVED",
            "priority": "IMMEDIATELY",
        })
        assert response.status_code == 200
        alert = client.get(f"/api/alerts/{alert_id}").json()
        assert alert["action"]["priority"] == "IMMEDIATELY"

    def test_should_set_ratio_trade_fields(self, client):
        alert_id = self._create_alert(client)
        response = client.post(f"/api/alerts/{alert_id}/action", json={
            "alert_id": alert_id,
            "decision": "APPROVED",
            "action_call": "RATIO",
            "is_ratio": True,
            "ratio_long": "LONG 60% RELIANCE",
            "ratio_short": "SHORT 40% HDFCBANK",
            "ratio_numerator_ticker": "RELIANCE",
            "ratio_denominator_ticker": "HDFCBANK",
        })
        assert response.status_code == 200
        alert = client.get(f"/api/alerts/{alert_id}").json()
        action = alert["action"]
        assert action["is_ratio"] is True
        assert action["ratio_long"] == "LONG 60% RELIANCE"
        assert action["ratio_short"] == "SHORT 40% HDFCBANK"
        assert action["ratio_numerator_ticker"] == "RELIANCE"
        assert action["ratio_denominator_ticker"] == "HDFCBANK"

    def test_should_set_fm_notes(self, client):
        alert_id = self._create_alert(client)
        response = client.post(f"/api/alerts/{alert_id}/action", json={
            "alert_id": alert_id,
            "decision": "APPROVED",
            "fm_notes": "Looks like a strong setup. Enter on pullback.",
        })
        assert response.status_code == 200
        alert = client.get(f"/api/alerts/{alert_id}").json()
        assert alert["action"]["fm_notes"] == "Looks like a strong setup. Enter on pullback."

    def test_should_return_404_for_nonexistent_alert(self, client):
        response = client.post("/api/alerts/99999/action", json={
            "alert_id": 99999, "decision": "APPROVED",
        })
        assert response.status_code == 404

    def test_should_overwrite_previous_action(self, client):
        alert_id = self._create_alert(client)
        # First action: DENIED
        client.post(f"/api/alerts/{alert_id}/action", json={
            "alert_id": alert_id, "decision": "DENIED",
        })
        # Second action: APPROVED (should overwrite)
        client.post(f"/api/alerts/{alert_id}/action", json={
            "alert_id": alert_id, "decision": "APPROVED",
            "action_call": "BUY",
        })
        alert = client.get(f"/api/alerts/{alert_id}").json()
        assert alert["status"] == "APPROVED"
        assert alert["action"]["decision"] == "APPROVED"


class TestUpdateAction:
    """PUT /api/alerts/{alert_id}/action"""

    def _create_and_approve_alert(self, client):
        resp = client.post("/webhook/tradingview", json={
            "ticker": "UPDATETEST", "close": 100.0,
        })
        alert_id = resp.json()["alert_id"]
        client.post(f"/api/alerts/{alert_id}/action", json={
            "alert_id": alert_id, "decision": "APPROVED",
            "action_call": "BUY",
        })
        return alert_id

    def test_should_update_action_call(self, client):
        alert_id = self._create_and_approve_alert(client)
        response = client.put(f"/api/alerts/{alert_id}/action", json={
            "action_call": "SELL",
        })
        assert response.status_code == 200
        alert = client.get(f"/api/alerts/{alert_id}").json()
        assert alert["action"]["action_call"] == "SELL"

    def test_should_update_fm_notes(self, client):
        alert_id = self._create_and_approve_alert(client)
        response = client.put(f"/api/alerts/{alert_id}/action", json={
            "fm_notes": "Updated notes: reduce position size.",
        })
        assert response.status_code == 200

    def test_should_update_trade_parameters(self, client):
        alert_id = self._create_and_approve_alert(client)
        response = client.put(f"/api/alerts/{alert_id}/action", json={
            "stop_loss": 90.0,
            "target_price": 150.0,
        })
        assert response.status_code == 200

    def test_should_return_404_for_nonexistent_alert(self, client):
        response = client.put("/api/alerts/99999/action", json={
            "fm_notes": "test",
        })
        assert response.status_code == 404

    def test_should_return_404_when_no_action_exists(self, client):
        resp = client.post("/webhook/tradingview", json={"ticker": "NOACTION"})
        alert_id = resp.json()["alert_id"]
        # No action created yet
        response = client.put(f"/api/alerts/{alert_id}/action", json={
            "fm_notes": "test",
        })
        assert response.status_code == 404
        assert "No action found" in response.json()["detail"]


# ── Delete Alerts ───────────────────────────────────────────


class TestDeleteAlert:
    """DELETE /api/alerts/{alert_id}"""

    def test_should_delete_alert(self, client):
        resp = client.post("/webhook/tradingview", json={"ticker": "DELETEME"})
        alert_id = resp.json()["alert_id"]
        response = client.delete(f"/api/alerts/{alert_id}")
        assert response.status_code == 200
        assert response.json()["success"] is True
        # Verify deleted
        get_resp = client.get(f"/api/alerts/{alert_id}")
        assert get_resp.status_code == 404

    def test_should_delete_alert_with_action(self, client):
        resp = client.post("/webhook/tradingview", json={"ticker": "DELETEWITHACTION"})
        alert_id = resp.json()["alert_id"]
        # Create action
        client.post(f"/api/alerts/{alert_id}/action", json={
            "alert_id": alert_id, "decision": "APPROVED",
        })
        # Delete should clean up both alert and action
        response = client.delete(f"/api/alerts/{alert_id}")
        assert response.status_code == 200

    def test_should_return_404_for_nonexistent_alert(self, client):
        response = client.delete("/api/alerts/99999")
        assert response.status_code == 404


class TestDeleteAllAlerts:
    """DELETE /api/alerts/all"""

    def test_should_delete_all_alerts(self, client):
        # Create a few alerts
        client.post("/webhook/tradingview", json={"ticker": "BATCH1"})
        client.post("/webhook/tradingview", json={"ticker": "BATCH2"})
        response = client.delete("/api/alerts/all")
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["deleted_count"] >= 2
        # Verify empty
        list_resp = client.get("/api/alerts")
        assert len(list_resp.json()["alerts"]) == 0


# ── Chart Retrieval ─────────────────────────────────────────


class TestGetChart:
    """GET /api/alerts/{alert_id}/chart"""

    def test_should_return_404_when_no_chart(self, client):
        resp = client.post("/webhook/tradingview", json={"ticker": "NOCHART"})
        alert_id = resp.json()["alert_id"]
        response = client.get(f"/api/alerts/{alert_id}/chart")
        assert response.status_code == 404

    def test_should_return_chart_when_present(self, client):
        resp = client.post("/webhook/tradingview", json={"ticker": "CHARTTEST"})
        alert_id = resp.json()["alert_id"]
        # Create action with chart
        client.post(f"/api/alerts/{alert_id}/action", json={
            "alert_id": alert_id,
            "decision": "APPROVED",
            "chart_image_b64": "iVBORw0KGgoAAAANSUhEUg==",
        })
        response = client.get(f"/api/alerts/{alert_id}/chart")
        assert response.status_code == 200
        assert response.json()["chart_image_b64"] == "iVBORw0KGgoAAAANSUhEUg=="
