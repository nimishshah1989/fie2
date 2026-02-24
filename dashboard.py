import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import os
import base64
import json

API_BASE = os.getenv("FIE_API_URL", "http://localhost:8000")

# Native sidebar config, no CSS hiding hacks.
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
    .stButton button { padding: 4px 12px !important; font-size: 13px !important; font-weight: 600 !important; }
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

def stat_pill(s):
    s = str(s or "PENDING").upper()
    if s == "PENDING": return "<span style='color:#B45309; background:#FFFBEB; border:1px solid #FDE68A; padding:2px 8px; border-radius:100px; font-size:9px; font-weight:700;'>PENDING</span>"
    if s == "APPROVED": return "<span style='color:#059669; background:#ECFDF5; border:1px solid #A7F3D0; padding:2px 8px; border-radius:100px; font-size:9px; font-weight:700;'>APPROVED</span>"
    return f"<span style='color:#DC2626; background:#FEF2F2; border:1px solid #FECACA; padding:2px 8px; border-radius:100px; font-size:9px; font-weight:700;'>{s}</span>"

def clean_placeholder(text):
    if not text: return ""
    t = str(text).strip()
    if "{{" in t or t in ["None", "null", ""]: return "Manual Alert"
    return t


# ─── Sidebar ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""<div style='padding:12px 0 24px;'>
        <div style='font-size:18px; font-weight:800; color:#0F172A !important; letter-spacing:-0.3px;'>JHAVERI</div>
        <div style='font-size:9px; color:#64748B !important; text-transform:uppercase; letter-spacing:2px; margin-top:2px;'>Intelligence Platform</div>
    </div>""", unsafe_allow_html=True)
    page = st.radio("Nav", ["Command Center", "Trade Desk", "Portfolio Analytics", "Alert Database", "Integrations"], label_visibility="collapsed")
    st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)
    sc1, sc2 = st.columns(2)
    with sc1:
        if st.button("Sync", use_container_width=True): st.rerun()
    with sc2:
        auto = st.toggle("Auto", value=False, key="auto_refresh")

_should_auto_refresh = st.session_state.get("auto_refresh", False) and page in ["Command Center", "Trade Desk", "Portfolio Analytics"]

# ═══════════════════════════════════════════════════════════
# COMMAND CENTER
# ═══════════════════════════════════════════════════════════
if page == "Command Center":
    st.markdown("<h1 style='color:#0F172A; font-size:22px; font-weight:800; margin-bottom:4px;'>Command Center</h1>", unsafe_allow_html=True)
    stats = api_call('GET', "/api/stats") or {}
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Alerts", stats.get("total_alerts", 0))
    c2.metric("Pending Queue", stats.get("pending", 0))
    now = datetime.now()
    c3.metric("Market Status", "OPEN" if (now.weekday() < 5 and 9 <= now.hour < 16) else "CLOSED")
    
    st.markdown("<hr/>", unsafe_allow_html=True)
    fc1, _, _, _ = st.columns([1, 1, 1, 2])
    with fc1:
        sf = st.selectbox("Filter", ["PENDING", "All", "APPROVED", "DENIED"], label_visibility="collapsed")
    
    params = {"limit": 50}
    if sf != "All": params["status"] = sf
    data = api_call('GET', "/api/alerts", params=params)
    
    if not data or not data.get("alerts"):
        st.markdown("<div class='empty-state'><div style='font-size:40px; opacity:0.3;'>📡</div><p style='font-size:14px;margin-top:12px;'>No signals found</p></div>", unsafe_allow_html=True)
    else:
        cols = st.columns(3)
        for i, al in enumerate(data["alerts"]):
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"""
                    <div style='display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;'>
                        <div style='font-size:16px; font-weight:800; color:#0F172A;'>{clean_placeholder(al.get("alert_name"))}</div>
                        {stat_pill(al.get('status'))}
                    </div>
                    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;'>
                        <div style='font-size:13px; font-weight:600; color:#475569;'>{al.get("ticker", "—")}</div>
                        <div style='font-size:10px; color:#64748B; font-weight:700;'>{fmt_ist(al.get('received_at'))}</div>
                    </div>
                    <div style='font-size:18px; font-weight:800; color:#0F172A;'>{fmt_price(al.get("price_at_alert"))}</div>
                    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# TRADE DESK
