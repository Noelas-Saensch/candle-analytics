# Synthesis — candle-analytics (2026-05-24)

> Topic-organized summary of the project and session 018 (Performance + UI upgrade).

---

## 1. Project Overview

**Mission**: Discover statistical edges in OHLCV data to produce viable trading strategies.

**Architecture**:

```
candle-analytics/
├── candles/              # Data layer (fetch, store, stream)
│   ├── clients/          # Binance, Hyperliquid API clients
│   ├── storage/          # SQLite + CSV persistence
│   ├── stream/           # WebSocket real-time streaming
│   ├── fetcher.py        # Orchestrator
│   └── main.py           # CLI
├── api/
│   ├── main.py           # FastAPI entrypoint + router registration
│   ├── routes.py         # Core routes: /api/candles, /api/pairs, WS endpoints
│   ├── dashboard.py      # Dashboard HTML page (charts, metrics, analysis)
│   ├── vibe_lab.py       # Vibe Lab SPA (AI code generation from NL)
│   ├── strategy_lab.py   # Strategy Lab SPA (config-based edge search)
│   ├── vibe_agent.py     # Standalone Groq agent for Vibe Lab code gen
│   ├── agent.py          # Standalone Groq agent for Strategy Lab config gen
│   ├── _agent/           # Generator, validator, analyzer modules
│   └── sandbox.py        # Sandboxed Python strategy executor
├── vibe_engine/          # Rust/PyO3: indicators (8), backtest, metrics
├── data/                 # SQLite DB + CSV exports
├── cron/                 # Data fetch cron job
├── sessions_upload/      # Session exports + synthesis
└── .opencode/skills/     # OpenCode skills (strategy-designer, etc.)
```

**Infrastructure**:
- 2 uvicorn servers: root (port 8000, May 22 snapshot), us (port 8001, latest)
- 2 LLM agent screen sessions: `vibe-agent` (Vibe Lab), `agent` (Strategy Lab)
- Groq API (qwen/qwen3-32b, free tier)
- SQLite + CSV for data persistence

---

## 2. What Exists (by Layer)

### Data Layer
| Component | Status | Details |
|-----------|--------|---------|
| Binance client | ✅ | Full OHLCV fetch, auto-pagination |
| Hyperliquid client | ✅ | `candleSnapshot` endpoint, symbol mapping |
| SQLite storage | ✅ | `ohlcv` table, metrics/percentiles columns |
| CSV export | ✅ | Per-pair/timeframe |
| WebSocket stream | ✅ | Real-time candles, auto-reconnect |
| Backfill | ✅ | Fetch 5000+ bars per symbol/TF |

### API Layer
| Component | Status | Details |
|-----------|--------|---------|
| /api/candles | ✅ | OHLCV + pre-computed metrics |
| /api/pairs | ✅ | Symbol list from config |
| /api/health | ✅ | DB health check |
| /api/fetch | ✅ | On-demand backfill |
| /ws/vibe-chat | ✅ | WebSocket + file bridge + polling |
| /ws/strategy-chat | ✅ | WebSocket + file bridge + polling |
| /vibe/generate | ✅ | Groq code gen + template fallback |
| /vibe/validate | ✅ | Python syntax + security validation |
| /vibe/run | ✅ | Sandbox backtest |
| /vibe/analyze | ✅ | LLM result analysis |
| /vibe/optimize | ✅ | Grid search (max 100 combos) |
| /vibe/ask-opencode | ✅ | File bridge to terminal expert |

### Web UI (Strategy Lab)
| Feature | Status | Details |
|---------|--------|---------|
| Chat interface | ✅ | WS + HTTP fallback, Groq agent |
| Config builder | ✅ | AI populates, user edits |
| Conditions builder | ✅ | Groups, AND/OR, metric/op/value |
| Edge search | ✅ | Candle-based backtest engine |
| Results grid/cards | ✅ | Sortable, filterable |
| Parameter sweep | ✅ | Grid search over thresholds |
| Walk-forward | ✅ | Train/test split, N windows |
| Monte Carlo | ✅ | p-value for win rate/avg return |
| Export (YAML/JSON/CSV) | ✅ | Reimportable YAML |

