# Strategy Engine — candle-analytics

## Edge search (`/api/edge/search`)

1. Fetch candles from DB (up to 999999 limit)
2. For each candle, compute all 7 metrics + percentile ranks
3. Evaluate condition groups against each bar
4. For matching bars, compute forward return (N bars ahead)
5. Return: matches list, stats (win rate, avg return, Sharpe), distribution

### Request format

```json
{
  "exchange": "binance", "symbol": "BTCUSDC", "timeframe": "1H",
  "lookahead": 5, "min_occurrences": 10,
  "groups": [{"logic": "AND", "conditions": [
    {"metric": "oc", "op": "gt", "value": 0.5}
  ]}],
  "logic": "AND",
  "walk_forward": false, "monte_carlo_shuffles": 0
}
```

### Available metrics for conditions

- Direct: `oc`, `oh`, `ol`, `hl`, `hc`, `lc`, `vol`
- Percentile: `pctl_oc`, `pctl_oh`, `pctl_ol`, `pctl_hl`, `pctl_hc`, `pctl_lc`, `pctl_vol`
- Indicators (pre-computed with default params): `rsi`, `sma`, `ema`, `bbands_upper/middle/lower`, `atr`, `macd_line/signal/histogram`, `stoch_k/d`, `vwap`, `williams_r`, `obv`, `cci`, `mfi`, `adx`
- Operators: `gt`, `gte`, `lt`, `lte`, `eq`, `neq`
- Optional: `params` dict for indicator parameters (e.g. `{"period": 14}`), `output` for multi-output indicators

### Condition with indicator params

```json
{"metric": "rsi", "op": "lt", "value": 30, "params": {"period": 14}}
```

## Sweep (`/api/edge/sweep`)

Grid search over param values + lookahead values. 100-combo cap.

## Backtest (Vibe Lab sandbox)

`api/sandbox.py` — `StrategySandbox` class:
- Injects `decide(i, ohlcv)` function into restricted `exec()` environment
- Bar-by-bar simulation with position tracking
- Supports: long/short, SL/TP via sandbox functions
- Returns: equity curve, trades, metrics (Sharpe, Sortino, Calmar, win rate, profit factor, max DD)

## Vibe Engine (Rust → PyO3)

`vibe_engine/` — compiled with `maturin develop --release`:
- Indicators: `sma`, `ema`, `rsi`, `bbands`, `atr`, `macd`, `stochastic`, `vwap`, `williams_r`, `obv`, `cci`, `mfi`, `adx`
- Backtest: `run_backtest(signals, prices, ...)`
- Metrics: `compute_metrics(equity_curve)`

Injected into sandbox as `ve` for import-free access.

## Indicator condition resolution

Conditions use an alias map (stored as `indicators["__alias__"]`). When a condition has `metric: "rsi"`, it resolves via alias to `"rsi_14"` — the precomputed default-param version. Custom params (e.g. `rsi(7)`) build a key `"rsi_7"`; if absent, eval returns `False`.

## `/api/conditions/interpret` (POST)

Parses free-text condition strings into structured `FilterCondition` objects:

```
POST /api/conditions/interpret
{"text": "rsi(14) < 30", "group_context": ""}

→ {"metric": "rsi", "op": "lt", "value": 30, "params": {"period": 14}, "label": "RSI lt 30", "fuzzy": false}
```

Regex patterns first: `metric[(period)] op value`, `metric pctl N`. AI fallback via Groq if no match.
