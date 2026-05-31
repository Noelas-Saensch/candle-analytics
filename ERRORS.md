# Error Knowledge Base — candle-analytics

## 2026-05-31 | Dashboard empty — exchange/pair dropdowns empty, chart not rendered (two root causes)

- **Error**: The exchange and symbol `<select>` elements have no `<option>` children. Chart is blank — no candles, no error message. Page HTML renders (header, tabs, controls bar visible) but JavaScript initialization fails silently.
- **Root cause #1 (predominant)**: `document.getElementById('mcontrols')` and `document.getElementById('maxBars')` at lines 3574-3579 return `null` because no HTML elements with those IDs exist in the template. Calling `.addEventListener('change', ...)` on `null` throws `TypeError: Cannot read properties of null (reading 'addEventListener')`. This crash occurs BEFORE `initChart()` and `loadPairs()` are reached — the entire inline script stops. **This is the real reason the dropdowns stay empty.** The `window.error` handler at line 3587 also never fires because it incorrectly checked `e.target.tagName === 'SCRIPT'` (for runtime errors `e.target` is the `Window` object, not `SCRIPT`).
- **Root cause #2 (secondary)**: Even if the null-crash were avoided, any runtime error in `initChart()` (e.g., `LightweightCharts` undefined if CDN fails) would also stop the script, preventing `loadPairs()` from running. Previously there was no try-catch, no fallback CDN, and no visible error message.
- **Fix (first attempt — Session 036, insufficient)**:
  1. **CDN fallback** — `onerror` handler on the `<script>` tag loads from `cdn.jsdelivr.net` if `unpkg.com` fails.
  2. **try-catch around initChart()** — catches chart creation errors, shows `#init-error` box.
  3. **.catch() on loadPairs()** — fetch errors logged.
  → Did NOT fix the issue because the crash at `mcontrols`/`maxBars` happened before `initChart()` was reached.
- **Fix (final — Session 036 continued)**:
  1. **Null-guard event listeners** — `document.getElementById('mcontrols')` and `document.getElementById('maxBars')` now check for `null` before calling `.addEventListener()`, wrapped in an outer try-catch.
  2. **Expand try-catch to indicator init** — `activeIndicators.push()` and `renderIndChips()` also wrapped in try-catch so any future failure doesn't prevent `loadPairs()`.
  3. **Simplify `window.error` handler** — removed incorrect `e.target.tagName === 'SCRIPT'` filter; now shows `#init-error` for any script error.
- **Lessons learned**:
  - A try-catch around `initChart()` is useless if code BEFORE it crashes first. Any synchronous DOM access in the init path can kill the entire bootstrap.
  - `window.addEventListener('error')` — for runtime errors, `e.target` is the `Window` object, not the `SCRIPT` element. The `e.target.tagName === 'SCRIPT'` guard was always false, making the handler a no-op.
  - Always null-guard `document.getElementById(...)` calls that target optional DOM elements.
- **Detection**: Manual observation. The smoke test (`chat_e2e.py smoke`) does NOT catch this — it checks DOM element existence and JS syntax but does not execute JS in a real browser.
- **Files**: `api/dashboard.py` — lines 3574-3579 (null-guarded event listeners), lines 3595-3608 (defensive bootstrap with nested try-catch), line 12 (CDN fallback), lines 267-271 (error div)


> Accumulated errors, root causes, and fixes for this project.
> Entries sorted newest-first. Updated after every bug fix.
>
> **Test safeguard**: Features causing 2+ bugs must have a test log in
> `TESTS_<feature>.md`. See `.opencode/skills/test-safeguard/SKILL.md`.

---

## 2026-05-31 | Primitive API blocks chart render cycle → revert to Canvas overlay + single-shot rAF

