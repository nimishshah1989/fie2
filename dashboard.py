import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time
import os
import base64

API_BASE = os.getenv("FIE_API_URL", "http://localhost:8000")
REFRESH_INTERVAL = 3  

st.set_page_config(page_title="JHAVERI | Platform", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    #MainMenu, footer, header[data-testid="stHeader"] { display: none !important; }
    
    /* Sleek UI Adjustments */
    section[data-testid="stSidebar"] { background-color: #0F172A !important; }
    section[data-testid="stSidebar"] * { color: #F8FAFC !important; }
    div[data-testid="stMetric"] { border: 1px solid #E2E8F0; border-radius: 8px; padding: 15px; }
    div[data-testid="stMetric"] label { font-size: 12px !important; color: #64748B !important; text-transform: uppercase; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 24px !important; color: #0F172A !important; }
    .pill { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .pill-green { background: #ECFDF5; color: #059669; border: 1px solid #A7F3D0; }
    .pill-red { background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; }
    .pill-yellow { background: #FFFBEB; color: #D97706; border: 1px solid #FDE68A; }
</style>
""", unsafe_allow_html=True)

def api_call(method, endpoint, data=None, params=None):
    try:
        url = f"{API_BASE}{endpoint}"
        if method == 'GET': r = requests.get(url, params=params, timeout=10)
        elif method == 'POST': r = requests.post(url, json=data, timeout=15)
        elif method == 'DELETE': r = requests.delete(url, timeout=10)
        if r.status_code in [200, 201]: return r.json()
    except Exception: return None

with st.sidebar:
    st.markdown("<h2 style='color:white; margin-bottom:0;'>JHAVERI</h2><p style='color:#94A3B8; font-size:11px; letter-spacing:1px; text-transform:uppercase;'>Intelligence Platform</p>", unsafe_allow_html=True)
    page = st.radio("Nav", ["⚡ Command Center", "✅ Trade Desk", "📈 Portfolio Analytics", "📊 System Ledger", "⚙️ Settings"], label_visibility="collapsed")

if page == "⚡ Command Center":
    st.title("Command Center")
    stats = api_call('GET', "/api/stats") or {}
    c1, c2, c3 = st.columns(3)
    c1.metric("Signals Today", stats.get("total_alerts", 0))
    c2.metric("Actions Pending", stats.get("pending", 0))
    c3.metric("System Alpha", f"{stats.get('avg_return_pct', 0):.2f}%")
    st.markdown("---")

    @st.fragment(run_every=REFRESH_INTERVAL)
    def render_feed():
        data = api_call('GET', "/api/alerts", params={"status": "PENDING", "limit": 20})
        if not data or not data.get("alerts"):
            st.info("No pending signals in the queue.")
            return

        for alert in data["alerts"]:
            with st.container(border=True):
                st.subheader(f"{alert.get('ticker')} — {alert.get('alert_name')}")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.caption(f"**Trigger:** ₹{alert.get('price_at_alert')} | **Sector:** {alert.get('sector', 'N/A')} | **Interval:** {alert.get('interval', 'N/A')}")
                    st.info(alert.get('signal_summary') or "Awaiting AI interpretation...")
                
                with col2:
                    # Classy Action Buttons
                    if st.button("✅ Approve", key=f"app_{alert['id']}", use_container_width=True):
                        api_call('POST', f"/api/alerts/{alert['id']}/action", {"alert_id": alert["id"], "decision": "APPROVED", "primary_call": "BUY"})
                        st.rerun()
                    if st.button("❌ Deny", key=f"den_{alert['id']}", use_container_width=True):
                        api_call('POST', f"/api/alerts/{alert['id']}/action", {"alert_id": alert["id"], "decision": "DENIED"})
                        st.rerun()
                    if st.button("⏱️ Review Later", key=f"rev_{alert['id']}", use_container_width=True):
                        st.toast("Flagged for later review.") # Keeps it pending visually
    render_feed()

elif page == "✅ Trade Desk":
    st.title("Trade Desk")
    st.caption("Execution routing. Auto-sync disabled to prevent data loss.")
    if st.button("🔄 Sync"): st.rerun()
    st.markdown("---")
    
    data = api_call('GET', "/api/alerts", params={"status": "PENDING", "limit": 10})
    if not data or not data.get("alerts"):
        st.success("Inbox Zero.")
    else:
        for alert in data["alerts"]:
            with st.container(border=True):
                st.subheader(f"{alert.get('ticker')} @ ₹{alert.get('price_at_alert')}")
                
                c1, c2 = st.columns(2)
                with c1: call = st.selectbox("Action Call", ["BUY", "SELL", "HOLD"], key=f"call_{alert['id']}")
                with c2: conv = st.selectbox("Conviction", ["HIGH", "MEDIUM", "LOW"], key=f"conv_{alert['id']}")
                
                pov = st.text_area("Manager Rationale", key=f"pov_{alert['id']}")
                
                audio_b64 = None
                if hasattr(st, "audio_input"):
                    audio_val = st.audio_input("Record Voice Note", key=f"audio_{alert['id']}")
                    if audio_val: audio_b64 = base64.b64encode(audio_val.read()).decode()
                
                if st.button("Authorize Execution", type="primary", key=f"auth_{alert['id']}"):
                    api_call('POST', f"/api/alerts/{alert['id']}/action", {
                        "alert_id": alert["id"], "decision": "APPROVED", "primary_call": call, 
                        "conviction": conv, "fm_rationale_text": pov, "fm_rationale_audio": audio_b64
                    })
                    st.success("Authorized.")
                    time.sleep(0.5)
                    st.rerun()

elif page == "📈 Portfolio Analytics":
    st.title("Portfolio Analytics")
    if st.button("🔄 Fetch Live NSE Prices", type="primary"):
        res = api_call('POST', "/api/performance/refresh")
        st.success(f"Prices Updated!")
        time.sleep(1)
        st.rerun()
        
    data = api_call('GET', "/api/performance")
    if data and data.get("performance"):
        df = pd.DataFrame(data["performance"])
        st.dataframe(df, use_container_width=True, hide_index=True)

elif page == "📊 System Ledger":
    st.title("Master System Ledger")
    
    # Filters for the Master Database
    c1, c2 = st.columns(2)
    with c1: f_stat = st.selectbox("Filter Status", ["All", "PENDING", "APPROVED", "DENIED"])
    
    params = {"limit": 500}
    if f_stat != "All": params["status"] = f_stat
    
    data = api_call('GET', "/api/alerts", params=params)
    if data and data.get("alerts"):
        df = pd.DataFrame(data["alerts"])
        view_df = pd.DataFrame({
            "Date": pd.to_datetime(df["received_at"]).dt.strftime('%d %b %Y %H:%M'),
            "Ticker": df["ticker"],
            "Price": df["price_at_alert"].apply(lambda x: f"₹{x:,.2f}" if x else "—"),
            "Signal": df["signal_direction"],
            "Status": df["status"]
        })
        
        # Color Coding the Dataframe
        def color_status(val):
            color = '#059669' if val in ['APPROVED', 'BULLISH'] else '#DC2626' if val in ['DENIED', 'BEARISH'] else '#D97706'
            return f'color: {color}; font-weight: bold'
            
        styled_df = view_df.style.map(color_status, subset=['Signal', 'Status'])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        del_id = st.text_input("Enter Alert ID to Delete")
        if st.button("Delete Permanent"):
            if api_call('DELETE', f"/api/alerts/{del_id}"): st.rerun()

elif page == "⚙️ Settings":
    st.title("Settings")
    st.code(f"Webhook: {API_BASE}/webhook/tradingview")
