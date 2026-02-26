"""
FIE — AI Engine
Generates institutional-grade technical analysis commentary using Gemini.
Style: CMT-level analyst briefing fund managers at a wealth management firm.
"""

import google.generativeai as genai
import os
import logging

logger = logging.getLogger(__name__)

api_key = os.getenv("GEMINI_API_KEY")
model = None

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")


def generate_technical_summary(ticker: str, price, indicators: dict, alert_message: str = "") -> str:
    """
    Generates 3-4 line institutional-grade technical commentary.
    Opens with directional bias + confluence, cites specific indicator values,
    uses Dow Theory language, ends with a key level or actionable insight.
    """
    if not model:
        return _rule_based_summary(ticker, price, indicators, alert_message)

    lines = []

    # Confluence
    bull = indicators.get("confluence_bull_score") or indicators.get("confluence_bull")
    bear = indicators.get("confluence_bear_score") or indicators.get("confluence_bear")
    bias = indicators.get("confluence_bias", "")
    if bull is not None and bear is not None:
        lines.append(f"Confluence: {bias} (Bull {bull}/10 vs Bear {bear}/10)")

    # Momentum
    rsi = indicators.get("rsi")
    if rsi is not None:
        v = float(rsi)
        desc = "overbought territory" if v > 70 else "oversold territory" if v < 30 else "neutral zone"
        lines.append(f"RSI-14: {v:.1f} ({desc})")
    stoch_k = indicators.get("stoch_k")
    if stoch_k is not None:
        lines.append(f"Stochastic %K: {float(stoch_k):.1f}")
    mfi = indicators.get("mfi")
    if mfi is not None:
        lines.append(f"MFI: {float(mfi):.1f}")

    # Trend
    macd_hist = indicators.get("macd_hist")
    macd_line = indicators.get("macd_line")
    macd_sig  = indicators.get("macd_signal")
    if macd_hist is not None:
        v = float(macd_hist)
        lines.append(f"MACD histogram: {v:.4f} ({'positive' if v > 0 else 'negative'})")
    if macd_line is not None and macd_sig is not None:
        lines.append(f"MACD Line: {float(macd_line):.4f}, Signal: {float(macd_sig):.4f}")

    st_dir = indicators.get("supertrend_dir")
    if st_dir:
        lines.append(f"SuperTrend: {st_dir}")

    adx = indicators.get("adx")
    di_plus  = indicators.get("di_plus")
    di_minus = indicators.get("di_minus")
    if adx is not None:
        v = float(adx)
        s = "strong trend" if v > 25 else "weak/consolidating"
        line = f"ADX: {v:.1f} ({s})"
        if di_plus and di_minus:
            line += f", +DI: {float(di_plus):.1f}, -DI: {float(di_minus):.1f}"
        lines.append(line)

    # Moving averages
    ma_align = indicators.get("ma_alignment")
    if ma_align:
        lines.append(f"MA Alignment: {ma_align}")

    ema_200 = indicators.get("ema_200")
    vwap    = indicators.get("vwap")
    if price and ema_200:
        rel = "above" if float(price) > float(ema_200) else "below"
        lines.append(f"Price {rel} EMA-200 ({float(ema_200):.1f})")
    if vwap and price:
        rel = "above" if float(price) > float(vwap) else "below"
        lines.append(f"Price {rel} VWAP ({float(vwap):.1f})")

    ema_refs = []
    for label, key in [("EMA-9", "ema_9"), ("EMA-20", "ema_20"), ("EMA-50", "ema_50")]:
        v = indicators.get(key)
        if v is not None:
            ema_refs.append(f"{label}: {float(v):.1f}")
    if ema_refs:
        lines.append("Key MAs: " + ", ".join(ema_refs))

    # Volatility
    bb_pctb = indicators.get("bb_pctb")
    atr_pct = indicators.get("atr_pct")
    if bb_pctb is not None:
        v = float(bb_pctb)
        pos = "upper band" if v > 0.8 else "lower band" if v < 0.2 else "mid-band"
        lines.append(f"BB %B: {v:.2f} (near {pos})")
    if atr_pct is not None:
        lines.append(f"ATR%: {float(atr_pct):.2f}%")

    # Volume
    vol_ratio = indicators.get("vol_ratio")
    if vol_ratio is not None:
        v = float(vol_ratio)
        desc = "volume surge" if v > 2 else "elevated volume" if v > 1.3 else "average volume"
        lines.append(f"Volume Ratio: {v:.1f}x ({desc})")
    if indicators.get("vol_spike"):
        lines.append("Volume Spike detected")

    # HTF
    htf_trend = indicators.get("htf_trend")
    htf_rsi   = indicators.get("htf_rsi")
    if htf_trend:
        htf_line = f"HTF Daily Trend: {htf_trend}"
        if htf_rsi:
            htf_line += f" (RSI: {float(htf_rsi):.1f})"
        lines.append(htf_line)

    # Levels
    pivot_pp = indicators.get("pivot_pp")
    high_20  = indicators.get("high_20")
    low_20   = indicators.get("low_20")
    if pivot_pp:
        lines.append(f"Pivot Point: {float(pivot_pp):.1f}")
    if high_20:
        lines.append(f"20-period High: {float(high_20):.1f}")
    if low_20:
        lines.append(f"20-period Low: {float(low_20):.1f}")

    candle = indicators.get("candle_pattern")
    if candle and candle.upper() not in ("NONE", ""):
        lines.append(f"Candle Pattern: {candle}")

    indicator_context = "\n".join(lines) if lines else "Limited indicator data available."

    interval = indicators.get("interval", "")
    tf_map = {"1":"1-minute","3":"3-minute","5":"5-minute","15":"15-minute",
              "30":"30-minute","60":"1-hour","D":"daily","W":"weekly"}
    tf_desc = tf_map.get(str(interval), f"{interval}-period") if interval else "intraday"

    prompt = f"""You are a CMT-certified technical analyst at Jhaveri Securities, a leading Indian wealth management firm managing Rs 3,500 crores AUM. You are briefing a senior fund manager about an alert that just fired.

ALERT: {ticker} at price Rs {price} on {tf_desc} timeframe

TECHNICAL DATA:
{indicator_context}

ALERT CONTEXT: {alert_message or 'System-generated alert'}

Write EXACTLY 3-4 sentences of institutional technical analysis commentary:
1. FIRST sentence: State directional bias and confluence score (e.g., "NIFTY displays a bearish technical structure with 5/10 bear confluence on the 15-minute chart.")
2. SECOND sentence: Reference 2-3 specific indicator VALUES — RSI number, MACD histogram direction, SuperTrend status, or ADX reading.
3. THIRD sentence: Use a Dow Theory or technical framework concept — MA stack alignment, trend confirmation, distribution/accumulation phase, or HTF trend context.
4. FOURTH sentence (preferred): End with the most important KEY LEVEL — support, resistance, pivot, or EMA — and what a break implies.

STYLE RULES:
- Precise and confident — no hedging language
- Use specific numbers from the data
- Max 4 sentences, no bullet points, no headers
- Do not start with "I" or "The alert"
- Write like a senior analyst briefing a fund manager, not a retail investor

EXAMPLE:
"NIFTY displays a bearish technical structure with 5/10 bear confluence. RSI-14 at 51 is neutral, but MACD histogram is negative with SuperTrend confirming bearish direction. MA alignment is fully bearish (EMA-9 < EMA-21 < EMA-50), consistent with Dow Theory distribution phase, while the HTF daily trend also remains bearish. Key support at 25,500 (20-period low); a sustained break below could accelerate selling toward the 25,200 pivot zone."

Now write the commentary:"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        return text if text else _rule_based_summary(ticker, price, indicators, alert_message)
    except Exception as e:
        logger.warning(f"Gemini API error for {ticker}: {e}")
        return _rule_based_summary(ticker, price, indicators, alert_message)


def _rule_based_summary(ticker: str, price, indicators: dict, alert_message: str = "") -> str:
    """Fallback rule-based summary when Gemini API is unavailable."""
    parts = []

    bull    = indicators.get("confluence_bull_score") or indicators.get("confluence_bull") or 0
    bear    = indicators.get("confluence_bear_score") or indicators.get("confluence_bear") or 0
    bias    = indicators.get("confluence_bias", "")
    st_dir  = indicators.get("supertrend_dir", "")
    ma_align = indicators.get("ma_alignment", "")
    htf     = indicators.get("htf_trend", "")
    rsi     = indicators.get("rsi")
    macd_hist = indicators.get("macd_hist")
    adx     = indicators.get("adx")

    # Sentence 1
    if bias and bull is not None and bear is not None:
        parts.append(f"{ticker} displays a {bias.lower()} technical setup with {bear}/10 bear and {bull}/10 bull confluence.")
    elif st_dir:
        parts.append(f"{ticker} is in a {st_dir.lower()} technical configuration per SuperTrend.")
    else:
        parts.append(f"{ticker} has triggered a technical alert at Rs {price}.")

    # Sentence 2
    notes = []
    if rsi is not None:
        v = float(rsi)
        notes.append(f"RSI-14 at {v:.1f} is {'overbought' if v>70 else 'oversold' if v<30 else 'neutral'}")
    if macd_hist is not None:
        notes.append(f"MACD histogram is {'positive' if float(macd_hist)>0 else 'negative'}")
    if st_dir:
        notes.append(f"SuperTrend is {st_dir.lower()}")
    if adx is not None:
        v = float(adx)
        notes.append(f"ADX at {v:.1f} {'signals a strong trend' if v>25 else 'suggests weak conditions'}")
    if notes:
        parts.append("; ".join(notes[:3]) + ".")

    # Sentence 3
    if ma_align:
        align_desc = "fully aligned" if ma_align in ("BULL", "BEAR") else "mixed"
        s = f"MA stack is {align_desc} ({ma_align})"
        if htf:
            s += f", consistent with the HTF daily trend ({htf})"
        parts.append(s + ".")

    # Sentence 4
    low_20  = indicators.get("low_20")
    high_20 = indicators.get("high_20")
    pivot   = indicators.get("pivot_pp")
    if low_20 and st_dir == "BEARISH":
        parts.append(f"Watch the 20-period low at {float(low_20):.1f}; a break below would confirm continuation.")
    elif high_20 and st_dir == "BULLISH":
        parts.append(f"Breakout above the 20-period high at {float(high_20):.1f} would confirm bullish momentum.")
    elif pivot:
        parts.append(f"Pivot point at {float(pivot):.1f} is the key level for directional confirmation.")

    return " ".join(parts) if parts else (alert_message or f"Technical alert for {ticker} at Rs {price}.")


def synthesize_fm_rationale(ticker: str, call: str, text_note: str = None, audio_b64=None) -> str:
    """Formalizes FM's voice/text note into institutional language."""
    if not model:
        return text_note or "Rationale captured."

    prompt = f"""You are a quantitative analyst at Jhaveri Securities formalizing a Fund Manager's trade rationale for a {call} call on {ticker}.

Review the manager's note and synthesize it into a professional 2-3 sentence 'Fund Manager's View'.
Use precise institutional market terminology. Do not invent facts not mentioned by the manager.
Write in third person (e.g., "The Fund Manager believes...").

Manager's Note: {text_note or '(No text provided)'}"""

    contents = [prompt]
    if audio_b64:
        contents.append({"mime_type": "audio/wav", "data": audio_b64})

    try:
        response = model.generate_content(contents)
        return response.text.strip()
    except Exception as e:
        logger.warning(f"FM rationale synthesis error: {e}")
        return text_note or "Rationale captured."
