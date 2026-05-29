# Architecture — candle-analytics

## Data flow

```
EXCHANGES (Binance/Hyperliquid)
  ↓ fetch_klines()
DATA LAYER (candles/)
  ├─ clients/    — HTTP + WebSocket per exchange
  ├─ storage/    — SQLite (ohlcv table) + CSV export
  ├─ fetcher.py  — fetch → compute metrics → save
  └─ config.py   — Settings (pydantic-settings)
    ↓
API LAYER (api/)
  ├─ main.py        — FastAPI app, CORS, lifespan
  ├─ routes.py      — REST + WebSocket + file bridge
  ├─ dashboard.py   — Chart SPA (TradingView Lightweight Charts)
  ├─ analyze.py     — Percentile analysis table
  ├─ strategy_lab.py— Edge discovery filter builder
  ├─ vibe_lab.py    — AI code generation chat
  ├─ agent.py       — Strategy Lab LLM agent (standalone)
  ├─ vibe_agent.py  — Vibe Lab LLM agent (standalone)
  └─ sandbox.py     — Restricted exec env for backtest
    ↓
BROWSER — SPA at /dashboard, /strategy-lab, /vibe-lab
```

## Layers

| Layer | Path | Role |
|-------|------|------|
| Data | `candles/` | Fetch, store, compute metrics |
| API | `api/` | Serve data, WebSocket, LLM agents |
| UI | Embedded HTML/JS | 3 SPA pages, ES5, inline `<script>` |
| Strategy | `api/routes.py` | Edge search, sweep, batch |
| AI | `api/agent.py` + `api/vibe_agent.py` | Groq LLM, file-bridge IPC |

## File bridge IPC

```
Browser ↔ WebSocket → routes.py ↔ /tmp/*.json ↔ agent.py (standalone)
```

## 3 screen sessions

| Session | Process | Port |
|---------|---------|------|
| `candle` | .venv/bin/uvicorn api.main:app | 8001 |
| `agent` | .venv/bin/python api/agent.py (Strategy Lab) | — |
| `vibe-agent` | .venv/bin/python api/vibe_agent.py (Vibe Lab) | — |
