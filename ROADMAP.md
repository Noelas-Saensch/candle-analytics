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
| **Data layer** | Binance client, Hyperliquid client, SQLite storage, CSV export, WebSocket real-time, Docker deployment |
| **API** | REST (candles, pairs, fetch, events), SSE for live updates, /api/candles/count |
| **Dashboard** | Candlestick chart, volume histogram, auto-scale, regression line, SSE live updates |
| **Metrics** | 7 OHLC metrics pre-computed at insert time, percentiles pre-computed in DB |
| **Chart families** | 6 families (Distribution, Time Series, Correlation, Percentile, Pattern, Overlay), 23+ chart types, per-family params, info tooltips |
| **Caching** | sessionStorage cache, in-memory cache, /api/candles/count lightweight check, background data prefetch |
| **RAW DATA** | Paginated table (100 rows), sortable columns, column filters, percentile display |
| **Infra** | auto-export plugin with stats tracking, session-lifecycle skill, synthesis command, session audit |
| **Git** | SSH remote, auto-push on session export |

### Phase 2 : Strategy Research 🟢

- [ ] **UI/UX refresh** — l'interface est fonctionnelle mais mérite un redesign complet (css, layout, typographie, couleurs)
- [x] **Strategy Lab page** — FastAPI route `/strategy-lab`, 3-part SPA (Chat / Parameters / Results)
- [x] **Conversational AI strategy design** — chat interface that guides user step by step:
  - User describes strategy in natural language
  - Guiding phases: MARCHÉ → CONDITIONS → SORTIE → RISQUE
  - Validates contradictions, flags questionable assumptions
  - Generates structured config → populates editable Parameters panel
- [x] **Strategy-designer skill** — `~/.config/opencode/skills/strategy-designer/SKILL.md`
  - 5-phase conversation flow with validation rules
  - File-bridge communication: `/tmp/strategy_chat_req_*.json` / `res_*.json`
- [x] **LLM agent service** — `api/agent.py` + Groq `llama-3.3-70b-versatile`:
  - Watches request files, calls local LLM, writes responses back
  - Injects strategy-designer skill as system prompt
  - Reads chat log for multi-turn context
  - Runs in dedicated `screen -dmS agent` session
- [x] **WebSocket bridge** — `/api/ws/strategy-chat` for real-time chat between Lab and OpenCode
- [x] **HTTP fallback** — `POST /api/edge/chat` + polling `GET /api/edge/chat/{id}` if WS unavailable
- [x] **Metric filter builder** (AI-populated + manually editable) — conditions with AND/OR/group logic
- [x] **Intelligent occurrence search** — `/api/edge/search` backend:
  - Scans all bars matching filter conditions
  - Measures forward return (N bars ahead)
  - Returns win rate, avg return, Sharpe, distribution
  - Filters by minimum occurrences, time range, pair
- [x] **Edge browser** — grid/card view toggle, sort by win rate / Sharpe / occurrence
- [x] **Vibe Lab** — AI strategy generation from natural language
  - Rust engine (vibe_engine): RSI, SMA, EMA, BBANDS, ATR, MACD, Stochastique, VWAP, ADX, CCI, MFI, Williams %R, OBV
  - LLM code generation (Groq/Qwen) with templates fallback
  - Sandbox execution with position tracking, equity curve, metrics
  - Strategy validator (syntax, security, required functions)
  - LLM analysis (score 1-10, strengths, weaknesses, recommendations)
- [x] **Backtesting engine** — sandbox-based vectorized backtest from generated code
  - Entry/exit via decide() signal function
  - SL/TP via backtest engine (Rust)
  - Metrics: win rate, profit factor, max drawdown, Sharpe, Sortino, Calmar
