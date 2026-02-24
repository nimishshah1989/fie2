#!/bin/bash
echo "Starting Jhaveri Intelligence Platform"
echo "======================================="

# Initialize DB
python -c "from models import init_db; init_db()"

# Railway provides $PORT - FastAPI serves everything on this single port
# FastAPI handles: /webhook/*, /api/* directly  
# FastAPI proxies: /* to internal Streamlit on 8501
PORT=${PORT:-8000}
echo "Unified server on port $PORT"

exec uvicorn server:app --host 0.0.0.0 --port $PORT --workers 1
