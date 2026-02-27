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
FROM python:3.11-slim

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY server.py models.py price_service.py ./

# Copy built frontend from Stage 1
COPY --from=frontend /app/web/out ./web/out

# Railway sets PORT dynamically
ENV PORT=8000
EXPOSE 8000

# Use shell form so $PORT is expanded at runtime
CMD uvicorn server:app --host 0.0.0.0 --port $PORT
