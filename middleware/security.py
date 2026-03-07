"""
Security middleware for FIE v3.

SecurityHeadersMiddleware — adds defensive HTTP headers to every response.
RequestSizeLimitMiddleware — rejects request bodies exceeding a configurable max size.
RequestLoggingMiddleware — logs all API requests with timing information.
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

logger = logging.getLogger("fie_v3.security")

# ─── Default security headers ────────────────────────────
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds standard security headers to every HTTP response.

    For API paths (starting with /api), also sets Cache-Control: no-store
    to prevent caching of sensitive financial data.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Apply all security headers
        for header_name, header_value in _SECURITY_HEADERS.items():
            response.headers[header_name] = header_value

        # Prevent caching of API responses — financial data should never be stale-cached
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Rejects incoming requests whose body exceeds a configurable size limit.

    Uses the Content-Length header for a fast pre-check. If Content-Length
    is not present (e.g. chunked transfer), the request is allowed through
    since the body hasn't been read yet.

    Args:
        app: The ASGI application.
        max_size: Maximum allowed body size in bytes. Defaults to 10MB.
    """

    def __init__(self, app: ASGIApp, max_size: int = 10 * 1024 * 1024) -> None:
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next) -> Response:
        # Fast path: check Content-Length header before reading any body bytes
        content_length = request.headers.get("content-length")

        if content_length is not None:
            try:
                length = int(content_length)
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Invalid Content-Length header",
                        "code": "INVALID_CONTENT_LENGTH",
                    },
                )

            if length > self.max_size:
                max_mb = self.max_size / (1024 * 1024)
                logger.warning(
                    "Request rejected: body size %d bytes exceeds %dMB limit (path=%s, client=%s)",
                    length,
                    int(max_mb),
                    request.url.path,
                    request.client.host if request.client else "unknown",
                )
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": f"Request body too large. Maximum size is {int(max_mb)}MB.",
                        "code": "REQUEST_TOO_LARGE",
                    },
                )

        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all API requests with timing information."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        # Only log API requests (not static files)
        if request.url.path.startswith("/api") or request.url.path in ("/health", "/webhook/tradingview"):
            access_logger = logging.getLogger("fie_v3.access")
            access_logger.info(
                "%s %s %d %.1fms",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "client_ip": request.client.host if request.client else "unknown",
                },
            )

        return response
