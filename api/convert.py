"""Strategy converter — Natural Language ↔ PineScript ↔ Python/Rust"""

import json
import logging
import os
import re
import httpx

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "qwen/qwen3-32b"

DIRECTIONS = {
    "nl_python": "Natural Language → Python",
    "nl_pinescript": "Natural Language → PineScript",
    "pinescript_python": "PineScript → Python",
    "python_pinescript": "Python → PineScript",
    "nl_rust": "Natural Language → Rust",
}

SYSTEM_PROMPTS = {
    "nl_python": """You are a PineScript-to-trading-strategy converter. Output ONLY valid JSON.

Convert the user's natural language description into a Python trading strategy.
The strategy must use the vibe_engine library for indicators and define a `decide(i, ohlcv)` function.

Available vibe_engine indicators:
- ve.rsi(close, period=14)
- ve.sma(values, period)
- ve.ema(values, period)
- ve.bbands(values, period=20, std_dev=2.0) -> (upper, middle, lower)
- ve.atr(high, low, close, period=14)
- ve.macd(values, fast=12, slow=26, signal=9) -> (macd_line, signal_line, hist)
- ve.stochastic(high, low, close, period=14) -> (k, d)
- ve.vwap(high, low, close, volume)

Sandbox: long(symbol, qty), short(symbol, qty), close_position(symbol), get_position(symbol), get_price(symbol)
Data: ohlcv DataFrame with columns o, h, l, c, v, t

Output JSON: {"code": "...", "description": "...", "indicators_used": [...], "parameters": {...}}
""",
    "nl_pinescript": """You are a natural-language-to-PineScript converter. Output ONLY valid JSON.

Convert the user's trading strategy description into TradingView PineScript v5 code.
Use standard PineScript v5 syntax with indicator(), plot(), etc.

Output JSON: {"code": "PineScript v5 code", "description": "...", "indicators_used": [...], "parameters": {...}}
""",
    "pinescript_python": """You are a PineScript-to-Python converter. Output ONLY valid JSON.

Translate TradingView PineScript v5 code into equivalent Python using vibe_engine indicators:

PineScript equivalents in vibe_engine:
- ta.sma(src, len) -> ve.sma(values, period)
- ta.ema(src, len) -> ve.ema(values, period)
- ta.rsi(src, len) -> ve.rsi(close, period)
- ta.bb(src, len, mult) -> ve.bbands(values, period, std_dev)
- ta.atr(len) -> ve.atr(high, low, close, period)
- ta.macd(src, f, s, sig) -> ve.macd(values, fast, slow, signal)
- ta.stoch(h, l, c, len) -> ve.stochastic(high, low, close, period)
- ta.vwap(h, l, c, v) -> ve.vwap(high, low, close, volume)
- ta.crossover(a, b) -> last crossover check
- ta.crossunder(a, b) -> last crossunder check

Generate a `decide(i, ohlcv)` function that returns signal dicts.

Output JSON: {"code": "Python code with decide() function", "description": "...", "indicators_used": [...], "parameters": {...}}
""",
    "python_pinescript": """You are a Python-to-PineScript converter. Output ONLY valid JSON.

Translate Python trading strategies (using vibe_engine) into TradingView PineScript v5 code.
The input code uses a `decide(i, ohlcv)` pattern with vibe_engine indicators.
Convert to proper PineScript v5 with indicator(), plot(), plotshape(), etc.

Output JSON: {"code": "PineScript v5 code", "description": "...", "indicators_used": [...], "parameters": {...}}
""",
    "nl_rust": """You are a natural-language-to-Rust converter. Output ONLY valid JSON.

Convert the user's trading strategy description into Rust code using the vibe_engine_rs library.
The Rust code should define a function `fn decide(i: usize, ohlcv: &[Candle]) -> Option<Signal>`
using available Rust indicator functions from vibe_engine_rs.

Available Rust functions:
- rsi(close: &[f64], period: usize) -> Vec<f64>
- sma(values: &[f64], period: usize) -> Vec<f64>
- ema(values: &[f64], period: usize) -> Vec<f64>
- bbands(values: &[f64], period: usize, std_dev: f64) -> (Vec<f64>, Vec<f64>, Vec<f64>)
- macd(values: &[f64], fast: usize, slow: usize, signal: usize) -> (Vec<f64>, Vec<f64>, Vec<f64>)
- atr(high: &[f64], low: &[f64], close: &[f64], period: usize) -> Vec<f64>

Output JSON: {"code": "Rust code", "description": "...", "indicators_used": [...], "parameters": {...}}
""",
}


