# CANDLE-ANALYTICS — ROADMAP

> **Mission** : Fetch OHLCV data from CEX (Binance) and DEX (Hyperliquid).  
> Store locally (SQLite + CSV) and serve via CLI and/or FastAPI.  
> Designed for local use (manual backfill) and server deployment (H24 cron).

---

## PAIRS

| Pair | Binance | Hyperliquid | Status |
|------|---------|-------------|--------|
| BTC/USDC | BTCUSDC | TBD | ✅ active |
| GOLD/USDC | PAXGUSDC | PAXGUSDC | ✅ active |
| EURC/USDC | ❌ no pair | TBD | ❌ abandoned |

> **Note**: USDT pairs forbidden by French regulation. Only USDC pairs used.

---

## TIMEFRAMES

Supported: `1m, 5m, 15m, 30m, 1H, 2H, 4H, 6H, 12H, 1D, 2D, 3D, 1W, 2W, 1M, 2M, 3M, 4M, 6M, 1Y`

**Default**: `1m`, `1H`, `1D`

---

## TASKS

### 🟢 To Do
- [ ] Hyperliquid client implementation (check available endpoints)
- [ ] WebSocket support for real-time candle updates
- [ ] Dockerfile + docker-compose for server deployment
- [ ] Dashboard (simple web UI for candle visualisation)
- [ ] Multi-user API key management

### ✅ Done
- [x] Project scaffold (dirs, .env, .gitignore, requirements.txt)
- [x] ROADMAP.md + CHRONOLOGIE.md created
- [x] Core config & models (pydantic-settings, OHLCV schema)
- [x] Binance client (public klines API, no key needed)
- [x] SQLite storage (ohlcv table + indexes)
- [x] CSV export
- [x] Fetcher orchestrator
- [x] CLI entry point
- [x] FastAPI server + routes
- [x] Backfill script (last 5000 bars per default TF)
- [x] Cron doc template
- [x] opencode skill + command (candle-fetch)
- [x] Git init (push blocked — expired token)
- [x] session-export command + skill
- [x] session-import command

### 🔄 Modified
- *(none yet)*

### ❌ Abandoned
- EURC/USDC on Binance — pair does not exist

---

## RULES

1. **No USDT** — French regulation forbids it. USDC only.
2. **Public endpoints first** — klines don't need API keys.
3. **SQLite + CSV dual storage** — structured queries + portability.
4. **One CLI to rule them** — `python -m candles` handles fetch, backfill, server.
5. **Every session logged** — see CHRONOLOGIE.md.
6. **Sessions auto-saved** — use `/session-export` to save full AI session to `sessions_upload/`.