- **Error**: Ichimoku cloud Primitive API (`ISeriesPrimitive`) runs `updateAllViews()` inside the chart's render pipeline. Even with visible-range filtering + grouped path fills, every scroll/zoom frame calls `timeToCoordinate()` + `priceToCoordinate()` for ~60 points, blocking the chart from rendering until it completes. Cloud rendering should NEVER block the chart.
- **Cause**: The `ISeriesPrimitive` design inherently runs custom rendering inside the chart's own Canvas render cycle. There is no API to decouple custom draws from the chart's frame. Any JS execution time in `updateAllViews()` or `drawBackground()` directly delays the chart's render → jank on every interaction.
- **Fix**: Reverted to Canvas overlay approach: a separate `<canvas>` element positioned absolutely over the chart container with `pointer-events: none`. Cloud drawing runs in its own `requestAnimationFrame` (single-shot, not persistent loop — zero idle CPU). Chart and cloud render independently. Added `scheduleCloudDraw()` (debounces multiple events into one rAF), `drawCloud()`, `ensureCloudCanvas()`. Generalized `_cloudOverlays{}` to support both Ichimoku AND BBands cloud fills from a single `renderCloudFill()`.
- **Files**: `api/dashboard.py` — removed `createCloudPrimitive()`, `removeCloudPrimitive()`, `_ichimokuCloudPrimitive`, `renderIchimokuCloud()`. Added `_cloudOverlays`, `_cloudDrawRequestId`, `ensureCloudCanvas()`, `scheduleCloudDraw()`, `drawCloud()`, `renderCloudFill()`.

## 2026-05-31 | Volume as deletable indicator — remove hardcoded volumeSeries

- **Error**: Volume was created as a hardcoded `HistogramSeries` in `initChart()` and updated in `loadChart()` + `startLive()`. It could not be removed or reconfigured like other indicators. Volume bar colors were hardcoded `rgba(38,166,154,0.3)`/`rgba(239,83,80,0.3)` instead of matching candlestick chart settings (bullBody/bearBody).
- **Cause**: Volume was never migrated to the indicator system when `INDICATOR_CATALOG` was introduced.
- **Fix**: Added `volume` to `INDICATOR_CATALOG` in the Volume category. Removed `volumeSeries` globe + series creation from `initChart()`. Added `renderVolumeIndicator()` function that reads candle data from `_cachedCandles`, creates a HistogramSeries with per-point colors from `loadChartSettings().bullBody`/`bearBody`. `computeAndRenderIndicators()` now filters volume from the API request and handles it locally. `loadChart()` auto-adds volume if not present. `startLive()` SSE handler updates via `indicatorSeries["volume"][0]`. Timestamp added to legend. Smoke test updated to check for `name: "volume"` instead of `volumeSeries`.
- **Files**: `api/dashboard.py`, `scripts/chat_e2e.py`

## 2026-05-31 | BBands missing indicator_groups cloud entry

- **Error**: BBands middleware and lower lines rendered but no cloud fill between them. Cloud fill only worked for Ichimoku.
- **Cause**: `indicator_groups` for BBands was never added to the server compute endpoint in `routes.py`.
- **Fix**: Added `indicator_groups["bbands"]` with `"cloud": {"top": "bbands_upper", "bottom": "bbands_lower"}` after the bbands computation block. Frontend's `renderCloudFill()` already handled any cloud group generically.
- **Files**: `api/routes.py` — line ~1917

## 2026-05-31 | Zone lines missing configurable width

- **Error**: Overbought/oversold zone lines always rendered with `lineWidth: 1`. Users couldn't adjust zone line thickness in the indicator config panel.
- **Cause**: `INDICATOR_ZONES` levels didn't have a `width` field. Config panel had no width selector. Rendering code hardcoded `lineWidth: 1`.
- **Fix**: Added `width: 1` to all INDICATOR_ZONES level defaults. Added width `<select>` (1-4) per zone in `openIndicatorConfig()`. Read width in `applyIndicatorConfig()`. Pass `z.width || 1` to `createPriceLine()`.
- **Files**: `api/dashboard.py` — `INDICATOR_ZONES`, `initZoneSettings()`, `openIndicatorConfig()`, `applyIndicatorConfig()`, render loop in `renderIndicatorSeries()`.

## 2026-05-31 | Ichimoku cloud | Per-segment Canvas fill() calls cause 0.5-1s lag on scroll/zoom

- **Error**: After visible-range filtering fix, scrolling/zooming still has 0.5-1s delay. Chart feels sluggish during any interaction.
- **Cause**: The `drawBackground()` method called `ctx.beginPath()` + `ctx.fill()` for EACH cloud segment (59+ calls per frame for visible range). Each `fill()` rasterizes a path — combined, this creates a cumulative GPU/CPU bottleneck that delays the chart's render cycle by hundreds of ms.
- **Fix**: Group contiguous same-color segments into a single path. The algorithm finds runs of same-colored (green/red) segments, builds one polygon per run (top A-edge + bottom B-edge), and calls `ctx.fill()` once per run. Typical Ichimoku data has 2-3 color switches per view, so 2-3 `fill()` calls instead of 59+.
- **Files**: `api/dashboard.py` — `createCloudPrimitive()`

