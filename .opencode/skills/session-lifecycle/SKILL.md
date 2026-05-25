---
name: session-lifecycle
description: >
  Manages session lifecycle across days. Automatically detects new day/new
  session on startup, updates CHRONOLOGIE.md with session entries, generates
  synthesis summaries, and tracks free-plan usage statistics. Use when starting
  a new session or when the user says "new day", "new session", or "resume".
---

# Session Lifecycle

## Auto-detection on session start

On every session start, check the following:

1. **New day?** — Compare today's date against the last entry in CHRONOLOGIE.md
   - If today > last entry date → **new day detected**
   - Action: prompt user "New day detected — create session entry?"

2. **Last session ended abruptly?** — Check for `sessions_upload/.synthesis-needed`
   - If marker exists → "Last session ended abruptly — synthesize it?"
   - If user agrees, run `/synthesis s` to fill the gap
   - After completion (or user declines), remove `.synthesis-needed`

3. **Restart all servers** — Kill stale screen sessions and restart all 3 processes:
   - Kill: `screen -S agent -X quit 2>/dev/null; screen -S vibe-agent -X quit 2>/dev/null; screen -S candle -X quit 2>/dev/null`
   - Restart in order: Strategy Lab agent → Vibe Lab agent → FastAPI server
   - Clean up stale `/tmp/vibe_chat_req_*.json`, `/tmp/vibe_chat_res_*.json`, `/tmp/strategy_chat_req_*.json`, `/tmp/strategy_chat_res_*.json`
   - Verify server health via `/api/health`
   - Report status of all 3 processes

4. **Read project docs** — Read `USERS_DOCUMENT/project-docs/*.md` relevant to the session's focus:
   - `ARCHITECTURE.md` — system overview
   - `API.md` — endpoints, WS, IPC
   - `FRONTEND.md` — UI conventions
   - `DATA.md` — DB schema, metrics
   - `STRATEGY_ENGINE.md` — edge search, backtest
   - `AGENTS.md` — LLM agent configs
   - `TEMPLATES.md` — strategy config format
   - `CONVENTIONS.md` — code style, rules

5. **Pending strategy chat requests?** — Check `/tmp/strategy_chat_req_*.json`
   - If any exist → "You have pending strategy requests from the Lab — handle them?"
   - If user agrees, run the **strategy-designer** skill to process them

6. **New project?** — If ROADMAP.md or CHRONOLOGIE.md doesn't exist yet
   - Offer to create them from the standard templates

## Session entry template (for CHRONOLOGIE.md)

```markdown
## YYYY-MM-DD — Session NNN : Brief title

**Duration** : ~Xh  
**Context** : One-line description of what this session focused on

### Added
- ...

### Changed
- ...

### Problems encountered
| Problem | Solution |
|---------|----------|
| ... | ... |

### Files changed
- ...

### Notes
- ...
```

## End-of-session checklist

When the session is ending (user says `/exit`, `/quit`, `stop`, or `restart`):

1. The auto-export plugin already saves the conversation
2. Offer to run `/synthesis s` if significant work was done
3. Update CHRONOLOGIE.md with the final session entry
4. Update ROADMAP.md (move done items to ✅ Done, add new 🟢 To Do items)
5. **Check for unprocessed strategy requests** — review `/tmp/strategy_chat_req_*.json` and respond if any
6. **Run code-quality checklist** (`~/.config/opencode/skills/code-quality/SKILL.md`)
   — catch `const` dupes, silent catches, broken imports, missing endpoints, WS connectivity

## Sub-agent usage during session

Use `task` sub-agents for parallelism during development. Rules:

1. **Exploration first** — before any edit, launch parallel `explore` agents to understand the codebase layout
2. **Parallel reads** — reading N files → single `explore` agent, not N sequential reads
3. **Independent work** — features A and B share no files → launch both as parallel `general` agents
4. **Sequential work** — B depends on A → single agent or manual chain, never parallel

Sub-agent results are returned to me, not to you. Anything that needs your input is relayed via `question`.

## Post-build rule: restart all servers

After ANY file edit, creation, or deletion in the project, restart ALL 3 processes:
```bash
ALL_OK=true

# 1. Kill old sessions
screen -S agent -X quit 2>/dev/null
screen -S vibe-agent -X quit 2>/dev/null
screen -S candle -X quit 2>/dev/null
sleep 1

# 2. Clean up stale IPC files
rm -f /tmp/vibe_chat_req_*.json /tmp/vibe_chat_res_*.json /tmp/strategy_chat_req_*.json /tmp/strategy_chat_res_*.json

# 3. Start Strategy Lab agent
screen -dmS agent bash -c 'cd /home/anymous/PROJETS/candle-analytics && python3 api/agent.py' || { echo "FAIL: agent screen"; ALL_OK=false; }
sleep 1

# 4. Start Vibe Lab agent
screen -dmS vibe-agent bash -c 'cd /home/anymous/PROJETS/candle-analytics && python3 api/vibe_agent.py' || { echo "FAIL: vibe-agent screen"; ALL_OK=false; }
sleep 1

# 5. Start FastAPI server
screen -dmS candle bash -c 'cd /home/anymous/PROJETS/candle-analytics && uvicorn api.main:app --host 0.0.0.0 --port 8001' || { echo "FAIL: candle screen"; ALL_OK=false; }
sleep 3
curl -sf http://localhost:8001/api/health > /dev/null || { echo "FAIL: health check"; ALL_OK=false; }

# 6. Verify all 3
echo "agent: $(ps aux | grep 'api/agent.py' | grep -v grep | wc -l) running"
echo "vibe-agent: $(ps aux | grep 'api/vibe_agent.py' | grep -v grep | wc -l) running"
echo "candle: $(ps aux | grep 'uvicorn' | grep -v grep | wc -l) running"
echo "## Servers: $([ "$ALL_OK" = true ] && echo '✅ all restarted' || echo '❌ some failed')"
```

This ensures the dashboard always reflects the latest code. The server runs in a
`screen` session without `--reload` because `--reload` does NOT detect changes
inside inline HTML/JS f-strings in `dashboard.py`.

**Always confirm restart status** at the end of every build message — append
`agent/vibe-agent/candle: ✅` or `❌ (reason)` for any that failed.

## Free-plan limit tracking

OpenCode free plan (Big Pickle / Zen) has **no documented session/daily/weekly/monthly
limits**. The free models are available "for a limited time" while collecting
feedback, and data may be used for model training.

When the user asks about limits:
- Inform them no published limits exist
- The auto-export stats (duration, tokens, compressions, MB) provide a rough
  estimate of usage, but there's no server-side limit tracking to compare against
- Limits may be undocumented backend constraints (no reset date known)

## Stats block appended to auto-export files

The auto-export plugin now appends a stats section at the top of each exported
session file:

```markdown
## Session Stats
- **Duration:** 2h 17m
- **Messages:** 142 (user: 38, assistant: 104)
- **Tokens used:** ~12 400
- **Compactions:** 3
- **Total output size:** 2.3 MB
- **Free plan used:** ~12 400 / unknown
- **Estimated limit reset:** not documented
```

These stats help the user estimate their actual usage even though no formal
limits are published.
