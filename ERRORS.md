# Error Knowledge Base — candle-analytics

> Accumulated errors, root causes, and fixes for this project.
> Entries sorted newest-first. Updated after every bug fix.

---

## 2026-05-25 | api/strategy_lab.py | `'' + var + ''` inside onclick (JS SyntaxError — no backslash)
- **Error**: Strategy Lab page: send button does nothing, chat input invisible, entire JS broken. Node.js reports `SyntaxError: Unexpected string` at lines with `selectCatalogCategory('' + key + '')`.
- **Cause**: Python `"""..."""` processes `\'` as an escaped single quote → produces `'` (no backslash). So `\'' + key + '\'` becomes `'' + key + ''` in the JS output. The `()` after `'' + key + ''` becomes a bare `)` in JS with no matching `(` (the `(` was inside a JS string literal). Three onclick handlers affected: `selectCatalogCategory`, `addFromCatalog` (2 occurrences).
- **Fix**: Changed `\'` → `\\'` in Python `"""` source for all 3 onclick handlers. Python `\\'` produces `\'` in output (correct JS escape for single quote inside single-quoted JS string).
- **Script**: Created `scripts/check-pyjs-quotes.sh` to automatically detect this class of bug. Created `.opencode/skills/pyjs-quote-debug/SKILL.md` as a reusable skill.
- **Files**: `api/strategy_lab.py` (lines 1414, 1446, 1462)

## 2026-05-25 | scripts/ | Created pyjs-quote-debug skill + check script
- **Error**: (tooling) No automated check existed for Python-to-JS quoting bugs — `\'` inside `"""` silently produces `'` instead of `\'` in JS output.
- **Cause**: Python `"""` strings interpret `\'` as escape for `'`, eating the backslash. The fix is `\\'`.
- **Fix**: Created `scripts/check-pyjs-quotes.sh` (bash + inline Python) and `.opencode/skills/pyjs-quote-debug/SKILL.md`.
- **Files**: `scripts/check-pyjs-quotes.sh`, `.opencode/skills/pyjs-quote-debug/SKILL.md`

## 2026-05-25 | api/routes.py | `**data` spread écrase `"type": "response"` dans les 2 WS — Strategy Lab + Vibe Lab timeout
- **Error**: Strategy Lab et Vibe Lab montrent "disconnected" ou timeout après 30s. Les réponses de l'agent arrivent mais le navigateur ne les reçoit pas.
- **Cause**: Les deux `_poll_and_send()` envoient `ws.send_json({"type": "response", "id": req_id, **data})`. Le spread `**data` contient `"type": "message"` (ou `"code_generated"`, `"config_update"`) — il écrase `"type": "response"`. Même bug sur les deux endpoints WS, déjà corrigé partiellement pour `vibe_lab.py` JS côté navigateur mais pas côté serveur. Le JS `handleWSMessage()` traite `type: "message"` correctement, mais le flux est quand même perturbé.
- **Fix**: Inversé l'ordre : `ws.send_json({"id": req_id, **data, "type": "response"})` — `"type": "response"` est maintenant le dernier et surcharge le type interne. Fix appliqué aux deux `_poll_and_send()`.
- **Files**: `api/routes.py:1173`, `api/routes.py:1195`

## 2026-05-24 | api/agent.py | `load_dotenv()` manquant — "⚠️ Groq API is not responding" dans Strategy Lab
- **Error**: Strategy Lab chat shows "⚠️ Groq API is not responding. Set GROQ_API_KEY or check console.groq.com" despite valid key in `.env`.
- **Cause**: `agent.py` est un script standalone (pas un routeur FastAPI). Il n'hérite pas du `load_dotenv()` de `main.py`.  La variable `GROQ_API_KEY` était lue via `os.environ.get()` avant tout chargement du `.env`. Le fichier `.env` n'était jamais chargé.
- **Fix**: Ajouté `from dotenv import load_dotenv; load_dotenv(dotenv_path="/home/anymous/PROJETS/candle-analytics/.env")` en haut de `agent.py`, avant l'import de `os` et la lecture de la variable. Même pattern que `vibe_agent.py`.
- **Files** : `api/agent.py`
- **Note** : la clé Groq elle-même était valide — le curl direct retournait 200. Seul le chargement dans le process standalone était cassé.

