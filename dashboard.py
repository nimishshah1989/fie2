"""
FIE v3 — Dashboard
Jhaveri Intelligence Platform — Financial Intelligence Engine
Clean white UI, 3-tab layout: Command Center | Trade Center | Alert Database
"""

import streamlit as st
import requests
import json
import base64
import os
from datetime import datetime
from typing import Optional

# ─── Configuration ─────────────────────────────────────

API_URL = os.getenv("FIE_API_URL", "http://localhost:8000")
PAGE_TITLE = "FIE — Jhaveri Intelligence Platform"

# ─── Page Config ───────────────────────────────────────

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Global CSS (Jhaveri Intelligence Platform style) ──

st.markdown("""
<style>
  /* ── Fonts ── */
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

  * { font-family: 'DM Sans', sans-serif; }

  /* ── Page ── */
  .stApp { background: #ffffff; }
  .block-container { padding: 0 !important; max-width: 100% !important; }
  section[data-testid="stSidebar"] { display: none; }

  /* ── Hide Streamlit chrome ── */
  #MainMenu, footer, header { visibility: hidden; }
  .stDeployButton { display: none; }

  /* ── Top header bar ── */
  .jie-header {
    background: #0f1923;
    color: white;
    padding: 0 32px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 56px;
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: 0 1px 0 rgba(255,255,255,0.06);
  }
  .jie-header-brand {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #e8f0fe;
  }
  .jie-header-brand span.dot {
    width: 28px; height: 28px;
    background: linear-gradient(135deg, #3b82f6, #1d4ed8);
    border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px;
  }
  .jie-header-meta { font-size: 12px; color: #64748b; }

  /* ── Tab navigation ── */
  .jie-nav {
    background: #fff;
    border-bottom: 1.5px solid #f1f5f9;
    padding: 0 32px;
    display: flex;
    align-items: center;
    gap: 2px;
    position: sticky;
    top: 56px;
    z-index: 99;
  }
  .jie-nav a {
    display: inline-block;
    padding: 14px 20px 12px;
    font-size: 13.5px;
    font-weight: 500;
    color: #64748b;
    border-bottom: 2.5px solid transparent;
    text-decoration: none;
    cursor: pointer;
    transition: all 0.15s;
  }
  .jie-nav a.active {
    color: #1e40af;
    border-bottom-color: #1e40af;
    font-weight: 600;
  }
  .jie-nav .badge {
    display: inline-block;
    background: #ef4444;
    color: white;
    border-radius: 10px;
    font-size: 10px;
    font-weight: 700;
    padding: 1px 6px;
    margin-left: 6px;
    vertical-align: middle;
  }

  /* ── Page content ── */
  .jie-page { padding: 28px 32px; }
  .jie-page-title {
    font-size: 20px;
    font-weight: 700;
    color: #0f172a;
    margin: 0 0 4px;
  }
  .jie-page-sub { font-size: 13px; color: #94a3b8; margin: 0 0 24px; }

  /* ── Stat cards row ── */
  .stat-row { display: flex; gap: 16px; margin-bottom: 24px; }
  .stat-card {
    flex: 1;
    background: #ffffff;
    border: 1.5px solid #f1f5f9;
    border-radius: 12px;
    padding: 18px 20px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  }
  .stat-label { font-size: 11px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; }
  .stat-value { font-size: 26px; font-weight: 700; color: #0f172a; line-height: 1; }
  .stat-value.bull { color: #059669; }
  .stat-value.bear { color: #ef4444; }
  .stat-value.neutral { color: #f59e0b; }
  .stat-sub { font-size: 12px; color: #94a3b8; margin-top: 4px; }

  /* ── Alert card ── */
  .alert-card {
    background: #ffffff;
    border: 1.5px solid #f1f5f9;
    border-radius: 14px;
    padding: 20px 22px;
    margin-bottom: 12px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    transition: box-shadow 0.15s, border-color 0.15s;
  }
  .alert-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); border-color: #e2e8f0; }
  .alert-card.bull  { border-left: 4px solid #059669; }
  .alert-card.bear  { border-left: 4px solid #ef4444; }
  .alert-card.neutral { border-left: 4px solid #f59e0b; }

  .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
  .card-ticker { font-size: 22px; font-weight: 800; color: #0f172a; letter-spacing: -0.02em; }
  .card-price  { font-size: 20px; font-weight: 700; color: #1e40af; }
  .card-exchange { font-size: 11px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 2px; }
  .card-interval { background: #f1f5f9; color: #475569; border-radius: 6px; padding: 2px 8px; font-size: 11px; font-weight: 600; font-family: 'DM Mono', monospace; }

  .ohlcv-row { display: flex; gap: 20px; flex-wrap: wrap; margin: 10px 0; }
  .ohlcv-item { text-align: center; }
  .ohlcv-label { font-size: 10px; font-weight: 700; color: #cbd5e1; text-transform: uppercase; letter-spacing: 0.08em; }
  .ohlcv-val   { font-size: 13px; font-weight: 600; color: #334155; font-family: 'DM Mono', monospace; }

  .card-ts { font-size: 11px; color: #94a3b8; margin-top: 6px; }
  .card-data { font-size: 12.5px; color: #475569; background: #f8fafc; border-radius: 8px; padding: 8px 12px; margin-top: 10px; border: 1px solid #f1f5f9; line-height: 1.5; }

  /* ── Signal chips ── */
  .chip {
    display: inline-block;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    padding: 3px 10px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }
  .chip-bull    { background: #dcfce7; color: #15803d; }
  .chip-bear    { background: #fee2e2; color: #b91c1c; }
  .chip-neutral { background: #fef3c7; color: #92400e; }
  .chip-pending { background: #f1f5f9; color: #475569; }
  .chip-approved { background: #dcfce7; color: #15803d; }
  .chip-denied  { background: #fee2e2; color: #b91c1c; }

  /* ── Priority chip ── */
  .chip-imm   { background: #fce7f3; color: #9d174d; }
  .chip-week  { background: #fef3c7; color: #92400e; }
  .chip-month { background: #ede9fe; color: #5b21b6; }

  /* ── Analysis bullets ── */
  .analysis-block {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 14px 16px;
    margin-top: 12px;
  }
  .analysis-title {
    font-size: 11px;
    font-weight: 700;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 10px;
    display: flex; align-items: center; gap: 6px;
  }
  .analysis-bullet {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 4px 0;
    font-size: 12.5px;
    color: #334155;
    line-height: 1.45;
    border-bottom: 1px solid #f1f5f9;
  }
  .analysis-bullet:last-child { border-bottom: none; }
  .analysis-num { font-size: 10px; font-weight: 700; color: #3b82f6; min-width: 16px; margin-top: 2px; }

  /* ── FM action panel ── */
  .action-panel {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 16px;
    margin-top: 12px;
  }
  .action-panel-title { font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 12px; }

  /* ── Divider ── */
  .jie-divider { height: 1px; background: #f1f5f9; margin: 24px 0; }

  /* ── Empty state ── */
  .empty-state { text-align: center; padding: 64px 32px; color: #94a3b8; }
  .empty-state .icon { font-size: 48px; margin-bottom: 12px; }
  .empty-state h3 { font-size: 16px; font-weight: 600; color: #64748b; margin-bottom: 4px; }
  .empty-state p  { font-size: 13px; }

  /* ── Streamlit widget overrides ── */
  div[data-testid="stButton"] button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    padding: 6px 16px !important;
  }
  div[data-testid="stSelectbox"] > div > div {
    border-radius: 8px !important;
    border-color: #e2e8f0 !important;
    font-size: 13px !important;
  }
  div[data-testid="stTextInput"] input,
  div[data-testid="stTextArea"] textarea {
    border-radius: 8px !important;
    border-color: #e2e8f0 !important;
    font-size: 13px !important;
  }
  div[data-testid="stFileUploader"] {
    border-radius: 10px !important;
  }
  .stTabs [data-baseweb="tab-list"] { display: none; }

</style>
""", unsafe_allow_html=True)