class ConvertRequest(BaseModel):
    source: str = ""
    target: str = ""
    code: str
    direction: str = "nl_python"
    exchange: str = "binance"
    symbol: str = "BTCUSDC"
    timeframe: str = "1H"


def _call_groq(messages: list[dict]) -> dict | None:
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return None

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 4096,
    }

    for attempt in range(3):
        try:
            with httpx.Client(timeout=60) as client:
                resp = client.post(GROQ_URL, headers=headers, json=payload)

            if resp.status_code == 429:
                import time
                logger.warning("Groq rate limited (attempt %d/3)", attempt + 1)
                time.sleep(2 ** attempt)
                continue

            if resp.status_code != 200:
                logger.warning("Groq returned %d (attempt %d/3): %s", resp.status_code, attempt + 1, resp.text[:300])
                if attempt < 2:
                    import time
                    time.sleep(1)
                    continue
                return None

            raw = resp.json()["choices"][0]["message"]["content"].strip()
            if "</think>" in raw:
                raw = re.sub(r'^<think>.*?</think>\s*', "", raw, flags=re.DOTALL)
            idx = raw.find("<think>")
            if idx >= 0:
                raw = raw[:idx]
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)
            if not raw.startswith("{"):
                logger.warning("Groq response not JSON: %s...", raw[:200])
                return None
            return json.loads(raw)

        except Exception as e:
            logger.warning("Groq call error (attempt %d/3): %s", attempt + 1, e)
            if attempt < 2:
                import time
                time.sleep(1)
                continue
            return None
    return None


def _build_prompt(direction: str, code: str, exchange: str, symbol: str, timeframe: str) -> str:
    prompt = SYSTEM_PROMPTS.get(direction, "")
    if direction.startswith("nl_"):
        return f"""{prompt}

User description:
{code}

Exchange: {exchange}
Symbol: {symbol}
Timeframe: {timeframe}

Output ONLY valid JSON."""
    else:
        return f"""{prompt}

Source code to convert:
```
{code}
```

Exchange: {exchange}
Symbol: {symbol}
Timeframe: {timeframe}

Output ONLY valid JSON."""


@router.post("/api/convert")
async def convert(req: ConvertRequest):
    if req.direction not in SYSTEM_PROMPTS:
        return JSONResponse({"error": f"Unknown direction '{req.direction}'. Choose from: {', '.join(SYSTEM_PROMPTS.keys())}"}, status_code=400)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPTS[req.direction]},
        {"role": "user", "content": _build_prompt(req.direction, req.code, req.exchange, req.symbol, req.timeframe)},
    ]

    result = _call_groq(messages)

    if result is None:
        return JSONResponse({"error": "Conversion failed. Is GROQ_API_KEY set and Groq API reachable?"}, status_code=502)

    return result


# ─── Page ──────────────────────────────────────────────────────────────────────

PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Strategy Converter — Candle Analytics</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f5f5;color:#333;min-height:100vh;display:flex;flex-direction:column}
header{background:#1a1a2e;color:#fff;padding:16px 24px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}
header h1{font-size:18px;font-weight:600}
header nav{display:flex;gap:8px;margin-left:auto}
header nav a{color:#aaa;text-decoration:none;font-size:13px;padding:4px 10px;border-radius:4px}
header nav a:hover{color:#fff;background:rgba(255,255,255,0.1)}
header nav a.active{color:#fff;background:#4fc3f7}
.container{flex:1;display:flex;flex-direction:column;padding:20px;gap:16px;max-width:1400px;margin:0 auto;width:100%}
.controls-row{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.controls-row label{font-size:12px;font-weight:600;color:#666}
.controls-row select,.controls-row input{padding:6px 10px;border:1px solid #ccc;border-radius:4px;font-size:13px;background:#fff}
.controls-row select{min-width:160px}
.convert-btn{padding:8px 24px;background:#26a69a;color:#fff;border:none;border-radius:4px;font-size:14px;font-weight:600;cursor:pointer}
.convert-btn:hover{background:#2bbbad}
.convert-btn:disabled{opacity:.5;cursor:not-allowed}
.editor-split{flex:1;display:grid;grid-template-columns:1fr 1fr;gap:16px;min-height:0}
@media(max-width:800px){.editor-split{grid-template-columns:1fr}}
.panel{display:flex;flex-direction:column;background:#fff;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.08);overflow:hidden}
.panel-header{padding:10px 14px;background:#16213e;color:#fff;font-size:13px;font-weight:600;display:flex;justify-content:space-between;align-items:center}
.panel-header .lang-tag{font-size:11px;background:rgba(255,255,255,.15);padding:2px 8px;border-radius:3px}
.panel-body{flex:1;display:flex;flex-direction:column;min-height:0}
.panel-body textarea{flex:1;width:100%;border:none;resize:none;padding:14px;font-family:'SF Mono','Fira Code','Consolas',monospace;font-size:13px;line-height:1.5;outline:none;min-height:200px}
.panel-body pre{flex:1;margin:0;padding:14px;font-family:'SF Mono','Fira Code','Consolas',monospace;font-size:13px;line-height:1.5;overflow:auto;white-space:pre-wrap;word-break:break-all;background:#1a1a2e;color:#e0e0e0;min-height:200px}
.panel-footer{padding:8px 14px;background:#fafafa;border-top:1px solid #eee;font-size:11px;color:#999;display:flex;justify-content:space-between;align-items:center}
.loading{display:none;align-items:center;gap:8px;color:#999}
.loading .spinner{width:14px;height:14px;border:2px solid #ddd;border-top-color:#26a69a;border-radius:50%;animation:spin .6s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.error-msg{display:none;padding:10px 14px;background:#ffebee;color:#c62828;font-size:13px;border-radius:4px}
.copy-btn{padding:4px 10px;font-size:11px;background:transparent;border:1px solid #ccc;border-radius:3px;cursor:pointer;color:#666}
.copy-btn:hover{background:#eee}
.direction-arrows{display:flex;align-items:center;justify-content:center;font-size:24px;color:#26a69a;padding:4px 0;cursor:pointer;user-select:none}
.output-meta{display:flex;gap:16px;flex-wrap:wrap;padding:8px 14px;font-size:12px;color:#666}
.output-meta span{background:#f0f0f0;padding:2px 8px;border-radius:3px}
</style>
</head>
<body>
<header>
  <h1>⚡ Strategy Converter</h1>
  <nav>
    <a href="/dashboard">Dashboard</a>
    <a href="/strategy-lab">Strategy Lab</a>
    <a href="/vibe-lab">Vibe Lab</a>
    <a href="/convert" class="active">Convert</a>
  </nav>
</header>
<div class="container">
  <div class="controls-row">
    <label>Direction</label>
    <select id="direction">
      <option value="nl_python">Natural Language → Python</option>
      <option value="nl_pinescript">Natural Language → PineScript</option>
      <option value="pinescript_python">PineScript → Python</option>
      <option value="python_pinescript">Python → PineScript</option>
      <option value="nl_rust">Natural Language → Rust</option>
    </select>
    <label>Exchange</label>
    <select id="exchange"><option>binance</option><option>hyperliquid</option></select>
    <label>Symbol</label>
    <select id="symbol"><option>BTCUSDC</option><option>PAXGUSDC</option></select>
    <label>Timeframe</label>
    <select id="timeframe"><option>1H</option><option>1m</option><option>1D</option><option>4H</option></select>
    <button class="convert-btn" id="convertBtn" onclick="doConvert()">Convert</button>
  </div>
  <div class="error-msg" id="errorMsg"></div>
  <div class="editor-split">
    <div class="panel">
      <div class="panel-header" id="inputHeader"><span>Input</span><span class="lang-tag" id="inputLang">Natural Language</span></div>
      <div class="panel-body">
        <textarea id="inputCode" placeholder="Describe your strategy in natural language, or paste PineScript/Python code...">Buy when RSI crosses below 30 and sell when RSI crosses above 70</textarea>
      </div>
      <div class="panel-footer"><span id="inputStats">0 chars</span></div>
    </div>
    <div class="panel">
      <div class="panel-header" id="outputHeader"><span>Output</span><span class="lang-tag" id="outputLang">Python</span></div>
      <div class="panel-body">
        <pre id="outputCode"><span style="color:#666">Your converted strategy will appear here...</span></pre>
      </div>
      <div class="panel-footer">
        <div class="loading" id="loading"><div class="spinner"></div> Converting...</div>
        <div id="outputMeta" class="output-meta"></div>
        <button class="copy-btn" onclick="copyOutput()">Copy</button>
      </div>
    </div>
  </div>
</div>
<script>
var directionLabels = {
  nl_python: {inp:'Natural Language', out:'Python (vibe_engine)'},
  nl_pinescript:{inp:'Natural Language', out:'PineScript v5'},
  pinescript_python:{inp:'PineScript v5', out:'Python (vibe_engine)'},
  python_pinescript:{inp:'Python (vibe_engine)', out:'PineScript v5'},
  nl_rust:{inp:'Natural Language', out:'Rust (vibe_engine_rs)'},
};

document.getElementById('direction').addEventListener('change', function(){
  var d = this.value;
  var lbl = directionLabels[d] || {inp:'Input', out:'Output'};
  document.getElementById('inputLang').textContent = lbl.inp;
  document.getElementById('outputLang').textContent = lbl.out;
  if (d.startsWith('nl_')) {
    document.getElementById('inputCode').placeholder = 'Describe your strategy in natural language...';
  } else if (d.startsWith('pinescript')) {
    document.getElementById('inputCode').placeholder = 'Paste PineScript v5 code...';
  } else {
    document.getElementById('inputCode').placeholder = 'Paste Python strategy code...';
  }
});

document.getElementById('inputCode').addEventListener('input', function(){
  document.getElementById('inputStats').textContent = this.value.length + ' chars';
});

async function doConvert(){
  var btn = document.getElementById('convertBtn');
  var err = document.getElementById('errorMsg');
  var loading = document.getElementById('loading');
  var out = document.getElementById('outputCode');
  var meta = document.getElementById('outputMeta');
  var code = document.getElementById('inputCode').value.trim();
  if (!code) { showError('Please enter some code or description'); return; }
  btn.disabled = true;
  loading.style.display = 'flex';
  err.style.display = 'none';
  out.innerHTML = '<span style="color:#666">Converting...</span>';
  meta.innerHTML = '';
  try {
    var resp = await fetch('/api/convert', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        direction: document.getElementById('direction').value,
        code: code,
        exchange: document.getElementById('exchange').value,
        symbol: document.getElementById('symbol').value,
        timeframe: document.getElementById('timeframe').value,
      }),
    });
    var data = await resp.json();
    if (data.error) { showError(data.error); out.innerHTML = ''; return; }
    if (data.code) {
      out.textContent = data.code;
    } else {
      out.textContent = JSON.stringify(data, null, 2);
    }
    var html = '';
    if (data.indicators_used) html += '<span>Indicators: ' + data.indicators_used.join(', ') + '</span>';
    if (data.description) html += '<span>' + data.description + '</span>';
    if (data.parameters) html += '<span>Params: ' + JSON.stringify(data.parameters) + '</span>';
    meta.innerHTML = html;
  } catch(e) {
    showError('Network error: ' + e.message);
    out.innerHTML = '';
  }
  btn.disabled = false;
  loading.style.display = 'none';
}

function showError(msg){
  var el = document.getElementById('errorMsg');
  el.textContent = msg;
  el.style.display = 'block';
}

function copyOutput(){
  var code = document.getElementById('outputCode').textContent;
  navigator.clipboard.writeText(code).then(function(){
    var btn = document.querySelector('.copy-btn');
    btn.textContent = 'Copied!';
    setTimeout(function(){ btn.textContent = 'Copy'; }, 2000);
  });
}
</script>
</body>
</html>"""


@router.get("/convert", response_class=HTMLResponse)
async def convert_page():
    return PAGE_HTML
