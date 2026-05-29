# Conventions — candle-analytics

## Code style

- **Python**: async/await, pydantic-settings for config, httpx for HTTP
- **JS**: ES5 only (var, function, no arrow/const/let/?. /for...of/template literals)
- **Python strings containing JS**: escape `\'` as `\\'`, `\n` as `\\n`
- **Imports**: stdlib → third-party → local, alphabetical within groups

## Project structure

```
candle-analytics/
├── api/          — FastAPI server, routes, dashboards, agents
├── candles/      — Data layer: clients, storage, config, fetcher
├── vibe_engine/  — Rust PyO3 indicators + backtest
├── data/         — SQLite DB + CSV exports (gitignored)
├── scripts/      — backfill helper
├── cron/         — cron job templates
├── .opencode/    — AI skills: session-lifecycle, code-quality, auto-reload-server, strategy-designer
└── USERS_DOCUMENT/ — project-docs/, strategy config templates, saved models
```

## Screen sessions (3 total)

| Screen | Command | Must restart after code change? |
|--------|---------|-------------------------------|
| candle | `.venv/bin/uvicorn api.main:app --port 8001` | YES |
| agent | `.venv/bin/python api/agent.py` | NO (polls files) |
| vibe-agent | `.venv/bin/python api/vibe_agent.py` | NO (polls files) |

Restart ALL 3 on new session start (session-lifecycle skill step 3).

## Server ports

- Development: 8001 (screen session, no --reload)
- Legacy/Docker: 8000 (start.sh or docker-compose)

## Rules

- No USDT (French regulation)
- Public endpoints first (no API key needed for klines)
- SQLite + CSV dual storage
- One CLI: `python -m candles.main` (fetch, backfill, server)
- Never destroy API keys — comment them out
- Secrets in `.env` via `load_dotenv()`
- ERRORS.md after every bug fix, ROADMAP + CHRONOLOGIE after every session
