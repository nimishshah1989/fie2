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

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

# ─── CSS ─────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    * { font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important; }
    code, pre, .stCode { font-family: 'JetBrains Mono', monospace !important; }
    .stApp { background: #FAFBFC !important; }
    #MainMenu, footer { display: none !important; }
    header[data-testid="stHeader"], .stAppHeader, header.stAppHeader,
    div[data-testid="stHeader"], .st-emotion-cache-h4xjwg,
    .st-emotion-cache-18ni7ap { display: none !important; height: 0 !important; visibility: hidden !important; }
    .block-container { padding-top: 1rem !important; max-width: 1400px !important; }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0C1222 0%, #131B2E 100%) !important;
        border-right: 1px solid rgba(255,255,255,0.04) !important;
        min-width: 240px !important; width: 240px !important;
    }
    section[data-testid="stSidebar"] > div:first-child { padding-top: 1rem !important; }
    section[data-testid="stSidebar"] * { color: #C8D1DC !important; }
    section[data-testid="stSidebar"] .stRadio label:hover { color: #FFFFFF !important; }
    button[data-testid="stSidebarCollapseButton"],
    button[data-testid="baseButton-headerNoPadding"],
    [data-testid="collapsedControl"], .css-1dp5vir,
    button[kind="headerNoPadding"], .st-emotion-cache-1dp5vir,
    [data-testid="stHeaderActionElements"] { display: none !important; visibility: hidden !important; height: 0 !important; }
    section[data-testid="stSidebar"][aria-expanded="false"] {
        display: block !important; min-width: 240px !important; width: 240px !important;
        transform: none !important; margin-left: 0 !important;
    }
    div[data-testid="stMetric"] {
        background: #FFFFFF; border: 1px solid #E8ECF1; border-radius: 10px;
        padding: 18px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    div[data-testid="stMetric"]:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
    div[data-testid="stMetric"] label {
        font-size: 10px !important; color: #8493A8 !important;
        font-weight: 600 !important; text-transform: uppercase !important; letter-spacing: 0.5px !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 24px !important; color: #0F172A !important; font-weight: 700 !important;
    }
    h1 { color: #0F172A !important; font-size: 22px !important; font-weight: 700 !important; margin-bottom: 2px !important; }
    h3 { color: #1E293B !important; font-size: 15px !important; font-weight: 600 !important; }
    .pill { display: inline-flex; align-items: center; padding: 3px 10px; border-radius: 100px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
    .pill-bullish { background: #ECFDF5; color: #059669; }
    .pill-bearish { background: #FEF2F2; color: #DC2626; }
    .pill-neutral { background: #FFF7ED; color: #C2410C; }
    .pill-pending { background: #FFFBEB; color: #B45309; border: 1px solid #FDE68A; }
    .pill-approved { background: #ECFDF5; color: #059669; border: 1px solid #A7F3D0; }
    .pill-denied { background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; }
    .pill-review { background: #EFF6FF; color: #2563EB; border: 1px solid #BFDBFE; }
    .divider { border-top: 1px solid #F1F5F9; margin: 20px 0; }
    .empty-state { text-align: center; padding: 60px 20px; color: #94A3B8; }
    .refresh-dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #22C55E; margin-right: 6px; animation: pulse 2s infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
    .alert-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 14px; }
    .alert-card { background: #FFFFFF; border: 1px solid #E8ECF1; border-radius: 12px; padding: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); transition: all 0.15s ease; }
    .alert-card:hover { box-shadow: 0 6px 20px rgba(0,0,0,0.08); transform: translateY(-1px); }
    .ac-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
    .ac-title { font-size: 14px; font-weight: 700; color: #0F172A; }
    .ac-time { font-size: 10px; color: #94A3B8; }
    .ac-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px; margin: 10px 0; }
    .ac-lbl { font-size: 9px; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.4px; font-weight: 600; }
    .ac-val { font-size: 13px; color: #1E293B; font-weight: 600; }
    .ac-msg { font-size: 11px; color: #64748B; padding: 6px 10px; background: #F8FAFC; border-radius: 6px; margin-top: 8px; line-height: 1.5; }
    .db-card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 24px; margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.04); }
    .db-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.06); }
    [data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; border: 1px solid #E8ECF1; }
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
    except Exception: pass
    return None

def fmt_price(val):
    if val is None or val == 0: return "—"
    try: return f"₹{float(val):,.2f}"
    except: return "—"

def fmt_time(iso_str):
    if not iso_str: return "—"
    try:
        dt = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y, %H:%M")
    except: return str(iso_str)[:16]

def fmt_short(iso_str):
    if not iso_str: return "—"
    try:
        dt = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
        return dt.strftime("%d %b, %H:%M")
    except: return str(iso_str)[:16]

def fmt_vol(val):
    if val is None or val == 0: return "—"
    try:
        v = float(val)
        if v >= 1e9: return f"{v/1e9:.1f}B"
        if v >= 1e7: return f"{v/1e7:.1f}Cr"
        if v >= 1e5: return f"{v/1e5:.1f}L"
        if v >= 1e3: return f"{v/1e3:.0f}K"
        return f"{v:,.0f}"
    except: return "—"

def dir_pill(d):
    d = str(d or "NEUTRAL").upper()
    c = "pill-bullish" if d == "BULLISH" else "pill-bearish" if d == "BEARISH" else "pill-neutral"
    return f"<span class='pill {c}'>{d}</span>"

def stat_pill(s):
    s = str(s or "PENDING").upper()
    cm = {"PENDING":"pill-pending","APPROVED":"pill-approved","DENIED":"pill-denied","REVIEW_LATER":"pill-review"}
    lm = {"REVIEW_LATER": "REVIEW"}
    pill_cls = cm.get(s, "pill-pending")
    label = lm.get(s, s)
    return f"<span class='pill {pill_cls}'>{label}</span>"

def ret_color(v):
    if v is None: return "#64748B"
    return "#059669" if v > 0 else "#DC2626" if v < 0 else "#64748B"

def clean_placeholder(text):
    """Fallback to remove ugly literal placeholders from the UI"""
    if not text: return ""
    t = str(text)
    t = t.replace("{{strategy.order.comment}}", "Manual Alert")
    t = t.replace("{{alert_name}}", "Manual Alert")
    t = t.replace("alert_name", "Manual Alert")
    t = t.replace("{{strategy.order.action}}", "NEUTRAL")
    return t


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
        if st.button("Sync", use_container_width=True): st.rerun()
    with sc2:
        auto = st.toggle("Auto", value=True, key="auto_refresh")
    st.markdown(f"<div style='font-size:10px; color:#475569; margin-top:8px;'><span class='refresh-dot'></span>Live · {datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

_should_auto_refresh = st.session_state.get("auto_refresh", True) and page in ["Command Center", "Portfolio Analytics"]


# ═══════════════════════════════════════════════════════════
# COMMAND CENTER
# ═══════════════════════════════════════════════════════════
if page == "Command Center":
    st.markdown("<h1>Command Center</h1><p style='color:#64748B; font-size:13px; margin-bottom:20px;'>Real-time signal feed · Pending alerts requiring action</p>", unsafe_allow_html=True)
    stats = api_call('GET', "/api/stats") or {}
    pending_ct = stats.get("pending", 0) + stats.get("review_later", 0)
    bull_p = stats.get("bullish_pending", 0)
    bear_p = stats.get("bearish_pending", 0)
    
    # Signal Intensity removed, now 3 clean columns
    c1, c2, c3 = st.columns(3)
    c1.metric("Pending Alerts", pending_ct)
    c2.metric("Bullish / Bearish", f"{bull_p} / {bear_p}")
    now = datetime.now()
    c3.metric("Market", "OPEN" if (now.weekday() < 5 and 9 <= now.hour < 16) else "CLOSED")
    
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    fc1, _, _, _ = st.columns([1, 1, 1, 2])
    with fc1:
        sf = st.selectbox("Filter", ["PENDING", "All", "APPROVED", "DENIED", "REVIEW_LATER"], label_visibility="collapsed", key="cf")
    params = {"limit": 50}
    if sf != "All": params["status"] = sf
    data = api_call('GET', "/api/alerts", params=params)
    
    if not data or not data.get("alerts"):
        st.markdown("<div class='empty-state'><div style='font-size:40px; opacity:0.3;'>📡</div><p style='font-size:14px;margin-top:12px;'>No signals in the feed</p></div>", unsafe_allow_html=True)
    else:
        html = "<div class='alert-grid'>"
        for al in data["alerts"]:
            nm = clean_placeholder(al.get("alert_name") or "System Trigger")
            tk = al.get("ticker") or "—"
            pr = al.get("price_at_alert")
            dr = al.get("signal_direction", "NEUTRAL")
            sv = al.get("status", "PENDING")
            iv = al.get("interval") or "—"
            sec = al.get("sector") or "—"
            vol = al.get("volume")
            exch = al.get("exchange") or "—"
            asset = al.get("asset_class") or "—"
            rcv = fmt_short(al.get("received_at"))
            msg = clean_placeholder(al.get("alert_message") or "")
            inds = al.get("indicator_values") or {}
            
            ichips = ""
            for k, v in list(inds.items())[:4]:
                try: vv = f"{float(v):.1f}"
                except: vv = str(v)[:12]
                ichips += f"<span style='display:inline-block;padding:2px 7px;background:#F1F5F9;border-radius:4px;font-size:9px;color:#475569;margin-right:3px;margin-bottom:3px;font-weight:600;'>{k.upper()}: {vv}</span>"
            
            bc = "#10B981" if dr == "BULLISH" else "#EF4444" if dr == "BEARISH" else "#F59E0B"
            html += f"""<div class="alert-card" style="border-left:3px solid {bc};">
                <div class="ac-header">
                    <div><div class="ac-title">{nm}</div><div style="margin-top:4px;">{dir_pill(dr)} {stat_pill(sv)}</div></div>
                    <div class="ac-time">{rcv}</div>
                </div>
                <div class="ac-grid">
                    <div><div class="ac-lbl">Ticker</div><div class="ac-val">{tk}</div></div>
                    <div><div class="ac-lbl">Price</div><div class="ac-val">{fmt_price(pr)}</div></div>
                    <div><div class="ac-lbl">Exchange</div><div class="ac-val">{exch}</div></div>
                    <div><div class="ac-lbl">Interval</div><div class="ac-val">{iv}</div></div>
                    <div><div class="ac-lbl">Volume</div><div class="ac-val">{fmt_vol(vol)}</div></div>
                    <div><div class="ac-lbl">Asset</div><div class="ac-val">{asset}</div></div>
                </div>
                {f'<div style="margin-bottom:6px;">{ichips}</div>' if ichips else ''}
                {f'<div class="ac-msg">{msg[:180]}</div>' if msg else ''}
            </div>"""
        html += "</div>"
        st.markdown(html.replace('\n', ''), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# TRADE DESK
# ═══════════════════════════════════════════════════════════
elif page == "Trade Desk":
    st.markdown("<h1>Trade Desk</h1><p style='color:#64748B; font-size:13px; margin-bottom:24px;'>Review, approve, and record rationale for each alert</p>", unsafe_allow_html=True)
    st.markdown("### Pending Execution Queue")
    d1 = api_call('GET', "/api/alerts", params={"status": "PENDING", "limit": 20})
    d2 = api_call('GET', "/api/alerts", params={"status": "REVIEW_LATER", "limit": 20})
    pending = (d1.get("alerts", []) if d1 else []) + (d2.get("alerts", []) if d2 else [])
    
    if not pending:
        st.markdown("<div style='background:#F0FDF4; border:1px solid #BBF7D0; border-radius:8px; padding:20px; text-align:center;'><span style='color:#166534; font-weight:600;'>✓ Queue is clear</span></div>", unsafe_allow_html=True)
    else:
        for al in pending:
            aid = al["id"]
            with st.container(border=True):
                nm = clean_placeholder(al.get('alert_name','Signal'))
                
                # Native Streamlit components to prevent HTML DOM ghosting
                header_col1, header_col2 = st.columns([3, 1])
                with header_col1:
                    st.markdown(f"#### {nm}")
                    st.caption(f"{al.get('ticker','—')} · {al.get('exchange','—')} · {al.get('interval','—')}")
                with header_col2:
                    st.markdown(f"<div style='text-align:right;'><h4>{fmt_price(al.get('price_at_alert'))}</h4><span style='font-size:12px; color:#64748B;'>Vol: {fmt_vol(al.get('volume'))}</span></div>", unsafe_allow_html=True)
                
                msg = clean_placeholder(al.get("alert_message"))
                if msg:
                    st.info(msg[:250], icon="💬")
                
                # ─── Action Buttons ───
                approve_key = f"approve_{aid}"
                if approve_key not in st.session_state:
                    st.session_state[approve_key] = False
                
                b1, b2, b3, _ = st.columns([1,1,1,3])
                with b1:
                    if st.button("✓ Approve", key=f"ab{aid}", type="primary", use_container_width=True):
                        st.session_state[approve_key] = True
                with b2:
                    if st.button("✗ Reject", key=f"db{aid}", use_container_width=True):
                        api_call('POST', f"/api/alerts/{aid}/action", {"alert_id":aid,"decision":"DENIED"})
                        st.rerun()
                with b3:
                    if st.button("◷ Later", key=f"rb{aid}", use_container_width=True):
                        api_call('POST', f"/api/alerts/{aid}/action", {"alert_id":aid,"decision":"REVIEW_LATER"})
                        st.rerun()
                
                # ─── Condensed Approval Form ───
                if st.session_state.get(approve_key, False):
                    st.divider()
                    
                    ac1, ac2 = st.columns(2)
                    with ac1:
                        call = st.selectbox("Action Call", ["BUY","SELL","HOLD","STRONG_BUY","STRONG_SELL","ACCUMULATE","REDUCE","EXIT","WATCH"], key=f"call{aid}")
                    with ac2:
                        conv = st.select_slider("Conviction", ["LOW","MEDIUM","HIGH"], value="MEDIUM", key=f"conv{aid}")
                    
                    commentary = st.text_area("FM Commentary", placeholder="Your thesis, rationale, or notes for the board...", key=f"cmt{aid}", height=68)
                    chart_file = st.file_uploader("Attach Chart Image (Optional)", type=["png","jpg","jpeg"], key=f"ch{aid}")
                    
                    cb64 = None
                    if chart_file:
                        cb64 = base64.b64encode(chart_file.read()).decode('utf-8')
                        st.image(chart_file, caption="Chart preview", width=300)
                    
                    sc1, sc2, _ = st.columns([1,1,4])
                    with sc1:
                        if st.button("✓ Submit", key=f"sub{aid}", type="primary", use_container_width=True):
                            payload = {
                                "alert_id": aid, "decision": "APPROVED",
                                "primary_call": call, "conviction": conv,
                                "fm_rationale_text": commentary if commentary else None,
                                "chart_image_b64": cb64,
                            }
                            api_call('POST', f"/api/alerts/{aid}/action", payload)
                            st.session_state[approve_key] = False
                            st.rerun()
                    with sc2:
                        if st.button("Cancel", key=f"can{aid}", use_container_width=True):
                            st.session_state[approve_key] = False
                            st.rerun()
    
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.markdown("### Recent Decisions")
    hist = api_call('GET', "/api/alerts", params={"limit": 20})
    if hist and hist.get("alerts"):
        for a in [x for x in hist["alerts"] if x.get("status") in ("APPROVED","DENIED","REVIEW_LATER")][:10]:
            act = a.get("action") or {}
            nm = clean_placeholder(a.get('alert_name', a.get('ticker','—')))
            
            # Using 100% native Streamlit components to permanently kill the ghosting bug
            with st.container(border=True):
                rc1, rc2 = st.columns([3, 1])
                with rc1:
                    status_emoji = "✅" if a.get('status') == 'APPROVED' else "❌" if a.get('status') == 'DENIED' else "⏳"
                    st.markdown(f"**{nm}** &nbsp;|&nbsp; {status_emoji} `{a.get('status')}` &nbsp;|&nbsp; **{act.get('call','—')}** ({act.get('conviction','')})")
                    if act.get('remarks'):
                        st.caption(act.get('remarks')[:100])
                with rc2:
                    st.markdown(f"**{a.get('ticker','—')}**")
                    st.caption(f"{fmt_short(act.get('decision_at') or a.get('received_at'))}")


# ═══════════════════════════════════════════════════════════
# PORTFOLIO ANALYTICS
# ═══════════════════════════════════════════════════════════
elif page == "Portfolio Analytics":
    st.markdown("<h1>Portfolio Analytics</h1><p style='color:#64748B; font-size:13px; margin-bottom:24px;'>Live performance of approved positions</p>", unsafe_allow_html=True)
    cr, _ = st.columns([1, 4])
    with cr:
        if st.button("🔄 Refresh Live Prices", type="primary", use_container_width=True):
            with st.spinner("Fetching live prices..."): result = api_call('POST', "/api/performance/refresh")
            if result: st.toast(f"Updated {result.get('updated_count',0)} positions")
            st.rerun()
    
    data = api_call('GET', "/api/performance")
    if data and data.get("performance"):
        perf = data["performance"]
        n = len(perf)
        rets = [p.get("return_pct",0) or 0 for p in perf]
        avg = sum(rets)/max(n,1)
        wins = sum(1 for r in rets if r > 0)
        
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Positions", n)
        m2.metric("Avg Return", f"{avg:+.2f}%")
        m3.metric("Win Rate", f"{wins/max(n,1)*100:.0f}%")
        m4.metric("Best / Worst", f"{max(rets):+.1f}% / {min(rets):+.1f}%")
        
        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        
        for p in perf:
            rp = p.get("return_pct")
            rc = ret_color(rp)
            rs = f"{rp:+.2f}%" if rp is not None else "—"
            with st.container(border=True):
                pc1, pc2, pc3, pc4, pc5 = st.columns([2.5,1.5,1.5,1.5,1])
                with pc1:
                    nm = clean_placeholder(p.get('alert_name','—'))
                    st.markdown(f"<div style='font-weight:700;font-size:15px;color:#0F172A;'>{p.get('ticker','—')}</div><div style='font-size:11px;color:#64748B;'>{nm} · {dir_pill(p.get('signal_direction','NEUTRAL'))}</div>".replace('\n',''), unsafe_allow_html=True)
                with pc2:
                    st.markdown(f"<div style='font-size:10px;color:#94A3B8;font-weight:600;text-transform:uppercase;'>Entry → Current</div><div style='font-size:13px;color:#1E293B;font-weight:600;'>{fmt_price(p.get('reference_price'))} → {fmt_price(p.get('current_price'))}</div>".replace('\n',''), unsafe_allow_html=True)
                with pc3:
                    st.markdown(f"<div style='font-size:10px;color:#94A3B8;font-weight:600;text-transform:uppercase;'>Return</div><div style='font-size:18px;font-weight:700;color:{rc};'>{rs}</div>".replace('\n',''), unsafe_allow_html=True)
                with pc4:
                    dd = p.get("max_drawdown")
                    st.markdown(f"<div style='font-size:10px;color:#94A3B8;font-weight:600;text-transform:uppercase;'>Max DD</div><div style='font-size:13px;font-weight:600;color:#DC2626;'>{dd:.2f}%</div>".replace('\n','') if dd else "<div style='font-size:10px;color:#94A3B8;'>Max DD</div><div>—</div>", unsafe_allow_html=True)
                with pc5:
                    call_val = p.get("action_call") or "—"
                    conv_val = p.get("conviction") or "—"
                    st.markdown(f"<div style='font-size:10px;color:#94A3B8;font-weight:600;text-transform:uppercase;'>Call</div><div style='font-size:13px;font-weight:600;color:#0F172A;'>{call_val}</div><div style='font-size:10px;color:#64748B;'>{conv_val}</div>".replace('\n',''), unsafe_allow_html=True)
                
                upd = fmt_short(p.get("last_updated"))
                st.markdown(f"<div style='font-size:9px;color:#B0B8C4;margin-top:4px;'>Last updated: {upd}</div>".replace('\n',''), unsafe_allow_html=True)
    else:
        st.markdown("<div class='empty-state'><div style='font-size:40px; opacity:0.3;'>📊</div><p style='font-size:14px;margin-top:12px;'>No active positions</p></div>".replace('\n',''), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# ALERT DATABASE (Board View)
# ═══════════════════════════════════════════════════════════
elif page == "Alert Database":
    st.markdown("<h1>Alert Database</h1><p style='color:#64748B; font-size:13px; margin-bottom:24px;'>Board-ready view of all approved recommendations</p>", unsafe_allow_html=True)
    
    f1,f2,f3,f4 = st.columns([1,1,1,1])
    with f1: ds = st.selectbox("Status", ["APPROVED","All","PENDING","DENIED","REVIEW_LATER"], key="ds")
    
    # Replaced Text Filter with Time Filter
    with f2: time_filter = st.selectbox("Timeframe", ["All Time", "Last 24h", "Last 7d", "Last 30d"], key="tf")
    
    with f3: dl = st.selectbox("Rows", [50,100,200], key="dl")
    with f4: view_mode = st.selectbox("View", ["Cards", "Table"], key="vm")
    
    pm = {"limit": dl}
    if ds != "All": pm["status"] = ds
    
    m = api_call('GET', "/api/master", params=pm)
    
    if m and m.get("alerts"):
        als = m["alerts"]
        
        # Apply the timeframe filter locally based on the received timestamps
        if time_filter != "All Time":
            filtered_als = []
            current_ts = time.time()
            for a in als:
                try:
                    # Parse ISO format datetime safely
                    a_dt = datetime.fromisoformat(str(a.get('received_at')).replace("Z", "+00:00"))
                    diff_days = (current_ts - a_dt.timestamp()) / 86400.0
                    
                    if time_filter == "Last 24h" and diff_days <= 1:
                        filtered_als.append(a)
                    elif time_filter == "Last 7d" and diff_days <= 7:
                        filtered_als.append(a)
                    elif time_filter == "Last 30d" and diff_days <= 30:
                        filtered_als.append(a)
                except:
                    # If date parsing fails, leave the alert in to be safe
                    filtered_als.append(a)
            als = filtered_als
            
        st.markdown(f"<p style='font-size:12px; color:#94A3B8; margin-bottom:16px;'>Showing {len(als)} alerts</p>", unsafe_allow_html=True)
        
        if view_mode == "Cards":
            for a in als:
                act = a.get("action") or {}
                perf = a.get("performance") or {}
                rp = perf.get("return_pct")
                rc = ret_color(rp)
                rs = f"{rp:+.2f}%" if rp is not None else "—"
                nm = clean_placeholder(a.get('alert_name','—'))
                
                with st.container(border=True):
                    # Top section HTML
                    card = f"""
                        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid #F1F5F9;">
                            <div>
                                <div style="font-size:16px;font-weight:700;color:#0F172A;margin-bottom:4px;">{nm}</div>
                                <div>{dir_pill(a.get('signal_direction'))} {stat_pill(a.get('status'))}
                                {f"<span style='margin-left:8px;padding:3px 10px;background:#F1F5F9;border-radius:100px;font-size:10px;font-weight:700;color:#334155;'>{act.get('call','')}</span>" if act.get('call') else ''}
                                {f"<span style='margin-left:4px;font-size:10px;color:#64748B;'>({act.get('conviction','')})</span>" if act.get('conviction') else ''}
                                </div>
                            </div>
                            <div style="text-align:right;">
                                <div style="font-size:22px;font-weight:700;color:{rc};">{rs}</div>
                                <div style="font-size:10px;color:#94A3B8;">{fmt_short(a.get('received_at'))}</div>
                            </div>
                        </div>
                        <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:14px;margin-bottom:14px;">
                            <div><div style="font-size:10px;color:#94A3B8;text-transform:uppercase;font-weight:600;">Ticker</div><div style="font-size:14px;color:#0F172A;font-weight:700;">{a.get('ticker','—')}</div></div>
                            <div><div style="font-size:10px;color:#94A3B8;text-transform:uppercase;font-weight:600;">Entry Price</div><div style="font-size:14px;color:#0F172A;font-weight:700;">{fmt_price(a.get('price_at_alert'))}</div></div>
                            <div><div style="font-size:10px;color:#94A3B8;text-transform:uppercase;font-weight:600;">Current</div><div style="font-size:14px;color:#0F172A;font-weight:700;">{fmt_price(perf.get('current_price'))}</div></div>
                            <div><div style="font-size:10px;color:#94A3B8;text-transform:uppercase;font-weight:600;">Exchange</div><div style="font-size:14px;color:#0F172A;font-weight:700;">{a.get('exchange','—')}</div></div>
                        </div>"""
                    
                    remarks = act.get("remarks")
                    if remarks:
                        card += f"""<div style="background:#F8FAFC;border-left:3px solid #3B82F6;padding:12px 16px;border-radius:0 8px 8px 0;margin-top:10px;margin-bottom:14px;">
                            <div style="font-size:10px;color:#3B82F6;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:3px;">Fund Manager's View</div>
                            <div style="font-size:13px;color:#334155;line-height:1.6;">{remarks}</div>
                        </div>"""
                    st.markdown(card.replace('\n', ''), unsafe_allow_html=True)
                    
                    # Native Streamlit actions at the bottom of the card
                    act_col1, act_col2 = st.columns([1, 4])
                    with act_col1:
                        if st.button("🗑️ Delete", key=f"del_{a['id']}", use_container_width=True):
                            api_call('DELETE', f"/api/alerts/{a['id']}")
                            st.rerun()
                    with act_col2:
                        if act.get("has_chart"):
                            with st.expander("📊 View Attached Chart"):
                                chart_data = api_call('GET', f"/api/alerts/{a['id']}/chart")
                                if chart_data and chart_data.get("chart_image_b64"):
                                    try:
                                        img_bytes = base64.b64decode(chart_data["chart_image_b64"])
                                        st.image(img_bytes, caption=f"Chart for {a.get('ticker','—')}", use_container_width=True)
                                    except: pass
        
        else:
            rows = [{
                "Date": fmt_short(a.get("received_at")),
                "Alert": clean_placeholder(a.get("alert_name","—")),
                "Ticker": a.get("ticker","—"),
                "Direction": a.get("signal_direction","—"),
                "Price": fmt_price(a.get("price_at_alert")),
                "Status": a.get("status","PENDING"),
                "Call": (a.get("action") or {}).get("call","—"),
                "Conviction": (a.get("action") or {}).get("conviction","—"),
                "Return": f"{(a.get('performance') or {}).get('return_pct',0):+.2f}%" if (a.get("performance") or {}).get("return_pct") is not None else "—",
            } for a in als]
            df = pd.DataFrame(rows)
            def cs(v):
                return {"APPROVED":"background-color:#ECFDF5;color:#059669","DENIED":"background-color:#FEF2F2;color:#DC2626","PENDING":"background-color:#FFFBEB;color:#B45309","REVIEW_LATER":"background-color:#EFF6FF;color:#2563EB"}.get(v,"")
            st.dataframe(df.style.map(cs, subset=["Status"]), use_container_width=True, hide_index=True, height=600)

    else:
        st.markdown("<div class='empty-state'><div style='font-size:40px;opacity:0.3;'>📁</div><p style='font-size:14px;margin-top:12px;'>No alerts in database</p></div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# INTEGRATIONS
# ═══════════════════════════════════════════════════════════
elif page == "Integrations":
    st.markdown("<h1>Integrations</h1><p style='color:#64748B; font-size:13px; margin-bottom:24px;'>Webhook configuration and templates</p>", unsafe_allow_html=True)
    
    wh = f"{API_BASE}/webhook/tradingview"
    st.markdown(f"<div style='background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:16px; font-family:monospace; font-size:13px;'>POST <b>{wh}</b></div>", unsafe_allow_html=True)
    
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    
    st.markdown("### Strategy Alert Template")
    st.markdown("<p style='font-size:12px;color:#64748B;'>Use this for <b>Pine Script strategy alerts ONLY</b>. <code>{{strategy.order.comment}}</code> will break if pasted into a manual price/indicator alert.</p>", unsafe_allow_html=True)
    st.code(json.dumps({
        "ticker": "{{ticker}}", "exchange": "{{exchange}}", "interval": "{{interval}}",
        "open": "{{open}}", "high": "{{high}}", "low": "{{low}}",
        "close": "{{close}}", "volume": "{{volume}}", "time": "{{time}}",
        "timenow": "{{timenow}}",
        "alert_name": "{{strategy.order.comment}}",
        "signal": "{{strategy.order.action}}",
        "message": "{{strategy.order.comment}} on {{ticker}}"
    }, indent=2), language="json")
    
    st.markdown("### Manual / Indicator Alert Template")
    st.markdown("<p style='font-size:12px;color:#64748B;'>Use this for <b>manual indicator or line cross alerts</b>. You must manually type your alert name into the JSON below.</p>", unsafe_allow_html=True)
    st.code(json.dumps({
        "ticker": "{{ticker}}", "exchange": "{{exchange}}", "interval": "{{interval}}",
        "open": "{{open}}", "high": "{{high}}", "low": "{{low}}",
        "close": "{{close}}", "volume": "{{volume}}", "time": "{{time}}",
        "timenow": "{{timenow}}",
        "alert_name": "TYPE_YOUR_ALERT_NAME_HERE",
        "signal": "BULLISH",
        "indicators": {"rsi": "{{plot_0}}", "macd": "{{plot_1}}"},
        "message": "TYPE_YOUR_CUSTOM_MESSAGE_HERE"
    }, indent=2), language="json")
    
# ═══════════════════════════════════════════════════════
# AUTO-REFRESH
# ═══════════════════════════════════════════════════════
if _should_auto_refresh:
    time.sleep(2)
    st.rerun()