## 2026-05-24 | api/vibe_lab.py + api/routes.py | `handleWSMessage()` ignore les réponses `type: "message"` — Vibe Lab "still waiting"
- **Error**: Le Vibe Lab reste bloqué sur "Still waiting..." même quand l'agent répond. Les messages d'erreur Groq n'apparaissent jamais. Le code généré n'arrive pas dans le Tab 2 (sauf si le type est `code_generated`).
- **Cause**: Le serveur envoie `ws.send_json({"type": "response", "id": req_id, **data})`. Le spread `**data` (contenant `type: "message"`) écrase le `type: "response"` extérieur. Le navigateur reçoit `type: "message"` mais le JS ne vérifiait que `data.type === 'response' || data.type === 'code_generated'` — les réponses `type: "message"` (conversation, erreurs) étaient avalées silencieusement. Même bug que Session 016 pour `code_generated`, mais non corrigé pour `message`.
- **Fix**: Ajouté `data.type === 'message'` dans la condition `handleWSMessage()` de `vibe_lab.py:800`.  Également : supprimé le processus zombie vibe-agent double (PID 2773598) qui consommait les requêtes et doublait le rate-limit.   Ajouté retry 429 (3 tentatives avec backoff) dans `vibe_agent.py`.   Nettoyé la fonction `_log_vibe_chat` dupliquée dans `routes.py` — remplacée par import de `_log_vibe` depuis `vibe_lab.py`.
- **Files** : `api/vibe_lab.py:800`, `api/vibe_agent.py:118-160`, `api/routes.py:657-661`

## 2026-05-24 | api/vibe_lab.py + api/strategy_lab.py | `\'` inside Python `"""..."""` → JS syntax error
- **Error**: Browser fails to parse inline `<script>` entirely. Chat send button does nothing, WS stays "disconnected", all JS non-functional. Node.js reports `SyntaxError: Unexpected string` at line with `loadStrategy('' + s.id + '')"`.
- **Cause**: In Python triple-quoted strings (`"""..."""`), `\'` is processed as an escape sequence producing `'`. When the Python string contains JS code like `onclick="loadStrategy(\'' + s.id + '\')"`, the `\''` becomes `''` (two single quotes), breaking the JS string delimiter. Same issue with `split('\n')` where Python converts `\n` to an actual newline in the JS output.
- **Fix**: Changed `\'` → `\\'` in all JS-onclick patterns within `"""..."""` strings (4 occurrences: 3 in vibe_lab.py, 1 in strategy_lab.py). Changed `'\n'` → `'\\n'` for JS string split.
- **Files**: `api/vibe_lab.py:1233,1236,1314`, `api/strategy_lab.py:1018`

## 2026-05-24 | api/routes.py | Vibe lab WS poll too short (30s) for code generation (60s)
- **Error**: Chat response times out after 30s with "No response yet — check that vibe-agent is running". Code never appears in Tab 2 even though agent processes and writes response.
- **Cause**: `_vibe_poll_and_send()` iterates 30 times at 1s intervals (30s total). Groq API timeout is 60s and code generation with `max_tokens: 4096` routinely takes 40-50s. The response file arrives after polling ends → response is silently lost.
- **Fix**: Increased poll range from `30` → `60`. Also reduced `max_tokens` from 4096 → 2048 to speed up generation.
- **Files**: `api/routes.py:665`, `api/vibe_agent.py:133`

## 2026-05-24 | api/strategy_lab.py | Inline onchange handler with single quotes inside JS string
- **Error**: JS syntax error at line with `onchange="var badge=this.parentElement.querySelector('.group-badge...')"`. The `'.group-badge-...'` terminates the outer single-quoted JS string.
- **Cause**: Same root cause as the `\'` issue — attempted to fix by adding raw `'` inside a single-quoted JS string.
- **Fix**: Extracted the handler to a named `switchGroupLogic()` function instead of using inline JS.
- **Files**: `api/strategy_lab.py`

## 2026-05-24 | api/vibe_lab.py + api/strategy_lab.py | Textarea stays expanded after sending message
- **Error**: After typing a multi-line message and pressing Enter, the textarea height remains at the expanded size. Next message starts in a huge input box.
- **Cause**: `sendChatMessage()` calls `input.value = '';` but does not reset `input.style.height`. The `input` event listener previously set `height` to match `scrollHeight`.
- **Fix**: Added `input.style.height = 'auto';` after clearing the value.
- **Files**: `api/vibe_lab.py:831`, `api/strategy_lab.py:615`

