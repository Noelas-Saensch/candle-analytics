#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# test-dashboard.sh — Entry point for dashboard E2E tests
# Usage:
#   ./scripts/test-dashboard.sh smoke [--port 8001]
#   ./scripts/test-dashboard.sh ui    [--port 8001] [--headless true]
#   ./scripts/test-dashboard.sh all   [--port 8001]
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODE="${1:-all}"
shift 2>/dev/null || true

echo "==> test-dashboard.sh: mode=${MODE}"

case "${MODE}" in
  smoke|ui|all)
    python3 "${SCRIPT_DIR}/dashboard_e2e.py" "${MODE}" "$@"
    ;;
  *)
    echo "Usage: $0 {smoke|ui|all} [--port PORT] [--headless true]"
    exit 1
    ;;
esac