### Web UI (Vibe Lab)
| Feature | Status | Details |
|---------|--------|---------|
| Tab 1 — Chat | ✅ | NL → AI conversation, WS + Groq |
| Tab 2 — Code | ✅ | Editor, validate, save, optimise |
| Tab 3 — Results | ✅ | Metrics, equity curve, trades, analysis |
| Templates | ✅ | 4 built-in (no API key needed) |
| Strategy persistence | ✅ | Save/load/delete JSON |
| Comparison mode | ✅ | Side-by-side results |
| Parameter optimization | ✅ | Grid search, 100-combo cap |

### Dashboard
| Feature | Status | Details |
|---------|--------|---------|
| OHLCV chart | ✅ | TradingView Lightweight Charts |
| 6 chart families | ✅ | Distribution, Time Series, Correlation, Percentile, Pattern, Overlay |
| 7 OHLC metrics | ✅ | Pre-computed in DB |
| Crosshair/zoom | ✅ | Fixed visibility, range lock |
| Heatmap | ✅ | devicePixelRatio fix |
| RAW DATA | ✅ | Paginated, percentile-safe |

---

## 3. Session 018 — Changes Made

### Performance
- **`vibe_agent.py`**: `max_tokens` 4096 → 2048 (4x smaller output → 2x faster)
- **`routes.py`**: `_vibe_poll_and_send()` poll 30 → 60 iterations (matches Groq 60s timeout)
- *Impact*: Vibe Lab responses arrive in ~20-30s instead of timing out; code now reaches Tab 2

### Bug Fixes
- **JS quoting in Python `"""..."""` strings** — 4 occurrences where `\'` was interpreted by Python as `'`, breaking JS string delimiters
  - `vibe_lab.py:1233,1236` — loadStrategy/deleteStrategy onclick templates
  - `vibe_lab.py:1314` — `split('\n')` → `split('\\n')`
  - `strategy_lab.py:1018` — switchRtab onclick template
- **Textarea height reset** — `sendChatMessage()` now resets `input.style.height = 'auto'` after clearing (both labs)
- **Inline onchange quoting** — extracted `switchGroupLogic()` function to avoid inline handler quoting issues

### UI Improvements (Strategy Lab)
- **Number spinners** — CSS for `::-webkit-inner-spin-button`: dark theme colors, visible hover
- **Wider inputs** — condition inputs 70→90px, action inputs 60→80px, inline params widened + `padding-right: 22px`
- **Better placeholders** — `"val"` → `"ex: 25"` with `title` showing metric description
- **Group colors** — 4-color alternating border cycle (`#e94560`, `#26a69a`, `#7b1fa2`, `#f9a825`)
- **AND/OR badges** — colored badge (green/orange) with live `switchGroupLogic()` updater

### Documentation
- `CHRONOLOGIE.md` — Session 018 entry added
- `ERRORS.md` — 4 new error entries (JS quoting, WS poll, inline onchange, textarea height)
- `USERS_DOCUMENT/synthesis/synthesis-project-2026-05-24.md` — this file

---

## 4. Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| **File bridge for agents** (not in-process) | Agents are standalone processes that can crash/restart independently; no blocking of uvicorn async loop |
| **Dual servers** (port 8000 + 8001) | 8000 = stable snapshot by root, 8001 = active development; both share same DB |
| **No streaming** | Groq API supports streaming but file-bridge architecture makes it complex; would need SSE on top of file polling |
| **ES5 target** | Ensures compatibility with any browser; no transpilation step needed |
| **Pre-computed metrics in DB** | Avoids recomputing 7 OHLC metrics on every query; computed once at insert time |

---

## 5. Known Limitations

- **No TA indicators in Strategy Lab** — RSI, SMA, MACD, etc. only available in Vibe Lab sandbox
- **No multi-pair backtest** — single symbol per search
- **No streaming responses** — chat uses polling (1s intervals), not push
- **Dual servers** (8000 + 8001) — confusing, should consolidate
- **Free tier Groq limits** — 14,400 req/day, concurrency caps, no SLA
- **screen-based agents** — fragile; not supervised or auto-restarted

---

## 6. Files Changed (Session 018)

```
api/vibe_lab.py          — textarea height reset, 3 JS quoting fixes
api/strategy_lab.py       — textarea height reset, JS quoting fix, spinner CSS, wider inputs,
                            group colors/badges, placeholders, switchGroupLogic function
api/vibe_agent.py         — max_tokens 4096→2048
api/routes.py             — _vibe_poll_and_send range 30→60
CHRONOLOGIE.md            — Session 018 entry
ERRORS.md                 — 4 new error entries
sessions_upload/          — this synthesis file
```
