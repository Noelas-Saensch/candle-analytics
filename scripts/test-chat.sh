#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# test-chat.sh — Entry point for chat smoke / e2e tests
# Usage:
#   ./scripts/test-chat.sh smoke [--port 8001]
#   ./scripts/test-chat.sh chat  [--port 8001] [--url ...]
#   ./scripts/test-chat.sh all   [--port 8001]
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODE="${1:-all}"
shift 2>/dev/null || true

echo "==> test-chat.sh: mode=${MODE}"

case "${MODE}" in
  smoke|strategy|all)
    python3 "${SCRIPT_DIR}/chat_e2e.py" "${MODE}" "$@"
    ;;
  *)
    echo "Usage: $0 {smoke|strategy|all} [--port PORT]"
    exit 1
    ;;
esac
