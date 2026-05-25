---
name: pyjs-quote-debug
description: >
  Detects and fixes Python-to-JS quoting issues where backslashes are silently
  eaten inside Python triple-quoted strings containing inline HTML/JavaScript.
---

# Python-to-JS Quote Debug

## When to run

Trigger: when asked to "check quotes", "fix quotes", "debug js quoting",
"pyjs quotes", or when investigating broken onclick/event handlers in the
dashboard, strategy-lab, or vibe-lab pages.

---

## The bug

Inside Python `"""..."""` triple-quoted strings:

| Python source | Actual output | JS sees | Correct? |
|---------------|---------------|---------|----------|
| `\\'`         | `\'`          | `\'`    | YES      |
| `\'`          | `'`           | `'`     | **NO** — backslash eaten |
| `\\"`         | `\"`          | `\"`    | YES      |
| `\"`          | `"`           | `"`     | **NO** — backslash eaten |

The wrong patterns (`\'`, `\"`) look correct in the Python source but produce
broken JavaScript because Python consumes the backslash as part of its own
escape processing.

## Check

```bash
bash scripts/check-pyjs-quotes.sh
```

This scans every `.py` file in `api/` and reports. Pass specific files to
limit the check:

```bash
bash scripts/check-pyjs-quotes.sh api/strategy_lab.py api/vibe_lab.py
```

Reports:

1. **Suspect quoting** — `\'` or `\"` that might lose their backslash
2. **Empty-strings** — `''` where a backslash-escaped quote was likely intended
3. **JS syntax errors** — extracted onclick handlers checked with `node --check`

## Fix

If the script reports errors, the fix is to double the backslash:

```python
# WRONG — backslash eaten by Python
onclick="removeTrade(\'' + side + '\')"

# CORRECT — backslash reaches JS
onclick="removeTrade(\\'' + side + '\\')"
```

### Automated sed

For quick bulk fix on a single file:

```bash
# Fix single-quote escaping
sed -i "s/\\\\'/\\\\\\\\'/g" api/strategy_lab.py

# Fix double-quote escaping
sed -i 's/\\\\"/\\\\\\\\"/g' api/strategy_lab.py
```

**Caution**: only run sed on lines inside `"""..."""` that contain JS event
handlers. The pattern `\'` inside a regular Python string (not triple-quoted)
is fine.

---

## 3 patterns to watch for

### 1. onclick with JS string concatenation

```python
# WRONG — \'' produces just '' (empty string) instead of \'
onclick="addCondGroup(\'' + side + '\')"

# CORRECT
onclick="addCondGroup(\\'' + side + '\\')"
```

Why it breaks: the JS handler receives `addCondGroup('' + side + '')` where
`''` is an empty string literal. The argument becomes just `side` instead of
the intended value with quote boundaries.

### 2. Single backslash before quote in `"""..."""`

```python
# WRONG — \' becomes ' (backslash lost)
onclick="showAISuggest(this,\'cond\')"

# CORRECT — \\' becomes \' (backslash preserved)
onclick="showAISuggest(this,\\'cond\\')"
```
This only matters if the JS needs the backslash (e.g. inside a JS string
literal). Simple cases like `switchTab(\'chart\')` work fine because the
backslash is not needed in the JS output.

### 3. Any JS escape sequence needing a literal backslash

```python
# WRONG — \n becomes newline character instead of literal \n
msg = "Tooltip says: use \\n for newline"

# CORRECT
msg = "Tooltip says: use \\\\n for newline"
```

This applies to any backslash-based JS escape: `\n`, `\t`, `\r`, `\\`, etc.
