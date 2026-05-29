---
name: server-lifecycle
description: >
  Manages FastAPI server lifecycle — detect stale servers, kill by port,
  restart with health verification, log outcomes. Prevents "Disconnected"
  errors from zombie processes.
---

# Server Lifecycle

## Problem

- Old server processes linger on port 8000 (especially root-owned)
- New servers fail silently because port is taken
- WebSocket shows "Disconnected" — user sees stale server
- `pkill` / `screen -X quit` often fail (root process, different session)

## Tools

### `scripts/server.sh`

Centralised script for server management:

```bash
# Kill any process on PORT
scripts/server.sh kill [PORT]

# Start fresh server on PORT
scripts/server.sh start [PORT]

# Restart (kill + start + health check)
scripts/server.sh restart [PORT]

# Check health
scripts/server.sh health [PORT]

# List all servers with PID, port, owner
scripts/server.sh list
```

### Force-kill by port (last resort)

```bash
# Try multiple methods in order
fuser -k PORT/tcp 2>/dev/null            # fastest
kill $(lsof -ti:PORT) 2>/dev/null         # lsof method
sudo kill -9 $(fuser PORT/tcp 2>/dev/null)  # root method
```

## Lifecycle rules

1. **ALWAYS check port availability before starting** — `fuser PORT/tcp` returns 0 if in use
2. **ALWAYS verify health after start** — curl /api/health with 5s timeout, retry 3x
3. **ALWAYS log the outcome** — PID, port, health status
4. **Use port 8001** — port 8000 may have a root-owned stale server that can't be killed
5. **Log server output** — redirect to `/tmp/candle_server_PID.log`

## Quick reference

| Situation | Command |
|-----------|---------|
| Server shows "Disconnected" in UI | `scripts/server.sh restart 8001` |
| Port 8000 is taken by root | `scripts/server.sh kill 8000` (try all methods) |
| Need fresh start | `scripts/server.sh restart 8001` |
| Verify server is alive | `scripts/server.sh health 8001` |

## Starter script

Create `scripts/server.sh`:

```bash
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
    kill_port "${PORT}"
    ;;
  start)
    kill_port "${PORT}"
    cd "${PROJECT_DIR}"
    nohup .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port "${PORT}" > "/tmp/candle_server_${PORT}.log" 2>&1 &
    local pid=$!
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
    kill_port "${PORT}"
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
```

## Triggers

Run this skill when:
- The UI shows "Disconnected" or "connecting..."
- A new server needs to start after code changes
- The health check endpoint (`/api/health`) fails
- Any error mentions "port already in use" or "Address already in use"
