# Vibe Lab (`/vibe-lab`)

**Purpose:** A natural-language-to-backtest pipeline where users describe a trading strategy in plain English, an AI agent generates executable Python code, runs a sandboxed backtest, and displays performance metrics, equity curve, trade list, and AI-powered analysis.

---

## Layout

The page is organized into three tabs and a persistent market selector bar:

### Persistent Top Bar (visible across all tabs)
- Exchange selector (Binance / Hyperliquid)
- Pair selector (loaded from available pairs, fallback BTCUSDC/PAXGUSDC)
- Timeframe selector (1m to 1M)
- Bars limit (200 / 500 / 1000 / 2500 / 5000)

### Tab 1: Chat (`tab-describe`)
- Chat log with user/AI/system messages, avatar, timestamps, markdown rendering
- Text input (Enter to send, Shift+Enter for newline)
- Connection status indicator
- Action buttons (appear when code is generated): **Backtest**, **Improve**
- Typing indicator
- Export chat (Markdown), New conversation

### Tab 2: Code (`tab-code`)
- **Left panel (main)**:
  - Generated strategy code textarea (monospace, Python syntax)
  - Validation badge (Valid/Invalid) with error/warning details
  - Controls: Validate, Run Backtest, Copy, Save
  - **Parameter Optimization** section: Auto-detects numeric constants in the code, lets user define value ranges (comma-separated) and runs grid-search optimization
- **Right panel (sidebar)**:
  - **Saved Strategies**: List of previously saved strategies with load/delete

### Tab 3: Results (`tab-results`)
- **Backtest Results**:
  - Metrics grid: Total Return, Win Rate, Sharpe, Sortino, Profit Factor, Max DD, Trades, Final Balance
  - Equity curve chart (Chart.js line chart with position indicator)
  - Trades table (side, entry, exit, PnL %, PnL $)
  - **AI Analysis** card with score (0-10), summary, strengths, weaknesses, recommendations
  - Save and "Add to Comparison" buttons
  - "Iterate" button to refine strategy
- **Strategy Comparison** section (appears after adding results): Side-by-side metric cards for multiple backtest runs

---

## Key Features

- **Natural language → strategy code**: AI agent (Groq-powered) generates Python strategy code from user descriptions
- **Code templates**: Pre-built strategy templates (e.g., SMA crossover, RSI-based) for quick start
- **Sandboxed backtesting** via `StrategySandbox` class: executes generated code against real OHLCV data with trade simulation
- **Built-in validation**: Python AST-based validation of generated strategy code (checks for forbidden imports, missing `decide()` function, etc.)
- **AI analysis**: Automated analysis of backtest results with a score (0-10), strengths, weaknesses, and actionable recommendations
- **Parameter optimization**: Auto-detects numeric parameters in code, performs grid-search optimization (max 100 combinations)
- **Strategy comparison**: Add multiple backtest results to a comparison grid for side-by-side evaluation
- **Save/Load persistence**: Strategies saved as JSON files in `data/strategies/`
- **Chat interface** with WebSocket (primary) and HTTP polling (fallback) for agent communication
- **Code generation via Groq** (LLM) or via built-in templates (no API key required for templates)
- **AI "Improve" flow**: Ask the AI to suggest code improvements based on current results

---

## API Routes

### Endpoints served by this page's router (`api/vibe_lab.py`)

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/vibe-lab` | Returns the full Vibe Lab HTML page |
| POST | `/vibe/generate` | Generate strategy code from description (Groq or template) |
| POST | `/vibe/validate` | Validate strategy code (AST-based) |
| POST | `/vibe/run` | Run sandboxed backtest with strategy code |
| POST | `/vibe/analyze` | Analyze backtest results (score, strengths, etc.) |
| GET | `/vibe/templates` | List available strategy templates |
| POST | `/vibe/save` | Save strategy to disk (JSON) |
| GET | `/vibe/strategies` | List all saved strategies |
| GET | `/vibe/strategy/{sid}` | Load a specific saved strategy |
| DELETE | `/vibe/strategy/{sid}` | Delete a saved strategy |
| POST | `/vibe/optimize` | Run parameter grid-search optimization |
| POST | `/vibe/ask-opencode` | Write a prompt to a temp file for OpenCode |
| POST | `/vibe/chat` | HTTP fallback: submit a chat message |
| GET | `/vibe/chat/{req_id}` | HTTP fallback: poll for chat response |
| POST | `/vibe/chat/respond` | Write chat response (used by OpenCode agent) |

### Endpoints consumed from `api/routes.py` (prefix `/api`)

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/pairs` | List available exchange/symbol pairs |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `ws://{host}/api/ws/vibe-chat` | Primary communication channel with Vibe agent |

