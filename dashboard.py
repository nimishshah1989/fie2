"""
FIE — Financial Intelligence Engine Dashboard
Jhaveri Securities Intelligence Platform
5-Tab Streamlit Frontend: Command Center | Trade Center | Alert Database | Performance | Market Pulse
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta
import json
import base64
import os
import pytz

# ─── Config ────────────────────────────────────────────
API_BASE = os.getenv("FIE_API_URL", "http://localhost:8000")
IST = pytz.timezone("Asia/Kolkata")

st.set_page_config(
    page_title="FIE · Jhaveri Securities",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── CSS ───────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@300;400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

:root {
    --bg: #F4F5F7;
    --surface: #FFFFFF;
    --surface2: #F8F9FB;
    --border: #E2E4E9;
    --border2: #CDD1DA;
    --text: #0F1117;
    --text2: #4A5568;
    --text3: #8892A4;
    --bull: #0A8A4E;
    --bull-bg: #E8F7EF;
    --bear: #D92B2B;
    --bear-bg: #FEF0F0;
    --neutral: #6B7280;
    --neutral-bg: #F3F4F6;
    --accent: #1A56DB;
    --accent-bg: #EBF1FF;
    --gold: #B7791F;
    --gold-bg: #FEFCE8;
    --radius: 10px;
    --shadow: 0 1px 4px rgba(0,0,0,0.06), 0 2px 12px rgba(0,0,0,0.04);
    --shadow-md: 0 4px 16px rgba(0,0,0,0.08), 0 1px 4px rgba(0,0,0,0.04);
}

* { font-family: 'IBM Plex Sans', -apple-system, sans-serif !important; }
code, .mono { font-family: 'IBM Plex Mono', monospace !important; }

.stApp { background: var(--bg) !important; }
.main .block-container { padding: 0 1.5rem 2rem 1.5rem !important; max-width: 1500px !important; }
#MainMenu, footer, .stDeployButton, div[data-testid="stToolbar"],
div[data-testid="stDecoration"], div[data-testid="stStatusWidget"] { display: none !important; }
header[data-testid="stHeader"] { background: var(--surface) !important; border-bottom: 1px solid var(--border) !important; }
section[data-testid="stSidebar"] { display: none !important; }

/* ── Top Nav Header ── */
.fie-header {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 0 1.5rem;
    margin: 0 -1.5rem 1.5rem -1.5rem;
    display: flex;
    align-items: center;
    gap: 2rem;
    height: 56px;
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: 0 1px 0 var(--border);
}
.fie-brand {
    font-family: 'Syne', sans-serif !important;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: var(--text);
    white-space: nowrap;
    display: flex;
    align-items: center;
    gap: 8px;
}
.fie-brand span.bolt { color: var(--accent); font-size: 18px; }
.fie-live-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--bull);
    display: inline-block;
    animation: pulse-dot 2s infinite;
}
@keyframes pulse-dot {
    0%,100% { opacity:1; transform: scale(1); }
    50% { opacity:0.5; transform: scale(0.8); }
}

/* ── Tab Navigation ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0 !important;
    background: transparent !important;
    border-bottom: 2px solid var(--border) !important;
    padding: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    padding: 10px 20px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: var(--text3) !important;
    border-radius: 0 !important;
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    margin-bottom: -2px !important;
    letter-spacing: 0.01em !important;
}
.stTabs [aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab-panel"] { padding: 1.5rem 0 0 0 !important; }

/* ── Cards ── */
.alert-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 18px 20px;
    margin-bottom: 12px;
    box-shadow: var(--shadow);
    position: relative;
    overflow: hidden;
    transition: box-shadow 0.15s;
}
.alert-card:hover { box-shadow: var(--shadow-md); }
.alert-card.bull { border-left: 4px solid var(--bull); }
.alert-card.bear { border-left: 4px solid var(--bear); }
.alert-card.neutral { border-left: 4px solid var(--neutral); }
.alert-card.approved { border-left: 4px solid var(--bull); }
.alert-card.denied { border-left: 4px solid var(--bear); }

.card-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 12px;
    gap: 12px;
}
.card-ticker {
    font-family: 'Syne', sans-serif !important;
    font-size: 20px;
    font-weight: 700;
    color: var(--text);
    letter-spacing: -0.01em;
    line-height: 1;
}
.card-name { font-size: 11px; color: var(--text3); margin-top: 3px; letter-spacing: 0.02em; }
.card-price {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 22px;
    font-weight: 600;
    color: var(--text);
    text-align: right;
    line-height: 1;
}
.card-price-label { font-size: 10px; color: var(--text3); text-align: right; margin-top: 2px; letter-spacing: 0.04em; text-transform: uppercase; }
.card-ts { font-size: 11px; color: var(--text3); font-family: 'IBM Plex Mono', monospace !important; text-align: right; }

/* ── Pills ── */
.pill {
    display: inline-flex;
    align-items: center;
    padding: 3px 10px;
    border-radius: 100px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    line-height: 1.6;
}
.pill-bull { background: var(--bull-bg); color: var(--bull); }
.pill-bear { background: var(--bear-bg); color: var(--bear); }
.pill-neutral { background: var(--neutral-bg); color: var(--neutral); }
.pill-pending { background: #FFF7ED; color: #C05621; }
.pill-approved { background: var(--bull-bg); color: var(--bull); }
.pill-denied { background: var(--bear-bg); color: var(--bear); }
.pill-blue { background: var(--accent-bg); color: var(--accent); }
.pill-gold { background: var(--gold-bg); color: var(--gold); }
.pill-high { background: #FEF0F0; color: #C53030; }
.pill-medium { background: #FFFBEB; color: #B7791F; }
.pill-low { background: var(--bull-bg); color: var(--bull); }

/* ── Indicator Chips ── */
.ind-row { display: flex; flex-wrap: wrap; gap: 6px; margin: 10px 0; }
.ind-chip {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px;
    padding: 4px 10px;
    border-radius: 6px;
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--text2);
    white-space: nowrap;
}
.ind-chip.red { background: var(--bear-bg); border-color: #FCA5A5; color: var(--bear); }
.ind-chip.green { background: var(--bull-bg); border-color: #6EE7B7; color: var(--bull); }
.ind-chip.amber { background: #FFFBEB; border-color: #FCD34D; color: #92400E; }

/* ── Confluence Bar ── */
.confluence-bar-wrap { margin: 10px 0 6px 0; }
.confluence-label { font-size: 10px; color: var(--text3); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px; }
.confluence-bar { height: 6px; border-radius: 3px; background: var(--border); overflow: hidden; position: relative; }
.confluence-fill-bull { height: 100%; border-radius: 3px; background: linear-gradient(90deg, #0A8A4E, #34D399); }
.confluence-fill-bear { height: 100%; border-radius: 3px; background: linear-gradient(90deg, #D92B2B, #F87171); float: right; }

/* ── AI Commentary ── */
.ai-commentary {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px 14px;
    margin: 10px 0 0 0;
    font-size: 13px;
    line-height: 1.65;
    color: var(--text2);
}
.ai-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text3); margin-bottom: 6px; display: flex; align-items: center; gap: 6px; }

/* ── Stat Cards ── */
.stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px 20px;
    box-shadow: var(--shadow);
}
.stat-value {
    font-family: 'Syne', sans-serif !important;
    font-size: 28px;
    font-weight: 700;
    color: var(--text);
    line-height: 1;
}
.stat-label { font-size: 11px; color: var(--text3); margin-top: 4px; text-transform: uppercase; letter-spacing: 0.06em; }

/* ── Filter Bar ── */
.filter-bar {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 12px 16px;
    margin-bottom: 16px;
    box-shadow: var(--shadow);
}

/* ── Section Header ── */
.section-header {
    font-family: 'Syne', sans-serif !important;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text3);
    padding: 0 0 10px 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 16px;
}

/* ── Market Pulse Table ── */
.pulse-table { width: 100%; border-collapse: collapse; }
.pulse-table th {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text3);
    padding: 8px 12px;
    border-bottom: 2px solid var(--border);
    text-align: right;
}
.pulse-table th:first-child { text-align: left; }
.pulse-table td {
    font-size: 13px;
    padding: 10px 12px;
    border-bottom: 1px solid var(--border);
    color: var(--text);
    text-align: right;
    font-family: 'IBM Plex Mono', monospace !important;
}
.pulse-table td:first-child { text-align: left; font-family: 'IBM Plex Sans', sans-serif !important; font-size: 13px; font-weight: 500; }
.pulse-table tr:hover td { background: var(--surface2); }
.chg-pos { color: var(--bull) !important; }
.chg-neg { color: var(--bear) !important; }
.chg-neutral { color: var(--neutral) !important; }

/* ── Performance Table ── */
.perf-pos { color: var(--bull); font-weight: 600; }
.perf-neg { color: var(--bear); font-weight: 600; }

/* ── Action Button Overrides ── */
.stButton button {
    border-radius: 8px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 6px 16px !important;
    transition: all 0.15s !important;
    letter-spacing: 0.01em !important;
}
.stButton button:hover { transform: translateY(-1px) !important; }

/* ── Form elements ── */
.stSelectbox div[data-baseweb="select"] > div { border-radius: 8px !important; background: var(--surface) !important; border-color: var(--border) !important; }
.stTextInput input, .stTextArea textarea { border-radius: 8px !important; font-size: 13px !important; }
.stFileUploader { border-radius: 8px !important; }

/* ── No data state ── */
.no-data {
    text-align: center;
    padding: 48px 24px;
    color: var(--text3);
    font-size: 14px;
}
.no-data-icon { font-size: 32px; margin-bottom: 12px; }

/* ── Divider ── */
.card-divider { height: 1px; background: var(--border); margin: 12px 0; }

/* ── Detail Grid ── */
.detail-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin: 12px 0; }
.detail-cell { background: var(--surface2); border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; }
.detail-cell-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text3); margin-bottom: 4px; }
.detail-cell-value { font-family: 'IBM Plex Mono', monospace !important; font-size: 13px; font-weight: 500; color: var(--text); }

/* ── Chart Image ── */
.chart-img-wrap { border-radius: 8px; overflow: hidden; border: 1px solid var(--border); margin-top: 10px; }
.chart-img-wrap img { width: 100%; display: block; }

/* ── Expander ── */
.stExpander { border: 1px solid var(--border) !important; border-radius: var(--radius) !important; background: var(--surface) !important; box-shadow: var(--shadow) !important; }
.stExpander header { font-weight: 500 !important; font-size: 14px !important; }
</style>
""", unsafe_allow_html=True)


