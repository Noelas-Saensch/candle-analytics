# Candle-Analytics — Architecture

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
- **Percentiles computed server-side** — `/api/analyze/data` returns pre-computed percentile ranks for all 7 metrics.
- **Time window** — Date pickers control chart range; no candles-limit dropdown.
- **Dark theme** — `#1a1a2e` background, `#e94560` accent.