# ═══════════════════════════════════════════════════════════
elif page == "Trade Desk":
    st.markdown("<h1 style='color:#0F172A; font-size:22px; font-weight:800; margin-bottom:4px;'>Trade Desk</h1>", unsafe_allow_html=True)
    pending_data = api_call('GET', "/api/alerts", params={"status": "PENDING", "limit": 30})
    pending = pending_data.get("alerts", []) if pending_data else []
    
    if not pending:
        st.markdown("<div style='background:#F0FDF4; border:1px solid #BBF7D0; border-radius:8px; padding:20px; text-align:center;'><span style='color:#166534; font-weight:600;'>✓ Queue is clear</span></div>", unsafe_allow_html=True)
    else:
        cols = st.columns(3)
        for i, al in enumerate(pending):
            aid = al["id"]
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"""
                    <div style='display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;'>
                        <div style='font-size:16px; font-weight:800; color:#0F172A;'>{clean_placeholder(al.get('alert_name'))}</div>
                        <div style='font-size:10px; color:#64748B; font-weight:700;'>{fmt_ist(al.get('received_at'))}</div>
                    </div>
                    <div style='font-size:13px; font-weight:600; color:#475569; margin-bottom:12px;'>{al.get('ticker','—')}</div>
                    <div style='font-size:18px; font-weight:800; color:#0F172A; margin-bottom:12px;'>{fmt_price(al.get('price_at_alert'))}</div>
                    """, unsafe_allow_html=True)
                    
                    approve_key = f"approve_{aid}"
                    if approve_key not in st.session_state: st.session_state[approve_key] = False
                    
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("✓ Approve", key=f"ab{aid}", type="primary"): st.session_state[approve_key] = True
                    with b2:
                        if st.button("✗ Reject", key=f"db{aid}"):
                            api_call('POST', f"/api/alerts/{aid}/action", {"alert_id":aid,"decision":"DENIED"})
                            st.rerun()
                    
                    if st.session_state.get(approve_key, False):
                        st.divider()
                        call = st.selectbox("Call", ["BUY","SELL","HOLD"], key=f"call{aid}", label_visibility="collapsed")
                        conv = st.select_slider("Conviction", ["LOW","MEDIUM","HIGH"], value="MEDIUM", key=f"conv{aid}", label_visibility="collapsed")
                        cmt = st.text_area("Remarks", placeholder="Rationale...", key=f"cmt{aid}", height=68, label_visibility="collapsed")
                        sc1, sc2 = st.columns(2)
                        with sc1:
                            if st.button("Submit", key=f"sub{aid}", type="primary"):
                                api_call('POST', f"/api/alerts/{aid}/action", {
                                    "alert_id": aid, "decision": "APPROVED", "primary_call": call, "conviction": conv, "fm_rationale_text": cmt if cmt else None
                                })
                                st.session_state[approve_key] = False
                                st.rerun()
                        with sc2:
                            if st.button("Cancel", key=f"can{aid}"):
                                st.session_state[approve_key] = False
                                st.rerun()

