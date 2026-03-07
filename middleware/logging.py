"""
FIE v3 — Structured Logging Configuration
JSON logging for production, human-readable for development.
"""
import json
import logging
import sys
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """JSON log formatter for production environments."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
            }

        # Add extra fields if present
        for key in ("request_id", "method", "path", "status_code", "duration_ms", "client_ip"):
            if hasattr(record, key):
                log_data[key] = getattr(record, key)

        return json.dumps(log_data)


def setup_logging(environment: str = "production"):
    """Configure logging based on environment."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove existing handlers
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if environment == "dev":
        # Human-readable for development
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-8s %(name)-20s %(message)s",
            datefmt="%H:%M:%S",
        ))
    else:
        # JSON for production (parseable by CloudWatch, Datadog, etc.)
        handler.setFormatter(JSONFormatter())

    root_logger.addHandler(handler)

    # Reduce noise from third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("yfinance").setLevel(logging.WARNING)