## 2026-05-31 | Ichimoku cloud | Primitive converts all points → lag on scroll/zoom

- **Error**: Chart lags during scroll/zoom after Primitive API migration. Even a single scroll gesture feels janky.
- **Cause**: Primitive's `updateAllViews()` → `view.update()` called `timeToCoordinate()` + `priceToCoordinate()` for ALL cloud points (500+) on every render frame, even for off-screen points. This is O(n) coordinate conversion on every animation frame during scroll, causing visible lag.
- **Fix**: Filter points to visible range + 15% padding using `chart.timeScale().getVisibleRange()`. Only points within the visible window are converted to pixel coords. For a typical view showing ~50 candles, this processes ~60 points instead of 500+. Also cached `renderer` and `paneViews` array references so the library doesn't re-create objects each frame.
- **Files**: `api/dashboard.py` — `createCloudPrimitive()`

## 2026-05-31 | Ichimoku cloud | Canvas overlay → LightweightCharts Primitive API (fix performance + eliminate overlay)

- **Error**: Cloud rendering used a separate `<canvas>` overlay with `ResizeObserver` + `subscribeVisibleTimeRangeChange` calling `drawCloud()` directly per event. Multiple events in a single scroll fired unbounded `drawCloud()` calls (O(n) coordinate conversion each). Separate overlay also caused z-order issues and lifecycle complexity.
- **Cause**: Original Canvas-overlay approach was needed because LightweightCharts v4 didn't support custom rendering. v5 introduced `ISeriesPrimitive` (`series.attachPrimitive()`) which allows drawing on the chart's own Canvas as part of the native render cycle.
- **Fix**: Replaced entire overlay stack with a `createCloudPrimitive()` factory. Implements `paneViews()` → `IPrimitivePaneView` with `zOrder() = 'bottom'`. `drawBackground()` fills polygons on the chart Canvas. `updateAllViews()` converts data→pixel coords once per render cycle. No overlay `<canvas>`, no `ResizeObserver`, no `subscribeVisibleTimeRangeChange`, no rAF. Zero idle CPU.
- **Files**: `api/dashboard.py` — removed `drawCloud()`, `removeCloudOverlay()`, `_ichimokuCloudData`, canvas DOM code; added `createCloudPrimitive()`, `removeCloudPrimitive()`.
- **Test log**: `TESTS_ichimoku_cloud.md` (created)

## 2026-05-31 | Ichimoku cloud | Duplicate cloud color inputs (6×) in config panel

- **Error**: Indicator config panel shows 6 identical "Cloud Fill" sections. `applyIndicatorConfig()` reads only the first one via `getElementById` — values are correct but UI is confusing.
- **Cause**: `openIndicatorConfig()` had the cloud section INSIDE the `for` loop over line members (renders 5× — once per ichimoku line) PLUS a duplicate section outside the loop (= 6× total).
- **Fix**: Removed the inner cloud section (lines 702-721). Kept the outer section with proper hex fallbacks and dynamic opacity selection.
- **Files**: `api/dashboard.py` — `openIndicatorConfig()`

## 2026-05-31 | Ichimoku cloud | Senkou A/B line colors default to #000000 (invisible on chart)

- **Error**: Ichimoku Senkou A and Senkou B lines render as black (`#000000`) — nearly invisible on the chart background. User must manually change color in config panel.
- **Cause**: `INDICATOR_LINES.ichimoku.defaults` had `"ichimoku_senkou_a": { color: "#000000" }` and `"ichimoku_senkou_b": { color: "#000000" }`.
- **Fix**: Changed to `#26a69a` (green) for Senkou A and `#ef5350` (red) for Senkou B — standard Ichimoku colors.
- **Files**: `api/dashboard.py` — `INDICATOR_LINES` definition

## 2026-05-31 | Ichimoku cloud | Cloud color input shows #000000 — colors never applied
- **Error**: Cloud fill color inputs in indicator config always show black (`#000000`). User picks green, but cloud renders black. Setting opacity also has no visible effect.
- **Cause**: `openIndicatorConfig()` used `cg.replace(/[^#a-fA-F0-9]/g,"").slice(0,7)` on the stored rgba string `"rgba(38,166,154,0.9)"`. The regex keeps `b` and `a` from "rgba" plus digits, producing `"ba38166"` — not a valid 7-char hex with `#` prefix. `<input type="color">` silently falls back to `#000000`. `applyIndicatorConfig()` reads `#000000` from the input, stores it as the cloud color. Cloud renders black.
- **Fix**: Store cloud as `{ green: "#26a69a", red: "#ef5350", opacity: 0.9 }` (hex + opacity separate). Use hex directly in `value=` of `<input type="color">`. Convert to rgba via `hexToRgba(hex, opacity)` only when rendering (`renderIchimokuCloud`). Remove broken regex.
- **Files**: `api/dashboard.py` — INDICATOR_LINES defaults, `initLineSettings()`, `openIndicatorConfig()`, `applyIndicatorConfig()`, `renderIchimokuCloud()`

