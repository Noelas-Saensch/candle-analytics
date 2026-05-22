# CHRONOLOGIE — candle-analytics

> Dated log of all changes, additions, deletions, modifications, problems encountered and their solutions.

---

## 2026-05-22 — Session 001 : Initial project setup

**Duration** : ~2h  
**Context** : Project creation from scratch in `/home/anymous/PROJETS/candle-analytics/`

### Added
- **Project scaffold** — directory structure, `.env`, `.gitignore`, `requirements.txt`
- **ROADMAP.md** — mission, pairs, timeframes, task tracking, rules
- **CHRONOLOGIE.md** — this file
- **Config & models** — `candles/config.py` (Settings via pydantic-settings), `candles/models.py` (OHLCV, PairConfig)
- **Binance client** — `candles/clients/base.py` (httpx), `candles/clients/binance.py` (kline API)
- **Hyperliquid client** — `candles/clients/hyperliquid.py` (stub, `_fetch_klines` raises NotImplementedError)
- **SQLite storage** — `candles/storage/db.py` (ohlcv table, save/query methods)
- **CSV export** — `candles/storage/csv_writer.py`
- **Fetcher orchestrator** — `candles/fetcher.py` (fetch → store for all pairs/TFs)
- **CLI** — `candles/main.py` (argparse: fetch, backfill, server commands)
- **FastAPI server** — `api/main.py` + `api/routes.py` (GET /api/candles, /api/pairs, /api/health)
- **start.sh** — launch backend script
- **Backfill script** — `scripts/backfill.py` (fetch last 5000 bars per default TF)
- **Cron doc** — `cron/fetch-candles.cron`
- **opencode skill** — `~/.opencode/skill/candle-analytics.skill.md`
- **opencode command** — `~/.opencode/command/candle-fetch.command.md`

### Problems encountered
| Problem | Solution |
|---------|----------|
| EURC/USDC pair doesn't exist on Binance | Added to ROADMAP as ❌ abandoned, skipped during fetch |
| PAXGUSDC has non-standard `PERCENT_PRICE_BY_SIDE` filter (1.2/0.8) | Not a blocker for klines — only affects trading |
| Hyperliquid API docs unclear on OHLCV endpoint | Stubbed `_fetch_klines` with NotImplementedError — will implement when API is confirmed |

### Files created
- `candles/__init__.py`
- `candles/config.py`
- `candles/models.py`
- `candles/clients/__init__.py`
- `candles/clients/base.py`
- `candles/clients/binance.py`
- `candles/clients/hyperliquid.py`
- `candles/storage/__init__.py`
- `candles/storage/db.py`
- `candles/storage/csv_writer.py`
- `candles/fetcher.py`
- `candles/main.py`
- `api/__init__.py`
- `api/main.py`
- `api/routes.py`
- `scripts/backfill.py`
- `cron/fetch-candles.cron`
- `start.sh`
- `~/.opencode/skill/candle-analytics.skill.md`
- `~/.opencode/command/candle-fetch.command.md`

### Notes
- Binance klines endpoint is fully public — no API keys needed.
- `_seconds_until_next_hour` helper from the reference project's scheduler was adapted for the cron doc.
- The project follows the same code conventions as `Binance - Algo gestion` (httpx, pydantic-settings, async).

---

## 2026-05-22 — Session 002 : Session export/import commands

**Duration** : ~30min  
**Context** : Added auto export/import for AI sessions

### Added
- **Session management skill** — `~/.opencode/skill/session-management.skill.md`
- **session-export command** — `~/.opencode/command/session-export.command.md` (writes full session to `sessions_upload/`)
- **session-import command** — `~/.opencode/command/session-import.command.md` (reads sessions from `sessions_upload/`)
- **Session export test** — `sessions_upload/session-2026-05-22_16-30-00.md` (auto-export of session 001+002)

### Usage
```
/session-export              → export to current project's sessions_upload/
/session-export actual       → same as above
/session-export <project>    → export to /home/anymous/PROJETS/<project>/sessions_upload/
/session-import              → import sessions from current project
/session-import <project>    → import sessions from specified project
```