# ═══════════════════════════════════════════════════════════
# PORTFOLIO ANALYTICS (FIXED CRASH)
# ═══════════════════════════════════════════════════════════
elif page == "Portfolio Analytics":
    st.markdown("<h1 style='color:#0F172A; font-size:22px; font-weight:800; margin-bottom:4px;'>Portfolio Analytics</h1>", unsafe_allow_html=True)
    cr, _ = st.columns([1, 5])
    with cr:
        if st.button("🔄 Sync Prices", type="primary", use_container_width=True):
            api_call('POST', "/api/performance/refresh")
            st.rerun()
    
    data = api_call('GET', "/api/performance")
    if data and data.get("performance"):
        perf = data["performance"]
        n = len(perf)
        rets = [p.get("return_pct", 0.0) or 0.0 for p in perf]
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Positions", n)
        m2.metric("Avg Return", f"{sum(rets)/max(n,1):+.2f}%")
        m3.metric("Win Rate", f"{sum(1 for r in rets if r > 0)/max(n,1)*100:.0f}%")
        m4.metric("Best / Worst", f"{max(rets) if rets else 0:+.1f}% / {min(rets) if rets else 0:+.1f}%")
        
        st.markdown("<hr/>", unsafe_allow_html=True)
        cols = st.columns(3)
        for i, p in enumerate(perf):
            rp = p.get("return_pct")
            rc = "#059669" if rp and rp > 0 else "#DC2626" if rp and rp < 0 else "#64748B"
            
            # 🔥 BULLETPROOF FIX FOR THE MAX DRAWDOWN CRASH SEEN IN YOUR SCREENSHOT 🔥
            dd_raw = p.get("max_drawdown")
            if dd_raw in [None, "", "null", "None"]:
                dd_val = "—"
            else:
                try: dd_val = f"{float(dd_raw):.2f}%"
                except: dd_val = "—"
                
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"""
                    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;'>
                        <div style='font-size:16px; font-weight:800; color:#0F172A;'>{p.get('ticker','—')}</div>
                        <div style='font-size:18px; font-weight:800; color:{rc};'>{f"{rp:+.2f}%" if rp is not None else "—"}</div>
                    </div>
                    <div style='display:flex; justify-content:space-between; align-items:center; background:#F8FAFC; padding:8px 12px; border-radius:6px; border:1px solid #E2E8F0; margin-bottom:10px;'>
                        <div><div style='font-size:9px; color:#94A3B8; text-transform:uppercase;'>Entry</div><div style='font-size:13px; font-weight:700;'>{fmt_price(p.get('reference_price'))}</div></div>
                        <div><div style='font-size:9px; color:#94A3B8; text-transform:uppercase; text-align:right;'>Current</div><div style='font-size:13px; font-weight:700;'>{fmt_price(p.get('current_price'))}</div></div>
                    </div>
                    <div style='font-size:10px; color:#64748B; font-weight:600;'>Max DD: <span style='color:#DC2626;'>{dd_val}</span></div>
                    """, unsafe_allow_html=True)
    else:
        st.markdown("<div class='empty-state'><div style='font-size:40px; opacity:0.3;'>📊</div><p style='font-size:14px;margin-top:12px;'>No active positions</p></div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# ALERT DATABASE
# ═══════════════════════════════════════════════════════════
elif page == "Alert Database":
    st.markdown("<h1 style='color:#0F172A; font-size:22px; font-weight:800; margin-bottom:4px;'>Alert Database</h1>", unsafe_allow_html=True)
    m = api_call('GET', "/api/master", params={"limit": 100})
    if m and m.get("alerts"):
        cols = st.columns(3)
        for i, a in enumerate(m["alerts"]):
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"""
                    <div style='display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px;'>
                        <div style='font-size:16px; font-weight:800;'>{clean_placeholder(a.get('alert_name'))}</div>
                        {stat_pill(a.get('status'))}
                    </div>
                    <div style='font-size:13px; font-weight:700; color:#334155;'>{a.get('ticker','—')}</div>
                    <div style='font-size:12px; color:#64748B; font-weight:600; margin-bottom:16px;'>Price: <span style='color:#0F172A;'>{fmt_price(a.get('price_at_alert'))}</span></div>
                    """, unsafe_allow_html=True)
                    if st.button("🗑️ Delete", key=f"del_{a['id']}"):
                        api_call('DELETE', f"/api/alerts/{a['id']}")
                        st.rerun()

# ═══════════════════════════════════════════════════════════
# INTEGRATIONS
# ═══════════════════════════════════════════════════════════
elif page == "Integrations":
    st.markdown("<h1 style='color:#0F172A; font-size:22px; font-weight:800; margin-bottom:4px;'>Integrations</h1>", unsafe_allow_html=True)
    st.markdown(f"<div style='background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:16px; font-family:monospace; font-size:13px;'>POST <b>{API_BASE}/webhook/tradingview</b></div>", unsafe_allow_html=True)
    
    st.markdown("<br>### 🧪 Test Connection", unsafe_allow_html=True)
    test_json = json.dumps({"ticker": "RELIANCE", "close": "2950.50", "alert_name": "System Health Test"})
    if st.button("🚀 Fire Test Webhook", type="primary"):
        r = api_call('POST', "/webhook/tradingview", data=json.loads(test_json))
        st.success("Test sent!") if r and r.get("success") else st.error("Failed")

if _should_auto_refresh:
    time.sleep(5)
    st.rerun()
