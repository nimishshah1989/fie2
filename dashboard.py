"""
FIE Phase 2 — Institutional Intelligence Platform
(Claude Artifact UI Replication)
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

# ─── Institutional CSS (Claude Artifact Style) ─────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Global Font and Background */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    .stApp { background-color: #F8F9FA !important; }
    
    /* Hide Streamlit Clutter */
    #MainMenu, footer, header[data-testid="stHeader"] { display: none !important; }
    
    /* Navy Sidebar matching Claude Artifact */
    section[data-testid="stSidebar"] {
        background-color: #0F172A !important;
        border-right: none !important;
    }
    section[data-testid="stSidebar"] * { color: #F8FAFC !important; }
    section[data-testid="stSidebar"] .stRadio label { font-weight: 500; padding: 10px 0; }
    
    /* Metric Cards (Top Row) */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    div[data-testid="stMetric"] label { color: #64748B !important; font-size: 12px !important; font-weight: 600 !important; text-transform: uppercase; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #0F172A !important; font-weight: 700 !important; font-size: 28px !important; }
    
    /* Typography */
    h1, h2, h3 { color: #0F172A !important; font-weight: 700 !important; letter-spacing: -0.02em; }
    p, span { color: #334155; }
    
    /* Expander / Containers */
    div[data-testid="stExpander"], div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
    }
    
    /* Custom Pill Badges */
    .pill { display: inline-block; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
    .pill-green { background-color: #ECFDF5; color: #059669; border: 1px solid #A7F3D0; }
    .pill-red { background-color: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; }
    .pill-yellow { background-color: #FFFBEB; color: #D97706; border: 1px solid #FDE68A; }
    .pill-blue { background-color: #EFF6FF; color: #2563EB; border: 1px solid #BFDBFE; }
    
    /* Buttons */
    .stButton>button { border-radius: 6px !important; font-weight: 600 !important; }
    .stButton>button[kind="primary"] { background-color: #2563EB !important; border-color: #2563EB !important; }
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

def get_pill(text, intent):
    color = "blue"
    if intent in ["APPROVED", "BULLISH", "BUY"]: color = "green"
    elif intent in ["DENIED", "BEARISH", "SELL", "CRITICAL"]: color = "red"
    elif intent in ["PENDING", "HOLD", "HIGH"]: color = "yellow"
    return f'<span class="pill pill-{color}">{text}</span>'

# ─── Sidebar Navigation ────────────────────────────────
with st.sidebar:
    st.markdown("""
        <div style="padding: 10px 0 30px 0;">
            <div style="font-size: 20px; font-weight: 800; color: white; letter-spacing: -0.5px;">JHAVERI</div>
            <div style="font-size: 10px; color: #94A3B8; letter-spacing: 1.5px; text-transform: uppercase;">Intelligence Platform</div>
        </div>
    """, unsafe_allow_html=True)
    
    page = st.radio("Navigation", ["⚡ Command Center", "📊 Market Research", "✅ Trade Desk", "📈 Portfolio Analytics", "⚙️ Compliance & Settings"], label_visibility="collapsed")
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.caption(f"🟢 Live Sync: {REFRESH_INTERVAL}s")

# ═══════════════════════════════════════════════════════
# PAGE: COMMAND CENTER (Live Feed)
# ═══════════════════════════════════════════════════════
if page == "⚡ Command Center":
    st.title("Command Center")
    st.markdown("<p style='color: #64748B; margin-top:-15px; margin-bottom: 30px;'>Real-time market intelligence and systemic signals.</p>", unsafe_allow_html=True)
    
    # KPIs
    stats = api_call('GET', "/api/stats") or {}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Signals Today", stats.get("today_alerts", 0))
    c2.metric("Actions Pending", f'{stats.get("pending", 0)} Critical')
    c3.metric("System Alpha (YTD)", f'{stats.get("avg_return_pct", 0):.2f}%')
    c4.metric("Win Rate", f'{stats.get("win_rate", 0)}%')
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🤖 AI Action Board")

    @st.fragment(run_every=REFRESH_INTERVAL)
    def render_feed():
        data = api_call('GET', "/api/alerts", params={"limit": 50})
        if not data or not data.get("alerts"):
            st.info("No active signals in the feed.")
            return

        for alert in data["alerts"]:
            ticker = alert.get("ticker") or "UNKNOWN"
            alert_name = alert.get("alert_name") or "System Trigger"
            sig_dir = alert.get("signal_direction") or "NEUTRAL"
            status = alert.get("status", "PENDING")
            
            with st.container(border=True):
                col_head, col_badge = st.columns([5, 1])
                with col_head:
                    st.markdown(f"#### {ticker} — {alert_name}")
                with col_badge:
                    st.markdown(get_pill(status, status), unsafe_allow_html=True)
                
                c_data1, c_data2, c_data3 = st.columns(3)
                c_data1.caption(f"**Trigger:** {fmt_price(alert.get('price_at_alert'))}")
                c_data2.caption(f"**Signal:** {sig_dir}")
                c_data3.caption(f"**Interval:** {alert.get('interval', '—')}")
                
                st.markdown(f"<div style='background: #F8FAFC; padding: 12px; border-radius: 6px; font-size: 14px; color: #334155; margin-top: 8px; border-left: 3px solid #3B82F6;'>{alert.get('signal_summary') or alert.get('alert_message') or 'No AI summary available.'}</div>", unsafe_allow_html=True)
                
                if status == "APPROVED" and alert.get("action"):
                    act = alert["action"]
                    st.markdown(f"<div style='margin-top: 12px; font-size: 14px;'><b>Execution:</b> {act.get('primary_call', '')} | <b>Manager Note:</b> <span style='color: #059669;'>{act.get('fm_remarks', 'No notes provided')}</span></div>", unsafe_allow_html=True)

    render_feed()

# ═══════════════════════════════════════════════════════
# PAGE: TRADE DESK (Action Center)
# ═══════════════════════════════════════════════════════
elif page == "✅ Trade Desk":
    st.title("Trade Desk")
    st.markdown("<p style='color: #64748B; margin-top:-15px; margin-bottom: 30px;'>Pending approvals and execution routing.</p>", unsafe_allow_html=True)
    
    col_btn, _ = st.columns([1, 5])
    with col_btn:
        if st.button("🔄 Sync Queue", use_container_width=True): st.rerun()
    
    st.markdown("---")
    
    data = api_call('GET', "/api/alerts", params={"status": "PENDING", "limit": 20})
    
    if not data or not data.get("alerts"):
        st.success("Queue empty. All recommendations processed.")
    else:
        for alert in data["alerts"]:
            with st.container(border=True):
                st.markdown(f"#### {alert.get('ticker', 'UNKNOWN')} {get_pill(alert.get('signal_direction', 'NEUTRAL'), alert.get('signal_direction'))}", unsafe_allow_html=True)
                st.caption(f"**Alert:** {alert.get('alert_name')} | **Price:** {fmt_price(alert.get('price_at_alert'))}")
                st.info(alert.get('signal_summary') or alert.get('alert_message') or "No context provided.")
                
                st.markdown("##### Setup Trade")
                c1, c2, c3 = st.columns(3)
                with c1: action_call = st.selectbox("Action", ["BUY", "SELL", "HOLD", "IGNORE"], key=f"call_{alert['id']}")
                with c2: target_lvl = st.text_input("Target (Optional)", key=f"tgt_{alert['id']}")
                with c3: stop_lvl = st.text_input("Stop Loss (Optional)", key=f"sl_{alert['id']}")
                
                c_txt, c_mic = st.columns([2, 1])
                with c_txt:
                    pov = st.text_area("Manager's Rationale", placeholder="Explain execution logic...", key=f"pov_{alert['id']}")
                with c_mic:
                    audio_b64 = None
                    if hasattr(st, "audio_input"):
                        audio_val = st.audio_input("Record Voice Note", key=f"audio_{alert['id']}")
                        if audio_val: audio_b64 = base64.b64encode(audio_val.read()).decode("utf-8")
                    else:
                        st.warning("Update Streamlit in requirements.txt (>=1.39) for voice feature.")
                        
                c_app, c_den, _ = st.columns([1, 1, 3])
                with c_app:
                    if st.button("Authorize", type="primary", use_container_width=True, key=f"auth_{alert['id']}"):
                        payload = {"alert_id": alert["id"], "decision": "APPROVED", "primary_call": action_call, "fm_rationale_text": pov, "fm_rationale_audio": audio_b64}
                        if target_lvl.replace('.','',1).isdigit(): payload["primary_target_price"] = float(target_lvl)
                        if stop_lvl.replace('.','',1).isdigit(): payload["primary_stop_loss"] = float(stop_lvl)
                        if api_call('POST', f"/api/alerts/{alert['id']}/action", payload):
                            st.success("Authorized.")
                            time.sleep(0.5)
                            st.rerun()
                with c_den:
                    if st.button("Reject", use_container_width=True, key=f"rej_{alert['id']}"):
                        if api_call('POST', f"/api/alerts/{alert['id']}/action", {"alert_id": alert["id"], "decision": "DENIED"}):
                            st.rerun()

# ═══════════════════════════════════════════════════════
# PAGE: PORTFOLIO ANALYTICS (Performance)
# ═══════════════════════════════════════════════════════
elif page == "📈 Portfolio Analytics":
    st.title("Portfolio Analytics")
    st.markdown("<p style='color: #64748B; margin-top:-15px; margin-bottom: 30px;'>Return tracking on executed signals.</p>", unsafe_allow_html=True)
    
    if st.button("🔄 Sync Live Market Data"):
        res = api_call('POST', "/api/performance/refresh")
        if res: st.success(f"Synced {res.get('updated_count')} records.")
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
                "Date Executed": pd.to_datetime(df["approved_at"]).dt.strftime('%d %b %Y')
            })
            st.dataframe(view_df, use_container_width=True, hide_index=True)
    else:
        st.info("No active trades to track.")

# ═══════════════════════════════════════════════════════
# PAGE: MARKET RESEARCH (Ledger)
# ═══════════════════════════════════════════════════════
elif page == "📊 Market Research":
    st.title("System Ledger")
    st.markdown("<p style='color: #64748B; margin-top:-15px; margin-bottom: 30px;'>Complete historical database of all alerts.</p>", unsafe_allow_html=True)
    
    data = api_call('GET', "/api/alerts", params={"limit": 500})
    if data and data.get("alerts"):
        df = pd.DataFrame(data["alerts"])
        display_df = pd.DataFrame({
            "Date": pd.to_datetime(df["received_at"]).dt.strftime('%d %b %Y %H:%M'),
            "Ticker": df["ticker"],
            "Alert": df["alert_name"],
            "Status": df["status"],
            "Signal": df["signal_direction"]
        })
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        with st.expander("Danger Zone"):
            del_id = st.text_input("Enter Alert ID to delete:")
            if st.button("Delete Permanently", type="primary"):
                if del_id.isdigit() and api_call('DELETE', f"/api/alerts/{del_id}"):
                    st.success("Deleted.")
                    time.sleep(0.5)
                    st.rerun()

# ═══════════════════════════════════════════════════════
# PAGE: SETTINGS
# ═══════════════════════════════════════════════════════
elif page == "⚙️ Compliance & Settings":
    st.title("System Configuration")
    
    st.subheader("Webhook Integration")
    st.code(f"{API_BASE}/webhook/tradingview", language="text")
    
    st.subheader("⚠️ Required JSON Template")
    st.markdown("To prevent 'Unknown' errors, you **must** paste this exactly into the TradingView alert Message box:")
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
    "alert_name": "YOUR_STRATEGY_NAME_HERE",
    "signal_direction": "BULLISH",
    "sector": "Equity",
    "alert_message": "YOUR_CUSTOM_RATIONALE",
    "indicator_values": {
        "rsi": 70
    }
}""", language="json")

    st.markdown("---")
    if st.button("Inject Perfect Test Data"):
        if api_call('POST', "/api/test-alert"):
            st.success("Test injected. Go to Command Center to view.")