---## 2026-05-24 | api/vibe_lab.py | JS `handleWSMessage()` ignores `code_generated` response type
- **Error**: Agent generates code, response written to `/tmp/`, but browser never shows it (no code in Tab 2, no chat message).
- **Cause**: The WS handler `_vibe_poll_and_send()` does `ws.send_json({"type": "response", "id": req_id, **data})`. The `**data` spread (which contains `type: "code_generated"`) overwrites the outer `type: "response"`. The browser receives `type: "code_generated"` but the JS only checked `data.type === 'response'`. The message was silently dropped.
- **Fix**: Added `data.type === 'code_generated'` to the condition in `handleWSMessage()`.
- **Files**: `api/vibe_lab.py`

## 2026-05-24 | api/vibe_lab.py | JS uses ES2020 `?.` (optional chaining) — send button fails silently
- **Error**: Chat send button does nothing; `sendChatMessage()` executes but `document.getElementById('vibeExchange')?.value` throws when optional chaining not supported.
- **Cause**: The `?.` operator is ES2020. Replaced with manual null check: `var el = document.getElementById('vibeExchange'); var exchange = el ? el.value : 'binance';`.
- **Fix**: Removed all 5 instances of `?.`. Replaced all `const`/`let` with `var` (78 instances). Replaced all `for...of` with indexed `for` loops. Replaced `NodeList.forEach` with standard `for` loops.
- **Files**: `api/vibe_lab.py`

## 2026-05-24 | Server | WS endpoints 404 after code changes — stale uvicorn process
- **Error**: `/api/ws/vibe-chat` and `/api/ws/strategy-chat` return 404 even though routes are registered on the router. Verified routes exist via `app.routes` in Python.
- **Cause**: The uvicorn process was started BEFORE the `routes.py` changes were made (PID 2677827, started 12:38). The running Python process had the old code cached. WebSocket routes never existed in memory.
- **Fix**: Killed the process and restarted with `setsid uvicorn api.main:app --port 8001 > /tmp/uvicorn.log 2>&1 & disown`.
- **Files**: N/A (operational)

## 2026-05-24 | api/vibe_agent.py | `GROQ_API_KEY` always empty despite being in `.env`
- **Error**: Vibe agent logs "⚠️ Groq API is not responding. Set GROQ_API_KEY or check console.groq.com" even though key is present in `.env`.
- **Cause**: `api/vibe_agent.py` is a standalone script (not a route handler) — it doesn't inherit the server's `load_dotenv()` call in `main.py`. `GROQ_API_KEY` was a module-level `os.environ.get("GROQ_API_KEY", "")` evaluated before any env loading.
- **Fix**: Added `from dotenv import load_dotenv; load_dotenv(dotenv_path="/home/anymous/PROJETS/candle-analytics/.env")` at the top of `vibe_agent.py`.
- **Files**: `api/vibe_agent.py`

## 2026-05-24 | api/vibe_lab.py + api/strategy_lab.py | Chart.js CDN sans `defer` bloque parsing HTML
- **Error**: Les deux labs affichent "disconnected" et le bouton Send ne fait rien. Le script inline en bas de `<body>` ne s'exécute jamais.
- **Cause**: Le CDN Chart.js dans `<head>` n'a pas d'attribut `async`/`defer`. Le navigateur bloque le parsing HTML jusqu'au téléchargement du CDN. Si le CDN est lent ou inaccessible, tout le JS inline (connectWS, sendChatMessage, etc.) n'est jamais parsé ni exécuté.
- **Fix**: Ajouté `defer` au `<script src="...chart.js...">` dans les deux fichiers.
- **Files**: `api/vibe_lab.py`, `api/strategy_lab.py`

## 2026-05-24 | api/strategy_lab.py | JS utilise ES6+ (const/let/?. /for...of) → erreur dans les 2 labs
- **Error**: Strategy Lab montre "disconnected", bouton Send inopérant. Vibe Lab avait le même problème (corrigé session 016).
- **Cause**: 141 déclarations `const`/`let` (ES6), 2 `?.` (ES2020), 12 boucles `for...of` (ES6), 4 `NodeList.forEach` (ES6). N'importe laquelle de ces syntaxes peut faire échouer tout le script sur certains navigateurs.
- **Fix**: `const`→`var`, `let`→`var`, `?.`→vérification manuelle, `for...of`→boucle indexée, `NodeList.forEach`→`for`.
- **Files**: `api/strategy_lab.py`

## 2026-05-24 | api/_agent/generator.py | Qwen3 LLM response cut off inside `<think>` tags
- **Error**: AI generation failed with `json.JSONDecodeError: Expecting value: line 1 column 1`
- **Cause**: Qwen3 model wraps chain-of-thought reasoning in `<think>...</think>` tags before the JSON output. When `max_tokens` (2048) was too low, the model got cut off mid-think, missing the `</think>` closing tag. The regex `^<think>.*?</think>` required the closing tag, so the entire think block was kept as-is, making `json.loads()` fail.
- **Fix**: Added fallback: if `</think>` is absent, remove everything from `<think>` onward. Also increased `max_tokens` from 2048 → 4096.
- **Files**: `api/_agent/generator.py`

