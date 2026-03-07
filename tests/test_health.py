"""
Smoke tests for health, status, and root API endpoints.

These run in CI on every push and PR to catch import errors,
broken endpoints, and database connectivity issues early.
"""


def test_health_endpoint(client):
    """Health check should return 200 with status ok and DB counts."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "counts" in data
    assert "alerts" in data["counts"]
    assert "portfolios" in data["counts"]


def test_api_root(client):
    """Root API endpoint should identify the service."""
    response = client.get("/api")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "JHAVERI FIE v3"
    assert data["status"] == "running"


def test_status_endpoint(client):
    """Status endpoint should return version and analysis flag."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "analysis_enabled" in data
