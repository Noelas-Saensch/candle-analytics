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

---

## 2026-05-23 — Session 012 : Pre-computed metrics, per-family charts, efficiency overhaul

**Duration** : ~4h  
**Context** : Major refactor — pre-computed metrics in DB, chart family system with per-family types/metrics, crosshair/zoom fixes, data fetching optimization, session stats tracking

### Added
- **Pre-computed metrics in DB** — `metrics TEXT` column stores all 7 OHLC metrics as JSON during save; no more server-side computation on each query
- **Pre-computed percentiles** — `percentiles TEXT` column; backfilled on server startup via `startup_backfill()`
- **Per-family chart type dropdown** — each of the 6 families (Distribution, Time Series, Correlation, Percentile, Pattern, Overlay) gets its own `<select>` listing available chart types
- **Per-metric checkboxes** — each family shows checkboxes for all 7 metrics; `getFamMetrics()` helper reads which are checked; `Toutes` checkbox shortcuts all/none
- **CHART_TYPES config** — maps each family to multiple render functions; 16 old render functions updated to new `(ctx, canvas, data, activeMetrics, getFamParam, famId)` interface
- **Crosshair fix** — red vertical/horizontal lines with `visible: true` and `labelBackgroundColor: '#e94560'` for readable axis overlays
- **Zoom lock fix** — corrected from `minRange` to `maxRange`; prevents zoom-out beyond the original axis range
- **Heatmap DPR fix** — canvas now uses `devicePixelRatio` for crisp rendering at any screen zoom
- **RAW DATA crash fix** — `c.percentiles = c.percentiles || {}` initializer in `renderRawTable()`
- **Background data prefetch** — `prefetchAnalyze()` runs after chart loads to pre-load Metrics/RAW DATA tab data
- **Periodic auto-save** — every 25 messages (max 1/min) the auto-export plugin saves the session
- **SSH remote switch** — git origin switched from HTTPS to SSH for passwordless push

### Changed
- **api/analyze.py** — percentiles removed from server response; client recomputes locally from `metrics` values
- **api/analyze.py & api/dashboard.py** — pre-computed `metrics` and `percentiles` from DB are used directly
- **api/routes.py** — `/api/candles` now includes `metrics` in the response
- **api/dashboard.py** — `switchTab()` triggers `loadChart()` / `loadAnalyze()` / `loadRawData()` independently; `loadAnalyze()` computes percentiles client-side for the working set

### Planned (next)
- [ ] **Enhanced auto-export stats** — track session duration, token usage, compressions, payload MB in export files
- [ ] **Data fetching via sessionStorage** — cache API responses across page refreshes; check before fetch
- [ ] **Background data fetch** — load chart + metrics data in parallel at page load, not per-tab
- [ ] **/api/candles/count endpoint** — light check before full data fetch
- [ ] **RAW DATA server-side pagination** — LIMIT 100, load more on scroll
- [ ] **SQL aggregate metrics** — server returns min/max/mean from SQLite aggregations
- [ ] **Session-lifecycle skill** — auto-detect new day/session, prompt for synthesis

### Problems encountered
| Problem | Solution |
|---------|----------|
| RAW DATA table crashed on empty percentiles | Added `c.percentiles = c.percentiles \|\| {}` in `renderRawTable()` |
| Crosshair labels invisible | Added `visible: true` (was `labelVisible`) + `labelBackgroundColor` |
| Zoom could go beyond data range | Changed from `minRange` to `maxRange` in zoom limits |
| Heatmap blurry on retina displays | Applied `devicePixelRatio` scaling |
| Percentile computation slow client-side | Pre-computed in DB, served directly |
| Each chart type had different function signatures | Unified 16 render functions to same `(ctx, canvas, data, activeMetrics, getFamParam, famId)` interface |

### Files changed
- `api/dashboard.py` — full rewrite of chart family system, new per-family params, crosshair/zoom fixes
- `api/routes.py` — `/api/candles` includes `metrics` in response
- `api/analyze.py` — percentiles removed from server, client-side only
- `candles/storage/db.py` — `metrics TEXT` + `percentiles TEXT` columns, `startup_backfill()`
- `candles/fetcher.py` — compute metrics during `save_candles()`
- `candles/models.py` — `metrics` + `percentiles` fields added
- `candles/config.py` — `BACKFILL_PCTL_BARS` setting added
- `~/.config/opencode/plugins/auto-export.ts` — enhanced with periodic auto-save
- `~/.config/opencode/skills/synthesis/SKILL.md` — abrupt-stop detection

