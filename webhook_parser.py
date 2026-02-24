"""
FIE Phase 2 — TradingView Webhook Parser
Extracts maximum information from TradingView webhook payloads.
"""

import json
import re
from datetime import datetime, timezone
from typing import Optional
from models import AlertType, SignalDirection


TV_PLACEHOLDERS = {
    "ticker": "ticker",
    "exchange": "exchange",
    "open": "price_open",
    "high": "price_high",
    "low": "price_low",
    "close": "price_close",
    "volume": "volume",
    "time": "time_utc",
    "timenow": "timenow_utc",
    "interval": "interval",
}

SECTOR_KEYWORDS = {
    "BANK": "Banking", "NIFTYBANK": "Banking", "BANKNIFTY": "Banking",
    "PSUBANK": "Banking", "PVTBANK": "Banking", "FINNIFTY": "Financial Services",
    "IT": "Information Technology", "NIFTYIT": "Information Technology",
    "PHARMA": "Pharma & Healthcare", "NIFTYPHARMA": "Pharma & Healthcare",
    "FMCG": "FMCG", "NIFTYFMCG": "FMCG",
    "AUTO": "Automobile", "NIFTYAUTO": "Automobile",
    "METAL": "Metal & Mining", "NIFTYMETAL": "Metal & Mining",
    "REALTY": "Real Estate", "NIFTYREALTY": "Real Estate",
    "ENERGY": "Energy", "NIFTYENERGY": "Energy",
    "INFRA": "Infrastructure", "NIFTYINFRA": "Infrastructure",
    "MEDIA": "Media & Entertainment", "NIFTYMEDIA": "Media & Entertainment",
    "MIDCAP": "Broad Market", "SMALLCAP": "Broad Market",
    "NIFTY50": "Broad Market", "NIFTY": "Broad Market", "NIFTY500": "Broad Market",
    "GOLD": "Commodities", "SILVER": "Commodities", "CRUDE": "Commodities",
    "USDINR": "Currency",
}

ASSET_CLASS_KEYWORDS = {
    "NIFTY": "INDEX", "BANK": "INDEX", "SENSEX": "INDEX",
    "GOLD": "COMMODITY", "SILVER": "COMMODITY", "CRUDE": "COMMODITY",
    "USDINR": "CURRENCY", "EURINR": "CURRENCY", "GBPINR": "CURRENCY",
}

BULLISH_WORDS = [
    "bullish", "buy", "long", "uptrend", "breakout", "golden cross",
    "above", "crossed above", "support", "higher high", "accumulate",
    "oversold bounce", "reversal up", "bottom", "recovery"
]
BEARISH_WORDS = [
    "bearish", "sell", "short", "downtrend", "breakdown", "death cross",
    "below", "crossed below", "resistance", "lower low", "distribute",
    "overbought", "reversal down", "top", "correction"
]


def parse_webhook_payload(raw_data: dict | str) -> dict:
    result = {
        "raw_payload": None,
        "ticker": None, "exchange": None, "interval": None,
        "price_open": None, "price_high": None, "price_low": None,
        "price_close": None, "price_at_alert": None, "volume": None,
        "time_utc": None, "timenow_utc": None,
        "alert_name": None, "alert_message": None, "alert_condition": None,
        "indicator_values": {},
        "alert_type": AlertType.ABSOLUTE,
        "numerator_ticker": None, "denominator_ticker": None,
        "numerator_price": None, "denominator_price": None,
        "ratio_value": None,
        "signal_direction": None, "signal_strength": None, "signal_summary": None,
        "sector": None, "asset_class": None,
    }
    
    if isinstance(raw_data, str):
        try:
            parsed = json.loads(raw_data)
            raw_data = parsed
        except json.JSONDecodeError:
            raw_data = {"message": raw_data}
    
    result["raw_payload"] = raw_data
    
    _extract_standard_fields(raw_data, result)
    _extract_indicators(raw_data, result)
    _detect_relative_alert(raw_data, result)
    _classify_instrument(result)
    _interpret_signal(raw_data, result)
    _generate_summary(result)
    
    return result


