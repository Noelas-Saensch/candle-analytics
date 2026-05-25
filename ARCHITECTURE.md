# Candle-Analytics — Architecture

> **Note** : Cette vue d'ensemble est simplifiée. Voir `USERS_DOCUMENT/project-docs/` pour les docs détaillés :
> - `ARCHITECTURE.md` — architecture complète (data flow, layers, IPC, screen sessions)
> - `API.md` — tous les endpoints REST + WebSocket
> - `AGENTS.md` — agents LLM (Strategy Lab, Vibe Lab)
> - `FRONTEND.md` — SPA architecture
> - `STRATEGY_ENGINE.md` — système de conditions et edge search
> - `pages/` — per-page docs (dashboard, strategy-lab, vibe-lab, analyze)

## Stack

| Layer | Technology |
|-------|-----------|
| API server | FastAPI (Python 3.13) |
| Data storage | SQLite (`data/candles.db`) + CSV (`data/csv/`) |
| Chart rendering | Lightweight Charts (TradingView) — browser-side |
| Deployment | Docker (python:3.13-slim) + docker-compose |
| WebSocket streaming | Binance/Hyperliquid real-time feeds |

## Server Structure

```
api/
├── main.py          # FastAPI app, CORS, lifespan, router registration
├── routes.py        # REST endpoints: /api/candles, /api/pairs, /api/fetch
├── dashboard.py     # SPA with tabbed UI: Chart + Analyze views
└── analyze.py       # Analyze API: /api/analyze/data (percentile computation)

candles/
├── config.py        # pydantic-settings (env vars, pairs, timeframes)
├── fetcher.py       # Orchestrator: fetch & store (pairs → exchange clients)
├── clients/
│   ├── binance.py   # Binance klines API client (pagination, backfill)
│   └── hyperliquid.py # Hyperliquid candleSnapshot client
├── storage/
│   └── db.py        # SQLite CRUD (query_candles, save_candles, get_available_pairs)
├── stream/
│   ├── handler.py   # WebSocket handlers (Binance + Hyperliquid)
│   └── runner.py    # Stream orchestrator with auto-reconnect
└── models.py        # OHLCV Pydantic model
```

## Data Flow

```
Exchange API (Binance/Hyperliquid)
    ↓ fetch_klines / candleSnapshot
Fetcher orchestrator
    ↓
SQLite (INSERT OR REPLACE) + CSV export
    ↓
FastAPI (/api/candles)
    ↓
Browser (Lightweight Charts + Analyze table)
```

## Site Navigation (SPA)

Single page at `/dashboard` with two tabs:

1. **Chart** — Candlestick + Volume histogram, price auto-scale
2. **Analyze** — Percentile rank table (OHLC metrics in % from OPEN)

Both tabs share the filter bar (exchange, pair, timeframe, date range).
Analyze tab adds a metric filter dropdown.

## REST API

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/api/candles` | exchange, symbol, timeframe, limit, start_time, end_time | Query stored candles |
| GET | `/api/pairs` | — | List available (exchange, symbol, timeframe) combinations |
| POST | `/api/fetch` | exchange, symbol, timeframe, limit, start_time, end_time | Fetch & store from exchange |
| GET | `/api/health` | — | Server status + configured pairs/timeframes |
| GET | `/analyze/data` | exchange, symbol, timeframe, limit, start_time, end_time | Candles with % metrics + percentile ranks |
| GET | `/dashboard` | — | Tabbed SPA (Chart + Analyze) |
| GET | `/analyze` | — | Standalone analyze page (direct access) |

## Key Design Decisions

- **USDC only** — No USDT (French regulation). Pairs use USDC quote.
- **Dual storage** — SQLite for queries, CSV for portability/backup.
- **Metrics pre-computed at insert time** — All 7 OHLC metrics (OC%, OH%, OL%, HL%, HC%, LC%, Vol%) are computed during `save_candles()` and stored as `metrics TEXT` JSON. Avoids server-side recomputation on every `/api/candles` query.
- **Percentiles pre-computed in DB** — Stored as `percentiles TEXT` JSON, backfilled on server startup for the last N candles (configurable via `BACKFILL_PCTL_BARS`). Client can also recompute locally from `metrics` values.
- **Percentiles removed from server API** — `/analyze/data` no longer computes percentiles server-side; client computes from `metrics` values in JS for the active working set.
- **Per-family chart type system** — 6 families (Distribution, Time Series, Correlation, Percentile, Pattern, Overlay), each with its own chart type `<select>` and per-metric checkboxes.
- **Client-side data caching** — In-memory cache (`_cachedCandles`, `_cacheKey`) shared across tabs. Plans to move to `sessionStorage` for persistence across page refreshes.
- **Background data prefetch** — `prefetchAnalyze()` runs after chart loads to pre-load Metrics/RAW DATA data before user switches tabs.
- **Time window** — Date pickers control chart range; no candles-limit dropdown.
- **Dark theme** — `#1a1a2e` background, `#e94560` accent.
