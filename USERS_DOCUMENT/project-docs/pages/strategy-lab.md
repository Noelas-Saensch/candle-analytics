# Strategy Lab (`/strategy-lab`)

**Purpose:** An AI-assisted strategy editor that lets users build, backtest, and refine trading strategies using a chat interface with OpenCode, combined with a visual condition/order builder and detailed results analysis (edge, walk-forward, Monte Carlo, sweep).

---

## Layout

The page is divided into three main sections:

### Part 1: AI Strategy Chat
- Chat log (user/AI/system messages with avatar, timestamps, markdown rendering, analysis cards)
- Text input (Enter to send, Shift+Enter for newline)
- Connection status indicator (WebSocket connected/connecting/disconnected)
- Action buttons (appear after config is loaded): **Backtest**, **Amelioration**, **Deep Thinking**
- Typing indicator ("thinking...")
- Export chat (Markdown) and New conversation buttons

### Part 2: Strategy Configuration (`#paramsSection`)
- **Header**: Strategy name, exchange, symbol, timeframe, leverage, direction (Long Only / Short Only / Both)
- **Engine Search Group** (collapsible):
  - Lookahead (forward return calculation window)
  - Min Occurrences (minimum pattern matches)
  - MC Shuffles (Monte Carlo permutations)
  - Walk-Forward (enable/disable + windows + train %)
  - Train Start / Backtest End dates
  - Sweep enabled checkbox
- **Trade Cards**: Separate LONG and SHORT columns, each containing:
  - Trade cards with OPEN and CLOSE sections
  - Each section has **Conditions** (in AND/OR groups with Threshold/Pctl subcategories) and **Orders** (market/limit/stop_market/stop_limit/sl/tp/ts with size and price)
  - Condition input with autocomplete search dropdown, AI suggest button (✨), and Indicator Browser modal
- **Controls**: Run Search, Save, Export JSON, Load, Clear

### Part 3: Results (`#results`)
- Tabbed result view: **Edge**, **Sweep**, **Walk-Forward**, **Monte Carlo**, **Export**
- Edge tab: Statistics grid (occurrences, forward count, win rate, wins/losses, avg return, profit factor, sharpe, max DD), forward-return histogram (Chart.js), edge browser (grid or card view)
- Sweep tab: Table of parameter sweep results
- Walk-Forward tab: Summary + per-window table
- Monte Carlo tab: p-value significance display
- Export tab: YAML / JSON / CSV export options

---

## Key Features

- **AI-powered strategy building**: Natural language descriptions are sent to OpenCode via WebSocket (or HTTP fallback), which responds with strategy configs, code, or analysis
- **Visual condition builder**: Add/remove conditions with operator selection, metric selection, threshold/percentile modes, inline parsing (e.g., `oc > 0.5`, `pctl 80`)
- **Indicator Browser**: Modal with categorized indicators and metrics (loaded from `/api/conditions/catalog`)
- **AI Suggest**: Context-aware suggestions for any field (name, leverage, lookahead, conditions, order size/price) via `/api/edge/suggest`
- **Condition autocomplete**: Search-as-you-type dropdown from the condition registry
- **Backtesting engine** (`/api/edge/search`): Pattern-based edge detection with forward returns computation
- **Walk-Forward analysis**: Tests strategy robustness across multiple time windows (train/test splits)
- **Monte Carlo simulation**: Random shuffling of forward returns to compute p-values for statistical significance
- **Sweep**: Brute-force parameter scanning across metric values and lookaheads
- **Export**: Edge definitions in YAML, JSON, or CSV (forward returns)
- **Save/Load**: Persistent storage of strategy configs as JSON files in `USERS_DOCUMENT/saved_models/`
- **Deep Thinking** (🧠): AI-powered qualitative analysis of the strategy with score, strengths, weaknesses, recommendations
- **Amelioration** (📈): AI suggests specific parameter changes with old/new values and reasoning
- **Default template**: Pre-filled SMA Crossover + RSI example on load

---

## API Routes