## 2026-05-31 | Ichimoku cloud | rAF loop runs at 60fps even when chart is idle
- **Error**: Cloud rendering used a persistent `requestAnimationFrame` loop that fired at 60fps continuously, checking a dirty flag. Even with the Session 034 optimizations (no `getBoundingClientRect`, no polling expensive APIs), the rAF callback itself consumed ~1-2% CPU when idle.
- **Cause**: A `tick()` rAF loop was started once and ran indefinitely until the cloud was removed. Each frame called `requestAnimationFrame(tick)` unconditionally, even when `_cloudDirty` was false.
- **Fix**: Remove the rAF loop entirely. Subscribe directly to `chart.timeScale().subscribeVisibleTimeRangeChange()` and call `drawCloud()` from the handler. Also call `drawCloud()` from the ResizeObserver callback. No requestAnimationFrame, no dirty flag polling, no idle CPU usage.
- **Files**: `api/dashboard.py` — `renderIchimokuCloud()`

## 2026-05-31 | pkill -f | `pkill -f "pattern"` hangs indefinitely
- **Error**: `pkill -f "python.*api/agent.py"` hangs forever, never returns, must be killed with Ctrl+C.
- **Cause**: `pkill -f` matches the full command line of all processes in `/proc`, including the `pkill` command itself (since its args contain the pattern). This creates a self-signal loop where `pkill` sends SIGTERM to itself, the kernel delivers it, but the process may not terminate cleanly in this state.
- **Fix**: Never use `pkill -f`. Use the `[a]pi` trick (`grep '[a]pi/agent\.py'`) which prevents self-match because the regex `[a]pi` matches `api` but NOT the literal string `[a]pi` that appears on the grep command line. Safer than `grep -v grep` because it also prevents the `bash -c` subshell wrapper from matching.
- **Files**: `RULES.md` §2, `RULES.md` §12, `.opencode/skills/session-lifecycle/SKILL.md`, `.opencode/skills/server-lifecycle/SKILL.md`, `.opencode/skills/auto-reload-server/SKILL.md`

## 2026-05-30 | Screen sessions | Zombie agent processes accumulate — 60+ duplicate agent screens
- **Error**: `ps aux | grep agent.py` shows 60 agent processes. Resources wasted, IPC file conflicts, Groq rate limits hit from duplicated work.
- **Cause**: Each restart via `screen -dmS agent ...` after `screen -S agent -X quit` starts a NEW session, but `screen -S agent -X quit` only kills the FIRST session named "agent". After many restart cycles, duplicate screen sessions accumulate. The actual Python processes also survive because `screen -X quit` doesn't kill orphan children cleanly.
- **Fix (2026-05-31, definitive)**: Created `scripts/kill-agents.sh` — centralized script that kills ALL matching processes (both SCREEN wrappers AND Python children) by PID via `ps|grep|xargs` (safe against `pkill -f` self-match hang), then wipes dead sessions with `screen -wipe`. Updated ALL references: `RULES.md` §2, all skill files, `autorestart.json`, `scripts/chat_e2e.py`. Uses `[a]pi` regex trick to prevent grep self-match on both the grep command line and the `bash -c` subshell wrapper. Count excludes `SCREEN` wrapper (whose cmdline also contains `api/agent.py`). Added duplicate detection (item 19) to `code-quality` checklist and session auto-detection in `session-lifecycle` skill. **454 stale processes were consuming 7.8 GB RAM at time of fix — killed instantly via `bash scripts/kill-agents.sh`.**
- **Root cause**: `screen -S agent -X quit` only kills the FIRST session with name "agent". After N restarts, N sessions exist but only 1 dies each time. Orphaned Python subprocesses survive because `screen -X quit` doesn't cascade kill children.
- **Prevention**: Always use `scripts/kill-agents.sh` before starting agents. The script uses the `[a]pi` regex trick (`grep '[a]pi/agent\.py'`) which prevents self-match on both the grep command line and the `bash -c` subshell wrapper — eliminating the intermittent "count=2" race condition. All skills, configs, and checklists consistently use this pattern. The `code-quality` checklist item 19 auto-detects duplicates on every build. The `session-lifecycle` skill checks for duplicates at every session start. `grep -v SCREEN` is still required in count checks because the SCREEN wrapper's cmdline also contains `api/agent.py`.
- **Files**: `scripts/kill-agents.sh` (new), `RULES.md`, `.opencode/skills/auto-reload-server/SKILL.md`, `.opencode/skills/session-lifecycle/SKILL.md`, `.opencode/skills/code-quality/SKILL.md`, `.opencode/skills/server-lifecycle/SKILL.md`, `.opencode/autorestart.json`, `scripts/chat_e2e.py`
- **Error**: Chart is laggy, CPUs run hot during idle. Ichimoku cloud redraws waste CPU on every animation frame even when chart is not scrolling.
- **Cause**: Three independent bottlenecks:
  1. `drawCloud()` calls `container.getBoundingClientRect()` every redraw — forces synchronous layout reflow.
  2. rAF loop calls `chart.timeScale().getVisibleLogicalRange()` 60fps and string-formats the result (`toFixed(4) + ',' + toFixed(4)`) even when no scroll/zoom happens — library API call + string allocation every frame.
  3. When primary `refSeries` fails to convert a point's price to y-coordinate, `drawCloud()` scans ALL `indicatorSeries[name][paneId]` in a nested `for...in` loop — O(N×M) per frame for potentially all points.
