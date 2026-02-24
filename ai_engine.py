import google.generativeai as genai
import os

api_key = os.getenv("GEMINI_API_KEY")
model = None

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

def generate_technical_summary(ticker, price, indicators, alert_message):
    """Translates raw webhook data into a professional technical description."""
    if not model:
        return alert_message or "System Alert"
        
    prompt = f"""
    Act as a CMT-certified technical analyst. An alert just fired for {ticker} at {price}.
    Raw Message: {alert_message}
    Indicators: {indicators}
    
    Write a concise, 2-sentence technical summary of what this setup represents (e.g., shape forming, higher-high, moving average bounce, momentum shift). Do not provide trading advice, just analyze the structure.
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return alert_message or "System Alert"

def synthesize_fm_rationale(ticker, call, text_note=None, audio_b64=None):
    """Listens to the FM's voice or reads text, and writes a professional view."""
    if not model:
        return text_note or "Rationale captured."
        
    prompt = f"""
    You are a quantitative analyst formalizing a Fund Manager's trade rationale for a {call} call on {ticker}.
    Review the attached voice note and/or text note provided by the manager.
    Synthesize their thoughts into a highly professional, 2-3 sentence 'Fund Manager's View'.
    Use precise institutional market terminology. Do not invent data that the manager did not mention.
    """
    
    contents = [prompt]
    
    if audio_b64:
        contents.append({
            "mime_type": "audio/wav", 
            "data": audio_b64
        })
    if text_note:
        contents.append(f"Manager's Raw Text: {text_note}")
        
    try:
        response = model.generate_content(contents)
        return response.text.strip()
    except Exception as e:
        return text_note or "Rationale captured."