### Endpoints served by this page's router (`api/strategy_lab.py`)

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/strategy-lab` | Returns the full Strategy Lab HTML page |
| POST | `/strategy-lab/save` | Saves a strategy config to `saved_models/` as JSON |
| GET | `/strategy-lab/strategies` | Lists all saved strategy config files |
| GET | `/strategy-lab/strategy/{name}` | Loads a specific strategy by name |

### Endpoints consumed from `api/routes.py` (prefix `/api`)

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/pairs` | List available exchange/symbol pairs |
| POST | `/api/edge/search` | Run a single edge search (backtest) |
| POST | `/api/edge/batch-search` | Run multiple edge searches at once |
| POST | `/api/edge/sweep` | Parameter sweep across metric values |
| GET | `/api/edge/export` | Export edge results (YAML/JSON/CSV) |
| POST | `/api/edge/suggest` | AI suggestions for config fields |
| POST | `/api/edge/chat` | HTTP fallback for chat submissions |
| GET | `/api/edge/chat/{req_id}` | Poll for chat response |
| POST | `/api/edge/chat/respond` | Write a response (used by OpenCode) |
| GET | `/api/conditions/catalog` | Full condition/indicator catalog |
| GET | `/api/conditions/search` | Search conditions by query string |
| POST | `/api/conditions/interpret` | Interpret a natural-language condition |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `ws://{host}/api/ws/strategy-chat` | Primary communication channel with OpenCode agent |

---

## Dependencies

| Library / Resource | Version | Usage |
|--------------------|---------|-------|
| Chart.js (CDN) | 4.4.7 | Histogram rendering (forward return distribution) |
| FastAPI | (project) | Server-side route handler |
| Pydantic | (project) | Request/response validation |
| WebSocket API | (browser) | Bidirectional chat with strategy agent |
| Python `glob` | stdlib | File listing for saved strategies |
| Python `json` | stdlib | Strategy serialization |

---

## Chat / WebSocket Info

The Strategy Lab uses a **WebSocket** at `/api/ws/strategy-chat` for real-time communication with an OpenCode strategy agent.

- **Primary mode**: WebSocket (`ws://`). On connect, the server sends an `ack`, then polls for a response file, and delivers it via `send_json`.
- **Fallback mode**: HTTP polling. If WebSocket fails, the page switches to `/api/edge/chat` (POST to send, GET `/api/edge/chat/{id}` to poll at 1.5s intervals).
- **Message types**:
  - `message` / `response` — Regular AI chat responses
  - `config_update` — AI-generated strategy configuration, auto-rendered into the UI
  - `deep_thinking` — Qualitative analysis with score, strengths, weaknesses, recommendations
  - `amelioration` — Parameter improvement suggestions with old/new values and reasoning
  - `ack` — Server acknowledges receipt of message
  - `timeout` — No response received within polling window (30s WS, 12s for HTTP with "still waiting" reminder)
- **Conversation export** available as Markdown via "Export" button
- **Known bug fixed**: The `**data` spread inside `ws.send_json()` was overwriting the outer `"type": "response"` — fixed by reversing the spread order so `"type": "response"` is the final override.

---

## Known Issues (from ERRORS.md)

- **2026-05-25**: `**data` spread in `ws.send_json()` overwrites `"type": "response"` — both WS endpoints affected. Fix: reversed spread order.
- **2026-05-24**: `load_dotenv()` missing in `agent.py` — standalone script couldn't read `GROQ_API_KEY` from `.env`. Fix: added explicit `load_dotenv()`.
- **2026-05-24**: SyntaxWarning `'\w'` invalid escape sequence in JS regex within Python triple-quoted string. Fix: doubled backslashes (`\\w`, `\\s`, `\\d`).
- **2026-05-24**: Inline `onchange` handler with single quotes broke JS string termination. Fix: extracted to named function.
- **2026-05-24**: Textarea stays expanded after sending message. Fix: reset `input.style.height = 'auto'`.
- **2026-05-24**: Chart.js CDN without `defer` blocked HTML parsing. Fix: added `defer`.
- **2026-05-24**: JS uses ES6+ syntax (const/let/?. /for...of) — errors on older browsers. Fix: all converted to `var` / indexed loops / manual null checks.
