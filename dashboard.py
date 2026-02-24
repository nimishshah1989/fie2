"""
FIE Phase 2 — High-Density Institutional Dashboard
Optimized for Streamlit Native Containers
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time
import os
import base64

# ─── Configuration ─────────────────────────────────────
API_BASE = os.getenv("FIE_API_URL", "http://localhost:8000")
REFRESH_INTERVAL = 3  

st.set_page_config(page_title="JHAVERI | Intelligence", layout="wide", initial_sidebar_state="expanded")

# ─── High-Density CSS Overlay ──────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    
    /* Hide Streamlit Clutter */
    #MainMenu, footer, header[data-testid="stHeader"] { display: none !important; }
    
    /* Compact Metrics */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 10px 15px;
    }
    div[data-testid="stMetric"] label { font-size: 11px !important; font-weight: 600 !important; color: #64748B !important; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 20px !important; font-weight: 700 !important; color: #0F172A !important; }
    
    /* Pill Badges */
    .pill { padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; text-transform: uppercase; }
    .pill-BULLISH, .pill-APPROVED { background-color: #ECFDF5; color: #059669; border: 1px solid #A7F3D0; }
    .pill-BEARISH, .pill-DENIED { background-color: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; }
    .pill-PENDING, .pill-NEUTRAL { background-color: #FFFBEB; color: #D97706; border: 1px solid #FDE68A; }
    
    /* Compact Buttons */
    .stButton>button { padding: 2px 10px !important; font-size: 12px !important; min-height: 32px !important; }
    
    /* Alert Card Density */
    .alert-card-meta { font-size: 12px; color: #64748B; margin-bottom: 8px; }
    .alert-card-summary { font-size: 13px; color: #334155; background: #F8FAFC; padding: 10px; border-left: 3px solid #3B82F6; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# ─── Helpers ───────────────────────────────────────────
def api_call(method, endpoint, data=None, params=None):
    try:
        url = f"{API_BASE}{endpoint}"
        if method == 'GET': r = requests.get(url, params=params, timeout=10)
        elif method == 'POST': r = requests.post(url, json=data, timeout=15)
        elif method == 'DELETE': r = requests.delete(url, timeout=10)
        if r.status_code in [200, 201]: return r.json()
    except Exception: return None

def fmt_price(val):
    try: return f"₹{float(val):,.2f}"
    except: return "—"

def get_pill(text):
    return f'<span class="pill pill-{str(text).upper()}">{text}</span>'

# ─── Sidebar Navigation ────────────────────────────────
with st.sidebar:
    st.markdown("""
        <div style="padding-bottom: 20px;">
            <div style="font-size: 20px; font-weight: 800; letter-spacing: -0.5px;">JHAVERI</div>
            <div style="font-size: 10px; color: #64748B; letter-spacing: 1.5px; text-transform: uppercase;">Intelligence Platform</div>
        </div>
    """, unsafe_allow_html=True)
    
    page = st.radio("Navigation", ["⚡ Command Center", "✅ Trade Desk", "📈 Portfolio Analytics", "📊 System Ledger", "⚙️ Settings"], label_visibility="collapsed")
    st.markdown("---")
    st.caption(f"🟢 Live Sync: {REFRESH_INTERVAL}s")

# ═══════════════════════════════════════════════════════
# PAGE: COMMAND CENTER (Live Feed)
# ═══════════════════════════════════════════════════════
if page == "⚡ Command Center":
    st.markdown("### Command Center")
    
    # Restored Filters
    with st.expander("🔍 Filter Market Feed", expanded=False):
        f1, f2, f3 = st.columns(3)
        with f1: filter_status = st.selectbox("Status", ["All", "PENDING", "APPROVED", "DENIED"])
        with f2: filter_signal = st.selectbox("Signal", ["All", "BULLISH", "BEARISH", "NEUTRAL"])
        with f3: filter_search = st.text_input("Search Ticker/Message", "")

    fp = {}
    if filter_status != "All": fp["status"] = filter_status
    if filter_signal != "All": fp["signal_direction"] = filter_signal
    if filter_search: fp["search"] = filter_search

    # KPI Row (Removed Alpha/Win Rate)
    stats = api_call('GET', "/api/stats") or {}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Intel Processed", stats.get("total_alerts", 0))
    c2.metric("Signals Today", stats.get("today_alerts", 0))
    c3.metric("Pending Execution", stats.get("pending", 0))
    c4.metric("Approved Active", stats.get("approved", 0))
    
    st.markdown("<br>", unsafe_allow_html=True)

    @st.fragment(run_every=REFRESH_INTERVAL)
    def render_feed():
        data = api_call('GET', "/api/alerts", params=fp)
        if not data or not data.get("alerts"):
            st.info("No active signals matching criteria.")
            return

        for alert in data["alerts"]:
            ticker = alert.get("ticker") or "UNKNOWN"
            alert_name = alert.get("alert_name") or "System Trigger"
            sig_dir = alert.get("signal_direction") or "NEUTRAL"
            status = alert.get("status", "PENDING")
            price = fmt_price(alert.get("price_at_alert"))
            
            with st.container(border=True):
                # Dense Layout: Main info and Action Buttons side-by-side
                col_info, col_actions = st.columns([4, 1])
                
                with col_info:
                    # Title & Badges
                    st.markdown(f"**{ticker}** — {alert_name} &nbsp;&nbsp; {get_pill(sig_dir)} &nbsp; {get_pill(status)}", unsafe_allow_html=True)
                    # Compact Meta Data
                    st.markdown(f"<div class='alert-card-meta'>💰 Trigger: <b>{price}</b> &nbsp;|&nbsp; ⏱ Interval: <b>{alert.get('interval', '—')}</b> &nbsp;|&nbsp; 🏛 Sector: <b>{alert.get('sector', '—')}</b></div>", unsafe_allow_html=True)
                    # AI Context
                    summary = alert.get('signal_summary') or alert.get('alert_message') or 'No AI summary available.'
                    st.markdown(f"<div class='alert-card-summary'>{summary}</div>", unsafe_allow_html=True)
                    
                    # Logged Execution context (if approved)
                    if status == "APPROVED" and alert.get("action"):
                        act = alert["action"]
                        st.markdown(f"<div style='font-size: 12px; margin-top: 6px;'><b>Executed:</b> {act.get('primary_call', '')} | <b>Note:</b> <span style='color: #059669;'>{act.get('fm_remarks', '—')}</span></div>", unsafe_allow_html=True)

                with col_actions:
                    # Restored Action Buttons on the Card
                    if status == "PENDING":
                        st.write("") # Spacer
                        if st.button("✅ Approve", key=f"app_{alert['id']}", use_container_width=True):
                            api_call('POST', f"/api/alerts/{alert['id']}/action", {
                                "alert_id": alert["id"], "decision": "APPROVED", "primary_call": "WATCH"
                            })
                            st.rerun()
                        if st.button("❌ Deny", key=f"den_{alert['id']}", use_container_width=True):
                            api_call('POST', f"/api/alerts/{alert['id']}/action", {
                                "alert_id": alert["id"], "decision": "DENIED"
                            })
                            st.rerun()

    render_feed()

# ═══════════════════════════════════════════════════════
# PAGE: TRADE DESK (Action Center)
# ═══════════════════════════════════════════════════════
elif page == "✅ Trade Desk":
    st.markdown("### Execution Desk")
    st.caption("Detailed execution routing. Manual sync mode enabled to prevent data wipe.")
    
    if st.button("🔄 Sync Pending Alerts", use_container_width=False): st.rerun()
    st.markdown("---")
    
    data = api_call('GET', "/api/alerts", params={"status": "PENDING", "limit": 20})
    
    if not data or not data.get("alerts"):
        st.success("Queue empty. All recommendations processed.")
    else:
        for alert in data["alerts"]:
            with st.container(border=True):
                st.markdown(f"**{alert.get('ticker', 'UNKNOWN')}** — {alert.get('alert_name')} {get_pill(alert.get('signal_direction', 'NEUTRAL'))}", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:12px; color:#64748B; margin-bottom:10px;'>Trigger Price: <b>{fmt_price(alert.get('price_at_alert'))}</b></div>", unsafe_allow_html=True)
                st.info(alert.get('signal_summary') or alert.get('alert_message') or "No context provided.")
                
                # Dense Execution Form
                c1, c2, c3 = st.columns(3)
                with c1: action_call = st.selectbox("Action Call", ["BUY", "SELL", "HOLD", "IGNORE"], key=f"call_{alert['id']}")
                with c2: target_lvl = st.text_input("Target Level (Opt)", key=f"tgt_{alert['id']}")
                with c3: stop_lvl = st.text_input("Stop Loss (Opt)", key=f"sl_{alert['id']}")
                
                c_txt, c_mic = st.columns([2, 1])
                with c_txt:
                    pov = st.text_area("Manager Rationale", placeholder="Explain execution logic...", height=100, key=f"pov_{alert['id']}")
                with c_mic:
                    audio_b64 = None
                    if hasattr(st, "audio_input"):
                        audio_val = st.audio_input("Record Voice Note", key=f"audio_{alert['id']}")
                        if audio_val: audio_b64 = base64.b64encode(audio_val.read()).decode("utf-8")
                    else:
                        st.warning("Update Streamlit (>=1.39) for voice.")
                        
                c_sub, c_rej, _ = st.columns([1, 1, 3])
                with c_sub:
                    if st.button("Authorize Execution", type="primary", use_container_width=True, key=f"auth_{alert['id']}"):
                        payload = {"alert_id": alert["id"], "decision": "APPROVED", "primary_call": action_call, "fm_rationale_text": pov, "fm_rationale_audio": audio_b64}
                        if target_lvl.replace('.','',1).isdigit(): payload["primary_target_price"] = float(target_lvl)
                        if stop_lvl.replace('.','',1).isdigit(): payload["primary_stop_loss"] = float(stop_lvl)
                        if api_call('POST', f"/api/alerts/{alert['id']}/action", payload):
                            st.success("Authorized.")
                            time.sleep(0.5)
                            st.rerun()
                with c_rej:
                    if st.button("Reject Signal", use_container_width=True, key=f"rej_full_{alert['id']}"):
                        if api_call('POST', f"/api/alerts/{alert['id']}/action", {"alert_id": alert["id"], "decision": "DENIED"}):
                            st.rerun()

# ═══════════════════════════════════════════════════════
# PAGE: PORTFOLIO ANALYTICS (Performance)
# ═══════════════════════════════════════════════════════
elif page == "📈 Portfolio Analytics":
    st.markdown("### Portfolio Performance")
    
    # Moved Alpha and Win Rate Here
    stats = api_call('GET', "/api/stats") or {}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("System Alpha (YTD)", f'{stats.get("avg_return_pct", 0):.2f}%')
    c2.metric("System Win Rate", f'{stats.get("win_rate", 0)}%')
    
    tp = stats.get("top_performer", {}) or {}
    c3.metric("Max Winner", f'{tp.get("ticker", "—")} ({tp.get("return_pct", 0):.1f}%)')
    
    wp = stats.get("worst_performer", {}) or {}
    c4.metric("Max Drawdown", f'{wp.get("ticker", "—")} ({wp.get("return_pct", 0):.1f}%)')
    
    st.markdown("---")
    
    if st.button("🔄 Sync Live Market Prices", type="primary"):
        res = api_call('POST', "/api/performance/refresh")
        if res: st.success(f"Synced {res.get('updated_count')} active tracking records.")
        time.sleep(1)
        st.rerun()
            
    data = api_call('GET', "/api/performance")
    if data and data.get("performance"):
        df = pd.DataFrame(data["performance"])
        if not df.empty:
            view_df = pd.DataFrame({
                "Asset": df["ticker"],
                "Action": df["call"],
                "Entry Price": df["reference_price"].apply(lambda x: fmt_price(x)),
                "Current Price": df["current_price"].apply(lambda x: fmt_price(x)),
                "Net %": df["return_pct"].apply(lambda x: f"{x:+.2f}%" if pd.notnull(x) else "—"),
                "Execution Date": pd.to_datetime(df["approved_at"]).dt.strftime('%d %b %Y')
            })
            st.dataframe(view_df, use_container_width=True, hide_index=True)
    else:
        st.info("No active trades to track.")

# ═══════════════════════════════════════════════════════
# PAGE: SYSTEM LEDGER
# ═══════════════════════════════════════════════════════
elif page == "📊 System Ledger":
    st.markdown("### Master Alert Database")
    
    data = api_call('GET', "/api/alerts", params={"limit": 500})
    if data and data.get("alerts"):
        df = pd.DataFrame(data["alerts"])
        display_df = pd.DataFrame({
            "Date": pd.to_datetime(df["received_at"]).dt.strftime('%d %b %Y %H:%M'),
            "Alert ID": df["id"],
            "Ticker": df["ticker"],
            "Signal": df["signal_direction"],
            "Status": df["status"],
            "Alert Context": df["alert_name"]
        })
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        with st.expander("Danger Zone - Record Deletion"):
            st.warning("Deleting a record permanently removes it from performance tracking.")
            del_id = st.text_input("Enter Alert ID:")
            if st.button("Delete Permanently"):
                if del_id.isdigit() and api_call('DELETE', f"/api/alerts/{del_id}"):
                    st.success("Deleted.")
                    time.sleep(0.5)
                    st.rerun()
    else:
        st.info("Database is empty.")

# ═══════════════════════════════════════════════════════
# PAGE: SETTINGS
# ═══════════════════════════════════════════════════════
elif page == "⚙️ Settings":
    st.markdown("### System Configuration")
    
    st.subheader("Webhook Endpoint")
    st.code(f"{API_BASE}/webhook/tradingview", language="text")
    
    st.subheader("JSON Payload Template")
    st.info("Copy this EXACTLY into the TradingView message box to prevent 'Unknown' errors.")
    st.code("""{
    "ticker": "{{ticker}}",
    "exchange": "{{exchange}}",
    "interval": "{{interval}}",
    "price_at_alert": "{{close}}",
    "price_open": "{{open}}",
    "price_high": "{{high}}",
    "price_low": "{{low}}",
    "volume": "{{volume}}",
    "time_utc": "{{timenow}}",
    "alert_name": "YOUR_STRATEGY_NAME",
    "signal_direction": "BULLISH",
    "sector": "Equity",
    "alert_message": "YOUR_CUSTOM_RATIONALE",
    "indicator_values": {
        "rsi": 70
    }
}""", language="json")
