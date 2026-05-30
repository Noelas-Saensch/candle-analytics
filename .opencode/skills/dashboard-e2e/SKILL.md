# Dashboard E2E Skill

Catches chart rendering issues, JS runtime errors, CDN failures, empty dropdowns, and broken tab switching — before they reach the user's browser.

## Usage

```bash
# Quick smoke test (zero deps, < 1s)
./scripts/test-dashboard.sh smoke

# Full UI test (Playwright headless, ~10s)
./scripts/test-dashboard.sh ui

# Both (default)
./scripts/test-dashboard.sh all

# Custom port
./scripts/test-dashboard.sh all --port 8001

# Visible browser (debugging)
./scripts/test-dashboard.sh ui --headless false
```

## What it tests

### Smoke mode (zero dependencies)
- `/api/health` returns 200
- `/dashboard` returns 200
- JS syntax validated via `node --check`

### UI mode (Playwright)
- No JS page errors (ReferenceError, TypeError, etc.)
- Chart canvas rendered (LightweightCharts)
- Pairs dropdown has ≥2 options
- Timeframe dropdown has ≥2 options
- Tab switching: Chart → Analyze → RAW DATA → Chart
- Pair change triggers data load
- Console error detection (network failures, 404s, etc.)

## When to run

- After any change to `api/dashboard.py`
- After any change to CDN URLs or script loading strategy
- Before marking chart-related work as done
- After server restart to verify the dashboard loads correctly

## Dependencies

- `smoke` mode: `python3`, `node` (any version)
- `ui` mode: `playwright` Python package + chromium browser
  ```bash
  pip install playwright
  playwright install chromium
  ```

## Failed test checklist

| Symptom | Check |
|---------|-------|
| Chart canvas missing | CDN URL in `<head>`, try/catch around ChartZoom |
| Tabs not clickable | `defer` missing on CDN scripts |
| Dropdowns empty | `/api/pairs` returns data, LoadPairs() not crashing |
| Console "Failed to load resource" | CDN domain blocked by network/ad-blocker |
