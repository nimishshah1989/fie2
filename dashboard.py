"""
FIE — Financial Intelligence Engine Dashboard v3
Jhaveri Securities · 5-Tab Streamlit Frontend
Fixes: grid card layout, Trade Center approval flow, yfinance-only Market Pulse
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta
import base64
import os
import pytz

API_BASE = os.getenv("FIE_API_URL", "http://localhost:8000")
IST = pytz.timezone("Asia/Kolkata")

st.set_page_config(
    page_title="FIE · Jhaveri Securities",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════
# GLOBAL CSS
# ══════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;500&display=swap');

:root {
  --bg:        #0D0F14;
  --surface:   #161920;
  --surface2:  #1E2230;
  --surface3:  #252A3A;
  --border:    #2A2F42;
  --border2:   #3A4060;
  --text:      #E8ECF4;
  --text2:     #8B92A8;
  --text3:     #555D75;
  --bull:      #00C896;
  --bull-dim:  #003D2E;
  --bear:      #FF4757;
  --bear-dim:  #3D0010;
  --neutral:   #8B92A8;
  --accent:    #4A7AFF;
  --accent-dim:#0D1A40;
  --gold:      #FFB830;
  --gold-dim:  #2D2000;
  --radius:    8px;
  --radius-lg: 12px;
}

*, *::before, *::after {
  font-family: 'Space Grotesk', -apple-system, sans-serif !important;
  box-sizing: border-box;
}

.stApp { background: var(--bg) !important; color: var(--text) !important; }
.main .block-container { padding: 0 20px 40px 20px !important; max-width: 1400px !important; }
#MainMenu, footer, .stDeployButton,
div[data-testid="stToolbar"], div[data-testid="stDecoration"],
div[data-testid="stStatusWidget"] { display: none !important; }
header[data-testid="stHeader"] { height: 0 !important; min-height: 0 !important; }
section[data-testid="stSidebar"] { display: none !important; }
div[data-testid="stMarkdownContainer"] p { color: var(--text) !important; }

/* ── Top header ── */
.top-bar {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 0 20px;
  margin: 0 -20px 20px -20px;
  display: flex; align-items: center; justify-content: space-between;
  height: 52px;
}
.top-brand {
  font-size: 13px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase;
  color: var(--text); display: flex; align-items: center; gap: 10px;
}
.live-dot {
  width: 6px; height: 6px; border-radius: 50%; background: var(--bull);
  animation: blink 2s infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }
.top-stats { display: flex; gap: 24px; }
.top-stat { font-size: 12px; color: var(--text2); }
.top-stat strong { color: var(--text); font-weight: 600; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
  gap: 0 !important; background: var(--surface) !important;
  border-bottom: 1px solid var(--border) !important;
  padding: 0 20px !important;
  margin: 0 -20px 24px -20px !important;
}
.stTabs [data-baseweb="tab"] {
  padding: 12px 18px !important; font-size: 11px !important;
  font-weight: 700 !important; letter-spacing: 0.08em !important;
  text-transform: uppercase !important; color: var(--text3) !important;
  border-radius: 0 !important; background: transparent !important;
  border: none !important; border-bottom: 2px solid transparent !important;
  margin-bottom: -1px !important;
}
.stTabs [aria-selected="true"] { color: var(--accent) !important; border-bottom: 2px solid var(--accent) !important; }
.stTabs [data-baseweb="tab-panel"] { padding: 0 !important; }

/* ── Stat row ── */
.stat-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 20px; }
.stat-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 14px 16px; }
.stat-num { font-family: 'JetBrains Mono', monospace !important; font-size: 24px; font-weight: 600; color: var(--text); line-height: 1; }
.stat-num.bull { color: var(--bull); }
.stat-num.bear { color: var(--bear); }
.stat-lbl { font-size: 10px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text3); margin-top: 4px; }

/* ── Card grid ── */
.card-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }

/* ── Alert card ── */
.alert-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-lg); padding: 14px 16px;
  position: relative; overflow: hidden;
  transition: border-color .15s, transform .1s;
}
.alert-card:hover { border-color: var(--border2); transform: translateY(-1px); }
.alert-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
}
.alert-card.bull::before { background: var(--bull); }
.alert-card.bear::before { background: var(--bear); }
.alert-card.neutral::before { background: var(--neutral); }
.alert-card.approved::before { background: var(--bull); }
.alert-card.denied::before { background: var(--bear); }

.card-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
.card-ticker { font-size: 20px; font-weight: 700; color: var(--text); letter-spacing: -0.01em; line-height: 1; }
.card-sub { font-size: 11px; color: var(--text3); margin-top: 3px; }
.card-price { font-family: 'JetBrains Mono', monospace !important; font-size: 18px; font-weight: 500; color: var(--text); text-align: right; line-height: 1; }
.card-ts { font-family: 'JetBrains Mono', monospace !important; font-size: 10px; color: var(--text3); text-align: right; margin-top: 3px; }

/* ── Pills ── */
.pills { display: flex; flex-wrap: wrap; gap: 5px; margin: 6px 0; }
.pill { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; line-height: 1.6; }
.p-bull { background: var(--bull-dim); color: var(--bull); border: 1px solid #00C89630; }
.p-bear { background: var(--bear-dim); color: var(--bear); border: 1px solid #FF475730; }
.p-neutral { background: var(--surface3); color: var(--neutral); border: 1px solid var(--border); }
.p-pending { background: var(--gold-dim); color: var(--gold); border: 1px solid #FFB83030; }
.p-approved { background: var(--bull-dim); color: var(--bull); border: 1px solid #00C89630; }
.p-denied { background: var(--bear-dim); color: var(--bear); border: 1px solid #FF475730; }
.p-accent { background: var(--accent-dim); color: var(--accent); border: 1px solid #4A7AFF30; }
.p-high { background: var(--bear-dim); color: var(--bear); border: 1px solid #FF475730; }
.p-medium { background: var(--gold-dim); color: var(--gold); border: 1px solid #FFB83030; }
.p-low { background: var(--bull-dim); color: var(--bull); border: 1px solid #00C89630; }

/* ── Chips ── */
.chips { display: flex; flex-wrap: wrap; gap: 4px; margin: 6px 0; }
.chip { font-family: 'JetBrains Mono', monospace !important; font-size: 10px; padding: 2px 7px; border-radius: 3px; background: var(--surface2); border: 1px solid var(--border); color: var(--text2); white-space: nowrap; }
.chip.c-bull { background: var(--bull-dim); border-color: #00C89625; color: var(--bull); }
.chip.c-bear { background: var(--bear-dim); border-color: #FF475725; color: var(--bear); }
.chip.c-warn { background: var(--gold-dim); border-color: #FFB83025; color: var(--gold); }

/* ── Confluence bar ── */
.conf-wrap { margin: 6px 0 4px; }
.conf-lbl { font-size: 9px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text3); margin-bottom: 3px; }
.conf-track { height: 3px; border-radius: 2px; background: var(--surface3); display: flex; overflow: hidden; }
.conf-bull { background: var(--bull); border-radius: 2px 0 0 2px; }
.conf-bear { background: var(--bear); border-radius: 0 2px 2px 0; }

/* ── AI box ── */
.ai-box { background: var(--surface2); border: 1px solid var(--border); border-left: 3px solid var(--accent); border-radius: 6px; padding: 10px 12px; margin-top: 8px; font-size: 12px; line-height: 1.7; color: var(--text2); }
.ai-lbl { font-size: 9px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text3); margin-bottom: 4px; }

/* ── Section header ── */
.sec-hdr { font-size: 10px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text3); padding-bottom: 10px; border-bottom: 1px solid var(--border); margin-bottom: 14px; }

/* ── Detail grid ── */
.det-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; margin: 10px 0; }
.det-cell { background: var(--surface2); border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px; }
.det-lbl { font-size: 9px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text3); margin-bottom: 3px; }
.det-val { font-family: 'JetBrains Mono', monospace !important; font-size: 12px; font-weight: 500; color: var(--text); }

/* ── Action panel ── */
.action-panel { background: var(--surface2); border: 1px solid var(--border); border-radius: var(--radius); padding: 14px; }
.action-hdr { font-size: 10px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text3); margin-bottom: 10px; }

/* ── Streamlit overrides ── */
div[data-testid="stExpander"] { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: var(--radius) !important; }
div[data-testid="stExpanderDetails"] { background: var(--surface) !important; }
.stSelectbox div[data-baseweb="select"] > div { background: var(--surface2) !important; border-color: var(--border) !important; color: var(--text) !important; border-radius: 6px !important; font-size: 13px !important; }
.stTextInput input, .stNumberInput input, .stTextArea textarea { background: var(--surface2) !important; border-color: var(--border) !important; color: var(--text) !important; border-radius: 6px !important; font-size: 13px !important; }
label[data-testid] { color: var(--text2) !important; font-size: 10px !important; font-weight: 700 !important; letter-spacing: 0.06em !important; text-transform: uppercase !important; }
.stButton button { border-radius: 6px !important; font-size: 12px !important; font-weight: 600 !important; letter-spacing: 0.04em !important; border: none !important; }
.stButton button[kind="primary"] { background: var(--accent) !important; color: #fff !important; }
.stButton button[kind="secondary"] { background: var(--surface3) !important; color: var(--text) !important; border: 1px solid var(--border) !important; }
div[data-testid="stFileUploader"] > div { background: var(--surface2) !important; border-color: var(--border) !important; border-radius: 6px !important; }
.stDataFrame { background: var(--surface) !important; }
div[data-testid="stCaption"] { color: var(--text3) !important; font-size: 11px !important; }
hr { border-color: var(--border) !important; margin: 10px 0 !important; }
p, li { color: var(--text) !important; }

/* ── Market Pulse table ── */
.pt { width: 100%; border-collapse: collapse; margin-bottom: 2px; }
.pt-cat { font-size: 10px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text3); padding: 16px 10px 8px; }
.pt th { font-size: 9px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text3); padding: 8px 10px; border-bottom: 1px solid var(--border2); text-align: right; background: var(--surface2); }
.pt th:first-child { text-align: left; }
.pt td { font-family: 'JetBrains Mono', monospace !important; font-size: 12px; padding: 9px 10px; border-bottom: 1px solid var(--border); color: var(--text); text-align: right; }
.pt td:first-child { font-family: 'Space Grotesk', sans-serif !important; font-size: 13px; font-weight: 500; text-align: left; color: var(--text); }
.pt tr:hover td { background: var(--surface2); }
.up { color: var(--bull) !important; font-weight: 600; }
.dn { color: var(--bear) !important; font-weight: 600; }
.flat { color: var(--text3) !important; }

/* ── No data ── */
.no-data { text-align: center; padding: 60px 24px; color: var(--text3); font-size: 13px; }
.no-data-icon { font-size: 28px; margin-bottom: 10px; }

/* ── Selectbox / dropdown fixes — force visible text ── */
.stSelectbox div[data-baseweb="select"] > div,
.stSelectbox div[data-baseweb="select"] > div > div,
.stSelectbox [data-baseweb="select"] span,
.stSelectbox [data-baseweb="select"] div { 
  background: var(--surface2) !important; 
  color: var(--text) !important; 
  border-color: var(--border) !important; 
}
/* Dropdown list items */
[data-baseweb="menu"] { background: var(--surface2) !important; border: 1px solid var(--border2) !important; }
[data-baseweb="menu"] li { background: var(--surface2) !important; color: var(--text) !important; }
[data-baseweb="menu"] li:hover { background: var(--surface3) !important; color: var(--text) !important; }
[data-baseweb="option"] { background: var(--surface2) !important; color: var(--text) !important; }
[data-baseweb="option"]:hover { background: var(--surface3) !important; }
/* Selected item text */
div[data-baseweb="select"] [aria-selected="true"] { background: var(--accent-dim) !important; color: var(--accent) !important; }
/* Input and textarea */
.stTextInput input, .stNumberInput input, .stTextArea textarea { 
  background: var(--surface2) !important; border-color: var(--border) !important; 
  color: var(--text) !important; border-radius: 6px !important; font-size: 13px !important; 
}
/* Labels */
label[data-testid], .stSelectbox label, .stTextInput label, .stTextArea label, 
.stNumberInput label, .stFileUploader label {
  color: var(--text2) !important; font-size: 10px !important; font-weight: 700 !important; 
  letter-spacing: 0.08em !important; text-transform: uppercase !important; 
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════

def api_get(path, params=None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except:
        return None

def api_post(path, payload):
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def api_delete(path):
    try:
        r = requests.delete(f"{API_BASE}{path}", timeout=10)
        return r.status_code == 200
    except:
        return False

def fmt_ist(dt_str):
    if not dt_str: return "—"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(IST).strftime("%d-%b-%y %I:%M %p IST")
    except:
        return dt_str[:16] if dt_str else "—"

def price_fmt(p):
    if p is None: return "—"
    try:
        v = float(p)
        if v >= 10000: return f"₹{v:,.0f}"
        elif v >= 100: return f"₹{v:,.2f}"
        else: return f"₹{v:.4f}"
    except: return "—"

def card_cls(direction):
    d = (direction or "NEUTRAL").upper()
    return {"BULLISH": "bull", "BEARISH": "bear"}.get(d, "neutral")

def sig_pill(d):
    d = (d or "NEUTRAL").upper()
    if d == "BULLISH": return '<span class="pill p-bull">▲ Bullish</span>'
    if d == "BEARISH": return '<span class="pill p-bear">▼ Bearish</span>'
    return '<span class="pill p-neutral">◆ Neutral</span>'

def status_pill(s):
    s = (s or "PENDING").upper()
    cls = {"PENDING": "p-pending", "APPROVED": "p-approved", "DENIED": "p-denied", "REVIEW_LATER": "p-accent"}
    return f'<span class="pill {cls.get(s,"p-neutral")}">{s}</span>'

def conv_pill(c):
    c = (c or "MEDIUM").upper()
    cls = {"HIGH": "p-high", "MEDIUM": "p-medium", "LOW": "p-low"}
    return f'<span class="pill {cls.get(c,"p-neutral")}">{c}</span>'

def call_pill(c):
    c = (c or "").upper()
    buy_calls = {"BUY","STRONG_BUY","ACCUMULATE"}
    sell_calls = {"SELL","STRONG_SELL","REDUCE","EXIT"}
    if c in buy_calls: return f'<span class="pill p-bull" style="font-size:9px;">{c}</span>'
    if c in sell_calls: return f'<span class="pill p-bear" style="font-size:9px;">{c}</span>'
    return f'<span class="pill p-neutral" style="font-size:9px;">{c}</span>' if c else ""


TF_MAP = {
    "1": "1m", "3": "3m", "5": "5m", "15": "15m", "30": "30m",
    "60": "1h", "120": "2h", "240": "4h", "D": "1D", "W": "1W", "M": "1M",
    "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "2h": "2h", "4h": "4h", "1d": "1D", "1w": "1W",
}

def tf_label(i): return TF_MAP.get(str(i or ""), str(i or "—"))

def display_name(a):
    """Get the best display name for an alert card.
    Priority: alert_name (if set by user in TradingView) → alert_message (short ones like 'Nifty Test 1') → {ticker} Signal
    """
    ticker = a.get("ticker") or "—"
    aname = (a.get("alert_name") or "").strip()
    amsg  = (a.get("alert_message") or "").strip()

    # Use alert_name if it's a real user-set name (not generic fallback)
    if aname and aname not in ("System Trigger", "Manual Alert", ""):
        return aname

    # Use alert_message if it looks like a short custom name (not a long analysis text)
    if amsg and len(amsg) < 60 and not any(kw in amsg.lower() for kw in ["rsi", "macd", "alert on", "signal:", "price:", "confluence"]):
        return amsg

    return f"{ticker} Signal"


def chips_html(ind, full=False):
    if not ind: return ""
    c = []
    rsi = ind.get("rsi")
    if rsi is not None:
        v = float(rsi)
        cls = "c-bear" if v > 70 else "c-bull" if v < 30 else ""
        c.append(f'<span class="chip {cls}">RSI {v:.0f}</span>')
    mh = ind.get("macd_hist")
    if mh is not None:
        v = float(mh)
        c.append(f'<span class="chip {"c-bull" if v>0 else "c-bear"}">MACD {v:+.4f}</span>')
    st_ = ind.get("supertrend_dir")
    if st_:
        c.append(f'<span class="chip {"c-bull" if st_=="BULLISH" else "c-bear"}">ST {st_[:4]}</span>')
    adx = ind.get("adx")
    if adx is not None:
        v = float(adx)
        c.append(f'<span class="chip {"c-warn" if v>25 else ""}">ADX {v:.0f}</span>')
    ma = ind.get("ma_alignment")
    if ma:
        cls = "c-bull" if "BULL" in ma else "c-bear" if "BEAR" in ma else ""
        c.append(f'<span class="chip {cls}">MA {ma}</span>')
    htf = ind.get("htf_trend")
    if htf:
        c.append(f'<span class="chip {"c-bull" if htf=="BULLISH" else "c-bear" if htf=="BEARISH" else ""}">HTF {htf[:4]}</span>')
    if full:
        bb = ind.get("bb_pctb")
        if bb is not None:
            v = float(bb)
            c.append(f'<span class="chip {"c-bear" if v>0.8 else "c-bull" if v<0.2 else ""}">BB%B {v:.2f}</span>')
        vr = ind.get("vol_ratio")
        if vr is not None:
            v = float(vr)
            c.append(f'<span class="chip {"c-warn" if v>1.5 else ""}">Vol {v:.1f}x</span>')
        cp = ind.get("candle_pattern")
        if cp and cp.upper() not in ("NONE", ""):
            c.append(f'<span class="chip c-warn">{cp}</span>')
    return f'<div class="chips">{"".join(c)}</div>'

def conf_bar_html(ind):
    if not ind: return ""
    bull = ind.get("confluence_bull_score") or ind.get("confluence_bull") or 0
    bear = ind.get("confluence_bear_score") or ind.get("confluence_bear") or 0
    try:
        bull, bear = float(bull), float(bear)
        total = bull + bear
        if total == 0: return ""
        bp, brp = (bull/total)*100, (bear/total)*100
        return f"""<div class="conf-wrap">
