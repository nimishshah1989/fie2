import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import os
import base64
import json

API_BASE = os.getenv("FIE_API_URL", "http://localhost:8000")

st.set_page_config(page_title="Jhaveri Intelligence", layout="wide", initial_sidebar_state="expanded")

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

# ─── CSS ─────────────────────────────────────────────────
# All dangerous header/sidebar hiding CSS has been removed. 
# Streamlit will handle its native navigation safely.
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    * { font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important; }
    code, pre, .stCode { font-family: 'JetBrains Mono', monospace !important; }
    .stApp { background: #FAFBFC !important; }
    #MainMenu, footer { display: none !important; }
    
    .block-container { padding-top: 1.5rem !important; max-width: 1400px !important; }
    
    /* Metrics and Cards */
    div[data-testid="stMetric"] {
        background: #FFFFFF; border: 1px solid #E8ECF1; border-radius: 8px;
        padding: 16px; box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }
    div[data-testid="stMetric"] label { font-size: 11px !important; color: #64748B !important; font-weight: 700 !important; text-transform: uppercase !important; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 22px !important; color: #0F172A !important; font-weight: 800 !important; }
    h1 { color: #0F172A !important; font-size: 20px !important; font-weight: 800 !important; margin-bottom: 2px !important; }
    h3 { color: #1E293B !important; font-size: 14px !important; font-weight: 700 !important; margin-bottom: 16px !important; }
    .divider { border-top: 1px solid #E2E8F0; margin: 24px 0; }
    .empty-state { text-align: center; padding: 40px 20px; color: #94A3B8; }
    .refresh-dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #22C55E; margin-right: 6px; animation: pulse 2s infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
    
    /* Native container tightening */
    [data-testid="stVerticalBlockBorderWrapper"] { padding: 16px !important; border-radius: 10px !important; background: #FFFFFF !important; box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important; }
    [data-testid="stVerticalBlockBorderWrapper"]:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.06) !important; border-color: #CBD5E1 !important; }

    /* Make buttons neater and smaller */
    .stButton button {
        padding: 4px 12px !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        height: auto !important;
        min-height: 32px !important;
    }
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

def fmt_vol(val):
    if val is None or val == 0: return "—"
    try:
        v = float(val)
        if v >= 1e9: return f"{v/1e9:.1f}B"
        if v >= 1e7: return f"{v/1e7:.1f}Cr"
        if v >= 1e5: return f"{v/1e5:.1f}L"
        if v >= 1e3: return f"{v/1e3:.0f}K"
        return f"{v:,.0f}"
    except: return "—"

def asset_pill(asset_class):
    a = str(asset_class or "EQUITY").upper()
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

def ret_color(v):
    if v is None: return "#64748B"
    return "#059669" if v > 0 else "#DC2626" if v < 0 else "#64748B"

def clean_placeholder(text):
    if not text: return ""
    t = str(text).strip()
    invalid_names = ["{{strategy.order.comment}}", "{{alert_name}}", "alert_name", "None", "null", ""]
    if t in invalid_names:
        return "Manual Alert"
    return t


# ─── Sidebar ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""<div style='padding:12px 0 36px;'>
        <div style='font-size:18px; font-weight:800; color:#FFFFFF !important; letter-spacing:-0.3px;'>JHAVERI</div>
        <div style='font-size:9px; color:#64748B !important; text-transform:uppercase; letter-spacing:2px; margin-top:2px;'>Intelligence Platform</div>
    </div>""", unsafe_allow_html=True)
    page = st.radio("Nav", ["Command Center", "Trade Desk", "Portfolio Analytics", "Alert Database", "Integrations"], label_visibility="collapsed")
    st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)
    sc1, sc2 = st.columns(2)
    with sc1:
        if st.button("Sync", use_container_width=True): st.rerun()
    with sc2:
        auto = st.toggle("Auto", value=True, key="auto_refresh")
    st.markdown(f"<div style='font-size:10px; color:#475569; margin-top:8px;'><span class='refresh-dot'></span>Live · {datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

_should_auto_refresh = st.session_state.get("auto_refresh", True) and page in ["Command Center", "Portfolio Analytics"]


# ═══════════════════════════════════════════════════════════
# COMMAND CENTER
# ═══════════════════════════════════════════════════════════
if page == "Command Center":
    st.markdown("<h1>Command Center</h1><p style='color:#64748B; font-size:13px; margin-bottom:20px;'>Real-time signal feed</p>", unsafe_allow_html=True)
    stats = api_call('GET', "/api/stats") or {}
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Alerts", stats.get("total_alerts", 0))
    c2.metric("Pending Queue", stats.get("pending", 0))
    now = datetime.now()
    c3.metric("Market Status", "OPEN" if (now.weekday() < 5 and 9 <= now.hour < 16) else "CLOSED")
    
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    
    fc1, _, _, _ = st.columns([1, 1, 1, 2])
    with fc1:
        sf = st.selectbox("Filter", ["PENDING", "All", "APPROVED", "DENIED"], label_visibility="collapsed", key="cf")
    
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
                    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;'>
                        {asset_pill(al.get('asset_class'))}
                        <div style='font-size:11px; color:#64748B; font-weight:700;'>{fmt_ist(al.get('received_at'))}</div>
                    </div>
                    <div style='display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:12px;'>
                        <div>
                            <div style='font-size:16px; font-weight:800; color:#0F172A;'>{clean_placeholder(al.get("alert_name", "Alert"))}</div>
                            <div style='font-size:12px; font-weight:600; color:#475569;'>{al.get("ticker", "—")}</div>
                        </div>
                        <div style='text-align:right;'>
                            <div style='font-size:16px; font-weight:800; color:#0F172A;'>{fmt_price(al.get("price_at_alert"))}</div>
                            <div style='margin-top:4px;'>{stat_pill(al.get('status'))}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    msg = al.get("alert_message") or ""
                    if msg:
                        # Safely replace HTML tags so literal JSON doesn't break the layout
                        safe_msg = str(msg).replace('<', '&lt;').replace('>', '&gt;')
                        st.markdown(f"<div style='font-size:11px; color:#475569; padding:8px 10px; background:#F8FAFC; border-radius:6px; border:1px solid #E2E8F0; line-height:1.4; max-height:80px; overflow-y:auto; white-space:pre-wrap; font-family:monospace;'>{safe_msg}</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# TRADE DESK
# ═══════════════════════════════════════════════════════════
elif page == "Trade Desk":
    st.markdown("<h1>Trade Desk</h1><p style='color:#64748B; font-size:13px; margin-bottom:24px;'>Review and record rationale for each alert</p>", unsafe_allow_html=True)
    st.markdown("### Pending Execution Queue")
    
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
                    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;'>
                        {asset_pill(al.get('asset_class'))}
                        <div style='font-size:11px; color:#64748B; font-weight:700;'>{fmt_ist(al.get('received_at'))}</div>
                    </div>
                    <div style='display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:14px;'>
                        <div>
                            <div style='font-size:16px; font-weight:800; color:#0F172A;'>{clean_placeholder(al.get('alert_name','Signal'))}</div>
                            <div style='font-size:12px; font-weight:600; color:#475569;'>{al.get('ticker','—')} &middot; Vol: {fmt_vol(al.get('volume'))}</div>
                        </div>
                        <div style='text-align:right;'>
                            <div style='font-size:16px; font-weight:800; color:#0F172A;'>{fmt_price(al.get('price_at_alert'))}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    approve_key = f"approve_{aid}"
                    if approve_key not in st.session_state:
                        st.session_state[approve_key] = False
                    
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("✓ Approve", key=f"ab{aid}", type="primary"):
                            st.session_state[approve_key] = True
                    with b2:
                        if st.button("✗ Reject", key=f"db{aid}"):
                            api_call('POST', f"/api/alerts/{aid}/action", {"alert_id":aid,"decision":"DENIED"})
                            st.rerun()
                    
                    if st.session_state.get(approve_key, False):
                        st.divider()
                        call = st.selectbox("Call", ["BUY","SELL","HOLD","STRONG_BUY","STRONG_SELL"], key=f"call{aid}", label_visibility="collapsed")
                        conv = st.select_slider("Conviction", ["LOW","MEDIUM","HIGH"], value="MEDIUM", key=f"conv{aid}", label_visibility="collapsed")
                        commentary = st.text_area("Remarks", placeholder="Rationale...", key=f"cmt{aid}", height=68, label_visibility="collapsed")
                        
                        chart_file = st.file_uploader("Attach Chart (Optional)", type=["png","jpg","jpeg"], key=f"ch{aid}", label_visibility="collapsed")
                        cb64 = None
                        if chart_file:
                            cb64 = base64.b64encode(chart_file.read()).decode('utf-8')
                            st.image(chart_file, caption="Preview", width=150)
                        
                        sc1, sc2 = st.columns(2)
                        with sc1:
                            if st.button("Submit", key=f"sub{aid}", type="primary"):
                                api_call('POST', f"/api/alerts/{aid}/action", {
                                    "alert_id": aid, "decision": "APPROVED",
                                    "primary_call": call, "conviction": conv,
                                    "fm_rationale_text": commentary if commentary else None,
                                    "chart_image_b64": cb64
                                })
                                st.session_state[approve_key] = False
                                st.rerun()
                        with sc2:
                            if st.button("Cancel", key=f"can{aid}"):
                                st.session_state[approve_key] = False
                                st.rerun()
    
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.markdown("### Recent Decisions")
    hist = api_call('GET', "/api/alerts", params={"limit": 12})
    if hist and hist.get("alerts"):
        r_cols = st.columns(3)
        rc_list = [x for x in hist["alerts"] if x.get("status") in ("APPROVED","DENIED")][:12]
        
        for i, a in enumerate(rc_list):
            act = a.get("action") or {}
            with r_cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"""
                    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>
                        <div style='font-size:14px; font-weight:800; color:#0F172A;'>{clean_placeholder(a.get('alert_name','—'))}</div>
                        {stat_pill(a.get('status'))}
                    </div>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <div style='font-size:12px; font-weight:600; color:#334155;'>{a.get('ticker','—')} &middot; <span style='color:#0F172A;'>{act.get('call','—')}</span></div>
                        <div style='font-size:10px; color:#94A3B8; font-weight:700;'>{fmt_ist(act.get('decision_at') or a.get('received_at'))}</div>
                    </div>
                    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# PORTFOLIO ANALYTICS
# ═══════════════════════════════════════════════════════════
elif page == "Portfolio Analytics":
    st.markdown("<h1>Portfolio Analytics</h1><p style='color:#64748B; font-size:13px; margin-bottom:24px;'>Live performance of approved positions</p>", unsafe_allow_html=True)
    cr, _ = st.columns([1, 5])
    with cr:
        if st.button("🔄 Sync Prices", type="primary", use_container_width=True):
            with st.spinner("Fetching live prices..."): result = api_call('POST', "/api/performance/refresh")
            if result: st.toast(f"Updated {result.get('updated_count',0)} positions")
            st.rerun()
    
    data = api_call('GET', "/api/performance")
    if data and data.get("performance"):
        perf = data["performance"]
        n = len(perf)
        rets = [p.get("return_pct", 0.0) or 0.0 for p in perf]
        avg = sum(rets)/max(n,1)
        wins = sum(1 for r in rets if r > 0)
        
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Positions", n)
        m2.metric("Avg Return", f"{avg:+.2f}%")
        m3.metric("Win Rate", f"{wins/max(n,1)*100:.0f}%")
        
        best_ret = max(rets) if rets else 0.0
        worst_ret = min(rets) if rets else 0.0
        m4.metric("Best / Worst", f"{best_ret:+.1f}% / {worst_ret:+.1f}%")
        
        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        
        cols = st.columns(3)
        for i, p in enumerate(perf):
            rp = p.get("return_pct")
            rc = ret_color(rp)
            rs = f"{rp:+.2f}%" if rp is not None else "—"
            
            # 🔥 Bulletproof protection against NoneType format crash
            dd = p.get("max_drawdown")
            try:
                if dd is not None:
                    dd_html = f"<div style='font-size:13px;font-weight:600;color:#DC2626;'>{float(dd):.2f}%</div>"
                else:
                    dd_html = "<div style='font-size:13px;font-weight:600;color:#94A3B8;'>—</div>"
            except:
                dd_html = "<div style='font-size:13px;font-weight:600;color:#94A3B8;'>—</div>"
            
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"""
                    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;'>
                        <div style='font-size:16px; font-weight:800; color:#0F172A;'>{p.get('ticker','—')}</div>
                        <div style='font-size:18px; font-weight:800; color:{rc};'>{rs}</div>
                    </div>
                    <div style='font-size:11px; color:#64748B; font-weight:600; margin-bottom:12px;'>
                        {clean_placeholder(p.get('alert_name','—'))} &middot; <span style='color:#0F172A;'>{p.get("action_call") or "—"} ({p.get("conviction") or "—"})</span>
                    </div>
                    <div style='display:flex; justify-content:space-between; align-items:center; background:#F8FAFC; padding:8px 12px; border-radius:6px; border:1px solid #E2E8F0; margin-bottom:10px;'>
                        <div>
                            <div style='font-size:9px; color:#94A3B8; text-transform:uppercase; font-weight:800;'>Entry</div>
                            <div style='font-size:13px; font-weight:700; color:#0F172A;'>{fmt_price(p.get('reference_price'))}</div>
                        </div>
                        <div style='color:#CBD5E1;'>→</div>
                        <div style='text-align:right;'>
                            <div style='font-size:9px; color:#94A3B8; text-transform:uppercase; font-weight:800;'>Current</div>
                            <div style='font-size:13px; font-weight:700; color:#0F172A;'>{fmt_price(p.get('current_price'))}</div>
                        </div>
                    </div>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <div>
                            <div style='font-size:10px;color:#94A3B8;font-weight:600;text-transform:uppercase;'>Max DD</div>
                            {dd_html}
                        </div>
                        <div style='font-size:9px; color:#94A3B8; font-weight:700; text-align:right;'>UPD: {fmt_ist(p.get('last_updated'))}</div>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.markdown("<div class='empty-state'><div style='font-size:40px; opacity:0.3;'>📊</div><p style='font-size:14px;margin-top:12px;'>No active positions</p></div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# ALERT DATABASE
# ═══════════════════════════════════════════════════════════
elif page == "Alert Database":
    st.markdown("<h1>Alert Database</h1><p style='color:#64748B; font-size:13px; margin-bottom:24px;'>Board-ready view of all approved recommendations</p>", unsafe_allow_html=True)
    
    f1, f2, f3 = st.columns([1,1,2])
    with f1: ds = st.selectbox("Status", ["APPROVED", "All", "PENDING", "DENIED"], key="ds", label_visibility="collapsed")
    with f2: view_mode = st.selectbox("View", ["Cards", "Table"], key="vm", label_visibility="collapsed")
    
    pm = {"limit": 100}
    if ds != "All": pm["status"] = ds
    
    m = api_call('GET', "/api/master", params=pm)
    
    if m and m.get("alerts"):
        als = m["alerts"]
        st.markdown(f"<p style='font-size:11px; color:#94A3B8; margin-bottom:16px; font-weight:700;'>Showing {len(als)} records</p>", unsafe_allow_html=True)
        
        if view_mode == "Cards":
            cols = st.columns(3)
            for i, a in enumerate(als):
                act = a.get("action") or {}
                with cols[i % 3]:
                    with st.container(border=True):
                        st.markdown(f"""
                        <div style='display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px;'>
                            <div style='font-size:16px; font-weight:800; color:#0F172A;'>{clean_placeholder(a.get('alert_name','—'))}</div>
                            {stat_pill(a.get('status'))}
                        </div>
                        <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;'>
                            <div style='font-size:13px; font-weight:700; color:#334155;'>{a.get('ticker','—')}</div>
                            <div style='font-size:10px; color:#94A3B8; font-weight:700;'>{fmt_ist(a.get('received_at'))}</div>
                        </div>
                        <div style='font-size:12px; color:#64748B; font-weight:600; margin-bottom:16px;'>
                            Price: <span style='color:#0F172A;'>{fmt_price(a.get('price_at_alert'))}</span> &middot; Call: <span style='color:#0F172A;'>{act.get('call','—')}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        remarks = act.get("remarks")
                        if remarks:
                            safe_remarks = str(remarks).replace('<', '&lt;').replace('>', '&gt;')
                            st.markdown(f"<div style='font-size:11px; color:#475569; padding:8px 10px; background:#F8FAFC; border-radius:6px; border:1px solid #E2E8F0; line-height:1.4; margin-bottom:12px;'><strong>FM View:</strong> {safe_remarks}</div>", unsafe_allow_html=True)
                        
                        if act.get("has_chart"):
                            chart_data = api_call('GET', f"/api/alerts/{a['id']}/chart")
                            if chart_data and chart_data.get("chart_image_b64"):
                                try:
                                    img_bytes = base64.b64decode(chart_data["chart_image_b64"])
                                    st.image(img_bytes, width=100) 
                                except: pass
                        
                        bc1, bc2 = st.columns([1,2])
                        with bc1:
                            if st.button("🗑️ Delete", key=f"del_{a['id']}"):
                                api_call('DELETE', f"/api/alerts/{a['id']}")
                                st.rerun()
        else:
            rows = [{
                "Date (IST)": fmt_ist(a.get("received_at")),
                "Alert": clean_placeholder(a.get("alert_name","—")),
                "Ticker": a.get("ticker","—"),
                "Price": fmt_price(a.get("price_at_alert")),
                "Status": a.get("status","PENDING"),
                "Call": (a.get("action") or {}).get("call","—"),
                "Remarks": (a.get("action") or {}).get("remarks","—")
            } for a in als]
            df = pd.DataFrame(rows)
            def cs(v):
                return {"APPROVED":"background-color:#ECFDF5;color:#059669","DENIED":"background-color:#FEF2F2;color:#DC2626","PENDING":"background-color:#FFFBEB;color:#B45309"}.get(v,"")
            st.dataframe(df.style.map(cs, subset=["Status"]), use_container_width=True, hide_index=True)

    else:
        st.markdown("<div class='empty-state'><div style='font-size:40px;opacity:0.3;'>📁</div><p style='font-size:14px;margin-top:12px;'>No alerts in database</p></div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# INTEGRATIONS
# ═══════════════════════════════════════════════════════════
elif page == "Integrations":
    st.markdown("<h1>Integrations</h1><p style='color:#64748B; font-size:13px; margin-bottom:24px;'>Webhook configuration and templates</p>", unsafe_allow_html=True)
    
    wh = f"{API_BASE}/webhook/tradingview"
    st.markdown(f"<div style='background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:16px; font-family:monospace; font-size:13px;'>POST <b>{wh}</b></div>", unsafe_allow_html=True)
    
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.markdown("### Universal Webhook Template")
    st.markdown("<p style='font-size:12px;color:#64748B;'>Paste this directly into your TradingView alert message. Manually replace <code>\"Your Custom Alert Name\"</code> and the <code>message</code> text.</p>", unsafe_allow_html=True)
    st.code(json.dumps({
        "ticker": "{{ticker}}", "exchange": "{{exchange}}", "interval": "{{interval}}",
        "open": "{{open}}", "high": "{{high}}", "low": "{{low}}",
        "close": "{{close}}", "volume": "{{volume}}", "time": "{{time}}",
        "timenow": "{{timenow}}",
        "alert_name": "Your Custom Alert Name",
        "message": "Write what happened here (e.g. Price broke resistance)"
    }, indent=2), language="json")
    
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.markdown("### 🧪 Connection Tester")
    st.markdown("<p style='font-size:12px;color:#64748B;'>Use this button to instantly test if the app is receiving webhooks properly.</p>", unsafe_allow_html=True)
    
    test_json = json.dumps({
        "ticker": "RELIANCE", "exchange": "NSE", "interval": "1D",
        "close": "2950.50", "volume": "14500000",
        "time": "2026-02-24T09:15:00Z", "timenow": "2026-02-24T15:30:00Z",
        "alert_name": "System Health Test",
        "message": "This is an automated test to confirm the database and UI are working."
    })
    
    if st.button("🚀 Fire Test Webhook", type="primary"):
        try:
            r = api_call('POST', "/webhook/tradingview", data=json.loads(test_json))
            if r and r.get("success"): 
                st.success(f"✓ Test Alert successfully inserted into database! Check the Command Center.")
            else: 
                st.error(f"Failed to insert. Backend returned: {r}")
        except Exception as e:
            st.error(f"Connection failed: {e}")

    
# ═══════════════════════════════════════════════════════
# AUTO-REFRESH
# ═══════════════════════════════════════════════════════
if _should_auto_refresh:
    time.sleep(5)
    st.rerun()
