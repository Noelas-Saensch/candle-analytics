# Frontend — candle-analytics

All UIs are **inline HTML/JS in Python f-strings** — no build step, no framework.

## Pages

| Route | File | Library | Features |
|-------|------|---------|----------|
| `/dashboard` | `api/dashboard.py` | TradingView Lightweight Charts + Chart.js | 6 chart families (Distribution, Time Series, Correlation, Percentile, Pattern, Overlay), RAW DATA table, live crosshair, volume histogram, regression line |
| `/analyze` | `api/analyze.py` | None (styled table) | Percentile rank analysis, 7 OHLC metrics |
| `/strategy-lab` | `api/strategy_lab.py` | Chart.js (results) | 4-panel: Chat ↔ Parameters (with Engine Search Group) ↔ Conditions (3-chip input) ↔ Results (Edge, Sweep, WF, MC, Export) |
| `/vibe-lab` | `api/vibe_lab.py` | Chart.js (equity curve) | 3-tab: Describe ↔ Code ↔ Results (backtest metrics, LLM analysis, comparison) |

## JS conventions

- **ES5 only** — `var`, function expressions, no arrow functions, no `?.`, no `for...of`, no `NodeList.forEach`, no template literals
- All JS is inline in `<script>` at bottom of `<body>`
- CDN scripts use `defer` attribute
- DOM queries via `document.getElementById` / `querySelectorAll`

## Chart families (dashboard.py)

| Family | Chart types | Render function pattern |
|--------|-------------|------------------------|
| Distribution | Histogram, KDE, Box plot | `(ctx, canvas, data, activeMetrics, getFamParam, famId)` |
| Time Series | Line, Area, Scatter, Heatmap | same |
| Correlation | Heatmap, Scatter matrix | same |
| Percentile | Gauge, Timeline, Table | same |
| Pattern | Recurrence, Sequence, Cluster | same |
| Overlay | Multi-metric, Raw price, Volume | same |

## Cache strategy

1. `sessionStorage` cache for API responses
2. In-memory cache (JS object)
3. Background prefetch on page load
4. `/api/candles/count` light check before full fetch