### Notes
- The 7 OHLC metrics (OC%, OH%, OL%, HL%, HC%, LC%, Vol%) are now computed once at insert time and stored as JSON
- Percentiles are pre-computed on startup for the last 2000 candles per pair/TF (configurable via `BACKFILL_PCTL_BARS`)
- OpenCode free plan (Big Pickle / Zen) has no documented session/daily/weekly/monthly limits
- Session lifecycle skill added to auto-detect new day and prompt for CHRONOLOGIE update

---

## 2026-05-24 — Session 014 : Vibe Lab bug fixes + maintenance

**Duration** : ~2h  
**Context** : Fixed 3 critical Vibe Lab bugs (pair dropdown empty, tabs not clickable, generate button broken), added ask-opencode endpoint, GROQ_API_KEY, expanded bar options.

### Fixed
- **All 10 JS fetch URLs** — changed from `/api/vibe/...` to `/vibe/...` (root cause of all 404 errors)
- **`loadPairs()`** — added `catch()` with fallback symbols (BTCUSDC/PAXGUSDC) + inline script for instant pre-population
- **`loadTemplates()`** — added error guard + `catch()`
- **`loadSavedStrategies()`** — already had `catch()` (verified)
- **`askOpenCode()`** — replaced broken `/api/edge/chat` call with `POST /vibe/ask-opencode` endpoint that writes to `/tmp/vibe_opencode_*.md`
- **JS regex `\d`** — escaped for Python SyntaxWarning
- **Cleanup** — removed unused `_pendingOC` state variable and dead `request` object

### Added
- **`POST /vibe/ask-opencode`** — new endpoint that writes strategy request to `/tmp/` for terminal-based OpenCode expert mode
- **GROQ_API_KEY** — set in `.env` for Vibe Lab (Qwen3-32b) and Strategy Lab LLM agent
- **Bars dropdown** — added 2500 and 5000 options
- **Inline pair fallback** — `<script>` right after the pair `<select>` guarantees options load before the main JS
- **ROADMAP RULE #9** — "Never destroy API keys, comment them out instead"
- **ROADMAP RULE #10** — "Auto-update ROADMAP + CHRONOLOGIE after each session"

### Changed
- **`.env`** — added `GROQ_API_KEY`
- **`api/agent.py`** — updated comment to reference `.env` instead of inline key
- **`ROADMAP.md`** — added rules 9 and 10

### Problems encountered
| Problem | Solution |
|---------|----------|
| All JS fetches returned 404 | Changed `/api/vibe/` → `/vibe/` (vibe_router has no `/api` prefix) |
| Pair dropdown empty after hard refresh | Added inline `<script>` that populates before main JS runs |
| `askOpenCode()` called non-existent `/api/edge/chat` | Created `POST /vibe/ask-opencode` endpoint that writes to `/tmp/` |
| Server kept dying (child of bash) | Used `setsid` + `disown` to properly detach from shell |
| GROQ_API_KEY not found in system | User provided new key — set in `.env` |

---

## 2026-05-23 — Session 013 : Vibe Lab — AI strategy generation engine

**Duration** : ~2h  
**Context** : Created Vibe Lab — natural language → AI-generated Python strategy → backtest → analyze pipeline. Inspired by VibeTrading.

### Added
- **`vibe_engine/`** — Rust library with PyO3 bindings:
  - `indicators.rs` — RSI, SMA, EMA, BBANDS, ATR, MACD, Stochastique, VWAP (pure Rust, numpy arrays)
  - `backtest.rs` — Vectorized backtest engine with SL/TP, long/short entry
  - `metrics.rs` — Compute engine: Sharpe, Sortino, Calmar, drawdown, win rate, profit factor
  - `Cargo.toml` — PyO3 + numpy deps
  - `lib.rs` — Python module entry point
- **`api/_agent/`** — LLM agent pipeline:
  - `generator.py` — Gemini/Groq code generation from natural language + 4 templates (SMA crossover, RSI oversold, BB mean reversion, MACD crossover)
  - `validator.py` — Static validation: syntax check, required functions, security blacklist
  - `analyzer.py` — LLM backtest analysis: score 1-10, strengths, weaknesses, recommendations
  - `__init__.py`
