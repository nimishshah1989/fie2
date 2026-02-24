#!/bin/bash
echo "Starting Jhaveri Intelligence Platform"
echo "======================================="

# Initialize DB
python -c "from models import init_db; init_db()"

# Start backend
echo "Starting FastAPI backend on port 8000..."
uvicorn server:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

sleep 3

# Start frontend
echo "Starting Streamlit dashboard on port 8501..."
streamlit run dashboard.py --server.port 8501 --server.address 0.0.0.0 --server.headless true &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

echo ""
echo "======================================="
echo "Platform is running"
echo "  Dashboard:  http://localhost:8501"
echo "  API:        http://localhost:8000"
echo "  Webhook:    http://localhost:8000/webhook/tradingview"
echo "  API Docs:   http://localhost:8000/docs"
echo "======================================="

wait $BACKEND_PID $FRONTEND_PID
