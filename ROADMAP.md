# CANDLE-ANALYTICS — ROADMAP

> **Mission** : Discover statistical edges in OHLCV data to produce viable trading strategies.  
> Later: add onchain data (interest rates, whale transfers, order flow), orderbook depth, funding rates, open interest.  
> **Heart**: Transform raw market data into a measurable, repeatable edge via systematic metric analysis, pattern detection, and statistical validation.

---

## Research Pipeline

```
DATA LAYER → METRICS LAYER → ANALYSIS LAYER → EDGE DETECT → STRATEGY → VALIDATION → EXECUTION
```

| Layer | What it does | Status |
|-------|-------------|--------|
| **Data** | Fetch & store raw OHLCV from CEX/DEX. Future: onchain, orderbook, funding, OI | ✅ Binance + Hyperliquid |
| **Metrics** | Compute 7 OHLC metrics (OC%, OH%, OL%, HL%, HC%, LC%, Vol%) per candle | ✅ Pre-computed in DB |
| **Analysis** | Percentile ranks, distributions, correlations, regimes | ✅ Dashboard (chart families) |
| **Edge Detect** | Find recurring statistical patterns with predictive forward returns | 🟢 Strategy Lab |
| **Strategy** | Formalize edge into entry/exit rules, sizing, risk management | 🔵 Phase 3 |
| **Validation** | Walk-forward, Monte Carlo, out-of-sample, Deflated Sharpe Ratio | 🔵 Phase 3 |
| **Execution** | Paper trading → live, adaptive fetch, kill switch, alerts | 🔵 Phase 3 |

---

## Data Sources

### Current (OHLCV)
| Pair | Exchange | Format |
|------|----------|--------|
| BTC/USDC | Binance (BTCUSDC) + Hyperliquid (BTC) | 1m–1M, SQLite + CSV |
| GOLD/USDC (PAXG) | Binance (PAXGUSDC) + Hyperliquid (PAXG) | 1m–1M, SQLite + CSV |

> **Note**: USDT forbidden by French regulation. USDC only.

### Planned
- **Onchain**: interest rates, large transfers, whale wallet activity, exchange flows
- **Orderbook**: cumulative depth, bid/ask imbalance, order flow
- **Derivatives**: funding rates, open interest, long/short ratio
- **Macro**: correlation with broader market indices, volatility indexes

---

## Phases

```
Phase 1 ── OHLCV Foundation ─────── ✅ Done
Phase 2 ── Strategy Research ────── 🟢 In progress
Phase 3 ── Live Trading ─────────── 🔵 Planned
Phase 4 ── Advanced Data + ML ───── 🔮 Future
```

### Phase 1 : OHLCV Foundation ✅

| Domain | Features |
|--------|----------|
| **Data layer** | Binance client, Hyperliquid client, SQLite storage, CSV export, WebSocket real-time |
| **API** | REST (candles, pairs, fetch, events), SSE for live updates, /api/candles/count |
| **Dashboard** | Candlestick chart, volume histogram, auto-scale, regression line, SSE live updates |
| **Metrics** | 7 OHLC metrics pre-computed at insert time, percentiles pre-computed in DB |
| **Chart families** | 6 families (Distribution, Time Series, Correlation, Percentile, Pattern, Overlay), 23+ chart types |
| **Caching** | sessionStorage cache, in-memory cache, /api/candles/count lightweight check |
| **RAW DATA** | Paginated table (100 rows), sortable columns, column filters, percentile display |
| **Infra** | auto-export plugin, session-lifecycle skill, synthesis command, session audit |

### Phase 2 : Strategy Research 🟢

