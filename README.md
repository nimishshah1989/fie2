# JHAVERI Financial Intelligence Engine (FIE) — Phase 2 MVP

## Architecture
- **Backend**: FastAPI (webhook receiver, REST API, Streamlit reverse proxy)
- **Frontend**: Streamlit (proxied through FastAPI for single-port deployment)
- **Database**: PostgreSQL (Railway) / SQLite (local dev)
- **Price Data**: Yahoo Finance (yfinance) with NSE/BSE index mapping
- **Deployment**: Railway (single service, single port)

## TradingView Alert Templates

### For Strategy Alerts (Pine Script)
Use `{{strategy.order.comment}}` to auto-pull the alert name:
```json
{
  "ticker": "{{ticker}}",
  "exchange": "{{exchange}}",
  "interval": "{{interval}}",
  "open": "{{open}}", "high": "{{high}}", "low": "{{low}}",
  "close": "{{close}}", "volume": "{{volume}}",
  "time": "{{time}}", "timenow": "{{timenow}}",
  "alert_name": "{{strategy.order.comment}}",
  "signal": "{{strategy.order.action}}",
  "message": "{{strategy.order.comment}} on {{ticker}}"
}
```

### For Indicator Alerts
```json
{
  "ticker": "{{ticker}}",
  "exchange": "{{exchange}}",
  "interval": "{{interval}}",
  "open": "{{open}}", "high": "{{high}}", "low": "{{low}}",
  "close": "{{close}}", "volume": "{{volume}}",
  "time": "{{time}}", "timenow": "{{timenow}}",
  "alert_name": "Your Alert Name Here",
  "signal": "BULLISH",
  "indicators": {"rsi": "{{plot_0}}", "macd": "{{plot_1}}"},
  "message": "Your custom context"
}
```

## Environment Variables
- `DATABASE_URL` — PostgreSQL connection string
- `PORT` — Server port (default: 8000)
- `GEMINI_API_KEY` — Optional, for AI summaries (Phase 2)
