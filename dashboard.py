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
from streamlit_autorefresh import st_autorefresh

API_URL    = os.getenv("FIE_API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="JIP — Financial Intelligence Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# DESIGN SYSTEM — Light theme, white cards, clean finance aesthetic
# Font: Inter  |  Green: #059669  |  Red: #dc2626  |  Blue: #2563eb
# ══════════════════════════════════════════════════════════════════════════════

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, .stApp {
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
    background: #f5f7fa;
    color: #1e293b;
    -webkit-font-smoothing: antialiased;
}
.block-container { padding: 0 28px !important; max-width: 100% !important; }
/* Sidebar styling */
section[data-testid="stSidebar"] {
    background: #f0fdf4 !important;
    border-right: 1px solid #d1fae5 !important;
    width: 260px !important;
    min-width: 260px !important;
}
section[data-testid="stSidebar"] > div { padding: 20px 16px !important; }
section[data-testid="stSidebar"] [data-testid="stRadio"] > label { font-size: 0 !important; height: 0 !important; overflow: hidden !important; }
section[data-testid="stSidebar"] [data-testid="stRadio"] label p { color: #1e293b !important; font-size: 13px !important; font-weight: 500 !important; }
section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label { padding: 8px 12px !important; border-radius: 8px !important; margin: 2px 0 !important; cursor: pointer !important; }
section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label:hover { background: #dcfce7 !important; }
section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label[data-checked="true"] { background: #bbf7d0 !important; }
section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label[data-checked="true"] p { color: #059669 !important; font-weight: 600 !important; }
#MainMenu, footer, header { display: none !important; visibility: hidden !important; }
.stDeployButton { display: none !important; }

/* ── HEADER ── */
.jip-hdr {
    background: #ffffff;
    border-bottom: 1px solid #e5e7eb;
    height: 56px; padding: 0 28px;
    display: flex; align-items: center; justify-content: space-between;
    position: sticky; top: 0; z-index: 300;
}
.jip-brand { display: flex; align-items: center; gap: 12px; }
.jip-brand-logo {
    width: 32px; height: 32px; border-radius: 8px;
    background: linear-gradient(135deg, #0d9488 0%, #059669 100%);
    display: flex; align-items: center; justify-content: center;
    font-size: 15px; flex-shrink: 0; color: #fff;
}
.jip-brand-name { font-size: 15px; font-weight: 800; color: #0f172a; letter-spacing: 0.03em; }
.jip-brand-sep  { color: #cbd5e1; margin: 0 2px; font-size: 16px; font-weight: 300; }
.jip-brand-sub  { font-size: 10px; color: #94a3b8; letter-spacing: 0.08em; font-weight: 600; text-transform: uppercase; }
.jip-hdr-date   { font-size: 13px; color: #64748b; font-weight: 400; }

/* ── STATS ROW ── */
.stats-row {
    display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px;
    padding: 16px 0 12px;
}
.stat {
    background: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px;
    padding: 16px 20px;
}
.stat-lbl { font-size: 12px; font-weight: 500; color: #94a3b8; margin-bottom: 8px; }
.stat-val { font-size: 30px; font-weight: 700; color: #1e293b; line-height: 1; letter-spacing: -0.02em; }
.stat-val.g { color: #059669; }
.stat-val.r { color: #dc2626; }
.stat-val.y { color: #d97706; }
.stat-sub { font-size: 11px; color: #b0b8c4; margin-top: 6px; font-weight: 400; }

/* ── PAGE CONTENT ── */
.jip-content { padding: 0; }

/* ── CARD GRID (Command Center) ── */
.card-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
}
@media (max-width: 1100px) {
    .card-grid { grid-template-columns: 1fr 1fr; }
    .stats-row { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 768px) {
    .card-grid { grid-template-columns: 1fr; }
}
/* ── PERFORMANCE CARD GRID ── */
.perf-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
@media (max-width: 1100px) { .perf-grid { grid-template-columns: 1fr 1fr; } }
@media (max-width: 768px)  { .perf-grid { grid-template-columns: 1fr; } }
.perf-card {
    background: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px;
    padding: 14px 16px; overflow: hidden;
}
.perf-card:hover { border-color: #cbd5e1; box-shadow: 0 1px 4px rgba(0,0,0,0.04); }
.perf-card .pc-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; margin-bottom: 10px; }
.perf-card .pc-ticker { font-size: 14px; font-weight: 700; color: #0f172a; }
.perf-card .pc-date { font-size: 10px; color: #94a3b8; margin-top: 2px; }
.perf-card .pc-row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 8px; }
.perf-card .pc-cell { flex: 1; min-width: 60px; }
.perf-card .pc-lbl { font-size: 9px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 2px; }
.perf-card .pc-val { font-size: 13px; font-weight: 600; color: #1e293b; font-family: 'SF Mono','Fira Code',monospace; }
.perf-card .pc-g { color: #059669; }
.perf-card .pc-r { color: #dc2626; }
.perf-card .pc-foot { display: flex; align-items: center; justify-content: space-between; padding-top: 8px; border-top: 1px solid #f1f5f9; }

/* ── ALERT CARD ── */
.ac {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    overflow: hidden;
}
.ac.bull { border-left: 3px solid #10b981; }
.ac.bear { border-left: 3px solid #ef4444; }
.ac-main {
    padding: 12px 16px;
    display: flex; align-items: flex-start; justify-content: space-between; gap: 14px;
}
.ac-left { flex: 1; min-width: 0; }
.ac-right { text-align: right; flex-shrink: 0; }
.ac-ticker {
    font-size: 14px; font-weight: 700; color: #0f172a;
    display: flex; align-items: center; gap: 8px; line-height: 1.2;
}
.ac-name   { font-size: 11px; color: #64748b; margin-top: 2px; max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ac-meta   { font-size: 10px; color: #64748b; margin-top: 4px; display: flex; align-items: center; gap: 6px; }
.ac-itv    { background: #f1f5f9; color: #64748b; border-radius: 4px; padding: 1px 6px; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 10px; font-weight: 500; }
.ac-price-lbl { font-size: 10px; color: #94a3b8; letter-spacing: 0.03em; }
.ac-price { font-size: 16px; font-weight: 700; color: #2563eb; line-height: 1.2; font-family: 'SF Mono', 'Fira Code', monospace; }
.ac-ts    { font-size: 9px; color: #b0b8c4; margin-top: 3px; }
.ac-ts span { display: block; }

/* OHLCV strip */
.ac-ohlcv {
    display: flex; gap: 0;
    border-top: 1px solid #f1f5f9;
    background: #f8fafc;
    padding: 5px 16px;
}
.ac-o-item { flex: 1; text-align: center; padding: 0 2px; border-right: 1px solid #e5e7eb; }
.ac-o-item:last-child { border-right: none; }
.ac-o-lbl { font-size: 9px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }
.ac-o-val { font-size: 11px; font-weight: 600; color: #475569; font-family: 'SF Mono', 'Fira Code', monospace; margin-top: 1px; }

/* alert message text */
.ac-msg {
    font-size: 11px; color: #64748b;
    background: #f8fafc; border-top: 1px solid #f1f5f9;
    padding: 7px 16px; line-height: 1.5;
    max-height: 44px; overflow: hidden;
}

/* ── CHIPS ── */
.chip { display: inline-block; border-radius: 4px; font-size: 10px; font-weight: 600; padding: 2px 8px; letter-spacing: 0.02em; text-transform: uppercase; }
.chip-bull { background: #ecfdf5; color: #059669; }
.chip-bear { background: #fef2f2; color: #dc2626; }
.chip-app  { background: #ecfdf5; color: #059669; }
.chip-den  { background: #fef2f2; color: #dc2626; }
.chip-imm  { background: #fff7ed; color: #ea580c; }
.chip-wk   { background: #eef2ff; color: #4f46e5; }
.chip-mo   { background: #f5f3ff; color: #7c3aed; }

/* ── FM DECISION STRIP ── */
.fm-strip {
    display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
    padding: 8px 16px; background: #f8fafc; border-top: 1px solid #f1f5f9;
}
.fm-lbl    { font-size: 9px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.06em; }
.fm-action { font-size: 13px; font-weight: 800; color: #0f172a; }
.fm-ratio  { font-size: 10px; color: #64748b; width: 100%; padding-top: 3px; }

/* ── INSIGHTS BLOCK (collapsible) ── */
.cl-details {
    border-top: 1px solid #dbeafe;
    background: #f8fafc;
}
.cl-details[open] { background: #eff6ff; }
.cl-summary {
    font-size: 10px; font-weight: 700; color: #2563eb;
    text-transform: uppercase; letter-spacing: 0.06em;
    padding: 10px 16px; cursor: pointer;
    display: flex; align-items: center; gap: 5px;
    list-style: none; user-select: none;
}
.cl-summary::-webkit-details-marker { display: none; }
.cl-summary::before {
    content: "▶"; font-size: 8px; color: #93c5fd; transition: transform 0.15s;
    display: inline-block; margin-right: 4px;
}
.cl-details[open] > .cl-summary::before { transform: rotate(90deg); }
.cl-summary:hover { background: #eff6ff; }
.cl-block {
    background: #eff6ff;
    padding: 8px 16px 14px;
}
.cl-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 18px; }
.cl-bullet {
    display: flex; align-items: flex-start; gap: 6px;
    font-size: 11px; color: #1e40af; line-height: 1.45; padding: 2px 0;
}
.cl-n { font-size: 9px; font-weight: 700; color: #2563eb; min-width: 14px; flex-shrink: 0; margin-top: 2px; }

/* ── EMPTY STATE ── */
.empty {
    text-align: center; padding: 60px 24px; color: #94a3b8;
    background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px;
    margin-top: 4px;
}
.empty-icon { font-size: 40px; margin-bottom: 12px; opacity: 0.6; }
.empty h3 { font-size: 15px; font-weight: 600; color: #475569; margin: 0; }
.empty p  { font-size: 13px; margin-top: 6px; color: #94a3b8; }

/* ── API KEY BANNER ── */
.api-warn {
    background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px;
    padding: 10px 16px; margin: 12px 0 0;
    font-size: 12px; color: #92400e;
    display: flex; align-items: center; gap: 8px;
}
.api-warn code { background: #fef3c7; padding: 2px 6px; border-radius: 4px; font-size: 11px; color: #78350f; }

/* ── TIGHTER STREAMLIT SPACING ── */
div[data-testid="stVerticalBlock"] { gap: 0rem !important; }
div[data-testid="stVerticalBlock"] > div { margin-top: 0 !important; padding-top: 0 !important; }
div[data-testid="stVerticalBlockBorderWrapper"] { padding: 0 !important; margin: 0 !important; }
div[data-testid="stHorizontalBlock"] { gap: 16px !important; align-items: end !important; }
div.stMarkdown { margin-bottom: 0 !important; }
div[data-testid="stCaptionContainer"] { margin-top: 2px !important; margin-bottom: 4px !important; }
div[data-testid="stElementContainer"] { margin: 0 !important; padding: 0 !important; }
div[data-testid="stColumn"] { padding: 0 4px !important; }
/* Target Streamlit's main inner block gap */
section.main .block-container > div { gap: 0 !important; }
section.main .block-container > div > div { gap: 0 !important; }
section.main .block-container > div > div > div { gap: 0 !important; }
div[data-testid="stVerticalBlock"] > div[style*="flex"] { gap: 0 !important; }
/* Reduce select/input vertical footprint */
div[data-testid="stSelectbox"], div[data-testid="stTextInput"] { margin-bottom: 0 !important; padding-bottom: 0 !important; }

/* ── STREAMLIT WIDGET OVERRIDES ── */
div[data-testid="stButton"] > button {
    background: #ffffff !important;
    color: #475569 !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 6px !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    padding: 4px 12px !important;
    height: 30px !important;
    min-height: 30px !important;
    transition: all 0.15s !important;
    box-shadow: none !important;
    font-family: 'Inter', system-ui, sans-serif !important;
    white-space: nowrap !important;
    letter-spacing: 0.01em !important;
    line-height: 1 !important;
}
div[data-testid="stButton"] > button:hover {
    background: #f1f5f9 !important;
    color: #0f172a !important;
    border-color: #cbd5e1 !important;
}
div[data-testid="stButton"] > button[kind="primary"] {
    background: #059669 !important;
    color: #ffffff !important;
    border-color: #059669 !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #047857 !important;
    color: #fff !important;
}
div[data-testid="stSelectbox"] label,
div[data-testid="stTextInput"] label,
div[data-testid="stFileUploader"] label {
    font-size: 11px !important; color: #64748b !important;
    font-weight: 600 !important; text-transform: uppercase !important;
    letter-spacing: 0.03em !important;
    font-family: 'Inter', system-ui, sans-serif !important;
}
div[data-testid="stSelectbox"] > div > div {
    background: #ffffff !important; border: 1px solid #d1d5db !important;
    border-radius: 8px !important; font-size: 13px !important; color: #1e293b !important;
}
div[data-testid="stTextInput"] input {
    background: #ffffff !important; border: 1px solid #d1d5db !important;
    border-radius: 8px !important; font-size: 13px !important; color: #1e293b !important;
}
div[data-testid="stFileUploader"] {
    background: #ffffff !important; border: 1px dashed #d1d5db !important;
    border-radius: 6px !important; padding: 2px !important;
}
div[data-testid="stFileUploader"] > div { padding: 4px 8px !important; }
div[data-testid="stFileUploader"] button {
    background: #f8fafc !important; color: #475569 !important;
    border: 1px solid #d1d5db !important; border-radius: 6px !important;
    font-size: 11px !important; padding: 3px 10px !important; height: 26px !important;
}
div[data-testid="stFileUploader"] small,
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] { font-size: 10px !important; }
div[data-testid="stFileUploader"] section { padding: 4px !important; }
div[data-testid="stExpander"] {
    background: #ffffff !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 8px !important;
}
div[data-testid="stExpander"] summary {
    font-size: 12px !important; font-weight: 600 !important;
    color: #475569 !important;
    background: #ffffff !important;
    border-radius: 8px !important;
    padding: 10px 16px !important;
}
div[data-testid="stExpander"] summary:hover { color: #1e293b !important; }
div[data-testid="stInfo"] { background: #eff6ff !important; border-color: #2563eb !important; color: #1e40af !important; font-size: 12px !important; border-radius: 8px !important; }
div[data-testid="stSuccess"] { background: #ecfdf5 !important; border-color: #059669 !important; color: #065f46 !important; font-size: 12px !important; border-radius: 8px !important; }
div[data-testid="stError"] { background: #fef2f2 !important; border-color: #dc2626 !important; color: #991b1b !important; font-size: 12px !important; border-radius: 8px !important; }
div[data-testid="stCaption"] { color: #94a3b8 !important; font-size: 11px !important; }
div[data-testid="stImage"] img { border-radius: 8px; }
.stTabs [data-baseweb="tab-list"] { display: none; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #f1f5f9; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

/* ── GLOBAL STREAMLIT COMPACTNESS ── */
.stApp > div > div > div > div { padding-top: 0 !important; }
section.main > div.block-container { padding-top: 0 !important; padding-bottom: 0 !important; }
div[data-testid="stAppViewBlockContainer"] { padding: 0 28px !important; }
div[data-testid="stMainBlockContainer"] { padding: 0 28px !important; }
/* Force zero gap on Streamlit emotion-cache flex containers */
div[class*="st-emotion-cache"][style*="flex-direction: column"] { gap: 0 !important; }
div[class*="e1f1d6gn"] { gap: 0 !important; }
div[class*="e17vllj"] { gap: 0 !important; }
div[class*="ea3mdgi"] { gap: 0 !important; }
/* Kill all Streamlit-generated vertical gaps */
.stApp [class*="st-emotion-cache"] { gap: 0 !important; row-gap: 0 !important; }
/* Keep horizontal gaps for columns */
div[data-testid="stHorizontalBlock"] { gap: 16px !important; }

/* ── URGENCY COLOR-CODED CARDS ── */
.ac.urgency-now  { border-top: 3px solid #ea580c; }
.ac.urgency-week { border-top: 3px solid #4f46e5; }
.ac.urgency-month { border-top: 3px solid #7c3aed; }
/* FM strip inside card-grid cards */
.ac .fm-strip-inline {
    display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
    padding: 6px 16px; background: #f8fafc; border-top: 1px solid #f1f5f9;
    font-size: 11px;
}
.ac .fm-strip-inline .fm-action-label { font-weight: 700; color: #0f172a; font-size: 12px; }
/* Button gap fix for Trade Center */
.trade-card-wrap { margin-bottom: 6px; }
/* Detail panel styling */
.detail-section { margin-bottom: 14px; }
.detail-title { font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; }

/* ── COMPACT CARD (Trade Center 3-col) ── */
.ac-sm { margin-bottom: 8px; }
.ac-sm .ac-main { padding: 10px 12px; gap: 10px; }
.ac-sm .ac-ticker { font-size: 13px; }
.ac-sm .ac-name { font-size: 10px; max-width: 180px; }
.ac-sm .ac-meta { font-size: 9px; }
.ac-sm .ac-price { font-size: 14px; }
.ac-sm .ac-price-lbl { font-size: 9px; }
.ac-sm .ac-ohlcv { padding: 6px 12px 8px; }
.ac-sm .ac-o-lbl { font-size: 9px; }
.ac-sm .ac-o-val { font-size: 11px; font-weight: 600; }
.ac-sm .ac-msg { font-size: 10px; padding: 4px 12px; max-height: 30px; }
.ac-sm .ac-ts { font-size: 8px; }

/* ── DETAIL DIALOG STYLING ── */
div[data-testid="stDialog"] > div { border-radius: 12px !important; }
.detail-section { margin-bottom: 14px; }
.detail-title { font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; }
.detail-insights { background: #eff6ff; border-radius: 8px; padding: 12px 16px; }
.detail-insights .di-item { display: flex; gap: 6px; font-size: 12px; color: #1e40af; line-height: 1.5; padding: 3px 0; }
.detail-insights .di-num { font-size: 10px; font-weight: 700; color: #2563eb; min-width: 16px; flex-shrink: 0; margin-top: 2px; }
.detail-fm-notes { background: #f0fdf4; border: 1px solid #d1fae5; border-radius: 8px; padding: 10px 14px; font-size: 12px; color: #065f46; line-height: 1.5; }

/* ── INDEX / PERFORMANCE TABLE ── */
.idx-table {
    width: 100%; border-collapse: collapse;
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 12px;
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    overflow: hidden;
}
.idx-table thead th {
    background: #f8fafc; color: #64748b;
    font-size: 10px; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.04em;
    padding: 10px 12px; text-align: left;
    border-bottom: 1px solid #e5e7eb;
    white-space: nowrap;
}
.idx-table tbody td {
    padding: 10px 12px; border-bottom: 1px solid #f1f5f9;
    color: #1e293b; font-size: 12px; white-space: nowrap;
}
.idx-table tbody tr:hover { background: #f8fafc; }
.idx-table .mono { font-family: 'SF Mono', 'Fira Code', monospace; }
.idx-table .g { color: #059669; font-weight: 600; }
.idx-table .r { color: #dc2626; font-weight: 600; }
.idx-table .signal-ow { background: #ecfdf5; color: #059669; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 10px; }
.idx-table .signal-uw { background: #fef2f2; color: #dc2626; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 10px; }
.idx-table .signal-base { background: #eef2ff; color: #4f46e5; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 10px; }
.idx-table .signal-n { background: #f1f5f9; color: #64748b; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 10px; }
.idx-table .sector-hdr td {
    background: #f0fdf4; color: #059669; font-size: 11px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.06em; padding: 8px 12px;
    border-bottom: 2px solid #a7f3d0; border-top: 1px solid #d1fae5;
}

/* ── CHART LIGHTBOX ── */
input.chart-toggle { display: none !important; }
.chart-lightbox {
    display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
    background: rgba(0,0,0,0.82); z-index: 9999;
    align-items: center; justify-content: center; cursor: pointer;
}
input.chart-toggle:checked + .chart-lightbox { display: flex !important; }
.chart-lightbox img { max-width: 90vw; max-height: 90vh; border-radius: 8px; box-shadow: 0 8px 32px rgba(0,0,0,0.4); }
.chart-lightbox-close {
    position: absolute; top: 16px; right: 24px; color: #fff;
    font-size: 28px; cursor: pointer; z-index: 10000;
    width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;
    background: rgba(255,255,255,0.15); border-radius: 50%;
}
.chart-thumb {
    cursor: pointer; border-radius: 6px; border: 1px solid #e5e7eb;
    transition: opacity 0.15s;
}
.chart-thumb:hover { opacity: 0.85; }

/* ── NO-BLACK: Force light theme on ALL interactive elements ── */
/* Dropdown popover / menu — ultra-high specificity */
body [data-baseweb="popover"],
body div[data-baseweb="popover"],
[data-baseweb="popover"] {
    background: #ffffff !important;
    background-color: #ffffff !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
}
body [data-baseweb="menu"],
body [data-baseweb="menu"] ul,
[data-baseweb="menu"],
[data-baseweb="menu"] ul,
[role="listbox"],
[role="listbox"] ul {
    background: #ffffff !important;
    background-color: #ffffff !important;
}
body [data-baseweb="menu"] li,
body [role="listbox"] li,
[data-baseweb="menu"] li,
[data-baseweb="menu"] [role="option"],
[role="listbox"] [role="option"],
[role="listbox"] li {
    background: #ffffff !important;
    background-color: #ffffff !important;
    color: #374151 !important;
    font-size: 13px !important;
}
body [data-baseweb="menu"] li:hover,
body [role="listbox"] li:hover,
[data-baseweb="menu"] li:hover,
[role="listbox"] li:hover,
[data-baseweb="menu"] [role="option"]:hover,
[role="listbox"] [role="option"]:hover {
    background: #f0fdf4 !important;
    background-color: #f0fdf4 !important;
    color: #059669 !important;
}
body [data-baseweb="menu"] li[aria-selected="true"],
body [role="listbox"] li[aria-selected="true"],
[data-baseweb="menu"] li[aria-selected="true"],
[role="listbox"] li[aria-selected="true"],
[data-baseweb="menu"] [role="option"][aria-selected="true"],
[role="listbox"] [role="option"][aria-selected="true"] {
    background: #ecfdf5 !important;
    background-color: #ecfdf5 !important;
    color: #059669 !important;
    font-weight: 600 !important;
}
/* Select trigger */
[data-baseweb="select"] > div,
body [data-baseweb="select"] > div {
    background: #ffffff !important;
    background-color: #ffffff !important;
    border-color: #d1d5db !important;
    color: #374151 !important;
}
[data-baseweb="select"] span,
[data-baseweb="select"] div[class*="value"] {
    color: #374151 !important;
}
[data-baseweb="select"] svg {
    color: #9ca3af !important;
}
/* Text inputs */
[data-baseweb="input"],
body [data-baseweb="input"] {
    background: #ffffff !important;
    background-color: #ffffff !important;
    border-color: #d1d5db !important;
}
[data-baseweb="input"] input,
body [data-baseweb="input"] input {
    color: #374151 !important;
    background: #ffffff !important;
    background-color: #ffffff !important;
}
/* Tags */
[data-baseweb="tag"] {
    background: #ecfdf5 !important;
    color: #059669 !important;
}
/* Expander icons/text */
div[data-testid="stExpander"] summary svg {
    color: #9ca3af !important;
}
/* Radio buttons */
section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label div {
    color: #374151 !important;
}
/* Ensure no dark focus outlines */
*:focus-visible {
    outline-color: #059669 !important;
}
/* Override dark backgrounds on Streamlit widgets */
div[data-testid="stSelectbox"] [data-baseweb="select"] > div > div {
    color: #374151 !important;
    background: #ffffff !important;
}
/* Kill any remaining dark overlays from Streamlit theme */
div[data-baseweb="popover"] > div,
div[data-baseweb="popover"] > div > div,
div[data-baseweb="popover"] > div > div > ul {
    background: #ffffff !important;
    background-color: #ffffff !important;
}
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
    return ""

def prio_chip(p: str) -> str:
    if not p: return ""
    m = {
        "IMMEDIATELY":    ('<span class="chip chip-imm">🔴 Now</span>'),
        "WITHIN_A_WEEK":  ('<span class="chip chip-wk">🔵 Week</span>'),
        "WITHIN_A_MONTH": ('<span class="chip chip-mo">🟣 Month</span>'),
    }
    return m.get(p, esc(p))


# ══════════════════════════════════════════════════════════════════════════════
# INDEX SECTOR CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════════════

TOP_25_INDICES = [
    "NIFTY 50", "NIFTY BANK", "NIFTY IT", "NIFTY NEXT 50", "NIFTY FINANCIAL SERVICES",
    "NIFTY MIDCAP SELECT", "NIFTY 100", "NIFTY 500", "NIFTY PHARMA", "NIFTY AUTO",
    "NIFTY FMCG", "NIFTY METAL", "NIFTY REALTY", "NIFTY ENERGY", "NIFTY MIDCAP 50",
    "NIFTY MIDCAP 100", "NIFTY SMALLCAP 100", "NIFTY SMALLCAP 250", "NIFTY PSU BANK",
    "NIFTY PRIVATE BANK", "NIFTY HEALTHCARE INDEX", "NIFTY CONSUMER DURABLES",
    "NIFTY OIL & GAS", "NIFTY MEDIA", "INDIA VIX",
]
_TOP_25_SET = set(TOP_25_INDICES)

INDEX_SECTOR_MAP = {
    # Broad Market
    "NIFTY 50": "Broad Market", "NIFTY NEXT 50": "Broad Market", "NIFTY 100": "Broad Market",
    "NIFTY 200": "Broad Market", "NIFTY 500": "Broad Market", "NIFTY TOTAL MARKET": "Broad Market",
    "NIFTY MIDCAP SELECT": "Broad Market", "NIFTY500 MULTICAP 50:25:25": "Broad Market",
    "NIFTY LARGEMIDCAP 250": "Broad Market",
    # Banking & Financial
    "NIFTY BANK": "Banking & Financial", "NIFTY FINANCIAL SERVICES": "Banking & Financial",
    "NIFTY PSU BANK": "Banking & Financial", "NIFTY PRIVATE BANK": "Banking & Financial",
    "NIFTY FINANCIAL SERVICES 25/50": "Banking & Financial",
    "NIFTY FINANCIAL SERVICES EX-BANK": "Banking & Financial",
    "NIFTY MIDSMALL FINANCIAL SERVICES": "Banking & Financial",
    "NIFTY CAPITAL MARKETS": "Banking & Financial",
    # IT & Technology
    "NIFTY IT": "IT & Technology", "NIFTY MIDSMALL IT & TELECOM": "IT & Technology",
    "NIFTY INDIA DIGITAL": "IT & Technology", "NIFTY INDIA INTERNET": "IT & Technology",
    # Pharma & Healthcare
    "NIFTY PHARMA": "Pharma & Healthcare", "NIFTY HEALTHCARE INDEX": "Pharma & Healthcare",
    "NIFTY MIDSMALL HEALTHCARE": "Pharma & Healthcare", "NIFTY500 HEALTHCARE": "Pharma & Healthcare",
    # Auto & Mobility
    "NIFTY AUTO": "Auto & Mobility", "NIFTY EV & NEW AGE AUTOMOTIVE": "Auto & Mobility",
    "NIFTY MOBILITY": "Auto & Mobility", "NIFTY TRANSPORTATION & LOGISTICS": "Auto & Mobility",
    # Consumer & FMCG
    "NIFTY FMCG": "Consumer & FMCG", "NIFTY CONSUMER DURABLES": "Consumer & FMCG",
    "NIFTY INDIA CONSUMPTION": "Consumer & FMCG", "NIFTY INDIA NEW AGE CONSUMPTION": "Consumer & FMCG",
    "NIFTY MIDSMALL INDIA CONSUMPTION": "Consumer & FMCG", "NIFTY NON-CYCLICAL CONSUMER": "Consumer & FMCG",
    # Commodities & Energy
    "NIFTY METAL": "Commodities & Energy", "NIFTY ENERGY": "Commodities & Energy",
    "NIFTY OIL & GAS": "Commodities & Energy", "NIFTY COMMODITIES": "Commodities & Energy",
    "NIFTY CHEMICALS": "Commodities & Energy",
    # Infra & Realty
    "NIFTY REALTY": "Infra & Realty", "NIFTY INFRASTRUCTURE": "Infra & Realty",
    "NIFTY CORE HOUSING": "Infra & Realty", "NIFTY HOUSING": "Infra & Realty",
    "NIFTY INDIA INFRASTRUCTURE & LOGISTICS": "Infra & Realty",
    "NIFTY500 MULTICAP INFRASTRUCTURE 50:30:20": "Infra & Realty",
    # Mid & Small Cap
    "NIFTY MIDCAP 50": "Mid & Small Cap", "NIFTY MIDCAP 100": "Mid & Small Cap",
    "NIFTY MIDCAP 150": "Mid & Small Cap", "NIFTY SMALLCAP 50": "Mid & Small Cap",
    "NIFTY SMALLCAP 100": "Mid & Small Cap", "NIFTY SMALLCAP 250": "Mid & Small Cap",
    "NIFTY MIDSMALLCAP 400": "Mid & Small Cap", "NIFTY MICROCAP 250": "Mid & Small Cap",
    # Thematic
    "NIFTY MEDIA": "Thematic", "NIFTY MNC": "Thematic", "NIFTY CPSE": "Thematic",
    "NIFTY PSE": "Thematic", "NIFTY SERVICES SECTOR": "Thematic",
    "NIFTY INDIA MANUFACTURING": "Thematic", "NIFTY500 MULTICAP INDIA MANUFACTURING 50:30:20": "Thematic",
    "NIFTY INDIA DEFENCE": "Thematic", "NIFTY INDIA TOURISM": "Thematic",
    "NIFTY RURAL": "Thematic", "NIFTY INDIA RAILWAYS PSU": "Thematic",
    "NIFTY CONGLOMERATE 50": "Thematic", "NIFTY IPO": "Thematic",
    "NIFTY INDIA CORPORATE GROUP INDEX - TATA GROUP 25% CAP": "Thematic",
    "NIFTY INDIA SELECT 5 CORPORATE GROUPS (MAATR)": "Thematic",
    # Strategy & Factor
    "NIFTY ALPHA 50": "Strategy", "NIFTY50 VALUE 20": "Strategy",
    "NIFTY100 QUALITY 30": "Strategy", "NIFTY50 EQUAL WEIGHT": "Strategy",
    "NIFTY100 EQUAL WEIGHT": "Strategy", "NIFTY100 LOW VOLATILITY 30": "Strategy",
    "NIFTY200 QUALITY 30": "Strategy", "NIFTY200 MOMENTUM 30": "Strategy",
    "NIFTY200 ALPHA 30": "Strategy", "NIFTY200 VALUE 30": "Strategy",
    "NIFTY ALPHA LOW-VOLATILITY 30": "Strategy", "NIFTY MIDCAP150 QUALITY 50": "Strategy",
    "NIFTY MIDCAP150 MOMENTUM 50": "Strategy", "NIFTY500 MOMENTUM 50": "Strategy",
    "NIFTY DIVIDEND OPPORTUNITIES 50": "Strategy", "NIFTY GROWTH SECTORS 15": "Strategy",
    "NIFTY HIGH BETA 50": "Strategy", "NIFTY LOW VOLATILITY 50": "Strategy",
    "NIFTY QUALITY LOW-VOLATILITY 30": "Strategy", "NIFTY SMALLCAP250 QUALITY 50": "Strategy",
    "NIFTY SMALLCAP250 MOMENTUM QUALITY 100": "Strategy",
    "NIFTY MIDSMALLCAP400 MOMENTUM QUALITY 100": "Strategy",
    "NIFTY500 EQUAL WEIGHT": "Strategy", "NIFTY500 VALUE 50": "Strategy",
    "NIFTY500 QUALITY 50": "Strategy", "NIFTY500 LOW VOLATILITY 50": "Strategy",
    "NIFTY WAVES": "Strategy", "NIFTY TOP 10 EQUAL WEIGHT": "Strategy",
    "NIFTY TOP 15 EQUAL WEIGHT": "Strategy", "NIFTY TOP 20 EQUAL WEIGHT": "Strategy",
    "NIFTY500 MULTICAP MOMENTUM QUALITY 50": "Strategy",
    "NIFTY ALPHA QUALITY LOW-VOLATILITY 30": "Strategy",
    "NIFTY ALPHA QUALITY VALUE LOW-VOLATILITY 30": "Strategy",
    "NIFTY100 ALPHA 30": "Strategy", "NIFTY500 MULTIFACTOR MQVLV 50": "Strategy",
    "NIFTY500 FLEXICAP QUALITY 30": "Strategy",
    "NIFTY TOTAL MARKET MOMENTUM QUALITY 50": "Strategy",
    # Fixed Income
    "NIFTY 8-13 YR G-SEC": "Fixed Income", "NIFTY 10 YR BENCHMARK G-SEC": "Fixed Income",
    "NIFTY 10 YR BENCHMARK G-SEC (CLEAN PRICE)": "Fixed Income",
    "NIFTY 4-8 YR G-SEC INDEX": "Fixed Income", "NIFTY 11-15 YR G-SEC INDEX": "Fixed Income",
    "NIFTY 15 YR AND ABOVE G-SEC INDEX": "Fixed Income",
    "NIFTY COMPOSITE G-SEC INDEX": "Fixed Income",
    "NIFTY BHARAT BOND INDEX - APRIL 2030": "Fixed Income",
    "NIFTY BHARAT BOND INDEX - APRIL 2031": "Fixed Income",
    "NIFTY BHARAT BOND INDEX - APRIL 2032": "Fixed Income",
    "NIFTY BHARAT BOND INDEX - APRIL 2033": "Fixed Income",
    # Volatility
    "INDIA VIX": "Volatility",
    # ESG & Shariah
    "NIFTY100 ESG SECTOR LEADERS": "ESG & Shariah", "NIFTY100 ESG": "ESG & Shariah",
    "NIFTY100 ENHANCED ESG": "ESG & Shariah", "NIFTY SHARIAH 25": "ESG & Shariah",
    "NIFTY50 SHARIAH": "ESG & Shariah", "NIFTY500 SHARIAH": "ESG & Shariah",
    # Leveraged / Derived
    "NIFTY50 TR 2X LEVERAGE": "Leveraged", "NIFTY50 PR 2X LEVERAGE": "Leveraged",
    "NIFTY50 TR 1X INVERSE": "Leveraged", "NIFTY50 PR 1X INVERSE": "Leveraged",
    "NIFTY50 DIVIDEND POINTS": "Leveraged", "NIFTY50 USD": "Leveraged",
}

SECTOR_ORDER = [
    "Broad Market", "Banking & Financial", "IT & Technology", "Pharma & Healthcare",
    "Auto & Mobility", "Consumer & FMCG", "Commodities & Energy", "Infra & Realty",
    "Mid & Small Cap", "Thematic", "Strategy", "Fixed Income", "Volatility",
    "ESG & Shariah", "Leveraged", "Other",
]

def _get_sector(nse_name):
    return INDEX_SECTOR_MAP.get(nse_name, "Other")


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

def card_html(a: dict) -> str:
    """Return HTML string for an alert card (no Streamlit widgets)."""
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

    return f"""<div class="ac {bcls}">
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
</div>"""


def card(a: dict):
    """Render an alert card as HTML."""
    st.markdown(card_html(a), unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# FM ACTION DIALOG — Modal popup for approving alerts
# ══════════════════════════════════════════════════════════════════════════════

@st.dialog("FM Action Panel", width="large")
def fm_action_dialog(alert_id, ticker_name):
    """Modal dialog for FM to approve an alert with action details."""
    _PRIO_MAP = {
        "Immediately": "IMMEDIATELY",
        "Within a Week": "WITHIN_A_WEEK",
        "Within a Month": "WITHIN_A_MONTH",
    }

    st.markdown(f"""<div style="display:flex;align-items:center;gap:12px;padding:8px 0 12px;border-bottom:1px solid #e5e7eb;margin-bottom:12px;">
<div style="width:32px;height:32px;border-radius:8px;background:#ecfdf5;display:flex;align-items:center;justify-content:center;font-size:14px;">📊</div>
<div>
<div style="font-size:14px;font-weight:700;color:#0f172a;">{esc(ticker_name)}</div>
<div style="font-size:11px;color:#64748b;">Alert #{alert_id} · Complete the fields below and submit</div>
</div>
</div>""", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        act = st.selectbox("Action", ["BUY","SELL","HOLD","RATIO","ACCUMULATE","REDUCE","SWITCH","WATCH"], key="dlg_act")
    with c2:
        prio_label = st.selectbox("Priority / Intensity", list(_PRIO_MAP.keys()), key="dlg_prio")
    prio = _PRIO_MAP[prio_label]

    c3, c4 = st.columns(2)
    with c3:
        fm_notes = st.text_area("FM Commentary (optional)", placeholder="Add your notes, thesis, or observations...", key="dlg_notes", height=120)
    with c4:
        cf = st.file_uploader("Chart Screenshot (optional)", type=["png","jpg","jpeg","webp"], key="dlg_chart")
        if cf:
            cf.seek(0)
            st.image(cf.read(), caption="Chart ready", width=200)

    is_ratio = (act == "RATIO")
    rl = rs = rnt = rdt = None
    if is_ratio:
        r1, r2 = st.columns(2)
        with r1:
            rl = st.text_input("Long leg", placeholder="LONG 60% RELIANCE", key="dlg_rl")
            rnt = st.text_input("Numerator Ticker", placeholder="e.g. RELIANCE", key="dlg_rnt")
        with r2:
            rs = st.text_input("Short leg", placeholder="SHORT 40% HDFCBANK", key="dlg_rs")
            rdt = st.text_input("Denominator Ticker", placeholder="e.g. HDFCBANK", key="dlg_rdt")

    st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)
    sb1, sb2, _ = st.columns([2, 2, 6])
    with sb1:
        if st.button("Submit Approval", type="primary", use_container_width=True, key="dlg_submit"):
            b64 = None
            if cf:
                cf.seek(0)
                b64 = base64.b64encode(cf.read()).decode("utf-8")
            with st.spinner("Approving…"):
                res = post_action({
                    "alert_id": alert_id, "decision": "APPROVED",
                    "action_call": act, "is_ratio": is_ratio,
                    "ratio_long": rl if is_ratio else None,
                    "ratio_short": rs if is_ratio else None,
                    "ratio_numerator_ticker": rnt if is_ratio else None,
                    "ratio_denominator_ticker": rdt if is_ratio else None,
                    "priority": prio, "chart_image_b64": b64,
                    "fm_notes": fm_notes if fm_notes else None,
                })
            if res.get("success"):
                st.session_state.action_card_id = None
                st.rerun()
            else:
                st.error(f"Error: {res.get('error','Unknown')}")
    with sb2:
        if st.button("Cancel", use_container_width=True, key="dlg_cancel"):
            st.session_state.action_card_id = None
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    # Auto-refresh every 30 seconds — Streamlit preserves widget state across reruns
    st_autorefresh(interval=30000, key="auto_refresh")

    alerts   = get_alerts()
    pending  = [a for a in alerts if a.get("status") == "PENDING"]
    approved = [a for a in alerts if a.get("status") == "APPROVED"]
    denied   = [a for a in alerts if a.get("status") == "DENIED"]
    np_count = len(pending)
    bull = sum(1 for a in alerts if a.get("signal_direction") == "BULLISH")
    bear = sum(1 for a in alerts if a.get("signal_direction") == "BEARISH")

    # ── SIDEBAR ─────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
    <div style="width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,#0d9488,#059669);display:flex;align-items:center;justify-content:center;font-size:17px;color:#fff;flex-shrink:0;">⚡</div>
    <div>
        <div style="font-size:15px;font-weight:800;color:#0f172a;letter-spacing:0.03em;">JHAVERI</div>
        <div style="font-size:9px;color:#94a3b8;letter-spacing:0.08em;font-weight:600;text-transform:uppercase;">Intelligence Platform</div>
    </div>
</div>""", unsafe_allow_html=True)

        st.markdown(f"""
<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin:12px 0 16px;">
    <div style="background:#f8fafc;border:1px solid #e5e7eb;border-radius:8px;padding:8px 10px;text-align:center;">
        <div style="font-size:18px;font-weight:700;color:#1e293b;">{len(alerts)}</div>
        <div style="font-size:9px;color:#94a3b8;font-weight:500;">Total</div>
    </div>
    <div style="background:#fff7ed;border:1px solid #fde68a;border-radius:8px;padding:8px 10px;text-align:center;">
        <div style="font-size:18px;font-weight:700;color:#d97706;">{np_count}</div>
        <div style="font-size:9px;color:#d97706;font-weight:500;">Pending</div>
    </div>
    <div style="background:#ecfdf5;border:1px solid #a7f3d0;border-radius:8px;padding:8px 10px;text-align:center;">
        <div style="font-size:18px;font-weight:700;color:#059669;">{len(approved)}</div>
        <div style="font-size:9px;color:#059669;font-weight:500;">Approved</div>
    </div>
</div>""", unsafe_allow_html=True)

        nav_options = [
            "Command Center",
            "Trade Center",
            "Approved Cards",
            "Alert Performance",
            "Market Pulse",
        ]
        nav_keys = ["command", "trade", "approved", "perf", "pulse"]

        selected = st.radio("Navigation", nav_options, key="nav_radio", label_visibility="collapsed")
        t = nav_keys[nav_options.index(selected)]

        if np_count and t == "trade":
            st.caption(f"{np_count} pending")

        st.markdown(f'<div style="font-size:10px;color:#b0b8c4;margin-top:16px;text-align:center;">{datetime.now().strftime("%A, %d %b %Y")}<br/>{datetime.now().strftime("%I:%M %p")}<br/>Auto-refreshing</div>', unsafe_allow_html=True)

    # ── Reset cross-page session state on nav change ──
    if "last_page" not in st.session_state:
        st.session_state.last_page = t
    if st.session_state.last_page != t:
        st.session_state.last_page = t
        # Clear action/detail states from other pages
        for k in ["action_card_id", "approved_detail_id", "detail_alert_id"]:
            if k in st.session_state:
                st.session_state[k] = None

    # ── API key warning ──
    try:
        _status = requests.get(f"{API_URL}/api/status", timeout=3).json()
        if not _status.get("analysis_enabled"):
            st.markdown("""
<div class="api-warn">
  ⚠️ <strong>Analysis disabled</strong> — Set ANTHROPIC_API_KEY on the server.
  <code>ANTHROPIC_API_KEY=sk-ant-...</code>
</div>""", unsafe_allow_html=True)
    except Exception:
        pass

    # ══════════════════════════════
    # COMMAND CENTER — Grid layout
    # ══════════════════════════════
    if t == "command":
        # Stats row
        st.markdown(f"""
<div class="stats-row">
  <div class="stat"><div class="stat-lbl">Total Alerts</div><div class="stat-val">{len(alerts)}</div><div class="stat-sub">All signals</div></div>
  <div class="stat"><div class="stat-lbl">Pending</div><div class="stat-val y">{np_count}</div><div class="stat-sub">Awaiting action</div></div>
  <div class="stat"><div class="stat-lbl">Approved</div><div class="stat-val g">{len(approved)}</div><div class="stat-sub">Actioned</div></div>
  <div class="stat"><div class="stat-lbl">Denied</div><div class="stat-val r">{len(denied)}</div><div class="stat-sub">Passed</div></div>
  <div class="stat"><div class="stat-lbl">Bullish ▲</div><div class="stat-val g">{bull}</div><div class="stat-sub">Signals</div></div>
  <div class="stat"><div class="stat-lbl">Bearish ▼</div><div class="stat-val r">{bear}</div><div class="stat-sub">Signals</div></div>
</div>""", unsafe_allow_html=True)

        if not pending:
            st.markdown('<div class="empty"><div class="empty-icon">📡</div><h3>No pending alerts</h3><p>Waiting for incoming TradingView webhooks</p></div>', unsafe_allow_html=True)
        else:
            f1, f2, _ = st.columns([2, 2, 6])
            with f1: sf = st.selectbox("Signal", ["All","BULLISH","BEARISH"], key="cc_s")
            with f2: so = st.selectbox("Sort", ["Newest First","Oldest First"], key="cc_o")
            st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
            fl = pending if sf == "All" else [a for a in pending if a.get("signal_direction") == sf]
            if so == "Oldest First": fl = list(reversed(fl))
            st.caption(f"{len(fl)} pending alerts")
            cards_html = "".join(card_html(a) for a in fl[:50])
            st.markdown(f'<div class="card-grid">{cards_html}</div>', unsafe_allow_html=True)

    # ══════════════════════════════
    # TRADE CENTER — Cards + Action
    # ══════════════════════════════
    elif t == "trade":
        # Track which card is being actioned
        if "action_card_id" not in st.session_state:
            st.session_state.action_card_id = None

        # ── Filters ──
        f1, f2, _ = st.columns([2, 2, 6])
        with f1: tc_sf = st.selectbox("Signal", ["All","BULLISH","BEARISH"], key="tc_s")
        with f2: tc_so = st.selectbox("Sort", ["Newest First","Oldest First"], key="tc_o")
        st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)

        tc_list = pending if tc_sf == "All" else [a for a in pending if a.get("signal_direction") == tc_sf]
        if tc_so == "Oldest First": tc_list = list(reversed(tc_list))

        st.caption(f"{len(tc_list)} pending alerts · Click Approve to action")
        if not tc_list:
            st.markdown('<div class="empty"><div class="empty-icon">✅</div><h3>All caught up</h3><p>No pending alerts</p></div>', unsafe_allow_html=True)
        else:
            # Render cards in 3-col grid with approve/deny buttons
            cols = st.columns(3)
            for i, a in enumerate(tc_list):
                with cols[i % 3]:
                    st.markdown(f'<div class="ac-sm">{card_html(a)}</div>', unsafe_allow_html=True)
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("Approve", key=f"apbtn_{a['id']}", use_container_width=True, type="primary"):
                            st.session_state.action_card_id = a["id"]
                            st.rerun()
                    with b2:
                        if st.button("Deny", key=f"denbtn_{a['id']}", use_container_width=True):
                            res = post_action({"alert_id": a["id"], "decision": "DENIED"})
                            if res.get("success"): st.rerun()
                            else: st.error(f"Error: {res.get('error','Unknown')}")
                    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)

        # ── Open FM Action dialog if Approve was clicked ──
        active_id = st.session_state.get("action_card_id")
        if active_id:
            active_alert = next((a for a in pending if a["id"] == active_id), None)
            if active_alert:
                fm_action_dialog(active_id, active_alert.get("ticker", "—"))

    # ══════════════════════════════
    # APPROVED CARDS — Grid layout
    # ══════════════════════════════
    elif t == "approved":
        # Stats row for approved cards
        app_imm = sum(1 for a in approved if (a.get("action") or {}).get("priority") == "IMMEDIATELY")
        app_wk  = sum(1 for a in approved if (a.get("action") or {}).get("priority") == "WITHIN_A_WEEK")
        app_mo  = sum(1 for a in approved if (a.get("action") or {}).get("priority") == "WITHIN_A_MONTH")
        st.markdown(f"""<div class="stats-row" style="grid-template-columns: repeat(4, 1fr);">
  <div class="stat"><div class="stat-lbl">Approved</div><div class="stat-val g">{len(approved)}</div><div class="stat-sub">Total approved</div></div>
  <div class="stat"><div class="stat-lbl">Immediate</div><div class="stat-val" style="color:#ea580c;">{app_imm}</div><div class="stat-sub">Act now</div></div>
  <div class="stat"><div class="stat-lbl">This Week</div><div class="stat-val" style="color:#4f46e5;">{app_wk}</div><div class="stat-sub">Within a week</div></div>
  <div class="stat"><div class="stat-lbl">This Month</div><div class="stat-val" style="color:#7c3aed;">{app_mo}</div><div class="stat-sub">Within a month</div></div>
</div>""", unsafe_allow_html=True)

        if not approved:
            st.markdown('<div class="empty"><div class="empty-icon">🗄️</div><h3>No approved alerts</h3><p>Approve alerts in Trade Center — they appear here with insights</p></div>', unsafe_allow_html=True)
        else:
            # Filters
            f1, f2, f3, _ = st.columns([2, 2, 2, 4])
            _URG_MAP = {"All": "All", "Immediately": "IMMEDIATELY", "Within a Week": "WITHIN_A_WEEK", "Within a Month": "WITHIN_A_MONTH"}
            with f1: ap_uf_label = st.selectbox("Urgency", list(_URG_MAP.keys()), key="ap_u")
            with f2: ap_sf = st.selectbox("Signal", ["All","BULLISH","BEARISH"], key="ap_s")
            with f3: ap_tk = st.text_input("Search", placeholder="NIFTY, BITCOIN…", key="ap_t")
            st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

            ap_uf = _URG_MAP[ap_uf_label]
            fl = list(approved)
            if ap_uf != "All": fl = [a for a in fl if (a.get("action") or {}).get("priority") == ap_uf]
            if ap_sf != "All": fl = [a for a in fl if a.get("signal_direction") == ap_sf]
            if ap_tk: fl = [a for a in fl if ap_tk.upper() in (a.get("ticker") or "").upper()]
            st.caption(f"{len(fl)} approved alerts")

            # Track which approved alert detail to show
            if "approved_detail_id" not in st.session_state:
                st.session_state.approved_detail_id = None

            # Build approved cards as HTML in 3-col grid — same base as Command Center card
            def _approved_card_html(a):
                action = a.get("action") or {}
                prio = action.get("priority", "")
                urgency_cls = ""
                if prio == "IMMEDIATELY": urgency_cls = " urgency-now"
                elif prio == "WITHIN_A_WEEK": urgency_cls = " urgency-week"
                elif prio == "WITHIN_A_MONTH": urgency_cls = " urgency-month"

                sig = (a.get("signal_direction") or "").upper()
                bcls = {"BULLISH": "bull", "BEARISH": "bear"}.get(sig, "")
                ticker = esc(a.get("ticker") or "—")
                name = a.get("alert_name") or ""
                t_up = ticker.replace("&amp;", "&")
                name_s = esc(name) if name.upper() not in [t_up.upper(), "ALERT", "", "UNKNOWN ALERT"] else ""
                exch = esc(a.get("exchange") or "—")
                intv = esc(a.get("interval") or "—")
                price = a.get("price_at_alert") or a.get("price_close")
                action_call = esc(action.get("action_call") or "—")
                t1 = ft(a.get("time_utc") or "")
                t2 = ft(a.get("received_at") or "")
                ts_html = ""
                if t1 != "—": ts_html += f'<span>Alert: {t1}</span>'
                if t2 != "—": ts_html += f'<span>Recv: {t2}</span>'

                # FM strip
                legs_html = ""
                if action.get("is_ratio"):
                    legs = [l for l in [action.get("ratio_long"), action.get("ratio_short")] if l]
                    if legs: legs_html = f'<div style="font-size:10px;color:#64748b;width:100%;padding-top:2px;">{"  ·  ".join(esc(l) for l in legs)}</div>'

                # Analysis summary
                analysis = action.get("chart_analysis")
                analysis_count = 0
                if analysis:
                    valid = [b for b in analysis if b and b != "—"]
                    analysis_count = len(valid)
                mode_icon = "🔭" if action.get("has_chart") else "📝"

                return f"""<div class="ac {bcls}{urgency_cls}">
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
  <div class="fm-strip-inline">
    <span class="fm-action-label">{action_call}</span>
    {prio_chip(prio)}
    {legs_html}
  </div>
  {f'<div style="padding:4px 16px;font-size:10px;color:#64748b;background:#f8fafc;border-top:1px solid #f1f5f9;">{mode_icon} {analysis_count} insights</div>' if analysis_count else ''}
</div>"""

            # Render grid
            app_cols = st.columns(3)
            for i, a in enumerate(fl[:100]):
                with app_cols[i % 3]:
                    st.markdown(_approved_card_html(a), unsafe_allow_html=True)
                    if st.button("Details", key=f"apdet_{a['id']}", use_container_width=True):
                        st.session_state.approved_detail_id = a["id"]
                    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)

            # Detail panel (shown below grid when Details is clicked)
            detail_id = st.session_state.get("approved_detail_id")
            if detail_id:
                detail_a = next((a for a in fl if a["id"] == detail_id), None)
                if detail_a:
                    action = detail_a.get("action") or {}
                    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
                    prio = action.get("priority", "")
                    prio_color = {"IMMEDIATELY": "#ea580c", "WITHIN_A_WEEK": "#4f46e5", "WITHIN_A_MONTH": "#7c3aed"}.get(prio, "#059669")
                    st.markdown(f"""<div style="background:#f8fafc;border:1px solid #e5e7eb;border-top:3px solid {prio_color};border-radius:10px;padding:14px 20px;margin-bottom:8px;">
<div style="font-size:14px;font-weight:700;color:#0f172a;">{esc(detail_a.get("ticker",""))} — Approved Details</div>
<div style="font-size:11px;color:#64748b;">FM decision: <strong>{esc(action.get("action_call","—"))}</strong> · {prio_chip(prio)}</div>
</div>""", unsafe_allow_html=True)

                    # Chart and insights side by side — equal space
                    has_chart_img = action.get("has_chart")

                    if has_chart_img:
                        detail_cols = st.columns([1, 1])
                        with detail_cols[0]:
                            try:
                                r = requests.get(f"{API_URL}/api/alerts/{detail_id}/chart", timeout=8)
                                b64_data = r.json().get("chart_image_b64", "")
                                if b64_data:
                                    if not b64_data.startswith("data:"):
                                        b64_data = "data:image/png;base64," + b64_data
                                    st.markdown('<div class="detail-title">Chart</div>', unsafe_allow_html=True)
                                    st.image(b64_data, use_container_width=True)
                            except Exception:
                                pass
                        with detail_cols[1]:
                            # Insights
                            analysis = action.get("chart_analysis")
                            if analysis:
                                valid = [b for b in analysis if b and b != "—"]
                                if valid:
                                    insights_html = f'<div class="detail-title">Insights · {len(valid)} points</div><div class="detail-insights">'
                                    for bi, bv in enumerate(valid):
                                        insights_html += f'<div class="di-item"><span class="di-num">{bi+1}.</span><span>{esc(bv)}</span></div>'
                                    insights_html += '</div>'
                                    st.markdown(insights_html, unsafe_allow_html=True)
                            # FM notes
                            fm_n = action.get("fm_notes")
                            if fm_n:
                                st.markdown(f'<div style="margin-top:12px;"><div class="detail-title">FM Commentary</div><div class="detail-fm-notes">{esc(fm_n)}</div></div>', unsafe_allow_html=True)
                    else:
                        # No chart — full width insights
                        analysis = action.get("chart_analysis")
                        if analysis:
                            valid = [b for b in analysis if b and b != "—"]
                            if valid:
                                insights_html = f'<div class="detail-title">Insights · {len(valid)} points</div><div class="detail-insights">'
                                for bi, bv in enumerate(valid):
                                    insights_html += f'<div class="di-item"><span class="di-num">{bi+1}.</span><span>{esc(bv)}</span></div>'
                                insights_html += '</div>'
                                st.markdown(insights_html, unsafe_allow_html=True)
                            else:
                                st.markdown('<div style="font-size:12px;color:#94a3b8;">No insights available yet</div>', unsafe_allow_html=True)
                        else:
                            st.markdown('<div style="font-size:12px;color:#94a3b8;">No insights available yet</div>', unsafe_allow_html=True)
                        fm_n = action.get("fm_notes")
                        if fm_n:
                            st.markdown(f'<div style="margin-top:12px;"><div class="detail-title">FM Commentary</div><div class="detail-fm-notes">{esc(fm_n)}</div></div>', unsafe_allow_html=True)

                    if st.button("Close Details", key="close_app_detail"):
                        st.session_state.approved_detail_id = None
                        st.rerun()

    # ══════════════════════════════
    # MARKET PULSE — Full Index Table
    # ══════════════════════════════
    elif t == "pulse":

        c1, c2, c3, c4 = st.columns([2, 1.5, 1.5, 2])
        with c1:
            base_idx = st.selectbox("Base Index", [
                "NIFTY", "SENSEX", "BANKNIFTY", "NIFTYIT", "NIFTYPHARMA",
                "NIFTYFMCG", "NIFTYAUTO", "NIFTYMETAL",
            ], key="pulse_base")
        with c2:
            period_filter = st.selectbox("Return Period", ["1D", "1W", "1M", "3M", "6M", "12M"], key="pulse_period")
        with c3:
            sector_options = ["All Indices", "Top 25"] + SECTOR_ORDER
            sector_filter = st.selectbox("Sector", sector_options, key="pulse_sector")
        with c4:
            st.markdown('<div style="height:25px;"></div>', unsafe_allow_html=True)
            if st.button("Refresh", use_container_width=True, type="primary"):
                st.rerun()

        st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

        # Fetch live index data from NSE via nsetools
        try:
            idx_resp = requests.get(f"{API_URL}/api/indices/live", params={"base": base_idx}, timeout=30).json()
        except Exception:
            idx_resp = {"indices": [], "success": False}

        idx_list = idx_resp.get("indices", [])

        if idx_list:
            api_ts = idx_resp.get("timestamp", "")
            try:
                ts_dt = datetime.fromisoformat(api_ts)
                ts_str = ts_dt.strftime("%d-%b-%y %I:%M %p")
            except Exception:
                ts_str = datetime.now().strftime("%d-%b-%y %I:%M %p")

            # ── Sort and filter by sector ──
            def _sort_key(item):
                name = item.get("nse_name") or item.get("index_name", "")
                is_top = name in _TOP_25_SET
                sector = _get_sector(name)
                try:
                    sect_idx = SECTOR_ORDER.index(sector)
                except ValueError:
                    sect_idx = len(SECTOR_ORDER)
                if is_top:
                    try:
                        top_idx = TOP_25_INDICES.index(name)
                    except ValueError:
                        top_idx = 999
                    return (0, top_idx, name)
                return (1, sect_idx, name)

            # Apply sector filter
            if sector_filter == "Top 25":
                filtered = [i for i in idx_list if (i.get("nse_name") or i.get("index_name", "")) in _TOP_25_SET]
            elif sector_filter != "All Indices":
                filtered = [i for i in idx_list if _get_sector(i.get("nse_name") or i.get("index_name", "")) == sector_filter]
            else:
                filtered = list(idx_list)

            filtered.sort(key=_sort_key)

            st.caption(f"Live NSE data · {len(filtered)} of {len(idx_list)} indices · Base: {base_idx} · Updated: {ts_str}")

            def _signal_badge(sig):
                if not sig:
                    return ""
                if sig == "BASE":
                    return '<span class="signal-base">BASE</span>'
                if "OW" in sig:
                    return '<span class="signal-ow">' + esc(sig) + '</span>'
                if "UW" in sig:
                    return '<span class="signal-uw">' + esc(sig) + '</span>'
                return '<span class="signal-n">' + esc(sig) + '</span>'

            def _ratio_rec(ratio, sig):
                if sig == "BASE":
                    return '<span style="color:#4f46e5;font-weight:500;">Benchmark</span>'
                if ratio is None:
                    return "—"
                if ratio > 1.05:
                    return '<span style="color:#059669;">Strong relative strength</span>'
                elif ratio > 1.0:
                    return '<span style="color:#059669;">Outperforming base</span>'
                elif ratio < 0.95:
                    return '<span style="color:#dc2626;">Weak relative strength</span>'
                elif ratio < 1.0:
                    return '<span style="color:#dc2626;">Underperforming base</span>'
                return '<span style="color:#64748b;">In-line with base</span>'

            def _period_return(item, period_key):
                """Get index's own period return from API data."""
                index_returns = item.get("index_returns", {})
                return index_returns.get(period_key.lower())

            rows_html = ""
            current_sector = None
            for idx in filtered:
                close = idx.get("last")
                if close is None:
                    continue
                idx_name_raw = idx.get("nse_name") or idx.get("index_name", "")
                sector = _get_sector(idx_name_raw)
                is_top = idx_name_raw in _TOP_25_SET

                # Sector header row
                if sector_filter == "All Indices":
                    if is_top and current_sector != "__top25__":
                        current_sector = "__top25__"
                        rows_html += '<tr class="sector-hdr"><td colspan="7">Top 25 Indices</td></tr>'
                    elif not is_top and current_sector != sector:
                        current_sector = sector
                        rows_html += f'<tr class="sector-hdr"><td colspan="7">{esc(sector)}</td></tr>'

                close_str = "{:,.2f}".format(close) if close > 100 else "{:.4f}".format(close)
                ratio = idx.get("ratio")
                ratio_str = "{:.2f}".format(ratio) if ratio is not None else "—"
                signal = idx.get("signal", "NEUTRAL")
                chg = idx.get("percentChange")
                chg_str = "{:+.2f}%".format(chg) if chg is not None else "—"
                chg_cls = "g" if (chg or 0) >= 0 else "r"

                pret = _period_return(idx, period_filter)
                pret_str = "{:+.2f}%".format(pret) if pret is not None else "—"
                pret_cls = "g" if (pret or 0) >= 0 else "r"

                idx_name = esc(idx_name_raw)

                rows_html += f"""<tr>
                    <td style="font-weight:600;">{idx_name}</td>
                    <td class="mono">{close_str}</td>
                    <td class="mono">{ratio_str}</td>
                    <td>{_signal_badge(signal)}</td>
                    <td class="mono {chg_cls}">{chg_str}</td>
                    <td class="mono {pret_cls}">{pret_str}</td>
                    <td style="font-size:11px;max-width:180px;white-space:normal;">{_ratio_rec(ratio, signal)}</td>
                </tr>"""

            st.markdown(f"""
<table class="idx-table">
    <thead><tr>
        <th>Index Name</th>
        <th>Latest Price</th>
        <th>Ratio to {esc(base_idx)}</th>
        <th>Signal</th>
        <th>Daily Chg%</th>
        <th>{esc(period_filter)} Return</th>
        <th>Recommendation</th>
    </tr></thead>
    <tbody>{rows_html}</tbody>
</table>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty"><div class="empty-icon">📊</div><h3>Loading index data</h3><p>Fetching live prices from NSE...</p></div>', unsafe_allow_html=True)

        # ── Signal heatmap ──
        st.markdown('<div style="font-size:12px;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;margin:20px 0 8px;">Alert Signal Distribution</div>', unsafe_allow_html=True)
        tickers_seen = {}
        for a in alerts:
            tk = a.get("ticker", "—")
            sig = a.get("signal_direction", "NEUTRAL")
            if tk not in tickers_seen:
                tickers_seen[tk] = {"BULLISH": 0, "BEARISH": 0, "NEUTRAL": 0, "total": 0, "latest": a}
            tickers_seen[tk][sig] = tickers_seen[tk].get(sig, 0) + 1
            tickers_seen[tk]["total"] += 1

        sorted_tickers = sorted(tickers_seen.items(), key=lambda x: x[1]["total"], reverse=True)

        heat_html = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px;">'
        for tk, info in sorted_tickers[:20]:
            bull_pct = (info["BULLISH"] / info["total"] * 100) if info["total"] else 0
            bear_pct = (info["BEARISH"] / info["total"] * 100) if info["total"] else 0
            bg = "#ecfdf5" if bull_pct > bear_pct else ("#fef2f2" if bear_pct > bull_pct else "#f8fafc")
            border = "#10b981" if bull_pct > bear_pct else ("#ef4444" if bear_pct > bull_pct else "#e5e7eb")
            latest = info["latest"]
            latest_price = latest.get("price_at_alert") or latest.get("price_close")
            price_str = fp(latest_price) if latest_price else "—"
            heat_html += f"""<div style="background:{bg};border:1px solid {border};border-radius:8px;padding:10px 12px;">
                <div style="font-size:13px;font-weight:700;color:#0f172a;">{esc(tk)}</div>
                <div style="font-size:11px;color:#64748b;margin-top:2px;">{price_str}</div>
                <div style="display:flex;gap:8px;margin-top:6px;">
                    <span style="font-size:10px;color:#059669;font-weight:600;">▲ {info['BULLISH']}</span>
                    <span style="font-size:10px;color:#dc2626;font-weight:600;">▼ {info['BEARISH']}</span>
                    <span style="font-size:10px;color:#94a3b8;">{info['total']} total</span>
                </div>
            </div>"""
        heat_html += '</div>'
        st.markdown(heat_html, unsafe_allow_html=True)

    # ══════════════════════════════
    # ALERT PERFORMANCE — Card Grid
    # ══════════════════════════════
    elif t == "perf":

        if not approved:
            st.markdown('<div class="empty"><div class="empty-icon">📈</div><h3>No approved alerts</h3><p>Approve alerts in Trade Center to track performance</p></div>', unsafe_allow_html=True)
        else:
            try:
                perf_data = requests.get(f"{API_URL}/api/performance", timeout=30).json().get("performance", [])
            except Exception:
                perf_data = []

            if perf_data:
                # ── Summary stats ──
                returns = [p["return_pct"] for p in perf_data if p.get("return_pct") is not None]
                winners = [r for r in returns if r > 0]
                losers = [r for r in returns if r < 0]
                avg_return = sum(returns) / len(returns) if returns else 0
                hit_rate = (len(winners) / len(returns) * 100) if returns else 0
                best = max(returns) if returns else 0
                worst = min(returns) if returns else 0

                st.markdown(f"""<div class="stats-row" style="grid-template-columns: repeat(5, 1fr);">
                    <div class="stat"><div class="stat-lbl">Avg Return</div><div class="stat-val {'g' if avg_return >= 0 else 'r'}" style="font-size:24px;">{avg_return:+.2f}%</div><div class="stat-sub">Across {len(returns)} trades</div></div>
                    <div class="stat"><div class="stat-lbl">Hit Rate</div><div class="stat-val" style="font-size:24px;">{hit_rate:.0f}%</div><div class="stat-sub">{len(winners)}W / {len(losers)}L</div></div>
                    <div class="stat"><div class="stat-lbl">Best Trade</div><div class="stat-val g" style="font-size:24px;">{best:+.2f}%</div><div class="stat-sub">Top performer</div></div>
                    <div class="stat"><div class="stat-lbl">Worst Trade</div><div class="stat-val r" style="font-size:24px;">{worst:+.2f}%</div><div class="stat-sub">Bottom performer</div></div>
                    <div class="stat"><div class="stat-lbl">Active Trades</div><div class="stat-val" style="font-size:24px;">{len(perf_data)}</div><div class="stat-sub">Being tracked</div></div>
                </div>""", unsafe_allow_html=True)

                st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
                st.caption(f"{len(perf_data)} active trades")

                # ── Performance card grid (3 cols) — no detail panel ──
                perf_html = ""
                for idx_p, p in enumerate(perf_data):
                    sig = (p.get("signal_direction") or "").upper()
                    sig_badge = '<span class="chip chip-bull">▲ Bull</span>' if sig == "BULLISH" else ('<span class="chip chip-bear">▼ Bear</span>' if sig == "BEARISH" else '')
                    entry = p.get("entry_price")
                    curr = p.get("current_price")
                    ret_pct = p.get("return_pct")
                    days = p.get("days_since")
                    action_d = p.get("action") or {}
                    action_call = action_d.get("action_call", "—")
                    prio = action_d.get("priority", "")

                    entry_str = fp(entry) if entry else "—"
                    curr_str = fp(curr) if curr else "—"
                    ret_str = "{:+.2f}%".format(ret_pct) if ret_pct is not None else "—"
                    ret_cls = "pc-g" if (ret_pct or 0) >= 0 else "pc-r"
                    days_str = "{}d".format(days) if days is not None else "—"

                    alert_dt = p.get("received_at") or p.get("time_utc") or ""
                    try:
                        dt_obj = datetime.fromisoformat(alert_dt.replace("Z", ""))
                        alert_date_str = dt_obj.strftime("%d %b %y")
                    except Exception:
                        alert_date_str = "—"

                    prio_badge = ""
                    if prio == "IMMEDIATELY": prio_badge = '<span class="chip chip-imm" style="margin-left:4px;">Now</span>'
                    elif prio == "WITHIN_A_WEEK": prio_badge = '<span class="chip chip-wk" style="margin-left:4px;">Week</span>'
                    elif prio == "WITHIN_A_MONTH": prio_badge = '<span class="chip chip-mo" style="margin-left:4px;">Month</span>'

                    ticker_label = esc(p.get("ticker", "—"))

                    perf_html += f"""<div class="perf-card">
  <div class="pc-top">
    <div>
      <div class="pc-ticker">{ticker_label} {sig_badge}</div>
      <div class="pc-date">{alert_date_str}</div>
    </div>
    <div style="text-align:right;">
      <div style="font-size:12px;font-weight:700;color:#0f172a;">{esc(action_call)}</div>
      {prio_badge}
    </div>
  </div>
  <div class="pc-row">
    <div class="pc-cell"><div class="pc-lbl">Entry</div><div class="pc-val">{entry_str}</div></div>
    <div class="pc-cell"><div class="pc-lbl">Current</div><div class="pc-val" style="color:#2563eb;">{curr_str}</div></div>
    <div class="pc-cell"><div class="pc-lbl">Return</div><div class="pc-val {ret_cls}">{ret_str}</div></div>
    <div class="pc-cell"><div class="pc-lbl">Days</div><div class="pc-val">{days_str}</div></div>
  </div>
</div>"""
                st.markdown(f'<div class="perf-grid">{perf_html}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="empty"><div class="empty-icon">⏳</div><h3>Loading performance data</h3><p>Fetching live prices…</p></div>', unsafe_allow_html=True)



if __name__ == "__main__":
    main()