# ─── Helper ────────────────────────────────────────────

def fmt_price(v) -> str:
    if v is None: return "—"
    try:
        f = float(v)
        return f"₹{f:,.2f}" if f > 100 else f"{f:.4f}"
    except:
        return str(v)

def fmt_vol(v) -> str:
    if v is None: return "—"
    try:
        f = float(v)
        if f >= 1_000_000: return f"{f/1_000_000:.2f}M"
        if f >= 1_000:     return f"{f/1_000:.1f}K"
        return f"{f:.0f}"
    except:
        return str(v)

def fmt_ts(ts: str) -> str:
    if not ts: return "—"
    try:
        dt = datetime.fromisoformat(ts.replace("Z",""))
        return dt.strftime("%d %b %Y, %I:%M %p")
    except:
        return ts

def signal_chip(sig: str) -> str:
    s = (sig or "NEUTRAL").upper()
    cls = {"BULLISH": "chip-bull", "BEARISH": "chip-bear"}.get(s, "chip-neutral")
    return f'<span class="chip {cls}">{s}</span>'

def status_chip(s: str) -> str:
    cls = {"PENDING": "chip-pending", "APPROVED": "chip-approved", "DENIED": "chip-denied"}.get(s.upper(), "chip-pending")
    return f'<span class="chip {cls}">{s}</span>'

