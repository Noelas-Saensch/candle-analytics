---
name: code-quality
description: >
  Pre-declaration checklist executed at the end of every build to catch common
  bugs (const redeclaration, silent catch blocks, missing API responses, broken
  imports) before marking work as complete.
---

# Code Quality

## When to run

**After the last edit and before declaring a build complete.**  
Trigger: end of session, or after every significant batch of file changes.

---

## Pre-declaration checklist

Every item must pass. If any fails, fix it before proceeding.

### 1. JS `const` redeclaration scan

```bash
grep -n "const " api/dashboard.py | grep -v "^.*//" | sort
```

Manually verify no variable name appears twice in the same function scope.  
If found, rename one or switch to `let`.

### 2. Silent `catch` blocks

```bash
grep -n "catch(_)" api/dashboard.py api/strategy_lab.py
```

Every `catch(_) {}` must have a comment explaining WHY silence is safe, OR log
the error. Replace bare `catch(_) {}` with at least `catch(_) { console.warn(...) }`.

### 3. API endpoint responds

```bash
curl -s http://localhost:8001/api/health | grep ok || echo "FAIL: server dead"
curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/dashboard | grep 200 || echo "FAIL: /dashboard"
curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/strategy-lab | grep 200 || echo "FAIL: /strategy-lab"
```

### 4. Python imports valid

```bash
cd /home/anymous/PROJETS/candle-analytics && python3 -c "from api.main import app; print('imports OK')"
```

### 5. `--reload` NOT used in any startup command

```bash
grep -n "reload" ~/.config/opencode/skills/auto-reload-server/SKILL.md ~/.config/opencode/skills/session-lifecycle/SKILL.md && echo "WARNING: --reload referenced!"
```

If found, update to `screen` pattern.

### 6. Variables shadowing builtins

```bash
grep -nP "(^|\s)(all|type|id|dict|list|str|int|float|input|filter|map|open|file|dir|help|sum|min|max)\s*=" api/*.py
```

Any match should be renamed (e.g. `all_` → `all_data`, `type_` → `type_name`).

### 7. HTML response is well-formed

```bash
curl -s http://localhost:8001/dashboard | python3 -c "
import sys
h = sys.stdin.read()
# check balanced <div> tags (rough)
opens = h.count('<div')
closes = h.count('</div>')
if opens != closes:
    print(f'WARNING: <div> imbalance: {opens} open vs {closes} close')
else:
    print('HTML div balance OK')
"
```

### 8. Markdown files valid

```bash
grep -n "^\[\]" ROADMAP.md 2>/dev/null && echo "WARNING: empty checkbox found"
```

### 9. No hardcoded secrets

```bash
grep -rn "API_KEY\|SECRET\|PASSWORD\|token.*=" api/ candles/ 2>/dev/null
```

If any match, redact immediately.

### 10. All servers restart + verify

**This item MUST be run at the end of EVERY build** — all 3 processes must be running.

```bash
ALL_OK=true

# Kill old sessions
screen -S agent -X quit 2>/dev/null
screen -S vibe-agent -X quit 2>/dev/null
screen -S candle -X quit 2>/dev/null
sleep 1

# Clean stale IPC files
rm -f /tmp/vibe_chat_req_*.json /tmp/vibe_chat_res_*.json /tmp/strategy_chat_req_*.json /tmp/strategy_chat_res_*.json

# Start Strategy Lab agent
screen -dmS agent bash -c 'cd /home/anymous/PROJETS/candle-analytics && python3 api/agent.py' || { echo "FAIL: agent screen"; ALL_OK=false; }
sleep 1

# Start Vibe Lab agent
screen -dmS vibe-agent bash -c 'cd /home/anymous/PROJETS/candle-analytics && python3 api/vibe_agent.py' || { echo "FAIL: vibe-agent screen"; ALL_OK=false; }
sleep 1

# Start FastAPI server
screen -dmS candle bash -c 'cd /home/anymous/PROJETS/candle-analytics && uvicorn api.main:app --host 0.0.0.0 --port 8001' || { echo "FAIL: candle screen"; ALL_OK=false; }
sleep 3
if curl -sf http://localhost:8001/api/health > /dev/null; then
  echo "✅ Server healthy"
else
  echo "FAIL: health check failed"
  ALL_OK=false
fi

# Report all 3
echo "agent: $(ps aux | grep 'api/agent.py' | grep -v grep | wc -l) running"
echo "vibe-agent: $(ps aux | grep 'api/vibe_agent.py' | grep -v grep | wc -l) running"
echo "candle: $(ps aux | grep 'uvicorn' | grep -v grep | wc -l) running"
echo ""
echo "## Build complete — $([ "$ALL_OK" = true ] && echo '✅ all restarted' || echo '❌ some failed')"
```

### 11. WebSocket endpoint responds

```bash
# WebSocket handshake should succeed (use curl with ws upgrade)
curl -s -o /dev/null -w "%{http_code}" -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" http://localhost:8001/api/ws/strategy-chat 2>/dev/null | grep 101 || echo "INFO: curl WS check may fail but browser WS should work"
```

### 12. Strategy-designer skill exists

```bash
test -f ~/.config/opencode/skills/strategy-designer/SKILL.md || echo "FAIL: strategy-designer skill missing"
```

### 13. LLM agent processes running

```bash
ps aux | grep "api/agent.py" | grep -v grep || echo "FAIL: agent (Strategy Lab) not running"
ps aux | grep "api/vibe_agent.py" | grep -v grep || echo "FAIL: vibe-agent (Vibe Lab) not running"
```

### 14. Groq API key configured

```bash
[ -n "$GROQ_API_KEY" ] && echo "OK: GROQ_API_KEY set" || echo "FAIL: GROQ_API_KEY not set"
```

---

## Sub-agent usage patterns

During development, use sub-agents (`task` tool) for parallelism.
Apply these rules automatically — no checklist item needed.

### When to parallelise

| Task type | Action |
|-----------|--------|
| Explore 3+ independent files/modules | Launch `explore` agents in parallel (single message, multiple `task` calls) |
| Research multiple external sources | Launch 1 `explore` per source in parallel |
| Read N separate files | Group into 1 `explore` agent with "read these N files" |
| Sequential dependency (B needs A) | Single agent, or chain manually |

### Parallelism rules

1. **Batch by type** — all `explore` together, all `general` together (explore finishes faster)
2. **Pin the return format** — always end prompts with "Return: [specific items]"
3. **4-6 max** parallel agents per message (diminishing returns beyond)
4. **Never parallelise** tasks that modify the same files (race condition)

### Prompt template

```
[context: what to search / read]
Be thorough — check [locations].
Return:
- [specific item 1]
- [specific item 2]
```

## Quick reference

| Command | Purpose |
|---------|---------|
| `grep -n "const " api/dashboard.py` | Find all const declarations |
| `grep -n "catch(_)" api/*.py` | Find silent catches |
| `python3 -c "from api.main import app"` | Check Python imports |
| `curl -s http://localhost:8001/api/health` | Verify server is alive |
