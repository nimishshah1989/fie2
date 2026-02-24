import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time
import os
import base64
import json

API_BASE = os.getenv("FIE_API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Jhaveri Intelligence",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Session defaults ────────────────────────────────────
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

# ─── Premium CSS ─────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    * { font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important; }
    code, pre, .stCode { font-family: 'JetBrains Mono', monospace !important; }
    .stApp { background: #FAFBFC !important; }
    #MainMenu, footer { display: none !important; }
    /* Hide entire Streamlit header bar (contains broken Material icon text) */
    header[data-testid="stHeader"],
    .stAppHeader, header.stAppHeader,
    div[data-testid="stHeader"],
    .st-emotion-cache-h4xjwg,
    .st-emotion-cache-18ni7ap { display: none !important; height: 0 !important; visibility: hidden !important; }
    .block-container { padding-top: 1rem !important; }
    
    /* FORCE SIDEBAR ALWAYS VISIBLE */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0C1222 0%, #131B2E 100%) !important;
        border-right: 1px solid rgba(255,255,255,0.04) !important;
        min-width: 260px !important; width: 260px !important;
    }
    section[data-testid="stSidebar"] > div:first-child { padding-top: 1rem !important; }
    section[data-testid="stSidebar"] * { color: #C8D1DC !important; }
    section[data-testid="stSidebar"] .stRadio label:hover { color: #FFFFFF !important; }
    button[data-testid="stSidebarCollapseButton"],
    button[data-testid="baseButton-headerNoPadding"],
    [data-testid="collapsedControl"], .css-1dp5vir,
    button[kind="headerNoPadding"],
    .st-emotion-cache-1dp5vir,
    header[data-testid="stHeader"],
    [data-testid="stHeaderActionElements"] { display: none !important; visibility: hidden !important; height: 0 !important; overflow: hidden !important; }
    section[data-testid="stSidebar"][aria-expanded="false"] {
        display: block !important; min-width: 260px !important; width: 260px !important;
        transform: none !important; margin-left: 0 !important;
    }
    
    div[data-testid="stMetric"] {
        background: #FFFFFF; border: 1px solid #E8ECF1; border-radius: 10px;
        padding: 20px 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    div[data-testid="stMetric"]:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
    div[data-testid="stMetric"] label {
        font-size: 11px !important; color: #8493A8 !important;
        font-weight: 600 !important; text-transform: uppercase !important; letter-spacing: 0.5px !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 26px !important; color: #0F172A !important; font-weight: 700 !important;
    }
    h1 { color: #0F172A !important; font-size: 22px !important; font-weight: 700 !important; letter-spacing: -0.3px !important; margin-bottom: 2px !important; }
    h3 { color: #1E293B !important; font-size: 16px !important; font-weight: 600 !important; }
    
    .sig-card {
        background: #FFFFFF; border: 1px solid #E8ECF1; border-radius: 10px;
        padding: 20px 24px; margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    .sig-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.06); border-color: #D0D7E2; }
    .sig-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; }
    .sig-title { font-size: 15px; font-weight: 700; color: #0F172A; }
    .sig-meta { font-size: 11px; color: #94A3B8; text-align: right; line-height: 1.5; }
    .sig-body { display: flex; gap: 24px; flex-wrap: wrap; margin-bottom: 14px; }
    .sig-stat-label { font-size: 10px; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; margin-bottom: 2px; }
    .sig-stat-value { font-size: 14px; color: #1E293B; font-weight: 600; }
    .sig-ai {
        background: #F8FAFC; border-left: 3px solid #3B82F6;
        padding: 12px 16px; border-radius: 0 6px 6px 0; font-size: 13px; color: #475569; line-height: 1.6;
    }
    .sig-ai b { color: #1E293B; }
    
    .pill {
        display: inline-flex; align-items: center; padding: 3px 10px;
        border-radius: 100px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;
    }
    .pill-bullish { background: #ECFDF5; color: #059669; }
    .pill-bearish { background: #FEF2F2; color: #DC2626; }
    .pill-neutral { background: #FFF7ED; color: #C2410C; }
    .pill-pending { background: #FFFBEB; color: #B45309; border: 1px solid #FDE68A; }
    .pill-approved { background: #ECFDF5; color: #059669; border: 1px solid #A7F3D0; }
    .pill-denied { background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; }
    .pill-review { background: #EFF6FF; color: #2563EB; border: 1px solid #BFDBFE; }
    
    .divider { border-top: 1px solid #F1F5F9; margin: 20px 0; }
    .empty-state { text-align: center; padding: 60px 20px; color: #94A3B8; }
    .empty-state-text { font-size: 14px; font-weight: 500; }
    .block-container { padding-top: 2rem !important; max-width: 1200px !important; }
    [data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; border: 1px solid #E8ECF1; }
    .refresh-dot {
        display: inline-block; width: 6px; height: 6px; border-radius: 50%;
        background: #22C55E; margin-right: 6px; animation: pulse 2s infinite;
    }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
</style>
""", unsafe_allow_html=True)


def api_call(method, endpoint, data=None, params=None):
    try:
        url = f"{API_BASE}{endpoint}"
        if method == 'GET':
            r = requests.get(url, params=params, timeout=10)
        elif method == 'POST':
            r = requests.post(url, json=data, timeout=15)
        elif method == 'DELETE':
            r = requests.delete(url, timeout=10)
        else:
            return None
        if r.status_code in [200, 201]:
            return r.json()
    except Exception:
        pass
    return None

def fmt_price(val):
    if val is None or val == 0:
        return "—"
    try:
        return f"₹{float(val):,.2f}"
    except:
        return "—"

def fmt_time(iso_str):
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y, %H:%M")
    except:
        return str(iso_str)[:16]

def direction_pill(d):
    d = str(d or "NEUTRAL").upper()
    css = "pill-bullish" if d == "BULLISH" else "pill-bearish" if d == "BEARISH" else "pill-neutral"
    return f"<span class='pill {css}'>{d}</span>"

def status_pill(s):
    s = str(s or "PENDING").upper()
    css_map = {"PENDING": "pill-pending", "APPROVED": "pill-approved", "DENIED": "pill-denied", "REVIEW_LATER": "pill-review"}
    label_map = {"REVIEW_LATER": "REVIEW"}
    return f"<span class='pill {css_map.get(s, 'pill-pending')}'>{label_map.get(s, s)}</span>"


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
        if st.button("Sync", use_container_width=True):
            st.rerun()
    with sc2:
        auto = st.toggle("Auto", value=True, key="auto_refresh")
    
    st.markdown(f"<div style='font-size:10px; color:#475569; margin-top:8px;'><span class='refresh-dot'></span>Live &middot; {datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)


# ─── Auto-refresh (only on read-only pages) ──────────────
if st.session_state.get("auto_refresh", True) and page in ["Command Center", "Portfolio Analytics"]:
    time.sleep(3)
    st.rerun()


# ═══════════════════════════════════════════════════════
if page == "Command Center":
    st.markdown("<h1>Command Center</h1><p style='color:#64748B; font-size:13px; margin-bottom:24px;'>Real-time systemic signals and market intelligence</p>", unsafe_allow_html=True)
    stats = api_call('GET', "/api/stats") or {}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Signals", stats.get("total_alerts", 0))
    c2.metric("Pending Review", stats.get("pending", 0))
    c3.metric("System Alpha", f"{stats.get('avg_return_pct', 0.0):+.2f}%")
    now = datetime.now()
    c4.metric("Market Status", "OPEN" if (now.weekday() < 5 and 9 <= now.hour < 16) else "CLOSED")
    
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    fc1, _, _ = st.columns([1, 1, 3])
    with fc1:
        sf = st.selectbox("Filter", ["All", "PENDING", "APPROVED", "DENIED", "REVIEW_LATER"], label_visibility="collapsed", key="cf")
    params = {"limit": 50}
    if sf != "All":
        params["status"] = sf
    data = api_call('GET', "/api/alerts", params=params)
    
    if not data or not data.get("alerts"):
        st.markdown("<div class='empty-state'><div style='font-size:40px; opacity:0.3; margin-bottom:12px;'>📡</div><div class='empty-state-text'>No signals in the feed</div><p style='font-size:12px; color:#B0B8C4; margin-top:8px;'>Alerts appear when TradingView webhooks fire</p></div>", unsafe_allow_html=True)
    else:
        for al in data["alerts"]:
            name = al.get("alert_name") or "System Trigger"
            tk = al.get("ticker") or "—"
            pr = al.get("price_at_alert")
            dr = al.get("signal_direction", "NEUTRAL")
            st_val = al.get("status", "PENDING")
            iv = al.get("interval") or "—"
            sec = al.get("sector") or ""
            summ = al.get("signal_summary") or "Awaiting analysis..."
            rcv = fmt_time(al.get("received_at"))
            
            st.markdown(f"""<div class="sig-card">
                <div class="sig-header">
                    <div><div class="sig-title">{name} {direction_pill(dr)}</div>
                    <div style="font-size:12px; color:#64748B; margin-top:3px;">{tk} &middot; {iv}{(' &middot; ' + sec) if sec else ''}</div></div>
                    <div class="sig-meta">{rcv}<br/>{status_pill(st_val)}</div>
                </div>
                <div class="sig-body">
                    <div><div class="sig-stat-label">Trigger Price</div><div class="sig-stat-value">{fmt_price(pr)}</div></div>
                    <div><div class="sig-stat-label">Exchange</div><div class="sig-stat-value">{al.get('exchange') or 'NSE'}</div></div>
                    <div><div class="sig-stat-label">Type</div><div class="sig-stat-value">{al.get('alert_type', 'ABSOLUTE')}</div></div>
                </div>
                <div class="sig-ai"><b>AI Analysis</b>&ensp;—&ensp;{summ}</div>
            </div>""", unsafe_allow_html=True)

elif page == "Trade Desk":
    st.markdown("<h1>Trade Desk</h1><p style='color:#64748B; font-size:13px; margin-bottom:24px;'>Execution routing and rationale capture</p>", unsafe_allow_html=True)
    st.markdown("### Pending Execution Queue")
    d1 = api_call('GET', "/api/alerts", params={"status": "PENDING", "limit": 20})
    d2 = api_call('GET', "/api/alerts", params={"status": "REVIEW_LATER", "limit": 20})
    pending = (d1.get("alerts", []) if d1 else []) + (d2.get("alerts", []) if d2 else [])
    
    if not pending:
        st.markdown("<div style='background:#F0FDF4; border:1px solid #BBF7D0; border-radius:8px; padding:16px; text-align:center;'><span style='color:#166534; font-weight:600; font-size:13px;'>Queue is clear</span></div>", unsafe_allow_html=True)
    else:
        for al in pending:
            aid = al["id"]
            with st.container(border=True):
                st.markdown(f"""<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <div><span style="font-weight:700; font-size:15px; color:#0F172A;">{al.get('alert_name','Signal')}</span> {direction_pill(al.get('signal_direction'))} {status_pill(al.get('status'))}</div>
                    <span style="font-size:12px; color:#94A3B8;">{al.get('ticker','—')} &middot; {fmt_price(al.get('price_at_alert'))}</span>
                </div><div class='sig-ai' style='margin-bottom:14px;'><b>AI</b> — {al.get('signal_summary','—')}</div>""", unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    call = st.selectbox("Call", ["BUY","SELL","HOLD","ACCUMULATE","REDUCE","WATCH","EXIT"], key=f"c{aid}", label_visibility="collapsed")
                    conv = st.select_slider("Conviction", ["LOW","MEDIUM","HIGH"], value="MEDIUM", key=f"v{aid}")
                with c2:
                    tgt = st.number_input("Target", value=0.0, step=100.0, format="%.2f", key=f"t{aid}")
                    sl = st.number_input("Stop Loss", value=0.0, step=100.0, format="%.2f", key=f"s{aid}")
                with c3:
                    pov = st.text_area("Rationale", placeholder="Thesis...", key=f"p{aid}", height=80)
                    cf = st.file_uploader("Chart", type=["png","jpg","jpeg"], key=f"f{aid}", label_visibility="collapsed")
                
                cb64 = base64.b64encode(cf.read()).decode('utf-8') if cf else None
                pl = {"alert_id":aid, "primary_call":call, "conviction":conv, "fm_rationale_text":pov or None, "target_price":tgt if tgt>0 else None, "stop_loss":sl if sl>0 else None, "chart_image_b64":cb64}
                
                b1, b2, b3, _ = st.columns([1,1,1,3])
                with b1:
                    if st.button("✓ Approve", key=f"a{aid}", type="primary", use_container_width=True):
                        pl["decision"]="APPROVED"; api_call('POST', f"/api/alerts/{aid}/action", pl); st.rerun()
                with b2:
                    if st.button("✗ Deny", key=f"d{aid}", use_container_width=True):
                        pl["decision"]="DENIED"; api_call('POST', f"/api/alerts/{aid}/action", pl); st.rerun()
                with b3:
                    if st.button("◷ Later", key=f"r{aid}", use_container_width=True):
                        pl["decision"]="REVIEW_LATER"; api_call('POST', f"/api/alerts/{aid}/action", pl); st.rerun()
    
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.markdown("### Recent Decisions")
    hist = api_call('GET', "/api/alerts", params={"limit": 15})
    if hist and hist.get("alerts"):
        for a in [x for x in hist["alerts"] if x.get("status") in ("APPROVED","DENIED","REVIEW_LATER")][:10]:
            act = a.get("action") or {}
            st.markdown(f"""<div style="display:flex; justify-content:space-between; align-items:center; padding:10px 0; border-bottom:1px solid #F1F5F9;">
                <div><span style="font-weight:600; color:#0F172A; font-size:13px;">{a.get('alert_name', a.get('ticker','—'))}</span> {status_pill(a.get('status'))} <span style="font-size:12px; color:#64748B;">{act.get('call','—')}</span></div>
                <span style="font-size:11px; color:#94A3B8;">{fmt_time(a.get('received_at'))}</span>
            </div>""", unsafe_allow_html=True)

elif page == "Portfolio Analytics":
    st.markdown("<h1>Portfolio Analytics</h1><p style='color:#64748B; font-size:13px; margin-bottom:24px;'>Live performance of approved positions</p>", unsafe_allow_html=True)
    cr, _ = st.columns([1, 4])
    with cr:
        if st.button("Refresh Prices", type="primary", use_container_width=True):
            with st.spinner("Fetching..."): api_call('POST', "/api/performance/refresh")
            st.rerun()
    data = api_call('GET', "/api/performance")
    if data and data.get("performance"):
        perf = data["performance"]
        n = len(perf); avg = sum(p.get("return_pct",0) or 0 for p in perf)/max(n,1); wins = sum(1 for p in perf if (p.get("return_pct") or 0)>0)
        m1,m2,m3 = st.columns(3)
        m1.metric("Positions", n); m2.metric("Avg Return", f"{avg:+.2f}%"); m3.metric("Win Rate", f"{wins/max(n,1)*100:.0f}%")
        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        rows = [{"Ticker":p.get("ticker","—"), "Alert":p.get("alert_name","—"), "Entry":fmt_price(p.get("reference_price")), "Current":fmt_price(p.get("current_price")), "Return":f"{p.get('return_pct',0):+.2f}%" if p.get("return_pct") is not None else "—", "Approved":fmt_time(p.get("approved_at"))} for p in perf]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.markdown("<div class='empty-state'><div style='font-size:40px; opacity:0.3;'>📊</div><div class='empty-state-text'>No active positions</div></div>", unsafe_allow_html=True)

elif page == "Alert Database":
    st.markdown("<h1>Alert Database</h1><p style='color:#64748B; font-size:13px; margin-bottom:24px;'>Master repository</p>", unsafe_allow_html=True)
    f1,f2,f3,_ = st.columns([1,1,1,2])
    with f1: ds = st.selectbox("Status", ["All","PENDING","APPROVED","DENIED","REVIEW_LATER"], key="ds")
    with f2: dt = st.text_input("Ticker", key="dt")
    with f3: dl = st.selectbox("Rows", [50,100,200], key="dl")
    pm = {"limit": dl}
    if ds != "All": pm["status"] = ds
    if dt: pm["ticker"] = dt
    m = api_call('GET', "/api/master", params=pm)
    if m and m.get("alerts"):
        als = m["alerts"]
        st.markdown(f"<p style='font-size:12px; color:#94A3B8;'>Showing {len(als)} of {m.get('total', len(als))}</p>", unsafe_allow_html=True)
        rows = [{"ID":a["id"], "Date":fmt_time(a.get("received_at")), "Alert":a.get("alert_name","—"), "Ticker":a.get("ticker","—"), "Direction":a.get("signal_direction","—"), "Price":fmt_price(a.get("price_at_alert")), "Status":a.get("status","PENDING"), "Call":(a.get("action") or {}).get("call","—"), "Return":f"{(a.get('performance') or {}).get('return_pct',0):+.2f}%" if (a.get("performance") or {}).get("return_pct") is not None else "—"} for a in als]
        df = pd.DataFrame(rows)
        def cs(v):
            return {"APPROVED":"background-color:#ECFDF5;color:#059669","DENIED":"background-color:#FEF2F2;color:#DC2626","PENDING":"background-color:#FFFBEB;color:#B45309","REVIEW_LATER":"background-color:#EFF6FF;color:#2563EB"}.get(v,"")
        st.dataframe(df.style.map(cs, subset=["Status"]), use_container_width=True, hide_index=True, height=600)
        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        dc1,dc2 = st.columns([1,3])
        with dc1: did = st.number_input("Delete ID", min_value=1, step=1, key="did")
        with dc2:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("Delete"):
                r = api_call('DELETE', f"/api/alerts/{int(did)}")
                if r and r.get("success"): st.success(f"Deleted #{int(did)}"); st.rerun()

elif page == "Integrations":
    st.markdown("<h1>Integrations</h1><p style='color:#64748B; font-size:13px; margin-bottom:24px;'>Webhook config</p>", unsafe_allow_html=True)
    wh = f"{API_BASE}/webhook/tradingview"
    st.markdown(f"<div style='background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:16px; font-family:monospace; font-size:13px;'>POST <b>{wh}</b></div>", unsafe_allow_html=True)
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.markdown("### Alert Template")
    st.code(json.dumps({"ticker":"{{ticker}}","exchange":"{{exchange}}","interval":"{{interval}}","close":"{{close}}","volume":"{{volume}}","time":"{{time}}","timenow":"{{timenow}}","alert_name":"YOUR_NAME","signal":"BULLISH","indicators":{"rsi":"{{plot_0}}","macd":"{{plot_1}}"},"message":"Custom"}, indent=2), language="json")
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.markdown("### Test Webhook")
    tp = st.text_area("Payload", value=json.dumps({"ticker":"NIFTY","exchange":"NSE","interval":"1D","close":"22450.50","alert_name":"Nifty RSI Breakout","signal":"BULLISH","indicators":{"rsi":"68.5","macd":"125.3"},"message":"RSI crossed above 65"}, indent=2), height=180)
    if st.button("Send Test", type="primary"):
        try:
            r = api_call('POST', "/webhook/tradingview", data=json.loads(tp))
            if r and r.get("success"): st.success(f"Received (ID: {r.get('alert_id','—')})")
            else: st.error(f"Failed: {r}")
        except: st.error("Invalid JSON")
