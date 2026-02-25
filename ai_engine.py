import google.generativeai as genai
import os

api_key = os.getenv("GEMINI_API_KEY")
model = None

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

def generate_technical_summary(ticker, price, indicators, alert_message):
    """
    Translates raw indicator data into a professional technical description.
    With FIE Pine payloads, indicators now contains RSI, MACD, SuperTrend,
    ADX, Bollinger Bands, confluence scores, HTF trend, and more.
    """
    if not model:
        return alert_message or "System Alert"
    
    # Build a rich context from the indicator data
    context_parts = []
    
    # Momentum
    if indicators.get("rsi") is not None:
        rsi = float(indicators["rsi"])
        context_parts.append(f"RSI(14): {rsi:.1f}")
    if indicators.get("stoch_k") is not None:
        context_parts.append(f"Stochastic K: {indicators['stoch_k']}")
    if indicators.get("mfi") is not None:
        context_parts.append(f"MFI: {indicators['mfi']}")
    if indicators.get("cci") is not None:
        context_parts.append(f"CCI: {indicators['cci']}")
    
    # Trend
    if indicators.get("macd_hist") is not None:
        context_parts.append(f"MACD Histogram: {indicators['macd_hist']}")
    if indicators.get("supertrend_dir"):
        context_parts.append(f"SuperTrend: {indicators['supertrend_dir']}")
    if indicators.get("adx") is not None:
        adx = float(indicators["adx"])
        trend_str = "strong trend" if adx > 25 else "weak/no trend"
        context_parts.append(f"ADX: {adx:.1f} ({trend_str})")
    
    # Moving Average alignment
    if indicators.get("ma_alignment"):
        context_parts.append(f"MA Stack: {indicators['ma_alignment']}")
    if indicators.get("dist_vwap_pct") is not None:
        context_parts.append(f"Distance from VWAP: {indicators['dist_vwap_pct']}%")
    
    # Volatility
    if indicators.get("atr_pct") is not None:
        context_parts.append(f"ATR%: {indicators['atr_pct']}%")
    if indicators.get("bb_pctb") is not None:
        context_parts.append(f"BB %B: {indicators['bb_pctb']}")
    
    # Volume
    if indicators.get("vol_ratio") is not None:
        vr = float(indicators["vol_ratio"])
        vol_desc = "heavy volume" if vr > 2 else "above average" if vr > 1.3 else "normal volume"
        context_parts.append(f"Volume Ratio: {vr:.1f}x ({vol_desc})")
    
    # Candle pattern
    if indicators.get("candle_pattern") and indicators["candle_pattern"] != "NONE":
        context_parts.append(f"Candle Pattern: {indicators['candle_pattern']}")
    
    # Confluence
    if indicators.get("confluence_bias"):
        bs = indicators.get("confluence_bull_score", "?")
        brs = indicators.get("confluence_bear_score", "?")
        context_parts.append(f"Confluence: {indicators['confluence_bias']} (Bull:{bs}/Bear:{brs})")
    
    # Higher timeframe
    if indicators.get("htf_trend"):
        context_parts.append(f"Daily Trend: {indicators['htf_trend']}")
    
    indicator_context = "\n".join(context_parts) if context_parts else "Limited indicator data available."
    
    prompt = f"""Act as a CMT-certified technical analyst at an institutional wealth management firm.
An alert fired for {ticker} at price {price}.

Technical Data:
{indicator_context}

Alert Context: {alert_message}

Write a concise, 2-sentence technical summary of what this setup represents.
Focus on the confluence of signals — momentum, trend, volume confirmation, and multi-timeframe alignment.
Use professional institutional language. Do not provide trading advice, just analyze the structure."""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return alert_message or "System Alert"

def synthesize_fm_rationale(ticker, call, text_note=None, audio_b64=None):
    """Listens to the FM's voice or reads text, and writes a professional view."""
    if not model:
        return text_note or "Rationale captured."
        
    prompt = f"""You are a quantitative analyst formalizing a Fund Manager's trade rationale for a {call} call on {ticker}.
Review the attached voice note and/or text note provided by the manager.
Synthesize their thoughts into a highly professional, 2-3 sentence 'Fund Manager's View'.
Use precise institutional market terminology. Do not invent data that the manager did not mention."""
    
    contents = [prompt]
    if audio_b64:
        contents.append({"mime_type": "audio/wav", "data": audio_b64})
    if text_note:
        contents.append(f"Manager's Raw Text: {text_note}")
        
    try:
        response = model.generate_content(contents)
        return response.text.strip()
    except Exception as e:
        return text_note or "Rationale captured."
