"""
FIE v3 — Dashboard
Jhaveri Intelligence Platform
"""

import streamlit as st
import requests
import json
import base64
import html
import os
from datetime import datetime
from typing import Optional

API_URL    = os.getenv("FIE_API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="JIP — Financial Intelligence Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════════════════════
# DESIGN SYSTEM — Dark navy + slate, clean finance terminal aesthetic
# Accent: electric blue #2563eb  |  Bull: emerald #10b981  |  Bear: rose #f43f5e
# ══════════════════════════════════════════════════════════════════════════════

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&family=Geist+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, .stApp {
    font-family: 'Geist', system-ui, sans-serif;
    background: #0d1117;
    color: #e2e8f0;
    -webkit-font-smoothing: antialiased;
}
.block-container { padding: 0 !important; max-width: 100% !important; }
section[data-testid="stSidebar"] { display: none !important; }
#MainMenu, footer, header { display: none !important; visibility: hidden !important; }
.stDeployButton { display: none !important; }

/* ── HEADER ── */
.jip-hdr {
    background: #0d1117;
    border-bottom: 1px solid #1e293b;
    height: 50px; padding: 0 24px;
    display: flex; align-items: center; justify-content: space-between;
    position: sticky; top: 0; z-index: 300;
}
.jip-brand { display: flex; align-items: center; gap: 10px; }
.jip-brand-logo {
    width: 28px; height: 28px; border-radius: 6px;
    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; flex-shrink: 0;
}
.jip-brand-name { font-size: 13px; font-weight: 700; color: #f1f5f9; letter-spacing: 0.05em; }
.jip-brand-sep  { color: #334155; margin: 0 4px; }
.jip-brand-sub  { font-size: 11px; color: #64748b; letter-spacing: 0.04em; }
.jip-hdr-date   { font-size: 11px; color: #475569; font-family: 'Geist Mono', monospace; }

/* ── STATS ROW ── */
.stats-row {
    display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px;
    padding: 16px 24px 0;
}
.stat {
    background: #111827; border: 1px solid #1e293b; border-radius: 6px;
    padding: 10px 12px;
}
.stat-lbl { font-size: 9px; font-weight: 600; color: #475569; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 4px; }
.stat-val { font-size: 20px; font-weight: 700; color: #e2e8f0; line-height: 1; }
.stat-val.g { color: #10b981; }
.stat-val.r { color: #f43f5e; }
.stat-val.y { color: #f59e0b; }
.stat-sub { font-size: 9px; color: #475569; margin-top: 3px; }

/* ── PAGE CONTENT ── */
.jip-content { padding: 16px 24px 40px; }

/* ── ALERT CARD ── */
.ac {
    background: #111827;
    border: 1px solid #1e293b;
    border-radius: 6px;
    margin-bottom: 6px;
    overflow: hidden;
}
.ac.bull { border-left: 3px solid #10b981; }
.ac.bear { border-left: 3px solid #f43f5e; }
.ac-main {
    padding: 10px 14px;
    display: flex; align-items: flex-start; justify-content: space-between; gap: 16px;
}
.ac-left { flex: 1; min-width: 0; }
.ac-right { text-align: right; flex-shrink: 0; }
.ac-ticker {
    font-size: 15px; font-weight: 700; color: #f1f5f9;
    display: flex; align-items: center; gap: 8px; line-height: 1.2;
}
.ac-name   { font-size: 10px; color: #64748b; margin-top: 2px; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ac-meta   { font-size: 9px; color: #475569; margin-top: 5px; display: flex; align-items: center; gap: 6px; }
.ac-itv    { background: #1e293b; color: #94a3b8; border-radius: 3px; padding: 1px 6px; font-family: 'Geist Mono', monospace; font-size: 9px; }
.ac-price-lbl { font-size: 9px; color: #475569; text-transform: uppercase; letter-spacing: 0.06em; }
.ac-price { font-size: 17px; font-weight: 700; color: #60a5fa; line-height: 1.1; font-family: 'Geist Mono', monospace; }
.ac-ts    { font-size: 9px; color: #475569; margin-top: 2px; }
.ac-ts span { display: block; }

/* OHLCV strip */
.ac-ohlcv {
    display: flex; gap: 0;
    border-top: 1px solid #1e293b;
    background: #0d1117;
    padding: 6px 14px;
}
.ac-o-item { flex: 1; text-align: center; padding: 0 4px; border-right: 1px solid #1e293b; }
.ac-o-item:last-child { border-right: none; }
.ac-o-lbl { font-size: 8px; font-weight: 700; color: #334155; text-transform: uppercase; letter-spacing: 0.07em; }
.ac-o-val { font-size: 10px; font-weight: 500; color: #94a3b8; font-family: 'Geist Mono', monospace; margin-top: 1px; }

/* alert message text */
.ac-msg {
    font-size: 10px; color: #64748b;
    background: #0a0f1a; border-top: 1px solid #1e293b;
    padding: 7px 14px; line-height: 1.5;
    max-height: 52px; overflow: hidden;
}

/* ── CHIPS ── */
.chip { display: inline-block; border-radius: 3px; font-size: 9px; font-weight: 600; padding: 2px 6px; letter-spacing: 0.04em; text-transform: uppercase; }
.chip-bull { background: #064e3b; color: #34d399; }
.chip-bear { background: #4c0519; color: #fb7185; }
.chip-app  { background: #064e3b; color: #34d399; }
.chip-den  { background: #4c0519; color: #fb7185; }
.chip-imm  { background: #451a03; color: #fb923c; }
.chip-wk   { background: #1e1b4b; color: #818cf8; }
.chip-mo   { background: #1a1a2e; color: #a78bfa; }

/* ── FM DECISION STRIP ── */
.fm-strip {
    display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
    padding: 7px 14px; background: #0d1117; border-top: 1px solid #1e293b;
}
.fm-lbl    { font-size: 8px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.08em; }
.fm-action { font-size: 13px; font-weight: 800; color: #f1f5f9; }
.fm-ratio  { font-size: 9px; color: #64748b; width: 100%; padding-top: 3px; }

/* ── CLAUDE ANALYSIS BLOCK ── */
.cl-block {
    border-top: 1px solid #1d3a57;
    background: #0a1929;
    padding: 10px 14px 12px;
}
.cl-title {
    font-size: 9px; font-weight: 700; color: #3b82f6;
    text-transform: uppercase; letter-spacing: 0.09em; margin-bottom: 8px;
    display: flex; align-items: center; gap: 5px;
}
.cl-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 3px 20px; }
.cl-bullet {
    display: flex; align-items: flex-start; gap: 6px;
    font-size: 10px; color: #93c5fd; line-height: 1.45; padding: 2px 0;
}
.cl-n { font-size: 8px; font-weight: 700; color: #2563eb; min-width: 13px; flex-shrink: 0; margin-top: 2px; }

/* ── EMPTY STATE ── */
.empty {
    text-align: center; padding: 48px 24px; color: #334155;
}
.empty-icon { font-size: 32px; margin-bottom: 8px; }
.empty h3 { font-size: 13px; font-weight: 600; color: #475569; }
.empty p  { font-size: 11px; margin-top: 4px; color: #334155; }

/* ── API KEY BANNER ── */
.api-warn {
    background: #1c1206; border: 1px solid #78350f; border-radius: 5px;
    padding: 8px 14px; margin: 10px 24px 0;
    font-size: 11px; color: #fbbf24;
    display: flex; align-items: center; gap: 8px;
}
.api-warn code { background: #292107; padding: 1px 5px; border-radius: 3px; font-size: 10px; }

/* ── STREAMLIT WIDGET OVERRIDES ── */
div[data-testid="stButton"] > button {
    background: #1e293b !important;
    color: #94a3b8 !important;
    border: 1px solid #334155 !important;
    border-radius: 5px !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    padding: 5px 14px !important;
    transition: background 0.15s, color 0.15s !important;
    box-shadow: none !important;
}
div[data-testid="stButton"] > button:hover {
    background: #273549 !important;
    color: #e2e8f0 !important;
    border-color: #475569 !important;
}
div[data-testid="stButton"] > button[kind="primary"] {
    background: #1d4ed8 !important;
    color: #eff6ff !important;
    border-color: #2563eb !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #2563eb !important;
    color: #fff !important;
}
div[data-testid="stSelectbox"] label,
div[data-testid="stTextInput"] label,
div[data-testid="stFileUploader"] label { font-size: 10px !important; color: #64748b !important; font-weight: 600 !important; text-transform: uppercase !important; letter-spacing: 0.05em !important; }
div[data-testid="stSelectbox"] > div > div {
    background: #111827 !important; border: 1px solid #1e293b !important;
    border-radius: 5px !important; font-size: 12px !important; color: #e2e8f0 !important;
}
div[data-testid="stTextInput"] input {
    background: #111827 !important; border: 1px solid #1e293b !important;
    border-radius: 5px !important; font-size: 12px !important; color: #e2e8f0 !important;
}
div[data-testid="stFileUploader"] {
    background: #111827 !important; border: 1px dashed #334155 !important;
    border-radius: 6px !important;
}
div[data-testid="stFileUploader"] button {
    background: #1e293b !important; color: #94a3b8 !important;
    border: 1px solid #334155 !important; border-radius: 4px !important;
}
div[data-testid="stExpander"] {
    background: #111827 !important;
    border: 1px solid #1e293b !important;
    border-radius: 5px !important;
}
div[data-testid="stExpander"] summary {
    font-size: 11px !important; font-weight: 600 !important;
    color: #94a3b8 !important;
    background: #111827 !important;
    border-radius: 5px !important;
    padding: 8px 14px !important;
}
div[data-testid="stExpander"] summary:hover { color: #e2e8f0 !important; }
div[data-testid="stInfo"] { background: #0a1929 !important; border-color: #1d4ed8 !important; color: #93c5fd !important; font-size: 11px !important; }
div[data-testid="stSuccess"] { background: #052e16 !important; border-color: #16a34a !important; color: #86efac !important; font-size: 11px !important; }
div[data-testid="stError"] { background: #1c0a0a !important; border-color: #dc2626 !important; color: #fca5a5 !important; font-size: 11px !important; }
div[data-testid="stCaption"] { color: #475569 !important; font-size: 9px !important; }
div[data-testid="stImage"] img { border-radius: 5px; }
.stTabs [data-baseweb="tab-list"] { display: none; }

/* Scrollbar */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 3px; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def esc(v) -> str:
    if v is None: return ""
    return html.escape(str(v))

def fp(v) -> str:
    if v is None: return "—"
    try:
        f = float(v)
        return ("₹{:,.2f}" if f > 100 else "{:.5f}").format(f)
    except: return esc(v)

def fv(v) -> str:
    if v is None: return "—"
    try:
        f = float(v)
        if f >= 1e6: return "{:.1f}M".format(f / 1e6)
        if f >= 1e3: return "{:.1f}K".format(f / 1e3)
        return "{:.0f}".format(f)
    except: return esc(v)

def ft(ts: str) -> str:
    if not ts: return "—"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", ""))
        return dt.strftime("%d %b %y, %I:%M %p")
    except: return esc(ts)

def sig_chip(sig: str) -> str:
    s = (sig or "").upper()
    if s == "BULLISH": return '<span class="chip chip-bull">▲ Bull</span>'
    if s == "BEARISH": return '<span class="chip chip-bear">▼ Bear</span>'
    return ""  # No neutral chip

def prio_chip(p: str) -> str:
    if not p: return ""
    m = {
        "IMMEDIATELY":    ('<span class="chip chip-imm">🔴 Now</span>'),
        "WITHIN_A_WEEK":  ('<span class="chip chip-wk">🔵 Week</span>'),
        "WITHIN_A_MONTH": ('<span class="chip chip-mo">🟣 Month</span>'),
    }
    return m.get(p, esc(p))


# ══════════════════════════════════════════════════════════════════════════════
# API
# ══════════════════════════════════════════════════════════════════════════════

def get_alerts() -> list:
    try:
        r = requests.get(f"{API_URL}/api/alerts", params={"limit": 300}, timeout=8)
        r.raise_for_status()
        return r.json().get("alerts", [])
    except: return []

def post_action(payload: dict) -> dict:
    try:
        r = requests.post(
            f"{API_URL}/api/alerts/{payload['alert_id']}/action",
            json=payload, timeout=90,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"success": False, "error": str(e)}

def to_b64(f) -> str:
    f.seek(0)
    return base64.b64encode(f.read()).decode("utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# ALERT CARD
# ══════════════════════════════════════════════════════════════════════════════

def card(a: dict, mode: str = "view", first: bool = False):
    sig    = (a.get("signal_direction") or "").upper()
    bcls   = {"BULLISH": "bull", "BEARISH": "bear"}.get(sig, "")
    ticker = esc(a.get("ticker") or "—")
    name   = a.get("alert_name") or ""
    t_up   = ticker.replace("&amp;", "&")
    name_s = esc(name) if name.upper() not in [t_up.upper(), "ALERT", "", "UNKNOWN ALERT"] else ""
    exch   = esc(a.get("exchange") or "—")
    intv   = esc(a.get("interval") or "—")
    price  = a.get("price_at_alert") or a.get("price_close")
    msg    = esc((a.get("alert_data") or "")[:200])
    if len(a.get("alert_data") or "") > 200: msg += "…"
    t1     = ft(a.get("time_utc") or "")
    t2     = ft(a.get("received_at") or "")
    ts_html = ""
    if t1 != "—": ts_html += f'<span>Alert: {t1}</span>'
    if t2 != "—": ts_html += f'<span>Recv: {t2}</span>'

    action = a.get("action") or {}

    st.markdown(f"""
<div class="ac {bcls}">
  <div class="ac-main">
    <div class="ac-left">
      <div class="ac-ticker">{ticker} {sig_chip(sig)}</div>
      {f'<div class="ac-name">{name_s}</div>' if name_s else ""}
      <div class="ac-meta">{exch}&nbsp;·&nbsp;<span class="ac-itv">{intv}</span></div>
    </div>
    <div class="ac-right">
      <div class="ac-price-lbl">Alert Price</div>
      <div class="ac-price">{fp(price)}</div>
      <div class="ac-ts">{ts_html}</div>
    </div>
  </div>
  <div class="ac-ohlcv">
    <div class="ac-o-item"><div class="ac-o-lbl">O</div><div class="ac-o-val">{fp(a.get('price_open'))}</div></div>
    <div class="ac-o-item"><div class="ac-o-lbl">H</div><div class="ac-o-val">{fp(a.get('price_high'))}</div></div>
    <div class="ac-o-item"><div class="ac-o-lbl">L</div><div class="ac-o-val">{fp(a.get('price_low'))}</div></div>
    <div class="ac-o-item"><div class="ac-o-lbl">C</div><div class="ac-o-val">{fp(a.get('price_close'))}</div></div>
    <div class="ac-o-item"><div class="ac-o-lbl">Vol</div><div class="ac-o-val">{fv(a.get('volume'))}</div></div>
  </div>
  {f'<div class="ac-msg">{msg}</div>' if msg else ""}
</div>""", unsafe_allow_html=True)

    # ── TRADE CENTER action panel ──────────────────────────
    if mode == "action" and a.get("status") == "PENDING":
        with st.expander(f"⚡  Action — #{a['id']}  {a.get('ticker','')}", expanded=first):
            c1, c2 = st.columns([1, 1])
            with c1:
                act  = st.selectbox("Action", ["BUY","SELL","HOLD","RATIO","ACCUMULATE","REDUCE","SWITCH","WATCH"], key=f"ac_{a['id']}")
                prio = st.selectbox("Priority", ["IMMEDIATELY","WITHIN_A_WEEK","WITHIN_A_MONTH"], key=f"pr_{a['id']}")
            with c2:
                cf = st.file_uploader("Chart Screenshot", type=["png","jpg","jpeg","webp"], key=f"cf_{a['id']}",
                                      help="Upload a TradingView chart — Claude will analyze it on approval")
                if cf:
                    cf.seek(0)
                    st.image(cf.read(), caption="✅ Chart ready", use_column_width=True)

            is_ratio = (act == "RATIO")
            rl = rs = None
            if is_ratio:
                r1, r2 = st.columns(2)
                with r1: rl = st.text_input("Long leg",  placeholder="LONG 60% RELIANCE",  key=f"rl_{a['id']}")
                with r2: rs = st.text_input("Short leg", placeholder="SHORT 40% HDFCBANK", key=f"rs_{a['id']}")

            b1, b2 = st.columns(2)
            with b1:
                if st.button("✅  Approve", key=f"app_{a['id']}", use_container_width=True, type="primary"):
                    b64 = None
                    if cf:
                        cf.seek(0)
                        b64 = base64.b64encode(cf.read()).decode("utf-8")
                    if b64:
                        st.info("⏳ Sending chart to Claude for analysis…")
                    else:
                        st.info("⏳ Running text analysis with Claude…")
                    res = post_action({
                        "alert_id": a["id"], "decision": "APPROVED",
                        "action_call": act, "is_ratio": is_ratio,
                        "ratio_long": rl if is_ratio else None,
                        "ratio_short": rs if is_ratio else None,
                        "priority": prio, "chart_image_b64": b64,
                    })
                    if res.get("success"):
                        st.success("✅ Approved — moved to Approved Alerts")
                        st.rerun()
                    else:
                        st.error(f"Error: {res.get('error','Unknown')}")
            with b2:
                if st.button("✗  Deny", key=f"den_{a['id']}", use_container_width=True):
                    res = post_action({"alert_id": a["id"], "decision": "DENIED"})
                    if res.get("success"): st.rerun()
                    else: st.error(f"Error: {res.get('error','Unknown')}")

    # ── APPROVED ALERTS view ───────────────────────────────
    if mode == "approved" and action:
        legs_html = ""
        if action.get("is_ratio"):
            legs = [l for l in [action.get("ratio_long"), action.get("ratio_short")] if l]
            if legs: legs_html = f'<div class="fm-ratio">{"  ·  ".join(esc(l) for l in legs)}</div>'

        d = action.get("decision", "")
        dcls = "chip-app" if d == "APPROVED" else "chip-den"
        st.markdown(f"""
<div class="fm-strip">
  <span class="fm-lbl">FM</span>
  <span class="chip {dcls}">{esc(d)}</span>
  <span class="fm-action">{esc(action.get('action_call') or '—')}</span>
  {prio_chip(action.get('priority',''))}
  {legs_html}
</div>""", unsafe_allow_html=True)

        analysis = action.get("chart_analysis")
        if analysis:
            valid = [b for b in analysis if b and b != "—"]
            if valid:
                left  = valid[:4]
                right = valid[4:8]
                lh = "".join(f'<div class="cl-bullet"><span class="cl-n">{i+1}.</span><span>{esc(b)}</span></div>' for i,b in enumerate(left))
                rh = "".join(f'<div class="cl-bullet"><span class="cl-n">{i+5}.</span><span>{esc(b)}</span></div>' for i,b in enumerate(right))
                mode_label = "🔭 Vision" if action.get("has_chart") else "📝 Text"
                st.markdown(f"""
<div class="cl-block">
  <div class="cl-title">🤖 Claude Analysis &nbsp;·&nbsp; {mode_label}</div>
  <div class="cl-grid"><div>{lh}</div><div>{rh}</div></div>
</div>""", unsafe_allow_html=True)
        elif action.get("has_chart"):
            st.caption("⏳ Analysis pending")

        if action.get("has_chart"):
            with st.expander("📊 View Chart"):
                try:
                    r = requests.get(f"{API_URL}/api/alerts/{a['id']}/chart", timeout=8)
                    b64 = r.json().get("chart_image_b64","")
                    if b64: st.image(base64.b64decode(b64), use_column_width=True)
                except Exception as e:
                    st.warning(str(e))


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    if "tab" not in st.session_state:
        st.session_state.tab = "command"

    alerts   = get_alerts()
    pending  = [a for a in alerts if a.get("status") == "PENDING"]
    approved = [a for a in alerts if a.get("status") == "APPROVED"]
    denied   = [a for a in alerts if a.get("status") == "DENIED"]
    actioned = sorted(
        approved + denied,
        key=lambda a: (a.get("action") or {}).get("decision_at") or a.get("received_at") or "",
        reverse=True
    )
    np = len(pending)

    # ── HEADER ──────────────────────────────────────────────
    now = datetime.now().strftime("%d %b %Y  %H:%M")
    st.markdown(f"""
<div class="jip-hdr">
  <div class="jip-brand">
    <div class="jip-brand-logo">⚡</div>
    <span class="jip-brand-name">JHAVERI</span>
    <span class="jip-brand-sep">|</span>
    <span class="jip-brand-sub">Intelligence Platform</span>
  </div>
  <div class="jip-hdr-date">{now}</div>
</div>""", unsafe_allow_html=True)

    # ── API key warning ──────────────────────────────────────
    if not os.getenv("ANTHROPIC_API_KEY", "").strip():
        st.markdown("""
<div class="api-warn">
  ⚠️ <strong>ANTHROPIC_API_KEY not set</strong> — Claude analysis disabled.
  Add it in Railway: <code>ANTHROPIC_API_KEY=sk-ant-...</code>
</div>""", unsafe_allow_html=True)

    # ── STATS ────────────────────────────────────────────────
    bull = sum(1 for a in alerts if a.get("signal_direction") == "BULLISH")
    bear = sum(1 for a in alerts if a.get("signal_direction") == "BEARISH")
    st.markdown(f"""
<div class="stats-row">
  <div class="stat"><div class="stat-lbl">Total</div><div class="stat-val">{len(alerts)}</div><div class="stat-sub">Alerts</div></div>
  <div class="stat"><div class="stat-lbl">Pending</div><div class="stat-val y">{np}</div><div class="stat-sub">Awaiting action</div></div>
  <div class="stat"><div class="stat-lbl">Approved</div><div class="stat-val g">{len(approved)}</div><div class="stat-sub">Actioned</div></div>
  <div class="stat"><div class="stat-lbl">Denied</div><div class="stat-val r">{len(denied)}</div><div class="stat-sub">Passed</div></div>
  <div class="stat"><div class="stat-lbl">Bullish ▲</div><div class="stat-val g">{bull}</div><div class="stat-sub">Signals</div></div>
  <div class="stat"><div class="stat-lbl">Bearish ▼</div><div class="stat-val r">{bear}</div><div class="stat-sub">Signals</div></div>
</div>""", unsafe_allow_html=True)

    # ── TAB NAV ──────────────────────────────────────────────
    tc_lbl = f"📋 Trade Center ({np})" if np else "📋 Trade Center"
    t = st.session_state.tab
    nc1, nc2, nc3, nc4, _ = st.columns([1.1, 1.3, 1.3, 0.5, 4])
    with nc1:
        if st.button("⚡ Command Center", use_container_width=True,
                     type="primary" if t=="command" else "secondary"):
            st.session_state.tab = "command"; st.rerun()
    with nc2:
        if st.button(tc_lbl, use_container_width=True,
                     type="primary" if t=="trade" else "secondary"):
            st.session_state.tab = "trade"; st.rerun()
    with nc3:
        if st.button("✅ Approved Alerts", use_container_width=True,
                     type="primary" if t=="approved" else "secondary"):
            st.session_state.tab = "approved"; st.rerun()
    with nc4:
        if st.button("↺", use_container_width=True, help="Refresh"):
            st.rerun()

    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

    # ══════════════════════════════
    # COMMAND CENTER
    # ══════════════════════════════
    if t == "command":
        st.markdown('<div class="jip-content">', unsafe_allow_html=True)
        if not alerts:
            st.markdown('<div class="empty"><div class="empty-icon">📡</div><h3>No alerts yet</h3><p>Waiting for TradingView webhooks</p></div>', unsafe_allow_html=True)
        else:
            f1, f2, _ = st.columns([2, 2, 6])
            with f1: sf = st.selectbox("Signal", ["All","BULLISH","BEARISH"], key="cc_s")
            with f2: so = st.selectbox("Sort", ["Newest First","Oldest First"], key="cc_o")
            fl = alerts if sf == "All" else [a for a in alerts if a.get("signal_direction") == sf]
            if so == "Oldest First": fl = list(reversed(fl))
            st.caption(f"{len(fl)} alerts")
            for a in fl[:50]: card(a, mode="view")
        st.markdown("</div>", unsafe_allow_html=True)

    # ══════════════════════════════
    # TRADE CENTER
    # ══════════════════════════════
    elif t == "trade":
        st.markdown('<div class="jip-content">', unsafe_allow_html=True)
        st.caption(f"{np} pending alerts · Upload a chart screenshot to enable Claude vision analysis")
        if not pending:
            st.markdown('<div class="empty"><div class="empty-icon">✅</div><h3>All caught up</h3><p>No pending alerts</p></div>', unsafe_allow_html=True)
        else:
            for i, a in enumerate(pending):
                card(a, mode="action", first=(i == 0))
        st.markdown("</div>", unsafe_allow_html=True)

    # ══════════════════════════════
    # APPROVED ALERTS
    # ══════════════════════════════
    elif t == "approved":
        st.markdown('<div class="jip-content">', unsafe_allow_html=True)
        st.caption("FM decisions + Claude analysis · Approved and denied alerts")
        if not actioned:
            st.markdown('<div class="empty"><div class="empty-icon">🗄️</div><h3>No actioned alerts</h3><p>Approved alerts with Claude analysis appear here</p></div>', unsafe_allow_html=True)
        else:
            f1, f2, _ = st.columns([2, 2, 6])
            with f1: sf = st.selectbox("Status", ["All","APPROVED","DENIED"], key="db_s")
            with f2: tk = st.text_input("Search", placeholder="NIFTY, BITCOIN…", key="db_t")
            fl = actioned
            if sf != "All": fl = [a for a in fl if a.get("status") == sf]
            if tk: fl = [a for a in fl if tk.upper() in (a.get("ticker") or "").upper()]
            st.caption(f"{len(fl)} alerts")
            for a in fl[:100]: card(a, mode="approved")
        st.markdown("</div>", unsafe_allow_html=True)

    # Auto-refresh every 30s
    st.markdown("<script>setTimeout(()=>window.location.reload(),2000)</script>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