# ─── Utilities ─────────────────────────────────────────

def api_get(path, params=None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return None

def api_post(path, payload):
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def fmt_ist(dt_str):
    """Format UTC ISO string to dd-Mon-YY HH:MM AM/PM IST"""
    if not dt_str:
        return "—"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        ist_dt = dt.astimezone(IST)
        return ist_dt.strftime("%d-%b-%y %I:%M %p IST")
    except:
        return dt_str[:16] if dt_str else "—"

def price_fmt(p):
    if p is None:
        return "—"
    try:
        v = float(p)
        if v >= 10000:
            return f"₹{v:,.0f}"
        elif v >= 100:
            return f"₹{v:,.2f}"
        else:
            return f"₹{v:.4f}"
    except:
        return "—"

def signal_pill(direction):
    d = (direction or "NEUTRAL").upper()
    if d == "BULLISH":
        return '<span class="pill pill-bull">▲ Bullish</span>'
    elif d == "BEARISH":
        return '<span class="pill pill-bear">▼ Bearish</span>'
    else:
        return '<span class="pill pill-neutral">◆ Neutral</span>'

def status_pill(status):
    s = (status or "PENDING").upper()
    cls_map = {"PENDING": "pill-pending", "APPROVED": "pill-approved", "DENIED": "pill-denied", "REVIEW_LATER": "pill-blue"}
    return f'<span class="pill {cls_map.get(s, "pill-neutral")}">{s}</span>'

def conviction_pill(c):
    c = (c or "MEDIUM").upper()
    cls = {"HIGH": "pill-high", "MEDIUM": "pill-medium", "LOW": "pill-low"}
    return f'<span class="pill {cls.get(c, "pill-neutral")}">{c}</span>'

def card_class(direction):
    d = (direction or "NEUTRAL").upper()
    return {"BULLISH": "bull", "BEARISH": "bear"}.get(d, "neutral")

def ind_chips_html(indicators, compact=False):
    """Build indicator chip row HTML."""
    if not indicators:
        return ""
    chips = []

    rsi = indicators.get("rsi")
    if rsi is not None:
        v = float(rsi)
        cls = "red" if v > 70 else "green" if v < 30 else ""
        chips.append(f'<span class="ind-chip {cls}">RSI {v:.0f}</span>')

    macd_hist = indicators.get("macd_hist")
    if macd_hist is not None:
        v = float(macd_hist)
        cls = "green" if v > 0 else "red"
        chips.append(f'<span class="ind-chip {cls}">MACD {"+" if v>0 else ""}{v:.4f}</span>')

    st = indicators.get("supertrend_dir")
    if st:
        cls = "green" if st == "BULLISH" else "red"
        chips.append(f'<span class="ind-chip {cls}">ST {st[:4]}</span>')

    adx = indicators.get("adx")
    if adx is not None:
        v = float(adx)
        cls = "amber" if v > 25 else ""
        chips.append(f'<span class="ind-chip {cls}">ADX {v:.0f}</span>')

    ma = indicators.get("ma_alignment")
    if ma:
        cls = "green" if ma == "BULL" else "red" if ma == "BEAR" else ""
        chips.append(f'<span class="ind-chip {cls}">MA {ma}</span>')

    htf = indicators.get("htf_trend")
    if htf:
        cls = "green" if htf == "BULLISH" else "red" if htf == "BEARISH" else ""
        chips.append(f'<span class="ind-chip {cls}">HTF {htf[:4]}</span>')

    if not compact:
        bb = indicators.get("bb_pctb")
        if bb is not None:
            v = float(bb)
            cls = "red" if v > 0.8 else "green" if v < 0.2 else ""
            chips.append(f'<span class="ind-chip {cls}">BB%B {v:.2f}</span>')

        vr = indicators.get("vol_ratio")
        if vr is not None:
            v = float(vr)
            cls = "amber" if v > 1.5 else ""
            chips.append(f'<span class="ind-chip {cls}">Vol {v:.1f}x</span>')

        cp = indicators.get("candle_pattern")
        if cp and cp.upper() not in ("NONE", ""):
            chips.append(f'<span class="ind-chip amber">{cp}</span>')

    return f'<div class="ind-row">{"".join(chips)}</div>'

def confluence_bar_html(indicators):
    if not indicators:
        return ""
    bull = indicators.get("confluence_bull_score") or indicators.get("confluence_bull") or 0
    bear = indicators.get("confluence_bear_score") or indicators.get("confluence_bear") or 0
    try:
        bull, bear = float(bull), float(bear)
        total = bull + bear
        if total == 0:
            return ""
        bull_pct = (bull / total) * 100
        bear_pct = (bear / total) * 100
        return f"""<div class="confluence-bar-wrap">
<div class="confluence-label">Confluence — Bull {bull:.0f} vs Bear {bear:.0f}</div>
<div class="confluence-bar">
  <div class="confluence-fill-bull" style="width:{bull_pct:.1f}%;float:left;"></div>
  <div class="confluence-fill-bear" style="width:{bear_pct:.1f}%;"></div>
</div></div>"""
    except:
        return ""


# ─── Header ────────────────────────────────────────────
stats = api_get("/api/stats") or {}
pending = stats.get("pending", 0)
total = stats.get("total_alerts", 0)

st.markdown(f"""
<div class="fie-header">
  <div class="fie-brand">
    <span class="bolt">⚡</span> FIE &nbsp;·&nbsp; JHAVERI SECURITIES
    <div class="fie-live-dot"></div>
  </div>
</div>
""", unsafe_allow_html=True)


# ─── Tabs ───────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "⚡ Command Center",
    "🎯 Trade Center",
    "📁 Alert Database",
    "📊 Performance",
    "🌐 Market Pulse",
])


