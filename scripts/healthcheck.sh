#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PYTHON="${PROJECT_DIR}/.venv/bin/python"
ALL_OK=true

echo "=== Candle Analytics Healthcheck ==="
echo "Date: $(date)"
echo ""

# 1. Port 8001 health
echo -n "🔍 API server (port 8001)... "
if curl -sf http://localhost:8001/api/health > /dev/null 2>&1; then
  echo "✅ OK"
else
  echo "❌ DOWN"
  ALL_OK=false
fi

# 2. Agent process
echo -n "🔍 Strategy Lab agent... "
if screen -ls 2>/dev/null | grep -q "agent"; then
  AGENT_COUNT=$(ps aux | grep 'api/agent.py' | grep -v grep | wc -l)
  if [ "$AGENT_COUNT" -ge 1 ]; then
    echo "✅ running (${AGENT_COUNT} proc)"
  else
    echo "❌ screen exists but no process"
    ALL_OK=false
  fi
else
  echo "❌ screen not found"
  ALL_OK=false
fi

# 3. Vibe agent
echo -n "🔍 Vibe Lab agent... "
if screen -ls 2>/dev/null | grep -q "vibe-agent"; then
  VIBE_COUNT=$(ps aux | grep 'api/vibe_agent.py' | grep -v grep | wc -l)
  if [ "$VIBE_COUNT" -ge 1 ]; then
    echo "✅ running (${VIBE_COUNT} proc)"
  else
    echo "❌ screen exists but no process"
    ALL_OK=false
  fi
else
  echo "❌ screen not found"
  ALL_OK=false
fi

# 4. Dashboard page
echo -n "🔍 /dashboard page... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/dashboard 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
  echo "✅ HTTP ${HTTP_CODE}"
else
  echo "❌ HTTP ${HTTP_CODE}"
  ALL_OK=false
fi

# 5. Strategy Lab page
echo -n "🔍 /strategy-lab page... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/strategy-lab 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
  echo "✅ HTTP ${HTTP_CODE}"
else
  echo "❌ HTTP ${HTTP_CODE}"
  ALL_OK=false
fi

# 6. Vibe Lab page
echo -n "🔍 /vibe-lab page... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/vibe-lab 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
  echo "✅ HTTP ${HTTP_CODE}"
else
  echo "❌ HTTP ${HTTP_CODE}"
  ALL_OK=false
fi

# 7. Python imports
echo -n "🔍 Python imports... "
if "${VENV_PYTHON}" -c "from api.main import app; print('OK')" 2>/dev/null; then
  echo -n ""
else
  echo "❌ imports FAIL"
  ALL_OK=false
fi

echo ""
echo "=== Result ==="
if [ "$ALL_OK" = true ]; then
  echo "✅ All services healthy"
  exit 0
else
  echo "❌ Some services down"
  exit 1
fi
