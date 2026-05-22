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
