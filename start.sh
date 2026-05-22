#!/bin/bash
# Launch candle-analytics backend server

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== candle-analytics ==="

cleanup() {
    echo ""
    echo "Shutting down..."
    kill $SERVER_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

echo "[1/1] Starting API server (port ${PORT:-8000})..."
cd "$PROJECT_DIR"
python3 -m uvicorn api.main:app --reload --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}" &
SERVER_PID=$!

echo "  API: http://localhost:${PORT:-8000}"
echo "  Docs: http://localhost:${PORT:-8000}/docs"
echo ""
echo "Press Ctrl+C to stop"

wait