def _extract_standard_fields(data: dict, result: dict):
    field_map = {
        "ticker": "ticker", "symbol": "ticker",
        "exchange": "exchange",
        "interval": "interval", "timeframe": "interval",
        "open": "price_open", "high": "price_high",
        "low": "price_low", "close": "price_close",
        "price": "price_at_alert", "last_price": "price_at_alert",
        "volume": "volume",
        "time": "time_utc", "timenow": "timenow_utc",
        "alert_name": "alert_name", "name": "alert_name",
        "alert_message": "alert_message", "message": "alert_message",
        "condition": "alert_condition", "alert_condition": "alert_condition",
    }
    
    for src_key, dest_key in field_map.items():
        if src_key in data and data[src_key] is not None:
            value = data[src_key]
            if dest_key in ("price_open", "price_high", "price_low", "price_close", "price_at_alert", "volume"):
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    pass
            if result[dest_key] is None:
                result[dest_key] = value
    
    if result["price_at_alert"] is None and result["price_close"] is not None:
        result["price_at_alert"] = result["price_close"]


def _extract_indicators(data: dict, result: dict):
    indicator_keys = [
        "rsi", "rsi_14", "rsi_value",
        "macd", "macd_signal", "macd_histogram", "macd_line",
        "ema", "ema_20", "ema_50", "ema_100", "ema_200",
        "sma", "sma_20", "sma_50", "sma_100", "sma_200",
        "bb_upper", "bb_lower", "bb_middle", "bollinger",
        "adx", "adx_value", "atr", "atr_value",
        "obv", "obv_value", "stoch_k", "stoch_d", "stochastic",
        "vwap", "vwap_value", "supertrend", "supertrend_direction",
        "pivot", "pivot_r1", "pivot_r2", "pivot_s1", "pivot_s2",
        "volume_sma", "volume_ratio",
        "dma_50", "dma_200", "dma_position",
        "score", "composite_score", "signal_score",
        "ratio", "spread", "relative_strength",
        "custom_1", "custom_2", "custom_3",
        "indicator_name", "indicator_value",
    ]
    
    indicators = {}
    
    for key in indicator_keys:
        if key in data:
            try:
                indicators[key] = float(data[key]) if _is_numeric(data[key]) else data[key]
            except (ValueError, TypeError):
                indicators[key] = data[key]
    
    if "indicators" in data and isinstance(data["indicators"], dict):
        indicators.update(data["indicators"])
    
    if "data" in data and isinstance(data["data"], dict):
        for k, v in data["data"].items():
            if k not in ("ticker", "exchange", "interval"):
                indicators[k] = v
    
    if result.get("alert_message"):
        msg_indicators = _parse_indicators_from_text(result["alert_message"])
        indicators.update(msg_indicators)
    
    result["indicator_values"] = indicators if indicators else None