- [x] **Strategy Lab page** — FastAPI route `/strategy-lab`, 3-part SPA
- [x] **Conversational AI strategy design** — chat interface with guiding phases
- [x] **Strategy-designer skill** — 5-phase conversation flow with file-bridge
- [x] **LLM agent service** — Groq qwen model, file bridge IPC
- [x] **HTTP fallback** — POST `/api/edge/chat` + polling
- [x] **Metric filter builder + condition interpret API**
- [x] **Edge browser** — grid/card view, sort by win rate / Sharpe / occurrence
- [x] **Vibe Lab** — AI strategy generation, Rust engine, sandbox, validation
- [x] **Backtesting engine** — sandbox-based vectorized backtest
- [x] **Parameter sweep** — grid search over condition thresholds
- [x] **Walk-forward validation** — train/test split, rolling N windows
- [x] **Monte Carlo shuffle** — p-value for win rate and avg return
- [x] **Export edge** — YAML/JSON/CSV
- [x] **TA indicator overlay** — 13 indicators computed server-side, rendered on LightweightCharts
- [x] **Indicator customization panel** — color, period, line width per indicator
- [x] **Separate pane for oscillators** — RSI, MACD, Stoch etc. in own pane via `chart.addPane()`
- [x] **Unlimited indicator computation** — removed 500-candle limit, uses all stored candles via `limit=0` in `query_candles`
- [x] **Per-line TV-style settings** — each multi-line indicator member (ichimoku_tenkan, bbands_upper, etc.) has individual color, width, visible toggle
- [x] **Ichimoku cloud color config** — green/red fill colors with opacity via hex + dropdown, stored as rgba strings
- [x] **Momentum oscillator zones** — configurable overbought/oversold/midline levels with dashed price lines for RSI, Stoch, Williams %R, CCI, MFI
- [x] **Time scale always visible** — `#chart-wrapper` CSS layout fix ensures time scale remains visible below all sub-panes
- [x] **Runs on `.venv/bin/python`** — tous les processus screen utilisent le venv
- [x] **WebSocket fix** — `wsproto` installé, `/api/ws/strategy-chat` fonctionne
- [x] **GROQ 429 retry** — 3 tentatives avec backoff dans agent.py
- [x] **GROQ_KEY via .env** — load_dotenv() dans agent.py et vibe_agent.py
- [x] **Docker multi-stage** — Rust + Python build, 4 services (api, stream, agent, vibe-agent)
- [x] **Multi-pair / multi-exchange selection** — combine datasets (e.g. Binance BTC + Hyperliquid PAXG)
- [x] **Strategy LLM auto-test** — validator + fixer 100% locaux, boucle 3 prompts, prompt split en 7 catégories
- [x] **Fix 400 Groq** — `response_format` json avec suffix "Respond with valid JSON."
- [x] **Fix type→config_update** — fixer local convertit message en config_update
- [x] **Ichimoku aliases étendus** — 30+ entrées (japonais, descriptifs, dotted, numériques)
- [ ] **Fix data.win_rate is undefined** — crash quand Run Search retourne résultats sans win_rate

### Dashboard — Phase 2 🟢

- [x] **Chart settings modal** — gear button opens modal with bull/bear body/wick colors + chart bg, persisted in localStorage
- [x] **Controls bar** — separate row between header/tabs and indicators, contains gear, exchange/symbol/tf/date, Reg toggle, Update/Fetch
- [x] **Ichimoku defaults** — Tenkan #4fc3f7 w1, Kijun #4fc3f7 w2, SSA/SSB black w1/w2, cloud green/red 90%, Chikou orange w1
- [x] **Scale alignment** — all main-pane indicator series use priceScaleId='price'
- [x] **SSA/SSB forward projection** — extends beyond last candle via time extrapolation
- [x] **Chikou fix** — uses raw close prices (not rolled+NaN), backward time projection for idx<0
- [x] **Cloud rAF render** — replaces event-subscription-based Canvas overlay with single rAF loop polling visible range, zero subscription pile-up
- [x] **Crosshair legend** — shows candle OHLC + indicator values on hover
- [x] **Chart fills viewport** — css calc(100vh - header - controls-bar) with overflow:hidden
- [x] **Live SSE retry timer cleanup** — EventSource.onerror timer stored in window._liveRetryTimer, cancelled in stopLive()
- [x] **Server lifecycle** — server.sh handles kill/start/restart/health without --reload (no zombie processes)
- [x] **Cloud perf fix** — removed getBoundingClientRect() from drawCloud, replaced rAF polling with subscription+dirty flag, removed O(N*M) fallback loop

### Strategy Converter — Phase 2 🟢

- [x] **Converter page** — `/convert` route with split-panel UI, direction selector (NL→Python, NL→PineScript, PineScript↔Python, NL→Rust)
- [x] **POST /api/convert** — Groq-powered LLM endpoint with 5 system prompts, retry logic, think-tag stripping
- [x] **NL → Python** — generates `decide(i, ohlcv)` function using `vibe_engine` indicators
- [x] **NL → PineScript** — generates TradingView PineScript v5 with proper strategy() syntax
- [x] **PineScript → Python** — translates `ta.*` calls to `ve.*` equivalents, generates `decide()` function
- [x] **Python → PineScript** — translates `ve.*` + `decide()` pattern to PineScript v5
- [x] **NL → Rust** — generates Rust `fn decide()` using `vibe_engine_rs` functions
- [x] **Smoke test coverage** — `/convert` page HTML/JS/API checks in chat_e2e.py

### Phase 3 : Live Trading — Alertes / Conditions / Automation 🔵

> Voir le plan détaillé complet : [`USERS_DOCUMENT/project-docs/ALERTES_CONDITIONS_AUTOMATION.md`](USERS_DOCUMENT/project-docs/ALERTES_CONDITIONS_AUTOMATION.md)

