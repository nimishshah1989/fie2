# ============================================================================
# Jhaveri Intelligence Platform — Multi-stage Dockerfile
# Stage 1: Build Next.js static frontend
# Stage 2: Python runtime with FastAPI + static files
# ============================================================================

# ── Stage 1: Node.js build ──────────────────────────
FROM node:20-alpine AS frontend

WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ .
RUN npx next build

# ── Stage 2: Python runtime ─────────────────────────
FROM python:3.11

WORKDIR /app

# System deps for psycopg2, pandas, lxml, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps (server-only, skip Streamlit)
COPY requirements.server.txt .
RUN pip install --no-cache-dir -r requirements.server.txt

# Copy backend source
COPY server.py models.py price_service.py ./

# Copy built frontend from Stage 1
COPY --from=frontend /app/web/out ./web/out

EXPOSE 8000

# Use Python to read PORT — bypasses all shell expansion issues
CMD ["python", "-c", "import os,uvicorn;uvicorn.run('server:app',host='0.0.0.0',port=int(os.environ.get('PORT','8000')))"]