def _parse_indicators_from_text(text: str) -> dict:
    indicators = {}
    patterns = [
        (r"RSI[:\s]*(\d+\.?\d*)", "rsi"),
        (r"MACD[:\s]*([-]?\d+\.?\d*)", "macd"),
        (r"ADX[:\s]*(\d+\.?\d*)", "adx"),
        (r"ATR[:\s]*(\d+\.?\d*)", "atr"),
        (r"EMA\s*(\d+)[:\s]*(\d+\.?\d*)", None),
        (r"SMA\s*(\d+)[:\s]*(\d+\.?\d*)", None),
        (r"(?:50[\s-]?DMA|DMA[\s-]?50)[:\s]*(\d+\.?\d*)", "dma_50"),
        (r"(?:200[\s-]?DMA|DMA[\s-]?200)[:\s]*(\d+\.?\d*)", "dma_200"),
        (r"Volume[:\s]*(\d+\.?\d*[KMB]?)", "volume_indicator"),
        (r"Score[:\s]*([-]?\d+\.?\d*)", "score"),
        (r"Stoch[:\s]*(\d+\.?\d*)", "stochastic"),
        (r"OBV[:\s]*([-]?\d+\.?\d*)", "obv"),
        (r"VWAP[:\s]*(\d+\.?\d*)", "vwap"),
        (r"Supertrend[:\s]*([-]?\d+\.?\d*)", "supertrend"),
    ]
    for pattern, key in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if key is None:
                period = match.group(1)
                value = match.group(2)
                if "EMA" in pattern:
                    indicators[f"ema_{period}"] = float(value)
                else:
                    indicators[f"sma_{period}"] = float(value)
            else:
                try:
                    indicators[key] = float(match.group(1).replace('K', '000').replace('M', '000000').replace('B', '000000000'))
                except ValueError:
                    indicators[key] = match.group(1)
    return indicators


def _detect_relative_alert(data: dict, result: dict):
    if "numerator" in data or "denominator" in data:
        result["alert_type"] = AlertType.RELATIVE
        result["numerator_ticker"] = data.get("numerator", data.get("numerator_ticker"))
        result["denominator_ticker"] = data.get("denominator", data.get("denominator_ticker"))
        result["numerator_price"] = _safe_float(data.get("numerator_price"))
        result["denominator_price"] = _safe_float(data.get("denominator_price"))
        result["ratio_value"] = _safe_float(data.get("ratio", data.get("ratio_value")))
        return
    
    ticker = result.get("ticker", "") or ""
    if "/" in ticker and ticker.count("/") == 1:
        parts = ticker.split("/")
        result["alert_type"] = AlertType.RELATIVE
        result["numerator_ticker"] = parts[0].strip()
        result["denominator_ticker"] = parts[1].strip()
        return
    
    text_to_check = f"{data.get('alert_name', '')} {data.get('message', '')} {data.get('alert_message', '')}"
    ratio_patterns = [
        r"(\w+)\s*(?:vs\.?|versus|/|÷)\s*(\w+)",
        r"(\w+)\s*relative\s*to\s*(\w+)",
        r"ratio.*?(\w+).*?(\w+)",
    ]
    for pattern in ratio_patterns:
        match = re.search(pattern, text_to_check, re.IGNORECASE)
        if match:
            num = match.group(1).upper()
            den = match.group(2).upper()
            if len(num) >= 2 and len(den) >= 2 and num != den:
                if any(kw in num for kw in SECTOR_KEYWORDS) or any(kw in den for kw in SECTOR_KEYWORDS):
                    result["alert_type"] = AlertType.RELATIVE
                    result["numerator_ticker"] = num
                    result["denominator_ticker"] = den
                    break
    
    if result["alert_type"] == AlertType.ABSOLUTE:
        result["numerator_ticker"] = result.get("ticker")
        result["numerator_price"] = result.get("price_at_alert")


def _classify_instrument(result: dict):
    ticker = (result.get("ticker") or "").upper()
    for keyword, sector in SECTOR_KEYWORDS.items():
        if keyword in ticker:
            result["sector"] = sector
            break
    for keyword, asset_class in ASSET_CLASS_KEYWORDS.items():
        if keyword in ticker:
            result["asset_class"] = asset_class
            break
    if result["asset_class"] is None:
        result["asset_class"] = "EQUITY"


