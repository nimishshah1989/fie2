"""
FIE Phase 2 — Institutional Execution & Intelligence Feed
Streamlit Frontend
"""

import streamlit as st
import requests
import pandas as pd
import base64
from datetime import datetime
import os

API_BASE = os.getenv("FIE_API_URL", "http://localhost:8000")
REFRESH_INTERVAL = 3  

st.set_page_config(page_title="FIE | Intelligence Feed", layout="wide", initial_sidebar_state="expanded")

# ─── Institutional CSS Overhaul ────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    * { font-family: 'Inter', sans-serif !important; }
    .stApp { background: #f1f5f9 !important; color: #0f172a !important; }
    section[data-testid="stSidebar"] { background: #ffffff !important; border-right: 1px solid #e2e8f0 !important; }
    #MainMenu, footer, header { display: none !important; }
    
    /* Sleek Typography */
    h1, h2, h3 { font-weight: 700 !important; letter-spacing: -0.02em !important; color: #0f172a !important; }
    
    /* Institutional Data Cards */
    .data-card {
        background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px;
        padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }
    .data-card-header {
        display: flex; justify-content: space-between; align-items: center;
        border-bottom: 1px solid #f1f5f9; padding-bottom: 12px; margin-bottom: 12px;
    }
    .ticker-title { font-size: 18px; font-weight: 700; color: #0f172a; }
    .alert-name { font-size: 13px; color: #64748b; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }
    .timestamp { font-family: 'JetBrains Mono', monospace !important; font-size: 11px; color: #94a3b8; }
    
    /* Data Grid */
    .data-grid { display: flex; gap: 24px; font-size: 13px; }
    .data-pair { display: flex; flex-direction: column; }
    .data-label { color: #64748b; font-size: 11px; text-transform: uppercase; font-weight: 600; margin-bottom: 2px; }
    .data-value { font-family: 'JetBrains Mono', monospace !important; color: #0f172a; font-weight: 500; font-size: 14px;}
    
    /* NLP Analysis Box */
    .nlp-box { background: #f8fafc; border-left: 3px solid #3b82f6; padding: 12px 16px; margin-top: 16px; border-radius: 0 4px 4px 0; }
    .nlp-title { font-size: 11px; font-weight: 700; color: #2563eb; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
    .nlp-text { font-size: 14px; color: #334155; line-height: 1.5; }
    
    /* Execution View */
    .exec-box { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 12px 16px; margin-top: 16px; border-radius: 6px; }
    .exec-title { font-size: 11px; font-weight: 700; color: #166534; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
    
    /* Status Pills */
    .pill { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; font-family: 'JetBrains Mono'; }
    .pill-bullish { background: #ecfdf5; color: #059669; border: 1px solid #a7f3d0; }
    .pill-bearish { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
    .pill-pending { background: #fffbeb; color: #d97706; border: 1px solid #fde68a; }
    
    /* Streamlit Overrides */
    .stButton>button { width: 100%; border-radius: 6px; font-weight: 600; }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea { border-radius: 6px; border: 1px solid #cbd5e1; }
    .stTabs [data-baseweb="tab"] { font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ─── Formatters ───────────────────────────────────────────
def f_num(val, decimals=2):
    if val is None or val == "": return "—"
    try: return f"{float(val):,.{decimals}f}"
    except: return "—"

def f_str(val):
    return str(val) if val else "—"

def api_call(method, endpoint, data=None, params=None):
    try:
        url = f"{API_BASE}{endpoint}"
        if method == 'GET': r = requests.get(url, params=params, timeout=10)
        elif method == 'POST': r = requests.post(url, json=data, timeout=15)
        elif method == 'DELETE': r = requests.delete(url, timeout=10)
        if r.status_code in [200, 201]: return r.json()
    except Exception as e: return None

# ─── Navigation ───────────────────────────────────────────
with st.sidebar:
    st.markdown("""
        <div style="padding-bottom: 20px;">
            <div style="font-weight: 800; font-size: 18px; letter-spacing:-0.5px;">JHAVERI FIE</div>
            <div style="color: #64748b; font-size: 11px; font-weight: 600; letter-spacing: 1px;">INTELLIGENCE ENGINE</div>
        </div>
    """, unsafe_allow_html=True)
    page = st.radio("Nav", ["Live Feed", "Execution Desk", "System Ledger", "Performance Matrix", "Settings"], label_visibility="collapsed")
    st.markdown("---")
    st.caption(f"Sync: {REFRESH_INTERVAL}s")

# ═══════════════════════════════════════════════════════
# PAGE: LIVE FEED
# ═══════════════════════════════════════════════════════
if page == "Live Feed":
    st.markdown("### Market Intelligence Feed")
    
    # Stat Bar
    stats = api_call('GET', "/api/stats") or {}
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("System Alpha (Avg)", f"{f_num(stats.get('avg_return_pct', 0))}%")
    with c2: st.metric("Signals Today", stats.get("today_alerts", 0))
    with c3: st.metric("Pending Execution", stats.get("pending", 0))
    with c4: st.metric("Total Intel Processed", stats.get("total_alerts", 0))
    st.markdown("---")

    @st.fragment(run_every=REFRESH_INTERVAL)
    def render_feed():
        data = api_call('GET', "/api/alerts", params={"limit": 50})
        if not data or not data.get("alerts"):
            st.info("No active market signals in the feed.")
            return

        for alert in data["alerts"]:
            # Setup Variables
            ticker = alert.get("ticker") or alert.get("numerator_ticker") or "UNKNOWN"
            price = f_num(alert.get("price_at_alert"))
            sig = str(alert.get("signal_direction", "")).lower()
            sig_class = f"pill-{sig}" if sig in ['bullish', 'bearish'] else "pill-pending"
            sig_text = str(alert.get("signal_direction", "NEUTRAL")).upper()
            status = alert.get("status", "PENDING")
            alert_name = alert.get("alert_name", "System Trigger")
            
            # Format Date
            try: dt = datetime.fromisoformat(alert.get("received_at")).strftime("%d %b, %H:%M:%S")
            except: dt = "—"

            # Render HTML Card
            st.markdown(f"""
            <div class="data-card">
                <div class="data-card-header">
                    <div>
                        <div class="alert-name">{alert_name}</div>
                        <div class="ticker-title">{ticker} <span class="pill {sig_class}" style="margin-left:8px;">{sig_text}</span></div>
                    </div>
                    <div style="text-align: right;">
                        <div class="timestamp">{dt}</div>
                        <div class="pill {'pill-bullish' if status == 'APPROVED' else 'pill-pending'}" style="margin-top:4px;">{status}</div>
                    </div>
                </div>
                
                <div class="data-grid">
                    <div class="data-pair"><span class="data-label">Trigger Price</span><span class="data-value">{price}</span></div>
                    <div class="data-pair"><span class="data-label">Interval</span><span class="data-value">{f_str(alert.get('interval'))}</span></div>
                    <div class="data-pair"><span class="data-label">Sector</span><span class="data-value">{f_str(alert.get('sector'))}</span></div>
                </div>
                
                <div class="nlp-box">
                    <div class="nlp-title">Structural Analysis</div>
                    <div class="nlp-text">{f_str(alert.get('signal_summary'))}</div>
                    <div class="timestamp" style="margin-top: 6px;">Raw: {f_str(alert.get('alert_message'))}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # Render FM Execution if Approved
            if status == "APPROVED" and alert.get("action"):
                act = alert["action"]
                st.markdown(f"""
                <div class="exec-box">
                    <div class="exec-title">Execution Logged</div>
                    <div class="nlp-text"><b>{f_str(act.get('primary_call'))}</b> — {f_str(act.get('fm_remarks'))}</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    render_feed()

# ═══════════════════════════════════════════════════════
# PAGE: EXECUTION DESK (Action Center)
# ═══════════════════════════════════════════════════════
elif page == "Execution Desk":
    st.markdown("### Execution Desk")
    st.caption("Manual Sync Mode Enabled to prevent data loss during execution.")
    
    if st.button("🔄 Sync Feed", use_container_width=False): st.rerun()
    st.markdown("---")
    
    data = api_call('GET', "/api/alerts", params={"status": "PENDING", "limit": 50})
    
    if not data or not data.get("alerts"):
        st.success("Inbox Zero. No pending alerts.")
    else:
        for alert in data["alerts"]:
            ticker = alert.get("ticker") or "UNKNOWN"
            price = f_num(alert.get("price_at_alert"))
            
            with st.container(border=True):
                st.markdown(f"#### {ticker} — {alert.get('alert_name')}")
                st.markdown(f"**Price:** {price} | **Interval:** {alert.get('interval')}")
                st.info(f"**AI Analyst:** {alert.get('signal_summary')}")
                
                st.markdown("##### Log Decision")
                c1, c2, c3 = st.columns(3)
                with c1: 
                    action_call = st.selectbox("Action", ["BUY", "SELL", "HOLD", "IGNORE"], key=f"call_{alert['id']}")
                with c2: 
                    target_lvl = st.text_input("Target (Optional)", placeholder="e.g. 24500", key=f"tgt_{alert['id']}")
                with c3: 
                    stop_lvl = st.text_input("Stop Loss (Optional)", placeholder="e.g. 23900", key=f"sl_{alert['id']}")
                
                # POV & Attachments
                c_text, c_img = st.columns([2, 1])
                with c_text:
                    pov = st.text_area("Manager POV (Thesis)", placeholder="Explain execution logic here...", height=100, key=f"pov_{alert['id']}")
                    
                    # Safe Audio Input (Streamlit 1.39+)
                    audio_b64 = None
                    if hasattr(st, "audio_input"):
                        audio_val = st.audio_input("Or Record Voice Note", key=f"audio_{alert['id']}")
                        if audio_val: audio_b64 = base64.b64encode(audio_val.read()).decode("utf-8")
                    else:
                        st.caption("⚠️ Upgrade Streamlit to >=1.39 for native voice recording.")
                
                with c_img:
                    chart_img = st.file_uploader("Attach Chart", type=["png", "jpg"], key=f"img_{alert['id']}")
                    img_b64 = None
                    if chart_img: img_b64 = base64.b64encode(chart_img.read()).decode("utf-8")
                
                # Submit Block
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("Authorize Execution", type="primary", key=f"auth_{alert['id']}"):
                        payload = {
                            "alert_id": alert["id"],
                            "decision": "APPROVED",
                            "primary_call": action_call,
                            "fm_rationale_text": pov,
                            "fm_rationale_audio": audio_b64,
                            "chart_image_b64": img_b64
                        }
                        # Safely parse optionals
                        if target_lvl.replace('.','',1).isdigit(): payload["primary_target_price"] = float(target_lvl)
                        if stop_lvl.replace('.','',1).isdigit(): payload["primary_stop_loss"] = float(stop_lvl)
                        
                        if api_call('POST', f"/api/alerts/{alert['id']}/action", payload):
                            st.success("Execution Logged.")
                            time.sleep(0.5)
                            st.rerun()
                with col_btn2:
                    if st.button("Reject Signal", key=f"rej_{alert['id']}"):
                        if api_call('POST', f"/api/alerts/{alert['id']}/action", {"alert_id": alert["id"], "decision": "DENIED"}):
                            st.rerun()

# ═══════════════════════════════════════════════════════
# PAGE: SYSTEM LEDGER (Master Database)
# ═══════════════════════════════════════════════════════
elif page == "System Ledger":
    st.markdown("### Master Alert Database")
    st.caption("Complete historical ledger of all signals and executions.")
    
    data = api_call('GET', "/api/alerts", params={"limit": 300})
    if data and data.get("alerts"):
        df = pd.DataFrame(data["alerts"])
        
        # Clean up dataframe for display
        display_df = pd.DataFrame({
            "ID": df["id"],
            "Date": pd.to_datetime(df["received_at"]).dt.strftime('%Y-%m-%d %H:%M'),
            "Ticker": df["ticker"],
            "Price": df["price_at_alert"],
            "Signal": df["signal_direction"],
            "Status": df["status"],
            "Alert Name": df["alert_name"]
        })
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        st.markdown("#### Danger Zone")
        del_id = st.text_input("Enter Alert ID to permanently delete:")
        if st.button("Delete Record"):
            if del_id.isdigit():
                if api_call('DELETE', f"/api/alerts/{del_id}"):
                    st.success("Deleted.")
                    time.sleep(0.5)
                    st.rerun()
    else:
        st.info("Database is empty.")

# ═══════════════════════════════════════════════════════
# PAGE: PERFORMANCE MATRIX
# ═══════════════════════════════════════════════════════
elif page == "Performance Matrix":
    st.markdown("### Portfolio Performance")
    
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 Sync Market Data"):
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
                "Call": df["call"],
                "Entry Price": df["reference_price"].apply(lambda x: f_num(x)),
                "Current Price": df["current_price"].apply(lambda x: f_num(x)),
                "Net %": df["return_pct"].apply(lambda x: f"{x:+.2f}%" if pd.notnull(x) else "—"),
                "Date": pd.to_datetime(df["approved_at"]).dt.strftime('%Y-%m-%d')
            })
            st.dataframe(view_df, use_container_width=True, hide_index=True)
    else:
        st.info("No approved trades to track.")

# ═══════════════════════════════════════════════════════
# PAGE: SETTINGS
# ═══════════════════════════════════════════════════════
elif page == "Settings":
    st.markdown("### Infrastructure Details")
    st.code(f"Webhook URL:\n{API_BASE}/webhook/tradingview", language="text")
    if st.button("Inject Test Data"):
        if api_call('POST', "/api/test-alert"):
            st.success("Test injected.")
