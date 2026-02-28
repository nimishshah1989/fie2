#!/usr/bin/env python3
"""
Smoke Test Script — Jhaveri Intelligence Platform
==================================================
Tests all existing API endpoints to verify they return expected status codes.
Run BEFORE and AFTER any integration to catch breakage.

Usage:
    python3 test_smoke.py                          # Test localhost:8000
    python3 test_smoke.py https://your-app.railway.app   # Test production
"""

import sys
import json
import subprocess
from typing import Optional


BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"


def curl_request(
    method: str, path: str, body: Optional[dict] = None, expected_status: int = 200
) -> dict:
    """Make HTTP request via curl and return result dict."""
    url = f"{BASE_URL}{path}"
    cmd = ["curl", "-s", "-w", "\n%{http_code}", "-X", method, url]
    if body:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(body)]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        lines = result.stdout.strip().rsplit("\n", 1)
        status_code = int(lines[-1]) if len(lines) > 1 else 0
        response_body = lines[0] if len(lines) > 1 else result.stdout
        return {
            "url": url,
            "method": method,
            "status": status_code,
            "expected": expected_status,
            "passed": status_code == expected_status,
            "body_preview": response_body[:200],
        }
    except Exception as exc:
        return {
            "url": url,
            "method": method,
            "status": 0,
            "expected": expected_status,
            "passed": False,
            "body_preview": f"ERROR: {exc}",
        }


# ─── Test Definitions ─────────────────────────────────
# Each test: (method, path, body_or_None, expected_status, description)

TESTS = [
    # ── Health & Status ──
    ("GET", "/health", None, 200, "Health check"),
    ("GET", "/api", None, 200, "API root"),
    ("GET", "/api/status", None, 200, "Server status"),

    # ── Alerts CRUD ──
    ("GET", "/api/alerts", None, 200, "List alerts"),

    # ── Webhook ──
    (
        "POST",
        "/webhook/tradingview",
        {
            "ticker": "SMOKETEST",
            "timeframe": "1D",
            "signal": "BUY",
            "indicator": "Smoke Test",
            "price": 100.0,
            "exchange": "NSE",
        },
        200,
        "Webhook — create test alert",
    ),

    # ── Performance ──
    ("GET", "/api/performance", None, 200, "Alert performance"),

    # ── Actionables ──
    ("GET", "/api/actionables", None, 200, "Actionables list"),

    # ── Market Data ──
    ("GET", "/api/indices/latest", None, 200, "Latest index data"),
    ("GET", "/api/indices/live?base=NIFTY", None, 200, "Live index data"),
    ("GET", "/api/market/indices", None, 200, "Market indices"),
]


def run_tests():
    print(f"\n{'='*60}")
    print(f"  SMOKE TEST — {BASE_URL}")
    print(f"{'='*60}\n")

    results = []
    passed = 0
    failed = 0

    for method, path, body, expected, desc in TESTS:
        r = curl_request(method, path, body, expected)
        results.append((desc, r))
        status_icon = "PASS" if r["passed"] else "FAIL"
        status_color = "\033[92m" if r["passed"] else "\033[91m"
        reset = "\033[0m"

        print(
            f"  {status_color}{status_icon}{reset}  "
            f"{method:5s} {path:40s} "
            f"→ {r['status']} (expected {expected})  "
            f"{desc}"
        )

        if r["passed"]:
            passed += 1
        else:
            failed += 1
            print(f"         Response: {r['body_preview']}")

    # ── Summary ──
    print(f"\n{'─'*60}")
    total = passed + failed
    if failed == 0:
        print(f"  \033[92mALL {total} TESTS PASSED\033[0m")
    else:
        print(f"  \033[91m{failed}/{total} TESTS FAILED\033[0m")
    print(f"{'─'*60}\n")

    # ── Cleanup: delete the smoke test alert ──
    try:
        resp = subprocess.run(
            ["curl", "-s", f"{BASE_URL}/api/alerts"],
            capture_output=True, text=True, timeout=10,
        )
        alerts_data = json.loads(resp.stdout)
        if isinstance(alerts_data, dict):
            alerts = alerts_data.get("alerts", [])
        else:
            alerts = alerts_data
        for alert in alerts:
            if isinstance(alert, dict) and alert.get("ticker") == "SMOKETEST":
                alert_id = alert.get("id")
                if alert_id:
                    subprocess.run(
                        ["curl", "-s", "-X", "DELETE", f"{BASE_URL}/api/alerts/{alert_id}"],
                        capture_output=True, text=True, timeout=10,
                    )
                    print(f"  Cleaned up smoke test alert (id={alert_id})")
    except Exception:
        pass

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