def _interpret_signal(data: dict, result: dict):
    if "signal" in data:
        sig = str(data["signal"]).upper()
        if any(w in sig for w in ["BUY", "BULL", "LONG", "UP"]):
            result["signal_direction"] = SignalDirection.BULLISH
        elif any(w in sig for w in ["SELL", "BEAR", "SHORT", "DOWN"]):
            result["signal_direction"] = SignalDirection.BEARISH
        else:
            result["signal_direction"] = SignalDirection.NEUTRAL
        return
    
    text = " ".join([
        str(data.get("message", "")), str(data.get("alert_message", "")),
        str(data.get("alert_name", "")), str(data.get("condition", "")),
    ]).lower()
    
    bull_score = sum(1 for w in BULLISH_WORDS if w in text)
    bear_score = sum(1 for w in BEARISH_WORDS if w in text)
    
    if bull_score > bear_score:
        result["signal_direction"] = SignalDirection.BULLISH
        result["signal_strength"] = min(100, bull_score * 25)
    elif bear_score > bull_score:
        result["signal_direction"] = SignalDirection.BEARISH
        result["signal_strength"] = min(100, bear_score * 25)
    else:
        result["signal_direction"] = SignalDirection.NEUTRAL
        result["signal_strength"] = 50


def _generate_summary(result: dict):
    parts = []
    ticker = result.get("ticker") or "Unknown"
    direction = result.get("signal_direction")
    alert_type = result.get("alert_type")
    
    if alert_type == AlertType.RELATIVE:
        num = result.get("numerator_ticker", "?")
        den = result.get("denominator_ticker", "?")
        ratio = result.get("ratio_value")
        parts.append(f"Relative Alert: {num} vs {den}")
        if ratio:
            parts.append(f"Current Ratio: {ratio:.4f}")
    else:
        parts.append(f"Alert on {ticker}")
        if result.get("price_at_alert"):
            parts.append(f"Price: ₹{result['price_at_alert']:,.2f}")
    
    if direction:
        parts.append(f"Signal: {direction.value}")
    
    indicators = result.get("indicator_values") or {}
    if "rsi" in indicators:
        rsi = indicators["rsi"]
        rsi_status = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral"
        parts.append(f"RSI: {rsi:.1f} ({rsi_status})")
    if "macd" in indicators:
        parts.append(f"MACD: {indicators['macd']}")
    
    if result.get("alert_condition"):
        parts.append(f"Condition: {result['alert_condition']}")
    elif result.get("alert_message"):
        msg = result["alert_message"][:150]
        parts.append(f"Message: {msg}")
    
    result["signal_summary"] = " | ".join(parts)


def _safe_float(val) -> Optional[float]:
    if val is None: return None
    try: return float(val)
    except (ValueError, TypeError): return None


def _is_numeric(val) -> bool:
    try: float(val); return True
    except (ValueError, TypeError): return False


def get_recommended_alert_template() -> dict:
    return {
        "note": "Paste this into your TradingView Alert Message field.",
        "template": json.dumps({
            "ticker": "{{ticker}}", "exchange": "{{exchange}}", "interval": "{{interval}}",
            "open": "{{open}}", "high": "{{high}}", "low": "{{low}}",
            "close": "{{close}}", "volume": "{{volume}}", "time": "{{time}}",
            "timenow": "{{timenow}}", "alert_name": "YOUR_ALERT_NAME_HERE",
            "signal": "BULLISH_or_BEARISH",
            "indicators": {"rsi": "INDICATOR_VALUE", "macd": "INDICATOR_VALUE", "ema_200": "INDICATOR_VALUE"},
            "message": "YOUR_CUSTOM_MESSAGE"
        }, indent=2),
        "template_relative": json.dumps({
            "ticker": "{{ticker}}", "exchange": "{{exchange}}", "interval": "{{interval}}",
            "close": "{{close}}", "time": "{{timenow}}",
            "alert_name": "YOUR_RATIO_ALERT_NAME",
            "numerator": "NIFTYIT", "denominator": "NIFTY",
            "numerator_price": "NUMERATOR_PRICE", "denominator_price": "DENOMINATOR_PRICE",
            "ratio": "RATIO_VALUE", "signal": "BULLISH_or_BEARISH", "message": "YOUR_CUSTOM_MESSAGE"
        }, indent=2)
    }
