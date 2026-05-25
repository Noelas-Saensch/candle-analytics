# Strategy Config Template — candle-analytics

## Config structure (AI fills this, user edits in Parameters panel)

```json
{
  "exchange": "binance",
  "symbol": "BTCUSDC",
  "timeframe": "1H",
  "direction": "long_only",
  "entry": {
    "order_type": "market",
    "conditions": {
      "logic": "AND",
      "groups": [
        {
          "logic": "AND",
          "conditions": [
            {"subcategory": "threshold", "metric": "oc", "op": "gt", "value": 0.5}
          ]
        }
      ]
    },
    "sizing": {"method": "percent_equity", "value": 1, "max_concurrent": 1}
  },
  "exit": {
    "take_profit": {"enabled": true, "order_type": "market", "value": 2, "sizing_method": "percent_position", "sizing_value": 100},
    "stop_loss": {"enabled": true, "order_type": "market", "value": 1, "sizing_method": "percent_position", "sizing_value": 100},
    "trailing_stop": {"enabled": false, "method": "percent", "value": 2, "sizing_method": "percent_position", "sizing_value": 100}
  },
  "lookahead": 5,
  "min_occurrences": 10,
  "start_time": null,
  "end_time": null,
  "walk_forward": {"enabled": false, "windows": 4, "train_pct": 70},
  "monte_carlo": {"enabled": false, "shuffles": 200}
}
```

## Fields

| Section | Fields | Type |
|---------|--------|------|
| pair | exchange, symbol, timeframe | select (populated from API) |
| direction | long_only, short_only, both | select |
| entry.order_type | market, stop_market, stop_limit, limit | select |
| entry.conditions | groups of conditions with AND/OR logic | conditions_group |
| entry.sizing | method (% equity / fixed), value, max_concurrent | group |
| exit.take_profit | enabled, order_type, value, sizing | group |
| exit.stop_loss | enabled, order_type, value, sizing | group |
| exit.trailing_stop | enabled, method (% / ATR), value, sizing | group |
| search | lookahead, min_occurrences, date range, walk_forward, monte_carlo | mixed |

## Condition subcategories

| Subcategory | Metrics prefix | Description |
|-------------|---------------|-------------|
| Threshold | `oc`, `oh`, `ol`, `hl`, `hc`, `lc`, `vol` | Compare metric value directly |
| Percentile Rank | `pctl_oc`, etc. | Compare percentile rank |

Operators: `gt` (>), `gte` (≥), `lt` (<), `lte` (≤), `eq` (=), `neq` (≠)

## Template memory

When AI generates a novel config, it's auto-saved to `USERS_DOCUMENT/saved_models/` as `{timestamp}_{name}.json`. On new chat, user can load a previous model.