### Notes
- Folder naming is `sessions_upload/` (plural) at project root
- If folder doesn't exist, command creates it automatically

---

## 2026-05-22 — Session 003 : Session audit (repeated topics analysis)

**Duration** : ~30min  
**Context** : Added semantic analysis tool to detect repeated questions across sessions

### Added
- **Session analysis script** — `scripts/analyze_sessions.py` (discovery → parse → embed → cluster → report)
- **session-audit command** — `~/.opencode/command/session-audit.command.md`
- **session-analysis skill** — `~/.opencode/skill/session-analysis.skill.md`
- **Ollama embedding model** — `nomic-embed-text` pulled (274 MB)

### How it works
1. Discovers all `sessions_upload/` folders under `PROJETS/` and `DEV & CODE/`
2. Parses user messages from session `.md` files
3. Embeds via Ollama's `nomic-embed-text` → 768-dim vectors
4. Clusters by cosine similarity (Union-Find, default threshold 0.65)
5. Reports repeated topics grouped by frequency (🔴 ≥5, 🟡 3–4, 🟢 2)

### Usage
```
/session-audit                     → scan all projects
/session-audit --project NAME      → single project
/session-audit --threshold 0.5     → adjust sensitivity
```

### Test results
- Found 2 session files in candle-analytics
- Parsed 5 user messages (min 15 chars)
- At threshold 0.5: 4 messages clustered (project setup topic), 1 unique
- At threshold 0.65: all 5 unique (too strict for small dataset)
- Default threshold kept at 0.65 (will be more useful as sessions accumulate)

### Dependency
- `ollama pull nomic-embed-text` (274 MB) — no Python ML packages needed

---

## 2026-05-22 — Session 004 : Hyperliquid client implementation

**Duration** : ~15min  
**Context** : Implemented the Hyperliquid OHLCV client using `candleSnapshot` API endpoint

### Added
- **Hyperliquid client** — `candles/clients/hyperliquid.py` (full implementation)
  - Uses `POST https://api.hyperliquid.xyz/info` with `{"type": "candleSnapshot", ...}`
  - Maps project timeframes to Hyperliquid intervals (supports: 1m, 5m, 15m, 30m, 1H, 2H, 4H, 12H, 1D, 3D, 1W, 1M)
  - Auto-strips quote suffixes (USDC/USDT/USD) from config symbols to get Hyperliquid coin names
  - Handles time range calculation from `limit` parameter
  - `fetch_5000_klines` for backfill support

### Changed
- **ROADMAP.md** — Hyperliquid client marked ✅ done, updated pair symbols (BTC, PAXG)
- **ROADMAP.md** — Hyperliquid coin names confirmed: BTC= "BTC", PAXGUSDC= "PAXG"

### Test results
- `fetch_klines('BTC', '1H', limit=5)` → 6 candles returned ✓
- `fetch_klines('BTCUSDC', '1m', limit=3)` → 4 candles (symbol mapping works) ✓
- `fetch_klines('PAXGUSDC', '1H', limit=3)` → 4 candles (GOLD pair works) ✓

### Notes
- Hyperliquid API limits: max ~5000 candles per request, weight 20 + 1/60 items

---

## 2026-05-22 — Session 005 : WebSocket real-time streaming

**Duration** : ~20min  
**Context** : Added WebSocket stream support for live candle updates from Binance and Hyperliquid

### Added
- **Stream module** — `candles/stream/` with handler and runner:
  - `BinanceHandler` — connects to `wss://stream.binance.com:9443/stream` with combined streams
  - `HyperliquidHandler` — connects to `wss://api.hyperliquid.xyz/ws`, subscribes per coin/interval
  - `run_stream()` — orchestrator creates handlers for all configured pairs/timeframes
- **CLI command** — `python -m candles.main stream` (or `candle-fetch stream`)
- **Auto-reconnect** — both handlers retry after 5s on disconnect
- **Graceful shutdown** — SIGINT/SIGTERM handler stops all streams cleanly

