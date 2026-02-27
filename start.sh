#!/bin/bash
set -e

# Build Next.js frontend if Node.js is available and out/ doesn't exist yet
if [ -d "web" ] && [ -f "web/package.json" ] && command -v npm &> /dev/null && [ ! -d "web/out" ]; then
  echo "Building frontend..."
  cd web
  npm ci --production=false
  npx next build
  cd ..
  echo "Frontend built → web/out/"
fi

# Start FastAPI
uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}
