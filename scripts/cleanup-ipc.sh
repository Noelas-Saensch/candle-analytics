#!/usr/bin/env bash
# Clean stale IPC files older than 5 minutes
# Run via cron: */5 * * * * /path/to/scripts/cleanup-ipc.sh

IPC_FILES=(
  /tmp/strategy_chat_req_*.json
  /tmp/strategy_chat_res_*.json
  /tmp/vibe_chat_req_*.json
  /tmp/vibe_chat_res_*.json
  /tmp/vibe_opencode_*.md
)

for pattern in "${IPC_FILES[@]}"; do
  for f in $pattern; do
    [ -f "$f" ] || continue
    # Delete if older than 5 minutes (300 seconds)
    if [ $(($(date +%s) - $(stat -c %Y "$f"))) -gt 300 ]; then
      rm -f "$f"
      echo "Cleaned: $f"
    fi
  done
done