---

## Dependencies

| Library / Resource | Version | Usage |
|--------------------|---------|-------|
| Chart.js (CDN) | 4.4.7 | Equity curve chart |
| FastAPI | (project) | Server-side route handler |
| Pydantic | (project) | Request/response validation |
| Groq API | (external) | AI code generation via `generate_via_groq()` |
| Python `ast` | stdlib | Strategy code validation |
| Python `uuid` | stdlib | Request ID generation |
| pandas | (project) | Data handling in sandbox |
| StrategySandbox | (api/sandbox.py) | Sandboxed strategy execution |
| Templates | (api/_agent/generator.py) | Built-in strategy code templates |
| Analyzer | (api/_agent/analyzer.py) | Post-backtest result analysis |

---

## Chat / WebSocket Info

The Vibe Lab uses a **WebSocket** at `/api/ws/vibe-chat` for real-time communication with the Vibe agent (OpenCode with Groq backend).

- **Primary mode**: WebSocket (`ws://`). Server sends `ack`, polls response file (up to 60 retries at 1s intervals), then delivers via `send_json`.
- **Fallback mode**: HTTP polling — POST to `/vibe/chat`, poll GET `/vibe/chat/{id}` at 1.5s intervals.
- **Message types**:
  - `message` / `response` — Regular AI chat
  - `code_generated` — Strategy code ready, auto-populates Code tab with validation
  - `ack` — Server acknowledges
  - `timeout` — No response within 60 seconds (WS) or 15 seconds (HTTP)
- The chat exchanges are logged to `/tmp/vibe_chat_log.md`.
- **Known bugs fixed**: WebSocket response type overwriting, `code_generated` type not handled, ES2020 `?.` operator not supported, ES6+ syntax replaced with `var`, Chart.js CDN missing `defer`, fetch URLs wrong prefix (`/api/vibe/` instead of `/vibe/`).

---

## Known Issues (from ERRORS.md)

- **2026-05-25**: `**data` spread in WS `send_json()` overwrites outer `"type": "response"` — fix: reversed spread order.
- **2026-05-24**: Vibe Lab "still waiting" bug — `handleWSMessage()` ignored `type: "message"` responses. Fix: added `data.type === 'message'` to condition.
- **2026-05-24**: WS poll too short (30s) for code generation (60s Groq timeout). Fix: increased poll range to 60.
- **2026-05-24**: `\'` inside Python `"""..."""` caused JS syntax errors. Fix: changed to `\\'`.
- **2026-05-24**: Textarea stays expanded after sending. Fix: reset `input.style.height = 'auto'`.
- **2026-05-24**: JS `handleWSMessage()` ignored `code_generated` type. Fix: added condition.
- **2026-05-24**: JS uses ES2020 `?.` optional chaining — send button fails silently. Fix: replaced all with manual null checks and `var`.
- **2026-05-24**: Chart.js CDN without `defer` blocked HTML parsing. Fix: added `defer`.
- **2026-05-24**: `GROQ_API_KEY` always empty in `vibe_agent.py` — missing `load_dotenv()`. Fix: added explicit `load_dotenv()`.
- **2026-05-24**: All 10 JS fetch URLs used wrong prefix `/api/vibe/`. Fix: changed to `/vibe/`.
- **2026-05-24**: `loadPairs()` had no error handling. Fix: added `.catch()` with fallback symbols.
- **2026-05-24**: `askOpenCode()` called non-existent `/api/edge/chat`. Fix: created `/vibe/ask-opencode` endpoint.
- **2026-05-23**: Sandbox fails on column name mismatch (`open` vs `o`). Fix: added column rename.
- **2026-05-23**: Sandbox `get_price()` used wrong bar index (`iloc[-1]` instead of `iloc[i]`). Fix: changed to use current bar index.
- **2026-05-24**: Qwen3 LLM response cut off inside `<think>` tags. Fix: added fallback to remove unclosed `<think>` blocks.
- **2026-05-24**: Groq API rate limit (429) on free tier. Fix: added retry loop with exponential backoff.
