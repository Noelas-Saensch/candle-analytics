"""Vibe Lab — Natural language → AI-generated strategy → Backtest → Analyze"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import asyncio
import json
import logging
import os
import traceback as tb
import uuid
from datetime import datetime

from candles.storage.db import query_candles
from api._agent.generator import generate_via_groq, generate_from_template, TEMPLATES
from api._agent.validator import validate_strategy
from api._agent.analyzer import analyze_results
from api.sandbox import StrategySandbox

logger = logging.getLogger(__name__)
router = APIRouter()


class GenerateRequest(BaseModel):
    description: str = ""
    exchange: str = "binance"
    symbol: str = "BTCUSDC"
    timeframe: str = "1H"
    template: str | None = None
    params: dict | None = None


class RunRequest(BaseModel):
    code: str
    exchange: str = "binance"
    symbol: str = "BTCUSDC"
    timeframe: str = "1H"
    limit: int = 500


class ValidateRequest(BaseModel):
    code: str


class AnalyzeRequest(BaseModel):
    code: str
    results: dict


class SaveStrategyRequest(BaseModel):
    name: str
    code: str
    description: str = ""
    template: str = ""
    params: dict = {}
    exchange: str = "binance"
    symbol: str = "BTCUSDC"
    timeframe: str = "1H"


class OptimizeRequest(BaseModel):
    code_template: str
    param_grid: dict[str, list]
    exchange: str = "binance"
    symbol: str = "BTCUSDC"
    timeframe: str = "1H"
    limit: int = 500


STRATEGIES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "strategies")


def _load_strategies() -> list[dict]:
    os.makedirs(STRATEGIES_DIR, exist_ok=True)
    strategies = []
    for fname in sorted(os.listdir(STRATEGIES_DIR)):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(STRATEGIES_DIR, fname)) as f:
                    s = json.load(f)
                    s["id"] = fname.replace(".json", "")
                    strategies.append(s)
            except Exception as e:
                logger.warning("Failed to load strategy %s: %s", fname, e)
    return strategies


# ── API Endpoints ──

@router.post("/vibe/generate")
async def vibe_generate(req: GenerateRequest):
    if req.template and req.template in TEMPLATES:
        result = generate_from_template(req.template, req.params)
        validation = validate_strategy(result["code"])
        result["validation"] = {
            "valid": validation.valid,
            "errors": validation.errors,
            "warnings": validation.warnings,
        }
        return result

    result = generate_via_groq(req.description, req.exchange, req.symbol, req.timeframe)
    if result:
        validation = validate_strategy(result.get("code", ""))
        result["validation"] = {
            "valid": validation.valid,
            "errors": validation.errors,
            "warnings": validation.warnings,
        }
        return result

    return {"error": "Generation failed. Set GROQ_API_KEY or use a template.", "templates": list(TEMPLATES.keys())}


@router.post("/vibe/validate")
async def vibe_validate(req: ValidateRequest):
    v = validate_strategy(req.code)
    return {"valid": v.valid, "errors": v.errors, "warnings": v.warnings}


@router.post("/vibe/run")
async def vibe_run(req: RunRequest):
    v = validate_strategy(req.code)
    if not v.valid:
        return {"error": "Strategy invalid", "validation_errors": v.errors}

    try:
        rows = query_candles(
            exchange=req.exchange,
            symbol=req.symbol,
            timeframe=req.timeframe,
            limit=req.limit,
        )
        if not rows:
            return {"error": "No data available for this pair/timeframe"}

        sandbox = StrategySandbox(rows)
        result = sandbox.run(req.code)

        if result.get("error"):
            return {"error": result["error"]}

        analysis = analyze_results(result.get("metrics", {}), req.code)

        return {
            "trades": result["trades"],
            "equity_curve": result["equity_curve"],
            "final_balance": result["final_balance"],
            "total_trades": result["total_trades"],
            "metrics": result["metrics"],
            "analysis": {
                "score": analysis.score,
                "summary": analysis.summary,
                "strengths": analysis.strengths,
                "weaknesses": analysis.weaknesses,
                "recommendations": analysis.recommendations,
            },
        }
    except Exception as e:
        return {"error": f"Runtime error: {e}\n{tb.format_exc()}"}


@router.post("/vibe/analyze")
async def vibe_analyze(req: AnalyzeRequest):
    analysis = analyze_results(req.results, req.code)
    return {
        "score": analysis.score,
        "summary": analysis.summary,
        "strengths": analysis.strengths,
        "weaknesses": analysis.weaknesses,
        "recommendations": analysis.recommendations,
        "suggestions": analysis.suggestions,
    }


@router.get("/vibe/templates")
async def vibe_templates():
    return {"templates": list(TEMPLATES.keys())}


@router.post("/vibe/save")
async def vibe_save(req: SaveStrategyRequest):
    os.makedirs(STRATEGIES_DIR, exist_ok=True)
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in req.name).strip().replace(" ", "_")
    if not safe_name:
        return {"error": "Invalid name"}
    import time
    fname = f"{safe_name}_{int(time.time())}.json"
    data = {
        "name": req.name, "code": req.code, "description": req.description,
        "template": req.template, "params": req.params,
        "exchange": req.exchange, "symbol": req.symbol, "timeframe": req.timeframe,
        "created_at": time.time(),
    }
    path = os.path.join(STRATEGIES_DIR, fname)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return {"ok": True, "id": fname.replace(".json", ""), "name": req.name}


@router.get("/vibe/strategies")
async def vibe_strategies():
    return {"strategies": _load_strategies()}


@router.get("/vibe/strategy/{sid}")
async def vibe_strategy(sid: str):
    path = os.path.join(STRATEGIES_DIR, f"{sid}.json")
    if not os.path.exists(path):
        return {"error": "Strategy not found"}
    with open(path) as f:
        s = json.load(f)
    s["id"] = sid
    return s


@router.delete("/vibe/strategy/{sid}")
async def vibe_delete_strategy(sid: str):
    path = os.path.join(STRATEGIES_DIR, f"{sid}.json")
    if os.path.exists(path):
        os.remove(path)
    return {"ok": True}


@router.post("/vibe/optimize")
async def vibe_optimize(req: OptimizeRequest):
    from itertools import product
    import gc
    import time

    keys = list(req.param_grid.keys())
    values = list(req.param_grid.values())
    results = []

    rows = query_candles(exchange=req.exchange, symbol=req.symbol, timeframe=req.timeframe, limit=req.limit)
    if not rows:
        return {"error": "No data"}

    total = 1
    for v in values:
        total *= len(v)

    MAX_COMBOS = 100
    if total > MAX_COMBOS:
        return {"error": f"Too many combinations ({total}). Max is {MAX_COMBOS}."}

    for combo in product(*values):
        params = dict(zip(keys, combo))
        code = req.code_template
        for k, v in params.items():
            code = code.replace("{" + k + "}", str(v))

        v = validate_strategy(code)
        if not v.valid:
            continue

        try:
            sandbox = StrategySandbox(rows)
            result = sandbox.run(code)
            del sandbox
            gc.collect()
            if result.get("error"):
                continue
            results.append({
                "params": params,
                "metrics": result["metrics"],
                "total_trades": result["total_trades"],
                "final_balance": result["final_balance"],
            })
        except Exception:
            continue

    results.sort(key=lambda r: r["metrics"].get("sharpe", 0) or 0, reverse=True)
    return {
        "results": results[:20],
        "total_evaluated": len(results),
        "total_possible": total,
        "best": results[0] if results else None,
    }


@router.post("/vibe/ask-opencode")
async def vibe_ask_opencode(req: Request):
    body = await req.json()
    content = body.get("content", "")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"/tmp/vibe_opencode_{ts}.md"
    with open(fname, "w") as f:
        f.write(content)
    return {"id": os.path.basename(fname).replace(".md", ""), "file": fname}


# ── Vibe Chat HTTP fallback (same file-bridge as WebSocket) ──

VIBE_CHAT_LOG = "/tmp/vibe_chat_log.md"


def _log_vibe(role: str, content: str, detail: str = ""):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    extra = f" ({detail})" if detail else ""
    with open(VIBE_CHAT_LOG, "a") as f:
        f.write(f"\n## {ts} — {role}{extra}\n{content}\n")


class VibeChatRequest(BaseModel):
    content: str


@router.post("/vibe/chat")
async def vibe_chat_post(req: VibeChatRequest):
    req_id = str(uuid.uuid4())
    req_path = f"/tmp/vibe_chat_req_{req_id}.json"
    with open(req_path, "w") as f:
        json.dump({"id": req_id, "content": req.content, "timestamp": asyncio.get_event_loop().time()}, f)
    _log_vibe("User", req.content, detail=f"http_req_{req_id[:8]}")
    return {"id": req_id}


@router.get("/vibe/chat/{req_id}")
async def vibe_chat_poll(req_id: str):
    res_path = f"/tmp/vibe_chat_res_{req_id}.json"
    if os.path.exists(res_path):
        with open(res_path) as f:
            data = json.load(f)
        os.remove(res_path)
        return {"status": "ready", "data": data}
    return {"status": "pending"}


class VibeChatRespondRequest(BaseModel):
    req_id: str
    type: str = "message"
    content: str = ""
    response: dict | None = None


@router.post("/vibe/chat/respond")
async def vibe_chat_respond(
    body: VibeChatRespondRequest | None = None,
    req_id: str | None = None,
    type: str | None = None,
    content: str | None = None,
):
    if body:
        rid = body.req_id
        payload = {"type": body.type, "content": body.content}
        if body.response:
            payload["response"] = body.response
    else:
        rid = req_id
        payload = {"type": type or "message", "content": content or ""}

    if not rid:
        return {"error": "req_id required"}

    res_path = f"/tmp/vibe_chat_res_{rid}.json"
    with open(res_path, "w") as f:
        json.dump(payload, f)
    log_content = payload.get("response", payload.get("content", ""))
    if isinstance(log_content, dict):
        log_content = json.dumps(log_content, indent=2)[:500]
    _log_vibe("OpenCode", str(log_content), detail=f"res_{rid[:8]}")
    return {"status": "ok", "id": rid}


# ── Page ──

VIBE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Candle Analytics — Vibe Lab</title>
<script defer src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #e0e0e0; padding: 16px; }
h1 { font-size: 18px; color: #e94560; margin-bottom: 12px; }
h1 a { color: #888; font-size: 12px; text-decoration: none; }
h1 a:hover { color: #e94560; }
h2 { font-size: 14px; color: #e94560; margin: 14px 0 8px; }
h3 { font-size: 12px; color: #888; margin: 10px 0 6px; }
.section { background: #16213e; border: 1px solid #0f3460; border-radius: 6px; padding: 12px; margin-bottom: 12px; }
.section-divider { height: 2px; background: linear-gradient(90deg, #e94560, #0f3460); margin: 16px 0; }

.panel-row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 10px; }
.panel-row > * { flex: 1; min-width: 200px; }
.panel-row label { font-size: 11px; color: #888; display: block; margin-bottom: 2px; }
.panel-row select, .panel-row input, .panel-row textarea { width: 100%; background: #0f3460; color: #e0e0e0; border: 1px solid #1a3a6b; padding: 6px 10px; border-radius: 4px; font-size: 12px; font-family: inherit; }
.panel-row textarea { min-height: 60px; resize: vertical; }
.panel-row select:focus, .panel-row input:focus, .panel-row textarea:focus { outline: none; border-color: #e94560; }

/* Tabs */
.vibe-tabs { display: flex; gap: 0; margin-bottom: 10px; border-bottom: 1px solid #0f3460; }
.vibe-tab { padding: 6px 16px; font-size: 12px; color: #888; cursor: pointer; border: 1px solid transparent; border-bottom: none; border-radius: 4px 4px 0 0; margin-bottom: -1px; }
.vibe-tab:hover { color: #e0e0e0; }
.vibe-tab.active { color: #e94560; border-color: #0f3460; background: transparent; }
.vibe-content { display: none; }
.vibe-content.active { display: block; }

.controls { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin: 8px 0; }
.btn { background: #0f3460; color: #e0e0e0; border: 1px solid #1a3a6b; padding: 6px 16px; border-radius: 4px; font-size: 12px; cursor: pointer; }
.btn:hover { border-color: #e94560; }
.btn-primary { background: #e94560; color: #fff; border: none; }
.btn-primary:hover { background: #d63851; }
.btn-success { background: #1a5c1a; color: #26a69a; border: 1px solid #2a8a2a; }
.btn-success:hover { border-color: #26a69a; }
.btn-sm { padding: 3px 8px; font-size: 11px; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Code editor */
.code-wrap { position: relative; }
.code-wrap textarea { width: 100%; min-height: 250px; background: #0d1b2a; color: #c8d6e5; border: 1px solid #0f3460; border-radius: 4px; padding: 10px; font-family: 'Menlo', 'Monaco', 'Courier New', monospace; font-size: 11px; line-height: 1.5; resize: vertical; tab-size: 2; }
.code-wrap textarea:focus { outline: none; border-color: #e94560; }

/* Validation */
.v-badge { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 10px; font-weight: 600; }
.v-badge.valid { background: #1b5e20; color: #a5d6a7; }
.v-badge.invalid { background: #b71c1c; color: #ef9a9a; }

/* Metrics grid */
.metrics-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 8px; margin: 10px 0; }
.metric-card { background: #1a1a2e; border: 1px solid #0f3460; border-radius: 4px; padding: 8px; text-align: center; }
.metric-card .val { font-size: 16px; font-weight: 600; }
.metric-card .lbl { font-size: 10px; color: #888; margin-top: 2px; }
.pos { color: #26a69a !important; }
.neg { color: #ef5350 !important; }
.neu { color: #e0e0e0 !important; }

/* Equity chart */
#equityChart { max-height: 250px; width: 100%; }

/* Trades table */
.trade-table { width: 100%; border-collapse: collapse; font-size: 11px; }
.trade-table th, .trade-table td { padding: 4px 6px; text-align: right; border-bottom: 1px solid #0f3460; }
.trade-table th { color: #888; font-weight: 500; position: sticky; top: 0; background: #16213e; }
.trade-table td:first-child, .trade-table th:first-child { text-align: left; }
.trade-table tr:hover { background: #1a3a6b; }
.trade-wrap { max-height: 300px; overflow-y: auto; }

/* Analysis card */
.analysis-card { background: #1a1a2e; border: 1px solid #0f3460; border-radius: 6px; padding: 12px; margin: 8px 0; }
.analysis-card .score-big { font-size: 28px; font-weight: 800; text-align: center; padding: 10px; margin-bottom: 8px; border-radius: 4px; }
.analysis-card .score-high { background: #1b5e20; color: #a5d6a7; }
.analysis-card .score-mid { background: #e65100; color: #ffcc80; }
.analysis-card .score-low { background: #b71c1c; color: #ef9a9a; }
.analysis-card ul { padding-left: 16px; }
.analysis-card ul li { font-size: 12px; margin-bottom: 4px; color: #bbb; }
.analysis-card .section-label { font-size: 12px; font-weight: 700; margin: 8px 0 4px; color: #e0e0e0; }
.analysis-card .summary-text { font-size: 12px; line-height: 1.5; margin-bottom: 8px; color: #c8d6e5; }

/* Chat */
.chat-log { background: #0d1b2a; border: 1px solid #0f3460; border-radius: 4px; padding: 8px; min-height: 100px; max-height: 200px; overflow-y: auto; font-size: 12px; margin-bottom: 6px; }
.chat-log .msg { margin-bottom: 4px; padding: 4px 8px; border-radius: 4px; }
.chat-log .msg.user { background: #1a3a6b; color: #e0e0e0; }
.chat-log .msg.ai { background: #0f3460; color: #c8d6e5; }
.chat-log .msg.system { background: #1a2e1a; color: #26a69a; font-size: 10px; }
.chat-log .msg pre { font-size: 10px; background: #1a1a2e; padding: 4px; border-radius: 2px; margin: 2px 0; }

#status { color: #888; font-size: 12px; min-height: 18px; padding: 4px 0; }
.hidden { display: none; }

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #0f3460; border-radius: 2px; }

/* ── Chat styles (ported from Strategy Lab) ── */
.chat-wrap { display: flex; flex-direction: column; min-height: 340px; }
#chatLog { flex: 1; overflow-y: auto; padding: 10px; background: #0d1b2a; border: 1px solid #0f3460; border-radius: 6px; margin-bottom: 8px; font-size: 13px; line-height: 1.6; min-height: 280px; max-height: 420px; }
#chatLog .msg { margin-bottom: 8px; padding: 8px 12px; border-radius: 8px; max-width: 88%; word-wrap: break-word; }
#chatLog .msg.user { background: #1a3a6b; color: #e0e0e0; margin-left: auto; border-bottom-right-radius: 2px; }
#chatLog .msg.ai { background: #0f3460; color: #c8d6e5; border-bottom-left-radius: 2px; }
#chatLog .msg.ai .ai-avatar { display: inline-block; width: 18px; height: 18px; border-radius: 50%; background: #e94560; color: #fff; font-size: 10px; text-align: center; line-height: 18px; margin-right: 6px; vertical-align: middle; flex-shrink: 0; }
#chatLog .msg .time { font-size: 9px; color: #555; display: block; margin-top: 3px; }
#chatLog .msg.user .time { text-align: right; }
#chatLog .msg.ai .time { text-align: left; }
#chatLog .msg.system { background: #1a2e1a; color: #26a69a; text-align: center; max-width: 100%; font-size: 11px; border-radius: 4px; }
#chatLog .msg .ai-sep { border: none; border-top: 1px solid #1a3a6b; margin: 6px 0; }
#chatLog .msg.ai .ai-line { display: flex; align-items: flex-start; gap: 6px; }
#chatLog .msg.ai .ai-line .ai-avatar { flex-shrink: 0; margin-top: 1px; }
#chatLog .msg pre { background: #0d1b2a; border: 1px solid #1a3a6b; border-radius: 4px; padding: 8px; overflow-x: auto; font-size: 11px; margin: 6px 0; }
#chatLog .msg code { background: #1a1a2e; padding: 1px 4px; border-radius: 3px; font-size: 11px; }
#chatLog .msg pre code { background: none; padding: 0; }
.chat-input-row { display: flex; gap: 6px; align-items: flex-start; }
.chat-input-row textarea { flex: 1; background: #0f3460; color: #e0e0e0; border: 1px solid #1a3a6b; padding: 10px 14px; border-radius: 8px; font-size: 13px; resize: vertical; min-height: 40px; max-height: 150px; line-height: 1.4; font-family: inherit; }
.chat-input-row textarea:focus { outline: none; border-color: #e94560; }
.chat-input-row textarea::placeholder { color: #555; }
.chat-input-row .btn-wrap { display: flex; flex-direction: column; gap: 3px; }
.chat-input-row .btn-wrap .btn-send { background: #e94560; color: #fff; border: none; padding: 10px 22px; border-radius: 8px; font-size: 13px; cursor: pointer; white-space: nowrap; font-weight: 500; }
.chat-input-row .btn-wrap .btn-send:hover { background: #d63851; }
.chat-input-row .btn-wrap .btn-send:disabled { opacity: .5; cursor: not-allowed; }
.chat-footer { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-top: 2px; }
.chat-footer .chat-hint { font-size: 10px; color: #555; }
.chat-footer .chat-actions { display: flex; gap: 6px; }
.btn-chat { background: none; border: 1px solid #0f3460; color: #888; padding: 3px 9px; border-radius: 4px; font-size: 11px; cursor: pointer; }
.btn-chat:hover { border-color: #e94560; color: #e0e0e0; }
.conn-status { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }
.conn-status.connected { background: #26a69a; }
.conn-status.connecting { background: #f9a825; }
.conn-status.disconnected { background: #ef5350; }
.typing { color: #555; font-size: 11px; padding: 4px 8px; font-style: italic; }
.strategy-actions { display: flex; gap: 6px; padding: 6px 8px; }
.strategy-actions.hidden { display: none; }
.btn-action { flex: 1; padding: 7px 12px; border-radius: 5px; border: none; font-size: 12px; cursor: pointer; font-weight: 600; transition: opacity 0.15s; }
.btn-action:hover { opacity: 0.85; }
.btn-action.backtest { background: #26a69a; color: #fff; }
.btn-action.improve { background: #0f3460; color: #e0e0e0; border: 1px solid #1a3a6b; }
.btn-action.think { background: #7b1fa2; color: #fff; }
.strat-card { background: #1a1a2e; border: 1px solid #0f3460; border-radius: 4px; padding: 8px 12px; flex: 0 0 auto; }
.strat-card .sc-label { font-size: 9px; color: #555; text-transform: uppercase; }
.strat-card .sc-value { font-size: 13px; font-weight: 600; margin-top: 2px; }

.template-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 6px; margin: 6px 0; }
.template-card { background: #1a1a2e; border: 1px solid #0f3460; border-radius: 4px; padding: 8px; cursor: pointer; text-align: center; font-size: 11px; }
.template-card:hover { border-color: #e94560; }
.template-card .tc-name { color: #e94560; font-weight: 500; }

/* Save / strategies */
.save-row { display: flex; gap: 6px; align-items: center; margin: 8px 0; }
.save-row input { flex: 1; background: #0f3460; color: #e0e0e0; border: 1px solid #1a3a6b; padding: 6px 10px; border-radius: 4px; font-size: 12px; }
.strategy-list { max-height: 200px; overflow-y: auto; margin: 6px 0; }
.strategy-item { display: flex; justify-content: space-between; align-items: center; padding: 6px 8px; border-bottom: 1px solid #0f3460; font-size: 11px; cursor: pointer; }
.strategy-item:hover { background: #1a3a6b; }
.strategy-item .s-name { color: #e0e0e0; }
.strategy-item .s-info { color: #555; font-size: 10px; }
.strategy-item .s-del { color: #ef5350; cursor: pointer; padding: 0 4px; }

/* Comparison */
.compare-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 6px; margin: 8px 0; }
.compare-card { background: #1a1a2e; border: 1px solid #0f3460; border-radius: 4px; padding: 8px; font-size: 10px; }
.compare-card .cc-name { color: #e94560; font-weight: 600; font-size: 11px; margin-bottom: 4px; }
.compare-card .cc-row { display: flex; justify-content: space-between; padding: 1px 0; color: #bbb; }

/* Optimization */
.param-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin: 6px 0; }
.param-row input { width: 80px; background: #0f3460; color: #e0e0e0; border: 1px solid #1a3a6b; padding: 4px 6px; border-radius: 3px; font-size: 11px; }
.param-row label { font-size: 11px; color: #888; min-width: 50px; }
.opt-results { max-height: 300px; overflow-y: auto; margin: 8px 0; }
.opt-row { display: flex; gap: 8px; padding: 4px 6px; border-bottom: 1px solid #0f3460; font-size: 10px; align-items: center; }
.opt-row:hover { background: #1a3a6b; }
.opt-row .or-params { flex: 2; color: #888; }
.opt-row .or-metrics { flex: 3; display: flex; gap: 8px; color: #bbb; }
.opt-row.best { background: #1b5e20; }
.opt-row.best .or-params { color: #a5d6a7; }
.opt-row.best .or-metrics { color: #a5d6a7; }
</style>
</head>
<body>

<h1><a href="/strategy-lab">&larr;</a> &nbsp;Vibe Lab</h1>
<p style="font-size:11px;color:#555;margin-bottom:10px">Describe your strategy in natural language → AI generates code → Backtest → Analyze</p>

<!-- Market selector bar (persistent across all tabs) -->
<div class="section" style="padding:8px 12px;margin-bottom:8px">
  <div class="panel-row">
    <div style="flex:0 0 auto;min-width:120px">
      <label>Exchange</label>
      <select id="vibeExchange"><option value="binance">Binance</option><option value="hyperliquid">Hyperliquid</option></select>
    </div>
    <div style="flex:0 0 auto;min-width:140px">
      <label>Pair</label>
      <select id="vibeSymbol"><option value="BTCUSDC">BTCUSDC</option><option value="PAXGUSDC">PAXGUSDC</option></select>
    </div>
    <div style="flex:0 0 auto;min-width:100px">
      <label>Timeframe</label>
      <select id="vibeTimeframe">
        <option value="1m">1m</option><option value="5m">5m</option><option value="15m">15m</option>
        <option value="30m">30m</option><option value="1H" selected>1H</option><option value="4H">4H</option>
        <option value="1D">1D</option><option value="1W">1W</option><option value="1M">1M</option>
      </select>
    </div>
    <div style="flex:0 0 auto;min-width:80px">
      <label>Bars</label>
      <select id="vibeLimit"><option value="200">200</option><option value="500" selected>500</option><option value="1000">1000</option><option value="2500">2500</option><option value="5000">5000</option></select>
    </div>
  </div>
</div>

<div class="vibe-tabs">
  <div class="vibe-tab active" data-tab="describe" onclick="switchTab('describe')">1. Chat</div>
  <div class="vibe-tab" data-tab="code" onclick="switchTab('code')">2. Code</div>
  <div class="vibe-tab" data-tab="results" onclick="switchTab('results')">3. Results</div>
</div>

<!-- ── TAB 1: CHAT ── -->
<div class="vibe-content active" id="tab-describe">
  <div class="section" style="padding:0;border:none;background:transparent">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
      <h2 style="margin:0">💬 Strategy Chat</h2>
      <button class="btn-chat" onclick="exportChat()" title="Export chat">📥 Export</button>
      <button class="btn-chat" onclick="newChat()" title="New conversation">✕ New</button>
      <span style="flex:1"></span>
      <span style="font-size:11px;color:#555"><span class="conn-status disconnected" id="connStatus"></span><span id="connLabel">disconnected</span></span>
    </div>
    <div class="chat-wrap">
      <div id="chatLog"></div>
      <div class="chat-input-row">
        <textarea id="chatInput" placeholder="Describe your strategy..." rows="1" autofocus onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendChatMessage()}"></textarea>
        <div class="btn-wrap">
          <button class="btn-send" onclick="sendChatMessage()">Send</button>
        </div>
      </div>
      <div class="chat-footer">
        <div class="chat-hint">Enter to send · Shift+Enter for newline</div>
      </div>
      <div id="strategyActions" class="strategy-actions hidden">
        <button class="btn-action backtest" onclick="runBacktestFromChat()">🔍 Backtest</button>
        <button class="btn-action improve" onclick="requestImprovement()">📈 Improve</button>
      </div>
      <div id="typingIndicator" class="typing hidden">thinking...</div>
    </div>
  </div>
</div>

<!-- ── TAB 2: CODE ── -->
<div class="vibe-content" id="tab-code">
  <div style="display:flex;gap:12px;flex-wrap:wrap">
  <div style="flex:3;min-width:400px">
  <div class="section">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
      <h2 style="margin:0">Generated Strategy Code</h2>
      <div>
        <span id="validationBadge"></span>
        <span id="codeDescription" style="font-size:11px;color:#555;margin-left:8px"></span>
      </div>
    </div>
    <div class="code-wrap">
      <textarea id="strategyCode" spellcheck="false" placeholder="Strategy code will appear here..."></textarea>
    </div>
    <div id="validationDetails" style="font-size:11px;color:#888;margin:4px 0"></div>
    <div class="controls">
      <button class="btn" onclick="validateCode()">Validate</button>
      <button class="btn btn-primary" onclick="runBacktest()">▶ Run Backtest</button>
      <button class="btn btn-sm" onclick="copyCode()">Copy</button>
      <button class="btn btn-sm btn-success" onclick="showSaveDialog()">💾 Save</button>
    </div>
  </div>

  <!-- ── Optimization section ── -->
  <div class="section">
    <h2>Parameter Optimization</h2>
    <p style="font-size:11px;color:#555;margin-bottom:6px">Enter parameter values to search (comma-separated), then run optimization.</p>
    <div id="optParams"></div>
    <div class="controls">
      <button class="btn btn-primary" onclick="runOptimization()">⚡ Optimize</button>
      <span id="optStatus" style="font-size:11px;color:#555;margin-left:8px"></span>
    </div>
    <div id="optResults" class="opt-results hidden"></div>
  </div>
  </div>
  <div style="flex:1;min-width:200px">

  <!-- ── Saved Strategies sidebar ── -->
  <div class="section">
    <h2>Saved Strategies</h2>
    <div id="savedStrategyList" class="strategy-list">
      <div style="font-size:11px;color:#555">Loading...</div>
    </div>
    <div class="controls">
      <button class="btn btn-sm" onclick="loadSavedStrategies()">⟳ Refresh</button>
    </div>
  </div>

  </div>
  </div>
</div>

<!-- ── TAB 3: RESULTS ── -->
<div class="vibe-content" id="tab-results">
  <div class="section">
    <h2>Backtest Results</h2>
    <div id="status">Run a strategy first</div>

    <div id="resultsContent" class="hidden">
      <div class="metrics-grid" id="metricsGrid"></div>
      <div class="controls" style="justify-content:flex-end">
        <button class="btn btn-sm btn-success" onclick="addToComparison()">➕ Add to Comparison</button>
        <button class="btn btn-sm" onclick="showSaveDialog()">💾 Save</button>
      </div>
      <canvas id="equityChart"></canvas>
      <h3>Trades</h3>
      <div class="trade-wrap"><table class="trade-table" id="tradeTable"><thead><tr><th>#</th><th>Side</th><th>Entry</th><th>Exit</th><th>PnL %</th><th>PnL $</th></tr></thead><tbody></tbody></table></div>
      <h3>Analysis</h3>
      <div id="analysisContent"></div>
      <div class="controls">
        <button class="btn btn-sm" onclick="iterateStrategy()">🔄 Iterate</button>
        <button class="btn btn-sm" onclick="switchTab('code')">← Back to Code</button>
      </div>
    </div>
  </div>

  <!-- Comparison section -->
  <div class="section" id="comparisonSection" style="display:none">
    <h2>Strategy Comparison</h2>
    <div id="comparisonGrid" class="compare-grid"></div>
    <div class="controls">
      <button class="btn btn-sm" onclick="clearComparison()">Clear Comparison</button>
    </div>
  </div>
</div>

<script>
// ── State ──
var _currentCode = '';
var _lastResults = null;
var _lastAnalysis = null;
var _equityChart = null;
var _ws = null;
var _useFallback = false;
var _pendingId = null;
var _pendingPollInterval = null;
var _pendingChatTimeout = null;
var _comparisonList = [];

// ── Init ──
document.addEventListener('DOMContentLoaded', function () {
  loadPairs();
  loadSavedStrategies();

  var chatInput = document.getElementById('chatInput');
  if (chatInput) {
    chatInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatMessage(); }
    });
    chatInput.addEventListener('input', function () {
      this.style.height = 'auto';
      this.style.height = Math.min(this.scrollHeight, 150) + 'px';
    });
  }

  document.getElementById('strategyCode').addEventListener('input', renderOptParams);

  addChatMessage('system', 'Describe your strategy in the chat below. The AI will guide you step by step, then generate the code.');
  addChatMessage('ai', 'Ready. Tell me what kind of strategy you want to build. For example: "BTC momentum with RSI(14) oversold entries and SMA crossover confirmation."');
  connectWS();
});

// ── WebSocket connection ──
function connectWS() {
  var statusDot = document.getElementById('connStatus');
  var statusLabel = document.getElementById('connLabel');
  statusDot.className = 'conn-status connecting';
  statusLabel.textContent = 'connecting...';

  var proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  var url = proto + '//' + location.host + '/api/ws/vibe-chat';

  try { _ws = new WebSocket(url); }
  catch (e) { onWSFail('Exception: ' + e.message); return; }

  _ws.onopen = function () {
    statusDot.className = 'conn-status connected';
    statusLabel.textContent = 'Connected';
    addChatMessage('system', 'Connected to strategy assistant');
  };

  _ws.onmessage = function (evt) {
    try {
      var data = JSON.parse(evt.data);
      handleWSMessage(data);
    } catch (e) { console.warn('WS parse error', e); }
  };

  _ws.onclose = function () {
    if (_useFallback) return;
    statusDot.className = 'conn-status disconnected';
    statusLabel.textContent = 'disconnected (will retry)';
    setTimeout(connectWS, 3000);
  };

  _ws.onerror = function () { onWSFail('Connection error'); };
}

function onWSFail(reason) {
  if (_useFallback) return;
  console.warn('WS failed:', reason);
  document.getElementById('connStatus').className = 'conn-status disconnected';
  document.getElementById('connLabel').textContent = 'WebSocket failed, using HTTP';
  addChatMessage('system', 'WebSocket unavailable — using HTTP fallback. Responses may be slower.');
  _useFallback = true;
  _ws = null;
}

function handleWSMessage(data) {
  document.getElementById('typingIndicator').classList.add('hidden');

  if (data.type === 'ack') {
    _pendingId = data.id;
    if (_pendingChatTimeout) clearTimeout(_pendingChatTimeout);
    _pendingChatTimeout = setTimeout(function () {
      if (_pendingId) {
        addChatMessage('system', 'Still waiting...');
        document.getElementById('typingIndicator').classList.add('hidden');
      }
    }, 15000);
    return;
  }

  if (data.type === 'response' || data.type === 'message' || data.type === 'code_generated') {
    if (_pendingChatTimeout) { clearTimeout(_pendingChatTimeout); _pendingChatTimeout = null; }
    _pendingId = null;

    // code_generated — populate Code tab
    if (data.code) {
      receiveGeneratedCode(data);
      addChatMessage('ai', '✅ Code generated: <strong>' + (data.description || '') + '</strong><br><span style="font-size:10px;color:#555">Code is ready in the Code tab →</span>', true);
      return;
    }

    // regular message
    if (data.content) {
      addChatMessage('ai', data.content);
    }
    return;
  }

  if (data.type === 'timeout') {
    if (_pendingChatTimeout) { clearTimeout(_pendingChatTimeout); _pendingChatTimeout = null; }
    addChatMessage('system', 'No response in time — check that vibe-agent is running (screen -ls)');
    _pendingId = null;
  }
}

// ── Chat ──
function sendChatMessage() {
  var input = document.getElementById('chatInput');
  var text = input.value.trim();
  if (!text) return;

  input.value = ''; input.style.height = 'auto';
  addChatMessage('user', text);

  var exEl = document.getElementById('vibeExchange');
  var symEl = document.getElementById('vibeSymbol');
  var tfEl = document.getElementById('vibeTimeframe');
  var exchange = exEl ? exEl.value : 'binance';
  var symbol = symEl ? symEl.value : 'BTCUSDC';
  var timeframe = tfEl ? tfEl.value : '1H';

  var payload = { type: 'message', content: text, exchange: exchange, symbol: symbol, timeframe: timeframe };

  if (_ws && _ws.readyState === WebSocket.OPEN) {
    document.getElementById('typingIndicator').classList.remove('hidden');
    _ws.send(JSON.stringify(payload));
  } else if (_useFallback) {
    sendViaHTTP(text);
  } else {
    addChatMessage('system', 'Not connected. Retrying...');
    connectWS();
  }
}

// ── HTTP fallback ──
function sendViaHTTP(text) {
  document.getElementById('typingIndicator').classList.remove('hidden');
  addChatMessage('system', 'Message sent (HTTP fallback) — waiting for response...');
  fetch('/vibe/chat', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: text }),
  })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      _pendingId = data.id;
      if (_pendingPollInterval) clearInterval(_pendingPollInterval);
      _pendingPollInterval = setInterval(function () { pollResponse(data.id); }, 1500);
      if (_pendingChatTimeout) clearTimeout(_pendingChatTimeout);
      _pendingChatTimeout = setTimeout(function () {
        if (_pendingId) {
          addChatMessage('system', 'Still waiting... Check that vibe-agent is running');
          document.getElementById('typingIndicator').classList.add('hidden');
        }
      }, 15000);
    })
    .catch(function (err) {
      document.getElementById('typingIndicator').classList.add('hidden');
      addChatMessage('system', 'Error: ' + err.message);
    });
}

function pollResponse(id) {
  fetch('/vibe/chat/' + id)
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.status === 'ready') {
        clearInterval(_pendingPollInterval);
        _pendingPollInterval = null;
        if (_pendingChatTimeout) { clearTimeout(_pendingChatTimeout); _pendingChatTimeout = null; }
        document.getElementById('typingIndicator').classList.add('hidden');
        handleWSMessage(data.data);
        _pendingId = null;
      }
    })
    .catch(function () {});
}

// ── Chat rendering ──
function renderMarkdown(text) {
  var escaped = text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\\n/g, '<br>');
  var html = escaped;
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  html = html.replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>');
  html = html.replace(/\\*(.+?)\\*/g, '<em>$1</em>');
  return html;
}

function addChatMessage(role, content, raw) {
  var log = document.getElementById('chatLog');
  var time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  var formatted = raw ? content : renderMarkdown(content);

  if (role === 'ai') {
    var last = log.lastElementChild;
    if (last && last.classList.contains('ai')) {
      last.querySelector('.ai-body').insertAdjacentHTML('beforeend',
        '<hr class="ai-sep"><span>' + formatted + '</span>');
      log.scrollTop = log.scrollHeight;
      return;
    }
    var div = document.createElement('div');
    div.className = 'msg ai';
    div.innerHTML = '<div class="ai-line"><span class="ai-avatar">A</span><span class="ai-body">' + formatted + '</span></div><span class="time">' + time + '</span>';
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
    return;
  }

  var div = document.createElement('div');
  div.className = 'msg ' + role;
  div.innerHTML = formatted + '<span class="time">' + time + '</span>';
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

function exportChat() {
  var msgs = document.querySelectorAll('#chatLog .msg');
  var md = '# Vibe Lab — Chat Export\\n\\n';
  for (var mi = 0; mi < msgs.length; mi++) {
    var m = msgs[mi];
    var role = m.classList.contains('user') ? '**You**' : m.classList.contains('ai') ? '**AI**' : '*System*';
    var t = m.querySelector('.time');
    var time = t ? t.textContent : '';
    var body = m.innerText || m.textContent || '';
    var clean = body.replace(time, '').trim();
    md += '### ' + role + ' (' + time + ')\\n' + clean + '\\n\\n';
  }
  var blob = new Blob([md], { type: 'text/markdown' });
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'vibe-chat-' + new Date().toISOString().slice(0, 10) + '.md';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
}

function newChat() {
  document.getElementById('chatLog').innerHTML = '';
  _pendingId = null;
  if (_pendingPollInterval) { clearInterval(_pendingPollInterval); _pendingPollInterval = null; }
  if (_pendingChatTimeout) { clearTimeout(_pendingChatTimeout); _pendingChatTimeout = null; }
  document.getElementById('typingIndicator').classList.add('hidden');
  document.getElementById('strategyActions').classList.add('hidden');
  addChatMessage('system', 'New conversation started');
}

function runBacktestFromChat() {
  if (!_currentCode) { addChatMessage('system', 'No code generated yet. Describe a strategy first.'); return; }
  addChatMessage('system', '▶ Running backtest...');
  runBacktest();
}

function requestImprovement() {
  if (!_currentCode) { addChatMessage('system', 'No strategy to improve'); return; }
  addChatMessage('system', '📈 Describe what you want to improve, or ask the AI to suggest changes.');
  // Just var the user chat naturally — the agent will handle improvement requests
}

// ── Code generation handler ──
function receiveGeneratedCode(data) {
  var code = data.code || data.strategy_code || '';
  _currentCode = code;
  document.getElementById('strategyCode').value = code;

  if (data.description) {
    document.getElementById('codeDescription').textContent = data.description;
  }

  if (data.validation) {
    var v = data.validation;
    var badge = document.getElementById('validationBadge');
    badge.innerHTML = v.valid
      ? '<span class="v-badge valid">Valid</span>'
      : '<span class="v-badge invalid">Invalid</span>';
    var details = document.getElementById('validationDetails');
    details.innerHTML = (v.errors || []).map(function(e) { return '❌ ' + e; }).join('<br>')
      + (v.warnings || []).map(function(w) { return '⚠️ ' + w; }).join('<br>');
    if (!v.valid) return;
  } else {
    // Auto-validate
    validateCode();
  }

  document.getElementById('strategyActions').classList.remove('hidden');
  renderOptParams();
  switchTab('code');
}

// ── Pairs ──
function loadPairs() {
  var symEl = document.getElementById('vibeSymbol');
  if (!symEl) return;
  symEl.innerHTML = '<option>Loading...</option>';
  fetch('/api/pairs')
    .then(function(r){ return r.json(); })
    .then(function(data) {
      if (!data.pairs) throw new Error('No pairs data');
      var symbols = [];
      var seen = {};
      data.pairs.forEach(function(p) {
        if (!seen[p.symbol]) { seen[p.symbol] = true; symbols.push(p.symbol); }
      });
      symEl.innerHTML = symbols.map(function(s){ return '<option value="'+s+'">'+s+'</option>'; }).join('');
    })
    .catch(function(err) {
      symEl.innerHTML = '<option value="BTCUSDC">BTCUSDC</option><option value="PAXGUSDC">PAXGUSDC</option>';
    });
}

function switchTab(name) {
  var tabs = document.querySelectorAll('.vibe-tab');
  for (var si = 0; si < tabs.length; si++) { tabs[si].classList.toggle('active', tabs[si].dataset.tab === name); }
  var contents = document.querySelectorAll('.vibe-content');
  for (var si = 0; si < contents.length; si++) { contents[si].classList.toggle('active', contents[si].id === 'tab-' + name); }
}

// ── Validate ──
function validateCode() {
  var code = document.getElementById('strategyCode').value;
  fetch('/vibe/validate', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({code: code}),
  }).then(function(r) { return r.json(); }).then(function(data) {
    var badge = document.getElementById('validationBadge');
    badge.innerHTML = data.valid
      ? '<span class="v-badge valid">✓ Valid</span>'
      : '<span class="v-badge invalid">✗ Invalid</span>';
    var details = document.getElementById('validationDetails');
    details.innerHTML = (data.errors || []).map(function(e) { return '❌ ' + e; }).join('<br>')
      + (data.warnings || []).map(function(w) { return '⚠️ ' + w; }).join('<br>');
  });
}

function copyCode() {
  var ta = document.getElementById('strategyCode');
  ta.select();
  document.execCommand('copy');
  document.getElementById('validationDetails').textContent = 'Copied!';
}

// ── Run ──
function runBacktest() {
  var code = document.getElementById('strategyCode').value;
  if (!code.trim()) { document.getElementById('status').textContent = 'No code to run'; return; }
  _currentCode = code;

  var status = document.getElementById('status');
  var resultsDiv = document.getElementById('resultsContent');
  resultsDiv.classList.add('hidden');
  status.textContent = 'Running backtest...';

  var ex = document.getElementById('vibeExchange').value;
  var sym = document.getElementById('vibeSymbol').value;
  var tf = document.getElementById('vibeTimeframe').value;
  var limit = parseInt(document.getElementById('vibeLimit').value) || 500;

  fetch('/vibe/run', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({code: code, exchange: ex, symbol: sym, timeframe: tf, limit: limit}),
  }).then(function(r) { return r.json(); }).then(function(data) {
    if (data.error) {
      status.textContent = 'Error: ' + data.error;
      if (data.validation_errors) document.getElementById('validationDetails').innerHTML = data.validation_errors.join('<br>');
      return;
    }
    _lastResults = data;
    displayResults(data);
    status.textContent = data.total_trades + ' trades — Final balance: $' + data.final_balance.toFixed(2);
    switchTab('results');
  }).catch(function(err) { status.textContent = 'Error: ' + err.message; });
}

function displayResults(data) {
  var m = data.metrics || {};
  var grid = document.getElementById('metricsGrid');
  var cards = [
    {lbl: 'Total Return', val: (m.total_return_pct || 0).toFixed(2) + '%', cls: (m.total_return_pct || 0) >= 0 ? 'pos' : 'neg'},
    {lbl: 'Win Rate', val: (m.win_rate || 0).toFixed(1) + '%', cls: (m.win_rate || 0) >= 50 ? 'pos' : 'neg'},
    {lbl: 'Sharpe', val: (m.sharpe || 0).toFixed(2), cls: (m.sharpe || 0) >= 1 ? 'pos' : (m.sharpe || 0) >= 0 ? 'neu' : 'neg'},
    {lbl: 'Sortino', val: (m.sortino || 0).toFixed(2), cls: (m.sortino || 0) >= 1 ? 'pos' : 'neu'},
    {lbl: 'Profit Factor', val: m.profit_factor === Infinity ? '∞' : (m.profit_factor || 0).toFixed(2), cls: (m.profit_factor || 0) >= 1 ? 'pos' : 'neg'},
    {lbl: 'Max DD', val: (m.max_drawdown_pct || 0).toFixed(2) + '%', cls: 'neg'},
    {lbl: 'Trades', val: data.total_trades || 0, cls: 'neu'},
    {lbl: 'Final Balance', val: '$' + (data.final_balance || 0).toFixed(2), cls: 'neu'},
  ];
  grid.innerHTML = cards.map(function(c) { return '<div class="metric-card"><div class="val ' + c.cls + '">' + c.val + '</div><div class="lbl">' + c.lbl + '</div></div>'; }).join('');

  renderEquityCurve(data.equity_curve || []);
  renderTrades(data.trades || []);
  renderAnalysis(data.analysis);

  document.getElementById('resultsContent').classList.remove('hidden');
}

function renderEquityCurve(curve) {
  var canvas = document.getElementById('equityChart');
  if (!curve || !curve.length) return;

  var labels = curve.map(function(e) { return e.step; });
  var equity = curve.map(function(e) { return e.equity; });
  var positions = curve.map(function(e) { return e.position * (e.equity / 20); });

  if (_equityChart) _equityChart.destroy();

  _equityChart = new Chart(canvas, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {label: 'Equity', data: equity, borderColor: '#26a69a', backgroundColor: 'rgba(38,166,154,0.1)', fill: true, borderWidth: 2, pointRadius: 0, tension: 0.3},
        {label: 'In Position', data: positions, borderColor: '#e94560', backgroundColor: 'rgba(233,69,96,0.05)', fill: true, borderWidth: 1, pointRadius: 0},
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {legend: {labels: {color: '#888', font: {size: 10}}}},
      scales: {
        x: {ticks: {color: '#555', font: {size: 9}, maxTicksLimit: 10}, grid: {color: '#0f3460'}},
        y: {ticks: {color: '#888', font: {size: 10}}, grid: {color: '#0f3460'}},
      },
    },
  });
  canvas.style.height = '250px';
}

function renderTrades(trades) {
  var tbody = document.querySelector('#tradeTable tbody');
  if (!trades || !trades.length) { tbody.innerHTML = '<tr><td colspan="6">No trades</td></tr>'; return; }

  var html = '';
  for (var i = 0; i < trades.length; i++) {
    var t = trades[i];
    var side = t.side || 'long';
    var cls = (t.pnl_pct || 0) >= 0 ? 'pos' : 'neg';
    html += '<tr><td>' + (i + 1) + '</td><td>' + side.toUpperCase() + '</td>'
      + '<td>' + (t.entry || 0).toFixed(2) + '</td>'
      + '<td>' + (t.exit || 0).toFixed(2) + '</td>'
      + '<td class="' + cls + '">' + (t.pnl_pct || 0).toFixed(2) + '%</td>'
      + '<td class="' + cls + '">$' + (t.pnl_usd || 0).toFixed(2) + '</td></tr>';
  }
  tbody.innerHTML = html;
}

function renderAnalysis(analysis) {
  var container = document.getElementById('analysisContent');
  if (!analysis) { container.innerHTML = '<div style="font-size:11px;color:#555">No analysis available</div>'; return; }

  var score = analysis.score || 5;
  var scoreCls = score >= 7 ? 'score-high' : score >= 4 ? 'score-mid' : 'score-low';

  var html = '<div class="analysis-card">';
  html += '<div class="score-big ' + scoreCls + '">' + score + '/10</div>';
  if (analysis.summary) html += '<div class="summary-text">' + analysis.summary + '</div>';

  if (analysis.strengths && analysis.strengths.length) {
    html += '<div class="section-label">✅ Strengths</div><ul>';
    for (var i = 0; i < analysis.strengths.length; i++) { html += '<li>' + analysis.strengths[i] + '</li>'; }
    html += '</ul>';
  }
  if (analysis.weaknesses && analysis.weaknesses.length) {
    html += '<div class="section-label">⚠️ Weaknesses</div><ul>';
    for (var i = 0; i < analysis.weaknesses.length; i++) { html += '<li>' + analysis.weaknesses[i] + '</li>'; }
    html += '</ul>';
  }
  if (analysis.recommendations && analysis.recommendations.length) {
    html += '<div class="section-label">💡 Recommendations</div><ul>';
    for (var i = 0; i < analysis.recommendations.length; i++) { html += '<li>' + analysis.recommendations[i] + '</li>'; }
    html += '</ul>';
  }
  html += '</div>';
  container.innerHTML = html;
}

// ── Save / Load ──
function showSaveDialog() {
  var name = prompt('Strategy name:', 'My Strategy');
  if (!name || !name.trim()) return;
  var code = document.getElementById('strategyCode').value;
  if (!code.trim()) { alert('No code to save'); return; }
  var ex = document.getElementById('vibeExchange').value;
  var sym = document.getElementById('vibeSymbol').value;
  var tf = document.getElementById('vibeTimeframe').value;
  fetch('/vibe/save', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name: name.trim(), code: code, exchange: ex, symbol: sym, timeframe: tf}),
  }).then(function(r) { return r.json(); }).then(function(data) {
    if (data.ok) {
      document.getElementById('validationDetails').textContent = 'Saved: ' + data.name;
      loadSavedStrategies();
    } else {
      alert('Save failed: ' + (data.error || 'unknown'));
    }
  });
}

function loadSavedStrategies() {
  var list = document.getElementById('savedStrategyList');
  if (!list) return;
  list.innerHTML = '<div style="font-size:11px;color:#555">Loading...</div>';
  fetch('/vibe/strategies')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (!data.strategies || !data.strategies.length) {
        list.innerHTML = '<div style="font-size:11px;color:#555">No saved strategies</div>';
        return;
      }
      var html = '';
      for (var i = 0; i < data.strategies.length; i++) {
        var s = data.strategies[i];
        var d = s.created_at ? new Date(s.created_at * 1000).toLocaleDateString() : '';
html += '<div class="strategy-item" onclick="loadStrategy(\\'' + s.id + '\\')">'
           + '<div><div class="s-name">' + escapeHtml(s.name || 'Unnamed') + '</div>'
           + '<div class="s-info">' + (s.symbol || '') + ' ' + (s.timeframe || '') + ' — ' + d + '</div></div>'
           + '<span class="s-del" onclick="event.stopPropagation();deleteStrategy(\\'' + s.id + '\\')">✕</span>'
          + '</div>';
      }
      list.innerHTML = html;
    })
    .catch(function() { list.innerHTML = '<div style="font-size:11px;color:#ef5350">Failed to load</div>'; });
}

function escapeHtml(s) { return String(s).replace(/[&<>"]/g, function(c) {
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c] || c;
}); }

function loadStrategy(id) {
  fetch('/vibe/strategy/' + id)
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.error) { alert(data.error); return; }
      document.getElementById('strategyCode').value = data.code || '';
      document.getElementById('codeDescription').textContent = data.name || '';
      if (data.exchange) document.getElementById('vibeExchange').value = data.exchange;
      if (data.symbol) document.getElementById('vibeSymbol').value = data.symbol;
      if (data.timeframe) document.getElementById('vibeTimeframe').value = data.timeframe;
      switchTab('code');
    });
}

function deleteStrategy(id) {
  if (!confirm('Delete this strategy?')) return;
  fetch('/vibe/strategy/' + id, {method: 'DELETE'})
    .then(function(r) { return r.json(); })
    .then(function() { loadSavedStrategies(); });
}

// ── Comparison ──
function addToComparison() {
  if (!_lastResults) { alert('Run a backtest first'); return; }
  var code = document.getElementById('strategyCode').value;
  var name = prompt('Name this result:', 'Run ' + (_comparisonList.length + 1));
  if (!name) return;
  _comparisonList.push({name: name, code: code, results: _lastResults, equity: _lastResults.equity_curve || []});
  renderComparison();
}

function clearComparison() {
  _comparisonList = [];
  document.getElementById('comparisonSection').style.display = 'none';
}

function renderComparison() {
  var section = document.getElementById('comparisonSection');
  if (!_comparisonList.length) { section.style.display = 'none'; return; }
  section.style.display = 'block';

  var grid = document.getElementById('comparisonGrid');
  var html = '';
  for (var i = 0; i < _comparisonList.length; i++) {
    var item = _comparisonList[i];
    var m = item.results.metrics || {};
    html += '<div class="compare-card">'
      + '<div class="cc-name">' + escapeHtml(item.name) + '</div>'
      + '<div class="cc-row"><span>Return</span><span class="' + ((m.total_return_pct || 0) >= 0 ? 'pos' : 'neg') + '">' + (m.total_return_pct || 0).toFixed(2) + '%</span></div>'
      + '<div class="cc-row"><span>Sharpe</span><span>' + (m.sharpe || 0).toFixed(2) + '</span></div>'
      + '<div class="cc-row"><span>Sortino</span><span>' + (m.sortino || 0).toFixed(2) + '</span></div>'
      + '<div class="cc-row"><span>Win Rate</span><span>' + (m.win_rate || 0).toFixed(1) + '%</span></div>'
      + '<div class="cc-row"><span>PF</span><span>' + (m.profit_factor === Infinity ? '∞' : (m.profit_factor || 0).toFixed(2)) + '</span></div>'
      + '<div class="cc-row"><span>Max DD</span><span class="neg">' + (m.max_drawdown_pct || 0).toFixed(2) + '%</span></div>'
      + '<div class="cc-row"><span>Trades</span><span>' + (item.results.total_trades || 0) + '</span></div>'
      + '<div style="margin-top:4px"><span class="s-del" onclick="_comparisonList.splice(' + i + ',1);renderComparison()">✕ Remove</span></div>'
      + '</div>';
  }
  grid.innerHTML = html;
}

// ── Optimization ──
function detectParameters() {
  var code = document.getElementById('strategyCode').value;
  if (!code) return {};
  var params = {};
  var lines = code.split('\\n');
  for (var i = 0; i < lines.length; i++) {
    var parts = lines[i].trim().split('=');
    if (parts.length === 2) {
      var name = parts[0].trim();
      var val = parts[1].trim();
      if (/^[A-Z_][A-Z0-9_]*$/.test(name) && /^\\d+\\.?\\d*$/.test(val) && !name.startsWith('_')) {
        params[name] = parseFloat(val);
      }
    }
  }
  return params;
}

function renderOptParams() {
  var params = detectParameters();
  var container = document.getElementById('optParams');
  if (!container) return;
  if (!Object.keys(params).length) {
    container.innerHTML = '<div style="font-size:11px;color:#555">No parameters detected in code.</div>';
    return;
  }
  var html = '<div class="param-row" style="flex-wrap:wrap">';
  var pnames = Object.keys(params);
  for (var pi = 0; pi < pnames.length; pi++) {
    var name = pnames[pi];
    var val = params[name];
    var lo = Math.max(2, Math.round(val * 0.5));
    var hi = Math.round(val * 2);
    html += '<div><label>' + name + ' (=' + val + ')</label>'
      + '<input type="text" id="opt_' + name + '" value="' + lo + ',' + val + ',' + hi + '" placeholder="vals"></div>';
  }
  html += '</div>';
  container.innerHTML = html;
}

function runOptimization() {
  var code = document.getElementById('strategyCode').value;
  if (!code.trim()) { document.getElementById('optStatus').textContent = 'No code'; return; }

  var params = detectParameters();
  var paramGrid = {};
  var hasValues = false;
  var pnames = Object.keys(params);
  for (var pi = 0; pi < pnames.length; pi++) {
    var name = pnames[pi];
    var input = document.getElementById('opt_' + name);
    if (!input) continue;
    var vals = input.value.split(',').map(function(s) { return parseFloat(s.trim()); }).filter(function(v) { return !isNaN(v); });
    if (vals.length) { paramGrid[name] = vals; hasValues = true; }
  }
  if (!hasValues) { document.getElementById('optStatus').textContent = 'No parameters to optimize'; return; }

  var status = document.getElementById('optStatus');
  var resultsDiv = document.getElementById('optResults');
  resultsDiv.classList.add('hidden');
  status.textContent = 'Running optimization...';

  var ex = document.getElementById('vibeExchange').value;
  var sym = document.getElementById('vibeSymbol').value;
  var tf = document.getElementById('vibeTimeframe').value;
  var limit = parseInt(document.getElementById('vibeLimit').value) || 500;

  var codeTemplate = code;
  var pnames2 = Object.keys(params);
  for (var pi = 0; pi < pnames2.length; pi++) {
    var name = pnames2[pi];
    codeTemplate = codeTemplate.replace(
      new RegExp('^(' + name + ')\\s*=\\s*[0-9.]+', 'm'),
      '$1 = {' + name + '}'
    );
  }

  fetch('/vibe/optimize', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({code_template: codeTemplate, param_grid: paramGrid, exchange: ex, symbol: sym, timeframe: tf, limit: limit}),
  }).then(function(r) { return r.json(); }).then(function(data) {
    if (data.error) { status.textContent = 'Error: ' + data.error; return; }
    status.textContent = data.total_evaluated + '/' + data.total_possible + ' evaluated';
    var html = '';
    if (data.best) {
      html += '<div class="opt-row best"><span class="or-params">Best</span>'
        + '<span class="or-metrics">Shp ' + (data.best.metrics.sharpe || 0).toFixed(2)
        + ' | Ret ' + (data.best.metrics.total_return_pct || 0).toFixed(2) + '%'
        + ' | WR ' + (data.best.metrics.win_rate || 0).toFixed(1) + '%'
        + ' | Trades ' + (data.best.total_trades || 0)
        + '</span></div>';
    }
    for (var i = 0; i < data.results.length; i++) {
      var r = data.results[i];
      var rpkeys = Object.keys(r.params);
      var paramsStr = '';
      for (var rpi = 0; rpi < rpkeys.length; rpi++) {
        if (rpi > 0) paramsStr += ' ';
        paramsStr += rpkeys[rpi] + '=' + r.params[rpkeys[rpi]];
      }
      html += '<div class="opt-row">'
        + '<span class="or-params">' + paramsStr + '</span>'
        + '<span class="or-metrics">Shp ' + (r.metrics.sharpe || 0).toFixed(2)
        + ' | Ret ' + (r.metrics.total_return_pct || 0).toFixed(2) + '%'
        + ' | WR ' + (r.metrics.win_rate || 0).toFixed(1) + '%'
        + ' | Trades ' + (r.total_trades || 0)
        + '</span></div>';
    }
    resultsDiv.innerHTML = html;
    resultsDiv.classList.remove('hidden');
  }).catch(function(err) { status.textContent = 'Error: ' + err.message; });
}
</script>
</body>
</html>"""


@router.get("/vibe-lab", response_class=HTMLResponse)
async def vibe_lab_page():
    return VIBE_HTML
