"""
FIE v3 — Dashboard
Jhaveri Intelligence Platform — Financial Intelligence Engine
Clean white UI, 3-tab layout: Command Center | Trade Center | Alert Database
"""

import streamlit as st
import requests
import json
import base64
import html
import os
from datetime import datetime
from typing import Optional

# ─── Configuration ─────────────────────────────────────

API_URL    = os.getenv("FIE_API_URL", "http://localhost:8000")
PAGE_TITLE = "FIE — Jhaveri Intelligence Platform"

# ─── Page Config ───────────────────────────────────────

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Global CSS ────────────────────────────────────────

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

  * { font-family: 'DM Sans', sans-serif; }

  .stApp { background: #ffffff; }
  .block-container { padding: 0 !important; max-width: 100% !important; }
  section[data-testid="stSidebar"] { display: none; }
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
    position: sticky; top: 0; z-index: 100;
    box-shadow: 0 1px 0 rgba(255,255,255,0.06);
  }
  .jie-header-brand {
    display: flex; align-items: center; gap: 12px;
    font-size: 13px; font-weight: 600; letter-spacing: 0.06em;
    text-transform: uppercase; color: #e8f0fe;
  }
  .jie-header-brand .dot {
    width: 28px; height: 28px;
    background: linear-gradient(135deg, #3b82f6, #1d4ed8);
    border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px;
  }
  .jie-header-meta { font-size: 12px; color: #64748b; }

  /* ── Page content ── */
  .jie-page { padding: 20px 32px 40px; }
  .jie-page-title { font-size: 20px; font-weight: 700; color: #0f172a; margin: 0 0 4px; }
  .jie-page-sub   { font-size: 13px; color: #94a3b8; margin: 0 0 20px; }

  /* ── Stat row ── */
  .stat-row { display: flex; gap: 14px; margin-bottom: 22px; flex-wrap: wrap; }
  .stat-card {
    flex: 1; min-width: 120px;
    background: #fff; border: 1.5px solid #f1f5f9;
    border-radius: 12px; padding: 16px 18px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  }
  .stat-label { font-size: 11px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; }
  .stat-value { font-size: 26px; font-weight: 700; color: #0f172a; line-height: 1; }
  .stat-value.bull { color: #059669; }
  .stat-value.bear { color: #ef4444; }
  .stat-value.warn { color: #f59e0b; }
  .stat-sub { font-size: 12px; color: #94a3b8; margin-top: 4px; }

  /* ── Alert card ── */
  .alert-card {
    background: #fff; border: 1.5px solid #f1f5f9;
    border-radius: 14px; padding: 18px 20px; margin-bottom: 10px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    transition: box-shadow 0.15s, border-color 0.15s;
  }
  .alert-card:hover { box-shadow: 0 4px 14px rgba(0,0,0,0.07); border-color: #e2e8f0; }
  .alert-card.bull    { border-left: 4px solid #059669; }
  .alert-card.bear    { border-left: 4px solid #ef4444; }
  .alert-card.neutral { border-left: 4px solid #f59e0b; }

  /* card header */
  .card-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
  .card-ticker { font-size: 22px; font-weight: 800; color: #0f172a; letter-spacing: -0.02em; line-height: 1.1; }
  .card-name   { font-size: 12px; color: #64748b; margin-top: 3px; max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .card-meta   { font-size: 11px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.07em; margin-top: 4px; }
  .card-interval { background: #f1f5f9; color: #475569; border-radius: 5px; padding: 1px 7px; font-size: 11px; font-weight: 600; font-family: 'DM Mono', monospace; }

  /* price + time block */
  .card-price-block { text-align: right; }
  .card-price  { font-size: 22px; font-weight: 700; color: #1e40af; line-height: 1; }
  .card-price-label { font-size: 10px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 2px; }
  .card-ts     { font-size: 11px; color: #94a3b8; margin-top: 4px; }
  .card-ts-alert { font-size: 11px; color: #64748b; }

  /* OHLCV */
  .ohlcv-row { display: flex; gap: 18px; flex-wrap: wrap; margin: 10px 0 6px; padding: 10px 0; border-top: 1px solid #f8fafc; border-bottom: 1px solid #f8fafc; }
  .ohlcv-item { text-align: center; min-width: 50px; }
  .ohlcv-label { font-size: 9px; font-weight: 700; color: #cbd5e1; text-transform: uppercase; letter-spacing: 0.1em; }
  .ohlcv-val   { font-size: 12px; font-weight: 600; color: #334155; font-family: 'DM Mono', monospace; margin-top: 2px; }

  /* alert data text */
  .card-data {
    font-size: 12px; color: #475569; background: #f8fafc;
    border-radius: 8px; padding: 8px 12px; margin-top: 10px;
    border: 1px solid #f1f5f9; line-height: 1.5;
    white-space: pre-wrap; word-break: break-word;
  }

  /* chips */
  .chip {
    display: inline-block; border-radius: 20px;
    font-size: 10px; font-weight: 700; padding: 2px 9px;
    letter-spacing: 0.04em; text-transform: uppercase;
  }
  .chip-bull     { background: #dcfce7; color: #15803d; }
  .chip-bear     { background: #fee2e2; color: #b91c1c; }
  .chip-neutral  { background: #fef3c7; color: #92400e; }
  .chip-pending  { background: #f1f5f9; color: #475569; }
  .chip-approved { background: #dcfce7; color: #15803d; }
  .chip-denied   { background: #fee2e2; color: #b91c1c; }
  .chip-imm      { background: #fce7f3; color: #9d174d; }
  .chip-week     { background: #fef3c7; color: #92400e; }
  .chip-month    { background: #ede9fe; color: #5b21b6; }

  /* FM decision panel */
  .action-panel {
    background: #f8fafc; border: 1px solid #e2e8f0;
    border-radius: 10px; padding: 14px 16px; margin-top: 12px;
  }
  .action-panel-title { font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 10px; }
  .action-row { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
  .action-call { font-size: 14px; font-weight: 800; color: #0f172a; }
  .ratio-legs  { font-size: 12px; color: #475569; margin-top: 6px; }

  /* Claude analysis */
  .analysis-block {
    background: #f0f9ff; border: 1px solid #bae6fd;
    border-radius: 10px; padding: 14px 16px; margin-top: 12px;
  }
  .analysis-title {
    font-size: 10px; font-weight: 700; color: #0369a1;
    text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 10px;
  }
  .analysis-bullet {
    display: flex; align-items: flex-start; gap: 8px;
    padding: 5px 0; font-size: 12.5px; color: #0c4a6e; line-height: 1.45;
    border-bottom: 1px solid #e0f2fe;
  }
  .analysis-bullet:last-child { border-bottom: none; }
  .analysis-num { font-size: 10px; font-weight: 700; color: #0284c7; min-width: 16px; margin-top: 2px; flex-shrink: 0; }

  /* misc */
  .jie-divider { height: 1px; background: #f1f5f9; margin: 16px 0; }
  .empty-state { text-align: center; padding: 60px 32px; color: #94a3b8; }
  .empty-state .icon { font-size: 44px; margin-bottom: 10px; }
  .empty-state h3 { font-size: 15px; font-weight: 600; color: #64748b; margin-bottom: 4px; }
  .empty-state p  { font-size: 13px; }

  /* Streamlit overrides */
  div[data-testid="stButton"] button { border-radius: 8px !important; font-weight: 600 !important; font-size: 13px !important; }
  div[data-testid="stSelectbox"] > div > div { border-radius: 8px !important; border-color: #e2e8f0 !important; font-size: 13px !important; }
  div[data-testid="stTextInput"] input { border-radius: 8px !important; border-color: #e2e8f0 !important; font-size: 13px !important; }
  div[data-testid="stFileUploader"] { border-radius: 10px !important; }
  .stTabs [data-baseweb="tab-list"] { display: none; }

</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════

def esc(v) -> str:
    """HTML-escape a value before injecting into markup. Prevents XSS."""
    if v is None: return ""
    return html.escape(str(v))

def fmt_price(v) -> str:
    if v is None: return "—"
    try:
        f = float(v)
        # Indian indices / stocks are typically > 100; ratios/forex below
        return f"₹{f:,.2f}" if f > 100 else f"{f:.4f}"
    except:
        return esc(v)

def fmt_vol(v) -> str:
    if v is None: return "—"
    try:
        f = float(v)
        if f >= 1_000_000: return f"{f/1_000_000:.2f}M"
        if f >= 1_000:     return f"{f/1_000:.1f}K"
        return f"{f:.0f}"
    except:
        return esc(v)

def fmt_ts(ts: str, label: str = "") -> str:
    """Format ISO timestamp. Returns HTML span with optional label prefix."""
    if not ts: return "—"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", ""))
        formatted = dt.strftime("%d %b %Y, %I:%M %p")
        return f"{label} {formatted}".strip() if label else formatted
    except:
        return esc(ts)

def signal_chip(sig: str) -> str:
    s = (sig or "NEUTRAL").upper()
    cls = {"BULLISH": "chip-bull", "BEARISH": "chip-bear"}.get(s, "chip-neutral")
    return f'<span class="chip {cls}">{s}</span>'

def status_chip(s: str) -> str:
    cls = {"PENDING": "chip-pending", "APPROVED": "chip-approved", "DENIED": "chip-denied"}.get((s or "").upper(), "chip-pending")
    return f'<span class="chip {cls}">{esc(s)}</span>'

def priority_chip(p: str) -> str:
    if not p: return ""
    labels = {"IMMEDIATELY": "🔴 Immediately", "WITHIN_A_WEEK": "🟡 Within Week", "WITHIN_A_MONTH": "🟣 Within Month"}
    cls    = {"IMMEDIATELY": "chip-imm",       "WITHIN_A_WEEK": "chip-week",        "WITHIN_A_MONTH": "chip-month"}
    return f'<span class="chip {cls.get(p, "")}">{labels.get(p, esc(p))}</span>'


# ═══════════════════════════════════════════════════════
# API CALLS
# ═══════════════════════════════════════════════════════

def get_alerts() -> list:
    try:
        r = requests.get(f"{API_URL}/api/alerts", params={"limit": 300}, timeout=8)
        r.raise_for_status()
        return r.json().get("alerts", [])
    except Exception as e:
        return []  # errors shown in main() after layout is set up

def post_action(payload: dict) -> dict:
    try:
        r = requests.post(
            f"{API_URL}/api/alerts/{payload['alert_id']}/action",
            json=payload,
            timeout=60,   # 60s: Claude vision analysis can take ~20-30s
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"success": False, "error": str(e)}

def image_to_b64(uploaded_file) -> str:
    return base64.b64encode(uploaded_file.read()).decode("utf-8")


# ═══════════════════════════════════════════════════════
# ALERT CARD
# ═══════════════════════════════════════════════════════

def render_alert_card(a: dict, mode: str = "view", expanded: bool = False):
    """
    mode:
      'view'     — Command Center (read-only)
      'action'   — Trade Center   (approve/deny panel)
      'database' — Alert Database (FM decision + Claude analysis)
    """
    sig      = a.get("signal_direction", "NEUTRAL")
    cls      = {"BULLISH": "bull", "BEARISH": "bear"}.get(sig, "neutral")
    ticker   = esc(a.get("ticker") or "—")
    # Use alert_name for subtitle if it's different from ticker
    name     = a.get("alert_name", "") or ""
    name_sub = esc(name) if name and name.upper() != (a.get("ticker") or "").upper() else ""
    exchange = esc(a.get("exchange") or "—")
    interval = esc(a.get("interval") or "—")
    # price_at_alert is the dedicated trigger price field
    price    = a.get("price_at_alert") or a.get("price_close")
    # time_utc = when TradingView fired the alert (candle close time)
    # received_at = when our server received the webhook
    time_alert   = fmt_ts(a.get("time_utc") or "", "Alert:")
    time_recv    = fmt_ts(a.get("received_at") or "", "Recv:")
    data_txt = esc(a.get("alert_data") or "")[:400]
    if len(a.get("alert_data") or "") > 400:
        data_txt += "…"
    action = a.get("action") or {}

    # Timestamp display: show alert candle time primarily, received as secondary
    ts_html = ""
    if time_alert and time_alert != "Alert: —":
        ts_html = f'<div class="card-ts-alert">{time_alert}</div>'
    if time_recv and time_recv != "Recv: —":
        ts_html += f'<div class="card-ts">{time_recv}</div>'

    st.markdown(f"""
    <div class="alert-card {cls}">
      <div class="card-top">
        <div>
          <div class="card-ticker">{ticker} &nbsp;{signal_chip(sig)}</div>
          {f'<div class="card-name">{name_sub}</div>' if name_sub else ""}
          <div class="card-meta">{exchange} &nbsp;·&nbsp; <span class="card-interval">{interval}</span></div>
        </div>
        <div class="card-price-block">
          <div class="card-price-label">Alert Price</div>
          <div class="card-price">{fmt_price(price)}</div>
          {ts_html}
        </div>
      </div>
      <div class="ohlcv-row">
        <div class="ohlcv-item"><div class="ohlcv-label">Open</div><div class="ohlcv-val">{fmt_price(a.get('price_open'))}</div></div>
        <div class="ohlcv-item"><div class="ohlcv-label">High</div><div class="ohlcv-val">{fmt_price(a.get('price_high'))}</div></div>
        <div class="ohlcv-item"><div class="ohlcv-label">Low</div><div class="ohlcv-val">{fmt_price(a.get('price_low'))}</div></div>
        <div class="ohlcv-item"><div class="ohlcv-label">Close</div><div class="ohlcv-val">{fmt_price(a.get('price_close'))}</div></div>
        <div class="ohlcv-item"><div class="ohlcv-label">Volume</div><div class="ohlcv-val">{fmt_vol(a.get('volume'))}</div></div>
      </div>
      {f'<div class="card-data">{data_txt}</div>' if data_txt else ""}
    </div>
    """, unsafe_allow_html=True)

    # ── TRADE CENTER: action panel ──────────────────────
    if mode == "action" and a.get("status") == "PENDING":
        with st.expander(f"⚡ Take Action — #{a['id']} {a.get('ticker','')}", expanded=expanded):
            col1, col2 = st.columns(2)
            with col1:
                action_call = st.selectbox(
                    "Action",
                    ["BUY", "SELL", "HOLD", "RATIO", "ACCUMULATE", "REDUCE", "SWITCH", "WATCH"],
                    key=f"ac_{a['id']}"
                )
                priority = st.selectbox(
                    "Priority",
                    ["IMMEDIATELY", "WITHIN_A_WEEK", "WITHIN_A_MONTH"],
                    key=f"pr_{a['id']}"
                )
            with col2:
                chart_file = st.file_uploader(
                    "Upload Chart Screenshot",
                    type=["png", "jpg", "jpeg", "webp"],
                    key=f"chart_{a['id']}",
                    help="Chart image will be analyzed by Claude AI on approval"
                )

            is_ratio   = (action_call == "RATIO")
            ratio_long = ratio_short = None
            if is_ratio:
                rc1, rc2 = st.columns(2)
                with rc1:
                    ratio_long  = st.text_input("Leg 1 — Long",  placeholder="e.g. LONG 60% RELIANCE",  key=f"rl_{a['id']}")
                with rc2:
                    ratio_short = st.text_input("Leg 2 — Short", placeholder="e.g. SHORT 40% HDFCBANK", key=f"rs_{a['id']}")

            bc1, bc2 = st.columns(2)
            with bc1:
                if st.button("✅ Approve", key=f"approve_{a['id']}", use_container_width=True, type="primary"):
                    chart_b64 = image_to_b64(chart_file) if chart_file else None
                    if chart_b64:
                        st.info("⏳ Analyzing chart with Claude AI… (15-30s)")
                    result = post_action({
                        "alert_id":        a["id"],
                        "decision":        "APPROVED",
                        "action_call":     action_call,
                        "is_ratio":        is_ratio,
                        "ratio_long":      ratio_long  if is_ratio else None,
                        "ratio_short":     ratio_short if is_ratio else None,
                        "priority":        priority,
                        "chart_image_b64": chart_b64,
                    })
                    if result.get("success"):
                        st.success("✅ Approved! Moving to Alert Database.")
                        st.rerun()
                    else:
                        st.error(f"Error: {result.get('error', 'Unknown error')}")
            with bc2:
                if st.button("❌ Deny", key=f"deny_{a['id']}", use_container_width=True):
                    result = post_action({"alert_id": a["id"], "decision": "DENIED"})
                    if result.get("success"):
                        st.rerun()
                    else:
                        st.error(f"Error: {result.get('error', 'Unknown error')}")

    # ── ALERT DATABASE: FM decision + Claude analysis ───
    if mode == "database" and action:
        # Build ratio legs string — only show legs that are actually filled
        ratio_html = ""
        if action.get("is_ratio"):
            legs = [l for l in [action.get("ratio_long"), action.get("ratio_short")] if l]
            if legs:
                ratio_html = f'<div class="ratio-legs">{"  ·  ".join(esc(l) for l in legs)}</div>'

        st.markdown(f"""
        <div class="action-panel">
          <div class="action-panel-title">📋 FM Decision</div>
          <div class="action-row">
            {status_chip(action.get('decision', ''))}
            <span class="action-call">{esc(action.get('action_call') or '—')}</span>
            {priority_chip(action.get('priority', ''))}
          </div>
          {ratio_html}
        </div>
        """, unsafe_allow_html=True)

        # Claude chart analysis
        analysis = action.get("chart_analysis")
        if analysis:
            bullets_html = "".join(
                f'<div class="analysis-bullet">'
                f'<span class="analysis-num">{i+1}.</span>'
                f'<span>{esc(b)}</span>'
                f'</div>'
                for i, b in enumerate(analysis) if b and b != "—"
            )
            st.markdown(f"""
            <div class="analysis-block">
              <div class="analysis-title">🤖 Claude Chart Analysis</div>
              {bullets_html}
            </div>
            """, unsafe_allow_html=True)
        elif action.get("has_chart"):
            st.caption("⏳ Chart analysis not yet available.")

        if action.get("has_chart"):
            with st.expander("📊 View Chart Image"):
                try:
                    r = requests.get(f"{API_URL}/api/alerts/{a['id']}/chart", timeout=8)
                    b64 = r.json().get("chart_image_b64", "")
                    if b64:
                        st.image(base64.b64decode(b64), use_column_width=True)
                except Exception as e:
                    st.warning(f"Could not load chart: {e}")


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

def main():
    # ── Session state defaults ──
    if "tab" not in st.session_state:
        st.session_state.tab = "command"
    if "api_error" not in st.session_state:
        st.session_state.api_error = None

    # ── Fetch all alerts once per render ──
    all_alerts = get_alerts()
    if not all_alerts and st.session_state.api_error:
        # Will show error after layout renders
        pass

    pending  = [a for a in all_alerts if a.get("status") == "PENDING"]
    approved = [a for a in all_alerts if a.get("status") == "APPROVED"]
    denied   = [a for a in all_alerts if a.get("status") == "DENIED"]
    # Sort actioned alerts by decision time, newest first
    actioned = sorted(
        approved + denied,
        key=lambda a: (a.get("action", {}) or {}).get("decision_at") or a.get("received_at") or "",
        reverse=True
    )
    pending_count = len(pending)

    # ── Header ──
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

    # ── Tab navigation ──
    col_cc, col_tc, col_db, col_refresh, col_space = st.columns([1.2, 1.4, 1.3, 0.8, 4])
    with col_cc:
        if st.button("⚡ Command Center", use_container_width=True,
                     type="primary" if st.session_state.tab == "command" else "secondary"):
            st.session_state.tab = "command"
            st.rerun()
    with col_tc:
        tc_label = f"📋 Trade Center ({pending_count})" if pending_count else "📋 Trade Center"
        if st.button(tc_label, use_container_width=True,
                     type="primary" if st.session_state.tab == "trade" else "secondary"):
            st.session_state.tab = "trade"
            st.rerun()
    with col_db:
        if st.button("🗄️ Alert Database", use_container_width=True,
                     type="primary" if st.session_state.tab == "database" else "secondary"):
            st.session_state.tab = "database"
            st.rerun()
    with col_refresh:
        if st.button("🔄", use_container_width=True, help="Refresh alerts"):
            st.rerun()

    st.markdown('<div class="jie-divider"></div>', unsafe_allow_html=True)

    tab = st.session_state.tab

    # ══════════════════════════════════════════════════
    # COMMAND CENTER — read-only overview of all alerts
    # ══════════════════════════════════════════════════
    if tab == "command":
        st.markdown('<div class="jie-page">', unsafe_allow_html=True)
        st.markdown('<div class="jie-page-title">⚡ Command Center</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="jie-page-sub">Live overview of all incoming TradingView alerts · {now}</div>', unsafe_allow_html=True)

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
            <div class="stat-value warn">{pending_count}</div>
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
            <div class="stat-label">Bullish</div>
            <div class="stat-value bull">{bull}</div>
            <div class="stat-sub">Bullish signals</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Bearish</div>
            <div class="stat-value bear">{bear}</div>
            <div class="stat-sub">Bearish signals</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        if not all_alerts:
            st.markdown('<div class="empty-state"><div class="icon">📡</div><h3>No alerts yet</h3><p>Alerts appear here when TradingView webhooks are received</p></div>', unsafe_allow_html=True)
        else:
            fc1, fc2, _ = st.columns([2, 2, 6])
            with fc1:
                sig_f = st.selectbox("Signal", ["All", "BULLISH", "BEARISH", "NEUTRAL"], key="cc_sig")
            with fc2:
                sort_f = st.selectbox("Sort", ["Newest First", "Oldest First"], key="cc_sort")

            filtered = all_alerts
            if sig_f != "All":
                filtered = [a for a in filtered if a.get("signal_direction") == sig_f]
            if sort_f == "Oldest First":
                filtered = list(reversed(filtered))

            st.caption(f"{len(filtered)} alerts")
            for a in filtered[:50]:
                render_alert_card(a, mode="view")

        st.markdown("</div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════
    # TRADE CENTER — FM approves / denies pending alerts
    # ══════════════════════════════════════════════════
    elif tab == "trade":
        st.markdown('<div class="jie-page">', unsafe_allow_html=True)
        st.markdown('<div class="jie-page-title">📋 Trade Center</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="jie-page-sub">Review and act on pending alerts · {pending_count} pending</div>', unsafe_allow_html=True)

        if not pending:
            st.markdown('<div class="empty-state"><div class="icon">✅</div><h3>All caught up!</h3><p>No pending alerts requiring action</p></div>', unsafe_allow_html=True)
        else:
            for i, a in enumerate(pending):
                # First pending card opens expanded by default for quick action
                render_alert_card(a, mode="action", expanded=(i == 0))

        st.markdown("</div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════
    # ALERT DATABASE — actioned alerts + Claude analysis
    # ══════════════════════════════════════════════════
    elif tab == "database":
        st.markdown('<div class="jie-page">', unsafe_allow_html=True)
        st.markdown('<div class="jie-page-title">🗄️ Alert Database</div>', unsafe_allow_html=True)
        st.markdown('<div class="jie-page-sub">All actioned alerts with FM decisions and Claude chart analysis</div>', unsafe_allow_html=True)

        if not actioned:
            st.markdown('<div class="empty-state"><div class="icon">🗄️</div><h3>No actioned alerts yet</h3><p>Approved and denied alerts appear here with Claude analysis</p></div>', unsafe_allow_html=True)
        else:
            fc1, fc2, _ = st.columns([2, 2, 6])
            with fc1:
                status_f = st.selectbox("Status", ["All", "APPROVED", "DENIED"], key="db_status")
            with fc2:
                ticker_f = st.text_input("Search ticker", placeholder="e.g. NIFTY", key="db_ticker")

            filtered = actioned
            if status_f != "All":
                filtered = [a for a in filtered if a.get("status") == status_f]
            if ticker_f:
                filtered = [a for a in filtered if ticker_f.upper() in (a.get("ticker") or "").upper()]

            st.caption(f"{len(filtered)} actioned alerts")
            for a in filtered[:100]:
                render_alert_card(a, mode="database")

        st.markdown("</div>", unsafe_allow_html=True)

    # ── Auto-refresh every 30s using Streamlit's fragment rerun ──
    st.markdown("""
    <script>
    setTimeout(function() { window.location.reload(); }, 30000);
    </script>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
