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
