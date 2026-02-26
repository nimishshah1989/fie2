import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import time
import os
import json
import streamlit.components.v1 as components

API_BASE = os.getenv("FIE_API_URL", "http://localhost:8000")

st.set_page_config(page_title="Jhaveri Intelligence", layout="wide", initial_sidebar_state="expanded")

REFRESH_INTERVAL = 30

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; }
    .stApp { background: #FAFBFC !important; }
    #MainMenu, footer { display: none !important; }
    .block-container { padding-top: 1.5rem !important; max-width: 1400px !important; }
    div[data-testid="stMetric"] {
        background: #FFFFFF; border: 1px solid #E8ECF1; border-radius: 8px;
        padding: 16px; box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }
    div[data-testid="stMetric"] label { font-size: 11px !important; color: #64748B !important; font-weight: 700 !important; text-transform: uppercase !important; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 22px !important; color: #0F172A !important; font-weight: 800 !important; }
    .empty-state { text-align: center; padding: 40px 20px; color: #94A3B8; }
    [data-testid="stVerticalBlockBorderWrapper"] { 
        padding: 16px !important; border-radius: 10px !important; 
        background: #FFFFFF !important; box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
        border-color: #E8ECF1 !important;
    }
    .stButton button { padding: 4px 12px !important; font-size: 13px !important; font-weight: 600 !important; height: auto !important; min-height: 32px !important; }
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
    except Exception:
        pass
    return None

def fmt_price(val):
    if val is None or val == 0: return "—"
    try: return f"{float(val):,.2f}"
    except: return "—"

def now_ist():
    return datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)

def fmt_ist(iso_str):
    if not iso_str: return "—"
    try:
        dt = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
        ist_dt = dt + timedelta(hours=5, minutes=30)
        return ist_dt.strftime("%d-%b %I:%M %p").lower()
    except: return str(iso_str)[:16]

def asset_pill(asset_class):
    a = str(asset_class).strip().upper()
    if a in ["NONE", "NULL", "", "—"]: a = "EQUITY"
    colors = {"COMMODITY": ("#FFFBEB","#B45309","#FDE68A"), "CURRENCY": ("#ECFDF5","#059669","#A7F3D0"),
              "INDEX": ("#F3E8FF","#7E22CE","#D8B4FE")}
    bg, tc, br = colors.get(a, ("#EFF6FF","#2563EB","#BFDBFE"))
    return f"<span style='background:{bg}; color:{tc}; border:1px solid {br}; padding:2px 7px; border-radius:5px; font-size:9px; font-weight:800; letter-spacing:0.5px;'>{a}</span>"

def signal_pill(direction):
    d = str(direction or "NEUTRAL").upper()
    if d == "BULLISH": return "<span style='color:#059669; background:#ECFDF5; border:1px solid #A7F3D0; padding:2px 7px; border-radius:5px; font-size:9px; font-weight:700;'>BULLISH</span>"
    if d == "BEARISH": return "<span style='color:#DC2626; background:#FEF2F2; border:1px solid #FECACA; padding:2px 7px; border-radius:5px; font-size:9px; font-weight:700;'>BEARISH</span>"
    return "<span style='color:#64748B; background:#F1F5F9; border:1px solid #E2E8F0; padding:2px 7px; border-radius:5px; font-size:9px; font-weight:700;'>NEUTRAL</span>"

def stat_pill(s):
    s = str(s or "PENDING").upper()
    if s == "PENDING": return "<span style='color:#B45309; background:#FFFBEB; border:1px solid #FDE68A; padding:2px 8px; border-radius:100px; font-size:9px; font-weight:700;'>PENDING</span>"
    if s == "APPROVED": return "<span style='color:#059669; background:#ECFDF5; border:1px solid #A7F3D0; padding:2px 8px; border-radius:100px; font-size:9px; font-weight:700;'>APPROVED</span>"
    if s == "DENIED": return "<span style='color:#DC2626; background:#FEF2F2; border:1px solid #FECACA; padding:2px 8px; border-radius:100px; font-size:9px; font-weight:700;'>DENIED</span>"
    return f"<span style='color:#64748B; background:#F1F5F9; border:1px solid #E2E8F0; padding:2px 8px; border-radius:100px; font-size:9px; font-weight:700;'>{s}</span>"

def confluence_bar(bull, bear):
    try:
        b = int(bull or 0); s = int(bear or 0)
        bp = b / 10 * 100; sp = s / 10 * 100
        return f"""<div style='display:flex; gap:2px; margin:4px 0;'>
            <div style='height:4px; width:{bp}%; background:#059669; border-radius:2px;'></div>
            <div style='height:4px; width:{sp}%; background:#DC2626; border-radius:2px;'></div>
            <div style='height:4px; flex:1; background:#E2E8F0; border-radius:2px;'></div>
        </div>
        <div style='display:flex; justify-content:space-between; font-size:9px; color:#94A3B8;'>
            <span>{b}/10 Bull</span><span>{s}/10 Bear</span>
        </div>"""
    except: return ""

def rsi_gauge(val):
    try:
        v = float(val)
        if v > 70: color, label = "#DC2626", "OB"
        elif v < 30: color, label = "#059669", "OS"
        else: color, label = "#64748B", ""
        return f"<span style='color:{color}; font-weight:700;'>{v:.0f}</span>{f' <span style=\"font-size:8px; color:{color};\">{label}</span>' if label else ''}"
    except: return "—"

def clean_placeholder(text):
    if not text: return ""
    t = str(text).strip()
    if "{{" in t or t.lower() in ("none", "null", ""): return "Signal"
    return t

# ─── Sidebar ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""<div style='padding:12px 0 24px;'>
        <div style='font-size:18px; font-weight:800; color:#FFFFFF !important;'>JHAVERI</div>
        <div style='font-size:9px; color:#64748B !important; text-transform:uppercase; letter-spacing:2px;'>Intelligence Platform</div>
    </div>""", unsafe_allow_html=True)
    
    page = st.radio("Nav", [
        "Command Center", 
        "Trade Desk", 
        "Market Pulse",
        "Portfolio Analytics", 
        "Alert Database", 
        "Integrations"
    ], label_visibility="collapsed")
    
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    sc1, sc2 = st.columns(2)
    with sc1:
        if st.button("Sync", use_container_width=True): st.rerun()
    with sc2:
        auto = st.toggle("Auto", value=True, key="auto_refresh")
    
    ist = now_ist()
    is_market_open = ist.weekday() < 5 and 9 <= ist.hour < 16
    market_indicator = "OPEN" if is_market_open else "CLOSED"
    st.markdown(f"<div style='font-size:10px; color:#475569; margin-top:8px;'>Live &middot; {ist.strftime('%d-%b-%y %I:%M:%S %p')} IST</div>", unsafe_allow_html=True)

_should_auto_refresh = st.session_state.get("auto_refresh", True)


# ═══════════════════════════════════════════════════════════
# COMMAND CENTER
# ═══════════════════════════════════════════════════════════
if page == "Command Center":
    st.markdown("<h1 style='margin-bottom:4px;'>Command Center</h1><p style='color:#64748B; font-size:13px; margin-top:0;'>Real-time signal feed with technical intelligence</p>", unsafe_allow_html=True)
    
    stats = api_call('GET', "/api/stats") or {}
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Alerts", stats.get("total_alerts", 0))
    c2.metric("Pending Queue", stats.get("pending", 0))
    ist = now_ist()
    c3.metric("Market Status", "OPEN" if (ist.weekday() < 5 and 9 <= ist.hour < 16) else "CLOSED")
    
    st.divider()
    sf = st.selectbox("Filter", ["All", "PENDING", "APPROVED", "DENIED"], label_visibility="collapsed")
    params = {"limit": 50}
    if sf != "All": params["status"] = sf
    data = api_call('GET', "/api/alerts", params=params)
    
    if not data or not data.get("alerts"):
        st.markdown("""<div class='empty-state'>
            <div style='font-size:32px; margin-bottom:12px;'>No signals found</div>
            <div style='font-size:12px;'>Alerts will appear here when your TradingView webhooks fire. Check the Integrations page for setup instructions.</div>
        </div>""", unsafe_allow_html=True)
    else:
        cols = st.columns(3)
        for i, al in enumerate(data["alerts"]):
            with cols[i % 3]:
                with st.container(border=True):
                    alert_nm = clean_placeholder(al.get("alert_name"))
                    tkr = str(al.get("ticker", "—")).strip()
                    ind = al.get("indicators") or {}
                    has_rich_data = bool(ind and ind.get("rsi") is not None)
                    
                    interval_display = f"<span style='font-size:9px; color:#94A3B8; margin-left:4px;'>{al.get('interval','')}</span>" if al.get('interval') and al.get('interval') != '—' else ""
                    
                    st.markdown(f"""
                    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>
                        <div>{asset_pill(al.get('asset_class'))} {signal_pill(al.get('signal_direction'))}</div>
                        <div style='font-size:10px; color:#94A3B8;'>{fmt_ist(al.get('received_at'))}</div>
                    </div>
                    <div style='display:flex; justify-content:space-between; align-items:flex-end;'>
                        <div>
                            <div style='font-size:15px; font-weight:800; color:#0F172A;'>{alert_nm}{interval_display}</div>
                            {f"<div style='font-size:11px; color:#64748B;'>{tkr}</div>" if alert_nm.upper() != tkr.upper() else ""}
                        </div>
                        <div style='text-align:right;'>
                            <div style='font-size:16px; font-weight:800; color:#0F172A;'>{fmt_price(al.get("price_at_alert"))}</div>
                            <div>{stat_pill(al.get('status'))}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if has_rich_data:
                        rsi_html = rsi_gauge(ind.get("rsi"))
                        st_dir = ind.get("supertrend_dir", "")
                        st_color = "#059669" if st_dir == "BULLISH" else "#DC2626" if st_dir == "BEARISH" else "#94A3B8"
                        htf = ind.get("htf_trend", "")
                        htf_color = "#059669" if htf == "BULLISH" else "#DC2626" if htf == "BEARISH" else "#94A3B8"
                        adx_val = ind.get("adx")
                        adx_str = f"{float(adx_val):.0f}" if adx_val else "—"
                        
                        st.markdown(f"""
                        <div style='background:#F8FAFC; border-radius:6px; padding:8px 10px; margin-top:8px;'>
                            <div style='display:flex; justify-content:space-between; font-size:10px; margin-bottom:6px;'>
                                <div><span style='color:#94A3B8;'>RSI</span> {rsi_html}</div>
                                <div><span style='color:#94A3B8;'>ADX</span> <span style='font-weight:700;'>{adx_str}</span></div>
                                <div><span style='color:#94A3B8;'>ST</span> <span style='color:{st_color}; font-weight:700;'>{st_dir[:4] if st_dir else "—"}</span></div>
                                <div><span style='color:#94A3B8;'>HTF</span> <span style='color:{htf_color}; font-weight:700;'>{htf[:4] if htf else "—"}</span></div>
                            </div>
                            {confluence_bar(ind.get("confluence_bull_score"), ind.get("confluence_bear_score"))}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        ma_a = ind.get("ma_alignment", "")
                        cp = ind.get("candle_pattern", "")
                        extras = []
                        if ma_a and ma_a != "MIXED": extras.append(f"MA: {ma_a}")
                        if cp and cp != "NONE": extras.append(f"Pattern: {cp}")
                        vr = ind.get("vol_ratio")
                        if vr:
                            try:
                                if float(vr) > 1.5: extras.append(f"Vol: {float(vr):.1f}x")
                            except: pass
                        if extras:
                            st.markdown(f"<div style='font-size:9px; color:#64748B; margin-top:4px;'>{' &middot; '.join(extras)}</div>", unsafe_allow_html=True)
                    
                    # Show signal summary or alert message
                    summary = al.get("signal_summary") or ""
                    msg = al.get("alert_message") or ""
                    display_text = summary if summary and len(summary) > 20 else msg
                    if display_text and "{{" not in display_text and len(display_text) > 5:
                        st.markdown(f"<div style='font-size:11px; color:#475569; padding:8px; background:#F8FAFC; border-radius:6px; margin-top:8px; line-height:1.4;'>{display_text[:300]}</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# TRADE DESK
# ═══════════════════════════════════════════════════════════
elif page == "Trade Desk":
    st.markdown("<h1 style='margin-bottom:4px;'>Trade Desk</h1><p style='color:#64748B; font-size:13px; margin-top:0;'>Review pending signals and take action</p>", unsafe_allow_html=True)
    
    data = api_call('GET', "/api/alerts", params={"status": "PENDING", "limit": 50})
    alerts = data.get("alerts", []) if data else []
    
    if not alerts:
        st.markdown("""<div class='empty-state'>
            <div style='font-size:16px; font-weight:600; color:#475569;'>All clear - no pending signals</div>
            <div style='font-size:12px; margin-top:6px;'>New alerts will appear here for your review.</div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='font-size:13px; color:#64748B; margin-bottom:16px;'>{len(alerts)} signal(s) awaiting review</div>", unsafe_allow_html=True)
        
        for al in alerts:
            alert_id = al.get("id")
            tkr = str(al.get("ticker", "—")).strip()
            alert_nm = clean_placeholder(al.get("alert_name"))
            ind = al.get("indicators") or {}
            
            with st.container(border=True):
                hc1, hc2 = st.columns([3, 1])
                with hc1:
                    st.markdown(f"""
                    <div style='margin-bottom:6px;'>
                        {asset_pill(al.get('asset_class'))} {signal_pill(al.get('signal_direction'))}
                        <span style='font-size:10px; color:#94A3B8; margin-left:8px;'>{fmt_ist(al.get('received_at'))}</span>
                    </div>
                    <div style='font-size:18px; font-weight:800; color:#0F172A;'>{alert_nm}</div>
                    <div style='font-size:13px; color:#64748B;'>{tkr} &middot; {al.get('exchange','—')} &middot; {al.get('interval','—')}</div>
                    """, unsafe_allow_html=True)
                with hc2:
                    st.markdown(f"<div style='text-align:right; font-size:22px; font-weight:800; color:#0F172A;'>{fmt_price(al.get('price_at_alert'))}</div>", unsafe_allow_html=True)
                
                # Indicator row
                if ind and ind.get("rsi") is not None:
                    ic1, ic2, ic3, ic4, ic5 = st.columns(5)
                    with ic1:
                        rsi_val = ind.get("rsi")
                        rsi_c = "#DC2626" if rsi_val and float(rsi_val) > 70 else "#059669" if rsi_val and float(rsi_val) < 30 else "#475569"
                        st.markdown(f"<div style='font-size:10px; color:#94A3B8;'>RSI</div><div style='font-size:16px; font-weight:700; color:{rsi_c};'>{float(rsi_val):.0f}</div>", unsafe_allow_html=True)
                    with ic2:
                        adx_v = ind.get("adx")
                        st.markdown(f"<div style='font-size:10px; color:#94A3B8;'>ADX</div><div style='font-size:16px; font-weight:700;'>{float(adx_v):.0f if adx_v else '—'}</div>", unsafe_allow_html=True)
                    with ic3:
                        st.markdown(f"<div style='font-size:10px; color:#94A3B8;'>SuperTrend</div><div style='font-size:14px; font-weight:700;'>{ind.get('supertrend_dir','—')}</div>", unsafe_allow_html=True)
                    with ic4:
                        st.markdown(f"<div style='font-size:10px; color:#94A3B8;'>HTF Trend</div><div style='font-size:14px; font-weight:700;'>{ind.get('htf_trend','—')}</div>", unsafe_allow_html=True)
                    with ic5:
                        st.markdown(f"<div style='font-size:10px; color:#94A3B8;'>Confluence</div><div style='font-size:14px; font-weight:700;'>{ind.get('confluence_bias','—')}</div>", unsafe_allow_html=True)
                
                # AI Summary
                summary = al.get("signal_summary") or al.get("alert_message") or ""
                if summary and len(summary) > 10 and "{{" not in summary:
                    st.markdown(f"<div style='font-size:12px; color:#475569; padding:10px; background:#F0F9FF; border-left:3px solid #2563EB; border-radius:4px; margin:10px 0; line-height:1.5;'>{summary[:500]}</div>", unsafe_allow_html=True)
                
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                ac1, ac2, ac3, ac4 = st.columns(4)
                with ac1:
                    call = st.selectbox("Call", ["BUY", "STRONG_BUY", "SELL", "STRONG_SELL", "HOLD", "ACCUMULATE", "REDUCE", "WATCH", "EXIT"], key=f"call_{alert_id}")
                with ac2:
                    conviction = st.selectbox("Conviction", ["HIGH", "MEDIUM", "LOW"], index=1, key=f"conv_{alert_id}")
                with ac3:
                    target = st.number_input("Target", min_value=0.0, value=0.0, step=0.5, key=f"tgt_{alert_id}")
                with ac4:
                    stoploss = st.number_input("Stop Loss", min_value=0.0, value=0.0, step=0.5, key=f"sl_{alert_id}")
                
                notes = st.text_input("Fund Manager Notes", key=f"notes_{alert_id}", placeholder="Quick rationale...")
                
                bc1, bc2, bc3 = st.columns(3)
                with bc1:
                    if st.button("Approve", key=f"approve_{alert_id}", type="primary", use_container_width=True):
                        payload = {
                            "alert_id": alert_id, "decision": "APPROVED",
                            "primary_call": call, "conviction": conviction,
                            "fm_rationale_text": notes if notes else None,
                            "target_price": target if target > 0 else None,
                            "stop_loss": stoploss if stoploss > 0 else None,
                        }
                        result = api_call('POST', f"/api/alerts/{alert_id}/action", data=payload)
                        if result and result.get("success"):
                            st.success(f"Approved: {tkr} as {call}")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("Action failed")
                with bc2:
                    if st.button("Deny", key=f"deny_{alert_id}", use_container_width=True):
                        result = api_call('POST', f"/api/alerts/{alert_id}/action", data={"alert_id": alert_id, "decision": "DENIED"})
                        if result: st.rerun()
                with bc3:
                    if st.button("Later", key=f"later_{alert_id}", use_container_width=True):
                        result = api_call('POST', f"/api/alerts/{alert_id}/action", data={"alert_id": alert_id, "decision": "REVIEW_LATER"})
                        if result: st.rerun()


# ═══════════════════════════════════════════════════════════
# MARKET PULSE — Live NSE/BSE indices
# ═══════════════════════════════════════════════════════════
elif page == "Market Pulse":
    st.markdown("<h1 style='margin-bottom:4px;'>Market Pulse</h1><p style='color:#64748B; font-size:13px; margin-top:0;'>Live NSE and BSE indices, commodities, and currencies</p>", unsafe_allow_html=True)
    
    if st.button("Refresh Prices", type="primary"):
        st.cache_data.clear()
        st.rerun()
    
    @st.cache_data(ttl=60)
    def fetch_market_data():
        return api_call('GET', '/api/market-pulse')
    
    market_data = fetch_market_data()
    
    if not market_data or not market_data.get("indices"):
        st.warning("Market data is loading... Click Refresh to try again.")
    else:
        indices = market_data["indices"]
        
        categories = {}
        for item in indices:
            cat = item.get("category", "Other")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        
        cat_order = ["NSE Broad Market", "NSE Sectoral", "BSE Indices", "Commodities", "Currency"]
        
        for cat in cat_order:
            if cat not in categories:
                continue
            items = categories[cat]
            st.markdown(f"### {cat}")
            
            cols = st.columns(4)
            for j, item in enumerate(items):
                with cols[j % 4]:
                    with st.container(border=True):
                        name = item.get("name", item.get("ticker", ""))
                        price = item.get("current_price")
                        change = item.get("change_pct")
                        
                        if change is not None:
                            if change > 0:
                                chg_color = "#059669"
                                chg_str = f"+{change:.2f}%"
                            elif change < 0:
                                chg_color = "#DC2626"
                                chg_str = f"{change:.2f}%"
                            else:
                                chg_color = "#64748B"
                                chg_str = "0.00%"
                            chg_html = f"<span style='color:{chg_color}; font-size:12px; font-weight:700;'>{chg_str}</span>"
                        else:
                            chg_html = "<span style='color:#94A3B8; font-size:11px;'>N/A</span>"
                        
                        price_str = fmt_price(price) if price else "—"
                        
                        st.markdown(f"""
                        <div style='font-size:11px; color:#94A3B8; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;'>{name}</div>
                        <div style='display:flex; justify-content:space-between; align-items:baseline; margin-top:4px;'>
                            <div style='font-size:18px; font-weight:800; color:#0F172A;'>{price_str}</div>
                            <div>{chg_html}</div>
                        </div>
                        """, unsafe_allow_html=True)
            
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        
        updated = market_data.get("updated_at", "")
        st.markdown(f"<div style='text-align:center; font-size:10px; color:#94A3B8; margin-top:16px;'>Last updated: {updated}</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# PORTFOLIO ANALYTICS
# ═══════════════════════════════════════════════════════════
elif page == "Portfolio Analytics":
    st.markdown("<h1>Portfolio Analytics</h1>", unsafe_allow_html=True)
    if st.button("Sync Prices", type="primary"):
        api_call('POST', "/api/performance/refresh")
        st.rerun()
    data = api_call('GET', "/api/performance")
    if data and data.get("performance"):
        perf = data["performance"]
        n = max(len(perf), 1)
        rets = [p.get("return_pct", 0.0) or 0.0 for p in perf]
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Positions", len(perf))
        m2.metric("Avg Return", f"{sum(rets)/n:+.2f}%")
        m3.metric("Win Rate", f"{sum(1 for r in rets if r > 0)/n*100:.0f}%")
        m4.metric("Best/Worst", f"{max(rets):+.1f}% / {min(rets):+.1f}%")
        st.divider()
        cols = st.columns(3)
        for i, p in enumerate(perf):
            rp = p.get("return_pct", 0.0) or 0.0
            color = "#059669" if rp > 0 else "#DC2626"
            dd = p.get("max_drawdown", 0.0) or 0.0
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"""
                    <div style='display:flex; justify-content:space-between;'>
                        <div style='font-size:16px; font-weight:800;'>{p.get('ticker','—')}</div>
                        <div style='font-size:18px; font-weight:800; color:{color};'>{rp:+.2f}%</div>
                    </div>
                    <div style='display:flex; justify-content:space-between; background:#F8FAFC; padding:8px; border-radius:6px; margin:10px 0;'>
                        <div><div style='font-size:9px; color:#94A3B8;'>ENTRY</div><div style='font-size:13px;'>{fmt_price(p.get('reference_price'))}</div></div>
                        <div style='text-align:right;'><div style='font-size:9px; color:#94A3B8;'>CURRENT</div><div style='font-size:13px;'>{fmt_price(p.get('current_price'))}</div></div>
                    </div>
                    <div style='font-size:10px; color:#64748B;'>Call: <b>{p.get('action_call','—')}</b> &middot; Max DD: <span style='color:#DC2626;'>{dd:.2f}%</span></div>
                    """, unsafe_allow_html=True)
    else:
        st.markdown("<div class='empty-state'>No active positions - approve alerts from the Trade Desk to start tracking</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# ALERT DATABASE
# ═══════════════════════════════════════════════════════════
elif page == "Alert Database":
    st.markdown("<h1>Alert Database</h1>", unsafe_allow_html=True)
    m = api_call('GET', "/api/master", params={"limit": 100})
    if m and m.get("alerts"):
        all_alerts = m["alerts"]
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Total", len(all_alerts))
        sc2.metric("Bullish", sum(1 for a in all_alerts if a.get("signal_direction") == "BULLISH"))
        sc3.metric("Bearish", sum(1 for a in all_alerts if a.get("signal_direction") == "BEARISH"))
        sc4.metric("Approved", sum(1 for a in all_alerts if a.get("status") == "APPROVED"))
        st.divider()
        cols = st.columns(3)
        for i, a in enumerate(all_alerts):
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"""
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <div style='font-size:14px; font-weight:700;'>{clean_placeholder(a.get('alert_name'))}</div>
                        {stat_pill(a.get('status'))}
                    </div>
                    <div style='font-size:12px; color:#475569; margin:4px 0;'>{a.get('ticker','—')} &middot; Price: <b>{fmt_price(a.get('price_at_alert'))}</b></div>
                    <div style='font-size:10px; color:#94A3B8;'>{signal_pill(a.get('signal_direction'))} &middot; {fmt_ist(a.get('received_at'))}</div>
                    """, unsafe_allow_html=True)
                    if st.button("Delete", key=f"del_{a['id']}", use_container_width=True):
                        api_call('DELETE', f"/api/alerts/{a['id']}")
                        st.rerun()
    else:
        st.markdown("<div class='empty-state'>No alerts in database</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# INTEGRATIONS
# ═══════════════════════════════════════════════════════════
elif page == "Integrations":
    st.markdown("<h1>Integrations</h1>", unsafe_allow_html=True)
    
    with st.container(border=True):
        st.markdown("### TradingView Webhook")
        webhook_url = f"{API_BASE}/webhook/tradingview"
        st.code(webhook_url, language=None)
        st.markdown("""
        **Setup Steps:**
        1. Add the **FIE Signal Engine v1.0** Pine Script indicator to your chart
        2. Configure the indicator settings (Signal Direction, Trigger Condition, etc.)
        3. Create an alert: Condition = "FIE Signal Engine v1.0" then "alert() function calls only"
        4. Enable Webhook and paste the URL above
        5. Leave the Message field empty - the Pine Script generates the full payload
        """)
    
    with st.container(border=True):
        st.markdown("### Test Webhook")
        st.markdown("Send a test signal to verify the pipeline is working:")
        test_ticker = st.text_input("Ticker", value="NIFTY", key="test_ticker")
        test_price = st.number_input("Price", value=22500.0, key="test_price")
        test_signal = st.selectbox("Direction", ["BULLISH", "BEARISH", "NEUTRAL"], key="test_signal")
        
        if st.button("Send Test Signal", type="primary"):
            test_payload = {
                "ticker": test_ticker, "exchange": "NSE", "close": test_price,
                "alert_name": f"Test Signal - {test_ticker}",
                "message": f"Manual test signal for {test_ticker} at {test_price}",
                "signal": test_signal, "interval": "5m",
            }
            try:
                r = requests.post(f"{API_BASE}/webhook/tradingview", json=test_payload, timeout=10)
                if r.status_code == 200:
                    result = r.json()
                    st.success(f"Test signal sent! Alert ID: {result.get('alert_id', '?')}")
                else:
                    st.error(f"Failed: HTTP {r.status_code} - {r.text}")
            except Exception as e:
                st.error(f"Connection error: {e}")
    
    with st.container(border=True):
        st.markdown("### System Status")
        stats = api_call('GET', "/api/stats")
        if stats:
            st.markdown(f"Database: Connected ({stats.get('total_alerts', 0)} alerts)")
        else:
            st.markdown("Database: Not responding")
        gemini_key = os.getenv("GEMINI_API_KEY")
        st.markdown(f"AI Engine: {'Gemini configured' if gemini_key else 'GEMINI_API_KEY not set'}")


# ─── AUTO REFRESH ──────────────────────────────────────────
if _should_auto_refresh and page in ["Command Center", "Trade Desk", "Market Pulse"]:
    components.html(f"""
    <script>
        if (!window._fie_refresh_set) {{
            window._fie_refresh_set = true;
            setTimeout(function() {{
                var buttons = window.parent.document.querySelectorAll('button');
                for (var i = 0; i < buttons.length; i++) {{
                    if (buttons[i].innerText.includes('Sync')) {{
                        buttons[i].click();
                        break;
                    }}
                }}
            }}, {REFRESH_INTERVAL * 1000});
        }}
    </script>
    """, height=0)
