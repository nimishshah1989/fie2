import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import os
import base64
import json
import streamlit.components.v1 as components

API_BASE = os.getenv("FIE_API_URL", "http://localhost:8000")

st.set_page_config(page_title="Jhaveri Intelligence", layout="wide", initial_sidebar_state="expanded")

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; }
    .stApp { background: #FAFBFC !important; }
    #MainMenu, footer { display: none !important; }
    .block-container { padding-top: 1.5rem !important; max-width: 1400px !important; }
    div[data-testid="stMetric"] {
        background: #FFFFFF; border: 1px solid #E8ECF1; border-radius: 8px;
        padding: 16px; box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }
    div[data-testid="stMetric"] label { font-size: 11px !important; color: #64748B !important; font-weight: 700 !important; text-transform: uppercase !important; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 22px !important; color: #0F172A !important; font-weight: 800 !important; }
    .empty-state { text-align: center; padding: 40px 20px; color: #94A3B8; }
    [data-testid="stVerticalBlockBorderWrapper"] { 
        padding: 16px !important; border-radius: 10px !important; 
        background: #FFFFFF !important; box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
        border-color: #E8ECF1 !important;
    }
    .stButton button { padding: 4px 12px !important; font-size: 13px !important; font-weight: 600 !important; height: auto !important; min-height: 32px !important; }
</style>
""", unsafe_allow_html=True)

# ─── Helpers ─────────────────────────────────────────────
def api_call(method, endpoint, data=None, params=None):
    try:
        url = f"{API_BASE}{endpoint}"
        if method == 'GET': r = requests.get(url, params=params, timeout=10)
        elif method == 'POST': r = requests.post(url, json=data, timeout=30)
        elif method == 'DELETE': r = requests.delete(url, timeout=10)
        else: return None
        if r.status_code in [200, 201]: return r.json()
    except Exception: pass
    return None

def fmt_price(val):
    if val is None or val == 0: return "—"
    try: return f"{float(val):,.2f}"
    except: return "—"

def fmt_ist(iso_str):
    if not iso_str: return "—"
    try:
        dt = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
        ist_dt = dt + timedelta(hours=5, minutes=30)
        return ist_dt.strftime("%d-%b %I:%M %p").lower()
    except: return str(iso_str)[:16]

def asset_pill(asset_class):
    a = str(asset_class).strip().upper()
    if a in ["NONE", "NULL", "", "—"]: a = "EQUITY"
    colors = {"COMMODITY": ("#FFFBEB","#B45309","#FDE68A"), "CURRENCY": ("#ECFDF5","#059669","#A7F3D0"),
              "INDEX": ("#F3E8FF","#7E22CE","#D8B4FE")}
    bg, tc, br = colors.get(a, ("#EFF6FF","#2563EB","#BFDBFE"))
    return f"<span style='background:{bg}; color:{tc}; border:1px solid {br}; padding:2px 7px; border-radius:5px; font-size:9px; font-weight:800; letter-spacing:0.5px;'>{a}</span>"

def signal_pill(direction):
    d = str(direction or "NEUTRAL").upper()
    if d == "BULLISH": return "<span style='color:#059669; background:#ECFDF5; border:1px solid #A7F3D0; padding:2px 7px; border-radius:5px; font-size:9px; font-weight:700;'>BULLISH</span>"
    if d == "BEARISH": return "<span style='color:#DC2626; background:#FEF2F2; border:1px solid #FECACA; padding:2px 7px; border-radius:5px; font-size:9px; font-weight:700;'>BEARISH</span>"
    return "<span style='color:#64748B; background:#F1F5F9; border:1px solid #E2E8F0; padding:2px 7px; border-radius:5px; font-size:9px; font-weight:700;'>NEUTRAL</span>"

def stat_pill(s):
    s = str(s or "PENDING").upper()
    if s == "PENDING": return "<span style='color:#B45309; background:#FFFBEB; border:1px solid #FDE68A; padding:2px 8px; border-radius:100px; font-size:9px; font-weight:700;'>PENDING</span>"
    if s == "APPROVED": return "<span style='color:#059669; background:#ECFDF5; border:1px solid #A7F3D0; padding:2px 8px; border-radius:100px; font-size:9px; font-weight:700;'>APPROVED</span>"
    return f"<span style='color:#DC2626; background:#FEF2F2; border:1px solid #FECACA; padding:2px 8px; border-radius:100px; font-size:9px; font-weight:700;'>{s}</span>"

def confluence_bar(bull, bear):
    try:
        b = int(bull or 0); s = int(bear or 0)
        total = max(b + s, 1)
        bp = b / 10 * 100; sp = s / 10 * 100
        return f"""<div style='display:flex; gap:2px; margin:4px 0;'>
            <div style='height:4px; width:{bp}%; background:#059669; border-radius:2px;'></div>
            <div style='height:4px; width:{sp}%; background:#DC2626; border-radius:2px;'></div>
            <div style='height:4px; flex:1; background:#E2E8F0; border-radius:2px;'></div>
        </div>
        <div style='display:flex; justify-content:space-between; font-size:9px; color:#94A3B8;'>
            <span>{b}/10 Bull</span><span>{s}/10 Bear</span>
        </div>"""
    except: return ""

def rsi_gauge(val):
    try:
        v = float(val)
        if v > 70: color, label = "#DC2626", "OB"
        elif v < 30: color, label = "#059669", "OS"
        else: color, label = "#64748B", ""
        return f"<span style='color:{color}; font-weight:700;'>{v:.0f}</span>{f' <span style=\"font-size:8px; color:{color};\">{label}</span>' if label else ''}"
    except: return "—"

def clean_placeholder(text):
    if not text: return ""
    t = str(text).strip()
    if "{{" in t or t.lower() in ("none", "null", ""): return "Manual Alert"
    return t

# ─── Sidebar ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""<div style='padding:12px 0 24px;'><div style='font-size:18px; font-weight:800; color:#FFFFFF !important;'>JHAVERI</div><div style='font-size:9px; color:#64748B !important; text-transform:uppercase; letter-spacing:2px;'>Intelligence Platform</div></div>""", unsafe_allow_html=True)
    page = st.radio("Nav", ["Command Center", "Trade Desk", "Portfolio Analytics", "Alert Database", "Integrations"], label_visibility="collapsed")
    st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)
    sc1, sc2 = st.columns(2)
    with sc1:
        if st.button("Sync", use_container_width=True): st.rerun()
    with sc2:
        auto = st.toggle("Auto", value=True, key="auto_refresh")
    ist_now = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime('%d-%b-%y %I:%M:%S %p')
    st.markdown(f"<div style='font-size:10px; color:#475569; margin-top:8px;'>Live &middot; {ist_now} IST</div>", unsafe_allow_html=True)

_should_auto_refresh = st.session_state.get("auto_refresh", True)

# ═══════════════════════════════════════════════════════════
# COMMAND CENTER — with rich indicator cards
# ═══════════════════════════════════════════════════════════
if page == "Command Center":
    st.markdown("<h1 style='margin-bottom:4px;'>Command Center</h1><p style='color:#64748B; font-size:13px; margin-top:0;'>Real-time signal feed with technical intelligence</p>", unsafe_allow_html=True)
    stats = api_call('GET', "/api/stats") or {}
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Alerts", stats.get("total_alerts", 0))
    c2.metric("Pending Queue", stats.get("pending", 0))
    now_ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
    c3.metric("Market Status", "OPEN" if (now_ist.weekday() < 5 and 9 <= now_ist.hour < 16) else "CLOSED")
    
    st.divider()
    sf = st.selectbox("Filter", ["PENDING", "All", "APPROVED", "DENIED"], label_visibility="collapsed")
    params = {"limit": 50}
    if sf != "All": params["status"] = sf
    data = api_call('GET', "/api/alerts", params=params)
    
    if not data or not data.get("alerts"):
        st.markdown("<div class='empty-state'>No signals found</div>", unsafe_allow_html=True)
    else:
        cols = st.columns(3)
        for i, al in enumerate(data["alerts"]):
            with cols[i % 3]:
                with st.container(border=True):
                    alert_nm = clean_placeholder(al.get("alert_name"))
                    tkr = str(al.get("ticker", "—")).strip()
                    ind = al.get("indicators") or {}
                    has_rich_data = bool(ind and ind.get("rsi") is not None)
                    
                    # Header row: asset pill + signal pill + time
                    tkr_display = f"<span style='font-size:11px; color:#475569; margin-left:6px;'>{tkr}</span>" if alert_nm.upper() != tkr.upper() else ""
                    interval_display = f"<span style='font-size:9px; color:#94A3B8; margin-left:4px;'>{al.get('interval','')}</span>" if al.get('interval') and al.get('interval') != '—' else ""
                    
                    st.markdown(f"""
                    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>
                        <div>{asset_pill(al.get('asset_class'))} {signal_pill(al.get('signal_direction'))}</div>
                        <div style='font-size:10px; color:#94A3B8;'>{fmt_ist(al.get('received_at'))}</div>
                    </div>
                    <div style='display:flex; justify-content:space-between; align-items:flex-end;'>
                        <div>
                            <div style='font-size:15px; font-weight:800; color:#0F172A;'>{alert_nm}{interval_display}</div>
                            {f"<div style='font-size:11px; color:#64748B;'>{tkr}</div>" if alert_nm.upper() != tkr.upper() else ""}
                        </div>
                        <div style='text-align:right;'>
                            <div style='font-size:16px; font-weight:800; color:#0F172A;'>{fmt_price(al.get("price_at_alert"))}</div>
                            <div>{stat_pill(al.get('status'))}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Rich indicator strip (only for FIE Pine payloads)
                    if has_rich_data:
                        rsi_html = rsi_gauge(ind.get("rsi"))
                        st_dir = ind.get("supertrend_dir", "")
                        st_color = "#059669" if st_dir == "BULLISH" else "#DC2626" if st_dir == "BEARISH" else "#94A3B8"
                        htf = ind.get("htf_trend", "")
                        htf_color = "#059669" if htf == "BULLISH" else "#DC2626" if htf == "BEARISH" else "#94A3B8"
                        adx_val = ind.get("adx")
                        adx_str = f"{float(adx_val):.0f}" if adx_val else "—"
                        
                        st.markdown(f"""
                        <div style='background:#F8FAFC; border-radius:6px; padding:8px 10px; margin-top:8px;'>
                            <div style='display:flex; justify-content:space-between; font-size:10px; margin-bottom:6px;'>
                                <div><span style='color:#94A3B8;'>RSI</span> {rsi_html}</div>
                                <div><span style='color:#94A3B8;'>ADX</span> <span style='font-weight:700;'>{adx_str}</span></div>
                                <div><span style='color:#94A3B8;'>ST</span> <span style='color:{st_color}; font-weight:700;'>{st_dir[:4] if st_dir else "—"}</span></div>
                                <div><span style='color:#94A3B8;'>HTF</span> <span style='color:{htf_color}; font-weight:700;'>{htf[:4] if htf else "—"}</span></div>
                            </div>
                            {confluence_bar(ind.get("confluence_bull_score"), ind.get("confluence_bear_score"))}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # MA alignment + candle pattern
                        ma_a = ind.get("ma_alignment", "")
                        cp = ind.get("candle_pattern", "")
                        extras = []
                        if ma_a and ma_a != "MIXED": extras.append(f"MA: {ma_a}")
                        if cp and cp != "NONE": extras.append(f"Pattern: {cp}")
                        vr = ind.get("vol_ratio")
                        if vr:
                            try:
                                vrf = float(vr)
                                if vrf > 1.5: extras.append(f"Vol: {vrf:.1f}x")
                            except: pass
                        if extras:
                            st.markdown(f"<div style='font-size:9px; color:#64748B; margin-top:4px;'>{' &middot; '.join(extras)}</div>", unsafe_allow_html=True)
                    else:
                        # Legacy card — show alert message
                        msg = clean_placeholder(al.get("alert_message"))
                        if msg and "{{" not in msg and msg != "Manual Alert":
                            st.markdown(f"<div style='font-size:11px; color:#475569; padding:8px; background:#F8FAFC; border-radius:6px; margin-top:8px;'>{msg[:200]}</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# PORTFOLIO ANALYTICS
# ═══════════════════════════════════════════════════════════
elif page == "Portfolio Analytics":
    st.markdown("<h1>Portfolio Analytics</h1>", unsafe_allow_html=True)
    if st.button("Sync Prices", type="primary"):
        api_call('POST', "/api/performance/refresh")
        st.rerun()
    data = api_call('GET', "/api/performance")
    if data and data.get("performance"):
        perf = data["performance"]
        n = max(len(perf), 1)
        rets = [p.get("return_pct", 0.0) or 0.0 for p in perf]
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Positions", len(perf))
        m2.metric("Avg Return", f"{sum(rets)/n:+.2f}%")
        m3.metric("Win Rate", f"{sum(1 for r in rets if r > 0)/n*100:.0f}%")
        m4.metric("Best/Worst", f"{max(rets):+.1f}% / {min(rets):+.1f}%")
        st.divider()
        cols = st.columns(3)
        for i, p in enumerate(perf):
            rp = p.get("return_pct", 0.0) or 0.0
            color = "#059669" if rp > 0 else "#DC2626"
            dd = p.get("max_drawdown", 0.0) or 0.0
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"""
                    <div style='display:flex; justify-content:space-between;'>
                        <div style='font-size:16px; font-weight:800;'>{p.get('ticker','—')}</div>
                        <div style='font-size:18px; font-weight:800; color:{color};'>{rp:+.2f}%</div>
                    </div>
                    <div style='display:flex; justify-content:space-between; background:#F8FAFC; padding:8px; border-radius:6px; margin:10px 0;'>
                        <div><div style='font-size:9px; color:#94A3B8;'>ENTRY</div><div style='font-size:13px;'>{fmt_price(p.get('reference_price'))}</div></div>
                        <div style='text-align:right;'><div style='font-size:9px; color:#94A3B8;'>CURRENT</div><div style='font-size:13px;'>{fmt_price(p.get('current_price'))}</div></div>
                    </div>
                    <div style='font-size:10px; color:#64748B;'>Max DD: <span style='color:#DC2626;'>{dd:.2f}%</span></div>
                    """, unsafe_allow_html=True)
    else:
        st.markdown("<div class='empty-state'>No active positions</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# ALERT DATABASE
# ═══════════════════════════════════════════════════════════
elif page == "Alert Database":
    st.markdown("<h1>Alert Database</h1>", unsafe_allow_html=True)
    m = api_call('GET', "/api/master", params={"limit": 100})
    if m and m.get("alerts"):
        cols = st.columns(3)
        for i, a in enumerate(m["alerts"]):
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"""
                    <div style='display:flex; justify-content:space-between;'>
                        <div style='font-size:16px; font-weight:800;'>{clean_placeholder(a.get('alert_name'))}</div>
                        {stat_pill(a.get('status'))}
                    </div>
                    <div style='font-size:13px; color:#334155; margin:5px 0;'>{a.get('ticker','—')}</div>
                    <div style='font-size:12px; margin-bottom:10px;'>Price: <b>{fmt_price(a.get('price_at_alert'))}</b></div>
                    """, unsafe_allow_html=True)
                    if st.button("Delete", key=f"del_{a['id']}", use_container_width=True):
                        api_call('DELETE', f"/api/alerts/{a['id']}")
                        st.rerun()

elif page == "Trade Desk":
    st.info("Visit Command Center to review pending alerts.")
elif page == "Integrations":
    st.code(f"Webhook URL: {API_BASE}/webhook/tradingview")
    st.markdown("### Pine Script Setup")
    st.markdown("Use the **FIE Signal Engine v1.0** Pine Script indicator. It automatically sends rich JSON payloads with 25+ indicators via webhook. No manual message formatting needed.")

# ─── AUTO REFRESH ──────────────────────────────────────────
if _should_auto_refresh:
    components.html("""<script>
        window.parent.document.querySelectorAll('button').forEach(btn => {
            if (btn.innerText.includes('Sync')) { setTimeout(() => btn.click(), 2000); }
        });
    </script>""", height=0)
