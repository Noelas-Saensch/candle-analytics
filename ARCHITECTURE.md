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
| Performance engine | Rust via PyO3/Maturin (`vibe_engine`) |
| AI agents | Groq API (`qwen/qwen3-32b`) — Strategy Lab + Vibe Lab |
| E2E testing | Playwright headless (optionnel) |

## Server Structure

```
api/
├── main.py              # FastAPI app, CORS, lifespan, router registration
├── routes.py            # REST endpoints + WS bridges + edge search engine
├── dashboard.py         # SPA: Chart + Analyze tabbed views
├── analyze.py           # Analyze API (metrics, percentiles)
├── strategy_lab.py      # Strategy Lab SPA (chat + params + results + order types)
├── vibe_lab.py          # Vibe Lab SPA (chat → code → backtest → analyze)
├── agent.py             # Strategy Lab LLM agent (file-bridge IPC)
├── vibe_agent.py        # Vibe Lab LLM agent (file-bridge IPC)
├── sandbox.py           # AI strategy execution sandbox (restricted exec)
├── condition_registry.py # 252 conditions, indicators, patterns registry
├── _lock.py             # File-based IPC lock
└── _agent/              # LLM generator, validator, analyzer
    ├── generator.py     # Groq/Qwen code generation
    ├── validator.py     # Strategy syntax + security validation
    └── analyzer.py      # Backtest result analysis
```

```
vibe_engine/             # Rust performance engine (PyO3)
├── src/
│   ├── lib.rs           # Python module entry (19+ exports)
│   ├── indicators.rs    # 13 TA indicators (RSI, SMA, EMA, BBANDS, etc.)
│   ├── backtest.rs      # Vectorized backtest engine
│   ├── metrics.rs       # Performance metrics (Sharpe, win rate, etc.)
│   ├── formula.rs       # Formula evaluator (eval_formula_inner + PyO3 wrapper)
│   ├── statemachine.rs  # Custom order type state machine
│   └── condeval.rs      # Condition group evaluator
└── Cargo.toml
```

```
candles/
├── config.py            # pydantic-settings (env vars, pairs, timeframes)
├── fetcher.py           # Orchestrator: fetch & store
├── clients/
│   ├── binance.py       # Binance klines API client
│   └── hyperliquid.py   # Hyperliquid candleSnapshot client
├── storage/
│   └── db.py            # SQLite CRUD
├── stream/
│   ├── handler.py       # WebSocket handlers
│   └── runner.py        # Stream orchestrator
└── models.py            # OHLCV Pydantic model
```

```
custom_types/            # Custom type registry (order types, indicators, conditions)
├── registry.py          # Python registry loader
├── orders.json          # Pre-populated order types
├── indicators.json      # Pre-populated indicator definitions
├── conditions.json      # Pre-populated condition templates
├── ai_generated.json    # AI-generated custom types (persisted by agent)
└── candles.json         # Candle patterns
```

## Skills (10 total)

| Skill | Location | Purpose |
|-------|----------|---------|
| auto-reload-server | `.opencode/skills/auto-reload-server/` | Restart FastAPI after file changes |
| chat-smoke | `.opencode/skills/chat-smoke/` | E2E chat test (smoke + Playwright) |
| code-quality | `.opencode/skills/code-quality/` | Pre-declaration checklist |
| external-source-audit | `.opencode/skills/external-source-audit/` | Security analysis of external sources |
| github-backup | `.opencode/skills/github-backup/` | Automated GitHub push |
| pyjs-quote-debug | `.opencode/skills/pyjs-quote-debug/` | Python→JS quoting bug detection |
| server-lifecycle | `.opencode/skills/server-lifecycle/` | Server lifecycle management |
| session-lifecycle | `.opencode/skills/session-lifecycle/` | Session detection + CHRONOLOGIE updates |
| strategy-designer | `.opencode/skills/strategy-designer/` | Strategy design conversation flow |
| subagent-cache | `.opencode/skills/subagent-cache/` | Sub-agent result caching |

## Data Flow

```
Exchange API (Binance/Hyperliquid)                  User Browser
    ↓ fetch_klines / candleSnapshot                     ↑
Fetcher orchestrator                              FastAPI / WS
    ↓                                                   ↑
SQLite + CSV ─────────→ Rust Engine (vibe_engine)       ↑
    |                      ↓ indicators, backtest       ↑
    |                   Edge Search Engine               ↑
    |                      ↓ conditions, orders          ↑
    └──→ AI Agents (Strategy Lab / Vibe Lab) ──────────┘
            ↑ LLM (Groq) + file-bridge IPC
```

## Pages / SPAs

| Route | Page | Features |
|-------|------|----------|
| `/dashboard` | Dashboard | Candlestick chart, volume, 6 chart families, RAW DATA table |
| `/strategy-lab` | Strategy Lab | Chat AI ↔ config builder, conditions, edge search, order types |
| `/vibe-lab` | Vibe Lab | AI code generation, sandbox backtest, equity curve, metrics |
| `/api/health` | JSON | Server health + configured pairs/TFs |

## WebSocket Endpoints

| Path | Purpose |
|------|---------|
| `/api/ws/strategy-chat` | Strategy Lab real-time chat ↔ agent |
| `/api/ws/vibe-chat` | Vibe Lab real-time chat ↔ agent |
| `/api/ws/candles` | Live candle updates (SSE fallback) |

## Key Design Decisions

- **USDC only** — No USDT (French regulation). Pairs use USDC quote.
- **Dual storage** — SQLite for queries, CSV for portability/backup.
- **Metrics pre-computed at insert time** — 7 OHLC metrics computed during `save_candles()`.
- **Percentiles pre-computed in DB** — Backfilled on server startup.
- **Rust engine for perf** — Indicators, backtest, formula eval, state machine in Rust via PyO3.
- **AI agents via file bridge** — Standalone Python scripts poll `/tmp/*.json` for IPC.
- **Custom type system** — Orders, indicators, conditions extensible via JSON registry + AI generation.
- **ES5-compatible JS** — No `const`/`let`/`?.`/`for...of`; validated via `node --check`.
- **Server lifecycle script** — `scripts/server.sh` manages port conflicts, health checks.
- **Chat smoke test** — `scripts/test-chat.sh` catches JS syntax errors before they reach users.