## 2026-05-24 | api/_agent/generator.py | Groq API rate limit (429) on free tier
- **Error**: `generate_via_groq()` returned None — silent failure, UI showed "Generation failed. Set GROQ_API_KEY or use a template."
- **Cause**: Groq free tier rate-limits requests (14,400 req/day, with concurrency caps). The code did a single attempt with no retry and no rate-limit awareness.
- **Fix**: Added 3-attempt retry loop with exponential backoff (1s, 2s) on 429 responses.
- **Files**: `api/_agent/generator.py`

## 2026-05-24 | api/main.py | `.env` not loaded into `os.environ`
- **Error**: `GROQ_API_KEY` from `.env` was not visible to `os.environ.get("GROQ_API_KEY")` in `generator.py` — AI generation always failed despite the key being present.
- **Cause**: pydantic-settings reads `.env` for the `Settings` class, but does NOT inject values into `os.environ`. The generator reads from `os.environ` directly.
- **Fix**: Added `load_dotenv(dotenv_path=...)` at module level in `api/main.py`.
- **Files**: `api/main.py`

## 2026-05-24 | api/vibe_lab.py | All 10 JS fetch URLs use wrong prefix `/api/vibe/`
- **Error**: Pair dropdown empty, tabs not clickable, generate button shows network error. Browser Console shows 404 on all `/api/vibe/...` fetches.
- **Cause**: All JS `fetch()` calls used `/api/vibe/...` but `vibe_lab_router` is included in `main.py` WITHOUT `/api` prefix — routes are at `/vibe/...` not `/api/vibe/...`. Every API call returned 404 silently (no `.catch()` handlers).
- **Fix**: Changed all 10 fetch URLs from `/api/vibe/` → `/vibe/`. Added `.catch()` handlers to `loadPairs()` and `loadTemplates()`. Added inline fallback `<script>` after the pair `<select>` for instant options regardless of JS state.
- **Files**: `api/vibe_lab.py`

## 2026-05-24 | api/vibe_lab.py | `loadPairs()` has no error handling
- **Error**: Pair dropdown stays empty when `/api/pairs` fetch fails silently.
- **Cause**: `loadPairs()` had no `.catch()` — any fetch error was swallowed by the Promise chain.
- **Fix**: Added `.catch()` with fallback symbols (BTCUSDC / PAXGUSDC). Also added inline `<script>` right after the `<select id="vibeSymbol">` element that populates it before the main JS even runs.
- **Files**: `api/vibe_lab.py`

## 2026-05-24 | api/vibe_lab.py | `askOpenCode()` calls non-existent `/api/edge/chat`
- **Error**: "Ask OpenCode" button in Vibe Lab does nothing — shows "Error" or sends request that never completes.
- **Cause**: The JS called `fetch('/api/edge/chat', ...)` which doesn't exist. No such endpoint was ever implemented.
- **Fix**: Created `POST /vibe/ask-opencode` endpoint that writes the strategy request to `/tmp/vibe_opencode_*.md`. Updated JS to call this endpoint and display the file path.
- **Files**: `api/vibe_lab.py`

## 2026-05-24 | Server (bash) | Server dies after bash tool timeout
- **Error**: Server started with `nohup uvicorn ... &` stops responding after 15-60 seconds. Health check returns 000 from curl.
- **Cause**: `nohup` processes are children of the bash session created by the tool. When the bash tool's timeout fires (or the command completes), the shell exits and kills its children — including the nohup'd uvicorn.
- **Fix**: Use `setsid uvicorn ... &` + `disown` to detach the process from the bash session entirely.
- **Files**: N/A (shell usage pattern)

## 2026-05-23 | api/sandbox.py | Vibe Lab sandbox fails on column name mismatch
- **Error**: Sandbox backtest crashes: `KeyError: 'open'` — template-generated code expects column names like `open`, `high`, `low`, `close` but pandas DataFrame has `o`, `h`, `l`, `c`.
- **Cause**: `query_candles()` returns rows with `open`/`high`/`low`/`close` keys from SQLite, but the sandbox converts to pandas with short column names `o`/`h`/`l`/`c`/`v`. Templates were written expecting the long names.
- **Fix**: Added column rename in `sandbox.py` before passing to template: `df.columns = ['t','o','h','l','c','v']`.
- **Files**: `api/sandbox.py`

