"""
FIE Phase 1 — Fund Manager Alert Intelligence Dashboard
Streamlit Frontend — v2 Professional White Theme
"""

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json
import time
import os
import base64

# ─── Configuration ─────────────────────────────────────
API_BASE = os.getenv("FIE_API_URL", "http://localhost:8000")
REFRESH_INTERVAL = 10  # Auto-refresh every 10 seconds

st.set_page_config(
    page_title="FIE — Alert Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Custom CSS — Professional White Theme ─────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&family=JetBrains+Mono:wght@300;400;500;600&display=swap');

    /* ── Global ── */
    .stApp { background: #F8F9FB !important; }
    .main .block-container {
        padding: 1.2rem 2rem 2rem 2rem !important;
        max-width: 1440px !important;
    }
    * { font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important; }

    /* ── Hide Streamlit UI ── */
    #MainMenu, footer, .stDeployButton { display: none !important; }
    header[data-testid="stHeader"] { background: transparent !important; }
    div[data-testid="stToolbar"] { display: none !important; }
    div[data-testid="stDecoration"] { display: none !important; }
    div[data-testid="stStatusWidget"] { display: none !important; }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background: #FFFFFF !important;
        border-right: 1px solid #E5E7EB !important;
    }
    section[data-testid="stSidebar"] .stRadio label { color: #374151 !important; }
    section[data-testid="stSidebar"] .stMarkdown { color: #1F2937 !important; }

    /* ── Typography ── */
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        font-family: 'DM Sans', sans-serif !important;
        color: #111827 !important;
        font-weight: 700 !important;
    }
    p, span, div, .stMarkdown p { color: #374151; }

    /* ── Stat Cards ── */
    .stat-card {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 14px;
        padding: 22px 20px;
        text-align: center;
        transition: all 0.2s ease;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .stat-card:hover { box-shadow: 0 4px 14px rgba(0,0,0,0.06); transform: translateY(-1px); }
    .stat-value {
        font-size: 30px;
        font-weight: 700;
        font-family: 'DM Sans', sans-serif !important;
    }
    .stat-label {
        font-size: 11px;
        color: #9CA3AF;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-family: 'JetBrains Mono', monospace !important;
        margin-top: 6px;
        font-weight: 500;
    }

    /* ── Alert Cards ── */
    .alert-card {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 14px;
        padding: 22px 26px;
        margin-bottom: 14px;
        border-left: 4px solid transparent;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        transition: all 0.2s ease;
    }
    .alert-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.06); }
    .alert-card.bullish { border-left-color: #10B981; }
    .alert-card.bearish { border-left-color: #EF4444; }
    .alert-card.neutral { border-left-color: #F59E0B; }
    .alert-card.pending { box-shadow: 0 0 0 1px rgba(245, 158, 11, 0.15); }

    .alert-ticker {
        font-size: 18px;
        font-weight: 700;
        color: #111827;
        font-family: 'DM Sans', sans-serif !important;
    }
    .alert-time {
        font-size: 11px;
        color: #9CA3AF;
        font-family: 'JetBrains Mono', monospace !important;
    }
    .alert-meta {
        display: flex;
        gap: 16px;
        margin-bottom: 8px;
        font-size: 12px;
        color: #6B7280;
        font-family: 'JetBrains Mono', monospace !important;
    }
    .alert-body {
        font-size: 14px;
        color: #4B5563;
        line-height: 1.6;
    }

    /* ── Badges ── */
    .badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace !important;
        letter-spacing: 0.5px;
    }
    .badge-pending { background: #FEF3C7; color: #92400E; }
    .badge-approved { background: #D1FAE5; color: #065F46; }
    .badge-denied { background: #FEE2E2; color: #991B1B; }

    .indicator-chip {
        display: inline-block;
        background: #F3F4F6;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 4px 12px;
        margin: 2px 4px 2px 0;
        font-size: 12px;
        font-family: 'JetBrains Mono', monospace !important;
        color: #4B5563;
    }
    .sector-tag {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 20px;
        font-size: 11px;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 600;
        background: #EFF6FF;
        color: #2563EB;
        letter-spacing: 0.3px;
    }
    .relative-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 10px;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 600;
        background: #F3E8FF;
        color: #7C3AED;
        letter-spacing: 0.3px;
        margin-left: 8px;
    }

    /* ── Header ── */
    .fie-header {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 16px;
        padding: 28px 32px;
        margin-bottom: 24px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }
    .fie-title {
        font-size: 26px;
        font-weight: 800;
        color: #111827;
        font-family: 'DM Sans', sans-serif !important;
    }
    .fie-subtitle {
        font-size: 12px;
        color: #9CA3AF;
        font-family: 'JetBrains Mono', monospace !important;
        letter-spacing: 2px;
        margin-bottom: 2px;
    }

    /* ── Filter Bar ── */
    .filter-bar {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 14px;
        padding: 16px 24px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        background: #F3F4F6;
        border-radius: 12px;
        padding: 4px;
        border: 1px solid #E5E7EB;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 9px;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 500;
        font-size: 14px;
        color: #6B7280;
        padding: 8px 20px;
    }
    .stTabs [aria-selected="true"] {
        background: #111827 !important;
        color: #FFFFFF !important;
        font-weight: 600;
    }
    .stTabs [data-baseweb="tab-highlight"] { display: none; }
    .stTabs [data-baseweb="tab-border"] { display: none; }

    /* ── Buttons ── */
    .stButton > button {
        border-radius: 10px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 0.5rem 1.4rem !important;
        border: 1px solid #E5E7EB !important;
        background: #FFFFFF !important;
        color: #374151 !important;
        transition: all 0.15s ease !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
    }
    .stButton > button:hover {
        background: #F9FAFB !important;
        border-color: #D1D5DB !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
    }
    .stButton > button[kind="primary"] {
        background: #111827 !important;
        color: #FFFFFF !important;
        border-color: #111827 !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: #1F2937 !important;
    }

    /* ── Select / Input ── */
    div[data-testid="stSelectbox"] > div > div,
    div[data-testid="stMultiSelect"] > div > div {
        background: #FFFFFF !important;
        border: 1px solid #E5E7EB !important;
        border-radius: 10px !important;
        color: #374151 !important;
    }
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: 10px !important;
        border: 1px solid #E5E7EB !important;
        background: #FFFFFF !important;
    }
    .stNumberInput > div > div > input {
        border-radius: 10px !important;
        border: 1px solid #E5E7EB !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* ── Expander ── */
    .streamlit-expanderHeader {
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 600 !important;
        background: #FFFFFF !important;
        border: 1px solid #E5E7EB !important;
        border-radius: 12px !important;
    }

    /* ── Metrics ── */
    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 16px 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    div[data-testid="stMetric"] label {
        color: #9CA3AF !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        letter-spacing: 0.05em !important;
        text-transform: uppercase !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #111827 !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* ── Dataframes ── */
    .stDataFrame { border: 1px solid #E5E7EB !important; border-radius: 12px !important; overflow: hidden; }

    /* ── Dividers ── */
    hr { border-color: #F3F4F6 !important; }

    /* ── Live dot ── */
    .live-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        background: #10B981;
        border-radius: 50%;
        margin-right: 6px;
        animation: pulse-dot 2s ease-in-out infinite;
    }
    @keyframes pulse-dot {
        0%, 100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
        50% { box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #D1D5DB; border-radius: 3px; }

    /* ── Info / Success / Warning boxes ── */
    .stAlert { border-radius: 12px !important; border: 1px solid #E5E7EB !important; }
</style>
""", unsafe_allow_html=True)


# ─── Helpers ───────────────────────────────────────────

def api_get(endpoint, params=None):
    try:
        r = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return None

def api_post(endpoint, data=None):
    try:
        r = requests.post(f"{API_BASE}{endpoint}", json=data, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return None

def api_delete(endpoint):
    try:
        r = requests.delete(f"{API_BASE}{endpoint}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return None

def fmt(val, prefix="", decimals=2):
    if val is None: return "—"
    if isinstance(val, (int, float)):
        return f"{prefix}{val:,.{decimals}f}"
    return str(val)

def signal_emoji(d):
    return {"BULLISH": "🟢", "BEARISH": "🔴"}.get(d, "🟡")

def status_badge(s):
    m = {"PENDING": ("badge-pending", "⏳"), "APPROVED": ("badge-approved", "✅"), "DENIED": ("badge-denied", "❌")}
    c, i = m.get(s, ("badge-pending", "❓"))
    return f'<span class="badge {c}">{i} {s}</span>'

def time_ago(dt_str):
    try:
        dt = datetime.fromisoformat(dt_str)
        diff = datetime.now() - dt
        if diff.seconds < 60: return "just now"
        if diff.seconds < 3600: return f"{diff.seconds // 60}m ago"
        if diff.seconds < 86400: return f"{diff.seconds // 3600}h ago"
        return f"{diff.days}d ago"
    except: return ""


# ─── Top Navigation ───────────────────────────────────

nav_left, nav_right = st.columns([3, 1])
with nav_left:
    st.markdown("""
    <div style="display:flex; align-items:center; gap:12px; padding:4px 0 16px;">
        <span style="font-size:22px; font-weight:800; color:#111827; font-family:'DM Sans';">⚡ FIE</span>
        <span style="font-size:11px; color:#9CA3AF; font-family:'JetBrains Mono'; letter-spacing:2px; padding-top:3px;">JHAVERI SECURITIES</span>
    </div>
    """, unsafe_allow_html=True)
with nav_right:
    st.markdown(f"""
    <div style="text-align:right; padding:8px 0 16px;">
        <span class="live-dot"></span>
        <span style="font-size:12px; color:#6B7280; font-family:'JetBrains Mono';">
            Live · Refreshes every {REFRESH_INTERVAL}s
        </span>
    </div>
    """, unsafe_allow_html=True)

page = st.radio(
    "nav",
    ["📊 Live Alerts", "✅ Action Center", "📈 Performance", "⚙️ Settings"],
    horizontal=True,
    label_visibility="collapsed",
)


# ═══════════════════════════════════════════════════════
# PAGE: LIVE ALERTS
# ═══════════════════════════════════════════════════════

if page == "📊 Live Alerts":

    # ── Inline Filter Bar (static — does NOT refresh) ──
    st.markdown('<div class="filter-bar">', unsafe_allow_html=True)
    fc1, fc2, fc3, fc4, fc5 = st.columns([1.2, 1.2, 1.2, 1.2, 1.5])

    sectors_data = api_get("/api/sectors")
    sector_list = ["All"] + (sectors_data.get("sectors", []) if sectors_data else [])

    with fc1:
        filter_status = st.selectbox("Status", ["All", "PENDING", "APPROVED", "DENIED"], key="f_status")
    with fc2:
        filter_signal = st.selectbox("Signal", ["All", "BULLISH", "BEARISH", "NEUTRAL"], key="f_signal")
    with fc3:
        filter_type = st.selectbox("Alert Type", ["All", "ABSOLUTE", "RELATIVE"], key="f_type")
    with fc4:
        filter_sector = st.selectbox("Sector", sector_list, key="f_sector")
    with fc5:
        filter_search = st.text_input("🔍 Search ticker or message", "", key="f_search")
    st.markdown('</div>', unsafe_allow_html=True)

    # Build filter params
    fp = {}
    if filter_status != "All": fp["status"] = filter_status
    if filter_signal != "All": fp["signal_direction"] = filter_signal
    if filter_type != "All": fp["alert_type"] = filter_type
    if filter_sector != "All": fp["sector"] = filter_sector
    if filter_search: fp["search"] = filter_search

    # ── Auto-refreshing data section (Background Fragment) ──
    @st.fragment(run_every=REFRESH_INTERVAL)
    def live_alerts_data():
        # ── Stats Row ──
        stats = api_get("/api/stats")
        if stats:
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            for col, val, lbl, clr in [
                (c1, stats.get('total_alerts', 0), "Total Alerts", "#2563EB"),
                (c2, stats.get('pending', 0), "Pending", "#F59E0B"),
                (c3, stats.get('today_alerts', 0), "Today", "#0891B2"),
                (c4, stats.get('bullish_count', 0), "Bullish", "#10B981"),
                (c5, stats.get('bearish_count', 0), "Bearish", "#EF4444"),
            ]:
                with col:
                    st.markdown(f'<div class="stat-card"><div class="stat-value" style="color:{clr};">{val}</div><div class="stat-label">{lbl}</div></div>', unsafe_allow_html=True)
            with c6:
                ar = stats.get('avg_return_pct', 0) or 0
                rc = "#10B981" if ar >= 0 else "#EF4444"
                st.markdown(f'<div class="stat-card"><div class="stat-value" style="color:{rc};">{ar:+.1f}%</div><div class="stat-label">Avg Return</div></div>', unsafe_allow_html=True)

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

        # ── Alert List ──
        alerts_data = api_get("/api/alerts", params=fp)

        if alerts_data and alerts_data.get("alerts"):
            alerts = alerts_data["alerts"]
            st.markdown(f"""
            <div style="margin-bottom:16px;">
                <span style="font-size:14px; color:#6B7280;">{alerts_data.get('total', len(alerts))} alerts matching filters</span>
            </div>
            """, unsafe_allow_html=True)

            for alert in alerts:
                sig = alert.get("signal_direction", "NEUTRAL")
                sig_class = sig.lower() if sig else "neutral"
                status = alert.get("status", "PENDING")
                pend_class = " pending" if status == "PENDING" else ""

                # Ticker display
                ticker_d = alert.get("ticker") or "Unknown"
                type_badge = ""
                if alert.get("alert_type") == "RELATIVE":
                    num = alert.get("numerator_ticker", "?")
                    den = alert.get("denominator_ticker", "?")
                    if num and den:
                        ticker_d = f"{num} / {den}"
                    type_badge = '<span class="relative-badge">RELATIVE</span>'

                # Indicators
                ind_html = ""
                if alert.get("indicator_values"):
                    for k, v in alert["indicator_values"].items():
                        vf = f"{v:.1f}" if isinstance(v, (int, float)) else str(v)
                        ind_html += f'<span class="indicator-chip">{k.upper()}: {vf}</span>'

                # Time
                received = alert.get("received_at", "")
                try:
                    dt = datetime.fromisoformat(received)
                    time_str = dt.strftime("%d %b %Y, %H:%M")
                except:
                    time_str = received

                # Sector & Price
                sec_html = f'<span class="sector-tag">{alert["sector"]}</span>' if alert.get("sector") else ""

                if alert.get("alert_type") == "RELATIVE":
                    price = f"Ratio: {(alert.get('ratio_value') or alert.get('price_at_alert') or 0):.4f}"
                else:
                    price_val = alert.get('price_at_alert')
                    price = f"Rs. {price_val if price_val is not None else 0:,.2f}"

                st.markdown(f"""
                <div class="alert-card {sig_class}{pend_class}">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
                        <div>
                            <span class="alert-ticker">{signal_emoji(sig)} {ticker_d}</span>{type_badge} {sec_html}
                        </div>
                        <div style="text-align:right;">
                            {status_badge(status)}<br>
                            <span class="alert-time">{time_str} · {time_ago(received)}</span>
                        </div>
                    </div>
                    <div class="alert-meta">
                        <span>📊 {alert.get('interval', '—')}</span>
                        <span>💰 {price}</span>
                        <span>📈 {alert.get('exchange', '—')}</span>
                    </div>
                    <div class="alert-body">
                        <strong>{alert.get('alert_name', '')}</strong><br>
                        {alert.get('signal_summary', alert.get('alert_message', 'No details'))}
                    </div>
                    {f'<div style="margin-top:10px;">{ind_html}</div>' if ind_html else ''}
                </div>
                """, unsafe_allow_html=True)

                # Quick actions for pending alerts
                if status == "PENDING":
                    c1, c2, c3, c4 = st.columns([2.5, 1, 1, 1])
                    with c1:
                        st.caption(f"Alert #{alert['id']}")
                    with c2:
                        if st.button("✅ Approve", key=f"qa_{alert['id']}"):
                            result = api_post(f"/api/alerts/{alert['id']}/action", {
                                "alert_id": alert["id"],
                                "decision": "APPROVED",
                                "primary_call": "BUY" if sig == "BULLISH" else "SELL" if sig == "BEARISH" else "WATCH",
                                "conviction": "MEDIUM",
                            })
                            if result and result.get("success"):
                                st.success("✅ Approved!")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("Failed to approve. Use Action Center for detailed approval.")
                    with c3:
                        if st.button("✖ Deny", key=f"qd_{alert['id']}"):
                            api_post(f"/api/alerts/{alert['id']}/action", {"alert_id": alert["id"], "decision": "DENIED"})
                            st.rerun()
                    with c4:
                        if st.button("🗑️ Delete", key=f"del_{alert['id']}"):
                            result = api_delete(f"/api/alerts/{alert['id']}")
                            if result and result.get("success"):
                                st.rerun()
                            else:
                                st.error("Delete failed.")
                else:
                    # Non-pending alerts still get a delete option
                    c1, c2 = st.columns([5, 1])
                    with c1:
                        if status == "APPROVED" and alert.get("action"):
                            a = alert["action"]
                            parts = []
                            if a.get("primary_call"): parts.append(f"**{a.get('primary_ticker','?')}**: {a['primary_call']}")
                            if a.get("secondary_call"): parts.append(f"**{a.get('secondary_ticker','?')}**: {a['secondary_call']}")
                            if parts:
                                st.caption(f"FM: {' | '.join(parts)} · {a.get('conviction', '—')}")
                    with c2:
                        if st.button("🗑️", key=f"del_{alert['id']}", help="Delete this alert permanently"):
                            result = api_delete(f"/api/alerts/{alert['id']}")
                            if result and result.get("success"):
                                st.rerun()
                            else:
                                st.error("Delete failed.")
        else:
            st.markdown("""
            <div style="text-align:center; padding:60px 40px; color:#9CA3AF;">
                <div style="font-size:3rem; margin-bottom:16px;">📭</div>
                <div style="font-size:1rem; font-weight:600; color:#6B7280;">No alerts yet</div>
                <div style="font-size:0.85rem; margin-top:6px;">Configure your TradingView webhook or load test alerts from Settings.</div>
            </div>
            """, unsafe_allow_html=True)

    # Call the fragment
    live_alerts_data()


# ═══════════════════════════════════════════════════════
# PAGE: ACTION CENTER (Manual Refresh Only)
# ═══════════════════════════════════════════════════════

elif page == "✅ Action Center":
    st.markdown("""
    <div class="fie-header">
        <div class="fie-subtitle">FUND MANAGER DECISION CONSOLE</div>
        <div class="fie-title">Action Center</div>
    </div>
    """, unsafe_allow_html=True)

    pending_data = api_get("/api/alerts", params={"status": "PENDING", "limit": 100})

    if pending_data and pending_data.get("alerts"):
        pending = pending_data["alerts"]
        
        col_title, col_sync = st.columns([4, 1])
        with col_title:
            st.markdown(f"### ⏳ {len(pending)} Alerts Awaiting Decision")
        with col_sync:
            if st.button("🔄 Sync New Alerts", use_container_width=True):
                st.rerun()

        for alert in pending:
            is_rel = alert.get("alert_type") == "RELATIVE"

            with st.expander(
                f"{signal_emoji(alert.get('signal_direction'))} "
                f"{'[R] ' if is_rel else ''}"
                f"{alert.get('ticker', '?')} — {alert.get('alert_name', 'Alert')}",
                expanded=True
            ):
                col_info, col_act = st.columns([3, 2])

                with col_info:
                    st.info(alert.get("signal_summary", "No summary"))
                    if alert.get("alert_message"):
                        st.markdown(f"**Message:** {alert['alert_message']}")

                    mc = st.columns(4)
                    for i, (lbl, key) in enumerate([("Price", "price_at_alert"), ("Open", "price_open"), ("High", "price_high"), ("Low", "price_low")]):
                        with mc[i]:
                            if is_rel:
                                st.metric(lbl, fmt(alert.get(key), decimals=4))
                            else:
                                st.metric(lbl, fmt(alert.get(key), prefix="Rs. "))

                    if alert.get("indicator_values"):
                        st.markdown("**Indicators:**")
                        st.dataframe(pd.DataFrame([alert["indicator_values"]]), use_container_width=True)

                    if is_rel:
                        st.markdown("**Relative Alert Details:**")
                        rc = st.columns(3)
                        with rc[0]: st.metric(f"Num: {alert.get('numerator_ticker','?')}", fmt(alert.get("numerator_price"), prefix="Rs. "))
                        with rc[1]: st.metric(f"Den: {alert.get('denominator_ticker','?')}", fmt(alert.get("denominator_price"), prefix="Rs. "))
                        with rc[2]: st.metric("Ratio", fmt(alert.get("ratio_value"), decimals=4))

                with col_act:
                    st.markdown("### 🎯 Take Action")
                    decision = st.radio("Decision", ["APPROVED", "DENIED"], horizontal=True, key=f"dec_{alert['id']}")

                    payload = {"alert_id": alert["id"], "decision": decision}

                    if decision == "APPROVED":
                        actions = ["BUY", "SELL", "HOLD", "STRONG_BUY", "STRONG_SELL", "OVERBOUGHT", "OVERSOLD", "EXIT", "ACCUMULATE", "REDUCE", "WATCH"]

                        ptk = alert.get("ticker", "?")
                        st.markdown(f"**📌 {ptk}:**")
                        pc = st.selectbox("Action on Instrument", actions, key=f"pc_{alert['id']}", label_visibility="collapsed")
                        pn = st.text_input("Notes", key=f"pn_{alert['id']}", placeholder="Optional...")

                        pc1, pc2 = st.columns(2)
                        with pc1: pt = st.number_input("Target Level", value=0.0, key=f"pt_{alert['id']}", format="%.4f")
                        with pc2: ps = st.number_input("Stop Loss", value=0.0, key=f"ps_{alert['id']}", format="%.4f")

                        payload.update({"primary_call": pc, "primary_notes": pn or None, "primary_target_price": pt if pt > 0 else None, "primary_stop_loss": ps if ps > 0 else None})

                        # ─── New AI Processed Voice/Text Input Section ───
                        st.markdown("---")
                        st.markdown("##### 🧠 Fund Manager Rationale (AI Processed)")
                        st.caption("Speak or type your thesis. The AI will synthesize it into a formal record.")

                        col_text, col_voice = st.columns([1, 1])
                        with col_text:
                            thesis_text = st.text_area("Type your rationale...", placeholder="E.g., Bouncing off the 200 EMA...", key=f"tt_{alert['id']}")
                        with col_voice:
                            thesis_audio = st.audio_input("🎙️ Record Voice Note", key=f"ta_{alert['id']}")

                        audio_b64 = None
                        if thesis_audio:
                            audio_b64 = base64.b64encode(thesis_audio.read()).decode("utf-8")

                        conv = st.select_slider("Conviction", ["LOW", "MEDIUM", "HIGH"], value="MEDIUM", key=f"cv_{alert['id']}")

                        payload.update({
                            "conviction": conv,
                            "fm_rationale_text": thesis_text,
                            "fm_rationale_audio": audio_b64
                        })
                        # ──────────────────────────────────────────────────

                    btn_label = "✅ Approve & Submit" if decision == "APPROVED" else "❌ Deny Alert"
                    if st.button(btn_label, key=f"sub_{alert['id']}", type="primary" if decision == "APPROVED" else "secondary", use_container_width=True):
                        result = api_post(f"/api/alerts/{alert['id']}/action", payload)
                        if result and result.get("success"):
                            st.success(f"✅ {decision}")
                            time.sleep(0.5)
                            st.rerun()
    else:
        st.markdown("""
        <div style="text-align:center; padding:60px 40px;">
            <div style="font-size:3rem; margin-bottom:16px;">🎉</div>
            <div style="font-size:1.1rem; font-weight:600; color:#111827;">All caught up!</div>
            <div style="font-size:0.85rem; margin-top:6px; color:#9CA3AF;">No pending alerts. Use 'Sync New Alerts' to check for updates.</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔄 Sync New Alerts", use_container_width=True):
            st.rerun()

    # Recently actioned
    st.markdown("---")
    st.markdown("### 📋 Recently Actioned")
    recent = api_get("/api/alerts", params={"limit": 20})
    if recent and recent.get("alerts"):
        actioned = [a for a in recent["alerts"] if a.get("status") != "PENDING"][:10]
        if actioned:
            for a in actioned:
                act = a.get("action") or {}
                call = act.get("primary_call", "—")
                st.markdown(f"{signal_emoji(a.get('signal_direction'))} **{a.get('ticker','?')}** — {status_badge(a.get('status'))} → {call} ({act.get('conviction', '—')})<br><span style='font-size:12px; color:#6B7280;'>{act.get('fm_remarks', '')}</span>", unsafe_allow_html=True)
        else:
            st.caption("No actioned alerts yet.")


# ═══════════════════════════════════════════════════════
# PAGE: PERFORMANCE
# ═══════════════════════════════════════════════════════

elif page == "📈 Performance":
    st.markdown("""
    <div class="fie-header">
        <div class="fie-subtitle">APPROVED ALERT PERFORMANCE TRACKING</div>
        <div class="fie-title">Performance Tracker</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Auto-refreshing data section (Background Fragment) ──
    @st.fragment(run_every=REFRESH_INTERVAL)
    def performance_data():
        perf_data = api_get("/api/performance", params={"limit": 100})
        stats = api_get("/api/stats")

        if stats:
            mc1, mc2, mc3, mc4 = st.columns(4)
            with mc1:
                st.markdown(f'<div class="stat-card"><div class="stat-value" style="color:#10B981;">{stats.get("approved",0)}</div><div class="stat-label">Approved Calls</div></div>', unsafe_allow_html=True)
            with mc2:
                ar = stats.get("avg_return_pct", 0) or 0
                rc = "#10B981" if ar >= 0 else "#EF4444"
                st.markdown(f'<div class="stat-card"><div class="stat-value" style="color:{rc};">{ar:+.1f}%</div><div class="stat-label">Avg Return</div></div>', unsafe_allow_html=True)
            with mc3:
                wr = stats.get("win_rate", 0) or 0
                wc = "#10B981" if wr >= 50 else "#EF4444"
                st.markdown(f'<div class="stat-card"><div class="stat-value" style="color:{wc};">{wr:.0f}%</div><div class="stat-label">Win Rate</div></div>', unsafe_allow_html=True)
            with mc4:
                tp = stats.get("top_performer", {}).get("return_pct", 0) or 0
                st.markdown(f'<div class="stat-card"><div class="stat-value" style="color:#10B981;">{tp:+.1f}%</div><div class="stat-label">Best Return</div></div>', unsafe_allow_html=True)

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

        if perf_data and perf_data.get("performance"):
            perfs = perf_data["performance"]
            df = pd.DataFrame(perfs)

            if not df.empty:
                tab1, tab2, tab3 = st.tabs(["📊 Performance Table", "📈 Returns Chart", "🏆 Sector Analysis"])

                with tab1:
                    display_cols = ["ticker", "call", "conviction", "reference_price", "current_price", "return_pct", "approved_at"]
                    avail_cols = [c for c in display_cols if c in df.columns]
                    display_df = df[avail_cols].copy()

                    col_names = {
                        "ticker": "Ticker/Ratio", "call": "Call", "conviction": "Conv.",
                        "reference_price": "Entry Level", "current_price": "Current Level",
                        "return_pct": "Net Return %", "approved_at": "Approved Date"
                    }
                    display_df = display_df.rename(columns={k: v for k, v in col_names.items() if k in display_df.columns})

                    if "Approved Date" in display_df.columns:
                        display_df["Approved Date"] = pd.to_datetime(display_df["Approved Date"]).dt.strftime('%Y-%m-%d %H:%M')

                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        height=min(600, 50 + len(display_df) * 35),
                        column_config={
                            "Net Return %": st.column_config.NumberColumn(format="%.2f%%"),
                            "Entry Level": st.column_config.NumberColumn(format="%.4f"),
                            "Current Level": st.column_config.NumberColumn(format="%.4f"),
                        }
                    )

                with tab2:
                    if "return_pct" in df.columns and "ticker" in df.columns:
                        chart_df = df[["ticker", "return_pct", "call"]].dropna(subset=["return_pct"]).sort_values("return_pct", ascending=True)

                        if not chart_df.empty:
                            colors = ["#10B981" if x >= 0 else "#EF4444" for x in chart_df["return_pct"]]

                            fig = go.Figure(go.Bar(
                                y=chart_df["ticker"],
                                x=chart_df["return_pct"],
                                orientation="h",
                                marker_color=colors,
                                text=[f"{x:+.2f}%" for x in chart_df["return_pct"]],
                                textposition="outside",
                                hovertemplate="<b>%{y}</b><br>Return: %{x:.2f}%<extra></extra>",
                            ))

                            fig.update_layout(
                                title="Returns by Alert (Total since Approval)",
                                paper_bgcolor="#FFFFFF",
                                plot_bgcolor="#FAFBFC",
                                font=dict(family="DM Sans", color="#374151"),
                                height=max(400, len(chart_df) * 35),
                                xaxis_title="Return %",
                                yaxis_title="",
                                showlegend=False,
                                margin=dict(l=120, r=60, t=50, b=40),
                                xaxis=dict(gridcolor="#F3F4F6", zerolinecolor="#E5E7EB"),
                                yaxis=dict(gridcolor="#F3F4F6"),
                            )

                            st.plotly_chart(fig, use_container_width=True)

                with tab3:
                    if "sector" in df.columns:
                        sector_df = df.groupby("sector").agg(
                            count=("return_pct", "count"),
                            avg_return=("return_pct", "mean"),
                            max_return=("return_pct", "max"),
                            min_return=("return_pct", "min"),
                        ).reset_index()

                        if not sector_df.empty:
                            colors_map = {
                                "Banking": "#2563EB", "Information Technology": "#0891B2",
                                "Broad Market": "#7C3AED", "Pharma & Healthcare": "#10B981",
                                "FMCG": "#F59E0B", "Automobile": "#EF4444"
                            }

                            fig2 = go.Figure()
                            fig2.add_trace(go.Bar(
                                x=sector_df["sector"],
                                y=sector_df["avg_return"],
                                name="Avg Return",
                                marker_color=[colors_map.get(s, "#6B7280") for s in sector_df["sector"]],
                                text=[f"{x:.1f}%" for x in sector_df["avg_return"]],
                                textposition="outside",
                            ))

                            fig2.update_layout(
                                title="Average Return by Sector",
                                paper_bgcolor="#FFFFFF",
                                plot_bgcolor="#FAFBFC",
                                font=dict(family="DM Sans", color="#374151"),
                                height=450,
                                yaxis_title="Return %",
                                margin=dict(l=60, r=40, t=50, b=40),
                                xaxis=dict(gridcolor="#F3F4F6"),
                                yaxis=dict(gridcolor="#F3F4F6", zerolinecolor="#E5E7EB"),
                            )

                            st.plotly_chart(fig2, use_container_width=True)

                            st.dataframe(sector_df.rename(columns={
                                "sector": "Sector", "count": "Alerts", "avg_return": "Avg %",
                                "max_return": "Best %", "min_return": "Worst %"
                            }), use_container_width=True)
        else:
            st.markdown("""
            <div style="text-align:center; padding:60px 40px;">
                <div style="font-size:3rem; margin-bottom:16px;">📊</div>
                <div style="font-size:1rem; font-weight:600; color:#111827;">No performance data yet</div>
                <div style="font-size:0.85rem; margin-top:6px; color:#9CA3AF;">Approve alerts first — tracking begins automatically via TradingView Heartbeats.</div>
            </div>
            """, unsafe_allow_html=True)

    # Call the fragment
    performance_data()


# ═══════════════════════════════════════════════════════
# PAGE: SETTINGS
# ═══════════════════════════════════════════════════════

elif page == "⚙️ Settings":
    st.markdown("""
    <div class="fie-header">
        <div class="fie-subtitle">SYSTEM CONFIGURATION</div>
        <div class="fie-title">Settings & Webhook Setup</div>
    </div>
    """, unsafe_allow_html=True)

    # System status
    health = api_get("/health")
    if health:
        st.markdown(f"""
        <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:12px; padding:14px 20px; margin-bottom:24px; display:flex; align-items:center; gap:10px;">
            <span class="live-dot"></span>
            <span style="font-size:14px; color:#166534; font-weight:600;">Backend Online</span>
            <span style="font-size:12px; color:#6B7280; margin-left:auto; font-family:'JetBrains Mono';">{health.get('timestamp', '')}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.error("❌ Critical: Backend engine is unreachable. Ensure the server is online.")

    # Quick actions
    col_qa1, col_qa2, col_qa3 = st.columns(3)
    with col_qa1:
        if st.button("🔄 Force Refresh Cache", use_container_width=True):
            st.rerun()
    with col_qa2:
        if st.button("📥 Load Test Alerts", use_container_width=True):
            result = api_post("/api/test-alert")
            if result and result.get("success"):
                st.success(f"✅ {result['count']} test alerts injected!")
                time.sleep(1)
                st.rerun()
    with col_qa3:
        st.markdown(f"""
        <div style="background:#F3F4F6; border-radius:10px; padding:10px 16px; text-align:center;">
            <span style="font-size:12px; color:#6B7280;">Background Sync: <strong>{REFRESH_INTERVAL}s</strong></span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("### 🔗 Webhook Configuration")
    st.markdown(f"""
    **Your TradingView Webhook URL:**
    ```
    {API_BASE}/webhook/tradingview
    ```
    """)

    st.markdown("---")
    st.markdown("### 📝 Alert Message Templates")

    tab_abs, tab_rel, tab_hb = st.tabs(["Single Asset Alert", "Relative Ratio Alert", "💓 Daily Heartbeat"])

    with tab_abs:
        st.markdown("Use this for **single ticker** alerts (Nifty, Stocks):")
        st.code("""{
    "ticker": "{{ticker}}",
    "exchange": "{{exchange}}",
    "interval": "{{interval}}",
    "close": "{{close}}",
    "timenow": "{{timenow}}",
    "alert_name": "YOUR_ALERT_NAME",
    "signal": "BULLISH",
    "message": "YOUR_CUSTOM_MESSAGE"
}""", language="json")

    with tab_rel:
        st.markdown("Use this for **relative ratio** charts (e.g. GOLD/SENSEX):")
        st.code("""{
    "ticker": "{{ticker}}",
    "exchange": "{{exchange}}",
    "interval": "{{interval}}",
    "close": "{{close}}",
    "timenow": "{{timenow}}",
    "alert_type": "RELATIVE",
    "alert_name": "YOUR_RATIO_ALERT",
    "signal": "BEARISH",
    "message": "Ratio dropping, initiate pair trade."
}""", language="json")

    with tab_hb:
        st.markdown("""
        **Crucial for Performance Tracking:** Set up a daily alert on the Daily Timeframe
        (Trigger: 'Once Per Bar Close') for every asset and ratio you monitor.
        This acts as the daily price feed instead of relying on external APIs.
        """)
        st.code("""{
    "is_heartbeat": true,
    "ticker": "{{ticker}}",
    "close": "{{close}}",
    "time": "{{timenow}}"
}""", language="json")

    st.markdown("---")
    st.markdown("### 🏗️ TradingView Setup Guide")
    st.markdown("""
    **Step 1:** Open your TradingView chart with the index/ratio.

    **Step 2:** Click the alert icon (🔔) or press `Alt + A`.

    **Step 3:** Set your condition (e.g., RSI crosses above 70).

    **Step 4:** In **Alert Actions**, check **Webhook URL** and paste your webhook link.

    **Step 5:** In the **Message** field, paste the correct JSON template. Replace placeholder values.

    **Step 6:** Click **Create** — the alert will now silently route to your dashboard!
    """)
