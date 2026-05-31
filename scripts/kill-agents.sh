#!/usr/bin/env bash
# kill-agents.sh — Kill ALL agent/vibe-agent processes & screen sessions.
#
# Why a dedicated script:
#   - `screen -S name -X quit` only kills the FIRST session with that name.
#     After many server restarts, duplicates pile up → memory leak.
#   - `pkill -f` HANGs because the pattern matches the pkill command itself in /proc.
#   - This script kills ALL matching Python processes by PID (via ps|grep|xargs),
#     then wipes dead screen sessions — leaving zero duplicates.
#
# Usage:
#   scripts/kill-agents.sh             # kill agents only
#   scripts/kill-agents.sh --all       # kill agents + uvicorn + clean IPC
#   scripts/kill-agents.sh --servers   # kill uvicorn servers only
#   scripts/kill-agents.sh --clean     # clean IPC files only
#
# This script is referenced by:
#   - RULES.md §2
#   - auto-reload-server/SKILL.md
#   - session-lifecycle/SKILL.md
#   - code-quality/SKILL.md
#   - server-lifecycle/SKILL.md
#   - autorestart.json
#   - api/agent.py, api/vibe_agent.py
#   - scripts/chat_e2e.py

# NO set -euo pipefail — grep/wc pipelines return non-zero on empty matches
# (e.g., grep -v SCREEN exits 1 when all lines filtered), which would abort
# the entire script under set -e with pipefail. Each command has || true instead.
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

kill_agents() {
  # Kill ALL agent.py and vibe_agent.py processes — handles any number of duplicates.
  # This kills BOTH the SCREEN wrapper (whose cmdline also contains api/agent.py)
  # AND the actual Python child process. Killing the SCREEN orphan-propagates
  # to the child, making screen -wipe clean up the rest.
  # [a]pi trick prevents grep self-match (pattern won't match its own literal [a]pi)
  ps aux | grep -E 'python.*[a]pi/agent\.py' | awk '{print $2}' | xargs -r kill 2>/dev/null || true
  ps aux | grep -E 'python.*[a]pi/vibe_agent\.py' | awk '{print $2}' | xargs -r kill 2>/dev/null || true
  sleep 1
  # Wipe dead screen entries
  screen -wipe 2>/dev/null || true
  echo "kill-agents: agent/vibe-agent processes killed"
}

kill_servers() {
  ps aux | grep -E '[u]vicorn' | awk '{print $2}' | xargs -r kill 2>/dev/null || true
  sleep 1
  # Kill by port as well (handles root-owned orphans)
  for p in 8000 8001 8002; do
    fuser -k "${p}/tcp" 2>/dev/null || true
  done
  screen -wipe 2>/dev/null || true
  echo "kill-agents: server processes killed"
}

clean_ipc() {
  rm -f /tmp/strategy_chat_req_*.json /tmp/strategy_chat_res_*.json
  rm -f /tmp/vibe_chat_req_*.json /tmp/vibe_chat_res_*.json
  rm -f /tmp/groq_busy.lock
  echo "kill-agents: IPC files cleaned"
}

check_counts() {
  local agent_count
  local vibe_count
  local screen_count
  # Exclude SCREEN wrapper (cmdline contains api/agent.py) and our own bash -c command
  # Use [a]pi trick to prevent grep self-match on its own command line
  agent_count=$(ps aux | grep '[a]pi/agent\.py' | grep -v SCREEN | wc -l)
  vibe_count=$(ps aux | grep '[a]pi/vibe_agent\.py' | grep -v SCREEN | wc -l)
  screen_count=$(screen -ls 2>/dev/null | grep -cE 'agent|vibe-agent' || true)
  echo "agent Python processes: ${agent_count} (expected: 1)"
  echo "vibe-agent Python processes: ${vibe_count} (expected: 1)"
  echo "screen sessions: ${screen_count} (expected: 2)"
  local issues=0
  [ "$agent_count" -gt 1 ] && echo "⚠️  agent DUPLICATE DETECTED" && issues=1
  [ "$vibe_count" -gt 1 ] && echo "⚠️  vibe-agent DUPLICATE DETECTED" && issues=1
  [ "$screen_count" -gt 2 ] && echo "⚠️  screen session DUPLICATE DETECTED" && issues=1
  [ "$issues" -eq 0 ] && echo "✅ counts OK"
  return "$issues"
}

case "${1:-}" in
  --all)
    kill_agents
    kill_servers
    clean_ipc
    ;;
  --servers)
    kill_servers
    ;;
  --clean)
    clean_ipc
    ;;
  --check)
    check_counts
    ;;
  *)
    kill_agents
    ;;
esac