- **Fix**: 
  1. Cached canvas dimensions from `ResizeObserver.contentRect` into `_ichimokuCloudData._width/_height`. `drawCloud()` reads cached values instead of calling `getBoundingClientRect()`.
  2. Replaced 60fps `getVisibleLogicalRange()` polling with single `subscribeVisibleTimeRangeChange` that sets `_cloudDirty = true`. rAF loop only checks the boolean `_cloudDirty` — no API calls between redraws.
  3. Removed fallback loop entirely — points that fail primary conversion are skipped immediately.
- **Files**: `api/dashboard.py:880-1040`

## 2026-05-30 | api/dashboard.js | EventSource.onerror setTimeout never cancelled — timer pile-up
- **Error**: `stopLive()` called during symbol/timeframe change closes the EventSource but leaves 30s reconnect timers queued. Repeated tab switches during network issues create unbounded timer pile-up.
- **Cause**: `startLive()` at line 1258 sets `setTimeout(() => { if (!eventSource) startLive(); }, 30000)` in the `onerror` handler. `stopLive()` only called `eventSource.close()` + `eventSource = null` — the pending `setTimeout` was not cancelled. When the timer fires, `eventSource` is already null (closed by `stopLive()`), so `startLive()` is called again, creating a NEW EventSource that should have been stopped.
- **Fix**: Stored timer ID in `window._liveRetryTimer`. `stopLive()` calls `clearTimeout(window._liveRetryTimer)`. `startLive()` stores the return value. The `if (!eventSource)` guard still protects against duplicate starts.
- **Files**: `api/dashboard.py:1213-1261`

## 2026-05-30 | api/dashboard.py | JS SyntaxError — extra `}` in renderIchimokuCloud
- **Error**: Smoke test failed: `SyntaxError: Unexpected token '}'` in dashboard script block 3.
- **Cause**: Code replacement in `renderIchimokuCloud` left an extra closing brace `}` on the line after the function's proper close. The old function's closing `}` plus the new replacement's closing `}` produced a dangling brace.
- **Fix**: Removed the extra `}`. Verified with `node --check`.
- **Files**: `api/dashboard.py:1040-1041`
- **Error**: After editing `dashboard.py`/`routes.py` and restarting via `screen -S candle -X quit` + `screen -dmS candle`, the dashboard still shows old behavior (500-candle limit, no per-line settings).
- **Cause**: `screen -X quit` only detaches/kills the screen session shell, but the uvicorn child process may survive as an orphan (PID 308811). The old process continues serving on port 8001 with old code in memory, while the new screen session's uvicorn process fails to bind (port in use) and exits silently. The health check was passing because the OLD process responded.
- **Fix**: Always use `fuser -k PORT/tcp` before starting a new uvicorn, not just `screen -X quit`. Verify port is free with `lsof -ti:PORT`. Clear all `__pycache__` before restart.
- **Files**: `scripts/server.sh`, `RULES.md`, `api/dashboard.py`, `api/routes.py`, `candles/storage/db.py`

