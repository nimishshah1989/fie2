"""
FIE v3 — Claude AI Analysis Service
Chart vision analysis and text-only analysis via Anthropic API.
"""

import httpx
import logging
import os

logger = logging.getLogger("fie_v3.claude")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


def _parse_bullets(raw_text: str) -> list:
    """Parse Claude's response into exactly 8 bullet points."""
    bullets = []
    for line in raw_text.strip().split("\n"):
        clean = line.strip().lstrip("•").lstrip("0123456789").lstrip(".").lstrip(")").strip()
        if clean:
            bullets.append(clean)
    result = bullets[:8]
    while len(result) < 8:
        result.append("—")
    return result


async def analyze_chart_vision(image_b64: str, alert) -> list:
    """Analyze a TradingView chart image using Claude Vision."""
    media_type = "image/png"
    raw_b64 = image_b64
    if image_b64.startswith("data:"):
        header, raw_b64 = image_b64.split(",", 1)
        if "jpeg" in header or "jpg" in header:
            media_type = "image/jpeg"
        elif "webp" in header:
            media_type = "image/webp"

    ticker   = str(alert.ticker   or "this instrument")
    interval = str(alert.interval or "unknown")
    price    = str(alert.price_at_alert or alert.price_close or "N/A")
    sig      = str(alert.signal_direction or "")
    name     = str(alert.alert_name or ticker)

    prompt = "\n".join([
        "You are a senior technical analyst at an Indian wealth management firm.",
        "Fund manager uploaded a TradingView chart for: " + name + " (" + ticker + "),",
        "interval: " + interval + ", alert price: " + price + ", signal: " + sig + ".",
        "",
        "Provide exactly 8 concise institutional bullet points covering:",
        "1. Overall trend structure",
        "2. Key support and resistance levels",
        "3. Momentum (RSI/MACD if visible)",
        "4. Volume analysis",
        "5. Candlestick pattern at trigger candle",
        "6. Moving average alignment",
        "7. Confluence/confirmation factors",
        "8. Risk/reward and actionable insight for fund manager",
        "",
        "Rules: Each bullet under 20 words. No preamble. Return ONLY 8 lines each starting with •",
    ])

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-5",
                    "max_tokens": 600,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": raw_b64,
                            }},
                            {"type": "text", "text": prompt}
                        ]
                    }]
                }
            )
        if resp.status_code != 200:
            logger.error("Claude API %d: %s", resp.status_code, resp.text[:200])
            return ["Claude API error " + str(resp.status_code) + " — check key/credits."]
        return _parse_bullets(resp.json()["content"][0]["text"])
    except httpx.TimeoutException:
        return ["Chart analysis timed out — re-approve to retry."]
    except Exception as e:
        logger.error("Vision analysis failed: %s", e, exc_info=True)
        return ["Chart analysis error: " + str(e)[:80]]


async def analyze_text_only(alert) -> list:
    """Analyze a TradingView alert using text-only Claude."""
    ticker   = str(alert.ticker   or "Unknown")
    interval = str(alert.interval or "unknown")
    price    = str(alert.price_at_alert or alert.price_close or "N/A")
    sig      = str(alert.signal_direction or "not specified")
    o        = str(alert.price_open)
    h        = str(alert.price_high)
    l        = str(alert.price_low)
    c        = str(alert.price_close)
    v        = str(alert.volume)
    msg      = str(alert.alert_data or "(no alert message)")

    prompt = "\n".join([
        "You are a senior technical analyst at an Indian wealth management firm.",
        "Analyse this TradingView alert and provide 8 concise institutional insights.",
        "",
        "Instrument: " + ticker + "  |  Interval: " + interval + "  |  Signal: " + sig,
        "Alert price: " + price + "  |  O: " + o + "  H: " + h + "  L: " + l + "  C: " + c + "  Vol: " + v,
        "Alert message: " + msg,
        "",
        "Cover: trend context, key levels from OHLCV, momentum, signal validity,",
        "risk considerations, position sizing thought, actionable insight for FM.",
        "",
        "Rules: Each bullet under 20 words. No preamble. Return ONLY 8 lines each starting with •",
    ])

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-5",
                    "max_tokens": 500,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
        if resp.status_code != 200:
            return ["Claude API error " + str(resp.status_code)]
        return _parse_bullets(resp.json()["content"][0]["text"])
    except Exception as e:
        logger.error("Text analysis failed: %s", e)
        return ["Analysis error: " + str(e)[:80]]
