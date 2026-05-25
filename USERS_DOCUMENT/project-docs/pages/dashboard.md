# Dashboard (`/dashboard`)

**Purpose:** The main landing page providing a real-time candlestick chart, a metric-analysis tab with percentile-based statistics and visualization families, and a raw data table with column filters and sorting.

---

## Layout

The page has a header bar with navigation tabs and market controls, and three main sub-views toggled by the tabs:

| Tab | View ID | Content |
|-----|---------|---------|
| **Chart** | `chart-view` | Interactive candlestick chart (LightweightCharts) with volume histogram, linear regression overlay, and SSE live updates |
| **Metrics** | `analyze-view` | Percentile-based "Info Array" table with threshold buckets + stacked visualization family charts (Distribution, Time Series, Correlation, Percentile, Pattern, Overlay) |
| **RAW DATA** | `rawdata-view` | Paginated sortable/filterable table of OHLCV candles with metric values and percentile columns |

**Header bar contains:**
- App title ("candle-analytics") and tab navigation
- Exchange / pair / timeframe selectors
- Date range pickers (from/to)
- Regression toggle checkbox
- "Update" button (fetches last 5000 candles) and "Fetch all" button
- Sub-controls for the Metrics tab: MAX LAST BAR input, metric checkboxes (OC%, OH%, OL%, HL%, HC%, LC%, Vol%)

---

## Key Features

- **Interactive Candlestick Chart** using LightweightCharts (TradingView-style) with:
  - OHLCV candlestick series + volume histogram
  - Linear regression line overlay (toggleable via "Reg" checkbox)
  - Auto-scale and fit-content buttons
  - Localized time formatting (Europe/Paris, French locale)
  - Crosshair with visible labels
  - SSE (Server-Sent Events) real-time updates — new candles streamed as they arrive
- **Multi-layered caching**: in-memory cache, sessionStorage cache, lightweight count-check before full fetch
- **Metrics Analysis** tab with:
  - "Info Array" — a percentile-threshold table showing Bull/Bear %, stats (min, median, max, mean), and concurrence percentages for each selected metric at configurable thresholds (top 1%, 2%, 3%, 5%, 10%)
  - Editable/addable/removable thresholds (max 5)
  - Reorderable metric columns
- **Six visualization families** (each with sub-types) rendered using Chart.js:
  - *Distribution*: Histogram, Box plot, CDF, QQ-plot, KDE, Violin plot
  - *Time Series*: Metric line, Rolling stats, Bollinger bands, Bull/Bear by hour, Week pattern heatmap
  - *Correlation*: Scatter + regression, Correlation heatmap, Autocorrelation, Cross-correlation, Pair plot (SPLOM)
  - *Percentile*: Percentile curve, Rank corridor, Fan chart, Percentile table
  - *Pattern*: Volatility clustering, Regime histogram, Cluster scatter (k-means)
  - *Overlay*: Multiple metrics overlaid on one chart, with normalization and smoothing
- **RAW DATA tab** with:
  - Paginated display (100 rows per page, "Load more" button)
  - Sortable columns (click header to sort ascending/descending)
  - Column-based filtering via dropdown popovers (date search/range, direction bull/bear, OHLCV min/max, positive/negative only, percentile above)
  - Filters are composable across columns
- **Live data streaming** via SSE endpoint `/api/events` — chart updates automatically when new candles appear
- **Data fetching** from exchange APIs via `/api/fetch` POST endpoint (triggered by "Update" or "Fetch all")

---

## API Routes

### Endpoints used by the dashboard page

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/dashboard` | Returns the full dashboard HTML page |
| GET | `/api/pairs` | Lists available exchange/symbol pairs |
| GET | `/api/candles/count` | Returns candle count for a given pair/timeframe/date range |
| GET | `/analyze/data` | Returns OHLCV candles with pre-computed metrics and percentiles |
| POST | `/api/fetch` | Triggers fetching candles from the exchange (Update / Fetch all) |
| GET | `/api/events` | SSE endpoint: streams new candles in near real-time |

### External routes used (from `api/routes.py`)

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/candles` | Raw candle query endpoint |
| GET | `/api/candles/count` | Candle count endpoint |
| GET | `/api/pairs` | Available pairs list |
| GET | `/api/events` | Server-Sent Events stream |

---

## Dependencies

| Library / Resource | Version | Usage |
|--------------------|---------|-------|
| LightweightCharts (unpkg) | 4.1.3 | Candlestick chart rendering |
| Chart.js (CDN) | 4.4.7 | All statistical charts (distribution, time series, correlation, etc.) |
| chartjs-plugin-zoom (CDN) | 2.2.0 | Zoom + pan on statistical charts (wheel/pinch) |
| FastAPI | (project) | Server-side route handler |
| SessionStorage | (browser) | Client-side caching of candle data |

---

## Chat / WebSocket Info

The Dashboard does **not** use WebSocket or chat. Real-time updates are delivered via **Server-Sent Events (SSE)** at `/api/events` — a polling-based streaming endpoint that checks for new candles every 5 seconds. The JS `EventSource` connects on page load (when Chart tab is active) and updates the candlestick series in-place. On SSE disconnection, a 30-second auto-retry is triggered.

---

## Known Issues (from ERRORS.md)

- **2026-05-23**: RAW DATA table crashed on empty/missing percentiles — fixed by adding `c.percentiles = c.percentiles || {}` initializer in `renderRawTable()`. (See ERRORS.md entry for 2026-05-23)
- **2026-05-23**: Chart.js crosshair labels were invisible — `labelVisible` was not a valid property, fixed to `visible: true` with `labelBackgroundColor`.
- **2026-05-23**: Chart.js zoom could exceed data range — used `minRange` instead of correct `maxRange`, fixed.
- **2026-05-23**: Heatmap blurry on retina displays — added `devicePixelRatio` scaling.
- **2026-05-22**: Hyperliquid OHLCV endpoint was unclear — stubbed with `NotImplementedError`, later implemented.