#### A — Infrastructure (parseur, moteur de triggers, persistence)
- [ ] **A.1** Parseur d'expressions de conditions (`POST /api/conditions/evaluate`)
- [ ] **A.2** Moteur de triggers (boucle d'évaluation, types on_close/on_cross/realtime/once)
- [ ] **A.3** Persistance SQLite (tables conditions, actions, historique + CRUD)

#### B — Canaux de livraison
- [ ] **B.1** Coloration de bougie (bar highlighting sur le chart)
- [ ] **B.2** Notification in-app (SSE toast)
- [ ] **B.3** Telegram Bot
- [ ] **B.4** Discord Webhook
- [ ] **B.5** Email SMTP
- [ ] **B.6** Webhook TradingView-compatible
- [ ] **B.7** WhatsApp (optionnel, basse priorité)

#### C — Exécution d'ordres
- [ ] **C.1** Paper Trading (extension StrategySandbox, position manager, P&L)
- [ ] **C.2** Live Trading CCXT (ordres, balance, positions, cancel)
- [ ] **C.3** Kill Switch (drawdown, pertes, erreurs, notification urgence)
- [ ] **C.4** Position Sizing (fixe, risk-based, Kelly)

#### D — Chart & UI
- [ ] **D.1** Condition triggers sur le chart (marqueurs, zones colorées)
- [ ] **D.2** Panneau de configuration des conditions (éditeur, actions, historique)
- [ ] **D.3** Live trigger log (flux SSE en temps réel)
- [ ] **D.4** Performance dashboard (equity curve, drawdown, métriques)

#### E — Filtres statistiques (HAUTE PRIORITÉ)
- [ ] **E.1** Amplitude OHLCV % (filtre les bougies plates)
- [ ] **E.2** Percentile rank (rolling window, classement des métriques)
- [ ] **E.3** Bar highlighting conditionnel (couleurs par filtre)
- [ ] **E.4** Éditeur de métriques (sélection source, comparaison, seuils)
- [ ] **E.5** Seuils utilisateur (sliders, persistance)

### Phase 4 : Advanced Data + ML 🔮

- [ ] Onchain data (whales, exchange flows)
- [ ] Orderbook data (depth, imbalance)
- [ ] Funding rates + OI
- [ ] 335+ technical indicators
- [ ] ML feature engineering pipeline
- [ ] ML edge detection
- [ ] LLM-powered edge discovery
- [ ] Cross-pair correlation
- [ ] Hedge finder (cointegrated pairs)

---

## Tasks by Phase

### Phase 1 (✅ Done)
All items listed in CHRONOLOGIE.md.

### Phase 2 (🟢 Status)
- [x] Strategy Lab SPA
- [x] Conversational AI + skill
- [x] Strategy-designer skill
- [x] LLM agent service (Groq, file bridge, multi-turn)
- [x] WebSocket bridge `/api/ws/strategy-chat`
- [x] HTTP fallback
- [x] Metric filter builder
- [x] /api/edge/search endpoint
- [x] Edge browser
- [x] Parameter sweep
- [x] Walk-forward validation
- [x] Monte Carlo shuffle
- [x] Export edge (YAML/JSON/CSV)
- [x] Backtesting engine
- [x] TA indicator support (13 indicators, Rust engine, Python bindings)
- [x] Indicator overlay on LightweightCharts (separate pane for oscillators)
- [x] Custom types registry + AI persistence
- [x] Rust state machine for custom orders
- [x] Server lifecycle skill
- [x] Chat smoke test tool + skill
- [x] Docker multi-stage build (Rust + Python)
- [x] All processes use .venv/bin/python
- [x] GROQ retry + .env loading fixes
- [x] wsproto for WebSocket support
- [ ] Multi-pair / multi-exchange selection

### 🧹 Phase Cleanup

- [x] ES5 scan
- [x] Python escape audit (pyjs-quote-debug)
- [x] Dead code removed
- [x] Error handling — routes API + fetch .catch() vérifiés
- [x] JS quoting bugs fixed (showIndMenu event delegation)
- [x] indicator response candles bug fixed
- [ ] CSS audit — duplicate rules, unify variables
- [ ] Responsive <1024px
- [ ] Unified notification system
- [ ] Proper logging (structured, replace print/append_log)
- [ ] README.md

### Phase 3 (🔵 Planned)
- [ ] In-process LLM integration
- [ ] Adaptive fetch rate system
- [ ] Paper trading engine
- [ ] Kill switch
- [ ] Alerts
- [ ] Position tracker
- [ ] Live performance dashboard
- [ ] Multi-strategy portfolio

### Phase 4 (🔮 Future)
- [ ] Onchain data integration
- [ ] Orderbook data
- [ ] Funding rates + OI
- [ ] 335+ technical indicators
- [ ] ML feature pipeline
- [ ] ML edge detection
- [ ] LLM-powered edge discovery
- [ ] Cross-pair correlation
- [ ] Hedge finder

---

## Similar Projects — Inspiration

| Project | Stars | What to borrow |
|---------|-------|----------------|
| [**vectorbt**](https://github.com/polakowo/vectorbt) | 7.5K | Matrix-based backtesting |
| [**Jesse**](https://github.com/jesse-ai/jesse) | 5.5K | Multi-TF/symbol architecture |
| [**manifoldbt**](https://github.com/Jimmy7892/manifoldbt) | 3 | Rust backtesting — 161× faster |
| [**AlphaEvo**](https://github.com/ZhuLinsen/alphaevo) | 29 | Self-evolving LLM strategies |

---

## RULES

See `RULES.md` for operational rules.

---

## TIMEFRAMES

Supported: `1m, 5m, 15m, 30m, 1H, 2H, 4H, 6H, 12H, 1D, 2D, 3D, 1W, 2W, 1M`

**Default**: `1H`
