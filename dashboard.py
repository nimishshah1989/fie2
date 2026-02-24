import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time
import os
import base64

API_BASE = os.getenv("FIE_API_URL", "http://localhost:8000")

st.set_page_config(page_title="JHAVERI | Intelligence", layout="wide", initial_sidebar_state="expanded")

# ─── Claude UI CSS Override ───
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif !important; }
    .stApp { background-color: #F8F9FA !important; }
    #MainMenu, footer, header[data-testid="stHeader"] { display: none !important; }
    
    /* Navy Sidebar */
    section[data-testid="stSidebar"] { background-color: #0F172A !important; border-right: none !important; }
    section[data-testid="stSidebar"] * { color: #F8FAFC !important; }
    
    /* KPI Metrics */
    div[data-testid="stMetric"] { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 15px 20px; box-shadow: 0 1px 2px rgba(0,0,0,0.03); }
    div[data-testid="stMetric"] label { font-size: 13px !important; color: #64748B !important; font-weight: 500 !important; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 28px !important; color: #0F172A !important; font-weight: 700 !important; }
    
    /* Typography */
    h1 { color: #0F172A !important; font-size: 24px !important; font-weight: 700 !important; letter-spacing: -0.5px !important; margin-bottom: 5px !important; }
    
    /* Status Pills */
    .pill { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-left: 8px; }
    .pill-green { background: #ECFDF5; color: #059669; border: 1px solid #A7F3D0; }
    .pill-red { background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; }
    .pill-yellow { background: #FFFBEB; color: #D97706; border: 1px solid #FDE68A; }
    
    /* Alert Cards */
    .alert-card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 16px; margin-bottom: 12px; }
    .alert-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #F1F5F9; padding-bottom: 10px; margin-bottom: 10px; }
    .ai-box { background: #F8FAFC; border-left: 3px solid #3B82F6; padding: 12px; border-radius: 0 4px 4px 0; font-size: 14px; color: #334155; margin-top: 10px;}
</style>
""", unsafe_allow_html=True)

def api_call(method, endpoint, data=None, params=None):
    try:
        url = f"{API_BASE}{endpoint}"
        if method == 'GET': r = requests.get(url, params=params, timeout=10)
        elif method == 'POST': r = requests.post(url, json=data, timeout=15)
        if r.status_code in [200, 201]: return r.json()
    except Exception: return None

with st.sidebar:
    st.markdown("<div style='padding: 10px 0 30px;'><div style='font-size:20px; font-weight:800; letter-spacing:-0.5px;'>JHAVERI</div><div style='font-size:10px; color:#94A3B8; text-transform:uppercase; letter-spacing:1px;'>Intelligence Platform</div></div>", unsafe_allow_html=True)
    page = st.radio("Nav", ["⚡ Command Center", "✅ Trade Desk", "📈 Portfolio Analytics", "⚙️ Integrations"], label_visibility="collapsed")
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    if st.button("🔄 Sync Engine"): st.rerun()

if page == "⚡ Command Center":
    st.markdown("<h1>Command Center</h1><p style='color:#64748B; font-size:14px;'>Real-time systemic signals and market intelligence.</p>", unsafe_allow_html=True)
    
    stats = api_call('GET', "/api/stats") or {}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Signals Today", stats.get("total_alerts", 0))
    c2.metric("Actions Pending", f'{stats.get("pending", 0)} Items')
    c3.metric("System Alpha", f"{stats.get('avg_return_pct', 0.0):.2f}%")
    c4.metric("Market Status", "OPEN")
    st.markdown("<br>", unsafe_allow_html=True)

    data = api_call('GET', "/api/alerts", params={"limit": 50})
    if not data or not data.get("alerts"):
        st.info("No active signals in the feed.")
    else:
        for alert in data["alerts"]:
            color = "green" if alert.get("signal_direction") == "BULLISH" else "red" if alert.get("signal_direction") == "BEARISH" else "yellow"
            status_pill = "<span class='pill pill-yellow'>PENDING</span>" if alert.get("status") == "PENDING" else f"<span class='pill pill-green'>ACTIONED</span>"
            
            st.markdown(f"""
            <div class="alert-card">
                <div class="alert-header">
                    <div style="font-weight: 700; font-size: 16px; color: #0F172A;">{alert.get('ticker')} — {alert.get('alert_name')} <span class="pill pill-{color}">{alert.get('signal_direction', 'NEUTRAL')}</span></div>
                    <div style="font-size: 12px; color: #94A3B8;">{alert.get('received_at', '')[:16].replace('T', ' ')} {status_pill}</div>
                </div>
                <div style="font-size: 13px; color: #64748B;"><b>Trigger Level:</b> ₹{alert.get('price_at_alert', 0):,.2f} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Interval:</b> {alert.get('interval', '1D')}</div>
                <div class="ai-box"><b>AI Analyst:</b> {alert.get('signal_summary', 'No summary generated.')}</div>
            </div>
            """, unsafe_allow_html=True)
            
            if alert.get("status") == "PENDING":
                if st.button("Route to Trade Desk ➔", key=f"route_{alert['id']}"):
                    st.toast("Signal routed to Trade Desk for execution.")

elif page == "✅ Trade Desk":
    st.markdown("<h1>Trade Desk</h1><p style='color:#64748B; font-size:14px;'>Execution routing and rationale capture.</p>", unsafe_allow_html=True)
    
    st.markdown("### ⏳ Pending Execution Queue")
    data = api_call('GET', "/api/alerts", params={"status": "PENDING", "limit": 20})
    if not data or not data.get("alerts"):
        st.success("Queue is completely clear.")
    else:
        for alert in data["alerts"]:
            with st.container(border=True):
                st.markdown(f"**{alert.get('ticker')}** @ ₹{alert.get('price_at_alert', 0):,.2f} <span class='pill pill-yellow'>{alert.get('signal_direction')}</span>", unsafe_allow_html=True)
                st.info(alert.get('signal_summary'))
                
                c1, c2 = st.columns([3, 1])
                with c1: pov = st.text_area("Investment Rationale", placeholder="Why are we taking this trade?", key=f"pov_{alert['id']}")
                with c2:
                    call = st.selectbox("Action", ["BUY", "SELL", "HOLD", "IGNORE"], key=f"call_{alert['id']}")
                    if st.button("✅ Authorize", type="primary", use_container_width=True, key=f"auth_{alert['id']}"):
                        api_call('POST', f"/api/alerts/{alert['id']}/action", {"alert_id": alert["id"], "decision": "APPROVED", "primary_call": call, "fm_rationale_text": pov})
                        st.rerun()

    st.markdown("---")
    st.markdown("### 📋 Historical Executions")
    hist_data = api_call('GET', "/api/alerts", params={"status": "APPROVED", "limit": 10})
    if hist_data and hist_data.get("alerts"):
        for alert in hist_data["alerts"]:
            act = alert.get("action", {})
            st.markdown(f"**{alert.get('ticker')}** ➔ {act.get('call', '—')} | <span style='color:#059669; font-size:13px;'>{act.get('remarks', 'No notes.')}</span>", unsafe_allow_html=True)

elif page == "📈 Portfolio Analytics":
    st.markdown("<h1>Portfolio Analytics</h1><p style='color:#64748B; font-size:14px;'>Live performance of systemic executions.</p>", unsafe_allow_html=True)
    
    if st.button("🔄 Refresh Live NSE Prices", type="primary"):
        api_call('POST', "/api/performance/refresh")
        st.rerun()
        
    data = api_call('GET', "/api/performance")
    if data and data.get("performance"):
        df = pd.DataFrame(data["performance"])
        view_df = pd.DataFrame({
            "Execution Date": pd.to_datetime(df["approved_at"]).dt.strftime('%d %b %Y'),
            "Asset": df["ticker"],
            "Entry Price": df["reference_price"].apply(lambda x: f"₹{x:,.2f}" if x else "—"),
            "Live Price": df["current_price"].apply(lambda x: f"₹{x:,.2f}" if x else "Syncing..."),
            "Net %": df["return_pct"].apply(lambda x: f"{x:+.2f}%" if pd.notnull(x) else "—"),
        })
        st.dataframe(view_df, use_container_width=True, hide_index=True)
    else:
        st.info("No active trades to track.")

elif page == "⚙️ Integrations":
    st.markdown("<h1>Integrations</h1>", unsafe_allow_html=True)
    st.code(f"Webhook: {API_BASE}/webhook/tradingview")