### Changed
- **BinanceClient.fetch_klines** — now paginates internally when `limit > 1000` (bypasses Binance's 1000-candle cap)
- **BinanceClient.fetch_5000_klines** — simplified to delegate to `fetch_klines(limit=5000)`

### Test results
- Stream connected to both exchanges simultaneously
- Binance: 3 BTCUSDC 1m candles received in ~15s ✅
- Hyperliquid: 3 BTCUSDC 1m candles received in ~15s ✅
- Data persisted to SQLite in real-time ✅

### Usage
```bash
# Start streaming (runs until Ctrl+C)
python -m candles.main stream

# Use opencode command
candle-fetch stream
```

### Notes
- Binance combined stream URL supports multiple pairs/timeframes in one connection
- Hyperliquid requires one subscription message per (coin, interval) pair
- Default `ping_interval=20s` keeps connections alive
- Reconnect retries indefinitely with 5s delay
- Some timeframes not supported by Hyperliquid (6H, 2D, 2W, 2M+) — mapped unsupported ones raise ValueError with list of supported intervals
- Public endpoint — no API key needed for candle snapshots

---

## 2026-05-22 — Session 006 : Docker deployment

**Duration** : ~10min  
**Context** : Containerized the API server and WebSocket stream for deployment

### Added
- **Dockerfile** — single-stage build on `python:3.13-slim`, exposes port 8000
- **docker-compose.yml** — two services:
  - `api` — FastAPI server (port 8000, env from `.env`, persistent `data/` volume)
  - `stream` — WebSocket stream daemon (auto-restart on failure)
- **.dockerignore** — excludes `data/`, `__pycache__/`, `.git/`, `.venv/`, etc.

### Changed
- **ROADMAP.md** — Docker deployment marked ✅ done

---

## 2026-05-22 — Session 008b : Auto-export on session end

**Duration** : ~20min  
**Context** : Created a plugin that automatically exports the session before any exit/stop/restart action

### Added
- **Auto-export plugin** — `~/.config/opencode/plugins/auto-export.ts`
  - Hooks `command.execute.before` to catch exit commands (`/exit`, `/quit`, `stop`, `restart`)
  - Hooks `tool.execute.before` to catch destructive bash (kill, shutdown, reboot, etc.)
  - Hooks `experimental.session.compacting` to catch session-end signals
  - Periodic auto-save every 25 messages (max 1/min)
  - Writes full conversation to `<project>/sessions_upload/auto-export-<timestamp>.md`
- **Auto-export skill** — `~/.config/opencode/skills/auto-export/SKILL.md`
- **Config update** — `~/.config/opencode/opencode.jsonc` registers the skills path

### Changed
- **~/.bashrc** — added opencode shell wrapper with SIGHUP trap

### How it works
1. Plugin runs inside opencode, monitors lifecycle events
2. Before any session-ending action, it fetches all messages via the client API
3. Writes them to `sessions_upload/` with timestamp and trigger reason
4. On SIGKILL/power loss: periodic auto-save limits data loss to ~25 messages

### Usage
```bash
# Start both services
docker compose up -d

# Start only the API
docker compose up -d api

# View logs
docker compose logs -f

# Stop
docker compose down
```

### Notes
- SQLite data persists via bind mount (`./data:/app/data`)
- Stream service runs indefinitely with auto-reconnect
- For production: use a dedicated DB (PostgreSQL) instead of SQLite

---

## 2026-05-22 — Session 007 : Dashboard web UI

**Duration** : ~15min  
**Context** : Added a simple web dashboard for candlestick visualisation

### Added
- **Dashboard page** — `api/dashboard.py` serves HTML at `/dashboard`
  - Built with TradingView Lightweight Charts (CDN)
  - Dark theme matching the project aesthetic
  - Dropdowns for exchange, symbol, timeframe, candle count
  - Fetches data from `/api/candles` and renders OHLCV candlesticks

### Changed
- **api/main.py** — registered dashboard router
- **ROADMAP.md** — Dashboard marked ✅ done

### Usage
```
Open http://localhost:8000/dashboard in a browser
```

### Test results
- HTML served at `/dashboard` ✅
- Pairs dropdown populated from `/api/pairs` ✅
- Candles rendered from `/api/candles` ✅

---

## 2026-05-22 — Session 008 : Dashboard improvements + storage estimate

**Duration** : ~15min  
**Context** : Added "All" option, fetch-on-demand, and analysed storage requirements

### Added
- **"All" option** — candle count dropdown now has `All` (removes limit, returns all stored candles)
- **Fetch-on-demand** — when no data exists for a pair/timeframe, a message appears with buttons to "Fetch last 5000" or "Fetch all" (calls `POST /api/fetch`)
- **`POST /api/fetch`** — new API endpoint to trigger backfill for a specific pair/timeframe

### Changed
- **api/routes.py** — removed `le=5000` limit constraint on `/api/candles`; added `/api/fetch` endpoint
- **api/dashboard.py** — updated HTML with no-data state and fetch buttons

### Storage estimate (full BTCUSDC history)

| Timeframe | Binance (since 2018-12-15) | Hyperliquid (since 2021-01-01) | Total |
|-----------|---------------------------|-------------------------------|-------|
| 1m | ~3.9M rows / ~310 MB | ~2.8M rows / ~225 MB | **~535 MB** |
| 1H | ~65K rows / ~5 MB | ~47K rows / ~4 MB | **~9 MB** |
| 1D | ~2.7K rows / ~0.2 MB | ~2K rows / ~0.2 MB | **~0.4 MB** |
| **Total** | | | **~545 MB** |

Main cost is 1m candles (~435 MB combined). 1H and 1D are negligible (~10 MB).

### Existing data found
All BTCUSDC data is in `candle-analytics/data/`:
- **SQLite** (`candles.db`, 6.9 MB) — 24,680 BTCUSDC rows (5000 per timeframe per exchange)
- **CSV** (`data/csv/*BTCUSDC*.csv`, 1.38 MB) — 6 files, same data

No BTCUSDC data found anywhere else on the system.

---

## 2026-05-22 — Session 009 : /restart command

**Duration** : ~10min  
**Context** : Created a `/restart` command that exports the session then restarts opencode

### Added
- **restart command** — `~/.opencode/command/restart.command.md`
  - Exports the full session to `sessions_upload/`
  - Creates a restart marker file and terminates the current process
- **Shell restart loop** — `~/.bashrc` opencode wrapper now detects `/tmp/opencode-restart` marker and re-launches automatically

### Usage
```
/restart
```
Session is saved, then opencode restarts automatically.

---

## 2026-05-22 — Session 010 : /synthesis command + skill

**Duration** : ~15min  
**Context** : Created a command + skill to generate concise topic-organized work summaries

### Added
- **synthesis command** — `~/.opencode/command/synthesis.command.md`
  - `/synthesis d [p|i|a]` — today's work
  - `/synthesis s [p|i|a]` — this session
  - `/synthesis a [p|i|a]` — all project (default)
  - Refinement: `p` (project only), `i` (infrastructure only), `a` (both, default)
- **synthesis skill** — `~/.config/opencode/skills/synthesis/SKILL.md`
  - Auto-detects abruptly ended sessions on next start
  - Offers to synthesize the gap
- **Plugin update** — auto-export now writes `.synthesis-needed` marker on session-end events
  - Marker is checked by the AI on next session start

### Answered
> *"Will CHRONOLOGIE.md and synthesis be useful together?"*

**Yes — they are complementary, not redundant.**

| | CHRONOLOGIE.md | Synthesis |
|---|---|---|
| Format | Chronological, session-by-session | Thematic, cross-session |
| Written | By AI at each session end | On demand via `/synthesis` |
| Purpose | Raw log of what happened | Distilled summary of work done |
| Detail | Detailed (files, problems, solutions) | Concise (features, decisions, patterns) |

CHRONOLOGIE.md is the **input data** for the synthesis — without it, the synthesis would have nothing to summarize. Keep both.
