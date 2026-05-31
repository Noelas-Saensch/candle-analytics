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

# Kill ALL old agents + servers (handles any number of duplicates — unlike screen -X quit)
scripts/kill-agents.sh --all
sleep 1

# Start Strategy Lab agent
screen -dmS agent bash -c 'cd /home/anymous/PROJETS/candle-analytics && .venv/bin/python api/agent.py' || { echo "FAIL: agent screen"; ALL_OK=false; }
sleep 1

# Start Vibe Lab agent
screen -dmS vibe-agent bash -c 'cd /home/anymous/PROJETS/candle-analytics && .venv/bin/python api/vibe_agent.py' || { echo "FAIL: vibe-agent screen"; ALL_OK=false; }
sleep 1

# Start FastAPI server
screen -dmS candle bash -c 'cd /home/anymous/PROJETS/candle-analytics && .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8001' || { echo "FAIL: candle screen"; ALL_OK=false; }
sleep 3
if curl -sf http://localhost:8001/api/health > /dev/null; then
  echo "✅ Server healthy"
else
  echo "FAIL: health check failed"
  ALL_OK=false
fi

# Report all 3 — warn if duplicates found (exclude SCREEN wrapper)
agent_count=$(ps aux | grep '[a]pi/agent\.py' | grep -v SCREEN | wc -l)
vibe_count=$(ps aux | grep '[a]pi/vibe_agent\.py' | grep -v SCREEN | wc -l)
echo "agent: ${agent_count} running $([ "$agent_count" -gt 1 ] && echo '⚠️ DUPLICATES!')"
echo "vibe-agent: ${vibe_count} running $([ "$vibe_count" -gt 1 ] && echo '⚠️ DUPLICATES!')"
echo "candle: $(ps aux | grep '[u]vicorn' | wc -l) running"
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
ps aux | grep "[a]pi/agent.py" || echo "FAIL: agent (Strategy Lab) not running"
ps aux | grep "[a]pi/vibe_agent.py" || echo "FAIL: vibe-agent (Vibe Lab) not running"
```

### 14. Groq API key configured

```bash
[ -n "$GROQ_API_KEY" ] && echo "OK: GROQ_API_KEY set" || echo "FAIL: GROQ_API_KEY not set"
```

### 15. Python-to-JS quoting check

Run AFTER every edit to any `.py` file that contains inline HTML/JS (especially `dashboard.py`, `strategy_lab.py`, `vibe_lab.py`, `convert.py`).

```bash
bash scripts/check-pyjs-quotes.sh api/dashboard.py api/strategy_lab.py api/vibe_lab.py api/convert.py
```

Must report `PASS` for all files. If it reports `FAIL`, fix the quoting before proceeding.

#### Common fixes

| Python source | What Python sends | JS sees | Fix |
|---|---|---|---|
| `\\'` | `\'` | `\'` | ✅ Correct |
| `\'` | `'` | `'` | ❌ Backslash eaten — use `\\'` |
| `\\"` | `\"` | `\"` | ✅ Correct |
| `\"` | `"` | `"` | ❌ Backslash eaten — use `\\"` |

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

### 16. E2E smoke test

Run BEFORE marking any server-side change as complete:

```bash
python3 scripts/chat_e2e.py smoke --port 8001
```

Must report `All tests passed`. Checks all pages (dashboard, strategy-lab, convert), JS syntax, HTML structure, and critical API endpoints.

### 17. Subscription cleanup audit

After any change involving event listeners, SSE, timers, or chart subscriptions:

```bash
# Check subscription ↔ cleanup pairs
grep -rn "\.subscribeCrosshairMove\|\.subscribeVisibleTimeRangeChange\|addEventListener\|new ResizeObserver\|new EventSource\|setTimeout" api/ --include="*.py" --exclude-dir=.venv
# Check cleanups exist
grep -rn "\.unsubscribe\|removeEventListener\|\.disconnect\|\.close()\|clearTimeout" api/ --include="*.py" --exclude-dir=.venv
```

Every subscription must have a matching cleanup. Reference RULES.md §10 for the pattern.

### 19. Stale agent process check

Run at session start AND after any server restart cycle:

```bash
# Detect duplicate agent processes (known memory leak pattern)
# Must exclude SCREEN wrapper (its cmdline also contains api/agent.py)
agent_count=$(ps aux | grep '[a]pi/agent\.py' | grep -v SCREEN | wc -l)
vibe_count=$(ps aux | grep '[a]pi/vibe_agent\.py' | grep -v SCREEN | wc -l)
screen_count=$(screen -ls 2>/dev/null | grep -cE 'agent|vibe-agent' || echo 0)
echo "agent Python processes: ${agent_count} (expected: 1)  vibe-agent: ${vibe_count} (expected: 1)  screen sessions: ${screen_count} (expected: 2)"
if [ "$agent_count" -gt 1 ] || [ "$vibe_count" -gt 1 ] || [ "$screen_count" -gt 2 ]; then
  echo "⚠️  DUPLICATE AGENTS DETECTED — run scripts/kill-agents.sh --all immediately"
fi
```

### 20. New page / route registration check

When adding a new page route:
- [ ] Router registered in `api/main.py`
- [ ] Smoke test `chat_e2e.py` has HTML/JS/API checks for the new page
- [ ] `<nav>` in the new page links back to all existing pages
- [ ] Existing pages' `<nav>` includes the new page link
