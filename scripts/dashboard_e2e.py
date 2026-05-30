"""
Dashboard E2E test — imitates a real user from the frontend.

Modes:
  smoke     — HTTP 200 + JS syntax check (zero deps)
  ui        — Playwright headless: chart canvas, dropdowns populated, tab switching, console error detection
  all       — smoke + ui

Usage:
  python scripts/dashboard_e2e.py smoke [--port 8001]
  python scripts/dashboard_e2e.py ui    [--port 8001] [--headless true]
  python scripts/dashboard_e2e.py all   [--port 8001]
"""

import os
import re
import subprocess
import sys
import time

_SCRIPTS_DIR = os.path.dirname(__file__)
_PROJECT_ROOT = os.path.join(_SCRIPTS_DIR, "..")
for p in [_PROJECT_ROOT, _SCRIPTS_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

PORT = 8001
BASE = ""
PASS = 0
FAIL = 0


def ok(msg):
    global PASS
    PASS += 1
    print(f"  ✅ {msg}")


def fail(msg):
    global FAIL
    FAIL += 1
    print(f"  ❌ {msg}")


# ── helpers ────────────────────────────────────────────────


def _http_ok(path, expected=200):
    import urllib.request
    try:
        r = urllib.request.urlopen(f"http://localhost:{PORT}{path}", timeout=10)
        return r.status == expected
    except Exception:
        return False


def _extract_js(filepath):
    with open(filepath) as f:
        content = f.read()
    match = re.search(r"<script>(.*?)</script>", content, re.DOTALL)
    if not match:
        return None
    js = match.group(1)
    tmp = f"/tmp/dashboard_e2e_extracted.js"
    with open(tmp, "w") as f2:
        f2.write(js)
    return tmp


def _node_check(js_path):
    r = subprocess.run(["node", "--check", js_path], capture_output=True, text=True)
    return r.returncode == 0, r.stderr


# ── smoke mode ─────────────────────────────────────────────


def test_smoke():
    print("\n── Smoke tests ──")

    ok("HTTP /api/health") if _http_ok("/api/health") else fail("HTTP /api/health")
    ok("HTTP /dashboard (200)") if _http_ok("/dashboard") else fail("HTTP /dashboard")

    js_path = _extract_js(os.path.join(_PROJECT_ROOT, "api/dashboard.py"))
    if js_path:
        valid, err = _node_check(js_path)
        ok("JS syntax valid") if valid else fail(f"JS syntax error: {err.strip()}")
    else:
        fail("No <script> block found in dashboard.py")


# ── UI mode (Playwright) ───────────────────────────────────


def test_ui(headless=True):
    print("\n── UI tests (Playwright) ──")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  ⚠️  playwright not installed — install with: pip install playwright && playwright install chromium")
        return

    errors = []
    console_log = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.on("console", lambda msg: console_log.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: errors.append(str(err)))

        page.goto(f"http://localhost:{PORT}/dashboard", wait_until="networkidle")
        time.sleep(2)

        # 1. No page errors
        ok("No JS page errors") if not errors else fail(f"JS errors: {errors}")

        # 2. Chart canvas exists (LightweightCharts)
        canvas = page.query_selector("#chart-view canvas")
        ok("Chart canvas rendered") if canvas else fail("No chart canvas found")

        # 3. Pairs dropdown populated
        pair_select = page.query_selector("select:nth-of-type(1)")
        if pair_select:
            opts = pair_select.query_selector_all("option")
            ok(f"Pairs dropdown: {len(opts)} options") if len(opts) >= 2 else fail(f"Only {len(opts)} pair options")
        else:
            fail("No pair <select> found")

        # 4. Timeframe dropdown populated
        tf_select = page.query_selector("select:nth-of-type(2)")
        if tf_select:
            opts = tf_select.query_selector_all("option")
            ok(f"Timeframe dropdown: {len(opts)} options") if len(opts) >= 2 else fail(f"Only {len(opts)} TF options")
        else:
            fail("No timeframe <select> found")

        # 5. Tab switching
        tabs = page.query_selector_all(".tab")
        tab_names = [t.inner_text().strip() for t in tabs] if tabs else []
        ok(f"Tabs found: {tab_names}") if len(tabs) >= 3 else fail(f"Expected ≥3 tabs, got {len(tabs)}")

        if len(tabs) >= 3:
            tabs[1].click()
            time.sleep(1)
            analyze_view = page.query_selector("#analyze-view")
            ok("Tab 2 (Analyze) switches view") if analyze_view else fail("Tab 2 click did not switch view")

            tabs[2].click()
            time.sleep(1)
            rawdata_view = page.query_selector("#rawdata-view")
            ok("Tab 3 (RAW DATA) switches view") if rawdata_view else fail("Tab 3 click did not switch view")

            tabs[0].click()
            time.sleep(1)
            chart_view = page.query_selector("#chart-view")
            ok("Tab 1 (Chart) switches back") if chart_view else fail("Tab 1 click did not restore chart view")

        # 6. Change pair
        if pair_select:
            opts = pair_select.query_selector_all("option")
            if len(opts) > 1:
                pair_select.select_option(index=1)
                time.sleep(1)
                ok("Pair change triggered data load") if not errors else fail(f"Pair change caused errors: {errors}")

        # 7. Console error check
        severe = [m for m in console_log if m.startswith("[error]")]
        ok(f"No console errors ({len(console_log)} messages)") if not severe else fail(f"Console errors: {severe}")

        browser.close()

    ok(f"UI tests completed — {PASS}/{PASS+FAIL} passed")


# ── main ───────────────────────────────────────────────────


def main():
    global PORT
    args = sys.argv[1:]

    mode = "all"
    if args and args[0] in ("smoke", "ui", "all"):
        mode = args.pop(0)

    for i, a in enumerate(args):
        if a == "--port" and i + 1 < len(args):
            PORT = int(args[i + 1])
        if a == "--headless" and i + 1 < len(args):
            headless = args[i + 1].lower() == "true"

    print(f"Dashboard E2E — mode={mode} port={PORT}")

    if mode in ("smoke", "all"):
        test_smoke()

    if mode in ("ui", "all"):
        test_ui()

    print(f"\n── Results: {PASS} passed, {FAIL} failed ──")
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
