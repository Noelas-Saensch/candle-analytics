---
name: chat-smoke
description: >
  End-to-end smoke and chat testing for Strategy Lab and Vibe Lab.
  Catches JS syntax errors, HTTP failures, and WebSocket pipeline
  issues before they reach the browser.
---

# Chat Smoke Test

## Problem

The chat in Strategy Lab and Vibe Lab breaks frequently. Root causes include:
- **JS syntax errors** from Python `"""` triple-quoted strings eating backslashes
- **WS protocol mismatch** (wrong `type` field in response)
- **Stale server processes** serving old code
- **CDN blocking** (Chart.js without `defer`)
- **ES5 incompatibility** (`const`/`let`/`?.`/`for...of`)

These are silent failures — the page loads, but Send does nothing, WS stays "Disconnected".

## Solution

Two-tier test runner in `scripts/chat_e2e.py`:

### Smoke mode (zero dependencies)

```bash
python scripts/chat_e2e.py smoke [--port 8001]
```

Checks:
1. HTTP 200 on `/strategy-lab`, `/vibe-lab`, `/api/health`
2. Extracts inline `<script>` blocks from each page
3. Validates JS syntax via `node --check`

Takes ~0.5s. Detects ~80% of chat-breaking bugs.

### Chat E2E mode (requires Playwright)

```bash
pip install playwright
playwright install chromium
python scripts/chat_e2e.py chat [--port 8001]
```

Checks:
1. Full page load in headless Chromium
2. Chat input exists and is interactive
3. Types a test message and clicks Send
4. Captures `console.error()` output
5. Reports any JS runtime errors

Takes ~10s. Catches WS protocol issues, runtime errors, DOM problems.

### Entry point

```bash
./scripts/test-chat.sh        # same as "all"
./scripts/test-chat.sh smoke  # quick check
./scripts/test-chat.sh chat   # full e2e
./scripts/test-chat.sh all    # smoke + chat
```

## Integration

Add to `code-quality` skill's pre-declaration checklist:
```bash
./scripts/test-chat.sh smoke --port 8001
```

## Trigger

Run this skill when:
- A PR changes `api/strategy_lab.py` or `api/vibe_lab.py`
- The chat Send button is reported as non-functional
- The WS shows "Disconnected" after server restart
- Before marking any JS-heavy build as "done"