- [x] **Parameter sweep** — grid search over condition thresholds + lookahead values
- [x] **Walk-forward validation** — train/test split, rolling N windows
- [x] **Monte Carlo shuffle** — p-value for win rate and avg return
- [x] **Export edge** — YAML (reimportable), JSON, CSV (forward returns)
- [x] **Vibe Lab Tab 1 — Chat interface** — WebSocket bridge + HTTP fallback + standalone vibe agent (Groq/Qwen code gen)
- [x] **Vibe Lab chat populates Tab 2 + 3** — `code_generated` responses trigger `receiveGeneratedCode()` → switch to Code tab; Backtest populates Results
- [x] **TA indicator support** — 18 indicators (RSI, SMA, EMA, BBANDS, ATR, MACD, Stochastique, VWAP, ADX, CCI, MFI, Williams %R, OBV) computed server-side via Rust engine
- [x] **Condition interpret endpoint** — `/api/conditions/interpret` parses free-text condition strings (e.g. "rsi(14) < 30") with regex + AI fallback
- [x] **Engine Search Group UI** — collapsible section with LA, MinOcc, MC Shuffles, Walk-Forward, train/test date range, sweep toggle
- [x] **RunSearch auto-mode** — `getSearchConfig` auto-includes `walk_forward` and `monte_carlo_shuffles` in every search request
- [ ] **Multi-pair / multi-exchange selection** — combine datasets (e.g. Binance BTC 1H + Hyperliquid PAXG 1D)

### Phase 3 : Live Trading 🔵

- [ ] **In-process LLM integration** — move agent logic from file bridge to direct FastAPI integration (lower latency, no polling)
- [ ] **Model upgrade** — evaluate 13B+ models for more nuanced strategy conversations
- [ ] **Adaptive fetch rate**:
  | Timeframe | Update |
  |---|---|
  | 1m, 5m, 15m, 30m | WebSocket (every tick) |
  | 1H, 2H, 4H, 6H, 12H | HTTP poll every 1 min |
  | 1D, 1W, 1M | HTTP poll every 5 min |
- [ ] **Paper trading engine** — simulated execution with configurable fees/slippage
- [ ] **Kill switch** — max drawdown / daily loss / Sharpe collapse detection
- [ ] **Alerts** — Telegram / email when edge triggers or kill switch trips
- [ ] **Position tracker** — open positions, P&L, trade history
- [ ] **Live performance dashboard** — equity curve, drawdown, win rate tracker
- [ ] **Multi-strategy portfolio** — run multiple edges simultaneously, shared capital

### Phase 4 : Advanced Data + ML 🔮