- **`api/sandbox.py`** — `StrategySandbox` class: restricted exec environment with injected sandbox functions (long/short/close/get_ohlcv/get_price), equity tracking, trade recording
- **`api/vibe_lab.py`** — Full SPA with 3 tabs:
  - Describe (templates + natural language input)
  - Code (editor + validation + backtest)
  - Results (metrics grid, equity curve chart, trades table, LLM analysis)
  - API endpoints: `/api/vibe/generate`, `/api/vibe/validate`, `/api/vibe/run`, `/api/vibe/analyze`, `/api/vibe/templates`
  - "Ask OpenCode" button for expert mode via terminal
- **Tab switch** — `api/strategy_lab.py`: toggle between Strategy Lab / Vibe Lab in header nav

### Changed
- **`api/main.py`** — Registered `vibe_lab_router`
- **`api/agent.py`** — Switched model from `llama-3.3-70b-versatile` to `qwen/qwen3-32b` (better code generation, same free tier)
- **`requirements.txt`** — Added `numpy`, `maturin`
- **`ROADMAP.md`** — Updated Phase 2 with Vibe Lab items

### Planned (next)
- [x] Build Rust library: `maturin develop --release` in `vibe_engine/` — all 8 indicators + backtest + metrics verified
- [x] `vibe_engine` injected into sandbox `local_vars` as `ve` for import-free access
- [x] Sandbox fixed — column rename (open→o, close→c, etc.), correct bar index in price lookup
- [x] Full pipeline tested — template generation → sandbox backtest → metrics + analysis
- [x] Strategy persistence — save/load/delete via `/vibe/save`, `/vibe/strategies`, `/vibe/strategy/{id}`
- [x] Comparison mode — add/remove results side-by-side
- [x] Parameter optimization endpoint — grid search with 100-combo cap + `gc.collect()` between iterations
- [ ] Multi-pair / multi-exchange backtest
- [ ] TA indicator support in Strategy Lab edge search (RSI, SMA, etc.)
- [ ] Live trading adapter (Hyperliquid)

### Notes
- VibeTrading architecture adapted for candle-analytics data sources (SQLite/OHLCV)
- Rust lib provides 50-100x faster indicator computation vs pandas
- Two LLM modes: Auto (Groq/Qwen) for quick generation, Expert (OpenCode terminal) for advanced
- Templates work without any API key — zero dependency

---

## 2026-05-24 — Session 016 : Vibe Lab chat ES5 fixes + WS restart + code_generated type handler

**Duration** : ~2h  
**Context** : User reported chat send button broken, WS disconnected, tabs 2/3 non-functional. Root causes found and fixed across JS, server processes, and WS message protocol.

### Fixed
- **Server stale process** — uvicorn PID 2677827 had been started before `routes.py` was modified; `/api/ws/vibe-chat` and `/api/ws/strategy-chat` returned 404 for all WebSocket connections. Killed and restarted with `setsid` + `disown`.
- **JS ES5 incompatibility** — 78 `const`/`let` declarations, 5 `?.` optional chaining operators, 3 `for...of` loops (with destructuring), and 1 `NodeList.forEach` call all converted to ES5-compatible syntax (`var`, manual null checks, standard `for` loops).
- **`handleWSMessage()` type check** — The WS handler at `routes.py:672` sends `{"type": "response", "id": req_id, **data}` where `data` from the agent response file has `{"type": "code_generated", ...}`. The `**data` spread overwrites `type`, so the browser receives `type: "code_generated"` but the JS handler only checked `data.type === 'response'`. The response was silently ignored — no code appeared in Tab 2. Added `data.type === 'code_generated'` to the condition.
- **Vibe agent missing `load_dotenv()`** — standalone `api/vibe_agent.py` didn't load `.env`, so `GROQ_API_KEY` was always empty. Added `load_dotenv(dotenv_path=...)` at module top (before `os` import).

### Changed
- **`api/vibe_lab.py`** — Full ES5 conversion of ~700 lines of JS:
  - `let`/`const` → `var` (78 instances)
  - `?.` → manual `&&` guard checks (5 instances)
  - `for...of` → indexed `for` loops with `Object.keys()` (3 loops)
  - `NodeList.forEach` → standard `for` loop in `switchTab()` and `exportChat()`
  - `handleWSMessage()` accepts `data.type === 'response' || data.type === 'code_generated'`