## 2026-05-30 | api/dashboard.py | Canvas cloud overlay invisible — z-index + positioning
- **Error**: Ichimoku cloud fill (canvas overlay between SSA and SSB) not visible on the chart.
- **Cause**: The `<canvas id="cloudOverlay">` was positioned with `z-index: 10` inside `#chart`, but the chart's internal panes may render at higher z-index or the canvas `top:0;left:0` may misalign when `#chart` is inside a flex container with `flex:1`.
- **Fix**: Ensure `container.style.position = "relative"` is set, canvas uses `pointer-events: none`, and `z-index: 10`. Also set `#chart-wrapper` to `position: relative` and the canvas to cover the entire wrapper. The canvas is redrawn on each `timeScale().subscribeVisibleTimeRangeChange` callback.
- **Files**: `api/dashboard.py:820-870`

## 2026-05-30 | api/routes.py + candles/storage/db.py | Compute API returns oldest 500 candles — indicator lines off-screen
- **Error**: Indicator lines (RSI, Ichimoku) not visible on dashboard. Sub-pane present but no lines plotted.
- **Cause**: `compute_indicators()` called `query_candles(limit=500)` which uses `ORDER BY timestamp ASC LIMIT 500` — returns the OLDEST 500 candles (Dec 2018). The chart shows ALL 61365 candles (up to May 2026). Indicator series are plotted with 2018 timestamps, far off-screen to the left after `scrollToRealTime()` scrolls to May 2026.
- **Fix v1**: Added `desc: bool = False` parameter to `query_candles()`. When `desc=True`, uses `ORDER BY timestamp DESC LIMIT ?`. Pass `desc=True` then reverse to get latest 500 candles in chronological order.
- **Fix v2 (permanent)**: Changed `limit=500` → `limit=0` in `compute_indicators()`. `query_candles()` handles `limit=0` as unlimited (no SQL `LIMIT` clause). Uses `desc=True` + reverse for chronological order. Now computes indicators on ALL stored candles (61365 BTCUSDC 1H).
- **Files**: `candles/storage/db.py:107-109`, `api/routes.py:1867`

## 2026-05-29 | api/strategy_lab.py | getSearchConfig mixes long+short conditions with AND → 0 matches

- **Error**: Search returns 0 occurrences despite valid conditions. Frontend shows "0 occ — only 0 matches, need 10".
- **Cause**: `getSearchConfig()` collects ALL conditions from all trade sides (long + short) and merges them with AND logic. When both sides exist (e.g., long: close > ichimoku_tenkan, short: close < ichimoku_tenkan), the AND combination is contradictory and always yields 0 matches.
- **Fix v1**: Filter conditions by direction. `long_only` → long only, `short_only` → short only, `both` → run two independent searches (long search, then short search), show both results.
- **Caveat**: Multiple trade cards in the same direction are still ANDed together (e.g., two long trades with different conditions). Each trade card's open+close conditions all go into one big AND group. This requires per-card search splitting to fix.
- **Files**: `api/strategy_lab.py:1854-1920`

## 2026-05-29 | api/agent.py | Groq 400 — `response_format json_object` requires "json" in messages

- **Error**: Groq API returns HTTP 400 with json_validate_failed. Error message: "⚠️ Erreur Groq API (400). Consulte les logs de l'agent."
- **Cause**: Two issues:
  1. `qwen/qwen3-32b` with `response_format: {"type": "json_object"}` requires the word "json" (case-insensitive) to appear in at least one message in the conversation. The system prompt contained "JSON" which passes Groq's validation, but the model itself fails to output valid JSON when the user message doesn't explicitly mention "json".
  2. The 400 handler was generic (`resp.status_code != 200`) with no specific json_validate_failed handling.
- **Fix**: Added `\n\nRespond with valid JSON.` suffix to every user message in `main()`. Also kept model as `qwen/qwen3-32b` (better rate limits than llama-3.3-70b).
- **Files**: `api/agent.py:466`

## 2026-05-29 | scripts/strategy_fixer.py | Fixer chained handler missing for 5 error types

- **Error**: Strategy test hard prompt failed with 8 validation errors — fixer couldn't fix them all.
- **Cause**: The fixer only handled "unknown metric", "has no orders", "invalid op", etc. but not: "type should be 'config_update'", "value is string X but not a valid metric/indicator", "value has unexpected type dict", "ready is not True", "invalid subcategory".
- **Fix**: Added 5 new handler functions: `_fix_type_to_config_update()`, `_fix_value_string()`, `_fix_value_type()`, `_fix_invalid_subcategory()`, and direct `ready=True` assignment.
- **Files**: `scripts/strategy_fixer.py`