- [ ] **Onchain data integration** — whale transfers, exchange flows, interest rates
- [ ] **Orderbook data** — cumulative depth, bid/ask imbalance, order flow imbalance
- [ ] **Funding rates + open interest** — derivatives market sentiment
- [ ] **335+ technical indicators** — integrate from [quant-ohlcv-feature](https://github.com/YuxinSUN89/quant-ohlcv-feature)
- [ ] **Feature engineering pipeline** — 77+ stationary ML-ready features (per asset, per TF)
- [ ] **ML-based edge detection** — regime classification, anomaly detection, predictive models
- [ ] **LLM-powered edge discovery** — describe strategy in natural language → generate + validate (inspired by [AlphaEvo](https://github.com/ZhuLinsen/alphaevo), [VibeTrading](https://github.com/VibeTradingLabs/vibetrading))
- [ ] **Cross-pair correlation** — leading indicator discovery across pairs/TFs
- [ ] **Hedge finder** — statistical arbitrage, cointegrated pairs

---

## Tasks by Phase

### Phase 1 (✅ Done — 40+ items completed)
All items listed in the [Done section of previous versions](./CHRONOLOGIE.md).

### Phase 2 (🟢 To Do)
- [x] Strategy Lab page (3-part SPA: Chat / Parameters / Results)
- [x] Conversational AI strategy design (chat + skill)
- [x] Strategy-designer skill (5-phase guided conversation)
- [x] LLM agent service (Groq llama-3.3-70b via API, file bridge, multi-turn)
- [x] WebSocket bridge `/api/ws/strategy-chat`
- [x] HTTP fallback for chat (POST + polling)
- [x] Metric filter builder (AI-populated + editable)
- [x] /api/edge/search endpoint
- [x] Edge browser (grid/card view)
- [x] Parameter sweep (grid search)
- [x] Walk-forward validation
- [x] Monte Carlo shuffle
- [x] Export edge (YAML/JSON/CSV)
- [x] Backtesting engine integration
- [x] TA indicator support (18 indicators via Rust engine + Python bindings)
- [x] Condition interpret API (`/api/conditions/interpret`)
- [x] Frontend condition input (`metric(period) op value` format with params serialization)
- [x] Engine Search Group UI (Walk-Forward, MC, Sweep, date range)
- [x] RunSearch auto-mode (WF + MC auto-included)
- [x] **Indicator Browser modal** — `GET /api/conditions/catalog` + modal avec hiérarchie catégories/sous-catégories/indicateurs/métriques
- [x] **On-the-fly indicator computation** — `_INDICATOR_FUNCS` + fallback on-demand pour indicateurs custom non pré-calculés
- [x] **AI ✨ suggestion buttons** — `POST /api/edge/suggest` + popover sur chaque input libre (12 champs)
- [x] **Condition validation** — `_validate_conditions()` dans `_run_single_search()` vérifie métriques vs `FLAT_REGISTRY`
- [ ] Multi-pair / multi-exchange selection

### Phase 3 (🔵 Planned)
- [ ] In-process LLM integration (direct FastAPI, no bridge)
- [ ] Model upgrade (13B+)
- [ ] Adaptive fetch rate system
- [ ] Paper trading engine
- [ ] Kill switch (drawdown / daily loss / Sharpe)
- [ ] Alerts (Telegram / email)
- [ ] Position tracker
- [ ] Live performance dashboard
- [ ] Multi-strategy portfolio

### 🧹 Phase Cleanup — Session de nettoyage, audit et amélioration générale

> Objectif : remettre le projet en état de marche sain avant d'attaquer Phase 3.

#### Audit code
- [ ] **ES5 scan** — vérifier qu'aucun `const`/`let`/`?.`/`for...of`/`NodeList.forEach` ne subsiste dans `strategy_lab.py` et `vibe_lab.py`
- [x] **Python escape audit** — automatisé via `scripts/check-pyjs-quotes.sh` + skill `pyjs-quote-debug`
- [ ] **Dead code removal** — `grep` des fonctions JS/Python non appelées, imports inutilisés
- [ ] **Error handling** — vérifier que toutes les routes API et tous les `fetch()` frontend ont des `.catch()` / `try-except`
- [ ] **Shadowed builtins** — `all`, `type`, `id`, `input`, `filter`, `map`, `open` etc. utilisés comme noms de variables

#### UI/UX
- [ ] **CSS audit** — supprimer les règles dupliquées/inutilisées, unifier les couleurs/variables CSS
- [ ] **Responsive** — tester les deux labs sur écran < 1024px, corriger les débordements
- [ ] **Loading states** — tous les boutons doivent montrer un état "loading" pendant les appels API
- [ ] **Notification system** — remplacer les `status.textContent` ad-hoc par un système de notification unifié
- [ ] **Tooltips** — vérifier que tous les champs de config ont des `title` explicatifs

#### Architecture
- [ ] **Agent monitoring** — script `healthcheck.sh` qui vérifie les 3 processus et les restart si morts
- [ ] **IPC cleanup** — cron/nettoyage automatique des `/tmp/strategy_chat_*` et `/tmp/vibe_chat_*` > 5 min
- [ ] **Logging** — remplacer les `print()` et `append_log()` par un vrai logger structuré
- [ ] **Config validation** — Pydantic models pour la config de stratégie (validation au lieu de JS-only)

#### Testing
- [ ] **Smoke tests** — script qui appelle tous les endpoints API et vérifie HTTP 200
- [ ] **WS health** — test automatisé de connexion WebSocket
- [ ] **Manual test checklist** — document avec la procédure de test complète

#### Skills & Tools
- [x] **github-backup skill** — backup GitHub automatisé (`.opencode/skills/github-backup/`)
- [x] **subagent-cache skill** + `scripts/cache-subagent.sh` — cache timestampé des résultats sub-agent
- [x] **pyjs-quote-debug skill** + `scripts/check-pyjs-quotes.sh` — détection bugs quoting Python→JS
- [x] **Pre-commit hook amélioré** — utilise `scripts/check-pyjs-quotes.sh` au lieu du naive `const` grep
- [x] **GROQ API vérifié** — agent répond correctement (testé avec requête réelle → config_update reçue)
- [x] **JS SyntaxError fixé** — 3 onclick handlers dans strategy_lab.py (selectCatalogCategory + 2×addFromCatalog)

#### Sécurité (external sources)
- [x] **Documenté dans AGENTS.md** — procédure d'analyse de sécurité pour repos/scripts externes
- [x] **Outils recommandés** — OpenSSF Scorecard, Trivy, Semgrep, Bandit (avec classement)
- [ ] **Installer et configurer** — ajouter au CI/CD ou pre-commit (optionnel)

#### Documentation
- [ ] **README.md** — setup, architecture, commandes utiles
- [ ] **API reference** — lister tous les endpoints avec leur méthode, paramètres, réponses
- [ ] **Agent diagram** — schéma ascii de l'architecture agent/file-bridge/WS
- [x] **Per-page docs** — 4 pages détaillées dans `USERS_DOCUMENT/project-docs/pages/`

### Phase 4 (🔮 Future)
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

## Similar Projects — Inspiration

| Project | Stars | What to borrow |
|---------|-------|----------------|
| [**vectorbt**](https://github.com/polakowo/vectorbt) | 7.5K | Matrix-based backtesting — run N configs in parallel |
| [**Jesse**](https://github.com/jesse-ai/jesse) | 5.5K | Multi-TF/symbol architecture, Monte Carlo, ML pipeline |
| [**VibeTrading**](https://github.com/VibeTradingLabs/vibetrading) | 1.4K | AI agent strategy generation → backtest → deploy |
| [**quant-ohlcv-feature**](https://github.com/YuxinSUN89/quant-ohlcv-feature) | — | 335+ academic features from OHLCV for Phase 4 |
| [**ta_lab2**](https://github.com/adammsafi/ta_lab2) | — | 109-TF feature engineering, IC-based evaluation |
| [**HedgeVision**](https://github.com/ayush108108/hedgevision) | — | Statistical arbitrage UI, cointegration screener |
| [**AlphaEvo**](https://github.com/ZhuLinsen/alphaevo) | 29 | Self-evolving LLM strategies — "diagnose → mutate → retest" |
| [**SignalFlow**](https://github.com/pathway2nothing/signalflow-trading) | 2 | Visual DAG editor for strategy pipelines |
| [**manifoldbt**](https://github.com/Jimmy7892/manifoldbt) | 3 | Rust backtesting — 161× faster than vectorbt |
| [**TradrLab**](https://tradrlab.com/) | — | AI Scenario Assistant — describe idea, get matches |
| [**NexQuant**](https://github.com/TPTBusiness/NexQuant) | 3 | Autonomous AI agent for quant strategy research |
| [**Kainex**](https://github.com/francismiko/kainex) | — | Multi-market, React + FastAPI, clean UI |

---

## RULES

See `RULES.md` for operational rules.

---

## TIMEFRAMES

Supported: `1m, 5m, 15m, 30m, 1H, 2H, 4H, 6H, 12H, 1D, 2D, 3D, 1W, 2W, 1M`

**Default**: `1H`
