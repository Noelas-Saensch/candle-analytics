# Data — candle-analytics

## SQLite schema (`ohlcv` table)

```sql
CREATE TABLE ohlcv (
  exchange TEXT NOT NULL,
  symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  open REAL NOT NULL,
  high REAL NOT NULL,
  low REAL NOT NULL,
  close REAL NOT NULL,
  volume REAL NOT NULL,
  metrics TEXT,         -- JSON: {"oc":..., "oh":..., "ol":..., "hl":..., "hc":..., "lc":...}
  UNIQUE(exchange, symbol, timeframe, timestamp)
);
```

## 7 OHLC metrics (computed at insert time)

| Key | Formula | Meaning |
|-----|---------|---------|
| `oc` | (close - open) / open * 100 | Body direction & size |
| `oh` | (high - open) / open * 100 | Upper wick from open |
| `ol` | (low - open) / open * 100 | Lower wick from open |
| `hl` | (high - low) / open * 100 | Total range |
| `hc` | (high - close) / open * 100 | Upper wick from close |
| `lc` | (low - close) / open * 100 | Lower wick from close |
| `vol` | volume / max_volume * 100 | Normalized volume (computed in API) |

## Percentiles

Computed server-side in `/api/edge/search` as percentile rank per metric per candle (bisect left on sorted values). Key: `oc` → `pctl_oc`, etc.

## Storage

- Primary: SQLite at `data/candles.db`
- Export: CSV at `data/csv/`
- Storage estimate (BTCUSDC full history): ~545 MB total (535 MB for 1m, 9 MB for 1H, negligible for 1D)

## Exchanges

| Exchange | Base URL | Auth | Rate limit |
|----------|----------|------|------------|
| Binance | `https://api.binance.com` | None (klines) | 1200/120s |
| Hyperliquid | `https://api.hyperliquid.xyz/info` | None (candleSnapshot) | ~20 weight/req |
