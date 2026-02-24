# Jhaveri Intelligence Platform — FIE Phase 2

## What Changed (Complete Changelog)

### A. Fixed: None/Zero/Div issues on cards
- **Root cause**: The webhook parser was storing `None` for fields not present in the payload, and the dashboard was rendering them as-is.
- **Fix**: All display functions now have `fmt_price()` and `fmt_time()` formatters that convert `None`/`0` to `"—"` gracefully.
- **Card titles** now show the **alert_name** (not ticker + strategy placeholder).
- Removed childish emoji icons — replaced with clean typographic pills and structured layout.

### B. Fixed: NLP Commentary not showing
- **Root cause**: The `signal_summary` field was being populated by the webhook parser's basic `_generate_summary()`, but the AI-generated summary from Gemini was only called with the `alert_message` string. If `GEMINI_API_KEY` wasn't set, it fell back to raw message text.
- **Fix**: The server now properly passes all data to `generate_technical_summary()` and stores the result. The dashboard consistently shows the AI analysis in a styled blue-bordered box on every card.

### C. Fixed: Inconsistent green text on some cards
- **Root cause**: The historical executions section was rendering `fm_remarks` inline with green color only when remarks existed, creating visual inconsistency.
- **Fix**: All cards now use standardized pill components and consistent formatting. Remarks display uniformly with a subtle left-border quote style.

### D. Fixed: Poor formatting of values
- All prices now formatted with `₹` symbol, commas, and 2 decimal places via `fmt_price()`.
- Percentages use `+/-` prefix and color-coded (green for gains, red for losses).
- Timestamps formatted to `DD Mon YYYY, HH:MM` via `fmt_time()`.
- Bold values where appropriate, proper spacing throughout.

### E. Trade Desk (Action Center) overhaul
- Removed OHLC fields (no intraday trading — only the trigger price is shown).
- Compact card layout with clear data hierarchy.
- **3-state decision buttons**: ✓ Approve (green), ✗ Deny (red), ◷ Review Later (blue).
- FM rationale text area with proper placeholder.
- Voice note: guidance text added (use device recorder + paste transcript — native browser audio recording is unreliable in Streamlit).
- Conviction slider: LOW / MEDIUM / HIGH.

### F. Stop Loss & Target — Optional fields
- Added `target_price` and `stop_loss` as optional number inputs on Trade Desk.
- If FM inputs values > 0, they're saved to the database and included in recommendations.
- Displayed in the master alert table.

### G. Chart Image Attachment
- File uploader on Trade Desk accepts PNG/JPG.
- Chart is base64-encoded and stored in `alert_actions.chart_image_b64`.
- The `chart_image_b64` column is added via migration on startup.

### H. New Page: Alert Database (Master View)
- Full tabular view of ALL historical alerts with:
  - Alert ID, Date, Name, Ticker, Direction, Price, Interval, Sector
  - Status (color-coded), FM Call, Conviction, Target, Stop Loss, Return %
- **Filters**: Status dropdown, Ticker search, row count selector.
- **Delete functionality**: Enter Alert ID → confirm → delete (cascades to actions & performance).
- Powered by new `/api/master` endpoint with pagination support.

### I. Performance Tracking improvements
- Entry price = price at alert trigger (confirmed).
- Price service now has **comprehensive NSE/BSE ticker mapping** (26+ indices).
- BSE fallback: if NSE lookup fails, automatically tries BSE suffix.
- Tracks: high_since, low_since, max_drawdown, return_absolute.
- Portfolio Analytics page shows: Active Positions, Avg Return, Win Rate metrics.
- Performance table includes: Entry, Current, Return %, High Since, Drawdown, Approved Date.

### J. Dashboard Design Overhaul
- **Font**: DM Sans (modern, not generic) + JetBrains Mono for code.
- **Sidebar**: Dark gradient navy (#0C1222 → #131B2E), minimal navigation labels.
- **Cards**: Clean white with subtle shadows, hover effects, structured sections.
- **Pills**: Rounded, muted color palette (not loud primary colors).
- **Layout**: Max-width 1200px, proper spacing, dividers.
- **Empty states**: Centered with icon + helper text.
- Removed all childish emoji usage from navigation and headers.
- Typography: Uppercase labels, proper letter-spacing, weight hierarchy.

### K. Approve/Deny/Review Later actions
- 3 distinct statuses with visual identity:
  - **Approve**: Green pill with checkmark
  - **Deny**: Red pill with cross
  - **Review Later**: Blue pill with clock icon
- `AlertStatus` enum updated with `REVIEW_LATER`.
- Review Later alerts appear in Trade Desk pending queue.

### L. Master Alert Database (rich view)
- Color-coded status column using pandas Styler.
- Filterable by status and ticker.
- Shows FM action details, conviction, target/SL, return %.
- Pagination support via API (`/api/master` with offset/limit).

---

## File Changes Summary

| File | Changes |
|------|---------|
| `models.py` | Added `REVIEW_LATER` status, `chart_image_b64` column, `_migrate_columns()`, more instruments |
| `server.py` | Added `/api/master`, `DELETE /api/alerts/{id}`, richer API responses, REVIEW_LATER support, chart upload, target/SL fields |
| `dashboard.py` | Complete rewrite — premium CSS, 5 pages, all formatting fixes, 3-state actions, master DB view |
| `webhook_parser.py` | No logic changes, cleaned up |
| `ai_engine.py` | No changes |
| `price_service.py` | Added 26+ NSE/BSE ticker mappings, BSE fallback, high/low/drawdown tracking |
| `requirements.txt` | Added `psycopg2-binary` |
| `start.sh` | Fixed paths for flat directory structure |

---

## Deployment on Railway

1. Push all files to your GitHub repo
2. Railway will auto-detect and rebuild
3. Ensure environment variables are set:
   - `DATABASE_URL` (Railway Postgres)
   - `GEMINI_API_KEY` (for AI summaries)
   - `FIE_API_URL` (your Railway backend URL, e.g. `https://fie2-production.up.railway.app`)

## Future Considerations (Phase 3)
- Pinecone integration for dynamic technical data retrieval
- Real-time WebSocket price feeds
- Multi-user authentication with role-based access
- PDF report generation for client distribution
- Historical backtesting engine