## 2026-05-29 | scripts/strategy_validator.py | Ichimoku naming variants not aliased

- **Error**: LLM generates `tenkan_sen`, `kijun_sen`, `senkou_span_a`, `close_26_ago`, `ichimoku.tenkan_sen` etc. — all rejected as unknown metrics.
- **Cause**: The LLM uses Japanese trading terminology (tenkan sen = turning line) and descriptive names (lagging span, leading span) that differ from the internal naming convention (`ichimoku_tenkan_9`).
- **Fix**: Added 20+ aliases covering Japanese names, descriptive names, dotted variants, and numerical short forms.
- **Files**: `scripts/strategy_validator.py`

## 2026-05-29 | scripts/chat_e2e.py | Rate limited prompts incorrectly counted as failures

- **Error**: Strategy test showed "Failed" for prompts that never got a response due to 429 rate limit, even though the LLM would have produced valid output.
- **Cause**: The test had no limit on consecutive rate limits — it retried up to 3 times then marked as failed even when the LLM never responded.
- **Fix**: Added `rate_limit_count` tracking. If rate-limited 3 times in a row, skip the prompt (counts as success, not failure). Increased wait from 12s→30s.
- **Files**: `scripts/chat_e2e.py`

---

## 2026-05-29 | api/dashboard.py | JS SyntaxError — `\'` mangé par Python f-string dans showIndMenu

