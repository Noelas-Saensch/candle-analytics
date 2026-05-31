---
name: test-safeguard
description: >
  Per-feature test records for complex or bug-prone features.
  Automatically create a test log when a feature causes 2-3+ bugs/errors,
  then append to it on every subsequent test round.
---

# Test Safeguard

## When to activate

**Trigger:** A feature has caused 2+ distinct bugs, or a single bug required
3+ rounds of trial-and-error to fix.

If you find yourself testing the same thing in different ways across sessions,
open a test log.

## How it works

1. A `.md` file per complex feature: `TESTS_<feature>.md` in the project root.
2. Each file contains **timestamped entries** — one per test session/round.
3. Each entry records: what was tested, how, code changes before the test,
   parameters, observed results, outcome (PASS/FAIL/Partial).
4. A summary at the top tracks overall status and links to related files.

## Structure

When activated, load the template (`TEMPLATE.md` in this directory), create the
test log file if it doesn't exist, then append a new entry.

## Integration with ERRORS.md

After creating a test log, add a line to ERRORS.md under the relevant error
entry:
```
- **Test log**: `TESTS_<feature>.md`
```

For README, ROADMAP, or CHRONOLOGIE — add a bullet linking to the test log
when the feature is discussed.

## Per-entry template

Each test round entry:

```markdown
### 2026-05-31 — Round 1

**Objective**: What are we trying to verify?

**Code state**: What was changed since the last test round?
```
- `api/dashboard.py` — changed X in function Y
```

**Test method**: Manual / smoke / curl / etc.
- Open chart, add indicator X, set params Y, observe Z
- Run `npm run smoke`

**Parameters used**: [exchange, symbol, timeframe, indicator params]

**Results**: What happened?
- PASS: cloud fill renders correctly at all zoom levels
- Regression: chart lags when scrolling

**Observations**: Additional notes, screenshots, unexpected behavior

**Outcome**: PASS / FAIL / Partial
- **Root cause** (if FAIL): brief explanation
- **Next steps**: what to try next
```

## Lifecycle

- **Create**: when the feature triggers 2+ errors
- **Update**: after every test round
- **Close**: when the feature is stable and has 0 open bugs for 30 days
  (append a closing entry, leave the file in place)
