"""
FIE v3 — Telegram Alert Distribution
Sends approved alert cards (chart + analysis) to a configured Telegram channel.
"""

import base64
import json
import logging
import os
from datetime import datetime

import httpx

logger = logging.getLogger("fie_v3.telegram")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)

_BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


# ─── Formatting Helpers ──────────────────────────────────────────

def _escape_md(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special = r"_*[]()~`>#+-=|{}.!"
    result = []
    for ch in text:
        if ch in special:
            result.append("\\")
        result.append(ch)
    return "".join(result)


def _format_header(alert: dict, action: dict) -> str:
    """Signal emoji + action + ticker info."""
    signal = (alert.get("signal_direction") or "NEUTRAL").upper()
    emoji = {"BULLISH": "\U0001f7e2", "BEARISH": "\U0001f534"}.get(signal, "\U0001f7e1")
    action_call = action.get("action_call") or "HOLD"
    ticker = alert.get("ticker") or "—"
    exchange = alert.get("exchange") or ""
    interval = alert.get("interval") or ""
    price = alert.get("price_at_alert") or alert.get("price_close")
    price_str = f"\u20b9{price:,.2f}" if price else "—"

    parts = [f"{emoji} {action_call}"]
    parts.append(f"\n{ticker} | {exchange} | {interval}")
    parts.append(f"Signal: {signal} | {price_str}")
    return "\n".join(parts)


def _format_trade_params(action: dict) -> str:
    """Entry range, SL, TP, risk/reward."""
    lines = []
    entry_low = action.get("entry_price_low")
    entry_high = action.get("entry_price_high")
    if entry_low is not None and entry_high is not None:
        lines.append(f"Entry: \u20b9{entry_low:,.2f} \u2013 \u20b9{entry_high:,.2f}")
    elif entry_low is not None:
        lines.append(f"Entry: \u20b9{entry_low:,.2f}")
    elif entry_high is not None:
        lines.append(f"Entry: \u20b9{entry_high:,.2f}")

    sl = action.get("stop_loss")
    tp = action.get("target_price")
    if sl is not None or tp is not None:
        sl_str = f"\u20b9{sl:,.2f}" if sl else "—"
        tp_str = f"\u20b9{tp:,.2f}" if tp else "—"
        lines.append(f"Stop Loss: {sl_str} | Target: {tp_str}")

    return "\n".join(lines)


def _format_analysis(analysis_items: list) -> str:
    """Numbered list of Claude analysis insights."""
    if not analysis_items:
        return ""
    lines = [f"{i+1}. {item}" for i, item in enumerate(analysis_items)]
    return "\n".join(lines)


def _format_caption(alert: dict, action: dict) -> str:
    """Short caption for photo (Telegram limit: 1024 chars). Plain text, no markdown."""
    header = _format_header(alert, action)
    trade = _format_trade_params(action)
    parts = [header]
    if trade:
        parts.append(f"\n{trade}")
    caption = "\n".join(parts)
    return caption[:1024]


def _format_full_message(alert: dict, action: dict) -> str:
    """Full follow-up text: FM notes + analysis + timestamp."""
    parts = []

    fm_notes = action.get("fm_notes")
    if fm_notes:
        parts.append(f"\U0001f4dd FM Notes\n{fm_notes}")

    analysis_raw = action.get("chart_analysis")
    if analysis_raw:
        items = json.loads(analysis_raw) if isinstance(analysis_raw, str) else analysis_raw
        if isinstance(items, list) and items:
            parts.append(f"\U0001f916 Analysis\n{_format_analysis(items)}")

    decision_at = action.get("decision_at")
    if decision_at:
        try:
            dt = datetime.fromisoformat(decision_at.replace("Z", "+00:00"))
            formatted = dt.strftime("%d %b %Y, %I:%M %p IST")
            parts.append(f"\u23f0 {formatted}")
        except (ValueError, AttributeError):
            pass

    return "\n\n".join(parts) if parts else ""


# ─── Telegram API Calls ──────────────────────────────────────────

async def _send_photo(image_b64: str, caption: str) -> bool:
    """Send chart image as photo to Telegram."""
    try:
        image_bytes = base64.b64decode(image_b64)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{_BASE_URL}/sendPhoto",
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
                files={"photo": ("chart.png", image_bytes, "image/png")},
            )
            if resp.status_code != 200:
                logger.error("Telegram sendPhoto failed: %s %s", resp.status_code, resp.text[:200])
                return False
            return True
    except Exception as exc:
        logger.error("Telegram sendPhoto error: %s", exc)
        return False


async def _send_message(text: str) -> bool:
    """Send text message to Telegram."""
    if not text.strip():
        return True
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{_BASE_URL}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": text},
            )
            if resp.status_code != 200:
                logger.error("Telegram sendMessage failed: %s %s", resp.status_code, resp.text[:200])
                return False
            return True
    except Exception as exc:
        logger.error("Telegram sendMessage error: %s", exc)
        return False


# ─── Public API ───────────────────────────────────────────────────

async def send_alert_card(alert: dict, action: dict) -> bool:
    """
    Format and send a full alert card to Telegram.
    Sends chart as photo with caption, then follow-up text with analysis.
    Returns True if at least one message was sent.
    """
    if not TELEGRAM_ENABLED:
        return False

    sent_any = False
    chart_b64 = action.get("chart_image_b64")

    if chart_b64:
        caption = _format_caption(alert, action)
        sent_any = await _send_photo(chart_b64, caption)
    else:
        # No chart — send header + trade params as text
        header = _format_header(alert, action)
        trade = _format_trade_params(action)
        text = f"{header}\n\n{trade}" if trade else header
        sent_any = await _send_message(text)

    # Follow-up text with FM notes + analysis
    full_text = _format_full_message(alert, action)
    if full_text:
        await _send_message(full_text)

    return sent_any