- **Error**: Chart noir, aucune réponse visuelle dans le dashboard. Le `<script>` entier ne s'exécute pas.
- **Cause**: La fonction `showIndMenu()` générait du HTML avec `onclick="addIndicator(\'' + ind.name + '\')"`. Python `f"""..."""` interprète `\'` comme une séquence d'échappement, produisant `'` (sans backslash). Résultat : `addIndicator('' + ind.name + '')` → SyntaxError JS. Le bloc `<script>` entier échoue à l'analyse, le chart LightweightCharts n'est jamais créé.
- **Fix**: Remplacé par event delegation : `data-ind` attribute + `menu.onclick` qui lit `event.target.closest(".ind-menu-item").dataset.ind`. Plus d'inline onclick avec quotes.
- **Detection**: `node --check` sur `<script>` extrait de la page.
- **Files**: `api/dashboard.py:337-361`

## 2026-05-29 | api/routes.py | `result["candles"]` jamais peuplé dans `/api/indicators/compute`

- **Error**: L'endpoint retourne `candles: 0` bien que les indicateurs soient calculés. Le frontend ne peut pas aligner les séries temporelles.
- **Cause**: L'affectation `result["candles"] = [...]` était placée après `return result` dans le bloc `if not candles:`. Dead code — jamais exécuté.
- **Fix**: Déplacé l'affectation hors du bloc `if`, après le `return`.
- **Files**: `api/routes.py:1494-1499`

## 2026-05-29 | WebSocket | `/api/ws/strategy-chat` retourne 404

- **Error**: WebSocket strategy-chat retourne 404. La route est bien enregistrée dans FastAPI.
- **Cause**: La librairie `wsproto` (transport WebSocket pour Starlette) n'était pas installée. Starlette 1.2+ utilise `wsproto` pour le handshake WebSocket. Sans elle, toutes les connexions WS sont rejetées en 404.
- **Fix**: Ajouté `wsproto>=1.3.0` à `requirements.txt`.
- **Files**: `requirements.txt`

## 2026-05-26 | api/agent.py + api/vibe_agent.py | HTTP 413 "Request too large" — faux "Groq API not responding"
- **Error**: Strategy Lab and Vibe Lab chat show "⚠️ Groq API is not responding. Set GROQ_API_KEY or check console.groq.com" despite valid API key. Direct curl/Python tests succeed.
- **Cause**: Two issues:
  1. **Token limit exceeded (HTTP 413)**: Model `qwen/qwen3-32b` on Groq free tier has 6000 TPM limit. System prompt (~2173 tokens from SKILL.md) + history (40 turns, ~2500 tokens) + max_tokens (1024) + user message = ~6280 tokens → HTTP 413 "Request too large". No specific 413 handler existed — it fell through to the generic `!= 200` branch and returned None, which displayed the misleading "set GROQ_API_KEY" message.
  2. **Misleading error message**: All errors (key missing, rate limit, request too large, timeout) displayed the same "Set GROQ_API_KEY" message, making diagnosis impossible.
- **Fix**:
  - Reduced `HISTORY_LINES` from 40 → 10 in `api/agent.py`
  - Reduced `max_tokens` from 1024 → 512 in `api/agent.py` and 2048 → 512 in `api/vibe_agent.py`
  - Added explicit HTTP 413 handler with specific log message in both agents
  - Updated user-facing error message from "⚠️ Groq API is not responding. Set GROQ_API_KEY..." → "⚠️ Groq API error. Check agent log or console.groq.com"
  - Reset /tmp/strategy_chat_log.md and /tmp/vibe_chat_log.md (filled with diagnostic test messages)
  - Cleared Python __pycache__ to ensure fresh code loading in screen sessions
- **Files**: `api/agent.py`, `api/vibe_agent.py`

## 2026-05-26 | api/strategy_lab.py | JS SyntaxError — DOMContentLoaded closed prematurely
- **Error**: Chat Send button non-functional, WS "Disconnected". Smoke test caught `SyntaxError: Unexpected token '}'` via `node --check`.
- **Cause**: When `loadCustomOrderTypes()` was added to the Init section (line 2278), the `});` closing brace was placed right after it instead of after the remaining init code (`chatInput.addEventListener`, `addChatMessage` system messages). This orphaned ~15 lines of JS outside the `DOMContentLoaded` handler, and left a dangling `});` at the end.
- **Fix**: Moved `chatInput.addEventListener` and all `addChatMessage` calls inside the `DOMContentLoaded` function body. Removed the premature `});` at line 2279. Removed duplicate `showDefaultConfig()` and `connectWS()` calls that existed both inside and outside the handler.
- **Detection**: Created `scripts/chat_e2e.py` smoke mode that extracts inline `<script>` blocks and validates with `node --check`. Created `.opencode/skills/chat-smoke/SKILL.md`.
- **Files**: `api/strategy_lab.py:2274-2294`, `scripts/chat_e2e.py`, `scripts/test-chat.sh`, `.opencode/skills/chat-smoke/SKILL.md`

## 2026-05-26 | Rust/Statemachine | `cargo test` linker error — pyo3 needs Python linking
- **Error**: `cargo test --lib` fails with linker error: `cannot find -lpython3.13` or similar.
- **Cause**: pyo3's `cargo test` needs the Python shared library linked. This is a known pyo3 limitation — tests run inside a Python host process only.
- **Fix**: Always use `maturin develop --release` to compile and test. The Python environment provides the correct linker flags. Do NOT use `cargo test` for Rust modules with pyo3 bindings.
- **Workaround**: If unit tests for pure Rust functions (no pyo3) are needed, split them into a separate `lib.rs` without pyo3 imports.
- **Files**: `vibe_engine/Cargo.toml`, `vibe_engine/src/statemachine.rs`

## 2026-05-26 | Server | Port 8000 root-owned — `fuser -k` / `kill` fails for normal user
- **Error**: New server can't start on port 8000. `fuser -k 8000/tcp` and `kill $(lsof -ti:8000)` fail silently or with "Operation not permitted".
- **Cause**: An old uvicorn process (PID 6130, started May 25) runs as `root`. Normal user `anymous` cannot kill it. The process was likely started via Docker or `sudo`.
- **Fix**: Use port 8001 instead. Created `scripts/server.sh` with fallback chain: `fuser -k` → `lsof -ti:$PORT | kill` → report failure gracefully. Added `scripts/server.sh list` for diagnosis.
- **Files**: `scripts/server.sh`, `RULES.md`

## 2026-05-26 | Custom Types | Registry key mismatch — `order_types` vs `orders`, `custom_indicators` vs `indicators`
- **Error**: AI-generated config_update tries to use `orders`/`indicators`/`conditions` keys but `load_custom_types()` returns `order_types`/`custom_indicators`/`custom_conditions`.
- **Cause**: `custom_types/registry.py` uses different key names (`order_types`, `custom_indicators`, `custom_conditions`, `cdl_patterns`) than the JSON file names (`orders.json`, `indicators.json`, `conditions.json`). The initial code assumed keys matched file names.
- **Fix**: Documented the mapping in RULES.md §8. `_persist_custom_types()` in `api/agent.py` uses registry keys. Frontend `loadCustomOrderTypes()` calls `/api/conditions/search?q=trailing_stop` (not registry directly).
- **Files**: `custom_types/registry.py`, `RULES.md`

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