- **`api/routes.py`** — No change needed (WS handler correct, just needed restart)
- **`api/vibe_agent.py`** — Added `from dotenv import load_dotenv; load_dotenv(...)` before other imports

### Verified working
- WebSocket `/api/ws/vibe-chat` connects and accepts messages ✅
- Vibe agent (screen session) processes requests via Groq and returns `code_generated` responses ✅
- Full flow tested: HTTP fallback POST → agent generates code → response with `type: code_generated` + `code` field ✅
- Strategy Lab WS `/api/ws/strategy-chat` also works ✅
- Server endpoints `/vibe/validate` and `/vibe/run` respond correctly ✅

### Files changed
- `api/vibe_lab.py` — ES5 conversion, type handler fix
- `api/vibe_agent.py` — added `load_dotenv()`

### Problems encountered
| Problem | Solution |
|---------|----------|
| WS returned 404 on both `/api/ws/vibe-chat` and `/api/ws/strategy-chat` | Killed stale uvicorn process (PID 2677827) and restarted |
| Code generated but never appeared in Tab 2 | `handleWSMessage()` didn't accept `type: 'code_generated'` — only `'response'` |
| Vibe agent responded "Groq API not responding" despite valid key | Missing `load_dotenv()` in standalone script |
| Send button non-functional in older browsers | Removed `?.` optional chaining operator |
| Whole script could fail from `for...of` with destructuring on older engines | Converted all `for...of` to indexed `for` loops |

---

## 2026-05-24 — Session 019 : Vibe Lab chat fix + Strategy Lab Groq auth

**Duration** : ~1h  
**Context** : Fixed Vibe Lab "still waiting" (messages `type:message` ignorés), Strategy Lab "Groq API not responding" (load_dotenv manquant), processus zombie, rate-limit retry.

### Fixed
- **Vibe Lab `handleWSMessage()`** — Ajouté `data.type === 'message'` (ligne 800). Jusque là, seuls `'response'` et `'code_generated'` étaient acceptés. Toutes les réponses conversationnelles de l'agent (et les messages d'erreur Groq) étaient silencieusement avalées par le navigateur.
- **Strategy Lab agent.py** — Ajouté `load_dotenv()` avec hardcoded path. Le script standalone n'avait aucun chargement du `.env`, donc `GROQ_API_KEY` était toujours vide.
- **Processus zombie** — Tué l'ancien vibe-agent (PID 2773598, hors screen) qui consommait les requêtes en parallèle et doublait le rate-limit Groq.
- **Rate limit 429** — Ajouté 3 tentatives avec backoff exponentiel dans `vibe_agent.py:call_groq()` (identique à `generator.py`).
- **Logging dupliqué** — Supprimé `_log_vibe_chat()` de `routes.py` ; importé `_log_vibe` depuis `vibe_lab.py` à la place.

### Problems encountered
| Problem | Solution |
|---------|----------|
| Vibe Lab "still waiting" — agent répond mais rien n'apparaît | `handleWSMessage()` ignorait `type:"message"` — ajouté à la condition |
| Strategy Lab "⚠️ Groq API not responding" | `agent.py` n'avait pas `load_dotenv()` — ajouté avec path hardcodé |
| Vieux vibe-agent en double | Killé le PID hors screen |
| Rate limit 429 sans retry dans vibe_agent | Ajouté boucle 3 tentatives avec backoff |

### Files changed
- `api/vibe_lab.py` — handleWSMessage accepte `type: "message"`
- `api/vibe_agent.py` — retry 429
- `api/agent.py` — load_dotenv() ajouté
- `api/routes.py` — _log_vibe_chat supprimé, import _log_vibe
- `ERRORS.md` — 2 entrées ajoutées

---

## 2026-05-24 — Session 018 : Performance + UI upgrade (both labs)

**Duration** : ~3h  
**Context** : Fix chat textarea height reset, Vibe Lab acceleration (max_tokens 4096→2048 + poll 30→60), Strategy Lab spinner styling + template-to-input improvements.

