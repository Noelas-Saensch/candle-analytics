# Analyze (`/analyze`)

**Purpose:** A standalone percentile-rank analysis page that displays OHLCV candles with computed metrics (OH%, OL%, HL%, HC%, LC%, OC%, Vol%) and their percentile rankings in a sortable table.

---

## Layout

A single-page table view with a controls bar at the top:

- **Controls bar**: Exchange / Pair / Timeframe selectors, Date range pickers (from/to), Metric filter dropdown (OC%, OH%, OL%, HL%, HC%, LC%, Vol%, or "All"), "Load" button
- **Status line**: Shows count of loaded candles
- **Main table**: Scrollable (max-height `calc(100vh - 160px)`) with sticky headers
  - Columns: Date, Open, Close, then for each active metric: Metric value (colored green/red based on sign) and Percentile rank (%)
- **Footer**: Explanatory text: "Metrics are % distance from OPEN. Percentile rank = % of candles with lower value."

---

## Key Features

- **Percentile ranking** for each metric computed on the fly: each candle's metric value is ranked against all candles in the loaded dataset
- **Metric filter**: Choose a single metric (OC%, OH%, OL%, etc.) or view all metrics at once
- **Sortable columns**: Click any column header to sort ascending/descending (toggle direction on re-click)
- **Date range filtering**: Filter candles by start/end date before loading
- **Color-coded metrics**: Positive values shown in green (`#26a69a`), negative in red (`#ef5350`)
- **Percentile column** for each metric shows what percentage of candles have a lower value
- Standalone page linked from the Dashboard header (`← Chart`)

---

## API Routes

### Endpoints served by this page's router (`api/analyze.py`)

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/analyze` | Returns the Analyze HTML page |
| GET | `/analyze/data` | Returns OHLCV candles with pre-computed metrics and percentile ranks |

### The `/analyze/data` endpoint:
- **Parameters**: `exchange`, `symbol`, `timeframe` (required); `start_time`, `end_time` (optional int ms); `limit` (optional, default 99999)
- **Response**: `{"count": N, "candles": [...]}` where each candle has:
  - `t` (timestamp), `o`, `h`, `l`, `c`, `v` (OHLCV)
  - `metrics` object: `{ oc, oh, ol, hl, hc, lc, vol }` — all computed as % distance from OPEN
  - `percentiles` object: percentile rank for each metric (computed server-side only if stored in DB, otherwise computed client-side)

### Endpoints consumed from `api/routes.py` (prefix `/api`)

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/pairs` | List available exchange/symbol pairs |

---

## Dependencies

| Library / Resource | Usage |
|--------------------|-------|
| FastAPI | Server-side route handler |
| SQLite (via `candles.storage.db.query_candles`) | Data retrieval |
| Python `json` | Stored metrics deserialization |

**No external JavaScript libraries** — the page is pure HTML/CSS/vanilla JS with no framework dependencies.

---

## Chat / WebSocket Info

The Analyze page does **not** use WebSocket or chat. It is a simple data-query-and-display page.

---

## Known Issues (from ERRORS.md)

No entries in ERRORS.md specifically reference the `/analyze` page. However, note that:

- The `/analyze/data` endpoint is the **same endpoint** used by the Dashboard's Metrics and RAW DATA tabs (via `ensureDataLoaded()`). Any data pipeline issues (e.g., empty percentiles, missing computed metrics) apply here as well.
- Percentile ranks shown on this page are computed **client-side** using simple percentile ranking (count of values less than current value / total * 100) — this differs from the server-side percentile computation and may produce slightly different results for very small datasets.
