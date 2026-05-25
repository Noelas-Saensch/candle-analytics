# API — candle-analytics

## REST endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Server status, pairs, timeframes |
| GET | `/api/pairs` | Available (exchange, symbol, timeframe) |
| GET | `/api/candles?exchange=&symbol=&timeframe=&limit=&start_time=&end_time=` | OHLCV rows with metrics |
| GET | `/api/candles/count?exchange=&symbol=&timeframe=&start_time=&end_time=` | Row count |
| POST | `/api/fetch` | Trigger backfill |
| GET | `/api/events` | SSE live updates |
| POST | `/api/edge/search` | Edge search — conditions → forward returns |
| POST | `/api/edge/batch-search` | Multiple searches at once |
| POST | `/api/edge/sweep` | Grid search over params |
| GET | `/api/edge/export?format=json\|yaml\|csv` | Export edge results |
| POST | `/api/edge/chat` | HTTP fallback chat (Strategy Lab) |
| GET | `/api/edge/chat/{id}` | Poll HTTP response |
| POST | `/api/edge/chat/respond` | Write response from OpenCode |

| Method | Path | Description |
|--------|------|-------------|
| GET | `/dashboard` | Chart SPA |
| GET | `/analyze` | Percentile analysis table |
| GET | `/strategy-lab` | Edge discovery tool |
| GET | `/vibe-lab` | AI code generation chat |

Vibe Lab endpoints (no /api prefix):
| POST | `/vibe/generate` | AI code generation |
| POST | `/vibe/validate` | Syntax/security check |
| POST | `/vibe/run` | Sandbox backtest |
| POST | `/vibe/analyze` | LLM analysis of backtest |
| GET | `/vibe/templates` | Strategy code templates |
| POST | `/vibe/save` + GET `/vibe/strategies` + GET/DELETE `/vibe/strategy/{sid}` | CRUD |
| POST | `/vibe/optimize` | Parameter grid search |
| POST | `/vibe/ask-opencode` | Write to /tmp/ for terminal AI |
| POST | `/vibe/chat` + GET `/vibe/chat/{id}` + POST `/vibe/chat/respond` | Chat HTTP fallback |

## WebSocket endpoints

| Path | Role |
|------|------|
| `/api/ws/vibe-chat` | Vibe Lab real-time chat |
| `/api/ws/strategy-chat` | Strategy Lab real-time chat |

### WS protocol (both labs)

Browser → Server:
```json
{"type": "message", "content": "...", "exchange": "...", "symbol": "...", "timeframe": "..."}
```

Server → Browser:
```json
{"type": "ack", "id": "uuid"}
// then after agent responds:
{"type": "response", "id": "uuid", **agent_data}
// or timeout:
{"type": "timeout", "content": "..."}
```

## File bridge

| Pattern | Writer | Reader |
|---------|--------|--------|
| `/tmp/{vibe,strategy}_chat_req_*.json` | routes.py WS handler | agent.py / vibe_agent.py |
| `/tmp/{vibe,strategy}_chat_res_*.json` | agent.py / vibe_agent.py | routes.py polling |
| `/tmp/{vibe,strategy}_chat_log.md` | Both | agent reads for history |