### Fixed
- **JS syntax errors (both labs)** — 4 occurrences of `\'` inside Python `"""..."""` triple-quoted strings → Python interprets `\'` as `'`, producing raw single quotes that break JS string delimiters. Fixed: `vibe_lab.py:1233,1236,1314` (loadStrategy/deleteStrategy onclick + split newline), `strategy_lab.py:1018` (switchRtab onclick).
- **Chat textarea height** — After sending a message, `input.value = '';` cleared the text but the `<textarea>` stayed at the expanded height from auto-resize. Added `input.style.height = 'auto';` after value reset in both `vibe_lab.py:831` and `strategy_lab.py:615`.
- **Vibe Lab slowness + code never in Tab 2** — Two root causes: (1) `max_tokens: 4096` forced Groq to generate 4x more tokens than Strategy Lab (1024), taking 40-50s per request. (2) The backend WS poll loop `_vibe_poll_and_send()` only waited 30 iterations (30s), but Groq timed out at 60s — the response file arrived after polling ended and was silently lost. Fixed: `vibe_agent.py:133` max_tokens 4096→2048; `routes.py:665` poll range 30→60.

### Changed
- **Strategy Lab number spinners** — Added CSS for `::-webkit-inner-spin-button` and `::-webkit-outer-spin-button`: visible background (`#0f3460`), border-left, hover state. Widened all number inputs: `.cond-row input[type=number]` 70→90px, `.action-row input[type=number]` 60→80px, plus inline inputs (Min occ 50→65px, WF 40→55px, MC 55→70px) with `padding-right: 22px` to prevent number/spinner overlap.
- **Strategy Lab template inputs** — Placeholder `"val"` → `"ex: 25"` with `title` showing metric name + description. Alternating group border colors (4-color cycle: `#e94560`, `#26a69a`, `#7b1fa2`, `#f9a825`). AND/OR badge with green (AND) / orange (OR) background + `switchGroupLogic()` function that updates badge on selector change.

### Files changed
- `api/vibe_lab.py` — textarea height reset, JS quoting fixes
- `api/strategy_lab.py` — textarea height reset, JS quoting fix, spinner CSS, wider inputs, group colors/badges, better placeholders, switchGroupLogic function
- `api/vibe_agent.py` — max_tokens 4096→2048
- `api/routes.py` — _vibe_poll_and_send range 30→60

### Problems encountered
| Problem | Solution |
|---------|----------|
| `loadStrategy('' + s.id + '')"` JS syntax error in rendered page | Changed `\'` → `\\'` in Python `"""..."""` string to produce escaped quote in JS |
| `split('\n')` Python string → actual newline in rendered JS | Changed `'\n'` → `'\\n'` in Python source |
| Inline `onchange` in addGroup had same quoting bug | Replaced inline handler with dedicated `switchGroupLogic()` function |
| Vibe Lab code never arrives in Tab 2 | WS poll only waited 30s, but Groq code generation takes 40-50s. Increased poll to 60 iterations + reduced max_tokens to 2048 |
| Textarea stays expanded after sending message | Added `input.style.height = 'auto'` in both sendChatMessage functions |

---

## 2026-05-24 — Session 017 : Chart.js `defer` + Strategy Lab ES5 conversion

**Duration** : ~1h  
**Context** : Chat "disconnected" et bouton Send inopérant dans les DEUX labs. Cause racine identifiée : CDN Chart.js blocant + ES6 dans Strategy Lab.

### Fixed
- **CDN Chart.js sans `defer`** — Ajouté `defer` à `<script src="...chart.js...">` dans `vibe_lab.py` et `strategy_lab.py`. Sans `defer`, le navigateur bloque le parsing HTML sur le téléchargement du CDN. Si le CDN est lent, tout le JS inline (chat, WS, envoi) ne s'exécute jamais.
- **Strategy Lab ES5 conversion** — 141 `const`→`var`, `let`→`var`, 2 `?.`→vérification manuelle, 12 `for...of`→boucles indexées, 4 `NodeList.forEach`→`for`.

### Files changed
- `api/vibe_lab.py` — ajouté `defer` au CDN Chart.js
- `api/strategy_lab.py` — ajouté `defer` au CDN Chart.js + conversion ES5 complète

---

## 2026-05-22 — Session 002b : Session export/import commands

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

---

## 2026-05-25 — Session 021 : Rust indicators expansion + backend integration + condition interpret + UI

**Duration** : ~3h  
**Context** : Extended the Rust indicator library with 5 new indicators, integrated all 18 pre-computed indicators into the backend search pipeline, added a free-text condition interpretation API, updated the frontend condition parser, and built the Engine Search Group UI with auto-mode for RunSearch.

