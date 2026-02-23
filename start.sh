#!/bin/bash
# FIE Phase 1 — Start both backend and frontend

echo "⚡ Starting FIE Phase 1 — Alert Intelligence Dashboard"
echo "======================================================"

# Start backend
echo "🔧 Starting FastAPI backend on port 8000..."
cd backend
python -c "from models import init_db; init_db()"
uvicorn server:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

# Wait for backend to be ready
echo "   Waiting for backend..."
sleep 3

# Start frontend
echo "🖥️  Starting Streamlit dashboard on port 8501..."
cd ../frontend
streamlit run dashboard.py --server.port 8501 --server.address 0.0.0.0 --server.headless true &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

echo ""
echo "======================================================"
echo "✅ FIE Phase 1 is running!"
echo ""
echo "   📊 Dashboard:  http://localhost:8501"
echo "   🔌 API:        http://localhost:8000"
echo "   📡 Webhook:    http://localhost:8000/webhook/tradingview"
echo "   📋 API Docs:   http://localhost:8000/docs"
echo ""
echo "   Press Ctrl+C to stop all services"
echo "======================================================"

# Wait for processes
wait $BACKEND_PID $FRONTEND_PID
