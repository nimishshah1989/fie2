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

# ─── SAFE CSS ─────────────────────────────────────────────────
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
    try: return f"₹{float(val):,.2f}"
    except: return "—"

def fmt_ist(iso_str):
    if not iso_str: return "—"
    try:
        dt = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
        ist_dt = dt + timedelta(hours=5, minutes=30)
        return ist_dt.strftime("%d-%b-%y %I:%M %p").lower()
    except: return str(iso_str)[:16]

def asset_pill(asset_class):
    a = str(asset_class).strip().upper()
    if a in ["NONE", "NULL", "", "—"]: a = "EQUITY"
    if a == "COMMODITY": bg, tc, br = "#FFFBEB", "#B45309", "#FDE68A"
    elif a == "CURRENCY": bg, tc, br = "#ECFDF5", "#059669", "#A7F3D0"
    elif a == "INDEX": bg, tc, br = "#F3E8FF", "#7E22CE", "#D8B4FE"
    else: bg, tc, br = "#EFF6FF", "#2563EB", "#BFDBFE"
    return f"<span style='background:{bg}; color:{tc}; border:1px solid {br}; padding:3px 8px; border-radius:6px; font-size:9px; font-weight:800; letter-spacing:0.5px;'>{a}</span>"

def stat_pill(s):
    s = str(s or "PENDING").upper()
    if s == "PENDING": return "<span style='color:#B45309; background:#FFFBEB; border:1px solid #FDE68A; padding:2px 8px; border-radius:100px; font-size:9px; font-weight:700;'>PENDING</span>"
    if s == "APPROVED": return "<span style='color:#059669; background:#ECFDF5; border:1px solid #A7F3D0; padding:2px 8px; border-radius:100px; font-size:9px; font-weight:700;'>APPROVED</span>"
    return f"<span style='color:#DC2626; background:#FEF2F2; border:1px solid #FECACA; padding:2px 8px; border-radius:100px; font-size:9px; font-weight:700;'>{s}</span>"

def clean_placeholder(text):
    if not text: return ""
    t = str(text).strip()
    if "{{" in t or t.lower() in ["none", "null", ""]: return "Manual Alert"
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
# COMMAND CENTER
# ═══════════════════════════════════════════════════════════
if page == "Command Center":
    st.markdown("<h1>Command Center</h1>", unsafe_allow_html=True)
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
        st.markdown("<div class='empty-state'>📡 No signals found</div>", unsafe_allow_html=True)
    else:
        cols = st.columns(3)
        for i, al in enumerate(data["alerts"]):
            with cols[i % 3]:
                with st.container(border=True):
                    alert_nm = clean_placeholder(al.get("alert_name"))
                    tkr = str(al.get("ticker", "—")).strip()
                    tkr_html = f"<div style='font-size:12px; color:#475569;'>{tkr}</div>" if alert_nm.upper() != tkr.upper() else ""
                    st.markdown(f"""
                    <div style='display:flex; justify-content:space-between; margin-bottom:10px;'>
                        {asset_pill(al.get('asset_class'))}
                        <div style='font-size:10px; color:#64748B;'>{fmt_ist(al.get('received_at'))}</div>
                    </div>
                    <div style='display:flex; justify-content:space-between; align-items:flex-end;'>
                        <div><div style='font-size:16px; font-weight:800;'>{alert_nm}</div>{tkr_html}</div>
                        <div style='text-align:right;'><div style='font-size:16px; font-weight:800;'>{fmt_price(al.get("price_at_alert"))}</div><div>{stat_pill(al.get('status'))}</div></div>
                    </div>
                    """, unsafe_allow_html=True)
                    msg = clean_placeholder(al.get("alert_message"))
                    if msg and "{{" not in msg:
                        st.markdown(f"<div style='font-size:11px; color:#475569; padding:8px; background:#F8FAFC; border-radius:6px; margin-top:8px;'>{msg}</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# PORTFOLIO ANALYTICS
# ═══════════════════════════════════════════════════════════
elif page == "Portfolio Analytics":
    st.markdown("<h1>Portfolio Analytics</h1>", unsafe_allow_html=True)
    if st.button("🔄 Sync Prices", type="primary"):
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
        st.markdown("<div class='empty-state'>📊 No active positions</div>", unsafe_allow_html=True)

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
                    if st.button("🗑️ Delete", key=f"del_{a['id']}", use_container_width=True):
                        api_call('DELETE', f"/api/alerts/{a['id']}")
                        st.rerun()

# ─── Default Pages ───────────────────────────────────────────
elif page == "Trade Desk":
    st.info("Visit Command Center to review pending alerts.")
elif page == "Integrations":
    st.code(f"Webhook URL: {API_BASE}/webhook/tradingview")

# ─── AUTO REFRESH (Targeted clicker) ──────────────────────────
if _should_auto_refresh:
    components.html("""
        <script>
        window.parent.document.querySelectorAll('button').forEach(btn => {
            if (btn.innerText.includes('Sync')) {
                setTimeout(() => btn.click(), 2000);
            }
        });
        </script>
        """, height=0)