### Added
- **A1 — 5 new Rust indicators** in `vibe_engine/src/indicators.rs`:
  - ADX (Average Directional Index), CCI (Commodity Channel Index), MFI (Money Flow Index), Williams %R, OBV (On-Balance Volume)
  - Python bindings in `lib.rs` via PyO3
  - All 5 unit-tested via `maturin develop --release` and Python import
- **B1 — Backend integration** in `api/_agent/edge_engine.py`:
  - `_fetch_and_prepare` now pre-computes all 18 indicators using `vibe_engine` (existing 8 + 5 new + 5 meta metrics)
  - `_eval_cond` updated with alias-based indicator key resolution (maps "rsi" → "rsi_14", "adx" → "adx_14", etc.)
  - `FilterCondition` model expanded with `params` (dict for period, stddev, etc.) and `output` (indicator column name) fields
- **B2 — `/api/conditions/interpret` endpoint** (`api/routes.py`):
  - POST endpoint that parses free-text condition strings (e.g. "rsi(14) < 30", "adx > 25", "sma(20) > sma(50)")
  - Regex-based parsing for `metric(period) op value` format
  - AI fallback via Groq for complex expressions
  - Returns structured `FilterCondition[]` with resolved indicator keys
- **A2 — Frontend condition input** (`api/strategy_lab.py`):
  - `parseCondInput()` handles `metric(period) op value` format
  - Serializes `params` (period, stddev, etc.) into condition data
  - Enables direct text input alongside the group builder UI
- **C1 — Engine Search Group UI** (`api/strategy_lab.py`):
  - New collapsible section between header and trade area
  - Lookahead (LA) selector, Minimum Occurrences (MinOcc), Monte Carlo Shuffles count
  - Walk-Forward toggle with windows + train% inputs
  - Train/Backtest date range pickers
  - Sweep toggle (auto grid search over conditions)
- **D — RunSearch auto-mode** (`api/strategy_lab.py`):
  - `getSearchConfig()` now auto-includes `walk_forward` and `monte_carlo_shuffles` in every search request
  - Results auto-show WF and MC tabs when data is present

### Changed
- **`vibe_engine/src/indicators.rs`** — added ADX, CCI, MFI, Williams %R, OBV functions
- **`vibe_engine/src/lib.rs`** — registered all 5 new indicators as Python-callable functions
- **`api/_agent/edge_engine.py`** — `_fetch_and_prepare` uses 18 indicators; `_eval_cond` uses alias resolution; `FilterCondition` extended
- **`api/routes.py`** — added `/api/conditions/interpret` POST endpoint
- **`api/strategy_lab.py`** — `parseCondInput()` updated, Engine Search Group UI added, `getSearchConfig()` auto-mode

### Problems encountered
| Problem | Solution |
|---------|----------|
| CCI high/low bands depend on asset volatility — fixed 100/‑100 not universal | Used TA standard: +100/‑100 as default thresholds, documented as configurable via `params` |

### Notes
- The Rust engine now provides 13 pure technical indicators (RSI, SMA, EMA, BBANDS, ATR, MACD, Stoch, VWAP, ADX, CCI, MFI, Williams %R, OBV) + 5 OHLC metrics = 18 total
- Alias resolution in `_eval_cond` is case-insensitive and maps common names (e.g. "williams", "williams%r", "%r") to the canonical column
- The `/api/conditions/interpret` endpoint uses regex first, LLM fallback second — no AI dependency for simple patterns

---

## 2026-05-25 — Session 022 : 4 piliers Strategy Lab — Parcourir indicateurs, calcul à la volée, AI ✨, validation conditions

**Duration** : ~4h  
**Context** : Implémentation de 4 fonctionnalités majeures dans le Strategy Lab : explorateur d'indicateurs (modal Parcourir), calcul on-the-fly des indicateurs custom, boutons AI ✨ sur chaque input, et validation des conditions avant Run Search. Corrections de bugs (orphan duplicate code, ES6 spread operator, positionnement des ✨, bug WS `**data`).

### Added

- **Pilier A — Explorateur d'indicateurs (modal Parcourir)** :
  - `GET /api/conditions/catalog` endpoint retournant `CONDITION_REGISTRY` hiérarchisée
  - Bouton `📊` Parcourir à côté de chaque input condition
  - Modal avec sidebar catégories → liste indicateurs → métriques détaillées
  - CSS : `.modal-overlay`, `.modal-content`, `.modal-cats`, `.modal-ind-item`, `.modal-metric-item`, `.btn-browse`
  - JS : `openConditionBrowser()`, `closeConditionBrowser()`, `renderCatalogCategories()`, `renderCatalogCategory()`, `addFromCatalog()`

