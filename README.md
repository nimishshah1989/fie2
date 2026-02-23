# ⚡ FIE Phase 1 — TradingView Alert Intelligence Dashboard

**Jhaveri Securities — Financial Intelligence Engine**

## Overview

Phase 1 of the FIE system: A real-time TradingView alert ingestion and fund manager decision dashboard. 

### Three Core Modules:

1. **🔌 Alert Ingestion Engine** — Webhook endpoint that receives TradingView alerts, captures all available data (price, indicators, signal, volume, etc.), and stores them in a structured database.

2. **📊 Live Alert Dashboard + Action Center** — Real-time display of incoming alerts with full context. Fund manager can approve/deny alerts and assign actionable calls (Buy, Sell, Hold, etc.) on both the numerator and denominator for relative alerts.

3. **📈 Performance Tracker** — Tracks approved alerts from date of approval. Shows 1D, 1W, 1M, 3M, 6M, 12M returns with win rate analysis and sector breakdown.

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the system
```bash
chmod +x start.sh
./start.sh
```

Or start individually:
```bash
# Terminal 1: Backend
cd backend
python -c "from models import init_db; init_db()"
uvicorn server:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend
cd frontend
streamlit run dashboard.py
```

### 3. Access
- **Dashboard:** http://localhost:8501
- **API Docs:** http://localhost:8000/docs
- **Webhook URL:** http://localhost:8000/webhook/tradingview

### 4. Load test data
Click **"📥 Load Test Alerts"** in the sidebar to generate sample alerts.

---

## TradingView Webhook Setup

### Step 1: Get your webhook URL
When deployed, your webhook URL will be:
```
https://your-domain.com/webhook/tradingview
```

### Step 2: Configure TradingView Alert
1. Open your chart in TradingView
2. Set up your alert condition
3. Enable **Webhook URL** and paste your endpoint
4. In the **Message** field, paste this JSON template:

#### For Single Index/Stock Alerts:
```json
{
    "ticker": "{{ticker}}",
    "exchange": "{{exchange}}",
    "interval": "{{interval}}",
    "open": "{{open}}",
    "high": "{{high}}",
    "low": "{{low}}",
    "close": "{{close}}",
    "volume": "{{volume}}",
    "time": "{{time}}",
    "timenow": "{{timenow}}",
    "alert_name": "YOUR_ALERT_NAME",
    "signal": "BULLISH",
    "indicators": {
        "rsi": "RSI_VALUE",
        "macd": "MACD_VALUE"
    },
    "message": "YOUR_DESCRIPTION"
}
```

#### For Relative Alerts (Index A vs Index B):
```json
{
    "ticker": "{{ticker}}",
    "exchange": "{{exchange}}",
    "interval": "{{interval}}",
    "close": "{{close}}",
    "timenow": "{{timenow}}",
    "alert_name": "IT_vs_Nifty_Ratio",
    "numerator": "NIFTYIT",
    "denominator": "NIFTY",
    "numerator_price": 34520.60,
    "denominator_price": 24210.85,
    "ratio": 1.4259,
    "signal": "BULLISH",
    "message": "IT outperforming broad market"
}
```

---

## Architecture

```
fie-phase1/
├── backend/
│   ├── server.py           # FastAPI server + webhook endpoint + REST API
│   ├── models.py           # SQLAlchemy database models
│   ├── webhook_parser.py   # TradingView payload parser
│   └── price_service.py    # yfinance price fetching + return computation
├── frontend/
│   └── dashboard.py        # Streamlit dashboard (Live Alerts, Action Center, Performance)
├── requirements.txt
├── start.sh
└── README.md
```

### Data Flow
```
TradingView Alert → Webhook POST → Parser → Database → Dashboard
                                                          ↓
                                            FM: Approve/Deny + Call
                                                          ↓
                                            Performance Tracking (yfinance)
```

---

## Action Types

When approving an alert, the Fund Manager assigns:

| Action | Meaning |
|--------|---------|
| BUY | Initiate new position |
| STRONG_BUY | High conviction buy |
| SELL | Exit position |
| STRONG_SELL | Urgent exit |
| HOLD | Maintain current position |
| ACCUMULATE | Add to existing position |
| REDUCE | Partially exit |
| EXIT | Full exit |
| OVERBOUGHT | Warning - potential reversal |
| OVERSOLD | Opportunity - potential bounce |
| WATCH | Monitor closely |
| SWITCH | Rotate allocation |

For **relative alerts**, the FM assigns separate calls for both the numerator and denominator.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/webhook/tradingview` | Receive TradingView alerts |
| GET | `/api/alerts` | List alerts with filters |
| GET | `/api/alerts/{id}` | Get alert details |
| POST | `/api/alerts/{id}/action` | FM takes action |
| GET | `/api/performance` | Performance tracking |
| POST | `/api/performance/refresh` | Refresh live prices |
| GET | `/api/stats` | Dashboard statistics |
| GET | `/api/sectors` | Available sectors |
| GET | `/api/price/{ticker}` | Live price lookup |
| POST | `/api/test-alert` | Generate test alerts |

---

## Deployment

### Streamlit Cloud (Frontend)
1. Push to GitHub
2. Connect to Streamlit Cloud
3. Set `FIE_API_URL` environment variable to your backend URL

### Backend (Railway / Render / VPS)
1. Deploy the `backend/` directory
2. Set `PORT` environment variable
3. Ensure the webhook URL is publicly accessible

### Cost: ~₹0-800/month
- Streamlit Cloud: Free
- Backend: Railway free tier or $5/month
- Database: SQLite (included)
- Price data: yfinance (free)

---

## Phase 2 Preview
This dashboard will connect to the FIE Recommendation Engine which translates FM actionables into actual mutual fund suggestions for investors.
