"""
FIE Phase 1 — Fund Manager Alert Intelligence Dashboard
Streamlit Frontend
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

# ─── Configuration ─────────────────────────────────────
API_BASE = os.getenv("FIE_API_URL", "http://localhost:8000")

st.set_page_config(page_title="FIE — Alert Intelligence", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# ─── Custom CSS ────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600&family=Outfit:wght@300;400;500;600;700;800&display=swap');
    .stApp { background: #0a0e17; }
    section[data-testid="stSidebar"] { background: #111827; border-right: 1px solid #1e2d3d; }
    .stApp header { background: transparent !important; }
    #MainMenu, footer, .stDeployButton { visibility: hidden; }
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { font-family: 'Outfit', sans-serif !important; color: #f8fafc !important; }
    p, span, div, .stMarkdown p { font-family: 'Outfit', sans-serif; }
    .stat-card { background: linear-gradient(135deg, #111827, #1a2332); border: 1px solid #1e2d3d; border-radius: 12px; padding: 20px; text-align: center; }
    .stat-value { font-size: 32px; font-weight: 800; font-family: 'Outfit'; }
    .stat-label { font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 2px; font-family: 'JetBrains Mono'; margin-top: 4px; }
    .alert-card { background: #111827; border: 1px solid #1e2d3d; border-radius: 14px; padding: 20px; margin-bottom: 12px; border-left: 4px solid transparent; }
    .alert-card.bullish { border-left-color: #10b981; }
    .alert-card.bearish { border-left-color: #ef4444; }
    .alert-card.neutral { border-left-color: #f59e0b; }
    .alert-card.pending { box-shadow: 0 0 0 1px rgba(245, 158, 11, 0.2); }
    .alert-ticker { font-size: 20px; font-weight: 700; color: #f8fafc; font-family: 'Outfit'; }
    .alert-time { font-size: 11px; color: #64748b; font-family: 'JetBrains Mono'; }
    .badge { padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; font-family: 'JetBrains Mono'; letter-spacing: 1px; }
    .badge-pending { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
    .badge-approved { background: rgba(16, 185, 129, 0.15); color: #10b981; }
    .badge-denied { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
    .indicator-chip { display: inline-block; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 4px 10px; margin: 2px; font-size: 12px; font-family: 'JetBrains Mono'; color: #94a3b8; }
    .sector-tag { display: inline-block; padding: 3px 10px; border-radius: 4px; font-size: 11px; font-family: 'JetBrains Mono'; background: rgba(59, 130, 246, 0.15); color: #3b82f6; letter-spacing: 1px; }
    .relative-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-family: 'JetBrains Mono'; background: rgba(139, 92, 246, 0.15); color: #8b5cf6; letter-spacing: 1px; margin-left: 8px; }
    .fie-header { background: linear-gradient(135deg, rgba(59, 130, 246, 0.08), rgba(6, 182, 212, 0.05)); border: 1px solid rgba(59, 130, 246, 0.2); border-radius: 16px; padding: 24px 30px; margin-bottom: 24px; }
    .fie-title { font-size: 28px; font-weight: 800; background: linear-gradient(135deg, #e2e8f0, #3b82f6, #06b6d4); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-family: 'Outfit'; }
    .fie-subtitle { font-size: 13px; color: #64748b; font-family: 'JetBrains Mono'; letter-spacing: 2px; }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; background: #111827; border-radius: 12px; padding: 4px; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px; font-family: 'Outfit'; }
    .stTabs [aria-selected="true"] { background: #3b82f6 !important; color: white !important; }
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


# ─── Sidebar ───────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 10px 0 20px;">
        <div style="font-size: 24px; font-weight: 800; font-family: 'Outfit'; color: #f8fafc;">⚡ FIE</div>
        <div style="font-size: 11px; color: #3b82f6; font-family: 'JetBrains Mono'; letter-spacing: 3px;">ALERT INTELLIGENCE</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    
    page = st.radio("Navigation", ["📊 Live Alerts", "✅ Action Center", "📈 Performance", "⚙️ Settings"], label_visibility="collapsed")
    
    st.markdown("---")
    st.markdown("**Filters**")
    filter_status = st.selectbox("Status", ["All", "PENDING", "APPROVED", "DENIED"])
    filter_signal = st.selectbox("Signal", ["All", "BULLISH", "BEARISH", "NEUTRAL"])
    filter_type = st.selectbox("Alert Type", ["All", "ABSOLUTE", "RELATIVE"])
    
    sectors_data = api_get("/api/sectors")
    sector_list = ["All"] + (sectors_data.get("sectors", []) if sectors_data else [])
    filter_sector = st.selectbox("Sector", sector_list)
    filter_search = st.text_input("🔍 Search", "")
    
    st.markdown("---")
    st.markdown("**Quick Actions**")
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()
    if st.button("📥 Load Test Alerts", use_container_width=True):
        result = api_post("/api/test-alert")
        if result and result.get("success"):
            st.success(f"✅ {result['count']} test alerts created!")
            time.sleep(1)
            st.rerun()
    if st.button("📊 Update Performance", use_container_width=True):
        with st.spinner("Fetching live prices..."):
            result = api_post("/api/performance/refresh")
            if result:
                st.success(f"✅ {result.get('updated_count', 0)} updated")
                time.sleep(1)
                st.rerun()

# Build filter params
fp = {}
if filter_status != "All": fp["status"] = filter_status
if filter_signal != "All": fp["signal_direction"] = filter_signal
if filter_type != "All": fp["alert_type"] = filter_type
if filter_sector != "All": fp["sector"] = filter_sector
if filter_search: fp["search"] = filter_search


# ═══════════════════════════════════════════════════════
# PAGE: LIVE ALERTS
# ═══════════════════════════════════════════════════════

if page == "📊 Live Alerts":
    st.markdown("""
    <div class="fie-header">
        <div class="fie-subtitle">JHAVERI SECURITIES — FINANCIAL INTELLIGENCE ENGINE</div>
        <div class="fie-title">Live Alert Monitor</div>
    </div>
    """, unsafe_allow_html=True)
    
    stats = api_get("/api/stats")
    if stats:
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        for col, val, lbl, clr in [
            (c1, stats['total_alerts'], "Total Alerts", "#3b82f6"),
            (c2, stats['pending'], "Pending", "#f59e0b"),
            (c3, stats['today_alerts'], "Today", "#06b6d4"),
            (c4, stats['bullish_count'], "Bullish", "#10b981"),
            (c5, stats['bearish_count'], "Bearish", "#ef4444"),
        ]:
            with col:
                st.markdown(f'<div class="stat-card"><div class="stat-value" style="color:{clr};">{val}</div><div class="stat-label">{lbl}</div></div>', unsafe_allow_html=True)
        with c6:
            ar = stats.get('avg_return_pct', 0)
            rc = "#10b981" if ar >= 0 else "#ef4444"
            st.markdown(f'<div class="stat-card"><div class="stat-value" style="color:{rc};">{ar:+.1f}%</div><div class="stat-label">Avg Return</div></div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    alerts_data = api_get("/api/alerts", params=fp)
    
    if alerts_data and alerts_data.get("alerts"):
        alerts = alerts_data["alerts"]
        st.markdown(f"**{alerts_data['total']} alerts** matching filters")
        
        for alert in alerts:
            sig = alert.get("signal_direction", "NEUTRAL")
            sig_class = sig.lower() if sig else "neutral"
            status = alert.get("status", "PENDING")
            pend_class = " pending" if status == "PENDING" else ""
            
            # Ticker
            ticker_d = alert.get("ticker") or "Unknown"
            type_badge = ""
            if alert.get("alert_type") == "RELATIVE":
                num = alert.get("numerator_ticker", "?")
                den = alert.get("denominator_ticker", "?")
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
            price = f"₹{alert['price_at_alert']:,.2f}" if alert.get("price_at_alert") else (f"Ratio: {alert['ratio_value']:.4f}" if alert.get("ratio_value") else "—")
            
            st.markdown(f"""
            <div class="alert-card {sig_class}{pend_class}">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <div><span class="alert-ticker">{signal_emoji(sig)} {ticker_d}</span>{type_badge} {sec_html}</div>
                    <div style="text-align:right;">{status_badge(status)}<br><span class="alert-time">{time_str} · {time_ago(received)}</span></div>
                </div>
                <div style="display:flex; gap:16px; margin-bottom:8px; font-size:12px; color:#64748b; font-family:'JetBrains Mono';">
                    <span>📊 {alert.get('interval', '—')}</span>
                    <span>💰 {price}</span>
                    <span>📈 {alert.get('exchange', '—')}</span>
                </div>
                <div style="font-size:14px; color:#cbd5e1; line-height:1.5;">
                    <strong>{alert.get('alert_name', '')}</strong><br>
                    {alert.get('signal_summary', alert.get('alert_message', 'No details'))}
                </div>
                {f'<div style="margin-top:8px;">{ind_html}</div>' if ind_html else ''}
            </div>
            """, unsafe_allow_html=True)
            
            if status == "PENDING":
                c1, c2, c3 = st.columns([3, 1, 1])
                with c1:
                    st.caption(f"Alert #{alert['id']}")
                with c2:
                    if st.button("✅ Approve", key=f"qa_{alert['id']}"):
                        st.session_state[f"approve_{alert['id']}"] = True
                with c3:
                    if st.button("❌ Deny", key=f"qd_{alert['id']}"):
                        api_post(f"/api/alerts/{alert['id']}/action", {"alert_id": alert["id"], "decision": "DENIED"})
                        st.rerun()
            elif status == "APPROVED" and alert.get("action"):
                a = alert["action"]
                parts = []
                if a.get("primary_call"): parts.append(f"**{a.get('primary_ticker','?')}**: {a['primary_call']}")
                if a.get("secondary_call"): parts.append(f"**{a.get('secondary_ticker','?')}**: {a['secondary_call']}")
                if parts:
                    st.caption(f"FM: {' | '.join(parts)} · {a.get('conviction', '—')}")
            st.markdown("---")
    else:
        st.info("📭 No alerts yet. Click **Load Test Alerts** in the sidebar or configure your TradingView webhook.")


# ═══════════════════════════════════════════════════════
# PAGE: ACTION CENTER
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
        st.markdown(f"### ⏳ {len(pending)} Alerts Awaiting Decision")
        
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
                            st.metric(lbl, fmt(alert.get(key), prefix="₹"))
                    
                    if alert.get("indicator_values"):
                        st.markdown("**Indicators:**")
                        st.dataframe(pd.DataFrame([alert["indicator_values"]]), use_container_width=True)
                    
                    if is_rel:
                        st.markdown("**Relative Alert Details:**")
                        rc = st.columns(3)
                        with rc[0]: st.metric(f"Num: {alert.get('numerator_ticker','?')}", fmt(alert.get("numerator_price"), prefix="₹"))
                        with rc[1]: st.metric(f"Den: {alert.get('denominator_ticker','?')}", fmt(alert.get("denominator_price"), prefix="₹"))
                        with rc[2]: st.metric("Ratio", fmt(alert.get("ratio_value"), decimals=4))
                
                with col_act:
                    st.markdown("### 🎯 Take Action")
                    decision = st.radio("Decision", ["APPROVED", "DENIED"], horizontal=True, key=f"dec_{alert['id']}")
                    
                    payload = {"alert_id": alert["id"], "decision": decision}
                    
                    if decision == "APPROVED":
                        actions = ["BUY", "SELL", "HOLD", "STRONG_BUY", "STRONG_SELL", "OVERBOUGHT", "OVERSOLD", "EXIT", "ACCUMULATE", "REDUCE", "WATCH"]
                        
                        ptk = alert.get("numerator_ticker") or alert.get("ticker", "?")
                        st.markdown(f"**📌 {ptk}:**")
                        pc = st.selectbox("Primary Call", actions, key=f"pc_{alert['id']}", label_visibility="collapsed")
                        pn = st.text_input("Notes", key=f"pn_{alert['id']}", placeholder="Optional...")
                        
                        pc1, pc2 = st.columns(2)
                        with pc1: pt = st.number_input("Target ₹", value=0.0, key=f"pt_{alert['id']}", format="%.2f")
                        with pc2: ps = st.number_input("Stop Loss ₹", value=0.0, key=f"ps_{alert['id']}", format="%.2f")
                        
                        payload.update({"primary_call": pc, "primary_notes": pn or None, "primary_target_price": pt if pt > 0 else None, "primary_stop_loss": ps if ps > 0 else None})
                        
                        if is_rel:
                            st.markdown("---")
                            dtk = alert.get("denominator_ticker", "?")
                            st.markdown(f"**📌 {dtk}:**")
                            sc = st.selectbox("Secondary Call", actions, key=f"sc_{alert['id']}", label_visibility="collapsed")
                            sn = st.text_input("Notes", key=f"sn_{alert['id']}", placeholder="Optional...")
                            
                            sc1, sc2 = st.columns(2)
                            with sc1: stt = st.number_input("Target ₹", value=0.0, key=f"st_{alert['id']}", format="%.2f")
                            with sc2: ss = st.number_input("Stop Loss ₹", value=0.0, key=f"ss_{alert['id']}", format="%.2f")
                            
                            payload.update({"secondary_call": sc, "secondary_notes": sn or None, "secondary_target_price": stt if stt > 0 else None, "secondary_stop_loss": ss if ss > 0 else None})
                        
                        st.markdown("---")
                        conv = st.select_slider("Conviction", ["LOW", "MEDIUM", "HIGH"], value="MEDIUM", key=f"cv_{alert['id']}")
                        remarks = st.text_area("Remarks", key=f"rm_{alert['id']}", placeholder="Reasoning...", height=60)
                        payload.update({"conviction": conv, "fm_remarks": remarks or None})
                    
                    btn = "✅ Approve & Submit" if decision == "APPROVED" else "❌ Deny Alert"
                    if st.button(btn, key=f"sub_{alert['id']}", type="primary" if decision == "APPROVED" else "secondary", use_container_width=True):
                        result = api_post(f"/api/alerts/{alert['id']}/action", payload)
                        if result and result.get("success"):
                            st.success(f"✅ {decision}")
                            time.sleep(0.5)
                            st.rerun()
    else:
        st.success("🎉 No pending alerts! All caught up.")
    
    # Recently actioned
    st.markdown("---")
    st.markdown("### 📋 Recently Actioned")
    recent = api_get("/api/alerts", params={"limit": 20})
    if recent and recent.get("alerts"):
        actioned = [a for a in recent["alerts"] if a.get("status") != "PENDING"][:10]
        for a in actioned:
            act = a.get("action") or {}
            call = act.get("primary_call", "—")
            st.markdown(f"{signal_emoji(a.get('signal_direction'))} **{a.get('ticker','?')}** — {status_badge(a.get('status'))} → {call} ({act.get('conviction', '—')})", unsafe_allow_html=True)


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
    
    perf_data = api_get("/api/performance", params={"limit": 100})
    stats = api_get("/api/stats")
    
    if stats:
        mc1, mc2, mc3, mc4 = st.columns(4)
        with mc1:
            st.markdown(f'<div class="stat-card"><div class="stat-value" style="color:#10b981;">{stats.get("approved",0)}</div><div class="stat-label">Approved Calls</div></div>', unsafe_allow_html=True)
        with mc2:
            ar = stats.get("avg_return_pct", 0)
            rc = "#10b981" if ar >= 0 else "#ef4444"
            st.markdown(f'<div class="stat-card"><div class="stat-value" style="color:{rc};">{ar:+.1f}%</div><div class="stat-label">Avg Return</div></div>', unsafe_allow_html=True)
        with mc3:
            wr = stats.get("win_rate", 0)
            wc = "#10b981" if wr >= 50 else "#ef4444"
            st.markdown(f'<div class="stat-card"><div class="stat-value" style="color:{wc};">{wr:.0f}%</div><div class="stat-label">Win Rate</div></div>', unsafe_allow_html=True)
        with mc4:
            tp = stats.get("top_performer", {}).get("return_pct", 0) or 0
            st.markdown(f'<div class="stat-card"><div class="stat-value" style="color:#10b981;">{tp:+.1f}%</div><div class="stat-label">Best Return</div></div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if perf_data and perf_data.get("performance"):
        perfs = perf_data["performance"]
        
        # Performance table
        df = pd.DataFrame(perfs)
        
        if not df.empty:
            # Tabs: Table view and Chart view
            tab1, tab2, tab3 = st.tabs(["📊 Performance Table", "📈 Returns Chart", "🏆 Sector Analysis"])
            
            with tab1:
                # Format for display
                display_cols = ["ticker", "call", "conviction", "reference_price", "current_price", "return_pct", "return_1d", "return_1w", "return_1m", "return_3m", "return_6m", "max_drawdown", "approved_at"]
                avail_cols = [c for c in display_cols if c in df.columns]
                display_df = df[avail_cols].copy()
                
                # Rename columns
                col_names = {
                    "ticker": "Ticker", "call": "Call", "conviction": "Conv.",
                    "reference_price": "Entry ₹", "current_price": "Current ₹",
                    "return_pct": "Total %", "return_1d": "1D %", "return_1w": "1W %",
                    "return_1m": "1M %", "return_3m": "3M %", "return_6m": "6M %",
                    "max_drawdown": "Max DD %", "approved_at": "Approved"
                }
                display_df = display_df.rename(columns={k: v for k, v in col_names.items() if k in display_df.columns})
                
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    height=min(600, 50 + len(display_df) * 35),
                    column_config={
                        "Total %": st.column_config.NumberColumn(format="%.2f%%"),
                        "1D %": st.column_config.NumberColumn(format="%.2f%%"),
                        "1W %": st.column_config.NumberColumn(format="%.2f%%"),
                        "1M %": st.column_config.NumberColumn(format="%.2f%%"),
                        "3M %": st.column_config.NumberColumn(format="%.2f%%"),
                        "6M %": st.column_config.NumberColumn(format="%.2f%%"),
                        "Max DD %": st.column_config.NumberColumn(format="%.2f%%"),
                        "Entry ₹": st.column_config.NumberColumn(format="₹%.2f"),
                        "Current ₹": st.column_config.NumberColumn(format="₹%.2f"),
                    }
                )
            
            with tab2:
                # Returns bar chart
                if "return_pct" in df.columns and "ticker" in df.columns:
                    chart_df = df[["ticker", "return_pct", "call"]].dropna(subset=["return_pct"]).sort_values("return_pct", ascending=True)
                    
                    if not chart_df.empty:
                        colors = ["#10b981" if x >= 0 else "#ef4444" for x in chart_df["return_pct"]]
                        
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
                            template="plotly_dark",
                            paper_bgcolor="#0a0e17",
                            plot_bgcolor="#111827",
                            font=dict(family="Outfit", color="#e2e8f0"),
                            height=max(400, len(chart_df) * 35),
                            xaxis_title="Return %",
                            yaxis_title="",
                            showlegend=False,
                            margin=dict(l=120),
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
            
            with tab3:
                # Sector analysis
                if "sector" in df.columns:
                    sector_df = df.groupby("sector").agg(
                        count=("return_pct", "count"),
                        avg_return=("return_pct", "mean"),
                        max_return=("return_pct", "max"),
                        min_return=("return_pct", "min"),
                    ).reset_index()
                    
                    if not sector_df.empty:
                        fig2 = go.Figure()
                        
                        colors_map = {"Banking": "#3b82f6", "Information Technology": "#06b6d4", "Broad Market": "#8b5cf6", "Pharma & Healthcare": "#10b981", "FMCG": "#f59e0b", "Automobile": "#ef4444"}
                        
                        fig2.add_trace(go.Bar(
                            x=sector_df["sector"],
                            y=sector_df["avg_return"],
                            name="Avg Return",
                            marker_color=[colors_map.get(s, "#64748b") for s in sector_df["sector"]],
                            text=[f"{x:.1f}%" for x in sector_df["avg_return"]],
                            textposition="outside",
                        ))
                        
                        fig2.update_layout(
                            title="Average Return by Sector",
                            template="plotly_dark",
                            paper_bgcolor="#0a0e17",
                            plot_bgcolor="#111827",
                            font=dict(family="Outfit", color="#e2e8f0"),
                            height=450,
                            yaxis_title="Return %",
                        )
                        
                        st.plotly_chart(fig2, use_container_width=True)
                        
                        st.dataframe(sector_df.rename(columns={
                            "sector": "Sector", "count": "Alerts", "avg_return": "Avg %",
                            "max_return": "Best %", "min_return": "Worst %"
                        }), use_container_width=True)
        else:
            st.info("No performance data yet. Approve some alerts and click **Update Performance**.")
    else:
        st.info("📊 No performance data. Approve alerts first, then click **Update Performance** in sidebar.")


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
    
    st.markdown("### 🔗 Webhook Configuration")
    st.markdown(f"""
    **Your TradingView Webhook URL:**
    ```
    {API_BASE}/webhook/tradingview
    ```
    
    Copy this URL into your TradingView alert's **Webhook URL** field.
    """)
    
    st.markdown("---")
    st.markdown("### 📝 Recommended Alert Message Templates")
    
    templates = api_get("/api/webhook-template")
    if templates:
        tab_abs, tab_rel = st.tabs(["Single Index/Stock Alert", "Relative (Two Index) Alert"])
        
        with tab_abs:
            st.markdown("Use this template for **single ticker** alerts (Nifty, Bank Nifty, individual stocks, etc.):")
            st.code(templates.get("template", ""), language="json")
        
        with tab_rel:
            st.markdown("Use this template for **relative/ratio** alerts (e.g., Nifty IT vs Nifty 50):")
            st.code(templates.get("template_relative", ""), language="json")
    
    st.markdown("---")
    st.markdown("### 🏗️ TradingView Setup Guide")
    st.markdown("""
    **Step 1:** Open your TradingView chart with the index/indicator
    
    **Step 2:** Click the alert icon (🔔) or press `Alt + A`
    
    **Step 3:** Set your condition (e.g., RSI crosses above 70)
    
    **Step 4:** In the **Alert Actions** section, check **Webhook URL** and paste:
    """)
    st.code(f"{API_BASE}/webhook/tradingview")
    st.markdown("""
    **Step 5:** In the **Message** field, paste the JSON template from above. Replace placeholder values with TradingView's built-in variables (`{{close}}`, `{{ticker}}`, etc.) or your indicator values.
    
    **Step 6:** Click **Create** — the alert will now send data to your FIE dashboard when triggered!
    
    ---
    
    ### 📊 Supported TradingView Variables
    
    | Variable | Description |
    |----------|-------------|
    | `{{ticker}}` | Symbol name |
    | `{{exchange}}` | Exchange |
    | `{{close}}` | Current close price |
    | `{{open}}` | Current open price |
    | `{{high}}` | Current high |
    | `{{low}}` | Current low |
    | `{{volume}}` | Current volume |
    | `{{time}}` | Bar time UTC |
    | `{{timenow}}` | Current time UTC |
    | `{{interval}}` | Timeframe |
    """)
    
    st.markdown("---")
    st.markdown("### 🔧 System Status")
    health = api_get("/health")
    if health:
        st.success(f"✅ Backend: {health.get('status', 'unknown')} — {health.get('timestamp', '')}")
    else:
        st.error("❌ Backend not reachable. Make sure the server is running.")
    
    st.markdown(f"**API URL:** `{API_BASE}`")
    st.markdown(f"**Database:** SQLite (local)")