- **Pilier B — Calcul à la volée des indicateurs custom** :
  - `_INDICATOR_FUNCS` (dict global metric → lambda compute) pour RSI, SMA, EMA, BBANDS, ATR, MACD, Stoch, VWAP, Williams %R, OBV, CCI, MFI, ADX
  - `_get_indicator_funcs()`, `_compute_indicator_on_demand()`
  - Pré-calcul des périodes communes dans `_compute_indicators()` (RSI 7/14/21, SMA 10/20/50/200, etc.)
  - Stockage `__raw__` (high/low/close/volume) pour calcul on-demand
  - Refacto `_eval_cond()` → `_resolve_indicator()` avec cache dans `indicators`

- **Pilier C — AI ✨ sur chaque input** :
  - `POST /api/edge/suggest` endpoint avec `SuggestRequest`/`SuggestResponse`
  - Bouton ✨ sur 12 champs : cfgName, cfgLeverage, cfgLookahead, cfgMinOcc, cfgMCShuffles, cfgWFWindows, cfgWFTrainPct, cfgStartDate, cfgEndDate, conditions, order size, order price
  - CSS : `.ai-suggest-btn`, `.ai-suggest-popover`, `.ai-suggest-item`
  - JS : `showAISuggest()`, `_closeSuggestPopover()`, `applySuggest()`
  - `ef-row` wrapper pour aligner ✨ horizontalement avec l'input

- **Pilier D — Validation des conditions avant Run Search** :
  - `_validate_conditions()` dans `routes.py` vérifie chaque métrique vs `FLAT_REGISTRY`
  - `_run_single_search()` retourne erreur descriptive avec les conditions invalides
  - Frontend `runSearch()` affiche `data.error` dans le status

### Changed
- **`api/strategy_lab.py`** — LAB_HTML : modal Parcourir, ✨ buttons, AI Suggest JS, cond-row/order-row/engine-field layout
- **`api/routes.py`** — `_validate_conditions()`, `_poll_and_send()` fix **data order, suggest endpoint
- **`api/condition_registry.py`** — (used by catalog endpoint)

### Fixed
- **Orphan duplicate code** `api/strategy_lab.py:1164-1205` — `SyntaxError: Illegal return statement` cassait tout JS
- **ES6 spread operator** `[...new Set(...)]` → ES5 manual loops (3 occurrences)
- **`paramsSection` visibility** — remis à `display: none` (revert changement non demandé)
- **✨ button position** — wrapper `ef-row` (`inline-flex`) pour aligner horizontalement input+✨ dans engine-fields
- **Bug WS `**data`** — `routes.py:1173,1195` : `{"type": "response", **data}` → `{**data, "type": "response"}` pour que le type serveur surcharge le type agent. Appliqué aux 2 `_poll_and_send()`

### Known Residue
- WS "disconnected" peut persister si processus agent dupliqué — tuer les zombies avec `kill $(pgrep -f api/agent.py)`
- Les processus agent/vibe-agent peuvent montrer count=2 à cause de threads internes

### Notes
- `getConfigFromChat()` et `showDefaultConfig()` coexistent — la config par défaut charge via `renderConfig()` qui set `display: block`, donc `#paramsSection` est visible au load malgré `display:none` CSS
- La correction `**data` était déjà faite côté JS pour vibe_lab (Session 016-017) mais pas côté serveur — les deux `_poll_and_send` étaient encore buggés

---

## 2026-05-25 — Session 023 : Nettoyage structure projet + audit skill global

**Duration** : ~1h  
**Context** : Réorganisation complète de la structure du projet : déplacement des fichiers, renommage des dossiers, mise à jour de tous les chemins, création d'un skill global `project-audit`.

