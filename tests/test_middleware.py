"""
Tests for FIE v3 security middleware.

Covers:
- SecurityHeadersMiddleware — defensive HTTP headers on all responses
- RequestSizeLimitMiddleware — reject oversized request bodies (413)
- API key authentication — optional auth gating for /api paths
"""



# ═══════════════════════════════════════════════════════════
#  SECURITY HEADERS
# ═══════════════════════════════════════════════════════════


class TestSecurityHeaders:
    """Tests for security headers added to every response."""

    def test_should_include_x_content_type_options_nosniff(self, client):
        """Every response should have X-Content-Type-Options: nosniff."""
        response = client.get("/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_should_include_x_frame_options_deny(self, client):
        """Every response should have X-Frame-Options: DENY."""
        response = client.get("/health")
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_should_include_x_xss_protection(self, client):
        """Every response should have X-XSS-Protection header."""
        response = client.get("/health")
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"

    def test_should_include_strict_transport_security(self, client):
        """Every response should have HSTS header."""
        response = client.get("/health")
        hsts = response.headers.get("Strict-Transport-Security")
        assert hsts is not None
        assert "max-age=" in hsts

    def test_should_include_referrer_policy(self, client):
        """Every response should have a Referrer-Policy header."""
        response = client.get("/health")
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_should_include_permissions_policy(self, client):
        """Every response should restrict dangerous browser APIs."""
        response = client.get("/health")
        perms = response.headers.get("Permissions-Policy")
        assert perms is not None
        assert "camera=()" in perms
        assert "microphone=()" in perms

    def test_should_include_cache_control_no_store_for_api_paths(self, client):
        """API responses (/api/*) should have Cache-Control: no-store."""
        response = client.get("/api")
        assert response.headers.get("Cache-Control") == "no-store"

    def test_should_include_cache_control_for_api_status(self, client):
        """The /api/status endpoint should also have no-store."""
        response = client.get("/api/status")
        assert response.headers.get("Cache-Control") == "no-store"

    def test_should_not_add_cache_control_for_health(self, client):
        """Non-API paths like /health should NOT have Cache-Control: no-store."""
        response = client.get("/health")
        cache_control = response.headers.get("Cache-Control")
        # /health is not under /api, so no-store should not be added
        assert cache_control != "no-store" or cache_control is None

    def test_security_headers_should_be_present_on_404(self, client):
        """Security headers should be present even on 404 responses."""
        response = client.get("/api/nonexistent-endpoint")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"


# ═══════════════════════════════════════════════════════════
#  REQUEST SIZE LIMIT
# ═══════════════════════════════════════════════════════════


class TestRequestSizeLimit:
    """Tests for the request size limit middleware (10MB default)."""

    def test_should_reject_oversized_request_with_413(self, client):
        """Request with Content-Length > 10MB should be rejected with 413."""
        oversized_length = str(11 * 1024 * 1024)  # 11MB
        response = client.post(
            "/health",
            headers={"Content-Length": oversized_length},
            content=b"x",  # actual body doesn't matter, header is checked first
        )
        assert response.status_code == 413
        data = response.json()
        assert "too large" in data.get("error", "").lower()
        assert data.get("code") == "REQUEST_TOO_LARGE"

    def test_should_allow_request_within_size_limit(self, client):
        """Request with Content-Length under 10MB should pass through."""
        response = client.get("/health")
        # Should succeed (200) since no body or small body
        assert response.status_code == 200

    def test_should_reject_request_just_over_10mb(self, client):
        """Request at exactly 10MB + 1 byte should be rejected."""
        just_over = str(10 * 1024 * 1024 + 1)
        response = client.post(
            "/health",
            headers={"Content-Length": just_over},
            content=b"x",
        )
        assert response.status_code == 413

    def test_should_allow_request_at_exactly_10mb(self, client):
        """Request at exactly 10MB should be allowed (limit is exclusive)."""
        exactly_10mb = str(10 * 1024 * 1024)
        # This should pass the middleware check (length <= max, not length < max)
        # The middleware checks `if length > self.max_size` so exactly 10MB passes
        response = client.post(
            "/health",
            headers={"Content-Length": exactly_10mb},
            content=b"x",
        )
        # Should NOT be 413 (middleware allows <= 10MB)
        assert response.status_code != 413

    def test_should_return_400_for_invalid_content_length(self, client):
        """Non-numeric Content-Length header should be rejected with 400."""
        response = client.post(
            "/health",
            headers={"Content-Length": "not-a-number"},
            content=b"x",
        )
        assert response.status_code == 400
        data = response.json()
        assert data.get("code") == "INVALID_CONTENT_LENGTH"


# ═══════════════════════════════════════════════════════════
#  API KEY AUTHENTICATION
# ═══════════════════════════════════════════════════════════


class TestApiKeyAuth:
    """Tests for the optional API key authentication middleware."""

    def test_should_allow_all_requests_when_no_api_key_set(self, client):
        """When FIE_API_KEY env var is not set, all requests should pass through."""
        # The conftest does not set FIE_API_KEY, so auth is disabled
        response = client.get("/api")
        assert response.status_code == 200

    def test_health_endpoint_should_always_be_public(self, client):
        """The /health endpoint should never require authentication."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_webhook_endpoint_should_always_be_public(self, client):
        """The /webhook/tradingview endpoint should never require authentication."""
        # This will return 422 (missing body) but NOT 401
        response = client.post("/webhook/tradingview")
        assert response.status_code != 401

    def test_api_root_should_be_public(self, client):
        """The /api root should be in the public paths list."""
        response = client.get("/api")
        assert response.status_code == 200

    def test_api_status_should_be_public(self, client):
        """The /api/status should be in the public paths list."""
        response = client.get("/api/status")
        assert response.status_code == 200
