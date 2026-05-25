#!/bin/bash
# Usage: scripts/cache-subagent.sh <topic> <tags> [file_path]
#
# Saves sub-agent output to .opencode/cache/subagent/YYYY-MM-DD_HHMMSS_<topic>.md
#
# Arguments:
#   topic     - Short descriptive name (used in filename and heading)
#   tags      - Comma-separated keywords for future search
#   file_path - Path to file containing agent output (reads from stdin if omitted)

set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 <topic> <tags> [file_path]" >&2
  echo "  If file_path is omitted, reads from stdin." >&2
  exit 1
fi

TOPIC="$1"
TAGS="$2"
INPUT_FILE="${3:-}"

CACHE_DIR=".opencode/cache/subagent"
mkdir -p "$CACHE_DIR"

NOW=$(date +"%Y-%m-%d %H:%M:%S")
TIMESTAMP=$(date +"%Y-%m-%d_%H%M%S")
TOPIC_SLUG=$(echo "$TOPIC" | tr '[:upper:]' '[:lower:]' | tr -s ' _' '-' | tr -cd 'a-z0-9-')
FILENAME="${TIMESTAMP}_${TOPIC_SLUG}.md"
OUTPUT_PATH="${CACHE_DIR}/${FILENAME}"

if [ -n "$INPUT_FILE" ]; then
  if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: file '$INPUT_FILE' not found" >&2
    exit 1
  fi
  FULL_RESULTS=$(cat "$INPUT_FILE")
elif [ ! -t 0 ]; then
  FULL_RESULTS=$(cat)
else
  echo "Error: no input provided (pipe content or supply file_path)" >&2
  exit 1
fi

{
  echo "# ${TOPIC} — ${NOW}"
  echo ""
  echo "## Summary"
  echo ""
  echo "## Full Results"
  echo "${FULL_RESULTS}"
  echo ""
  echo "## Tags"
  echo "${TAGS}"
} > "$OUTPUT_PATH"

echo "$OUTPUT_PATH"