### Changed
- **`sessions_upload/`** — reçoit les 3 `session-ses_*.md` qui traînaient à la racine
- **`USERS DOCUMENT/`** → **`USERS_DOCUMENT/`** — renommé (suppression de l'espace, compatible CLI)
- **`USERS DOCUMENT/NOTES_FOR_LATER/`** — renommé (suppression de l'espace)
- **`USERS_DOCUMENT/synthesis/`** — nouveau dossier : reçoit `synthesis-project-2026-05-24.md` depuis `sessions_upload/`
- **`.gitignore`** — ajouté `target/`, `.venv/`, `sessions_upload/`
- **`ARCHITECTURE.md`** — ajouté header pointant vers `USERS_DOCUMENT/project-docs/`
- **Tous les `.md` et `.py`** — `USERS DOCUMENT` → `USERS_DOCUMENT` (chemins mis à jour)

### Added
- **Skill global `project-audit`** — `~/.config/opencode/skills/project-audit/SKILL.md`
  - 6 phases : tree scan → dependency audit → git audit → doc sync → file organization (avec update paths) → improvement proposals
  - Quick reference, output format, checklist items
  - Détecté automatiquement par opencode (dossier dans `~/.config/opencode/skills/`)

### Fixed
- **Chemins obsolètes** — 7 fichiers mis à jour : `api/strategy_lab.py`, `RULES.md`, `session-lifecycle/SKILL.md`, `CONVENTIONS.md`, `TEMPLATES.md`, `synthesis-project-2026-05-24.md`, `ARCHITECTURE.md`
- Les transcripts historiques (`sessions_upload/session-ses_*.md`) conservent leurs anciens chemins (archives)

### Notes
- Aucune suppression — seulement des déplacements et renommages
- Le skill `project-audit` est global (pas limité à ce projet) : placé dans `~/.config/opencode/skills/`
- Prochaine étape : Phase Cleanup détaillée dans ROADMAP.md

---

## 2026-05-25 — Session 018 : Fix JS quoting, skills infra, GitHub backup

**Duration** : ~1h  
**Context** : STRAT LAB send broken, chat input invisible; création skills infra

### Fixed
- **JS SyntaxError dans strategy_lab.py** — Python `\'` dans `"""..."""` produit `'` sans backslash, cassant 3 onclick handlers (`selectCatalogCategory`, `addFromCatalog` ×2). Changé `\'` → `\\'` dans la source Python.
- **Toute la page Strategy Lab** — Le bloc `<script>` entier ne parsait plus à cause de l'erreur syntaxique : send button, WebSocket, chat input, tout était mort.

### Added
- **Skill `github-backup`** — `.opencode/skills/github-backup/SKILL.md` : backup automatisé vers GitHub avec commit + push SSH (fallback HTTPS token)
- **Skill `subagent-cache`** — `.opencode/skills/subagent-cache/SKILL.md` + `scripts/cache-subagent.sh` : sauvegarde timestampée des résultats sub-agent pour éviter de re-exécuter
- **Skill `pyjs-quote-debug`** — `.opencode/skills/pyjs-quote-debug/SKILL.md` + `scripts/check-pyjs-quotes.sh` : détection automatique des bugs de quoting Python→JS
- **Documentation par page** — `USERS_DOCUMENT/project-docs/pages/{dashboard,strategy-lab,vibe-lab,analyze}.md`

### Added (suite)
- **Sécurité external sources** — guide dans `AGENTS.md` avec classement : OpenSSF Scorecard ★★★★★, Trivy ★★★★★, Semgrep ★★★★, Bandit ★★★
- **Token GitHub redacted** — `ghp_*` retiré de l'historique git via `git filter-repo`, sauvegardé localement dans `.opencode/local/`
- **GROQ API validé** — testé avec requête réelle envoyée au Strategy Lab agent → réponse `config_update` reçue en 15s
- **Pre-commit hook réparé** — utilisait `python3` au lieu de `bash` pour lancer `check-pyjs-quotes.sh`

### Fixed (suite)
- **GitHub push secret scan** — le token PAT dans `sessions_upload/session-ses_1b00.md` bloquait le push. Solution : `git filter-repo` + redirection URL GitHub + re-push
- **Pre-commit const check** — le hook naïf détectait les `const` JS dans différentes fonctions comme des redeclarations. Solution : utiliser `check-pyjs-quotes.sh` qui extrait le JS et le valide avec `node --check`

### Notes
- ERRORS.md mis à jour avec l'entrée JS quoting fix + script de vérification
- Tous les scripts skills sont exécutables et testés
- 16 fichiers Python passent le check-pyjs-quotes.sh
- Projet entier commité et pushé sur GitHub : `git@github.com:Noelas-Saensch/candle-analytics.git`
- Session exportée automatiquement dans `sessions_upload/auto-export-*.md`