## 2026-05-23 | api/sandbox.py | Price lookup uses wrong bar index
- **Error**: `get_price()` always returns the last bar's close price regardless of the current bar index.
- **Cause**: The sandbox's `get_price()` function used `ohlcv['c'].iloc[-1]` (last row) instead of `ohlcv['c'].iloc[i]` (current bar).
- **Fix**: Changed to use the bar index `i` that's passed to `decide(i, ohlcv)`.
- **Files**: `api/sandbox.py`

## 2026-05-23 | api/dashboard.py | RAW DATA table crashes on empty percentiles
- **Error**: Dashboard RAW DATA tab crashes with JS error when percentiles are empty/null.
- **Cause**: `c.percentiles` can be `undefined` for newly inserted rows before backfill runs. The render function tried to access `c.percentiles.oc` directly.
- **Fix**: Added `c.percentiles = c.percentiles || {}` initializer in `renderRawTable()`.
- **Files**: `api/dashboard.py`

## 2026-05-23 | api/dashboard.py | Chart.js crosshair labels invisible
- **Error**: Crosshair lines appear but value labels are not visible (no text shown).
- **Cause**: Used `labelVisible` which is not a valid Chart.js property. The correct property is `visible` inside the crosshair plugin options.
- **Fix**: Changed to `visible: true` and added `labelBackgroundColor: '#e94560'`.
- **Files**: `api/dashboard.py`

## 2026-05-23 | api/dashboard.py | Chart.js zoom can exceed data range
- **Error**: User can zoom out past the original data range, creating empty axis space.
- **Cause**: Used `minRange` in zoom options, but the correct property for maximum zoom-out is `maxRange`.
- **Fix**: Changed from `minRange` to `maxRange`.
- **Files**: `api/dashboard.py`

## 2026-05-23 | api/dashboard.py | Heatmap blurry on retina displays
- **Error**: Heatmap chart looks blurry/pixelated on high-DPI displays.
- **Cause**: Canvas wasn't scaled by `devicePixelRatio`.
- **Fix**: Applied `devicePixelRatio` scaling to the canvas before rendering heatmap.
- **Files**: `api/dashboard.py`

## 2026-05-22 | candles/clients/hyperliquid.py | Hyperliquid OHLCV API unclear
- **Error**: `_fetch_klines()` not implemented — Hyperliquid API docs don't clearly document an OHLCV endpoint.
- **Cause**: Hyperliquid uses `candleSnapshot` endpoint (discovered later) — original research didn't find it.
- **Fix**: Stubbed with `NotImplementedError`. Later implemented using `POST https://api.hyperliquid.xyz/info` with `{"type": "candleSnapshot", ...}`.
- **Files**: `candles/clients/hyperliquid.py`

## 2026-05-22 | Data | EURC/USDC pair doesn't exist on Binance
- **Error**: Fetching EURCUSDC candles returns empty response — pair not found.
- **Cause**: EURC/USDC is not a listed pair on Binance.
- **Fix**: Added to ROADMAP as ❌ abandoned. Skipped during fetch loops. Added comment in config.
- **Files**: `ROADMAP.md`, `candles/config.py`

## 2026-05-25 | api/strategy_lab.py | SyntaxWarning: invalid escape sequence '\w'
- **Error**: `SyntaxWarning: invalid escape sequence '\w'` when importing strategy_lab.py. Also blocks AST parsing with -W error.
- **Cause**: JavaScript regex patterns like `/\w+/` inside Python triple-quoted string contain `\w`, `\s`, `\d` which are not valid Python string escape sequences. Python 3.13 raises SyntaxWarning for these.
- **Fix**: Changed `\w` → `\\w`, `\s` → `\\s`, `\d` → `\\d`, `\\(` → `\\(` in all JS regex literals embedded in the HTML template string. These produce the correct `\w`/`\s`/`\d`/`\(` in the rendered JavaScript.
- **Files**: `api/strategy_lab.py` (lines 1104, 1122, 1181, 1214)

## 2026-05-22 | Infrastructure (Git) | GitHub token expired
- **Error**: `git push` fails with 401 Bad Credentials. Remote is HTTPS with stored token.
- **Cause**: The token in `~/.git-credentials` expired.
- **Fix**: Switched remote from HTTPS to SSH: `git remote set-url origin git@github.com:Noelas-Saensch/candle-analytics.git`
- **Files**: N/A (git config)
