# JHAVERI Financial Intelligence Engine (FIE v3)

## Architecture
- **Backend**: FastAPI (Python 3.11) — webhook receiver, REST API, portfolio management
- **Frontend**: Next.js 16 (static export served by FastAPI)
- **Database**: PostgreSQL 16.6 (AWS RDS Mumbai)
- **Deployment**: Docker on AWS EC2 Mumbai, CI/CD via GitHub Actions
- **Price Data**: nsetools + Yahoo Finance (yfinance) with NSE/BSE mapping

## Quick Start (Local Dev)
```bash
# Backend
pip install -r requirements.server.txt
python3 server.py

# Frontend
cd web && pnpm install && pnpm dev
```

Or use Docker Compose:
```bash
docker compose up -d
```

## API Documentation
- Swagger UI: `/api/docs`
- ReDoc: `/api/redoc`
- Health check: `/health`

## Environment Variables
See `.env.example` for all required and optional variables.

## TradingView Webhook Templates

### Strategy Alerts (Pine Script)
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

### Indicator Alerts
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
  "message": "Your custom context"
}
```

## Deployment
See `docs/DEPLOYMENT.md` for full deployment guide and `docs/DISASTER_RECOVERY.md` for DR plan.