# ══════════════════════════════════════════════════════════
# TAB 1 — COMMAND CENTER
# ══════════════════════════════════════════════════════════
with tab1:
    @st.fragment(run_every=3)
    def command_center():
        data = api_get("/api/alerts", {"status": "PENDING", "limit": 50}) or {}
        alerts = data.get("alerts", [])

        # Stats row
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f'<div class="stat-card"><div class="stat-value">{len(alerts)}</div><div class="stat-label">Pending Alerts</div></div>', unsafe_allow_html=True)
        with c2:
            bull_count = sum(1 for a in alerts if (a.get("signal_direction","") or "").upper() == "BULLISH")
            st.markdown(f'<div class="stat-card"><div class="stat-value" style="color:var(--bull)">{bull_count}</div><div class="stat-label">Bullish Signals</div></div>', unsafe_allow_html=True)
        with c3:
            bear_count = sum(1 for a in alerts if (a.get("signal_direction","") or "").upper() == "BEARISH")
            st.markdown(f'<div class="stat-card"><div class="stat-value" style="color:var(--bear)">{bear_count}</div><div class="stat-label">Bearish Signals</div></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="stat-card"><div class="stat-value">{total}</div><div class="stat-label">Total Alerts</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if not alerts:
            st.markdown('<div class="no-data"><div class="no-data-icon">📭</div>No pending alerts. System is monitoring.</div>', unsafe_allow_html=True)
            return

        st.markdown(f'<div class="section-header">Live Pending Alerts · {len(alerts)} signals</div>', unsafe_allow_html=True)

        for a in alerts:
            direction = (a.get("signal_direction") or "NEUTRAL").upper()
            ind = a.get("indicators") or {}
            cls = card_class(direction)

            ts = fmt_ist(a.get("received_at"))
            price = price_fmt(a.get("price_at_alert"))
            summary = a.get("signal_summary") or a.get("alert_message") or "Signal received."

            chips_html = ind_chips_html(ind, compact=True)
            conf_html = confluence_bar_html(ind)
            sig_pill = signal_pill(direction)
            s_pill = status_pill("PENDING")

            asset = a.get("asset_class") or "—"
            interval = a.get("interval") or "—"
            tf_map = {"1":"1m","3":"3m","5":"5m","15":"15m","30":"30m","60":"1H","D":"Daily","W":"Weekly"}
            tf = tf_map.get(str(interval), f"{interval}")

            st.markdown(f"""
<div class="alert-card {cls}">
  <div class="card-header">
    <div>
      <div class="card-ticker">{a.get('ticker','—')}</div>
      <div class="card-name">{a.get('alert_name','—')} &nbsp;·&nbsp; {tf} &nbsp;·&nbsp; {asset}</div>
      <div style="margin-top:6px;display:flex;gap:6px;">{sig_pill}{s_pill}</div>
    </div>
    <div style="text-align:right;">
      <div class="card-price">{price}</div>
      <div class="card-price-label">Alert Price</div>
      <div class="card-ts">{ts}</div>
    </div>
  </div>
  {conf_html}
  {chips_html}
  <div class="ai-commentary">
    <div class="ai-label">🤖 AI Analysis</div>
    {summary}
  </div>
</div>
""", unsafe_allow_html=True)

    command_center()


# ══════════════════════════════════════════════════════════
# TAB 2 — TRADE CENTER
# ══════════════════════════════════════════════════════════
with tab2:
    data = api_get("/api/alerts", {"status": "PENDING", "limit": 50}) or {}
    alerts = data.get("alerts", [])

    if not alerts:
        st.markdown('<div class="no-data"><div class="no-data-icon">✅</div>No pending alerts to action. All clear!</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="section-header">Trade Center · {len(alerts)} Awaiting Action</div>', unsafe_allow_html=True)

        for a in alerts:
            direction = (a.get("signal_direction") or "NEUTRAL").upper()
            ind = a.get("indicators") or {}
            cls = card_class(direction)
            ts = fmt_ist(a.get("received_at"))
            price = price_fmt(a.get("price_at_alert"))
            summary = a.get("signal_summary") or a.get("alert_message") or ""
            alert_id = a.get("id")

            with st.expander(f"#{alert_id} · {a.get('ticker','—')} · {a.get('alert_name','Signal')} · {price} · {ts}", expanded=False):

                # Full detail card inside expander
                col_l, col_r = st.columns([3, 2])

                with col_l:
                    # Signal + metadata
                    sig_pill = signal_pill(direction)
                    asset = a.get("asset_class") or "—"
                    interval = a.get("interval") or "—"
                    tf_map = {"1":"1m","3":"3m","5":"5m","15":"15m","30":"30m","60":"1H","D":"Daily","W":"Weekly"}
                    tf = tf_map.get(str(interval), f"{interval}")
                    sector = a.get("sector") or "—"

                    st.markdown(f"""
<div class="alert-card {cls}" style="margin-bottom:0">
  <div class="card-header">
    <div>
      <div class="card-ticker">{a.get('ticker','—')}</div>
      <div class="card-name">{a.get('alert_name','—')} &nbsp;·&nbsp; {tf} &nbsp;·&nbsp; {asset}</div>
      <div style="margin-top:6px;">{sig_pill} <span class="pill pill-blue">{sector}</span></div>
    </div>
    <div style="text-align:right;">
      <div class="card-price">{price}</div>
      <div class="card-ts">{ts}</div>
    </div>
  </div>
  {confluence_bar_html(ind)}
  {ind_chips_html(ind, compact=False)}
</div>
""", unsafe_allow_html=True)

                    # Extended indicator grid
                    if ind:
                        def ic(k):
                            v = ind.get(k)
                            return f"{float(v):.4f}" if v is not None and isinstance(v, (int, float)) else (str(v) if v else "—")

                        st.markdown(f"""
<div class="detail-grid">
  <div class="detail-cell"><div class="detail-cell-label">RSI-14</div><div class="detail-cell-value">{ic('rsi')}</div></div>
  <div class="detail-cell"><div class="detail-cell-label">MACD Hist</div><div class="detail-cell-value">{ic('macd_hist')}</div></div>
  <div class="detail-cell"><div class="detail-cell-label">SuperTrend</div><div class="detail-cell-value">{ind.get('supertrend_dir','—')}</div></div>
  <div class="detail-cell"><div class="detail-cell-label">ADX</div><div class="detail-cell-value">{ic('adx')}</div></div>
  <div class="detail-cell"><div class="detail-cell-label">MA Align</div><div class="detail-cell-value">{ind.get('ma_alignment','—')}</div></div>
  <div class="detail-cell"><div class="detail-cell-label">BB %B</div><div class="detail-cell-value">{ic('bb_pctb')}</div></div>
  <div class="detail-cell"><div class="detail-cell-label">Vol Ratio</div><div class="detail-cell-value">{ic('vol_ratio')}</div></div>
  <div class="detail-cell"><div class="detail-cell-label">ATR%</div><div class="detail-cell-value">{ic('atr_pct')}</div></div>
  <div class="detail-cell"><div class="detail-cell-label">HTF Trend</div><div class="detail-cell-value">{ind.get('htf_trend','—')}</div></div>
  <div class="detail-cell"><div class="detail-cell-label">Candle Pat</div><div class="detail-cell-value">{ind.get('candle_pattern','—')}</div></div>
</div>
""", unsafe_allow_html=True)

                    # AI Commentary
                    if summary:
                        st.markdown(f'<div class="ai-commentary"><div class="ai-label">🤖 AI Analysis</div>{summary}</div>', unsafe_allow_html=True)

                with col_r:
                    st.markdown("**Take Action**")

                    action_key = f"action_{alert_id}"
                    if action_key not in st.session_state:
                        st.session_state[action_key] = None

                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    with btn_col1:
                        if st.button("✅ Approve", key=f"btn_approve_{alert_id}", use_container_width=True, type="primary"):
                            st.session_state[action_key] = "APPROVE"
                    with btn_col2:
                        if st.button("❌ Deny", key=f"btn_deny_{alert_id}", use_container_width=True):
                            # Immediate deny — no fields needed
                            result = api_post(f"/api/alerts/{alert_id}/action", {"alert_id": alert_id, "decision": "DENIED"})
                            if result and not result.get("error"):
                                st.success("Denied.")
                                st.rerun()
                            else:
                                st.error(f"Error: {result.get('error','Unknown')}")
                    with btn_col3:
                        if st.button("🔁 Later", key=f"btn_later_{alert_id}", use_container_width=True):
                            result = api_post(f"/api/alerts/{alert_id}/action", {"alert_id": alert_id, "decision": "REVIEW_LATER"})
                            if result and not result.get("error"):
                                st.info("Marked for review.")
                                st.rerun()
                            else:
                                st.error(f"Error: {result.get('error','Unknown')}")

                    # Approve form
                    if st.session_state.get(action_key) == "APPROVE":
                        st.markdown('<div class="card-divider"></div>', unsafe_allow_html=True)
                        st.markdown("**Approval Details**")

                        call_options = ["BUY", "STRONG_BUY", "SELL", "STRONG_SELL", "HOLD", "ACCUMULATE", "REDUCE", "WATCH", "EXIT"]
                        primary_call = st.selectbox("Call Type", call_options, key=f"call_{alert_id}")
                        conviction = st.selectbox("Conviction", ["HIGH", "MEDIUM", "LOW"], index=1, key=f"conv_{alert_id}")

                        st.markdown("**Optional — Pricing**")
                        p1, p2 = st.columns(2)
                        with p1:
                            target = st.number_input("Target Price", min_value=0.0, value=0.0, key=f"tp_{alert_id}", format="%.2f")
                        with p2:
                            stop = st.number_input("Stop Loss", min_value=0.0, value=0.0, key=f"sl_{alert_id}", format="%.2f")

                        fm_rationale = st.text_area("FM Rationale", placeholder="Brief thesis / key reason for this call...", key=f"rat_{alert_id}", height=80)

                        chart_file = st.file_uploader("Chart Screenshot (optional)", type=["png","jpg","jpeg","webp"], key=f"chart_{alert_id}")
                        chart_b64 = None
                        if chart_file:
                            chart_b64 = base64.b64encode(chart_file.read()).decode("utf-8")

                        if st.button("🚀 Submit Approval", key=f"submit_{alert_id}", type="primary", use_container_width=True):
                            payload = {
                                "alert_id": alert_id,
                                "decision": "APPROVED",
                                "primary_call": primary_call,
                                "conviction": conviction,
                                "fm_rationale_text": fm_rationale or None,
                                "target_price": target if target > 0 else None,
                                "stop_loss": stop if stop > 0 else None,
                                "chart_image_b64": chart_b64,
                            }
                            result = api_post(f"/api/alerts/{alert_id}/action", payload)
                            if result and not result.get("error"):
                                st.success(f"✅ Approved as {primary_call} with {conviction} conviction.")
                                st.session_state[action_key] = None
                                st.rerun()
                            else:
                                st.error(f"Error: {result.get('error','Unknown')}")


# ══════════════════════════════════════════════════════════
# TAB 3 — ALERT DATABASE
# ══════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-header">Alert Database · Complete Record</div>', unsafe_allow_html=True)

    # Filters
    with st.container():
        st.markdown('<div class="filter-bar">', unsafe_allow_html=True)
        f1, f2, f3, f4, f5 = st.columns([2, 2, 2, 2, 3])
        with f1:
            filter_status = st.selectbox("Status", ["All", "APPROVED", "DENIED", "REVIEW_LATER"], key="db_status")
        with f2:
            filter_signal = st.selectbox("Signal", ["All", "BULLISH", "BEARISH", "NEUTRAL"], key="db_signal")
        with f3:
            filter_asset = st.selectbox("Asset Class", ["All", "INDEX", "EQUITY", "COMMODITY", "CURRENCY"], key="db_asset")
        with f4:
            filter_call = st.selectbox("Call Type", ["All", "BUY", "STRONG_BUY", "SELL", "STRONG_SELL", "HOLD", "ACCUMULATE", "REDUCE", "WATCH", "EXIT"], key="db_call")
        with f5:
            filter_search = st.text_input("Search ticker / alert name", placeholder="e.g. NIFTY, BANKNIFTY...", key="db_search")
        st.markdown('</div>', unsafe_allow_html=True)

    all_data = api_get("/api/master", {"limit": 200}) or {}
    all_alerts = all_data.get("alerts", [])

    # Apply filters
    filtered = all_alerts
    if filter_status != "All":
        filtered = [a for a in filtered if (a.get("status") or "").upper() == filter_status]
    if filter_signal != "All":
        filtered = [a for a in filtered if (a.get("signal_direction") or "").upper() == filter_signal]
    if filter_asset != "All":
        filtered = [a for a in filtered if (a.get("asset_class") or "").upper() == filter_asset]
    if filter_call != "All":
        filtered = [a for a in filtered if a.get("action") and (a["action"].get("call") or "").upper() == filter_call]
    if filter_search:
        q = filter_search.upper()
        filtered = [a for a in filtered if q in (a.get("ticker") or "").upper() or q in (a.get("alert_name") or "").upper()]

    if not filtered:
        st.markdown('<div class="no-data"><div class="no-data-icon">🔍</div>No alerts match the selected filters.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f"**{len(filtered)} alerts**", unsafe_allow_html=False)

        for a in filtered:
            direction = (a.get("signal_direction") or "NEUTRAL").upper()
            status = (a.get("status") or "PENDING").upper()
            ind = a.get("indicators") or {}
            ts = fmt_ist(a.get("received_at"))
            price = price_fmt(a.get("price_at_alert"))
            summary = a.get("signal_summary") or a.get("alert_message") or ""
            action = a.get("action") or {}
            cls = "approved" if status == "APPROVED" else "denied" if status == "DENIED" else card_class(direction)
            alert_id = a.get("id")

            with st.expander(f"#{alert_id} · {a.get('ticker','—')} · {status} · {a.get('alert_name','—')} · {ts}", expanded=False):
                left, right = st.columns([3, 2])

                with left:
                    sig_pill = signal_pill(direction)
                    s_pill = status_pill(status)

                    st.markdown(f"""
<div class="alert-card {cls}" style="margin-bottom:0">
  <div class="card-header">
    <div>
      <div class="card-ticker">{a.get('ticker','—')}</div>
      <div class="card-name">{a.get('alert_name','—')} &nbsp;·&nbsp; {a.get('interval','—')} &nbsp;·&nbsp; {a.get('asset_class','—')}</div>
      <div style="margin-top:6px;">{sig_pill} {s_pill}</div>
    </div>
    <div style="text-align:right;">
      <div class="card-price">{price}</div>
      <div class="card-ts">{ts}</div>
    </div>
  </div>
  {ind_chips_html(ind, compact=False)}
</div>
""", unsafe_allow_html=True)

                    if summary:
                        st.markdown(f'<div class="ai-commentary"><div class="ai-label">🤖 AI Analysis</div>{summary}</div>', unsafe_allow_html=True)

                with right:
                    if action:
                        call = action.get("call") or "—"
                        conv = action.get("conviction") or "MEDIUM"
                        remarks = action.get("fm_remarks") or action.get("remarks") or ""
                        decision_at = fmt_ist(action.get("decision_at"))

                        st.markdown(f"""
**FM Decision**

{conviction_pill(conv)} &nbsp; **{call}**

Decided: {decision_at}
""", unsafe_allow_html=True)

                        if remarks:
                            st.markdown(f"""
<div class="ai-commentary">
  <div class="ai-label">💬 FM Rationale</div>
  {remarks}
</div>
""", unsafe_allow_html=True)

                        # Chart image
                        if action.get("has_chart"):
                            chart_data = api_get(f"/api/alerts/{alert_id}/chart")
                            if chart_data and chart_data.get("chart_image_b64"):
                                img_b64 = chart_data["chart_image_b64"]
                                st.markdown(f'<div class="chart-img-wrap"><img src="data:image/jpeg;base64,{img_b64}" /></div>', unsafe_allow_html=True)
                    else:
                        st.markdown("*No action taken yet.*")

                    # Delete button
                    if st.button("🗑 Delete Alert", key=f"del_{alert_id}"):
                        result = api_post(f"/api/alerts/{alert_id}/action", {"alert_id": alert_id, "decision": "DENIED"})
                        # Actually call delete endpoint
                        try:
                            requests.delete(f"{API_BASE}/api/alerts/{alert_id}", timeout=10)
                            st.success("Deleted.")
                            st.rerun()
                        except:
                            st.error("Delete failed.")


# ══════════════════════════════════════════════════════════
# TAB 4 — PERFORMANCE
# ══════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-header">Performance Tracker · Approved Alerts</div>', unsafe_allow_html=True)

    col_refresh, col_spacer = st.columns([1, 4])
    with col_refresh:
        if st.button("🔄 Refresh Prices", type="primary"):
            r = api_post("/api/performance/refresh", {})
            if r and not r.get("error"):
                st.success(f"Updated {r.get('updated_count', 0)} positions.")
            else:
                st.error("Refresh failed.")

    perf_data = api_get("/api/performance") or {}
    records = perf_data.get("performance", [])

    if not records:
        st.markdown('<div class="no-data"><div class="no-data-icon">📊</div>No performance data yet. Approve some alerts first.</div>', unsafe_allow_html=True)
    else:
        # Summary stats
        valid = [r for r in records if r.get("return_pct") is not None]
        if valid:
            avg_ret = sum(r["return_pct"] for r in valid) / len(valid)
            hit_rate = sum(1 for r in valid if r["return_pct"] > 0) / len(valid) * 100
            best = max(valid, key=lambda x: x["return_pct"])
            worst = min(valid, key=lambda x: x["return_pct"])

            s1, s2, s3, s4 = st.columns(4)
            with s1:
                color = "var(--bull)" if avg_ret >= 0 else "var(--bear)"
                st.markdown(f'<div class="stat-card"><div class="stat-value" style="color:{color}">{avg_ret:+.2f}%</div><div class="stat-label">Avg Return</div></div>', unsafe_allow_html=True)
            with s2:
                st.markdown(f'<div class="stat-card"><div class="stat-value">{hit_rate:.0f}%</div><div class="stat-label">Hit Rate</div></div>', unsafe_allow_html=True)
            with s3:
                st.markdown(f'<div class="stat-card"><div class="stat-value" style="color:var(--bull)">{best["return_pct"]:+.2f}%</div><div class="stat-label">Best: {best["ticker"]}</div></div>', unsafe_allow_html=True)
            with s4:
                st.markdown(f'<div class="stat-card"><div class="stat-value" style="color:var(--bear)">{worst["return_pct"]:+.2f}%</div><div class="stat-label">Worst: {worst["ticker"]}</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Build table
        rows = []
        for r in records:
            ret = r.get("return_pct")
            ref = r.get("reference_price")
            curr = r.get("current_price")
            dd = r.get("max_drawdown")
            rows.append({
                "ID": r.get("alert_id"),
                "Ticker": r.get("ticker", "—"),
                "Alert": (r.get("alert_name") or "—")[:30],
                "Call": r.get("action_call") or "—",
                "Conviction": r.get("conviction") or "—",
                "Alert Price": f"₹{float(ref):,.2f}" if ref else "—",
                "Current Price": f"₹{float(curr):,.2f}" if curr else "—",
                "Return %": ret,
                "Max DD%": dd,
                "Updated": (r.get("last_updated") or "—")[:10],
            })

        df = pd.DataFrame(rows)

        def color_ret(val):
            if val is None or not isinstance(val, (int, float)):
                return "color: gray"
            return f"color: {'#0A8A4E' if val >= 0 else '#D92B2B'}; font-weight: 600"

        def fmt_ret(val):
            if val is None or not isinstance(val, (int, float)):
                return "—"
            return f"{val:+.2f}%"

        df_display = df.copy()
        df_display["Return %"] = df_display["Return %"].apply(fmt_ret)
        df_display["Max DD%"] = df_display["Max DD%"].apply(lambda v: f"{v:.2f}%" if v is not None else "—")

        st.dataframe(
            df_display.drop(columns=["ID"]),
            use_container_width=True,
            hide_index=True,
        )


# ══════════════════════════════════════════════════════════
# TAB 5 — MARKET PULSE
# ══════════════════════════════════════════════════════════
with tab5:
    @st.fragment(run_every=60)
    def market_pulse():
        st.markdown('<div class="section-header">Market Pulse · NSE · BSE · Commodities · Currencies</div>', unsafe_allow_html=True)

        pulse_data = api_get("/api/market-pulse")

        if not pulse_data:
            st.warning("Unable to fetch market data. Check backend connectivity.")
            return

        indices = pulse_data.get("indices", [])
        updated_at = pulse_data.get("updated_at", "—")
        st.caption(f"Last updated: {updated_at}")

        # Group by category
        categories = {}
        for idx in indices:
            cat = idx.get("category", "Other")
            categories.setdefault(cat, []).append(idx)

        cat_order = ["NSE Broad Market", "NSE Sectoral", "BSE Indices", "Commodities", "Currency"]
        for cat in cat_order:
            items = categories.get(cat, [])
            if not items:
                continue

            st.markdown(f'<div class="section-header" style="margin-top:20px;">{cat}</div>', unsafe_allow_html=True)

            rows_html = ""
            for idx in items:
                name = idx.get("name", idx.get("ticker", "—"))
                price = idx.get("current_price")
                chg = idx.get("change_pct")
                high = idx.get("high")
                low = idx.get("low")
                prev_close = idx.get("prev_close")

                price_str = f"₹{float(price):,.2f}" if price else "—"
                high_str = f"₹{float(high):,.2f}" if high else "—"
                low_str = f"₹{float(low):,.2f}" if low else "—"
                prev_str = f"₹{float(prev_close):,.2f}" if prev_close else "—"

                if chg is not None:
                    chg_cls = "chg-pos" if chg > 0 else "chg-neg" if chg < 0 else "chg-neutral"
                    chg_arrow = "▲" if chg > 0 else "▼" if chg < 0 else "◆"
                    chg_str = f'<span class="{chg_cls}">{chg_arrow} {abs(chg):.2f}%</span>'
                else:
                    chg_str = '<span class="chg-neutral">—</span>'

                rows_html += f"""<tr>
  <td>{name}</td>
  <td>{price_str}</td>
  <td>{chg_str}</td>
  <td>{high_str}</td>
  <td>{low_str}</td>
  <td>{prev_str}</td>
</tr>"""

            st.markdown(f"""
<table class="pulse-table">
<thead><tr>
  <th>Index / Instrument</th>
  <th>Last Price</th>
  <th>Change %</th>
  <th>High</th>
  <th>Low</th>
  <th>Prev Close</th>
</tr></thead>
<tbody>{rows_html}</tbody>
</table>
""", unsafe_allow_html=True)

    market_pulse()
