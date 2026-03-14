# ============================================================================
# Jhaveri Intelligence Platform — Multi-stage Dockerfile
# Stage 1: Build Next.js static frontend
# Stage 2: Python runtime with FastAPI + static files
# ============================================================================

# ── Stage 1: Node.js build ──────────────────────────
FROM node:20-alpine AS frontend

RUN corepack enable && corepack prepare pnpm@9 --activate

WORKDIR /app/web
COPY web/package.json web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY web/ .
ENV NEXT_PUBLIC_API_URL=""
RUN pnpm run build

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
COPY server.py models.py price_service.py config.py ./
COPY routers/ ./routers/
COPY services/ ./services/
COPY middleware/ ./middleware/

# Copy built frontend from Stage 1
COPY --from=frontend /app/web/out ./web/out

EXPOSE 8000

# Use Python to read PORT — bypasses all shell expansion issues
CMD ["python", "-c", "import os,uvicorn;uvicorn.run('server:app',host='0.0.0.0',port=int(os.environ.get('PORT','8000')))"]
