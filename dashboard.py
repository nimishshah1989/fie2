import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time
import os
import base64
import json

API_BASE = os.getenv("FIE_API_URL", "http://localhost:8000")

st.set_page_config(page_title="Jhaveri Intelligence", layout="wide", initial_sidebar_state="expanded")

# ─── Premium CSS ─────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    * { font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important; }
    code, pre, .stCode { font-family: 'JetBrains Mono', monospace !important; }
    
    .stApp { background: #FAFBFC !important; }
    #MainMenu, footer, header[data-testid="stHeader"] { display: none !important; }
    
    /* ─── Sidebar ─── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0C1222 0%, #131B2E 100%) !important;
        border-right: 1px solid rgba(255,255,255,0.04) !important;
    }
    section[data-testid="stSidebar"] * { color: #C8D1DC !important; }
    section[data-testid="stSidebar"] .stRadio label:hover { color: #FFFFFF !important; }
    section[data-testid="stSidebar"] [data-testid="stRadio"] > div[role="radiogroup"] > label[data-baseweb="radio"] {
        padding: 8px 12px !important; border-radius: 6px !important; margin-bottom: 2px !important;
        transition: all 0.15s ease !important;
    }
    section[data-testid="stSidebar"] [data-testid="stRadio"] > div[role="radiogroup"] > label[data-baseweb="radio"]:hover {
        background: rgba(255,255,255,0.06) !important;
    }
    
    /* ─── KPI Cards ─── */
    div[data-testid="stMetric"] {
        background: #FFFFFF; border: 1px solid #E8ECF1; border-radius: 10px;
        padding: 20px 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        transition: box-shadow 0.2s ease;
    }
    div[data-testid="stMetric"]:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
    div[data-testid="stMetric"] label {
        font-size: 11px !important; color: #8493A8 !important;
        font-weight: 600 !important; text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 26px !important; color: #0F172A !important; font-weight: 700 !important;
    }
    
    /* ─── Typography ─── */
    h1 { color: #0F172A !important; font-size: 22px !important; font-weight: 700 !important; letter-spacing: -0.3px !important; margin-bottom: 2px !important; }
    h3 { color: #1E293B !important; font-size: 16px !important; font-weight: 600 !important; }
    
    /* ─── Signal Cards ─── */
    .sig-card {
        background: #FFFFFF; border: 1px solid #E8ECF1; border-radius: 10px;
        padding: 20px 24px; margin-bottom: 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        transition: all 0.2s ease;
    }
    .sig-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.06); border-color: #D0D7E2; }
    
    .sig-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; }
    .sig-title { font-size: 15px; font-weight: 700; color: #0F172A; }
    .sig-meta { font-size: 11px; color: #94A3B8; text-align: right; line-height: 1.5; }
    
    .sig-body { display: flex; gap: 24px; flex-wrap: wrap; margin-bottom: 14px; }
    .sig-stat { }
    .sig-stat-label { font-size: 10px; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; margin-bottom: 2px; }
    .sig-stat-value { font-size: 14px; color: #1E293B; font-weight: 600; }
    
    .sig-ai {
        background: #F8FAFC; border-left: 3px solid #3B82F6;
        padding: 12px 16px; border-radius: 0 6px 6px 0;
        font-size: 13px; color: #475569; line-height: 1.6;
    }
    .sig-ai b { color: #1E293B; }
    
    /* ─── Pills ─── */
    .pill {
        display: inline-flex; align-items: center; padding: 3px 10px;
        border-radius: 100px; font-size: 10px; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.5px;
    }
    .pill-bullish { background: #ECFDF5; color: #059669; }
    .pill-bearish { background: #FEF2F2; color: #DC2626; }
    .pill-neutral { background: #FFF7ED; color: #C2410C; }
    .pill-pending { background: #FFFBEB; color: #B45309; border: 1px solid #FDE68A; }
    .pill-approved { background: #ECFDF5; color: #059669; border: 1px solid #A7F3D0; }
    .pill-denied { background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; }
    .pill-review { background: #EFF6FF; color: #2563EB; border: 1px solid #BFDBFE; }
    
    /* ─── Divider ─── */
    .divider { border-top: 1px solid #F1F5F9; margin: 20px 0; }
    
    /* ─── Action Buttons ─── */
    .action-row { display: flex; gap: 8px; margin-top: 10px; }
    
    /* ─── Master Table ─── */
    .dataframe { font-size: 12px !important; }
    .dataframe th { 
        background: #F8FAFC !important; color: #64748B !important; 
        font-weight: 600 !important; text-transform: uppercase !important;
        font-size: 10px !important; letter-spacing: 0.5px !important;
    }
    .dataframe td { color: #334155 !important; font-size: 12px !important; }
    
    /* ─── Empty State ─── */
    .empty-state {
        text-align: center; padding: 60px 20px; color: #94A3B8;
    }
    .empty-state-icon { font-size: 40px; margin-bottom: 12px; opacity: 0.4; }
    .empty-state-text { font-size: 14px; font-weight: 500; }
    
    /* ─── Hide Streamlit Excess ─── */
    .block-container { padding-top: 2rem !important; max-width: 1200px !important; }
    div[data-testid="stVerticalBlock"] > div:has(> .stButton) { margin-top: -10px; }
    
    /* Table styling overrides */
    [data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; border: 1px solid #E8ECF1; }
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
    except Exception as e:
        st.error(f"API Error: {e}")
    return None


def fmt_price(val):
    """Format price with commas and rupee symbol"""
    if val is None or val == 0:
        return "—"
    try:
        return f"₹{float(val):,.2f}"
    except:
        return "—"


def fmt_pct(val):
    if val is None:
        return "—"
    try:
        v = float(val)
        color = "#059669" if v >= 0 else "#DC2626"
        return f"<span style='color:{color}; font-weight:600'>{v:+.2f}%</span>"
    except:
        return "—"


def fmt_time(iso_str):
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%d %b %Y, %H:%M")
    except:
        return iso_str[:16] if len(iso_str) > 16 else iso_str


def direction_pill(direction):
    d = (direction or "NEUTRAL").upper()
    css_class = "pill-bullish" if d == "BULLISH" else "pill-bearish" if d == "BEARISH" else "pill-neutral"
    return f"<span class='pill {css_class}'>{d}</span>"


def status_pill(status):
    s = (status or "PENDING").upper()
    css_map = {"PENDING": "pill-pending", "APPROVED": "pill-approved", "DENIED": "pill-denied", "REVIEW_LATER": "pill-review"}
    label_map = {"REVIEW_LATER": "REVIEW"}
    return f"<span class='pill {css_map.get(s, 'pill-pending')}'>{label_map.get(s, s)}</span>"


# ─── Sidebar Navigation ─────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding: 12px 0 36px;'>
        <div style='font-size: 18px; font-weight: 800; color: #FFFFFF !important; letter-spacing: -0.3px;'>JHAVERI</div>
        <div style='font-size: 9px; color: #64748B !important; text-transform: uppercase; letter-spacing: 2px; margin-top: 2px;'>Intelligence Platform</div>
    </div>
    """, unsafe_allow_html=True)
    
    page = st.radio(
        "Navigation", 
        ["Command Center", "Trade Desk", "Portfolio Analytics", "Alert Database", "Integrations"],
        label_visibility="collapsed"
    )
    
    st.markdown("<div style='height: 40px'></div>", unsafe_allow_html=True)
    
    if st.button("Sync", use_container_width=True):
        st.rerun()


# ═══════════════════════════════════════════════════════
# PAGE 1: COMMAND CENTER
# ═══════════════════════════════════════════════════════
if page == "Command Center":
    st.markdown("<h1>Command Center</h1><p style='color:#64748B; font-size:13px; margin-bottom:24px;'>Real-time systemic signals and market intelligence</p>", unsafe_allow_html=True)
    
    stats = api_call('GET', "/api/stats") or {}
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Signals", stats.get("total_alerts", 0))
    c2.metric("Pending Review", stats.get("pending", 0))
    c3.metric("System Alpha", f"{stats.get('avg_return_pct', 0.0):+.2f}%")
    
    # Market status based on time
    now = datetime.now()
    is_market_hours = (now.weekday() < 5 and 9 <= now.hour < 16)
    c4.metric("Market Status", "OPEN" if is_market_hours else "CLOSED")
    
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    
    # Filter row
    col_f1, col_f2, _ = st.columns([1, 1, 3])
    with col_f1:
        status_filter = st.selectbox("Filter", ["All", "PENDING", "APPROVED", "DENIED", "REVIEW_LATER"], label_visibility="collapsed")
    
    data = api_call('GET', "/api/alerts", params={"limit": 50, "status": status_filter if status_filter != "All" else None})
    
    if not data or not data.get("alerts"):
        st.markdown("""
        <div class='empty-state'>
            <div class='empty-state-icon'>📡</div>
            <div class='empty-state-text'>No signals in the feed</div>
            <p style='font-size:12px; color:#B0B8C4; margin-top:8px;'>Alerts will appear here when TradingView webhooks fire</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for alert in data["alerts"]:
            ticker = alert.get("ticker", "—")
            alert_name = alert.get("alert_name", "System Trigger")
            price = alert.get("price_at_alert")
            direction = alert.get("signal_direction", "NEUTRAL")
            status = alert.get("status", "PENDING")
            interval = alert.get("interval") or "—"
            sector = alert.get("sector") or ""
            summary = alert.get("signal_summary") or "Awaiting AI analysis..."
            received = fmt_time(alert.get("received_at"))
            
            # Build the card
            st.markdown(f"""
            <div class="sig-card">
                <div class="sig-header">
                    <div>
                        <div class="sig-title">{alert_name} {direction_pill(direction)}</div>
                        <div style="font-size:12px; color:#64748B; margin-top:3px;">{ticker} &middot; {interval} &middot; {sector}</div>
                    </div>
                    <div class="sig-meta">
                        {received}<br/>{status_pill(status)}
                    </div>
                </div>
                <div class="sig-body">
                    <div class="sig-stat">
                        <div class="sig-stat-label">Trigger Price</div>
                        <div class="sig-stat-value">{fmt_price(price)}</div>
                    </div>
                    <div class="sig-stat">
                        <div class="sig-stat-label">Exchange</div>
                        <div class="sig-stat-value">{alert.get('exchange') or 'NSE'}</div>
                    </div>
                    <div class="sig-stat">
                        <div class="sig-stat-label">Type</div>
                        <div class="sig-stat-value">{alert.get('alert_type', 'ABSOLUTE')}</div>
                    </div>
                </div>
                <div class="sig-ai"><b>AI Analysis</b>&ensp;—&ensp;{summary}</div>
            </div>
            """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# PAGE 2: TRADE DESK
# ═══════════════════════════════════════════════════════
elif page == "Trade Desk":
    st.markdown("<h1>Trade Desk</h1><p style='color:#64748B; font-size:13px; margin-bottom:24px;'>Execution routing and rationale capture</p>", unsafe_allow_html=True)
    
    # ─── Pending Queue ─────────────────────────────
    st.markdown("### Pending Execution Queue")
    
    data = api_call('GET', "/api/alerts", params={"status": "PENDING", "limit": 20})
    review_data = api_call('GET', "/api/alerts", params={"status": "REVIEW_LATER", "limit": 20})
    
    pending_alerts = []
    if data and data.get("alerts"):
        pending_alerts.extend(data["alerts"])
    if review_data and review_data.get("alerts"):
        pending_alerts.extend(review_data["alerts"])
    
    if not pending_alerts:
        st.markdown("""
        <div style='background:#F0FDF4; border:1px solid #BBF7D0; border-radius:8px; padding:16px; text-align:center;'>
            <span style='color:#166534; font-weight:600; font-size:13px;'>Queue is clear — no pending actions</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        for alert in pending_alerts:
            alert_id = alert["id"]
            ticker = alert.get("ticker", "—")
            alert_name = alert.get("alert_name", "System Trigger")
            price = alert.get("price_at_alert")
            direction = alert.get("signal_direction", "NEUTRAL")
            summary = alert.get("signal_summary") or "No analysis available"
            current_status = alert.get("status", "PENDING")
            
            with st.container(border=True):
                # Header
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <div>
                        <span style="font-weight:700; font-size:15px; color:#0F172A;">{alert_name}</span>
                        {direction_pill(direction)}
                        {status_pill(current_status)}
                    </div>
                    <span style="font-size:12px; color:#94A3B8;">{ticker} &middot; {fmt_price(price)}</span>
                </div>
                """, unsafe_allow_html=True)
                
                # AI Summary
                st.markdown(f"<div class='sig-ai' style='margin-bottom:14px;'><b>AI Analysis</b> — {summary}</div>", unsafe_allow_html=True)
                
                # Action Row
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    call = st.selectbox(
                        "Call", ["BUY", "SELL", "HOLD", "ACCUMULATE", "REDUCE", "WATCH", "EXIT"],
                        key=f"call_{alert_id}", label_visibility="collapsed"
                    )
                    conviction = st.select_slider(
                        "Conviction", options=["LOW", "MEDIUM", "HIGH"],
                        value="MEDIUM", key=f"conv_{alert_id}"
                    )
                
                with col2:
                    target = st.number_input("Target (optional)", value=0.0, step=100.0, format="%.2f", key=f"tgt_{alert_id}")
                    stop = st.number_input("Stop Loss (optional)", value=0.0, step=100.0, format="%.2f", key=f"sl_{alert_id}")
                
                with col3:
                    # FM Rationale
                    pov = st.text_area("FM Rationale", placeholder="Record your investment thesis...", key=f"pov_{alert_id}", height=80)
                    
                    # Chart upload
                    chart_file = st.file_uploader("Attach Chart", type=["png", "jpg", "jpeg"], key=f"chart_{alert_id}", label_visibility="collapsed")
                
                # Voice recording note
                st.markdown("<p style='font-size:11px; color:#94A3B8; margin:4px 0 8px;'>For voice rationale, use your device recorder and paste the transcript above</p>", unsafe_allow_html=True)
                
                # Decision Buttons
                bcol1, bcol2, bcol3, _ = st.columns([1, 1, 1, 3])
                
                chart_b64 = None
                if chart_file:
                    chart_b64 = base64.b64encode(chart_file.read()).decode('utf-8')
                
                action_payload = {
                    "alert_id": alert_id,
                    "primary_call": call,
                    "conviction": conviction,
                    "fm_rationale_text": pov if pov else None,
                    "target_price": target if target > 0 else None,
                    "stop_loss": stop if stop > 0 else None,
                    "chart_image_b64": chart_b64,
                }
                
                with bcol1:
                    if st.button("✓ Approve", key=f"approve_{alert_id}", type="primary", use_container_width=True):
                        action_payload["decision"] = "APPROVED"
                        api_call('POST', f"/api/alerts/{alert_id}/action", action_payload)
                        st.rerun()
                
                with bcol2:
                    if st.button("✗ Deny", key=f"deny_{alert_id}", use_container_width=True):
                        action_payload["decision"] = "DENIED"
                        api_call('POST', f"/api/alerts/{alert_id}/action", action_payload)
                        st.rerun()
                
                with bcol3:
                    if st.button("◷ Review", key=f"review_{alert_id}", use_container_width=True):
                        action_payload["decision"] = "REVIEW_LATER"
                        api_call('POST', f"/api/alerts/{alert_id}/action", action_payload)
                        st.rerun()
    
    # ─── Recent Decisions ─────────────────────────
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.markdown("### Recent Decisions")
    
    hist_data = api_call('GET', "/api/alerts", params={"limit": 15})
    if hist_data and hist_data.get("alerts"):
        actioned = [a for a in hist_data["alerts"] if a.get("status") in ("APPROVED", "DENIED", "REVIEW_LATER")]
        if actioned:
            for alert in actioned[:10]:
                act = alert.get("action") or {}
                call_text = act.get("call") or "—"
                remarks = act.get("remarks") or ""
                conviction = act.get("conviction") or ""
                
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center; padding:10px 0; border-bottom:1px solid #F1F5F9;">
                    <div>
                        <span style="font-weight:600; color:#0F172A; font-size:13px;">{alert.get('alert_name', alert.get('ticker'))}</span>
                        &ensp;{status_pill(alert.get('status'))}
                        &ensp;<span style="font-size:12px; color:#64748B;">{call_text} &middot; {conviction}</span>
                    </div>
                    <span style="font-size:11px; color:#94A3B8;">{fmt_time(alert.get('received_at'))}</span>
                </div>
                """, unsafe_allow_html=True)
                
                if remarks:
                    st.markdown(f"<div style='font-size:12px; color:#64748B; padding:4px 0 8px; margin-left:12px; border-left:2px solid #E2E8F0; padding-left:12px;'>{remarks}</div>", unsafe_allow_html=True)
        else:
            st.info("No decisions recorded yet.")
    else:
        st.info("No historical data available.")


# ═══════════════════════════════════════════════════════
# PAGE 3: PORTFOLIO ANALYTICS
# ═══════════════════════════════════════════════════════
elif page == "Portfolio Analytics":
    st.markdown("<h1>Portfolio Analytics</h1><p style='color:#64748B; font-size:13px; margin-bottom:24px;'>Live performance tracking of approved positions</p>", unsafe_allow_html=True)
    
    col_r1, _ = st.columns([1, 4])
    with col_r1:
        if st.button("Refresh Prices", type="primary", use_container_width=True):
            with st.spinner("Fetching live NSE prices..."):
                result = api_call('POST', "/api/performance/refresh")
                if result:
                    st.success(f"Updated {result.get('updated_count', 0)} positions")
            st.rerun()
    
    data = api_call('GET', "/api/performance")
    
    if data and data.get("performance"):
        perf_list = data["performance"]
        
        # Summary metrics
        total_positions = len(perf_list)
        avg_return = sum(p.get("return_pct", 0) or 0 for p in perf_list) / max(total_positions, 1)
        winners = sum(1 for p in perf_list if (p.get("return_pct") or 0) > 0)
        
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Active Positions", total_positions)
        mc2.metric("Avg Return", f"{avg_return:+.2f}%")
        mc3.metric("Win Rate", f"{(winners/max(total_positions,1))*100:.0f}%")
        
        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        
        # Performance table
        rows = []
        for p in perf_list:
            ret_pct = p.get("return_pct")
            rows.append({
                "Ticker": p.get("ticker", "—"),
                "Alert": p.get("alert_name", "—"),
                "Call": p.get("action_call", "—"),
                "Entry": fmt_price(p.get("reference_price")),
                "Current": fmt_price(p.get("current_price")),
                "Return %": f"{ret_pct:+.2f}%" if ret_pct is not None else "—",
                "High Since": fmt_price(p.get("high_since")),
                "Drawdown": f"{p.get('max_drawdown', 0) or 0:.2f}%",
                "Approved": fmt_time(p.get("approved_at")),
            })
        
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.markdown("""
        <div class='empty-state'>
            <div class='empty-state-icon'>📊</div>
            <div class='empty-state-text'>No active positions to track</div>
            <p style='font-size:12px; color:#B0B8C4; margin-top:8px;'>Approve signals from the Trade Desk to begin tracking</p>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# PAGE 4: ALERT DATABASE (Master View)
# ═══════════════════════════════════════════════════════
elif page == "Alert Database":
    st.markdown("<h1>Alert Database</h1><p style='color:#64748B; font-size:13px; margin-bottom:24px;'>Master repository of all historical alerts</p>", unsafe_allow_html=True)
    
    # Filters
    fc1, fc2, fc3, _ = st.columns([1, 1, 1, 2])
    with fc1:
        db_status = st.selectbox("Status", ["All", "PENDING", "APPROVED", "DENIED", "REVIEW_LATER"], key="db_status")
    with fc2:
        db_ticker = st.text_input("Ticker", placeholder="e.g. NIFTY", key="db_ticker")
    with fc3:
        db_limit = st.selectbox("Show", [50, 100, 200], key="db_limit")
    
    params = {"limit": db_limit}
    if db_status != "All":
        params["status"] = db_status
    if db_ticker:
        params["ticker"] = db_ticker
    
    master_data = api_call('GET', "/api/master", params=params)
    
    if master_data and master_data.get("alerts"):
        alerts = master_data["alerts"]
        total = master_data.get("total", len(alerts))
        
        st.markdown(f"<p style='font-size:12px; color:#94A3B8; margin-bottom:12px;'>Showing {len(alerts)} of {total} alerts</p>", unsafe_allow_html=True)
        
        rows = []
        for a in alerts:
            act = a.get("action") or {}
            perf = a.get("performance") or {}
            
            rows.append({
                "ID": a["id"],
                "Date": fmt_time(a.get("received_at")),
                "Alert Name": a.get("alert_name", "—"),
                "Ticker": a.get("ticker", "—"),
                "Direction": a.get("signal_direction", "—"),
                "Price": fmt_price(a.get("price_at_alert")),
                "Interval": a.get("interval", "—"),
                "Sector": a.get("sector", "—"),
                "Status": a.get("status", "PENDING"),
                "FM Call": act.get("call", "—"),
                "Conviction": act.get("conviction", "—"),
                "Target": fmt_price(act.get("target_price")),
                "Stop Loss": fmt_price(act.get("stop_loss")),
                "Return %": f"{perf.get('return_pct', 0):+.2f}%" if perf.get("return_pct") is not None else "—",
            })
        
        df = pd.DataFrame(rows)
        
        # Color-code the status column
        def highlight_status(val):
            colors = {
                "APPROVED": "background-color: #ECFDF5; color: #059669",
                "DENIED": "background-color: #FEF2F2; color: #DC2626",
                "PENDING": "background-color: #FFFBEB; color: #B45309",
                "REVIEW_LATER": "background-color: #EFF6FF; color: #2563EB",
            }
            return colors.get(val, "")
        
        styled_df = df.style.map(highlight_status, subset=["Status"])
        st.dataframe(styled_df, use_container_width=True, hide_index=True, height=600)
        
        # Delete functionality
        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        st.markdown("### Manage Alerts")
        
        del_col1, del_col2 = st.columns([1, 3])
        with del_col1:
            del_id = st.number_input("Alert ID to delete", min_value=1, step=1, key="del_id")
        with del_col2:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("Delete Alert", type="secondary"):
                if del_id:
                    confirm = st.checkbox(f"Confirm deletion of Alert #{int(del_id)}", key="del_confirm")
                    if confirm:
                        result = api_call('DELETE', f"/api/alerts/{int(del_id)}")
                        if result:
                            st.success(f"Alert #{int(del_id)} deleted")
                            st.rerun()
    else:
        st.markdown("""
        <div class='empty-state'>
            <div class='empty-state-icon'>🗃️</div>
            <div class='empty-state-text'>No alerts in the database</div>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# PAGE 5: INTEGRATIONS
# ═══════════════════════════════════════════════════════
elif page == "Integrations":
    st.markdown("<h1>Integrations</h1><p style='color:#64748B; font-size:13px; margin-bottom:24px;'>Webhook configuration and alert templates</p>", unsafe_allow_html=True)
    
    st.markdown("### Webhook Endpoint")
    webhook_url = f"{API_BASE}/webhook/tradingview"
    st.markdown(f"""
    <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:16px; font-family:'JetBrains Mono', monospace; font-size:13px; color:#1E293B;">
        POST&ensp;<b>{webhook_url}</b>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    
    st.markdown("### Recommended TradingView Alert Template")
    st.markdown("<p style='font-size:13px; color:#64748B;'>Copy and paste this JSON into the TradingView alert message field. Replace placeholder values with actual TradingView variables.</p>", unsafe_allow_html=True)
    
    template = {
        "ticker": "{{ticker}}",
        "exchange": "{{exchange}}",
        "interval": "{{interval}}",
        "close": "{{close}}",
        "volume": "{{volume}}",
        "time": "{{time}}",
        "timenow": "{{timenow}}",
        "alert_name": "YOUR_ALERT_NAME",
        "signal": "BULLISH",
        "indicators": {
            "rsi": "{{plot_0}}",
            "macd": "{{plot_1}}",
        },
        "message": "Your custom context"
    }
    st.code(json.dumps(template, indent=2), language="json")
    
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    
    st.markdown("### Relative Alert Template (Ratio of Two Indices)")
    template_rel = {
        "ticker": "{{ticker}}",
        "exchange": "{{exchange}}",
        "interval": "{{interval}}",
        "close": "{{close}}",
        "time": "{{timenow}}",
        "alert_name": "NIFTYIT vs NIFTY Ratio",
        "numerator": "NIFTYIT",
        "denominator": "NIFTY",
        "numerator_price": "{{plot_0}}",
        "denominator_price": "{{plot_1}}",
        "ratio": "{{plot_2}}",
        "signal": "BULLISH",
        "message": "Ratio breakout detected"
    }
    st.code(json.dumps(template_rel, indent=2), language="json")
    
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    
    st.markdown("### Test Webhook")
    st.markdown("<p style='font-size:13px; color:#64748B;'>Send a test alert to verify your setup.</p>", unsafe_allow_html=True)
    
    test_payload = st.text_area(
        "Test Payload (JSON)",
        value=json.dumps({
            "ticker": "NIFTY",
            "exchange": "NSE",
            "interval": "1D",
            "close": "22450.50",
            "alert_name": "Nifty 50 RSI Breakout",
            "signal": "BULLISH",
            "indicators": {"rsi": "68.5", "macd": "125.3"},
            "message": "RSI crossed above 65 on daily timeframe"
        }, indent=2),
        height=200
    )
    
    if st.button("Send Test Alert", type="primary"):
        try:
            payload = json.loads(test_payload)
            result = api_call('POST', "/webhook/tradingview", data=payload)
            if result and result.get("success"):
                st.success(f"Test alert received successfully (ID: {result.get('alert_id', '—')})")
            else:
                st.error("Failed to send test alert")
        except json.JSONDecodeError:
            st.error("Invalid JSON payload")
