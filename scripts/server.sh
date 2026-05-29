#!/usr/bin/env bash
set -euo pipefail

PORT="${2:-8001}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

kill_port() {
  local p=$1
  fuser -k "${p}/tcp" 2>/dev/null && echo "Killed port ${p} (fuser)" && return 0
  local pid
  pid=$(lsof -ti:"${p}" 2>/dev/null) && kill "${pid}" 2>/dev/null && echo "Killed PID ${pid} on port ${p}" && return 0
  echo "Nothing on port ${p} or cannot kill"
  return 1
}

case "${1:-restart}" in
  kill)
    kill_port "${PORT}" || true
    ;;
    start)
    kill_port "${PORT}" || true
    cd "${PROJECT_DIR}"
    nohup .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port "${PORT}" > "/tmp/candle_server_${PORT}.log" 2>&1 &
    pid=$!
    echo "Started PID ${pid} on port ${PORT}"
    sleep 3
    for i in 1 2 3; do
      curl -sf "http://localhost:${PORT}/api/health" >/dev/null && echo "Health OK" && exit 0
      sleep 2
    done
    echo "Health check FAILED after 3 attempts"
    exit 1
    ;;
  restart)
    kill_port "${PORT}" || true
    sleep 1
    exec "$0" start "${PORT}"
    ;;
  health)
    curl -sf "http://localhost:${PORT}/api/health" >/dev/null && echo "OK" && exit 0
    echo "DOWN" && exit 1
    ;;
  list)
    echo "--- Servers on port 8000-8002 ---"
    for p in 8000 8001 8002; do
      pid=$(lsof -ti:"${p}" 2>/dev/null || echo "")
      if [ -n "${pid}" ]; then
        owner=$(ps -o user= -p "${pid}" 2>/dev/null || echo "?")
        echo "Port ${p}: PID ${pid} (${owner})"
      else
        echo "Port ${p}: free"
      fi
    done
    ;;
  *)
    echo "Usage: $0 {kill|start|restart|health|list} [PORT]"
    exit 1
    ;;
esac
