---
name: auto-reload-server
description: >
  Automatically restart the FastAPI server after any file change in api/ or
  candles/ so the dashboard reflects new code immediately.
---

# Auto-Reload Server

**`--reload` does NOT work reliably** — inline HTML/JS in `dashboard.py` string
content is not detected by `--reload` timestamp checks. Always restart manually.

## How it works

1. Server runs in a `screen` session (no `--reload`)
2. After EVERY file edit, kill the screen session and start a new one
3. Verify health before declaring success

## Startup command

Start ALL 3 processes (server + 2 agents):

```bash
# 1. Strategy Lab agent — requires GROQ_API_KEY env var
screen -dmS agent bash -c 'cd /home/anymous/PROJETS/candle-analytics && python3 api/agent.py'
sleep 1

# 2. Vibe Lab agent (code generation)
screen -dmS vibe-agent bash -c 'cd /home/anymous/PROJETS/candle-analytics && python3 api/vibe_agent.py'
sleep 1

# 3. FastAPI server
screen -dmS candle bash -c 'cd /home/anymous/PROJETS/candle-analytics && uvicorn api.main:app --host 0.0.0.0 --port 8001'
sleep 3

# 4. Verify
curl -s http://localhost:8001/api/health
```

To check processes: `screen -ls` or `ps aux | grep -E "api/agent|api/vibe_agent|uvicorn" | grep -v grep`

## Restart commands

Restart all 3 at once:
```bash
screen -S agent -X quit 2>/dev/null; screen -S vibe-agent -X quit 2>/dev/null; screen -S candle -X quit 2>/dev/null
sleep 1
rm -f /tmp/vibe_chat_req_*.json /tmp/vibe_chat_res_*.json /tmp/strategy_chat_req_*.json /tmp/strategy_chat_res_*.json
screen -dmS agent bash -c 'cd /home/anymous/PROJETS/candle-analytics && python3 api/agent.py'
sleep 1
screen -dmS vibe-agent bash -c 'cd /home/anymous/PROJETS/candle-analytics && python3 api/vibe_agent.py'
sleep 1
screen -dmS candle bash -c 'cd /home/anymous/PROJETS/candle-analytics && uvicorn api.main:app --host 0.0.0.0 --port 8001'
sleep 3
curl -s http://localhost:8001/api/health
echo "agent: $(ps aux | grep 'api/agent.py' | grep -v grep | wc -l) running"
echo "vibe-agent: $(ps aux | grep 'api/vibe_agent.py' | grep -v grep | wc -l) running"
echo "candle: $(ps aux | grep 'uvicorn' | grep -v grep | wc -l) running"
```

Restart Strategy Lab agent only:
```bash
screen -S agent -X quit 2>/dev/null; sleep 1
screen -dmS agent bash -c 'cd /home/anymous/PROJETS/candle-analytics && python3 api/agent.py'
sleep 1
```

Restart Vibe Lab agent only:
```bash
screen -S vibe-agent -X quit 2>/dev/null; sleep 1
screen -dmS vibe-agent bash -c 'cd /home/anymous/PROJETS/candle-analytics && python3 api/vibe_agent.py'
sleep 1
```

Restart server only:
```bash
screen -S candle -X quit 2>/dev/null; sleep 1
screen -dmS candle bash -c 'cd /home/anymous/PROJETS/candle-analytics && uvicorn api.main:app --host 0.0.0.0 --port 8001'
sleep 3
curl -s http://localhost:8001/api/health
```

## Files that require restart

Any change to:
- `api/*.py` — routes, dashboard, analyze, main, strategy_lab
- `candles/*.py` — config, fetcher, storage, clients, stream
- `requirements.txt` — dependency changes
- ROADMAP.md, SKILL.md — restart to prove the rule works

## Post-build restart checklist

After EVERY session where files were changed:
1. Run code-quality checklist (`~/.config/opencode/skills/code-quality/SKILL.md`)
2. Kill screen session, start new server
3. `curl -s http://localhost:8001/api/health | grep ok`
4. If dashboard modified: `curl -s http://localhost:8001/dashboard | head -1`
5. If strategy-lab modified: `curl -s http://localhost:8001/strategy-lab | head -1`

## Known endpoints to verify

| Route | Purpose |
|-------|---------|
| `/api/health` | Server alive |
| `/dashboard` | Main chart + metrics UI |
| `/analyze` | Percentile analysis table |
| `/strategy-lab` | Edge discovery filter builder |
| `/api/edge/search` | POST — scan candles for matching conditions |
