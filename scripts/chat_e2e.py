"""
End-to-end chat test for Strategy Lab.
Modes:
  smoke        — HTTP 200 + JS syntax check (zero deps)
  strategy     — Sends 3 strategy prompts (simple, medium, hard), validates responses,
                 auto-fixes common errors, retries with LLM if needed, loops up to 3x.
  all          — smoke + strategy

Usage:
  python scripts/chat_e2e.py smoke [--port 8001]
  python scripts/chat_e2e.py strategy [--port 8001]
  python scripts/chat_e2e.py all [--port 8001]
"""

import json
import os
import re
import subprocess
import sys
import time
import uuid

_SCRIPTS_DIR = os.path.dirname(__file__)
_PROJECT_ROOT = os.path.join(_SCRIPTS_DIR, "..")
for p in [_PROJECT_ROOT, _SCRIPTS_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

PORT = 8001
AGENT_TIMEOUT = 25
MAX_ITERATIONS = 3

PROMPTS = [
    {
        "name": "hard",
        "content": "Ichimoku BTCUSDC 1H: long when close above tenkan and kijun, above senkou A and B, chikou above close 26 ago",
    },
    {
        "name": "medium",
        "content": "SMA crossover: buy when sma20 crosses above sma50 on BTCUSDC 1H, short reverse",
    },
    {
        "name": "simple",
        "content": "rsi(14) < 30 buy, > 70 sell BTCUSDC 1H",
    },
]


def http_ok(path, expected_status=200):
    import urllib.request
    try:
        resp = urllib.request.urlopen(f"http://localhost:{PORT}{path}", timeout=10)
        return resp.status == expected_status
    except Exception:
        return False


def node_check_js(html_path):
    with open(html_path) as f:
        html = f.read()
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    if not scripts:
        return True, "no scripts found"
    for i, js in enumerate(scripts):
        js = js.strip()
        if not js:
            continue
        if js.startswith('{') or js.startswith('"use'):
            continue
        import tempfile
        tmp = tempfile.mktemp(suffix='.js')
        try:
            with open(tmp, 'w') as f:
                f.write(js)
            r = subprocess.run(['node', '--check', tmp], capture_output=True, text=True, timeout=10)
            if r.returncode != 0:
                return False, f"script block {i}: {r.stderr.strip()}"
        finally:
            os.unlink(tmp)
    return True, f"{len(scripts)} script blocks OK"


# ───────────────────── smoke mode ─────────────────────

def _check_page_js(path, name, errors):
    import urllib.request, tempfile
    try:
        html = urllib.request.urlopen(f"http://localhost:{PORT}{path}", timeout=10).read().decode()
        tmp = tempfile.mktemp(suffix='.html')
        with open(tmp, 'w') as f:
            f.write(html)
        ok, msg = node_check_js(tmp)
        if ok:
            print(f"  ✅ {name} JS syntax: {msg}")
        else:
            errors.append(f"{name} JS: {msg}")
            print(f"  ❌ {name} JS: {msg}")
        return html
    except Exception as e:
        errors.append(f"{name} fetch: {e}")
        print(f"  ❌ {name} fetch: {e}")
        return None


def _check_dashboard_html(html, errors):
    """Check dashboard-specific HTML elements and API endpoints."""
    checks = {
        "chart container": 'id="chart"',
        "chart wrapper": 'id="chart-wrapper"',
        "controls bar": 'class="controls-bar"',
        "gear button": 'class="gear-btn"',
        "settings modal": 'id="settingsModal"',
        "settings overlay": 'id="settingsOverlay"',
        "crosshair legend": 'id="crosshairLegend"',
        "exchange select": 'id="exchange"',
        "symbol select": 'id="symbol"',
        "timeframe select": 'id="timeframe"',
        "regression toggle": 'onchange="toggleRegression()"',
        "LightweightCharts CDN": 'lightweight-charts',
    }
    for name, needle in checks.items():
        if needle in html:
            print(f"  ✅ Dashboard HTML: {name}")
        else:
            errors.append(f"Dashboard HTML: missing {name}")
            print(f"  ❌ Dashboard HTML: missing {name}")

    # Key JS globals — check they appear in script blocks
    js_globals = [
        "chart = LightweightCharts.createChart",
        "candleSeries = chart.addSeries",
        "name: \"volume\"",
        "indicatorSeries = {}",
        "function initChart",
        "function renderIndicatorSeries",
        "function loadPairs",
        "function toggleRegression",
        "function loadChartSettings",
        "function toggleSettings",
        "function closeSettings",
        "function applyChartSettings",
        "function resetChartSettings",
        "subscribeCrosshairMove",
        "CHART_SETTINGS_KEY",
    ]
    for g in js_globals:
        if g in html:
            print(f"  ✅ Dashboard JS: {g.split('(')[0]}")
        else:
            errors.append(f"Dashboard JS: missing {g.split('(')[0]}")
            print(f"  ❌ Dashboard JS: missing {g.split('(')[0]}")

    # Critical API endpoints
    api_checks = [
        ("/api/pairs", "/api/pairs"),
        ("/api/candles/count", "/api/candles/count"),
    ]
    for name, path in api_checks:
        if http_ok(path):
            print(f"  ✅ Dashboard API: {name} HTTP 200")
        else:
            errors.append(f"Dashboard API: {name} failed")
            print(f"  ❌ Dashboard API: {name} failed")


def _check_dashboard_candles(errors):
    """Try fetching a candle snapshot to verify the data pipeline."""
    import urllib.request, json
    try:
        # Fetch pairs to get a valid exchange/symbol
        r = urllib.request.urlopen(f"http://localhost:{PORT}/api/pairs", timeout=10)
        data = json.loads(r.read())
        pairs = data.get("pairs", [])
        if not pairs:
            print("  ⚠️  Dashboard candles: no pairs to test")
            return
        ex = pairs[0]["exchange"]
        sym = pairs[0]["symbol"]
        url = f"http://localhost:{PORT}/api/candles?exchange={ex}&symbol={sym}&timeframe=1h&limit=5"
        r2 = urllib.request.urlopen(url, timeout=15)
        cdata = json.loads(r2.read())
        candles = cdata.get("candles", [])
        if len(candles) > 0:
            print(f"  ✅ Dashboard candles: {len(candles)} candles from {ex}/{sym}")
        else:
            # Candles can be legitimately empty (no data fetched yet) — warn, don't fail
            print(f"  ⚠️  Dashboard candles: empty from {ex}/{sym} (may need data fetch)")
    except Exception as e:
        errors.append(f"Dashboard candles: {e}")
        print(f"  ❌ Dashboard candles: {e}")


def _check_convert_html(html, errors):
    """Check convert page HTML elements and API endpoint."""
    checks = {
        "direction selector": 'id="direction"',
        "input code area": 'id="inputCode"',
        "output code area": 'id="outputCode"',
        "convert button": 'id="convertBtn"',
        "exchange select": 'id="exchange"',
        "symbol select": 'id="symbol"',
        "timeframe select": 'id="timeframe"',
        "input header": 'id="inputHeader"',
        "output header": 'id="outputHeader"',
        "loading indicator": 'id="loading"',
        "error message": 'id="errorMsg"',
    }
    for name, needle in checks.items():
        if needle in html:
            print(f"  ✅ Convert HTML: {name}")
        else:
            errors.append(f"Convert HTML: missing {name}")
            print(f"  ❌ Convert HTML: missing {name}")

    js_globals = [
        "function doConvert",
        "function copyOutput",
        "function showError",
        "directionLabels",
        "/api/convert",
    ]
    for g in js_globals:
        if g in html:
            print(f"  ✅ Convert JS: {g.split('(')[0]}")
        else:
            errors.append(f"Convert JS: missing {g.split('(')[0]}")
            print(f"  ❌ Convert JS: missing {g.split('(')[0]}")

    # Test POST /api/convert with invalid data — should return 400 or 502 (not 404)
    import urllib.request, json
    try:
        req = urllib.request.Request(
            f"http://localhost:{PORT}/api/convert",
            data=json.dumps({"direction":"nl_python","code":"test"}).encode(),
            headers={"Content-Type":"application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=15)
        if resp.status == 200:
            print("  ✅ Convert API: /api/convert HTTP 200")
        else:
            errors.append(f"Convert API: {resp.status}")
            print(f"  ❌ Convert API: {resp.status}")
    except urllib.error.HTTPError as e:
        if e.code in (400, 422, 502):
            print(f"  ✅ Convert API: /api/convert HTTP {e.code} (expected—no API key or invalid input)")
        else:
            errors.append(f"Convert API: HTTP {e.code}")
            print(f"  ❌ Convert API: HTTP {e.code}")
    except Exception as e:
        errors.append(f"Convert API: {e}")
        print(f"  ❌ Convert API: {e}")


def smoke_test():
    errors = []
    pages = [
        ("/strategy-lab", "Strategy Lab"),
        ("/api/health", "Health"),
        ("/dashboard", "Dashboard"),
        ("/convert", "Convert"),
    ]
    for path, name in pages:
        if http_ok(path):
            print(f"  ✅ {name} ({path}) HTTP 200")
        else:
            errors.append(f"{name} ({path}) failed")
            print(f"  ❌ {name} ({path}) failed")

    import urllib.request, tempfile
    for path, name in [("/strategy-lab", "strategy_lab"), ("/dashboard", "dashboard"), ("/convert", "convert")]:
        html = _check_page_js(path, name, errors)
        if html:
            if path == "/dashboard":
                _check_dashboard_html(html, errors)
            elif path == "/convert":
                _check_convert_html(html, errors)

    if errors:
        # Don't bother testing candles if basic checks failed
        return errors

    _check_dashboard_candles(errors)
    return errors


# ───────────────────── strategy mode ─────────────────────

def restart_servers(port=8001):
    """Kill zombie processes, clean IPC, start server, wait for health."""
    print("  🔄 Restarting servers...")

    # Force-kill ALL duplicates using centralized script (handles any number)
    SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
    kill_agents_script = os.path.join(SCRIPTS_DIR, "kill-agents.sh")
    server_script = os.path.join(SCRIPTS_DIR, "server.sh")
    if os.path.exists(kill_agents_script):
        subprocess.run(["bash", kill_agents_script, "--all"], capture_output=True, timeout=10)
    else:
        # Fallback: direct kill (safe method, no pkill -f)
        subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True, timeout=5)
        time.sleep(1)
        for s in ["agent", "vibe-agent", "candle"]:
            subprocess.run(["screen", "-S", s, "-X", "quit"], capture_output=True, timeout=5)
        time.sleep(1)
        subprocess.run("rm -f /tmp/*chat_req_*.json /tmp/*chat_res_*.json /tmp/vibe_chat_req_*.json /tmp/vibe_chat_res_*.json", shell=True, timeout=5)

    time.sleep(1)
    base = "/home/anymous/PROJETS/candle-analytics"
    subprocess.run(["screen", "-dmS", "agent", "bash", "-c",
                    f"cd {base} && .venv/bin/python api/agent.py"], timeout=10)
    time.sleep(1)
    subprocess.run(["screen", "-dmS", "vibe-agent", "bash", "-c",
                    f"cd {base} && .venv/bin/python api/vibe_agent.py"], timeout=10)
    time.sleep(1)
    # Use server.sh for reliable start, or fallback to direct uvicorn
    if os.path.exists(server_script):
        r = subprocess.run(["bash", server_script, "start", str(port)], capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            print(f"  ✅ Servers healthy via server.sh")
            return True
        print(f"  ⚠️  server.sh start failed (rc={r.returncode}): {r.stderr[:200]}")
        # fall through to direct start
    subprocess.run(["screen", "-dmS", "candle", "bash", "-c",
                    f"cd {base} && .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port {port}"], timeout=10)

    for i in range(15):
        time.sleep(1)
        try:
            import urllib.request
            r = urllib.request.urlopen(f"http://localhost:{port}/api/health", timeout=3)
            if r.status == 200:
                print(f"  ✅ Servers healthy after {i+1}s")
                return True
        except Exception:
            pass
    print("  ❌ Servers failed to start")
    return False


def _send_request(content, req_id=None):
    if req_id is None:
        req_id = str(uuid.uuid4())[:8]
    req = {"id": req_id, "type": "message", "content": content}
    path = f"/tmp/strategy_chat_req_{req_id}.json"
    with open(path, "w") as f:
        json.dump(req, f)
    return req_id


def _poll_response(req_id, timeout=AGENT_TIMEOUT):
    path = f"/tmp/strategy_chat_res_{req_id}.json"
    for i in range(timeout):
        time.sleep(1)
        if os.path.exists(path):
            try:
                with open(path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
    return None


def _is_rate_limited(resp: dict) -> bool:
    content = resp.get("content", "")
    return "429" in content or "rate" in content.lower() or "Limite de taux" in content


def _try_prompt(prompt_def, iteration=0, rate_limit_count=0) -> tuple[bool, list[str]]:
    """Send a prompt, validate, fix, retry. Returns (success, errors)."""
    try:
        from scripts.strategy_validator import validate_prompt_response
        from scripts.strategy_fixer import fix_errors
    except ImportError:
        from strategy_validator import validate_prompt_response
        from strategy_fixer import fix_errors

    name = prompt_def["name"]
    content = prompt_def["content"]
    print(f"\n  📝 [{name}] Sending: {content[:60]}...")

    req_id = _send_request(content)
    resp = _poll_response(req_id)

    if resp is None:
        return False, [f"[{name}] No response from agent after {AGENT_TIMEOUT}s"]

    # Handle rate limiting
    if _is_rate_limited(resp):
        rate_limit_count += 1
        if rate_limit_count >= 3:
            print(f"  ⏭️  [{name}] Rate limited {rate_limit_count}x, skipping")
            return True, []  # Skip, not fail
        wait = 30
        print(f"  ⏳ [{name}] Rate limited ({rate_limit_count}x), waiting {wait}s...")
        time.sleep(wait)
        if iteration < MAX_ITERATIONS:
            return _try_prompt(prompt_def, iteration + 1, rate_limit_count)

    # Validate
    errors = validate_prompt_response(name, resp)
    if not errors:
        print(f"  ✅ [{name}] Valid response (no errors)")
        return True, []

    print(f"  ⚠️  [{name}] {len(errors)} validation error(s):")
    for e in errors[:5]:
        print(f"       - {e}")

    # Try local fixer first (attempt A)
    fixed, remaining = fix_errors(resp, errors)
    if not remaining:
        print(f"  🔧 [{name}] Fixed all errors locally")
        return True, []

    if iteration < MAX_ITERATIONS - 1:
        fixed_count = len(errors) - len(remaining)
        print(f"  🔧 [{name}] Fixed {fixed_count}/{len(errors)} locally, {len(remaining)} remaining")
        print(f"  🔄 [{name}] Retry {iteration+2}/{MAX_ITERATIONS} with LLM...")
        time.sleep(5)
        feedback = f"Your previous response had errors. Fix these: " + "; ".join(remaining[:5])
        retry_content = f"{content}\n\nFeedback: {feedback}"
        return _try_prompt({**prompt_def, "content": retry_content}, iteration + 1, rate_limit_count)

    # All retries exhausted
    print(f"  ❌ [{name}] Failed after {MAX_ITERATIONS} iterations")
    return False, remaining


def strategy_test():
    errors = []
    overall_ok = True

    for pi, prompt_def in enumerate(PROMPTS):
        if pi > 0:
            delay = 20
            print(f"\n  ⏳ Waiting {delay}s between prompts to avoid rate limits...")
            time.sleep(delay)
        print(f"\n─── [{prompt_def['name']}] {'─' * 40}")
        success, errs = _try_prompt(prompt_def)
        if not success:
            overall_ok = False
            errors.extend(errs)

    print()
    if overall_ok:
        print("  ✅ All strategy prompts passed")
    else:
        print(f"  ❌ {len(errors)} error(s) across strategy prompts:")
        for e in errors:
            print(f"       - {e}")

    return errors


# ───────────────────── main ─────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Chat E2E test")
    parser.add_argument("mode", choices=["smoke", "strategy", "all"], default="all", nargs="?")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    global PORT
    PORT = args.port

    all_errors = []

    # Pre-check: verify port is reachable or force-clear it
    import subprocess
    fuser_r = subprocess.run(["fuser", f"{PORT}/tcp"], capture_output=True, timeout=5)
    if fuser_r.returncode == 0:
        pid = fuser_r.stdout.decode().strip()
        owner_r = subprocess.run(["ps", "-o", "user=", "-p", pid], capture_output=True, text=True, timeout=5)
        owner = owner_r.stdout.strip() if owner_r.returncode == 0 else "unknown"
        print(f"  ⚠️  Port {PORT} is occupied by PID {pid} ({owner}) — will force-kill")

    # Restart servers once for all modes
    if not restart_servers(PORT):
        all_errors.append("Server restart failed")
        print_summary(all_errors)
        sys.exit(1)

    if args.mode in ("smoke", "all"):
        print(f"\n🔍 Smoke test (port {PORT})")
        print("─" * 40)
        errors = smoke_test()
        if errors:
            all_errors.extend(errors)
            print("\n❌ Smoke test failed — strategy test skipped")
            print_summary(all_errors)
            sys.exit(1)

    if args.mode in ("strategy", "all"):
        print(f"\n🔍 Strategy test (port {PORT})")
        print("─" * 40)
        errors = strategy_test()
        all_errors.extend(errors)

    print_summary(all_errors)


def print_summary(all_errors):
    print("\n" + "=" * 50)
    if all_errors:
        print(f"❌ FAILED — {len(all_errors)} error(s):")
        for e in all_errors:
            print(f"   • {e}")
        sys.exit(1)
    else:
        print("✅ All tests passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