<div class="conf-lbl">Confluence — Bull {bull:.0f} vs Bear {bear:.0f}</div>
<div class="conf-track">
  <div class="conf-bull" style="width:{bp:.1f}%"></div>
  <div class="conf-bear" style="width:{brp:.1f}%"></div>
</div></div>"""
    except: return ""

def fv(ind, k, dec=2):
    v = (ind or {}).get(k)
    if v is None: return "—"
    try: return f"{float(v):.{dec}f}"
    except: return str(v)


# ══════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════
stats = api_get("/api/stats") or {}
pending_ct = stats.get("pending", 0)
total_ct = stats.get("total_alerts", 0)

st.markdown(f"""
<div class="top-bar">
  <div class="top-brand">⚡ FIE · Jhaveri Securities <div class="live-dot"></div></div>
  <div class="top-stats">
    <div class="top-stat">Pending <strong>{pending_ct}</strong></div>
    <div class="top-stat">Total <strong>{total_ct}</strong></div>
  </div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "⚡  Command Center",
    "🎯  Trade Center",
    "📁  Alert Database",
    "📊  Performance",
    "🌐  Market Pulse",
])


# ══════════════════════════════════════════════════════════
# TAB 1 — COMMAND CENTER
# Auto-refreshes every 3s via st.fragment — no page reload
# ══════════════════════════════════════════════════════════
with tab1:
    @st.fragment(run_every=3)
    def command_center():
        data = api_get("/api/alerts", {"status": "PENDING", "limit": 50}) or {}
        alerts = data.get("alerts", [])
        bull_ct = sum(1 for a in alerts if (a.get("signal_direction","") or "").upper() == "BULLISH")
        bear_ct = sum(1 for a in alerts if (a.get("signal_direction","") or "").upper() == "BEARISH")

        st.markdown(f"""<div class="stat-row">
<div class="stat-card"><div class="stat-num">{len(alerts)}</div><div class="stat-lbl">Pending</div></div>
<div class="stat-card"><div class="stat-num bull">{bull_ct}</div><div class="stat-lbl">Bullish</div></div>
<div class="stat-card"><div class="stat-num bear">{bear_ct}</div><div class="stat-lbl">Bearish</div></div>
<div class="stat-card"><div class="stat-num">{total_ct}</div><div class="stat-lbl">All Time</div></div>
</div>""", unsafe_allow_html=True)

        if not alerts:
            st.markdown('<div class="no-data"><div class="no-data-icon">📭</div>No pending alerts. System monitoring active.</div>', unsafe_allow_html=True)
            return

        st.markdown(f'<div class="sec-hdr">Live Feed · {len(alerts)} signals</div>', unsafe_allow_html=True)

        # Render cards in a 2-column grid
        st.markdown('<div class="card-grid">', unsafe_allow_html=True)
        for a in alerts:
            d = (a.get("signal_direction") or "NEUTRAL").upper()
            ind = a.get("indicators") or {}
            cls = card_cls(d)
            ts = fmt_ist(a.get("received_at"))
            price = price_fmt(a.get("price_at_alert"))
            ticker = a.get("ticker") or "—"
            dname = display_name(a)
            tf = tf_label(a.get("interval"))
            asset = a.get("asset_class") or "—"
            summary = a.get("signal_summary") or a.get("alert_message") or "Signal received."

            st.markdown(f"""<div class="alert-card {cls}">
  <div class="card-top">
    <div>
      <div class="card-ticker">{ticker}</div>
      <div class="card-sub">{dname} · {tf} · {asset}</div>
    </div>
    <div>
      <div class="card-price">{price}</div>
      <div class="card-ts">{ts}</div>
    </div>
  </div>
  <div class="pills">{sig_pill(d)} {status_pill("PENDING")}</div>
  {conf_bar_html(ind)}
  {chips_html(ind)}
  <div class="ai-box"><div class="ai-lbl">AI Analysis</div>{summary}</div>
</div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    command_center()


# ══════════════════════════════════════════════════════════
# TAB 2 — TRADE CENTER
# Cards with session-state selection (no expanders = no rerun bug)
# ══════════════════════════════════════════════════════════
with tab2:
    data = api_get("/api/alerts", {"status": "PENDING", "limit": 50}) or {}
    tc_alerts = data.get("alerts", [])

    if not tc_alerts:
        st.markdown('<div class="no-data"><div class="no-data-icon">✅</div>No pending alerts to action.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="sec-hdr">Trade Center · {len(tc_alerts)} awaiting action</div>', unsafe_allow_html=True)

        if "tc_selected" not in st.session_state:
            st.session_state.tc_selected = None
        if "tc_action" not in st.session_state:
            st.session_state.tc_action = None

        # ── Card list ──
        for a in tc_alerts:
            alert_id = a.get("id")
            d = (a.get("signal_direction") or "NEUTRAL").upper()
            ind = a.get("indicators") or {}
            cls = card_cls(d)
            ts = fmt_ist(a.get("received_at"))
            price = price_fmt(a.get("price_at_alert"))
            ticker = a.get("ticker") or "—"
            dname = display_name(a)
            tf = tf_label(a.get("interval"))
            asset = a.get("asset_class") or "—"
            summary = a.get("signal_summary") or a.get("alert_message") or ""
            is_selected = st.session_state.tc_selected == alert_id

            # Compact summary row — clicking it selects/deselects
            conf = ind.get("confluence_bias", "")
            bull_s = ind.get("confluence_bull_score", "")
            bear_s = ind.get("confluence_bear_score", "")
            conf_txt = f"Bull {bull_s} vs Bear {bear_s}" if (bull_s != "" or bear_s != "") else conf

            _conf_pill = f'<span class="pill" style="background:var(--surface3);color:var(--text2);font-size:9px;">{conf_txt}</span>' if conf_txt else ""
            selected_bg = "background:var(--surface2);border-color:var(--accent);" if is_selected else ""
            st.markdown(f"""<div class="alert-card {cls}" style="margin-bottom:4px;cursor:pointer;{selected_bg}">
  <div class="card-top" style="margin-bottom:6px;">
    <div>
      <div class="card-ticker" style="font-size:16px;">{ticker}</div>
      <div class="card-sub">{dname} · {tf} · {asset}</div>
    </div>
    <div style="text-align:right;">
      <div class="card-price">{price}</div>
      <div class="card-ts">{ts}</div>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
    {sig_pill(d)}
    {status_pill("PENDING")}
    {_conf_pill}
    {chips_html(ind)}
  </div>
</div>""", unsafe_allow_html=True)

            btn_cols = st.columns([1, 1, 1, 5])
            with btn_cols[0]:
                if st.button("Details" if not is_selected else "▲ Hide", key=f"sel_{alert_id}", use_container_width=True):
                    if is_selected:
                        st.session_state.tc_selected = None
                        st.session_state.tc_action = None
                    else:
                        st.session_state.tc_selected = alert_id
                        st.session_state.tc_action = None
                    st.rerun()
            with btn_cols[1]:
                if st.button("✓ Approve", key=f"appr_{alert_id}", use_container_width=True, type="primary"):
                    st.session_state.tc_selected = alert_id
                    st.session_state.tc_action = "APPROVE"
                    st.rerun()
            with btn_cols[2]:
                if st.button("✗ Deny", key=f"deny_{alert_id}", use_container_width=True):
                    r = api_post(f"/api/alerts/{alert_id}/action", {"alert_id": alert_id, "decision": "DENIED"})
                    if r and not r.get("error"):
                        if st.session_state.tc_selected == alert_id:
                            st.session_state.tc_selected = None
                        st.rerun()
                    else:
                        st.error(f"Error: {(r or {}).get('error','Unknown')}")

            # ── Detail panel — only shown for selected card ──
            if is_selected:
                with st.container():
                    st.markdown('<div style="background:var(--surface2);border:1px solid var(--border2);border-radius:0 0 8px 8px;padding:16px;margin-top:-4px;margin-bottom:12px;">', unsafe_allow_html=True)

                    dc1, dc2 = st.columns([3, 2])

                    with dc1:
                        # Indicator grid
                        if ind:
                            st.markdown(f"""<div class="det-grid">
  <div class="det-cell"><div class="det-lbl">RSI-14</div><div class="det-val">{fv(ind,'rsi',1)}</div></div>
  <div class="det-cell"><div class="det-lbl">MACD Hist</div><div class="det-val">{fv(ind,'macd_hist',4)}</div></div>
  <div class="det-cell"><div class="det-lbl">SuperTrend</div><div class="det-val">{ind.get('supertrend_dir','—')}</div></div>
  <div class="det-cell"><div class="det-lbl">ADX</div><div class="det-val">{fv(ind,'adx',1)}</div></div>
  <div class="det-cell"><div class="det-lbl">MA Align</div><div class="det-val">{ind.get('ma_alignment','—')}</div></div>
  <div class="det-cell"><div class="det-lbl">BB %B</div><div class="det-val">{fv(ind,'bb_pctb',2)}</div></div>
  <div class="det-cell"><div class="det-lbl">Vol Ratio</div><div class="det-val">{fv(ind,'vol_ratio',1)}x</div></div>
  <div class="det-cell"><div class="det-lbl">ATR%</div><div class="det-val">{fv(ind,'atr_pct',3)}%</div></div>
  <div class="det-cell"><div class="det-lbl">HTF Trend</div><div class="det-val">{ind.get('htf_trend','—')}</div></div>
  <div class="det-cell"><div class="det-lbl">Candle</div><div class="det-val">{ind.get('candle_pattern','—')}</div></div>
</div>""", unsafe_allow_html=True)

                        # ── Lazy commentary — fetch on demand via API ──
                        if ind:
                            cached_key = f"commentary_{alert_id}"
                            if cached_key not in st.session_state:
                                with st.spinner("Generating AI commentary..."):
                                    res = api_post(f"/api/alerts/{alert_id}/commentary", {})
                                    st.session_state[cached_key] = (res or {}).get("commentary", "")
                            commentary = st.session_state.get(cached_key, "")
                            if commentary:
                                st.markdown(f'<div class="ai-box" style="margin-top:10px;"><div class="ai-lbl">AI Analysis</div>{commentary}</div>', unsafe_allow_html=True)
                        elif summary:
                            st.markdown(f'<div class="ai-box" style="margin-top:10px;"><div class="ai-lbl">Alert Message</div>{summary}</div>', unsafe_allow_html=True)

                    with dc2:
                        if st.session_state.tc_action == "APPROVE":
                            st.markdown('<div style="font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--bull);margin-bottom:12px;">Approval Details</div>', unsafe_allow_html=True)
                            call_opts = ["BUY","STRONG_BUY","SELL","STRONG_SELL","HOLD","ACCUMULATE","REDUCE","WATCH","EXIT"]
                            p_call = st.selectbox("Call Type", call_opts, key=f"call_{alert_id}")
                            conv = st.selectbox("Conviction", ["HIGH","MEDIUM","LOW"], index=1, key=f"conv_{alert_id}")
                            tgt = st.number_input("Target Price ₹", min_value=0.0, value=0.0, key=f"tgt_{alert_id}", format="%.2f")
                            stp = st.number_input("Stop Loss ₹", min_value=0.0, value=0.0, key=f"stp_{alert_id}", format="%.2f")
                            rationale = st.text_area("FM Rationale", placeholder="Brief thesis — why this call?", key=f"rat_{alert_id}", height=80)
                            chart_file = st.file_uploader("Chart Screenshot", type=["png","jpg","jpeg","webp"], key=f"chart_{alert_id}")
                            chart_b64 = base64.b64encode(chart_file.read()).decode("utf-8") if chart_file else None

                            s1, s2 = st.columns(2)
                            with s1:
                                if st.button("✓ Submit Approval", key=f"sub_{alert_id}", type="primary", use_container_width=True):
                                    payload = {
                                        "alert_id": alert_id, "decision": "APPROVED",
                                        "primary_call": p_call, "conviction": conv,
                                        "fm_rationale_text": rationale or None,
                                        "target_price": tgt if tgt > 0 else None,
                                        "stop_loss": stp if stp > 0 else None,
                                        "chart_image_b64": chart_b64,
                                    }
                                    res = api_post(f"/api/alerts/{alert_id}/action", payload)
                                    if res and not res.get("error"):
                                        st.success(f"✅ Approved: {p_call} / {conv}")
                                        st.session_state.tc_selected = None
                                        st.session_state.tc_action = None
                                        st.rerun()
                                    else:
                                        st.error(f"Error: {(res or {}).get('error','Unknown error')}")
                            with s2:
                                if st.button("Cancel", key=f"can_{alert_id}", use_container_width=True):
                                    st.session_state.tc_action = None
                                    st.rerun()
                        else:
                            st.markdown('<div style="color:var(--text3);font-size:12px;">Click ✓ Approve button above to fill in trade details.</div>', unsafe_allow_html=True)

                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)



# ══════════════════════════════════════════════════════════
# TAB 3 — ALERT DATABASE
# ══════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="sec-hdr">Alert Database · Complete Record</div>', unsafe_allow_html=True)

    f1, f2, f3, f4, f5 = st.columns([1.5, 1.5, 1.5, 1.5, 3])
    with f1: db_status = st.selectbox("Status", ["All", "APPROVED", "DENIED", "PENDING", "REVIEW_LATER"], key="db_s")
    with f2: db_signal = st.selectbox("Signal", ["All", "BULLISH", "BEARISH", "NEUTRAL"], key="db_sig")
    with f3: db_asset = st.selectbox("Asset", ["All", "INDEX", "EQUITY", "COMMODITY", "CURRENCY"], key="db_as")
    with f4: db_call = st.selectbox("Call", ["All", "BUY", "STRONG_BUY", "SELL", "STRONG_SELL", "HOLD", "ACCUMULATE", "REDUCE", "WATCH", "EXIT"], key="db_c")
    with f5: db_search = st.text_input("Search", placeholder="Ticker or alert name...", key="db_q")

    all_data = api_get("/api/master", {"limit": 200}) or {}
    all_alerts = all_data.get("alerts", [])

    filtered = all_alerts
    if db_status != "All":
        filtered = [a for a in filtered if (a.get("status") or "").upper() == db_status]
    if db_signal != "All":
        filtered = [a for a in filtered if (a.get("signal_direction") or "").upper() == db_signal]
    if db_asset != "All":
        filtered = [a for a in filtered if (a.get("asset_class") or "").upper() == db_asset]
    if db_call != "All":
        filtered = [a for a in filtered if a.get("action") and (a["action"].get("call") or "").upper() == db_call]
    if db_search:
        q = db_search.upper()
        filtered = [a for a in filtered if q in (a.get("ticker") or "").upper() or q in (a.get("alert_name") or "").upper()]

    st.caption(f"{len(filtered)} alerts")

    if not filtered:
        st.markdown('<div class="no-data"><div class="no-data-icon">🔍</div>No alerts match filters.</div>', unsafe_allow_html=True)
    else:
        if "db_selected" not in st.session_state:
            st.session_state.db_selected = None

        for a in filtered:
            d = (a.get("signal_direction") or "NEUTRAL").upper()
            status = (a.get("status") or "PENDING").upper()
            ind = a.get("indicators") or {}
            ts = fmt_ist(a.get("received_at"))
            price = price_fmt(a.get("price_at_alert"))
            ticker = a.get("ticker") or "—"
            dname = display_name(a)
            cls = "approved" if status == "APPROVED" else "denied" if status == "DENIED" else card_cls(d)
            alert_id = a.get("id")
            action = a.get("action") or {}
            summary = a.get("signal_summary") or a.get("alert_message") or ""
            is_selected = st.session_state.db_selected == alert_id

            # Compact row card
            selected_bg = "background:var(--surface2);" if is_selected else ""
            _call_pill  = call_pill(action.get("call", "")) if action else ""
            _conv_pill  = conv_pill(action.get("conviction", "")) if action else ""
            st.markdown(f"""<div class="alert-card {cls}" style="margin-bottom:4px;{selected_bg}">
  <div class="card-top" style="margin-bottom:4px;">
    <div>
      <div class="card-ticker" style="font-size:15px;">{ticker}</div>
      <div class="card-sub">{dname} · {tf_label(a.get('interval'))} · {a.get('asset_class','—')}</div>
    </div>
    <div style="text-align:right;">
      <div class="card-price">{price}</div>
      <div class="card-ts">{ts}</div>
    </div>
  </div>
  <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
    {sig_pill(d)} {status_pill(status)} {_call_pill} {_conv_pill}
  </div>
</div>""", unsafe_allow_html=True)

            db_row_cols = st.columns([1, 5])
            with db_row_cols[0]:
                if st.button("Details" if not is_selected else "Hide", key=f"dbs_{alert_id}", use_container_width=True):
                    st.session_state.db_selected = None if is_selected else alert_id
                    st.rerun()

            if is_selected:
                with st.container():
                    st.markdown(f'<div style="background:var(--surface2);border:1px solid var(--border2);border-radius:0 0 8px 8px;padding:16px;margin-top:-4px;margin-bottom:12px;">', unsafe_allow_html=True)

                    dl, dr = st.columns([3, 2])

                    with dl:
                        if ind:
                            st.markdown(f"""<div class="det-grid">
  <div class="det-cell"><div class="det-lbl">RSI-14</div><div class="det-val">{fv(ind,'rsi',1)}</div></div>
  <div class="det-cell"><div class="det-lbl">MACD Hist</div><div class="det-val">{fv(ind,'macd_hist',4)}</div></div>
  <div class="det-cell"><div class="det-lbl">SuperTrend</div><div class="det-val">{ind.get('supertrend_dir','—')}</div></div>
  <div class="det-cell"><div class="det-lbl">ADX</div><div class="det-val">{fv(ind,'adx',1)}</div></div>
  <div class="det-cell"><div class="det-lbl">MA Align</div><div class="det-val">{ind.get('ma_alignment','—')}</div></div>
  <div class="det-cell"><div class="det-lbl">BB %B</div><div class="det-val">{fv(ind,'bb_pctb',2)}</div></div>
  <div class="det-cell"><div class="det-lbl">Vol Ratio</div><div class="det-val">{fv(ind,'vol_ratio',1)}x</div></div>
  <div class="det-cell"><div class="det-lbl">ATR%</div><div class="det-val">{fv(ind,'atr_pct',3)}%</div></div>
  <div class="det-cell"><div class="det-lbl">HTF Trend</div><div class="det-val">{ind.get('htf_trend','—')}</div></div>
  <div class="det-cell"><div class="det-lbl">Candle</div><div class="det-val">{ind.get('candle_pattern','—')}</div></div>
</div>""", unsafe_allow_html=True)
                        if summary:
                            st.markdown(f'<div class="ai-box" style="margin-top:10px;"><div class="ai-lbl">AI Analysis</div>{summary}</div>', unsafe_allow_html=True)

                    with dr:
                        if action:
                            call = action.get("call") or "—"
                            conv = action.get("conviction") or "MEDIUM"
                            remarks = action.get("remarks") or ""
                            dec_at = fmt_ist(action.get("decision_at"))
                            tgt = action.get("target_price")
                            stp = action.get("stop_loss")
                            st.markdown(f"""<div style="background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:14px;">
  <div style="font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:var(--text3);margin-bottom:8px;">FM Decision</div>
  <div style="font-size:20px;font-weight:700;color:var(--text);margin-bottom:6px;">{call}</div>
  <div class="pills">{conv_pill(conv)}</div>
  {'<div style="margin-top:8px;font-size:11px;color:var(--text2);">Target: <b>₹' + f"{float(tgt):,.2f}" + '</b></div>' if tgt else ''}
  {'<div style="font-size:11px;color:var(--text2);">Stop: <b>₹' + f"{float(stp):,.2f}" + '</b></div>' if stp else ''}
  <div style="font-size:11px;color:var(--text3);margin-top:8px;font-family:'JetBrains Mono',monospace">{dec_at}</div>
</div>""", unsafe_allow_html=True)
                            if remarks:
                                st.markdown(f'<div class="ai-box" style="margin-top:10px;border-left-color:var(--gold)"><div class="ai-lbl">FM Rationale</div>{remarks}</div>', unsafe_allow_html=True)
                            if action.get("has_chart"):
                                chart_data = api_get(f"/api/alerts/{alert_id}/chart")
                                if chart_data and chart_data.get("chart_image_b64"):
                                    img = chart_data["chart_image_b64"]
                                    st.markdown(f'<div style="border-radius:6px;overflow:hidden;border:1px solid var(--border);margin-top:10px;"><img src="data:image/jpeg;base64,{img}" style="width:100%;display:block"/></div>', unsafe_allow_html=True)
                        else:
                            st.caption("No action taken yet.")

                        if st.button("🗑 Delete Alert", key=f"del_{alert_id}"):
                            if api_delete(f"/api/alerts/{alert_id}"):
                                st.session_state.db_selected = None
                                st.rerun()
                            else:
                                st.error("Delete failed.")

                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
# TAB 4 — PERFORMANCE
# ══════════════════════════════════════════════════════════
with tab4:
    @st.fragment(run_every=60)
    def performance_tab():
        st.markdown('<div class="sec-hdr">Performance Tracker · Approved Calls · Auto-refreshes every 60s</div>', unsafe_allow_html=True)

        # Auto-refresh prices on every fragment run
        api_post("/api/performance/refresh", {})

        perf_data = api_get("/api/performance") or {}
        records = perf_data.get("performance", [])
        nifty_ret = perf_data.get("nifty_return")

        ist_now = datetime.now(IST).strftime("%d-%b-%Y %I:%M %p IST")
        st.caption(f"Prices refreshed · {ist_now}")

        if not records:
            st.markdown('<div class="no-data"><div class="no-data-icon">📊</div>No data yet.<br>Approve an alert to start tracking performance.</div>', unsafe_allow_html=True)
            return

        valid = [r for r in records if r.get("return_pct") is not None]
        beats_list = [r for r in valid if r.get("beats_benchmark") is True]
        hit_list   = [r for r in valid if r.get("return_pct", 0) > 0]
        avg_r    = sum(r["return_pct"] for r in valid) / len(valid) if valid else 0
        hit_rate = len(hit_list) / len(valid) * 100 if valid else 0
        beat_rate = len(beats_list) / len(valid) * 100 if valid else 0
        best  = max(valid, key=lambda x: x["return_pct"]) if valid else None
        worst = min(valid, key=lambda x: x["return_pct"]) if valid else None
        max_dd_list = [r for r in records if r.get("max_drawdown") is not None]
        worst_dd = min(max_dd_list, key=lambda x: x["max_drawdown"]) if max_dd_list else None

        # ── Page-level KPI cards ──
        nifty_str = f"NIFTY 1d: {nifty_ret:+.2f}%" if nifty_ret is not None else "NIFTY: —"
        wd_num = f"{worst_dd['max_drawdown']:.2f}%" if worst_dd else "—"
        wd_tick = worst_dd['ticker'] if worst_dd else "—"
        st.markdown(f"""<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:20px;">
<div class="stat-card"><div class="stat-num {'bull' if avg_r>=0 else 'bear'}">{avg_r:+.2f}%</div><div class="stat-lbl">Avg Return</div><div style="font-size:10px;color:var(--text3);margin-top:4px;">{nifty_str}</div></div>
<div class="stat-card"><div class="stat-num {'bull' if hit_rate>=50 else 'bear'}">{hit_rate:.0f}%</div><div class="stat-lbl">Hit Rate</div><div style="font-size:10px;color:var(--text3);margin-top:4px;">{len(hit_list)}/{len(valid)} profitable</div></div>
<div class="stat-card"><div class="stat-num {'bull' if beat_rate>=50 else 'bear'}">{beat_rate:.0f}%</div><div class="stat-lbl">Beat Benchmark</div><div style="font-size:10px;color:var(--text3);margin-top:4px;">vs NIFTY 50</div></div>
<div class="stat-card"><div class="stat-num bear">{wd_num}</div><div class="stat-lbl">Worst Drawdown</div><div style="font-size:10px;color:var(--text3);margin-top:4px;">{wd_tick}</div></div>
</div>""", unsafe_allow_html=True)

        if best and worst:
            b_ref = float(best['reference_price']) if best.get('reference_price') else 0
            b_cur = float(best['current_price']) if best.get('current_price') else 0
            w_ref = float(worst['reference_price']) if worst.get('reference_price') else 0
            w_cur = float(worst['current_price']) if worst.get('current_price') else 0
            st.markdown(f"""<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-bottom:20px;">
<div class="stat-card" style="border-left:3px solid var(--bull);">
  <div style="font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--text3);margin-bottom:6px;">Best Call</div>
  <div style="font-size:16px;font-weight:700;color:var(--text);">{best['ticker']} · {best.get('action_call','—')}</div>
  <div style="font-size:22px;font-weight:700;color:var(--bull);margin:4px 0;">{best['return_pct']:+.2f}%</div>
  <div style="font-size:11px;color:var(--text2);">₹{b_ref:,.2f} → ₹{b_cur:,.2f}</div>
</div>
<div class="stat-card" style="border-left:3px solid var(--bear);">
  <div style="font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--text3);margin-bottom:6px;">Worst Call</div>
  <div style="font-size:16px;font-weight:700;color:var(--text);">{worst['ticker']} · {worst.get('action_call','—')}</div>
  <div style="font-size:22px;font-weight:700;color:var(--bear);margin:4px 0;">{worst['return_pct']:+.2f}%</div>
  <div style="font-size:11px;color:var(--text2);">₹{w_ref:,.2f} → ₹{w_cur:,.2f}</div>
</div>
</div>""", unsafe_allow_html=True)

        # ── Per-alert cards ──
        st.markdown('<div class="sec-hdr" style="margin-top:8px;">Individual Call Performance</div>', unsafe_allow_html=True)

        def pr(v):
            if v is None: return '<span style="color:var(--text3);">—</span>'
            col = "var(--bull)" if v >= 0 else "var(--bear)"
            return f'<span style="color:{col};font-weight:600;">{v:+.2f}%</span>'

        for r in records:
            ret     = r.get("return_pct")
            ref     = r.get("reference_price")
            curr    = r.get("current_price")
            dd      = r.get("max_drawdown")
            hi      = r.get("high_since")
            lo      = r.get("low_since")
            r1d     = r.get("return_1d")
            r1w     = r.get("return_1w")
            r1m     = r.get("return_1m")
            call    = r.get("action_call") or "—"
            conv    = r.get("conviction") or "—"
            tgt     = r.get("target_price")
            stp     = r.get("stop_loss")
            ticker  = r.get("ticker") or "—"
            direction = r.get("signal_direction", "BULLISH")
            beats   = r.get("beats_benchmark")
            updated = (r.get("last_updated") or "")[:10]

            ret_color = "var(--bull)" if (ret or 0) >= 0 else "var(--bear)"
            ret_str  = f"{ret:+.2f}%" if ret is not None else "—"
            ref_str  = f"₹{float(ref):,.2f}" if ref else "—"
            curr_str = f"₹{float(curr):,.2f}" if curr else "—"
            dd_str   = f"{dd:.2f}%" if dd is not None else "—"
            hi_str   = f"₹{float(hi):,.2f}" if hi else "—"
            lo_str   = f"₹{float(lo):,.2f}" if lo else "—"
            tgt_str  = f"₹{float(tgt):,.2f}" if tgt else "—"
            stp_str  = f"₹{float(stp):,.2f}" if stp else "—"

            benchmark_badge = ""
            if beats is True:
                benchmark_badge = '<span class="pill p-bull" style="font-size:9px;">↑ Beat NIFTY</span>'
            elif beats is False:
                benchmark_badge = '<span class="pill p-bear" style="font-size:9px;">↓ Lagged NIFTY</span>'

            dd_pill  = f'<span class="pill" style="font-size:9px;background:var(--surface3);color:var(--text2);">DD {dd_str}</span>' if dd is not None else ""
            hi_pill  = f'<span class="pill" style="font-size:9px;background:var(--surface3);color:var(--text2);">H {hi_str}</span>' if hi else ""
            lo_pill  = f'<span class="pill" style="font-size:9px;background:var(--surface3);color:var(--text2);">L {lo_str}</span>' if lo else ""

            # Target/stop progress bar
            progress_html = ""
            if tgt and stp and ref and curr:
                tgt_f, stp_f, curr_f = float(tgt), float(stp), float(curr)
                if tgt_f != stp_f:
                    rng  = tgt_f - stp_f
                    prog = max(0, min(100, (curr_f - stp_f) / rng * 100))
                    bar_col = "var(--bull)" if prog > 50 else "var(--gold)"
                    progress_html = f"""<div style="margin-top:10px;">
<div style="display:flex;justify-content:space-between;font-size:9px;color:var(--text3);margin-bottom:3px;">
  <span>SL {stp_str}</span><span>Entry {ref_str}</span><span>TGT {tgt_str}</span>
</div>
<div style="height:4px;background:var(--surface3);border-radius:2px;overflow:hidden;">
  <div style="width:{prog:.0f}%;height:100%;background:{bar_col};border-radius:2px;"></div>
</div></div>"""

            st.markdown(f"""<div class="alert-card {'bull' if (ret or 0)>=0 else 'bear'}" style="margin-bottom:10px;">
<div style="display:flex;justify-content:space-between;align-items:flex-start;">
  <div>
    <div style="font-size:18px;font-weight:700;color:var(--text);line-height:1;">{ticker}</div>
    <div style="font-size:11px;color:var(--text2);margin-top:2px;">{call} · {conv} · {updated}</div>
  </div>
  <div style="text-align:right;">
    <div style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:700;color:{ret_color};line-height:1;">{ret_str}</div>
    <div style="font-size:11px;color:var(--text3);margin-top:2px;">{ref_str} → {curr_str}</div>
  </div>
</div>
<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;">
  {benchmark_badge}{dd_pill}{hi_pill}{lo_pill}
</div>
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:10px;">
  <div class="det-cell"><div class="det-lbl">From Entry</div><div class="det-val" style="color:{ret_color};">{ret_str}</div></div>
  <div class="det-cell"><div class="det-lbl">1 Day</div><div class="det-val">{pr(r1d)}</div></div>
  <div class="det-cell"><div class="det-lbl">1 Week</div><div class="det-val">{pr(r1w)}</div></div>
  <div class="det-cell"><div class="det-lbl">1 Month</div><div class="det-val">{pr(r1m)}</div></div>
</div>
{progress_html}
</div>""", unsafe_allow_html=True)

    performance_tab()


# ══════════════════════════════════════════════════════════
# TAB 5 — MARKET PULSE
# Pure yfinance batch download — no nsetools dependency
# Auto-refreshes every 60s via st.fragment
# ══════════════════════════════════════════════════════════
with tab5:
    @st.fragment(run_every=60)
    def market_pulse():
        st.markdown('<div class="sec-hdr">Market Pulse · NSE Indices + Commodities + FX</div>', unsafe_allow_html=True)

        NSE_UNIVERSE = [
            # ── NSE Broad Market ──
            ("NIFTY 50",            "^NSEI",              "NSE Broad"),
            ("NIFTY NEXT 50",       "^NSMIDCP",           "NSE Broad"),
            ("NIFTY 100",           "^CNX100",            "NSE Broad"),
            ("NIFTY 200",           "^CNX200",            "NSE Broad"),
            ("NIFTY 500",           "^CRSLDX",            "NSE Broad"),
            ("NIFTY MIDCAP 50",     "^NSEMDCP50",         "NSE Broad"),
            ("NIFTY MIDCAP 100",    "^CNXMC",             "NSE Broad"),
            ("NIFTY SMALLCAP 100",  "^CNXSC",             "NSE Broad"),
            ("NIFTY SMALLCAP 250",  "^CNXSC250",          "NSE Broad"),
            ("NIFTY MICROCAP 250",  "NIFTY_MICROCAP250.NS","NSE Broad"),
            ("NIFTY LARGEMIDCAP",   "NIFTY_LARGEMIDCAP250.NS","NSE Broad"),
            ("INDIA VIX",           "^INDIAVIX",          "NSE Broad"),
            # ── NSE Sectoral ──
            ("NIFTY BANK",          "^NSEBANK",           "NSE Sectoral"),
            ("NIFTY IT",            "^CNXIT",             "NSE Sectoral"),
            ("NIFTY PHARMA",        "^CNXPHARMA",         "NSE Sectoral"),
            ("NIFTY AUTO",          "^CNXAUTO",           "NSE Sectoral"),
            ("NIFTY FMCG",          "^CNXFMCG",           "NSE Sectoral"),
            ("NIFTY METAL",         "^CNXMETAL",          "NSE Sectoral"),
            ("NIFTY REALTY",        "^CNXREALTY",         "NSE Sectoral"),
            ("NIFTY ENERGY",        "^CNXENERGY",         "NSE Sectoral"),
            ("NIFTY PSU BANK",      "^CNXPSUBANK",        "NSE Sectoral"),
            ("NIFTY INFRA",         "^CNXINFRA",          "NSE Sectoral"),
            ("NIFTY MEDIA",         "^CNXMEDIA",          "NSE Sectoral"),
            ("NIFTY HEALTHCARE",    "NIFTYHEALTHCARE.NS", "NSE Sectoral"),
            ("NIFTY FIN SERVICE",   "NIFTY_FIN_SERVICE.NS","NSE Sectoral"),
            ("NIFTY CONSUMER DURB", "NIFTYCONSUMER.NS",   "NSE Sectoral"),
            ("NIFTY OIL & GAS",     "^CNXOILGAS",         "NSE Sectoral"),
            ("NIFTY CHEMICALS",     "^CNXCHEMICALS",      "NSE Sectoral"),
            ("NIFTY CPSE",          "NIFTYCPSE.NS",       "NSE Sectoral"),
            # ── BSE ──
            ("SENSEX",              "^BSESN",             "BSE"),
            ("BSE MIDCAP",          "BSE-MIDCAP.BO",      "BSE"),
            ("BSE SMALLCAP",        "BSE-SMLCAP.BO",      "BSE"),
            ("BSE BANKEX",          "BSE-BANKEX.BO",      "BSE"),
            ("BSE IT",              "BSE-IT.BO",          "BSE"),
            # ── Commodities ──
            ("GOLD (MCX)",          "GC=F",               "Commodities"),
            ("SILVER (MCX)",        "SI=F",               "Commodities"),
            ("CRUDE OIL (MCX)",     "CL=F",               "Commodities"),
            ("NATURAL GAS",         "NG=F",               "Commodities"),
            ("COPPER",              "HG=F",               "Commodities"),
            ("ALUMINIUM",           "ALI=F",              "Commodities"),
            # ── FX ──
            ("USD/INR",             "USDINR=X",           "FX"),
            ("EUR/INR",             "EURINR=X",           "FX"),
            ("GBP/INR",             "GBPINR=X",           "FX"),
            ("JPY/INR",             "JPYINR=X",           "FX"),
            # ── Global ──
            ("S&P 500",             "^GSPC",              "Global"),
            ("NASDAQ",              "^IXIC",              "Global"),
            ("HANG SENG",           "^HSI",               "Global"),
            ("NIKKEI 225",          "^N225",              "Global"),
        ]

        symbols = [s for _, s, _ in NSE_UNIVERSE]
        price_cache = {}

        try:
            import yfinance as yf
            # Batch download — much faster than individual calls
            raw = yf.download(
                tickers=" ".join(symbols),
                period="5d",
                auto_adjust=True,
                progress=False,
                threads=True,
            )

            for (name, sym, cat) in NSE_UNIVERSE:
                try:
                    # Multi-ticker download: raw["Close"][sym]
                    if len(symbols) > 1:
                        closes = raw["Close"][sym].dropna()
                        highs = raw["High"][sym].dropna()
                        lows = raw["Low"][sym].dropna()
                    else:
                        closes = raw["Close"].dropna()
                        highs = raw["High"].dropna()
                        lows = raw["Low"].dropna()

                    if closes.empty:
                        price_cache[sym] = None
                        continue

                    curr = float(closes.iloc[-1])
                    prev = float(closes.iloc[-2]) if len(closes) > 1 else None
                    chg = round(((curr - prev) / prev) * 100, 2) if prev else None
                    price_cache[sym] = {
                        "price": curr,
                        "chg": chg,
                        "high": float(highs.iloc[-1]) if not highs.empty else None,
                        "low": float(lows.iloc[-1]) if not lows.empty else None,
                    }
                except:
                    price_cache[sym] = None

        except Exception as e:
            st.error(f"Market data fetch failed: {e}")
            st.caption("Tip: Ensure yfinance is installed and Railway has internet access.")
            return

        ist_now = datetime.now(IST).strftime("%d-%b-%Y %I:%M %p IST")
        live_count = sum(1 for v in price_cache.values() if v is not None)
        st.caption(f"Data via Yahoo Finance · {live_count}/{len(NSE_UNIVERSE)} indices loaded · {ist_now} · Refreshes every 60s")

        # Group and render
        cats_order = ["NSE Broad", "NSE Sectoral", "BSE", "Commodities", "FX", "Global"]
        cats_map = {}
        for name, sym, cat in NSE_UNIVERSE:
            cats_map.setdefault(cat, []).append((name, sym))

        for cat in cats_order:
            items = cats_map.get(cat)
            if not items: continue

            rows_html = ""
            for name, sym in items:
                d = price_cache.get(sym)
                if d is None:
                    p_str, chg_str, h_str, l_str = "—", '<span class="flat">N/A</span>', "—", "—"
                else:
                    p = d.get("price")
                    chg = d.get("chg")
                    h = d.get("high")
                    lo = d.get("low")
                    p_str = f"{p:,.2f}" if p else "—"
                    h_str = f"{h:,.2f}" if h else "—"
                    l_str = f"{lo:,.2f}" if lo else "—"
                    if chg is not None:
                        arrow = "▲" if chg > 0 else "▼" if chg < 0 else "◆"
                        cls = "up" if chg > 0 else "dn" if chg < 0 else "flat"
                        chg_str = f'<span class="{cls}">{arrow} {abs(chg):.2f}%</span>'
                    else:
                        chg_str = '<span class="flat">—</span>'

                rows_html += f"""<tr>
<td>{name}</td>
<td>{p_str}</td>
<td>{chg_str}</td>
<td>{h_str}</td>
<td>{l_str}</td>
</tr>"""

            st.markdown(f"""
<table class="pt">
<thead>
<tr><td colspan="5" class="pt-cat">{cat}</td></tr>
<tr>
  <th>Index / Instrument</th>
  <th>Last Price</th>
  <th>Change %</th>
  <th>Day High</th>
  <th>Day Low</th>
</tr>
</thead>
<tbody>{rows_html}</tbody>
</table>
""", unsafe_allow_html=True)

    market_pulse()