def priority_chip(p: str) -> str:
    if not p: return ""
    labels = {"IMMEDIATELY": "🔴 Immediately", "WITHIN_A_WEEK": "🟡 Within Week", "WITHIN_A_MONTH": "🟣 Within Month"}
    cls    = {"IMMEDIATELY": "chip-imm", "WITHIN_A_WEEK": "chip-week", "WITHIN_A_MONTH": "chip-month"}
    return f'<span class="chip {cls.get(p,"")}"> {labels.get(p, p)}</span>'


def get_alerts(status: Optional[str] = None):
    try:
        params = {"limit": 200}
        if status:
            params["status"] = status
        r = requests.get(f"{API_URL}/api/alerts", params=params, timeout=8)
        return r.json().get("alerts", [])
    except Exception as e:
        st.error(f"API error: {e}")
        return []

def post_action(payload: dict):
    try:
        r = requests.post(f"{API_URL}/api/alerts/{payload['alert_id']}/action", json=payload, timeout=60)
        return r.json()
    except Exception as e:
        return {"success": False, "error": str(e)}

def image_to_b64(uploaded_file) -> str:
    data = uploaded_file.read()
    return base64.b64encode(data).decode("utf-8")


# ─── Alert Card ────────────────────────────────────────

def render_alert_card(a: dict, mode: str = "view"):
    """
    mode: 'view' (Command Center), 'action' (Trade Center), 'database' (Alert DB)
    """
    sig = a.get("signal_direction", "NEUTRAL")
    cls = {"BULLISH": "bull", "BEARISH": "bear"}.get(sig, "neutral")
    ticker   = a.get("ticker", "—")
    price    = a.get("price_close")
    exchange = a.get("exchange", "—")
    interval = a.get("interval", "—")
    ts       = fmt_ts(a.get("received_at", ""))
    data_txt = a.get("alert_data", "")
    action   = a.get("action") or {}

    st.markdown(f"""
    <div class="alert-card {cls}">
      <div class="card-header">
        <div>
          <div class="card-ticker">{ticker} {signal_chip(sig)}</div>
          <div class="card-exchange">{exchange} &nbsp;·&nbsp; <span class="card-interval">{interval}</span></div>
        </div>
        <div style="text-align:right">
          <div class="card-price">{fmt_price(price)}</div>
          <div class="card-ts">{ts}</div>
        </div>
      </div>
      <div class="ohlcv-row">
        <div class="ohlcv-item"><div class="ohlcv-label">Open</div><div class="ohlcv-val">{fmt_price(a.get('price_open'))}</div></div>
        <div class="ohlcv-item"><div class="ohlcv-label">High</div><div class="ohlcv-val">{fmt_price(a.get('price_high'))}</div></div>
        <div class="ohlcv-item"><div class="ohlcv-label">Low</div><div class="ohlcv-val">{fmt_price(a.get('price_low'))}</div></div>
        <div class="ohlcv-item"><div class="ohlcv-label">Close</div><div class="ohlcv-val">{fmt_price(a.get('price_close'))}</div></div>
        <div class="ohlcv-item"><div class="ohlcv-label">Volume</div><div class="ohlcv-val">{fmt_vol(a.get('volume'))}</div></div>
      </div>
      {f'<div class="card-data">{data_txt[:300]}{"…" if len(data_txt or "") > 300 else ""}</div>' if data_txt else ""}
    </div>
    """, unsafe_allow_html=True)

    # ── Mode: Action (Trade Center) ──
    if mode == "action" and a.get("status") == "PENDING":
        with st.expander(f"⚡ Take Action — #{a['id']} {ticker}", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                action_call = st.selectbox(
                    "Action", ["BUY", "SELL", "HOLD", "RATIO", "ACCUMULATE", "REDUCE", "SWITCH", "WATCH"],
                    key=f"ac_{a['id']}"
                )
                priority = st.selectbox(
                    "Priority", ["IMMEDIATELY", "WITHIN_A_WEEK", "WITHIN_A_MONTH"],
                    key=f"pr_{a['id']}"
                )
            with col2:
                chart_file = st.file_uploader(
                    "Upload Chart Screenshot", type=["png", "jpg", "jpeg", "webp"],
                    key=f"chart_{a['id']}"
                )

            is_ratio = action_call == "RATIO"
            ratio_long = ratio_short = None
            if is_ratio:
                c1, c2 = st.columns(2)
                with c1:
                    ratio_long  = st.text_input("Leg 1 — Long", placeholder="e.g. LONG 60% RELIANCE", key=f"rl_{a['id']}")
                with c2:
                    ratio_short = st.text_input("Leg 2 — Short", placeholder="e.g. SHORT 40% HDFCBANK", key=f"rs_{a['id']}")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Approve", key=f"approve_{a['id']}", use_container_width=True):
                    chart_b64 = image_to_b64(chart_file) if chart_file else None
                    payload = {
                        "alert_id": a["id"],
                        "decision": "APPROVED",
                        "action_call": action_call,
                        "is_ratio": is_ratio,
                        "ratio_long": ratio_long,
                        "ratio_short": ratio_short,
                        "priority": priority,
                        "chart_image_b64": chart_b64,
                    }
                    result = post_action(payload)
                    if result.get("success"):
                        st.success("✅ Approved and saved!")
                        st.rerun()
                    else:
                        st.error(f"Error: {result.get('error', 'Unknown')}")
            with c2:
                if st.button("❌ Deny", key=f"deny_{a['id']}", use_container_width=True, type="secondary"):
                    result = post_action({"alert_id": a["id"], "decision": "DENIED"})
                    if result.get("success"):
                        st.rerun()
                    else:
                        st.error(f"Error: {result.get('error')}")

    # ── Mode: Database (Alert DB) ──
    if mode == "database" and action:
        # FM decision summary
        st.markdown(f"""
        <div class="action-panel">
          <div class="action-panel-title">📋 FM Decision</div>
          <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center">
            {status_chip(action.get('decision',''))}
            <span style="font-size:13px;font-weight:700;color:#0f172a">{action.get('action_call','—')}</span>
            {priority_chip(action.get('priority',''))}
          </div>
          {'<div style="margin-top:8px;font-size:12px;color:#64748b">'+action.get("ratio_long","")+" · "+action.get("ratio_short","")+"</div>" if action.get("is_ratio") and action.get("ratio_long") else ""}
        </div>
        """, unsafe_allow_html=True)

        # Claude chart analysis
        analysis = action.get("chart_analysis")
        if analysis:
            bullets_html = "".join(
                f'<div class="analysis-bullet"><span class="analysis-num">{i+1}.</span><span>{b}</span></div>'
                for i, b in enumerate(analysis)
            )
            st.markdown(f"""
            <div class="analysis-block">
              <div class="analysis-title">🤖 Claude Chart Analysis</div>
              {bullets_html}
            </div>
            """, unsafe_allow_html=True)

        if action.get("has_chart"):
            with st.expander("📊 View Chart Image"):
                try:
                    r = requests.get(f"{API_URL}/api/alerts/{a['id']}/chart", timeout=8)
                    b64 = r.json().get("chart_image_b64", "")
                    if b64:
                        img_data = base64.b64decode(b64)
                        st.image(img_data, use_column_width=True)
                except Exception as e:
                    st.warning(f"Could not load chart: {e}")


# ─── Header ────────────────────────────────────────────

def render_header(pending_count: int):
    now = datetime.now().strftime("%A, %d %B %Y")
    st.markdown(f"""
    <div class="jie-header">
      <div class="jie-header-brand">
        <span class="dot">⚡</span>
        JHAVERI &nbsp;<span style="color:#3b82f6">INTELLIGENCE PLATFORM</span>
      </div>
      <div class="jie-header-meta">Financial Intelligence Engine &nbsp;·&nbsp; {now}</div>
    </div>
    """, unsafe_allow_html=True)


def render_nav(current: str, pending_count: int):
    badge = f'<span class="badge">{pending_count}</span>' if pending_count else ""
    tabs = [
        ("Command Center", "command", "⚡"),
        ("Trade Center", "trade", f"📋"),
        ("Alert Database", "database", "🗄️"),
    ]
    nav_html = '<div class="jie-nav">'
    for label, key, icon in tabs:
        b = badge if key == "trade" else ""
        active = "active" if current == key else ""
        nav_html += f'<a class="{active}" onclick="void(0)">{icon} {label}{b}</a>'
    nav_html += "</div>"
    st.markdown(nav_html, unsafe_allow_html=True)


# ─── MAIN ──────────────────────────────────────────────

def main():
    if "tab" not in st.session_state:
        st.session_state.tab = "command"

    # Fetch data
    all_alerts    = get_alerts()
    pending       = [a for a in all_alerts if a.get("status") == "PENDING"]
    approved      = [a for a in all_alerts if a.get("status") == "APPROVED"]
    denied        = [a for a in all_alerts if a.get("status") == "DENIED"]
    pending_count = len(pending)

    render_header(pending_count)

    # Tab buttons as top-level Streamlit columns (since we can't do real nav)
    col_cc, col_tc, col_db, col_space = st.columns([1, 1, 1, 5])
    with col_cc:
        if st.button("⚡ Command Center", use_container_width=True,
                     type="primary" if st.session_state.tab == "command" else "secondary"):
            st.session_state.tab = "command"
            st.rerun()
    with col_tc:
        label = f"📋 Trade Center ({pending_count})" if pending_count else "📋 Trade Center"
        if st.button(label, use_container_width=True,
                     type="primary" if st.session_state.tab == "trade" else "secondary"):
            st.session_state.tab = "trade"
            st.rerun()
    with col_db:
        if st.button("🗄️ Alert Database", use_container_width=True,
                     type="primary" if st.session_state.tab == "database" else "secondary"):
            st.session_state.tab = "database"
            st.rerun()

    st.markdown('<div class="jie-divider"></div>', unsafe_allow_html=True)

    tab = st.session_state.tab

    # ══ COMMAND CENTER ══
    if tab == "command":
        st.markdown('<div class="jie-page">', unsafe_allow_html=True)
        st.markdown('<div class="jie-page-title">⚡ Command Center</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="jie-page-sub">Live overview of all incoming TradingView alerts &nbsp;·&nbsp; {datetime.now().strftime("%A, %d %B %Y")}</div>', unsafe_allow_html=True)

        # Stats
        bull = sum(1 for a in all_alerts if a.get("signal_direction") == "BULLISH")
        bear = sum(1 for a in all_alerts if a.get("signal_direction") == "BEARISH")

        st.markdown(f"""
        <div class="stat-row">
          <div class="stat-card">
            <div class="stat-label">Total Alerts</div>
            <div class="stat-value">{len(all_alerts)}</div>
            <div class="stat-sub">All time</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Pending Review</div>
            <div class="stat-value neutral">{pending_count}</div>
            <div class="stat-sub">Awaiting FM action</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Approved</div>
            <div class="stat-value bull">{len(approved)}</div>
            <div class="stat-sub">Actioned</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Denied</div>
            <div class="stat-value bear">{len(denied)}</div>
            <div class="stat-sub">Passed</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Bullish Signals</div>
            <div class="stat-value bull">{bull}</div>
            <div class="stat-sub">BULLISH direction</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Bearish Signals</div>
            <div class="stat-value bear">{bear}</div>
            <div class="stat-sub">BEARISH direction</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        if not all_alerts:
            st.markdown("""
            <div class="empty-state">
              <div class="icon">📡</div>
              <h3>No alerts yet</h3>
              <p>Alerts will appear here when TradingView webhooks are received</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Filter row
            col_f1, col_f2, _ = st.columns([2, 2, 6])
            with col_f1:
                sig_filter = st.selectbox("Signal", ["All", "BULLISH", "BEARISH", "NEUTRAL"], key="cc_sig")
            with col_f2:
                sort_order = st.selectbox("Sort", ["Newest First", "Oldest First"], key="cc_sort")

            filtered = all_alerts
            if sig_filter != "All":
                filtered = [a for a in filtered if a.get("signal_direction") == sig_filter]
            if sort_order == "Oldest First":
                filtered = list(reversed(filtered))

            st.markdown(f"<div style='font-size:12px;color:#94a3b8;margin-bottom:16px'>{len(filtered)} alerts</div>", unsafe_allow_html=True)

            for a in filtered[:50]:
                render_alert_card(a, mode="view")

        st.markdown("</div>", unsafe_allow_html=True)

    # ══ TRADE CENTER ══
    elif tab == "trade":
        st.markdown('<div class="jie-page">', unsafe_allow_html=True)
        st.markdown('<div class="jie-page-title">📋 Trade Center</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="jie-page-sub">Review pending alerts and take FM action &nbsp;·&nbsp; {pending_count} pending</div>', unsafe_allow_html=True)

        if not pending:
            st.markdown("""
            <div class="empty-state">
              <div class="icon">✅</div>
              <h3>All caught up!</h3>
              <p>No pending alerts requiring action</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            for a in pending:
                render_alert_card(a, mode="action")

        st.markdown("</div>", unsafe_allow_html=True)

    # ══ ALERT DATABASE ══
    elif tab == "database":
        st.markdown('<div class="jie-page">', unsafe_allow_html=True)
        st.markdown('<div class="jie-page-title">🗄️ Alert Database</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="jie-page-sub">All actioned alerts with FM decisions and Claude chart analysis</div>', unsafe_allow_html=True)

        actioned = approved + denied
        if not actioned:
            st.markdown("""
            <div class="empty-state">
              <div class="icon">🗄️</div>
              <h3>No actioned alerts yet</h3>
              <p>Approved and denied alerts with Claude chart analysis will appear here</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            col_f1, col_f2, _ = st.columns([2, 2, 6])
            with col_f1:
                status_filter = st.selectbox("Status", ["All", "APPROVED", "DENIED"], key="db_status")
            with col_f2:
                ticker_search = st.text_input("Search ticker", placeholder="e.g. NIFTY", key="db_ticker")

            filtered = actioned
            if status_filter != "All":
                filtered = [a for a in filtered if a.get("status") == status_filter]
            if ticker_search:
                filtered = [a for a in filtered if ticker_search.upper() in (a.get("ticker") or "").upper()]

            st.markdown(f"<div style='font-size:12px;color:#94a3b8;margin-bottom:16px'>{len(filtered)} actioned alerts</div>", unsafe_allow_html=True)

            for a in filtered[:100]:
                render_alert_card(a, mode="database")

        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
