import json
import os
import glob
from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

router = APIRouter()

SAVED_DIR = os.path.join(os.path.dirname(__file__), "..", "USERS_DOCUMENT", "saved_models")
os.makedirs(SAVED_DIR, exist_ok=True)


class StrategySaveRequest(BaseModel):
    name: str
    config: dict


@router.post("/strategy-lab/save")
async def strategy_save(req: StrategySaveRequest):
    safe_name = req.name.replace("/", "_").replace(" ", "_")
    path = os.path.join(SAVED_DIR, safe_name + ".json")
    with open(path, "w") as f:
        json.dump({"name": req.name, "config": req.config, "created": datetime.now().isoformat()}, f, indent=2)
    return {"name": req.name, "path": path}


@router.get("/strategy-lab/strategies")
async def strategy_list():
    strategies = []
    for fpath in sorted(glob.glob(os.path.join(SAVED_DIR, "*.json")), key=os.path.getmtime, reverse=True):
        try:
            with open(fpath) as f:
                data = json.load(f)
            strategies.append({
                "name": data.get("name", os.path.basename(fpath)),
                "created": data.get("created", ""),
                "path": fpath,
            })
        except (json.JSONDecodeError, OSError):
            continue
    return {"strategies": strategies}


@router.get("/strategy-lab/strategy/{name:path}")
async def strategy_load(name: str):
    # Try exact filename first
    for ext in ("", ".json"):
        fpath = os.path.join(SAVED_DIR, name + ext)
        if os.path.exists(fpath):
            try:
                with open(fpath) as f:
                    data = json.load(f)
                return data
            except (json.JSONDecodeError, OSError):
                return {"error": "Failed to load strategy"}
    # Try glob match
    for fpath in glob.glob(os.path.join(SAVED_DIR, "*.json")):
        try:
            with open(fpath) as f:
                data = json.load(f)
            if data.get("name") == name:
                return data
        except (json.JSONDecodeError, OSError):
            continue
    return {"error": "Strategy not found"}

LAB_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Candle Analytics — Strategy Lab</title>
<script defer src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #e0e0e0; padding: 16px; }
h1 { font-size: 18px; color: #e94560; margin-bottom: 12px; }
h1 a { color: #888; font-size: 12px; text-decoration: none; }
h1 a:hover { color: #e94560; }
h2 { font-size: 14px; color: #e94560; margin: 16px 0 8px; }
h3 { font-size: 12px; color: #888; margin: 10px 0 6px; }

.section { background: #16213e; border: 1px solid #0f3460; border-radius: 6px; padding: 12px; margin-bottom: 12px; }
.section-divider { height: 2px; background: linear-gradient(90deg, #e94560, #0f3460); margin: 16px 0; }

/* ── Part 1: Chat ── */
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
.analysis-card { background: #16213e; border: 1px solid #0f3460; border-radius: 6px; padding: 10px; margin: 6px 0; }
.analysis-card .analysis-score { font-size: 22px; font-weight: 800; text-align: center; padding: 8px; margin-bottom: 8px; border-radius: 4px; }
.analysis-card .score-good { background: #1b5e20; color: #a5d6a7; }
.analysis-card .score-mid { background: #e65100; color: #ffcc80; }
.analysis-card .score-bad { background: #b71c1c; color: #ef9a9a; }
.analysis-card .analysis-text { font-size: 12px; line-height: 1.5; margin-bottom: 8px; }
.analysis-card .analysis-section { margin-top: 8px; }
.analysis-card .analysis-label { font-size: 12px; font-weight: 700; margin-bottom: 4px; color: #e0e0e0; }
.analysis-card ul { margin: 0; padding-left: 16px; }
.analysis-card ul li { font-size: 11px; margin-bottom: 3px; color: #bbb; }
.analysis-card .suggestion-row { display: flex; gap: 6px; padding: 5px 0; border-bottom: 1px solid #0f3460; font-size: 11px; }
.analysis-card .suggestion-row:last-child { border-bottom: none; }
.analysis-card .suggestion-num { width: 20px; color: #e94560; font-weight: 700; flex-shrink: 0; }
.analysis-card .sug-old { color: #ef5350; text-decoration: line-through; }
.analysis-card .sug-new { color: #26a69a; font-weight: 600; }
.analysis-card .sug-reason { color: #888; font-size: 10px; margin-top: 2px; }

/* ── Part 2: Strategy Config ── */
#paramsSection { display: none; }
.strat-header { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 10px; padding: 8px; background: #0d1b2a; border: 1px solid #0f3460; border-radius: 4px; }
.strat-name-input { background: transparent; color: #e0e0e0; border: none; font-size: 15px; font-weight: 600; padding: 2px 6px; min-width: 160px; flex: 1; }
.strat-name-input:focus { outline: none; border-bottom: 1px solid #e94560; }
.strat-name-input::placeholder { color: #555; font-weight: 400; }
.strat-header select, .strat-header input { background: #0f3460; color: #e0e0e0; border: 1px solid #1a3a6b; padding: 3px 6px; border-radius: 3px; font-size: 11px; }
.field-sm { min-width: 80px; }
.field-tiny { width: 65px; padding-right: 20px !important; }

/* Engine Search Group */
.engine-group { background: #0d1b2a; border: 1px solid #1a3a6b; border-radius: 4px; margin-bottom: 10px; }
.engine-group-header { display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; cursor: pointer; font-size: 12px; font-weight: 600; color: #e0e0e0; user-select: none; }
.engine-group-header:hover { background: #16213e; }
.engine-toggle { font-size: 10px; color: #555; transition: transform 0.2s; }
.engine-group-body { padding: 8px 10px; border-top: 1px solid #1a3a6b; }
.engine-group-body.closed { display: none; }
.engine-row { display: flex; gap: 12px; margin-bottom: 8px; flex-wrap: wrap; }
.engine-row:last-child { margin-bottom: 0; }
.engine-field { display: flex; flex-direction: column; gap: 2px; min-width: 120px; flex: 1; }
.engine-field label { font-size: 10px; color: #888; white-space: nowrap; }
.ef-row { display: inline-flex; align-items: center; gap: 2px; }
.engine-field input[type=number],
.engine-field input[type=date] { background: #0f3460; color: #e0e0e0; border: 1px solid #1a3a6b; padding: 3px 6px; border-radius: 3px; font-size: 11px; max-width: 120px; }
.engine-field input[type=checkbox] { margin-right: 4px; vertical-align: middle; }
.ai-suggest-btn { vertical-align: middle; }
.engine-note { font-size: 10px; color: #555; padding: 4px 8px; background: #16213e; border-radius: 3px; margin-top: 4px; }

.trade-area { margin: 6px 0; display: flex; gap: 12px; }
.direction-column { flex: 1; min-width: 0; }
.direction-column.full-width-col { flex: 1 1 100%; }
.direction-column.half-width { flex: 1 1 calc(50% - 6px); }
.direction-column.hidden { display: none; }
.col-header { font-size: 11px; font-weight: 600; color: #e94560; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 1px; }

/* Trade card */
.trade-card { background: #0d1b2a; border: 1px solid #0f3460; border-radius: 5px; padding: 8px; margin-bottom: 8px; }
.trade-card-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; font-size: 12px; color: #e0e0e0; font-weight: 600; }
.trade-card-header .trade-del { margin-left: auto; cursor: pointer; color: #ef5350; font-size: 14px; opacity: .6; }
.trade-card-header .trade-del:hover { opacity: 1; }
.trade-sections { display: flex; gap: 8px; flex-wrap: wrap; }
.trade-section { flex: 1; min-width: 260px; background: #1a1a2e; border: 1px solid #0f3460; border-radius: 4px; padding: 6px; }
.trade-section-title { font-size: 10px; font-weight: 600; color: #888; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px; }
.conditions-box { margin-bottom: 6px; }
.cond-group { background: #16213e; border: 1px solid #1a3a6b; border-radius: 3px; padding: 4px 6px; margin-bottom: 4px; }
.cond-group-header { display: flex; align-items: center; gap: 4px; font-size: 10px; color: #888; margin-bottom: 3px; }
.cond-group-header select { background: #0f3460; color: #e0e0e0; border: 1px solid #1a3a6b; padding: 1px 4px; border-radius: 2px; font-size: 10px; }
.cond-row { display: flex; align-items: center; gap: 3px; margin-bottom: 3px; font-size: 10px; flex-wrap: wrap; }
.cond-row .cond-sc { display: inline-flex; gap: 0; }
.cond-row .cond-sc .sc-btn { background: #0f3460; color: #888; border: 1px solid #1a3a6b; padding: 1px 5px; font-size: 9px; cursor: pointer; }
.cond-row .cond-sc .sc-btn:first-child { border-radius: 2px 0 0 2px; }
.cond-row .cond-sc .sc-btn:last-child { border-radius: 0 2px 2px 0; }
.cond-row .cond-sc .sc-btn.active { background: #e94560; color: #fff; border-color: #e94560; }
.cond-row .cond-input { background: #0f3460; color: #e0e0e0; border: 1px solid #1a3a6b; padding: 1px 5px; border-radius: 2px; font-size: 10px; min-width: 120px; flex: 1; }
.cond-row .cond-input:focus { outline: none; border-color: #e94560; }
.cond-row .cond-del { cursor: pointer; color: #ef5350; font-size: 12px; padding: 0 2px; opacity: .6; }
.cond-row .cond-del:hover { opacity: 1; }
.cond-row .cond-badge { font-size: 8px; padding: 1px 4px; border-radius: 2px; background: #0f3460; color: #888; white-space: nowrap; }
.cond-row .cond-error { font-size: 9px; color: #ef5350; }
.cond-row .cond-suggest { position: relative; display: inline-block; flex: 1; min-width: 120px; }
.cond-row .cond-suggest input { width: 100%; box-sizing: border-box; }
.cond-suggest-dropdown { position: absolute; top: 100%; left: 0; right: 0; z-index: 1000; background: #0d1b2a; border: 1px solid #1a3a6b; border-radius: 0 0 4px 4px; max-height: 200px; overflow-y: auto; display: none; }
.cond-suggest-dropdown.show { display: block; }
.cond-suggest-item { padding: 4px 8px; font-size: 10px; cursor: pointer; border-bottom: 1px solid #0f3460; display: flex; justify-content: space-between; align-items: center; }
.cond-suggest-item:last-child { border-bottom: none; }
.cond-suggest-item:hover { background: #1a3a6b; }
.cond-suggest-item .cs-label { color: #e0e0e0; font-weight: 600; }
.cond-suggest-item .cs-cat { color: #555; font-size: 9px; margin-left: 8px; white-space: nowrap; }
.cond-suggest-item .cs-desc { color: #888; font-size: 9px; display: block; margin-top: 1px; }
.cond-suggest-item .cs-badge { background: #0f3460; color: #888; padding: 0 4px; border-radius: 2px; font-size: 8px; white-space: nowrap; }

/* Orders */
.orders-box { margin-top: 4px; }
.order-row { display: flex; align-items: center; gap: 3px; margin-bottom: 3px; font-size: 10px; flex-wrap: wrap; }
.order-row select, .order-row input[type=number] { background: #0f3460; color: #e0e0e0; border: 1px solid #1a3a6b; padding: 1px 4px; border-radius: 2px; font-size: 10px; }
.order-row input[type=number] { width: 55px; padding-right: 18px; }
.order-row .order-del { cursor: pointer; color: #ef5350; font-size: 12px; padding: 0 2px; opacity: .6; }
.order-row .order-del:hover { opacity: 1; }
.order-title { font-size: 9px; color: #555; font-weight: 600; margin: 4px 0 2px; }

input[type=number]::-webkit-inner-spin-button,
input[type=number]::-webkit-outer-spin-button {
  opacity: 1; background: #16213e;
  border-left: 1px solid #1a3a6b; height: 100%; cursor: pointer;
  width: 16px; margin: 0;
}
input[type=number]::-webkit-inner-spin-button:hover,
input[type=number]::-webkit-outer-spin-button:hover { background: #1a3a6b; }
input[type=number] { -moz-appearance: textfield; }
input[type=number]:hover, input[type=number]:focus { -moz-appearance: number-input; }

.controls { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.controls .btn { background: #0f3460; color: #e0e0e0; border: 1px solid #1a3a6b; padding: 5px 14px; border-radius: 4px; font-size: 12px; cursor: pointer; }
.controls .btn:hover { border-color: #e94560; }
.controls .btn-primary { background: #e94560; color: #fff; border: none; }
.controls .btn-primary:hover { background: #d63851; }
.controls .btn-sm { padding: 3px 8px; font-size: 11px; }

/* ── Part 3: Results ── */
.result-tabs { display: flex; gap: 0; margin-bottom: 8px; border-bottom: 1px solid #0f3460; }
.rtab { padding: 5px 12px; font-size: 11px; color: #888; cursor: pointer; border: 1px solid transparent; border-bottom: none; border-radius: 4px 4px 0 0; margin-bottom: -1px; }
.rtab:hover { color: #e0e0e0; }
.rtab.active { color: #e94560; border-color: #0f3460; background: transparent; }
.rtab-content { display: none; }
.rtab-content.active { display: block; }
#status { color: #888; font-size: 12px; margin-bottom: 8px; min-height: 18px; }

.stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 8px; margin-bottom: 12px; }
.stat-card { background: #1a1a2e; border: 1px solid #0f3460; border-radius: 4px; padding: 8px; text-align: center; }
.stat-card .val { font-size: 18px; font-weight: 600; }
.stat-card .lbl { font-size: 10px; color: #888; margin-top: 2px; }
.stat-card .pos { color: #26a69a; }
.stat-card .neg { color: #ef5350; }
.stat-card .neu { color: #e0e0e0; }
#histChart { max-height: 200px; width: 100%; }

.edge-table { width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 6px; }
.edge-table th, .edge-table td { padding: 4px 6px; text-align: right; border-bottom: 1px solid #0f3460; }
.edge-table th { color: #888; font-weight: 500; position: sticky; top: 0; background: #16213e; cursor: pointer; user-select: none; }
.edge-table th:hover { color: #e0e0e0; }
.edge-table td:first-child, .edge-table th:first-child { text-align: left; }
.edge-table tr:hover { background: #1a3a6b; }
.edge-wrap { max-height: 400px; overflow-y: auto; }
.edge-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 8px; }
.edge-card { background: #1a1a2e; border: 1px solid #0f3460; border-radius: 6px; padding: 8px; cursor: pointer; }
.edge-card:hover { border-color: #e94560; }
.edge-card .ec-title { font-size: 11px; color: #e94560; font-weight: 500; }
.edge-card .ec-row { display: flex; justify-content: space-between; font-size: 10px; color: #888; margin-top: 2px; }
.edge-card .ec-val { font-weight: 600; }
.view-toggle { display: inline-flex; gap: 0; }
.view-toggle .vt-btn { padding: 3px 8px; font-size: 10px; background: #0f3460; color: #888; border: 1px solid #1a3a6b; cursor: pointer; }
.view-toggle .vt-btn:first-child { border-radius: 3px 0 0 3px; }
.view-toggle .vt-btn:last-child { border-radius: 0 3px 3px 0; }
.view-toggle .vt-btn.active { background: #e94560; color: #fff; border-color: #e94560; }

.wf-table { width: 100%; border-collapse: collapse; font-size: 11px; }
.wf-table th, .wf-table td { padding: 3px 6px; text-align: center; border-bottom: 1px solid #0f3460; }
.wf-table th { color: #888; font-weight: 500; background: #16213e; }
.wf-degradation { font-size: 11px; padding: 4px 8px; border-radius: 3px; display: inline-block; }
.wf-degradation.good { background: #1a3a2e; color: #26a69a; }
.wf-degradation.bad { background: #3a1a1a; color: #ef5350; }

.mc-info { font-size: 11px; margin: 4px 0; }
.mc-info .sig { font-weight: 600; }
.mc-info .sig.yes { color: #26a69a; }
.mc-info .sig.no { color: #ef5350; }

.hidden { display: none; }
#sweepStatus { font-size: 11px; color: #888; margin-top: 4px; }

/* Browse button */
.btn-browse { background: none; border: 1px solid #1a3a6b; color: #888; padding: 1px 5px; border-radius: 3px; font-size: 11px; cursor: pointer; line-height: 1.4; }
.btn-browse:hover { border-color: #e94560; color: #e0e0e0; }

/* AI Suggest button + popover */
.ai-suggest-btn { background: none; border: none; color: #888; font-size: 14px; cursor: pointer; padding: 0 4px; opacity: 0.5; line-height: 1; vertical-align: middle; }
.ai-suggest-btn:hover { opacity: 1; color: #f9a825; }
.ai-suggest-popover { position: absolute; z-index: 5000; background: #0d1b2a; border: 1px solid #1a3a6b; border-radius: 6px; padding: 6px 0; min-width: 180px; max-width: 260px; box-shadow: 0 4px 16px rgba(0,0,0,0.4); display: none; }
.ai-suggest-popover.show { display: block; }
.ai-suggest-item { padding: 5px 12px; font-size: 11px; cursor: pointer; color: #c8d6e5; border-bottom: 1px solid #0f3460; }
.ai-suggest-item:last-child { border-bottom: none; }
.ai-suggest-item:hover { background: #1a3a6b; color: #e0e0e0; }
.ai-suggest-item .asi-label { color: #26a69a; font-weight: 500; }
.ai-suggest-item .asi-hint { color: #555; font-size: 9px; display: block; }

/* ── Condition Browser Modal ── */
.modal-overlay { display: none; position: fixed; z-index: 9999; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); }
.modal-overlay.show { display: block; }
.modal-content { position: relative; margin: 5% auto; width: 800px; max-width: 90%; max-height: 80vh; background: #16213e; border: 1px solid #0f3460; border-radius: 8px; overflow: hidden; display: flex; flex-direction: column; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 1px solid #0f3460; }
.modal-header h3 { margin: 0; font-size: 14px; color: #e94560; }
.modal-close { background: none; border: none; color: #888; font-size: 20px; cursor: pointer; padding: 0 4px; }
.modal-close:hover { color: #ef5350; }
.modal-body { display: flex; flex: 1; overflow: hidden; min-height: 300px; }
.modal-cats { width: 180px; min-width: 140px; overflow-y: auto; border-right: 1px solid #0f3460; padding: 8px 0; }
.modal-cat-item { padding: 8px 12px; font-size: 12px; cursor: pointer; color: #888; border-left: 2px solid transparent; }
.modal-cat-item:hover { color: #e0e0e0; background: #1a3a6b; }
.modal-cat-item.active { color: #e94560; border-left-color: #e94560; background: #0d1b2a; }
.modal-panel { flex: 1; overflow-y: auto; padding: 12px; }
.modal-subcat { margin-bottom: 12px; }
.modal-subcat-title { font-size: 11px; font-weight: 600; color: #888; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; padding-bottom: 4px; border-bottom: 1px solid #0f3460; }
.modal-ind-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 6px; margin-bottom: 10px; }
.modal-ind-item { background: #0d1b2a; border: 1px solid #1a3a6b; border-radius: 4px; padding: 6px 8px; cursor: pointer; font-size: 11px; }
.modal-ind-item:hover { border-color: #e94560; }
.modal-ind-item .mi-name { color: #e0e0e0; font-weight: 600; }
.modal-ind-item .mi-desc { color: #555; font-size: 9px; margin-top: 2px; }
.modal-ind-item .mi-preset { font-size: 9px; color: #26a69a; display: inline-block; margin-right: 4px; padding: 1px 4px; background: #1a3a2e; border-radius: 2px; }
.modal-metrics-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 4px; }
.modal-metric-item { background: #0d1b2a; border: 1px solid #1a3a6b; border-radius: 3px; padding: 5px 8px; cursor: pointer; font-size: 11px; }
.modal-metric-item:hover { border-color: #e94560; }
.modal-metric-item .mm-name { color: #26a69a; font-weight: 600; }
.modal-metric-item .mm-desc { color: #555; font-size: 9px; }

/* Scrollbar */
#chatLog::-webkit-scrollbar { width: 4px; }
#chatLog::-webkit-scrollbar-track { background: transparent; }
#chatLog::-webkit-scrollbar-thumb { background: #0f3460; border-radius: 2px; }
</style>
</head>
<body>

<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
  <h1 style="margin:0"><a href="/dashboard">&larr;</a> &nbsp;Strategy Lab</h1>
  <div style="display:flex;gap:0;border:1px solid #0f3460;border-radius:4px;overflow:hidden;font-size:12px">
    <a href="/strategy-lab" style="padding:5px 14px;background:#e94560;color:#fff;text-decoration:none;font-weight:500">Strategy Lab</a>
    <a href="/vibe-lab" style="padding:5px 14px;background:#0f3460;color:#888;text-decoration:none">Vibe Lab</a>
  </div>
  <span style="font-size:10px;color:#555;margin-left:auto">AI Strategy Editor</span>
</div>

<!-- ── PART 1: CHAT ── -->
<div class="section">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
    <div style="display:flex;align-items:center;gap:8px">
      <h2 style="margin:0">💬 Strategy IA Editor</h2>
      <button class="btn-chat" onclick="exportChat()" title="Export chat">📥 Export</button>
      <button class="btn-chat" onclick="newChat()" title="New conversation">✕ New</button>
    </div>
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
      <button class="btn-action improve" onclick="requestAmelioration()">📈 Amélioration</button>
      <button class="btn-action think" onclick="requestDeepThinking()">🧠 Deep Thinking</button>
    </div>
    <div id="typingIndicator" class="typing hidden">thinking...</div>
  </div>
</div>

<!-- ── PART 2: STRATEGY CONFIG ── -->
<div id="paramsSection" class="section">
  <div id="stratHeader" class="strat-header">
    <input type="text" id="cfgName" placeholder="[NOM_PERSONNALISABLE]" class="strat-name-input">
    <button type="button" class="ai-suggest-btn" onclick="showAISuggest(this,'cfgName')" title="AI suggest">✨</button>
    <select id="cfgExchange" class="field-sm"></select>
    <select id="cfgSymbol" class="field-sm"></select>
    <select id="cfgTimeframe" class="field-sm">
      <option value="1m">1m</option><option value="5m">5m</option><option value="15m">15m</option><option value="30m">30m</option>
      <option value="1H" selected>1H</option><option value="2H">2H</option><option value="4H">4H</option><option value="6H">6H</option><option value="12H">12H</option>
      <option value="1D">1D</option><option value="1W">1W</option><option value="1M">1M</option>
    </select>
    <input type="number" id="cfgLeverage" value="1" step="0.5" min="0.1" class="field-tiny" placeholder="Lev">
    <button type="button" class="ai-suggest-btn" onclick="showAISuggest(this,'cfgLeverage')" title="AI suggest">✨</button>
    <select id="cfgDirection" class="field-sm" onchange="onDirectionChange()">
      <option value="long_only">Long Only</option>
      <option value="short_only">Short Only</option>
      <option value="both">Both</option>
    </select>
  </div>

  <!-- ── Engine Search Group ── -->
  <div id="engineGroup" class="engine-group">
    <div class="engine-group-header" onclick="toggleEngineGroup()">
      <span>⚙️ Engine Search Group</span>
      <span class="engine-toggle" id="engineToggle">▼</span>
    </div>
    <div id="engineGroupBody" class="engine-group-body">
      <div class="engine-row">
        <div class="engine-field">
          <label title="Number of candles to look ahead for forward return calculation">LA (Lookahead)</label>
          <span class="ef-row"><input type="number" id="cfgLookahead" value="5" step="1" min="1" max="100">
          <button type="button" class="ai-suggest-btn" onclick="showAISuggest(this,'cfgLookahead')" title="AI suggest">✨</button></span>
        </div>
        <div class="engine-field">
          <label title="Minimum number of pattern occurrences required for a valid result">Min Occurrences</label>
          <span class="ef-row"><input type="number" id="cfgMinOcc" value="10" step="1" min="1" max="9999">
          <button type="button" class="ai-suggest-btn" onclick="showAISuggest(this,'cfgMinOcc')" title="AI suggest">✨</button></span>
        </div>
        <div class="engine-field">
          <label title="Number of Monte Carlo shuffles (0 = disabled). Randomizes forward returns to test robustness">MC Shuffles</label>
          <span class="ef-row"><input type="number" id="cfgMCShuffles" value="500" step="100" min="0" max="10000">
          <button type="button" class="ai-suggest-btn" onclick="showAISuggest(this,'cfgMCShuffles')" title="AI suggest">✨</button></span>
        </div>
      </div>
      <div class="engine-row">
        <div class="engine-field">
          <label title="Enable Walk-Forward analysis to test strategy robustness across time periods">
            <input type="checkbox" id="cfgWF" checked onchange="onWFChange()"> Walk-Forward
          </label>
        </div>
        <div class="engine-field">
          <label title="Number of walk-forward windows">WF Windows</label>
          <span class="ef-row"><input type="number" id="cfgWFWindows" value="5" step="1" min="2" max="20">
          <button type="button" class="ai-suggest-btn" onclick="showAISuggest(this,'cfgWFWindows')" title="AI suggest">✨</button></span>
        </div>
        <div class="engine-field">
          <label title="Percentage of each window used for training (rest = out-of-sample testing)">Train %</label>
          <span class="ef-row"><input type="number" id="cfgWFTrainPct" value="70" step="5" min="10" max="95">
          <button type="button" class="ai-suggest-btn" onclick="showAISuggest(this,'cfgWFTrainPct')" title="AI suggest">✨</button></span>
        </div>
      </div>
      <div class="engine-row">
        <div class="engine-field">
          <label title="Start date for backtest data range (leave empty for earliest available)">Train Start</label>
          <span class="ef-row"><input type="date" id="cfgStartDate">
          <button type="button" class="ai-suggest-btn" onclick="showAISuggest(this,'cfgStartDate')" title="AI suggest">✨</button></span>
        </div>
        <div class="engine-field">
          <label title="End date for backtest data range (leave empty for latest available)">Backtest End</label>
          <span class="ef-row"><input type="date" id="cfgEndDate">
          <button type="button" class="ai-suggest-btn" onclick="showAISuggest(this,'cfgEndDate')" title="AI suggest">✨</button></span>
        </div>
        <div class="engine-field">
          <label title="Enable automatic sweep across param values">
            <input type="checkbox" id="cfgSweep"> Sweep enabled
          </label>
        </div>
      </div>
      <div class="engine-note" title="Monte Carlo, Walk-Forward, and Sweep run automatically on every search">💡 Auto-mode enabled — MC, WF, and Sweep run automatically on every search</div>
    </div>
  </div>

  <div id="tradeArea" class="trade-area">
    <div class="direction-column full-width-col" id="longColumn">
      <div class="col-header">LONG</div>
      <div id="longTrades"></div>
      <button class="btn btn-sm" onclick="addTrade('long')">+ Trade</button>
    </div>
    <div class="direction-column hidden" id="shortColumn">
      <div class="col-header">SHORT</div>
      <div id="shortTrades"></div>
      <button class="btn btn-sm" onclick="addTrade('short')">+ Trade</button>
    </div>
  </div>
  <div class="controls" style="margin-top:10px">
    <button class="btn btn-primary" onclick="runSearch()">&#9654; Run Search</button>
    <button class="btn" onclick="saveStrategy()">&#128190; Save</button>
    <button class="btn" onclick="exportConfigJSON()">&#128196; Export JSON</button>
    <button class="btn" onclick="loadStrategy()">&#128218; Load</button>
    <button class="btn" onclick="clearConfig()">Clear</button>
  </div>
</div>

<div class="section-divider"></div>

<!-- ── PART 3: RESULTS ── -->
<div class="section">
  <h2>📊 Results</h2>
  <div id="status">Configure a strategy via the chat, then run a search</div>
  <div class="result-tabs">
    <div class="rtab active" data-rtab="main" onclick="switchRtab('main')">Edge</div>
    <div class="rtab" data-rtab="sweep" onclick="switchRtab('sweep')">Sweep</div>
    <div class="rtab" data-rtab="wf" onclick="switchRtab('wf')">Walk-Forward</div>
    <div class="rtab" data-rtab="mc" onclick="switchRtab('mc')">Monte Carlo</div>
    <div class="rtab" data-rtab="export" onclick="switchRtab('export')">Export</div>
  </div>

  <div class="rtab-content active" id="rtab-main">
    <div id="resultsContent" class="hidden">
      <div class="stat-grid" id="statGrid"></div>
      <canvas id="histChart"></canvas>
      <div id="histLegend" style="font-size:10px;color:#555;margin-top:4px"></div>
      <div class="controls" style="margin:8px 0">
        <div class="view-toggle">
          <div class="vt-btn active" data-view="grid" onclick="setView('grid')">Grid</div>
          <div class="vt-btn" data-view="cards" onclick="setView('cards')">Cards</div>
        </div>
      </div>
      <div id="edgeBrowser"></div>
    </div>
  </div>

  <div class="rtab-content" id="rtab-sweep">
    <div id="sweepStatus">Run a Sweep to see results</div>
    <div id="sweepContent" class="hidden">
      <div class="edge-wrap"><table class="edge-table" id="sweepTable"><thead></thead><tbody></tbody></table></div>
    </div>
  </div>

  <div class="rtab-content" id="rtab-wf">
    <div id="wfStatus">Run a search with Walk-Forward enabled</div>
    <div id="wfContent" class="hidden">
      <div id="wfSummary" style="font-size:12px;margin-bottom:8px"></div>
      <div class="edge-wrap"><table class="wf-table" id="wfTable"><thead></thead><tbody></tbody></table></div>
    </div>
  </div>

  <div class="rtab-content" id="rtab-mc">
    <div id="mcStatus">Run a search with Monte Carlo enabled</div>
    <div id="mcContent" class="hidden">
      <div id="mcResult" style="font-size:12px"></div>
    </div>
  </div>

  <div class="rtab-content" id="rtab-export">
    <div id="exportStatus">Run a search first, then export the edge</div>
    <div id="exportContent" class="hidden">
      <p style="font-size:11px;color:#888;margin-bottom:8px">Export the current edge definition:</p>
      <div class="controls">
        <button class="btn btn-sm" onclick="doExport('yaml')">YAML</button>
        <button class="btn btn-sm" onclick="doExport('json')">JSON</button>
        <button class="btn btn-sm" onclick="doExport('csv')">CSV (returns)</button>
      </div>
    </div>
  </div>
</div>

<script>
// ── Metrics definitions ──
var METRICS = {
  oc: { label: 'OC%', desc: '(close-open)/open*100' },
  oh: { label: 'OH%', desc: '(high-open)/open*100' },
  ol: { label: 'OL%', desc: '(low-open)/open*100' },
  hl: { label: 'HL%', desc: '(high-low)/open*100' },
  hc: { label: 'HC%', desc: '(high-close)/open*100' },
  lc: { label: 'LC%', desc: '(low-close)/open*100' },
  vol: { label: 'Vol%', desc: 'volume/maxVolume*100' },
};
var PCTL_METRICS = {};
var mkeys = Object.keys(METRICS);
for (var mi = 0; mi < mkeys.length; mi++) {
  var k = mkeys[mi];
  PCTL_METRICS['pctl_' + k] = { label: 'Pctl(' + METRICS[k].label + ')', desc: 'Percentile rank of ' + METRICS[k].label };
}
var ALL_METRICS = Object.assign({}, METRICS, PCTL_METRICS);
var OPS = { gt: '>', gte: '\u2265', lt: '<', lte: '\u2264', eq: '=', neq: '\u2260' };

// ── State ──
var _ws = null;
var _useFallback = false;
var _pendingId = null;
var _pendingPollInterval = null;
var _pendingChatTimeout = null;
var _currentConfig = null;
var _lastResult = null;
var _viewMode = 'grid';
var groupCounter = 0;

// ── WebSocket connection ──
function connectWS() {
  var statusDot = document.getElementById('connStatus');
  var statusLabel = document.getElementById('connLabel');
  statusDot.className = 'conn-status connecting';
  statusLabel.textContent = 'connecting...';

  var proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  var url = proto + '//' + location.host + '/api/ws/strategy-chat';

  try {
    _ws = new WebSocket(url);
  } catch (e) {
    onWSFail('Exception: ' + e.message);
    return;
  }

  _ws.onopen = function () {
    statusDot.className = 'conn-status connected';
    statusLabel.textContent = 'WebSocket connected';
    addChatMessage('system', 'Connected to strategy assistant');
  };

  _ws.onmessage = function (evt) {
    try {
      var data = JSON.parse(evt.data);
      handleWSMessage(data);
    } catch (e) {
      console.warn('WS parse error', e);
    }
  };

  _ws.onclose = function () {
    if (_useFallback) return;
    statusDot.className = 'conn-status disconnected';
    statusLabel.textContent = 'disconnected (will retry)';
    setTimeout(connectWS, 3000);
  };

  _ws.onerror = function () {
    onWSFail('Connection error');
  };
}

function onWSFail(reason) {
  if (_useFallback) return;
  console.warn('WS failed:', reason);
  document.getElementById('connStatus').className = 'conn-status disconnected';
  document.getElementById('connLabel').textContent = 'WebSocket failed, using HTTP fallback';
  addChatMessage('system', 'WebSocket unavailable — using HTTP fallback mode');
  _useFallback = true;
  _ws = null;
}

function handleWSMessage(data) {
  document.getElementById('typingIndicator').classList.add('hidden');

  if (data.type === 'ack') {
    _pendingId = data.id;
    addChatMessage('system', 'Message sent — processing...');
    if (_pendingChatTimeout) clearTimeout(_pendingChatTimeout);
    _pendingChatTimeout = setTimeout(function () {
      if (_pendingId) {
        addChatMessage('system', 'Still waiting...');
        document.getElementById('typingIndicator').classList.add('hidden');
      }
    }, 12000);
    return;
  }

  if (data.type === 'deep_thinking') {
    _pendingId = null;
    if (data.content) {
      addChatMessage('ai', renderAnalysis(data), true);
    }
    return;
  }

  if (data.type === 'amelioration') {
    _pendingId = null;
    if (data.content) {
      addChatMessage('ai', renderAmelioration(data), true);
    }
    return;
  }

  if (data.type === 'response' || data.type === 'message' || data.type === 'config_update') {
    if (_pendingChatTimeout) { clearTimeout(_pendingChatTimeout); _pendingChatTimeout = null; }
    var isConfig = data.type === 'config_update';
    if (data.content && !isConfig) {
      addChatMessage('ai', data.content);
    }
    if (isConfig || data.response) {
      var cfg = data.response || data;
      renderConfig(cfg);
      if (isConfig) {
        addChatMessage('system', '✓ Stratégie chargée — paramètres prêts dans le panneau de configuration');
      }
      if (data.ready) {
        showStrategyActions();
      }
    }
    _pendingId = null;
    return;
  }

  if (data.type === 'timeout') {
    if (_pendingChatTimeout) { clearTimeout(_pendingChatTimeout); _pendingChatTimeout = null; }
    addChatMessage('system', 'No response in time — check that the agent is running (screen -ls)');
    _pendingId = null;
  }
}

// ── Strategy action buttons ──
function showStrategyActions() {
  document.getElementById('strategyActions').classList.remove('hidden');
}
function hideStrategyActions() {
  document.getElementById('strategyActions').classList.add('hidden');
}

function sendChatPayload(type, content, extra) {
  var text = content || '';
  var payload = Object.assign({ type: type, content: text }, extra || {});
  if (_ws && _ws.readyState === WebSocket.OPEN) {
    document.getElementById('typingIndicator').classList.remove('hidden');
    _ws.send(JSON.stringify(payload));
  } else if (_useFallback) {
    fetch('/api/edge/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: text }),
    }).then(function (r) { return r.json(); }).then(function (data) {
      _pendingId = data.id;
      if (_pendingPollInterval) clearInterval(_pendingPollInterval);
      _pendingPollInterval = setInterval(function () { pollResponse(data.id); }, 1500);
      document.getElementById('typingIndicator').classList.remove('hidden');
    }).catch(function () {});
  } else {
    addChatMessage('system', 'Not connected. Retrying...');
    connectWS();
  }
}

function runBacktestFromChat() {
  addChatMessage('system', '⏳ Running backtest...');
  runSearch();
}

function requestDeepThinking() {
  var cfg = getSearchConfig();
  if (!cfg) { addChatMessage('system', 'No strategy configured'); return; }
  addChatMessage('system', '🧠 Analyzing strategy...');
  var configPayload = {
    exchange: cfg.exchange, symbol: cfg.symbol, timeframe: cfg.timeframe,
    lookahead: cfg.lookahead, min_occurrences: cfg.min_occurrences,
    groups: cfg.groups, logic: cfg.logic,
  };
  sendChatPayload('deep_thinking', 'Deep analysis requested', { config: configPayload });
}

function requestAmelioration() {
  var cfg = getSearchConfig();
  if (!cfg) { addChatMessage('system', 'No strategy to improve'); return; }
  if (!_lastResult) { addChatMessage('system', 'Run a backtest first, then request amélioration'); return; }
  addChatMessage('system', '📈 Analyzing results for improvements...');
  var configPayload = {
    exchange: cfg.exchange, symbol: cfg.symbol, timeframe: cfg.timeframe,
    lookahead: cfg.lookahead, min_occurrences: cfg.min_occurrences,
    groups: cfg.groups, logic: cfg.logic,
  };
  sendChatPayload('amelioration', 'Improvement suggestions requested', {
    config: configPayload, results: _lastResult,
  });
}

// ── Render analysis (deep thinking) in chat ──
function renderAnalysis(data) {
  var html = '<div class="analysis-card">';
  if (data.score != null) {
    var cls = data.score >= 7 ? 'score-good' : data.score >= 4 ? 'score-mid' : 'score-bad';
    html += '<div class="analysis-score ' + cls + '">' + data.score + '/10</div>';
  }
  if (data.content) html += '<div class="analysis-text">' + renderMarkdown(data.content) + '</div>';
  if (data.strengths && data.strengths.length) {
    html += '<div class="analysis-section"><div class="analysis-label">✅ Strengths</div><ul>';
    data.strengths.forEach(function (s) { html += '<li>' + renderMarkdown(s) + '</li>'; });
    html += '</ul></div>';
  }
  if (data.weaknesses && data.weaknesses.length) {
    html += '<div class="analysis-section"><div class="analysis-label">⚠️ Weaknesses</div><ul>';
    data.weaknesses.forEach(function (s) { html += '<li>' + renderMarkdown(s) + '</li>'; });
    html += '</ul></div>';
  }
  if (data.recommendations && data.recommendations.length) {
    html += '<div class="analysis-section"><div class="analysis-label">💡 Recommendations</div><ul>';
    data.recommendations.forEach(function (s) { html += '<li>' + renderMarkdown(s) + '</li>'; });
    html += '</ul></div>';
  }
  return html + '</div>';
}

function renderAmelioration(data) {
  var html = '<div class="analysis-card amelioration">';
  if (data.content) html += '<div class="analysis-text">' + renderMarkdown(data.content) + '</div>';
  if (data.suggestions && data.suggestions.length) {
    html += '<div class="analysis-section"><div class="analysis-label">💡 Suggested Changes</div>';
    data.suggestions.forEach(function (s, i) {
      html += '<div class="suggestion-row">'
        + '<div class="suggestion-num">#' + (i + 1) + '</div>'
        + '<div class="suggestion-detail">';
      if (s.param) html += '<code>' + s.param + '</code>: ';
      if (s.current != null) html += '<span class="sug-old">' + s.current + '</span> → ';
      if (s.suggested != null) html += '<span class="sug-new">' + s.suggested + '</span>';
      if (s.reason) html += '<div class="sug-reason">' + s.reason + '</div>';
      if (s.suggestion) html += '<div class="sug-reason">' + s.suggestion + '</div>';
      html += '</div></div>';
    });
    html += '</div>';
  }
  return html + '</div>';
}

// ── HTTP fallback ──
function sendViaHTTP(text) {
  document.getElementById('typingIndicator').classList.remove('hidden');
  addChatMessage('system', 'Message sent to OpenCode (terminal) — continue the conversation there');
  fetch('/api/edge/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
          addChatMessage('system', 'Still waiting... Make sure you are talking to OpenCode in the terminal');
          document.getElementById('typingIndicator').classList.add('hidden');
        }
      }, 12000);
    })
    .catch(function (err) {
      document.getElementById('typingIndicator').classList.add('hidden');
      addChatMessage('system', 'Error: ' + err.message);
    });
}

function pollResponse(id) {
  fetch('/api/edge/chat/' + id)
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.status === 'ready') {
        clearInterval(_pendingPollInterval);
        _pendingPollInterval = null;
        if (_pendingChatTimeout) { clearTimeout(_pendingChatTimeout); _pendingChatTimeout = null; }
        document.getElementById('typingIndicator').classList.add('hidden');
        var d = data.data;
        if (d.type === 'deep_thinking') {
          addChatMessage('ai', renderAnalysis(d), true);
        } else if (d.type === 'amelioration') {
          addChatMessage('ai', renderAmelioration(d), true);
        } else {
          var isCfg = d.type === 'config_update';
          if (d.content && !isCfg) addChatMessage('ai', d.content);
          if (d.response) renderConfig(d.response);
          else if (isCfg) { renderConfig(d); addChatMessage('system', '✓ Stratégie chargée — paramètres prêts dans le panneau de configuration'); }
        }
        _pendingId = null;
      }
    })
    .catch(function () {});
}

// ── Chat ──
function sendChatMessage() {
  var input = document.getElementById('chatInput');
  var text = input.value.trim();
  if (!text) return;

  input.value = ''; input.style.height = 'auto';
  addChatMessage('user', text);

  if (_ws && _ws.readyState === WebSocket.OPEN) {
    document.getElementById('typingIndicator').classList.remove('hidden');
    _ws.send(JSON.stringify({ type: 'message', content: text }));
  } else if (_useFallback) {
    sendViaHTTP(text);
  } else {
    addChatMessage('system', 'Not connected. Retrying...');
    connectWS();
  }
}

function renderMarkdown(text) {
  var escaped = text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\\n/g, '<br>');
  var html = escaped;
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  // bold
  html = html.replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>');
  // italic
  html = html.replace(/\\*(.+?)\\*/g, '<em>$1</em>');
  return html;
}

function addChatMessage(role, content, raw) {
  var log = document.getElementById('chatLog');
  var time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  var formatted = raw ? content : renderMarkdown(content);

  // AI stacking: append to last AI message
  if (role === 'ai') {
    var last = log.lastElementChild;
    if (last && last.classList.contains('ai')) {
      last.querySelector('.ai-body').insertAdjacentHTML('beforeend',
        '<hr class="ai-sep"><span>' + formatted + '</span>');
      log.scrollTop = log.scrollHeight;
      return;
    }
    // First AI message — create with avatar + body container
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
  var md = '# Strategy Lab — Chat Export\\n\\n';
  for (var ei = 0; ei < msgs.length; ei++) {
    var m = msgs[ei];
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
  a.download = 'strategy-chat-' + new Date().toISOString().slice(0, 10) + '.md';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
}

function newChat() {
  document.getElementById('chatLog').innerHTML = '';
  document.getElementById('paramsSection').style.display = 'none';
  document.getElementById('longTrades').innerHTML = '';
  document.getElementById('shortTrades').innerHTML = '';
  _currentConfig = null;
  _pendingId = null;
  if (_pendingPollInterval) { clearInterval(_pendingPollInterval); _pendingPollInterval = null; }
  if (_pendingChatTimeout) { clearTimeout(_pendingChatTimeout); _pendingChatTimeout = null; }
  document.getElementById('typingIndicator').classList.add('hidden');
  addChatMessage('system', 'New conversation started — defaults loaded');
  showDefaultConfig();
}

// ── Render config from AI / load ──
function renderConfig(cfg) {
  _currentConfig = cfg;
  var section = document.getElementById('paramsSection');
  section.style.display = 'block';

  // Header
  renderHeader(cfg);

  // Direction column visibility
  setDirection(cfg.direction || 'long_only');

  // Trades
  var longTrades = cfg.trades && cfg.trades.long ? cfg.trades.long : [];
  var shortTrades = cfg.trades && cfg.trades.short ? cfg.trades.short : [];
  renderTrades('long', longTrades);
  renderTrades('short', shortTrades);
}

function renderHeader(cfg) {
  var nameEl = document.getElementById('cfgName');
  if (nameEl) nameEl.value = cfg.name || '';
  if (cfg.exchange) loadPairsForConfig(cfg.exchange, cfg.symbol, cfg.timeframe);
  var la = document.getElementById('cfgLookahead');
  if (la && cfg.lookahead != null) la.value = cfg.lookahead;
  var mo = document.getElementById('cfgMinOcc');
  if (mo && cfg.min_occurrences != null) mo.value = cfg.min_occurrences;
  var lev = document.getElementById('cfgLeverage');
  if (lev && cfg.leverage != null) lev.value = cfg.leverage;
  var dir = document.getElementById('cfgDirection');
  if (dir && cfg.direction) dir.value = cfg.direction;
  // Engine group
  var mc = document.getElementById('cfgMCShuffles');
  if (mc && cfg.mc_shuffles != null) mc.value = cfg.mc_shuffles;
  var wf = document.getElementById('cfgWF');
  if (wf && cfg.walk_forward != null) wf.checked = cfg.walk_forward;
  var wfw = document.getElementById('cfgWFWindows');
  if (wfw && cfg.walk_windows != null) wfw.value = cfg.walk_windows;
  var wft = document.getElementById('cfgWFTrainPct');
  if (wft && cfg.walk_train_pct != null) wft.value = Math.round(cfg.walk_train_pct * 100);
  var sd = document.getElementById('cfgStartDate');
  if (sd && cfg.start_time) sd.value = new Date(cfg.start_time).toISOString().split('T')[0];
  var ed = document.getElementById('cfgEndDate');
  if (ed && cfg.end_time) ed.value = new Date(cfg.end_time).toISOString().split('T')[0];
  onWFChange();
}

function renderTrades(side, trades) {
  var container = document.getElementById(side + 'Trades');
  if (!container) return;
  var html = '';
  if (!trades || !trades.length) {
    // Default empty trade
    html = getTradeCardHTML(side, 0, null);
  } else {
    for (var ti = 0; ti < trades.length; ti++) {
      html += getTradeCardHTML(side, ti, trades[ti]);
    }
  }
  container.innerHTML = html;
}

// ── Trade card HTML generation ──
function getTradeCardHTML(side, idx, trade) {
  var t = trade || {};
  var open = t.open || {};
  var close = t.close || {};
  var html = '<div class="trade-card" data-side="' + side + '" data-idx="' + idx + '">';
  html += '<div class="trade-card-header">'
    + '<span>TRADE n°' + (idx + 1) + '</span>'
    + '<span class="trade-del" onclick="removeTrade(\\'' + side + '\\',' + idx + ')">&times;</span>'
    + '</div>';
  html += '<div class="trade-sections">';

  // OPEN TRADE
  html += '<div class="trade-section">';
  html += '<div class="trade-section-title">OPEN TRADE n°' + (idx + 1) + '</div>';
  html += getSectionHTML(side, idx, 'open', open);
  html += '</div>';

  // CLOSE TRADE
  html += '<div class="trade-section">';
  html += '<div class="trade-section-title">CLOSE TRADE n°' + (idx + 1) + '</div>';
  html += getSectionHTML(side, idx, 'close', close);
  html += '</div>';

  html += '</div></div>';
  return html;
}

function getSectionHTML(side, tradeIdx, which, section) {
  var html = '';

  // CONDITIONS
  html += '<div class="conditions-box">';
  var c = section.conditions || {};
  var groups = c.groups && c.groups.length ? c.groups : [{}];
  for (var gi = 0; gi < groups.length; gi++) {
    html += getCondGroupHTML(side, tradeIdx, which, gi, groups[gi], groups.length > 1);
  }
  html += '<button class="btn btn-sm" onclick="addCondGroup(\\'' + side + '\\',' + tradeIdx + ',\\'' + which + '\\')">+ Cond Group</button>';
  html += '</div>';

  // ORDERS
  html += '<div class="orders-box">';
  html += '<div class="order-title">ORDERS</div>';
  var orders = section.orders && section.orders.length ? section.orders : [{type:'market', size:1, size_type:'percent', price:null}];
  for (var oi = 0; oi < orders.length; oi++) {
    html += getOrderRowHTML(side, tradeIdx, which, oi, orders[oi]);
  }
  html += '<button class="btn btn-sm" onclick="addOrder(\\'' + side + '\\',' + tradeIdx + ',\\'' + which + '\\')">+ Order</button>';
  html += '</div>';

  return html;
}

function getCondGroupHTML(side, tradeIdx, which, gIdx, group, showDel) {
  var logic = group.logic || 'AND';
  var conds = group.conditions && group.conditions.length ? group.conditions : [];
  var html = '<div class="cond-group" data-side="' + side + '" data-ti="' + tradeIdx + '" data-which="' + which + '" data-gi="' + gIdx + '">';
  html += '<div class="cond-group-header">'
    + '<select onchange="setCondGroupLogic(this)">'
    + '<option value="AND"' + (logic === 'AND' ? ' selected' : '') + '>AND</option>'
    + '<option value="OR"' + (logic === 'OR' ? ' selected' : '') + '>OR</option>'
    + '</select>'
    + '<span>Group ' + (gIdx + 1) + '</span>';
  if (showDel) html += '<span style="flex:1"></span><span class="cond-del" onclick="removeCondGroup(this)">&times;</span>';
  html += '</div>';
  for (var ci = 0; ci < conds.length; ci++) {
    html += getCondRowHTML(side, tradeIdx, which, gIdx, ci, conds[ci]);
  }
  html += '<button class="btn btn-sm" onclick="addConditionToGroup(\\'' + side + '\\',' + tradeIdx + ',\\'' + which + '\\',' + gIdx + ')">+ Cond</button>';
  html += '</div>';
  return html;
}

function getCondRowHTML(side, tradeIdx, which, gIdx, cIdx, cond) {
  var subcat = cond.subcategory || 'threshold';
  var isPctl = subcat === 'pctl';
  var metricVal = cond.metric || '';
  var opVal = cond.op || '';
  var valNum = cond.value != null ? cond.value : '';
  var textVal = metricVal;
  if (isPctl) {
    textVal = 'pctl ' + valNum;
  } else if (metricVal && opVal) {
    textVal = metricVal + ' ' + (OPS[opVal] || opVal) + ' ' + valNum;
  }
  return '<div class="cond-row" data-side="' + side + '" data-ti="' + tradeIdx + '" data-which="' + which + '" data-gi="' + gIdx + '" data-ci="' + cIdx + '">'
    + '<span class="cond-sc">'
    + '<span class="sc-btn' + (subcat === 'threshold' ? ' active' : '') + '" data-sc="threshold" onclick="switchSubcat(this)">Threshold</span>'
    + '<span class="sc-btn' + (subcat === 'pctl' ? ' active' : '') + '" data-sc="pctl" onclick="switchSubcat(this)">Pctl</span>'
    + '</span>'
    + '<span class="cond-suggest"><input type="text" class="cond-input" value="' + textVal + '" placeholder="oc > 0.5 or pctl 80" onblur="parseCondInput(this); setTimeout(function(){ hideSuggest(this) }, 200)" oninput="searchConditions(this)" onfocus="searchConditions(this)"><div class="cond-suggest-dropdown"></div></span>'
    + '<button type="button" class="ai-suggest-btn" onclick="showAISuggest(this,\\'cond\\')" title="AI suggest">✨</button>'
    + '<button type="button" class="btn btn-sm btn-browse" onclick="openConditionBrowser(this)" title="Browse indicators">&nbsp;📊</button>'
    + '<span class="cond-del" onclick="this.parentElement.remove()">&times;</span>'
    + '<span class="cond-badge" id="condBadge-' + side + '-' + tradeIdx + '-' + which + '-' + gIdx + '-' + cIdx + '">' + (textVal || 'not set') + '</span>'
    + '</div>';
}

function getOrderRowHTML(side, tradeIdx, which, oIdx, order) {
  var ordTypes = ['market','limit','stop_market','stop_limit','sl','tp','ts'];
  var szTypes = ['percent','fixed','contracts'];
  var ot = order.type || 'market';
  var sz = order.size || 1;
  var st = order.size_type || 'percent';
  var pr = order.price != null ? order.price : '';
  return '<div class="order-row" data-side="' + side + '" data-ti="' + tradeIdx + '" data-which="' + which + '" data-oi="' + oIdx + '">'
    + '<select onchange="updateOrder(this)">'
    + ordTypes.map(function(t){return '<option value="' + t + '"' + (t === ot ? ' selected' : '') + '>' + t.toUpperCase() + '</option>';}).join('')
    + '</select>'
    + '<input type="number" step="0.5" value="' + sz + '" min="0" onchange="updateOrder(this)" style="width:55px" placeholder="Size">'
    + '<button type="button" class="ai-suggest-btn" onclick="showAISuggest(this,\\'order_size\\')" title="AI suggest">✨</button>'
    + '<select onchange="updateOrder(this)">'
    + szTypes.map(function(t){return '<option value="' + t + '"' + (t === st ? ' selected' : '') + '>' + t + '</option>';}).join('')
    + '</select>'
    + '<input type="number" step="0.5" value="' + pr + '" onchange="updateOrder(this)" style="width:60px" placeholder="Price">'
    + '<button type="button" class="ai-suggest-btn" onclick="showAISuggest(this,\\'order_price\\')" title="AI suggest">✨</button>'
    + '<span class="order-del" onclick="this.parentElement.remove()">&times;</span>'
    + '</div>';
}

// ── Condition parser ──
function parseCondInput(input) {
  var text = input.value.trim();
  var row = input.closest('.cond-row');
  var badge = row.querySelector('.cond-badge');
  var scBtns = row.querySelectorAll('.sc-btn');
  var subcat = 'threshold';
  for (var si = 0; si < scBtns.length; si++) {
    if (scBtns[si].classList.contains('active')) subcat = scBtns[si].getAttribute('data-sc');
  }

  // Reset params
  row.dataset.params = '{}';

  // Parse: metric(period) operator value  (indicator with params)
  var m = text.match(/^(\\w+)\\((\\d+)\\)\\s*(>=|<=|>|<|=|!=|gte|lte|gt|lt|eq|neq)\\s*([\\d.-]+)$/);
  if (m) {
    var opMap = {'>':'gt','>=':'gte','<':'lt','<=':'lte','=':'eq','!=':'neq','gt':'gt','gte':'gte','lt':'lt','lte':'lte','eq':'eq','neq':'neq'};
    var metric = m[1], op = opMap[m[3]] || m[3], val = parseFloat(m[4]);
    var period = parseInt(m[2]);
    var display = metric + '(' + period + ') ' + (OPS[op] || op) + ' ' + val;
    badge.textContent = display;
    badge.style.color = '#26a69a';
    row.dataset.parsed = '1';
    row.dataset.metric = metric;
    row.dataset.op = op;
    row.dataset.value = val;
    row.dataset.params = JSON.stringify({period: period});
    row.dataset.subcategory = subcat;
    return;
  }

  // Parse: metric operator value
  var m = text.match(/^(\\w+)\\s*(>=|<=|>|<|=|!=|gte|lte|gt|lt|eq|neq)\\s*([\\d.-]+)$/);
  if (m) {
    var opMap = {'>':'gt','>=':'gte','<':'lt','<=':'lte','=':'eq','!=':'neq','gt':'gt','gte':'gte','lt':'lt','lte':'lte','eq':'eq','neq':'neq'};
    var metric = m[1], op = opMap[m[2]] || m[2], val = parseFloat(m[3]);
    var display = metric + ' ' + (OPS[op] || op) + ' ' + val;
    badge.textContent = display;
    badge.style.color = '#26a69a';
    row.dataset.parsed = '1';
    row.dataset.metric = metric;
    row.dataset.op = op;
    row.dataset.value = val;
    row.dataset.subcategory = subcat;
    return;
  }

  // Parse: metric pctl value
  var m2 = text.match(/^(\\w+)\\s+pctl\\s+(\\d+)$/i);
  if (m2) {
    var metric2 = m2[1], val2 = parseInt(m2[2]);
    badge.textContent = 'Pctl(' + metric2 + ') >= ' + val2;
    badge.style.color = '#26a69a';
    row.dataset.parsed = '1';
    row.dataset.metric = 'pctl_' + metric2;
    row.dataset.op = 'gte';
    row.dataset.value = val2;
    row.dataset.subcategory = 'pctl';
    // Switch to pctl subcategory
    for (var si2 = 0; si2 < scBtns.length; si2++) {
      scBtns[si2].classList.toggle('active', scBtns[si2].getAttribute('data-sc') === 'pctl');
    }
    return;
  }

  badge.textContent = text || 'not set';
  badge.style.color = '#ef5350';
  row.dataset.parsed = '0';
  row.dataset.metric = '';
  row.dataset.op = '';
  row.dataset.value = '';
  row.dataset.subcategory = subcat;
}

var _searchTimeout = null;

// ── AI Suggest ──
var _suggestPopover = null;

function showAISuggest(btn, fieldName) {
  // Close existing popover
  if (_suggestPopover) { _suggestPopover.remove(); _suggestPopover = null; }

  // Find the closest input (previous sibling or inside the parent)
  var input = btn.previousElementSibling;
  while (input && input.tagName !== 'INPUT' && input.tagName !== 'TEXTAREA' && input.tagName !== 'SELECT') {
    input = input.previousElementSibling;
  }
  if (!input) input = btn.parentElement.querySelector('input, textarea, select');
  if (!input) return;

  var currentVal = input.value || '';

  // Create popover
  var popover = document.createElement('div');
  popover.className = 'ai-suggest-popover show';
  popover.innerHTML = '<div style="padding:6px 12px;font-size:10px;color:#555;border-bottom:1px solid #0f3460">AI suggestions for ' + fieldName + '</div><div class="asi-list" style="padding:0"><div style="padding:8px 12px;font-size:10px;color:#555">Loading...</div></div>';
  btn.parentElement.appendChild(popover);

  // Position below the button
  var rect = btn.getBoundingClientRect();
  popover.style.left = '0';
  popover.style.top = (btn.offsetHeight + 2) + 'px';

  _suggestPopover = popover;

  // Close on click outside
  setTimeout(function () {
    document.addEventListener('click', _closeSuggestPopover);
  }, 10);

  // Fetch suggestions
  fetch('/api/edge/suggest', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ field: fieldName, value: currentVal, config: getSearchConfig() || {} }),
  })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      var list = popover.querySelector('.asi-list');
      if (!data.suggestions || !data.suggestions.length) {
        list.innerHTML = '<div style="padding:8px 12px;font-size:10px;color:#555">No suggestions available</div>';
        return;
      }
      var html = '';
      for (var si = 0; si < data.suggestions.length; si++) {
        var sug = data.suggestions[si];
        html += '<div class="ai-suggest-item" onclick="applySuggest(this,\\'' + fieldName + '\\')" data-value="' + sug.value.replace(/"/g, '&quot;') + '">'
          + '<span class="asi-label">' + sug.label + '</span>'
          + (sug.hint ? '<span class="asi-hint">' + sug.hint + '</span>' : '')
          + '</div>';
      }
      list.innerHTML = html;
    })
    .catch(function () {
      var list = popover.querySelector('.asi-list');
      list.innerHTML = '<div style="padding:8px 12px;font-size:10px;color:#ef5350">Failed to load suggestions</div>';
    });
}

function _closeSuggestPopover(e) {
  if (_suggestPopover && !_suggestPopover.contains(e.target)) {
    _suggestPopover.remove();
    _suggestPopover = null;
    document.removeEventListener('click', _closeSuggestPopover);
  }
}

function applySuggest(el, fieldName) {
  var popover = el.closest('.ai-suggest-popover');
  var btn = popover.parentElement.querySelector('.ai-suggest-btn');
  var input = btn ? (btn.previousElementSibling || btn.parentElement.querySelector('input, textarea, select')) : null;
  if (!input) input = popover.parentElement.querySelector('input, textarea, select');
  if (!input) { popover.remove(); _suggestPopover = null; return; }

  var val = el.getAttribute('data-value') || el.textContent;
  input.value = val;

  // If this is a condition input, re-parse it
  if (input.classList.contains('cond-input')) {
    parseCondInput(input);
  }

  popover.remove();
  _suggestPopover = null;
  document.removeEventListener('click', _closeSuggestPopover);
}

function searchConditions(input) {
  if (_searchTimeout) clearTimeout(_searchTimeout);
  var dropdown = input.parentElement.querySelector('.cond-suggest-dropdown');
  if (!dropdown) return;
  var val = input.value.trim();
  if (val.match(/[>\\s]/)) { dropdown.classList.remove('show'); return; }
  _searchTimeout = setTimeout(function() {
    var q = encodeURIComponent(val);
    fetch('/api/conditions/search?q=' + q + '&max_results=8')
      .then(function(r) { return r.json(); })
      .then(function(data) {
        dropdown.innerHTML = '';
        if (!data.results || !data.results.length) {
          dropdown.innerHTML = '<div class="cond-suggest-item" style="color:#555;cursor:default">Aucun résultat — essayez une IA</div>';
          dropdown.classList.add('show');
          return;
        }
        data.results.forEach(function(entry) {
          var item = document.createElement('div');
          item.className = 'cond-suggest-item';
          var label = entry.label || entry.id;
          var cat = entry.category_label || '';
          var desc = entry.description || '';
          var hasPresets = entry.presets && entry.presets.length;
          item.innerHTML = '<div><span class="cs-label">' + label + '</span> <span class="cs-cat">' + cat + '</span><span class="cs-desc">' + desc + '</span></div>'
            + (hasPresets ? '<span class="cs-badge">' + entry.presets.length + ' presets</span>' : '<span class="cs-badge">' + (entry.type || '') + '</span>');
          item.onclick = function() { selectCondition(input, entry); };
          dropdown.appendChild(item);
        });
        dropdown.classList.add('show');
      })
      .catch(function() {});
  }, 300);
}

function hideSuggest(input) {
  var dropdown = input.parentElement.querySelector('.cond-suggest-dropdown');
  if (dropdown) dropdown.classList.remove('show');
}

function selectCondition(input, entry) {
  var row = input.closest('.cond-row');
  if (!row) return;
  var scBtns = row.querySelectorAll('.sc-btn');
  var subcat = 'threshold';
  for (var si = 0; si < scBtns.length; si++) {
    if (scBtns[si].classList.contains('active')) subcat = scBtns[si].getAttribute('data-sc');
  }
  // If entry has presets and first preset, use it
  if (entry.presets && entry.presets.length) {
    var preset = entry.presets[0];
    input.value = entry.id + ' ' + (preset.op || 'gt') + ' ' + preset.value;
  } else {
    input.value = entry.id + ' ' + (entry.default_op || 'gt') + ' ' + (entry.default_value != null ? entry.default_value : '');
  }
  parseCondInput(input);
  hideSuggest(input);
}

// ── Condition Browser Modal ──
var _browseInput = null;
var _catalogData = null;

function openConditionBrowser(btn) {
  _browseInput = btn.previousElementSibling.querySelector('.cond-input');
  var modal = document.getElementById('conditionModal');
  modal.classList.add('show');
  document.getElementById('modalPanel').innerHTML = '<div style="color:#555;font-size:12px;padding:20px;text-align:center">Loading...</div>';
  document.getElementById('modalCats').innerHTML = '';

  if (_catalogData) {
    renderCatalogCategories(_catalogData);
    return;
  }

  fetch('/api/conditions/catalog')
    .then(function (r) { return r.json(); })
    .then(function (data) {
      _catalogData = data;
      renderCatalogCategories(data);
    })
    .catch(function () {
      document.getElementById('modalPanel').innerHTML = '<div style="color:#ef5350;font-size:12px;padding:20px">Failed to load catalog</div>';
    });
}

function closeConditionBrowser() {
  document.getElementById('conditionModal').classList.remove('show');
  _browseInput = null;
}

function renderCatalogCategories(data) {
  var catKeys = Object.keys(data);
  var html = '';
  for (var ci = 0; ci < catKeys.length; ci++) {
    var key = catKeys[ci];
    var cat = data[key];
    var icon = cat.icon || '';
    html += '<div class="modal-cat-item' + (ci === 0 ? ' active' : '') + '" data-cat="' + key + '" onclick="selectCatalogCategory(\\'' + key + '\\')">' + icon + ' ' + cat.label + '</div>';
  }
  document.getElementById('modalCats').innerHTML = html;
  if (catKeys.length > 0) renderCatalogCategory(catKeys[0]);
}

function selectCatalogCategory(catId) {
  var items = document.querySelectorAll('.modal-cat-item');
  for (var ci = 0; ci < items.length; ci++) { items[ci].classList.toggle('active', items[ci].dataset.cat === catId); }
  renderCatalogCategory(catId);
}

function renderCatalogCategory(catId) {
  if (!_catalogData || !_catalogData[catId]) return;
  var cat = _catalogData[catId];
  var subcats = cat.subcategories || {};
  var subKeys = Object.keys(subcats);
  var html = '';

  for (var si = 0; si < subKeys.length; si++) {
    var sk = subKeys[si];
    var sub = subcats[sk];
    html += '<div class="modal-subcat"><div class="modal-subcat-title">' + sub.label + '</div>';

    // Metrics subcategory
    var metrics = sub.metrics || {};
    var mKeys = Object.keys(metrics);
    if (mKeys.length) {
      html += '<div class="modal-metrics-list">';
      for (var mi = 0; mi < mKeys.length; mi++) {
        var mk = mKeys[mi];
        var m = metrics[mk];
        html += '<div class="modal-metric-item" onclick="addFromCatalog(\\'' + mk + '\\')">'
          + '<div class="mm-name">' + (m.label || mk) + '</div>'
          + '<div class="mm-desc">' + (m.description || '').substring(0, 60) + '</div>'
          + '</div>';
      }
      html += '</div>';
    }

    // Indicators subcategory
    var indicators = sub.indicators || {};
    var iKeys = Object.keys(indicators);
    if (iKeys.length) {
      html += '<div class="modal-ind-list">';
      for (var ii = 0; ii < iKeys.length; ii++) {
        var ik = iKeys[ii];
        var ind = indicators[ik];
        html += '<div class="modal-ind-item" onclick="addFromCatalog(\\'' + ik + '\\')">'
          + '<div class="mi-name">' + (ind.label || ik) + '</div>'
          + '<div class="mi-desc">' + (ind.description || '').substring(0, 60) + '</div>';
        if (ind.presets) {
          for (var pi = 0; pi < ind.presets.length; pi++) {
            html += '<span class="mi-preset">' + ind.presets[pi].label + '</span>';
          }
        }
        html += '</div>';
      }
      html += '</div>';
    }

    html += '</div>';
  }

  document.getElementById('modalPanel').innerHTML = html || '<div style="color:#555;font-size:12px;padding:20px;text-align:center">No conditions in this category</div>';
}

function addFromCatalog(entryId) {
  if (!_browseInput) return;
  var input = _browseInput;
  // Look up the entry in FLAT_REGISTRY
  fetch('/api/conditions/search?q=' + encodeURIComponent(entryId) + '&max_results=1')
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.results && data.results.length) {
        selectCondition(input, data.results[0]);
      } else {
        input.value = entryId + ' > 0';
        parseCondInput(input);
      }
      closeConditionBrowser();
    })
    .catch(function () {
      input.value = entryId + ' > 0';
      parseCondInput(input);
      closeConditionBrowser();
    });
}

function switchSubcat(btn) {
  var sc = btn.parentElement;
  var btns = sc.querySelectorAll('.sc-btn');
  for (var si = 0; si < btns.length; si++) { btns[si].classList.toggle('active', btns[si] === btn); }
  var row = sc.closest('.cond-row');
  if (row) {
    var newSubcat = btn.getAttribute('data-sc');
    row.dataset.subcategory = newSubcat;
    // Re-parse the input to update badge
    var input = row.querySelector('.cond-input');
    if (input) parseCondInput(input);
  }
}

// ── Add / Remove helpers ──
function addTrade(side) {
  var container = document.getElementById(side + 'Trades');
  if (!container) return;
  var idx = container.children.length;
  var card = document.createElement('div');
  card.innerHTML = getTradeCardHTML(side, idx, null);
  container.appendChild(card.firstElementChild);
  reindexTrades(side);
}

function removeTrade(side, idx) {
  var container = document.getElementById(side + 'Trades');
  if (!container) return;
  var cards = container.querySelectorAll('.trade-card');
  if (cards[idx]) cards[idx].remove();
  reindexTrades(side);
}

function reindexTrades(side) {
  var container = document.getElementById(side + 'Trades');
  if (!container) return;
  var cards = container.querySelectorAll('.trade-card');
  for (var i = 0; i < cards.length; i++) {
    cards[i].dataset.idx = i;
    var header = cards[i].querySelector('.trade-card-header span:first-child');
    if (header) header.textContent = 'TRADE n°' + (i + 1);
    var titles = cards[i].querySelectorAll('.trade-section-title');
    if (titles[0]) titles[0].textContent = 'OPEN TRADE n°' + (i + 1);
    if (titles[1]) titles[1].textContent = 'CLOSE TRADE n°' + (i + 1);
  }
}

function addCondGroup(side, tradeIdx, which) {
  var card = getTradeCard(side, tradeIdx);
  if (!card) return;
  var section = card.querySelector('.trade-section' + (which === 'open' ? ':first-child' : ':last-child'));
  if (!section) return;
  var condBox = section.querySelector('.conditions-box');
  if (!condBox) return;
  var gIdx = condBox.querySelectorAll('.cond-group').length;
  var html = getCondGroupHTML(side, tradeIdx, which, gIdx, {}, true);
  condBox.insertAdjacentHTML('beforeend', html);
}

function removeCondGroup(el) {
  var group = el.closest('.cond-group');
  if (group) group.remove();
}

function addConditionToGroup(side, tradeIdx, which, gIdx) {
  var card = getTradeCard(side, tradeIdx);
  if (!card) return;
  var section = card.querySelector('.trade-section' + (which === 'open' ? ':first-child' : ':last-child'));
  if (!section) return;
  var group = section.querySelector('.cond-group[data-gi="' + gIdx + '"]');
  if (!group) return;
  var conds = group.querySelectorAll('.cond-row');
  var cIdx = conds.length;
  var row = document.createElement('div');
  row.innerHTML = getCondRowHTML(side, tradeIdx, which, gIdx, cIdx, {});
  group.insertBefore(row.firstElementChild, group.querySelector('button'));
}

function addOrder(side, tradeIdx, which) {
  var card = getTradeCard(side, tradeIdx);
  if (!card) return;
  var section = card.querySelector('.trade-section' + (which === 'open' ? ':first-child' : ':last-child'));
  if (!section) return;
  var ordersBox = section.querySelector('.orders-box');
  if (!ordersBox) return;
  var orders = ordersBox.querySelectorAll('.order-row');
  var oIdx = orders.length;
  var row = document.createElement('div');
  row.innerHTML = getOrderRowHTML(side, tradeIdx, which, oIdx, {});
  ordersBox.insertBefore(row.firstElementChild, ordersBox.querySelector('button'));
}

function setCondGroupLogic(sel) {
  // no visual update needed, data is read from DOM
}

function updateOrder(el) {
  // data is read from DOM on getSearchConfig
}

function getTradeCard(side, tradeIdx) {
  var container = document.getElementById(side + 'Trades');
  if (!container) return null;
  var cards = container.querySelectorAll('.trade-card');
  return cards[tradeIdx] || null;
}

// ── Direction column toggle ──
// ── Engine Search Group toggle ──
function toggleEngineGroup() {
  var body = document.getElementById('engineGroupBody');
  var toggle = document.getElementById('engineToggle');
  if (!body || !toggle) return;
  var closed = body.classList.toggle('closed');
  toggle.textContent = closed ? '▶' : '▼';
}

function onWFChange() {
  var wf = document.getElementById('cfgWF').checked;
  document.getElementById('cfgWFWindows').disabled = !wf;
  document.getElementById('cfgWFTrainPct').disabled = !wf;
}

function onDirectionChange() {
  var dir = document.getElementById('cfgDirection').value;
  setDirection(dir);
}
function setDirection(dir) {
  var longCol = document.getElementById('longColumn');
  var shortCol = document.getElementById('shortColumn');
  if (!longCol || !shortCol) return;
  longCol.classList.remove('full-width-col', 'half-width', 'hidden');
  shortCol.classList.remove('full-width-col', 'half-width', 'hidden');
  if (dir === 'short_only') {
    longCol.classList.add('hidden');
    shortCol.classList.add('full-width-col');
  } else if (dir === 'both') {
    longCol.classList.add('half-width');
    shortCol.classList.add('half-width');
  } else {
    // long_only (default)
    shortCol.classList.add('hidden');
    longCol.classList.add('full-width-col');
  }
}

// ── Show default config (with example template) ──
function showDefaultConfig() {
  renderConfig({
    name: 'ex: SMA Crossover + RSI',
    exchange: 'binance', symbol: 'BTCUSDC', timeframe: '1H', leverage: 1,
    direction: 'long_only', lookahead: 5, min_occurrences: 10,
    mc_shuffles: 500, walk_forward: true, walk_windows: 5, walk_train_pct: 0.7,
    trades: {
      long: [{
        open: {
          conditions: {
            logic: 'AND',
            groups: [
              { logic: 'AND', conditions: [
                { subcategory: 'threshold', metric: 'oc', op: 'gt', value: 0.2 },
              ]},
            ],
          },
          orders: [{ type: 'market', size: 1, size_type: 'percent', price: null }],
        },
        close: {
          conditions: { logic: 'AND', groups: [] },
          orders: [
            { type: 'sl', size: 1, size_type: 'percent', price: 1.0 },
            { type: 'tp', size: 1, size_type: 'percent', price: 2.5 },
          ],
        },
      }],
      short: [],
    },
  });
}

// ── Load pairs for config ──
function loadPairsForConfig(exchange, symbol, timeframe) {
  var exEl = document.getElementById('cfgExchange');
  var symEl = document.getElementById('cfgSymbol');
  var tfEl = document.getElementById('cfgTimeframe');

  fetch('/api/pairs')
    .then(function (r) { return r.json(); })
    .then(function (data) {
      var exchanges = [];
      var seenEx = {};
      data.pairs.forEach(function (p) { if (!seenEx[p.exchange]) { seenEx[p.exchange] = true; exchanges.push(p.exchange); } });
      exEl.innerHTML = exchanges.map(function (e) { return '<option value="' + e + '">' + e + '</option>'; }).join('');
      if (exchange) exEl.value = exchange;

      var symbols = [];
      var seenSym = {};
      data.pairs.forEach(function (p) {
        if (p.exchange === exEl.value && !seenSym[p.symbol]) { seenSym[p.symbol] = true; symbols.push(p.symbol); }
      });
      symEl.innerHTML = symbols.map(function (s) { return '<option value="' + s + '">' + s + '</option>'; }).join('');
      if (symbol) symEl.value = symbol;
      if (timeframe) tfEl.value = timeframe;

      exEl.addEventListener('change', function () {
        var syms = [];
        var seenSym2 = {};
        data.pairs.forEach(function (p) {
          if (p.exchange === exEl.value && !seenSym2[p.symbol]) { seenSym2[p.symbol] = true; syms.push(p.symbol); }
        });
        symEl.innerHTML = syms.map(function (s) { return '<option value="' + s + '">' + s + '</option>'; }).join('');
      });
    });
}

// ── Clear config ──
function clearConfig() {
  document.getElementById('paramsSection').style.display = 'none';
  _currentConfig = null;
  hideStrategyActions();
}

// ── Get config from UI ──
function getSearchConfig() {
  var ex = document.getElementById('cfgExchange');
  var sym = document.getElementById('cfgSymbol');
  var tf = document.getElementById('cfgTimeframe');
  if (!ex || !sym) return null;

  var trades = { long: [], short: [] };
  ['long', 'short'].forEach(function (side) {
    var container = document.getElementById(side + 'Trades');
    if (!container) return;
    var cards = container.querySelectorAll('.trade-card');
    for (var ci = 0; ci < cards.length; ci++) {
      var card = cards[ci];
      var trade = { open: getSectionData(card, 0), close: getSectionData(card, 1) };
      trades[side].push(trade);
    }
  });

  // Flatten all conditions into groups for the backend API
  var allGroups = [];
  var allLogic = 'AND';
  trades.long.concat(trades.short).forEach(function (t) {
    [t.open, t.close].forEach(function (s) {
      if (s.conditions && s.conditions.length) {
        s.conditions.forEach(function (g) {
          if (g.conditions && g.conditions.length) allGroups.push(g);
        });
      }
    });
  });

  if (allGroups.length === 0) return null;

  var lookahead = parseInt(document.getElementById('cfgLookahead').value) || 5;
  var minOcc = parseInt(document.getElementById('cfgMinOcc').value) || 5;
  var mcShuffles = parseInt(document.getElementById('cfgMCShuffles').value) || 500;
  var wfEnabled = document.getElementById('cfgWF').checked;
  var wfWindows = parseInt(document.getElementById('cfgWFWindows').value) || 5;
  var wfTrainPct = (parseInt(document.getElementById('cfgWFTrainPct').value) || 70) / 100;
  var startDate = document.getElementById('cfgStartDate').value;
  var endDate = document.getElementById('cfgEndDate').value;

  var cfg = {
    exchange: ex.value, symbol: sym.value, timeframe: tf.value,
    lookahead: lookahead,
    min_occurrences: minOcc,
    monte_carlo_shuffles: mcShuffles,
    groups: allGroups,
    logic: allLogic,
    direction: document.getElementById('cfgDirection').value,
  };
  if (wfEnabled) {
    cfg.walk_forward = true;
    cfg.walk_windows = wfWindows;
    cfg.walk_train_pct = wfTrainPct;
  }
  if (startDate) cfg.start_time = new Date(startDate).getTime();
  if (endDate) cfg.end_time = new Date(endDate).getTime();
  return cfg;
}

function getSectionData(card, sectionIdx) {
  var sections = card.querySelectorAll('.trade-section');
  var section = sections[sectionIdx];
  if (!section) return { conditions: [], orders: [] };

  // Gather conditions
  var condGroups = [];
  var groups = section.querySelectorAll('.cond-group');
  for (var gi = 0; gi < groups.length; gi++) {
    var g = groups[gi];
    var logicEl = g.querySelector('.cond-group-header select');
    var logic = logicEl ? logicEl.value : 'AND';
    var conds = [];
    var rows = g.querySelectorAll('.cond-row');
    for (var ri = 0; ri < rows.length; ri++) {
      var row = rows[ri];
      if (row.dataset.parsed !== '1') continue;
      var cond = {
        subcategory: row.dataset.subcategory || 'threshold',
        metric: row.dataset.metric,
        op: row.dataset.op,
        value: parseFloat(row.dataset.value),
      };
      if (row.dataset.params && row.dataset.params !== '{}') {
        try { cond.params = JSON.parse(row.dataset.params); } catch(e) {}
      }
      conds.push(cond);
    }
    if (conds.length) condGroups.push({ logic: logic, conditions: conds });
  }

  // Gather orders
  var orders = [];
  var orderRows = section.querySelectorAll('.order-row');
  for (var oi = 0; oi < orderRows.length; oi++) {
    var or = orderRows[oi];
    var selects = or.querySelectorAll('select');
    var inputs = or.querySelectorAll('input[type=number]');
    orders.push({
      type: selects[0] ? selects[0].value : 'market',
      size: inputs[0] ? parseFloat(inputs[0].value) || 1 : 1,
      size_type: selects[1] ? selects[1].value : 'percent',
      price: inputs[1] ? parseFloat(inputs[1].value) || null : null,
    });
  }

  return { conditions: condGroups, orders: orders };
}

// ── Config JSON (full export schema) ──
function getConfigJSON() {
  var cfg = {
    name: document.getElementById('cfgName').value,
    exchange: document.getElementById('cfgExchange').value,
    symbol: document.getElementById('cfgSymbol').value,
    timeframe: document.getElementById('cfgTimeframe').value,
    leverage: parseFloat(document.getElementById('cfgLeverage').value) || 1,
    direction: document.getElementById('cfgDirection').value,
    lookahead: parseInt(document.getElementById('cfgLookahead').value) || 5,
    min_occurrences: parseInt(document.getElementById('cfgMinOcc').value) || 5,
    trades: { long: [], short: [] },
  };

  ['long', 'short'].forEach(function (side) {
    var container = document.getElementById(side + 'Trades');
    if (!container) return;
    var cards = container.querySelectorAll('.trade-card');
    for (var ci = 0; ci < cards.length; ci++) {
      var card = cards[ci];
      cfg.trades[side].push({
        open: getSectionExport(card, 0),
        close: getSectionExport(card, 1),
      });
    }
  });

  return cfg;
}

function getSectionExport(card, sectionIdx) {
  var s = getSectionData(card, sectionIdx);
  return {
    conditions: { logic: 'AND', groups: s.conditions },
    orders: s.orders,
  };
}

// ── Save / Load / Export ──
function saveStrategy() {
  var cfg = getConfigJSON();
  if (!cfg || !cfg.trades || (!cfg.trades.long.length && !cfg.trades.short.length)) {
    addChatMessage('system', 'Nothing to save — configure a strategy first');
    return;
  }
  var name = cfg.name || prompt('Name this strategy config:', 'strategy-' + new Date().toISOString().slice(0, 10));
  if (!name) return;
  fetch('/strategy-lab/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: name, config: cfg }),
  }).then(function (r) { return r.json(); }).then(function (d) {
    addChatMessage('system', '✅ Strategy saved: ' + d.name);
  }).catch(function (err) {
    addChatMessage('system', 'Error saving: ' + err.message);
  });
}

function loadStrategy() {
  fetch('/strategy-lab/strategies')
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (!data.strategies || !data.strategies.length) {
        addChatMessage('system', 'No saved strategies found');
        return;
      }
      var html = '<div style="font-size:12px;margin:8px 0"><b>Saved strategies:</b><br>';
      for (var si = 0; si < data.strategies.length; si++) {
        var s = data.strategies[si];
        html += '<div style="padding:4px 0;border-bottom:1px solid #0f3460;display:flex;justify-content:space-between">'
          + '<a href="#" onclick="loadStrategyByName(\\'' + s.name.replace(/\\'/g, '\\u0027') + '\\');return false" style="color:#26a69a;font-size:12px">' + s.name + '</a>'
          + '<span style="font-size:10px;color:#555">' + (s.created || '') + '</span>'
          + '</div>';
      }
      html += '</div>';
      addChatMessage('ai', html, true);
    })
    .catch(function (err) { addChatMessage('system', 'Error loading: ' + err.message); });
}

function loadStrategyByName(name) {
  fetch('/strategy-lab/strategy/' + encodeURIComponent(name))
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.config) {
        renderConfig(data.config);
        addChatMessage('system', '✅ Loaded: ' + name);
      } else {
        addChatMessage('system', 'Error: ' + (data.error || 'unknown'));
      }
    })
    .catch(function (err) { addChatMessage('system', 'Error: ' + err.message); });
}

function exportConfigJSON() {
  var cfg = getConfigJSON();
  if (!cfg) { addChatMessage('system', 'Nothing to export'); return; }
  var blob = new Blob([JSON.stringify(cfg, null, 2)], { type: 'application/json' });
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'strategy-config-' + new Date().toISOString().slice(0, 10) + '.json';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
  addChatMessage('system', '📄 Config exported as JSON');
}

// ── Run Search ──
async function runSearch() {
  var cfg = getSearchConfig();
  if (!cfg) {
    document.getElementById('status').textContent = 'Build a strategy via chat first, or add conditions below';
    return;
  }

  var status = document.getElementById('status');
  status.textContent = 'Searching...';
  document.getElementById('resultsContent').classList.add('hidden');
  document.getElementById('wfContent').classList.add('hidden');
  document.getElementById('mcContent').classList.add('hidden');
  document.getElementById('exportContent').classList.add('hidden');
  switchRtab('main');

  try {
    var startTime = Date.now();
    var r = await fetch('/api/edge/search', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cfg),
    });
    var data = await r.json();
    _lastResult = data;

    if (data.error) {
      status.textContent = data.occurrences + ' occ — ' + data.error;
      return;
    }

    var elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    status.textContent = data.occurrences + ' occ, ' + data.forward_count + ' fwd (' + elapsed + 's)';
    document.getElementById('resultsContent').classList.remove('hidden');
    renderStats(data);
    renderHistogram(data);
    renderEdgeBrowser(data);

    if (data.walk_forward) { renderWalkForward(data.walk_forward); document.getElementById('wfContent').classList.remove('hidden'); }
    if (data.monte_carlo) { renderMonteCarlo(data.monte_carlo); document.getElementById('mcContent').classList.remove('hidden'); }
    document.getElementById('exportContent').classList.remove('hidden');
    document.getElementById('exportStatus').textContent = 'Ready to export ' + data.occurrences + ' occurrences';

    // Chat recap
    var wrCls = data.win_rate >= 50 ? '✅' : '⚠️';
    var recap = '<div style="font-size:12px;line-height:1.6">'
      + '<strong>Backtest Results</strong><br>'
      + wrCls + ' Win Rate: <strong>' + data.win_rate.toFixed(1) + '%</strong> &nbsp;|&nbsp; '
      + 'Sharpe: <strong>' + data.sharpe.toFixed(2) + '</strong> &nbsp;|&nbsp; '
      + 'PF: <strong>' + (data.profit_factor === Infinity ? '∞' : data.profit_factor.toFixed(2)) + '</strong><br>'
      + 'Occurrences: ' + data.occurrences + ' &nbsp;|&nbsp; '
      + 'Avg Return: ' + data.avg_return.toFixed(4) + '% &nbsp;|&nbsp; '
      + 'Max DD: ' + data.max_drawdown.toFixed(2) + '%<br>'
      + '<span style="font-size:10px;color:#555">' + elapsed + 's &nbsp;•&nbsp; '
      + '<a href="#" onclick="switchRtab(\\'main\\');return false" style="color:#26a69a">View in Results tab →</a></span>'
      + '</div>';
    addChatMessage('ai', recap, true);
  } catch (err) {
    status.textContent = 'Error: ' + err.message;
  }
}

// ── Run Sweep ──
async function runSweep() {
  var cfg = getSearchConfig();
  if (!cfg) {
    document.getElementById('status').textContent = 'Build a strategy via chat first';
    return;
  }

  var firstCond = cfg.groups[0] && cfg.groups[0].conditions[0];
  if (!firstCond) {
    document.getElementById('status').textContent = 'Add at least one condition for sweep';
    return;
  }

  var body = {
    exchange: cfg.exchange, symbol: cfg.symbol, timeframe: cfg.timeframe,
    lookahead_values: [1, 3, 5, 10],
    min_occurrences: cfg.min_occurrences || 5,
    groups: cfg.groups, logic: cfg.logic,
    sweep_params: [{ metric: firstCond.metric, op: firstCond.op, values: [0.5, 1, 1.5, 2, 3, 5] }],
  };
  if (cfg.start_time) body.start_time = cfg.start_time;
  if (cfg.end_time) body.end_time = cfg.end_time;

  switchRtab('sweep');
  document.getElementById('sweepContent').classList.remove('hidden');
  document.getElementById('sweepStatus').textContent = 'Sweeping ' + firstCond.metric + '...';

  try {
    var r = await fetch('/api/edge/sweep', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    var data = await r.json();
    if (data.error) { document.getElementById('sweepStatus').textContent = 'Error: ' + data.error; return; }

    document.getElementById('sweepStatus').textContent = data.results_count + ' results from ' + data.total_combinations + ' combinations';
    var html = '<thead><tr><th onclick="sortSweepTable(0)">Metric</th><th onclick="sortSweepTable(1)">Val</th><th onclick="sortSweepTable(2)">LA</th>'
      + '<th onclick="sortSweepTable(3)">WR%</th><th onclick="sortSweepTable(4)">Sharpe</th><th onclick="sortSweepTable(5)">Occ</th><th onclick="sortSweepTable(6)">Avg R%</th><th onclick="sortSweepTable(7)">PF</th></tr></thead><tbody>';
    for (var ri = 0; ri < data.results.length; ri++) {
      var r = data.results[ri];
      html += '<tr><td>' + r.sweep_metric + '</td><td>' + r.sweep_value + '</td><td>' + r.sweep_lookahead + '</td>'
        + '<td class="' + (r.win_rate >= 50 ? 'pos' : 'neg') + '">' + r.win_rate + '%</td>'
        + '<td class="' + (r.sharpe >= 1 ? 'pos' : r.sharpe >= 0 ? 'neu' : 'neg') + '">' + r.sharpe + '</td>'
        + '<td>' + r.occurrences + '</td><td>' + r.avg_return + '%</td><td>' + r.profit_factor + '</td></tr>';
    }
    html += '</tbody>';
    document.getElementById('sweepTable').innerHTML = html;
  } catch (err) {
    document.getElementById('sweepStatus').textContent = 'Error: ' + err.message;
  }
}

function sortSweepTable(col) {
  var st = document.getElementById('sweepTable');
  var tbody = st.querySelector('tbody');
  if (!tbody) return;
  var rows = [];
  for (var ri = 0; ri < tbody.children.length; ri++) { rows.push(tbody.children[ri]); }
  rows.sort(function (a, b) {
    var ac = a.children[col];
    var bc = b.children[col];
    var va = parseFloat(ac ? ac.textContent : '0');
    var vb = parseFloat(bc ? bc.textContent : '0');
    return (va - vb) * (st._sortDir || 1);
  });
  tbody.replaceChildren(...rows);
  st._sortDir = -(st._sortDir || 1);
}

// ── Render helpers ──
function renderStats(data) {
  var grid = document.getElementById('statGrid');
  var cards = [
    { label: 'Occurrences', val: data.occurrences, cls: 'neu' },
    { label: 'Forward Count', val: data.forward_count, cls: 'neu' },
    { label: 'Win Rate', val: data.win_rate.toFixed(1) + '%', cls: data.win_rate >= 50 ? 'pos' : 'neg' },
    { label: 'Wins / Losses', val: data.wins + ' / ' + data.losses, cls: 'neu' },
    { label: 'Avg Return', val: data.avg_return.toFixed(4) + '%', cls: data.avg_return >= 0 ? 'pos' : 'neg' },
    { label: 'Avg Win', val: data.avg_win.toFixed(4) + '%', cls: 'pos' },
    { label: 'Avg Loss', val: data.avg_loss.toFixed(4) + '%', cls: 'neg' },
    { label: 'Profit Factor', val: data.profit_factor === Infinity ? '\u221e' : data.profit_factor.toFixed(2), cls: data.profit_factor >= 1 ? 'pos' : 'neg' },
    { label: 'Sharpe', val: data.sharpe.toFixed(2), cls: data.sharpe >= 1 ? 'pos' : data.sharpe >= 0 ? 'neu' : 'neg' },
    { label: 'Max DD', val: data.max_drawdown.toFixed(2) + '%', cls: 'neg' },
  ];
  grid.innerHTML = cards.map(function (c) { return '<div class="stat-card"><div class="val ' + c.cls + '">' + c.val + '</div><div class="lbl">' + c.label + '</div></div>'; }).join('');
}

var histChart = null;
function renderHistogram(data) {
  var canvas = document.getElementById('histChart');
  var legend = document.getElementById('histLegend');
  if (!data.histogram || !data.histogram.bins.length) { legend.textContent = 'No histogram data'; return; }
  var labels = [];
  for (var i = 0; i < data.histogram.bins.length - 1; i++) {
    labels.push(data.histogram.bins[i].toFixed(2) + '..' + data.histogram.bins[i + 1].toFixed(2));
  }
  if (histChart) histChart.destroy();
  histChart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Forward Returns',
        data: data.histogram.counts,
        backgroundColor: data.histogram.bins.map(function (_, i) { return (data.histogram.bins[i] + data.histogram.bins[i + 1]) / 2 >= 0 ? 'rgba(38,166,154,0.7)' : 'rgba(239,83,80,0.7)'; }),
        borderColor: data.histogram.bins.map(function (_, i) { return (data.histogram.bins[i] + data.histogram.bins[i + 1]) / 2 >= 0 ? '#26a69a' : '#ef5350'; }),
        borderWidth: 1,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { backgroundColor: '#16213e', titleColor: '#e0e0e0', bodyColor: '#e0e0e0', borderColor: '#0f3460', borderWidth: 1 } },
      scales: { x: { ticks: { color: '#888', font: { size: 9 }, maxRotation: 45 }, grid: { color: '#0f3460' } }, y: { ticks: { color: '#888', font: { size: 10 } }, grid: { color: '#0f3460' }, beginAtZero: true } }
    }
  });
  legend.textContent = 'Distribution of forward returns (' + data.forward_count + ' samples)';
  canvas.style.height = '200px';
}

function renderEdgeBrowser(data) {
  var container = document.getElementById('edgeBrowser');
  var returns = data.forward_returns || [];
  if (!returns.length) { container.innerHTML = '<div style="font-size:11px;color:#555">No forward returns</div>'; return; }
  if (_viewMode === 'grid') {
    var html = '<div class="edge-wrap"><table class="edge-table"><thead><tr><th>#</th><th>Return %</th><th>Result</th></tr></thead><tbody>';
    for (var i = 0; i < returns.length; i++) {
      html += '<tr><td>' + (i + 1) + '</td><td class="' + (returns[i] >= 0 ? 'pos' : 'neg') + '">' + returns[i].toFixed(4) + '%</td><td class="' + (returns[i] >= 0 ? 'pos' : 'neg') + '">' + (returns[i] >= 0 ? 'WIN' : 'LOSS') + '</td></tr>';
    }
    html += '</tbody></table></div>';
    container.innerHTML = html;
  } else {
    var html = '<div class="edge-cards">';
    var step = Math.max(1, Math.floor(returns.length / 50));
    for (var i = 0; i < Math.min(returns.length, 200); i += step) {
      var r = returns[i];
      html += '<div class="edge-card"><div class="ec-title">#' + (i + 1) + '</div><div class="ec-row"><span>Return</span><span class="ec-val ' + (r >= 0 ? 'pos' : 'neg') + '">' + r.toFixed(4) + '%</span></div><div class="ec-row"><span>Result</span><span class="ec-val ' + (r >= 0 ? 'pos' : 'neg') + '">' + (r >= 0 ? 'WIN' : 'LOSS') + '</span></div></div>';
    }
    html += '</div>';
    container.innerHTML = html;
  }
}

function renderWalkForward(wf) {
  document.getElementById('wfContent').classList.remove('hidden');
  document.getElementById('wfStatus').textContent = 'Walk-Forward: ' + wf.summary.valid_windows + ' valid windows';
  var summary = wf.summary;
  var degCls = summary.degradation <= 1 ? 'good' : 'bad';
  document.getElementById('wfSummary').innerHTML = 'Avg Train WR: <b>' + summary.avg_train_win_rate + '%</b> &nbsp;|&nbsp; Avg Test WR: <b>' + summary.avg_test_win_rate + '%</b> &nbsp;|&nbsp; Degradation: <span class="wf-degradation ' + degCls + '">' + summary.degradation + '%</span> &nbsp;|&nbsp; Avg Train Sharpe: ' + summary.avg_train_sharpe + ' &nbsp;|&nbsp; Avg Test Sharpe: ' + summary.avg_test_sharpe;
  var html = '<thead><tr><th>Window</th><th>Train Occ</th><th>Train WR</th><th>Train Sharpe</th><th>Train Avg R</th><th>Test Occ</th><th>Test WR</th><th>Test Sharpe</th><th>Test Avg R</th></tr></thead><tbody>';
  for (var wi = 0; wi < wf.windows.length; wi++) {
    var w = wf.windows[wi];
    html += '<tr><td>' + (w.window + 1) + '</td><td>' + w.train.occurrences + '</td><td>' + w.train.win_rate + '%</td><td>' + w.train.sharpe + '</td><td>' + w.train.avg_return + '%</td><td>' + w.test.occurrences + '</td><td>' + w.test.win_rate + '%</td><td>' + w.test.sharpe + '</td><td>' + w.test.avg_return + '%</td></tr>';
  }
  html += '</tbody>';
  document.getElementById('wfTable').innerHTML = html;
}

function renderMonteCarlo(mc) {
  document.getElementById('mcContent').classList.remove('hidden');
  document.getElementById('mcStatus').textContent = 'Monte Carlo (' + mc.shuffles + ' shuffles)';
  var pWr = mc.p_win_rate;
  var pAvg = mc.p_avg_return;
  document.getElementById('mcResult').innerHTML = '<div class="mc-info"><b>Shuffles:</b> ' + mc.shuffles + '<br><b>p(win_rate):</b> ' + (pWr !== null ? pWr.toFixed(4) : 'N/A') + ' &rarr; <span class="sig ' + (pWr !== null && pWr < 0.05 ? 'yes' : 'no') + '">' + (pWr !== null && pWr < 0.05 ? 'SIGNIFICANT' : 'not significant') + '</span><br><b>p(avg_return):</b> ' + (pAvg !== null ? pAvg.toFixed(4) : 'N/A') + ' &rarr; <span class="sig ' + (pAvg !== null && pAvg < 0.05 ? 'yes' : 'no') + '">' + (pAvg !== null && pAvg < 0.05 ? 'SIGNIFICANT' : 'not significant') + '</span></div>';
}

// ── Tabs, View, Export ──
function switchRtab(name) {
  var rTabs = document.querySelectorAll('.rtab');
  for (var ri = 0; ri < rTabs.length; ri++) { rTabs[ri].classList.toggle('active', rTabs[ri].dataset.rtab === name); }
  var rContents = document.querySelectorAll('.rtab-content');
  for (var ri = 0; ri < rContents.length; ri++) { rContents[ri].classList.toggle('active', rContents[ri].id === 'rtab-' + name); }
}

function setView(mode) {
  _viewMode = mode;
  var vtBtns = document.querySelectorAll('.vt-btn[data-view]');
  for (var vi = 0; vi < vtBtns.length; vi++) { vtBtns[vi].classList.toggle('active', vtBtns[vi].dataset.view === mode); }
  if (_lastResult) renderEdgeBrowser(_lastResult);
}

function msToDate(ms) {
  var d = new Date(ms);
  return d.toISOString().slice(0, 10);
}
function dateToMs(dateStr) {
  return new Date(dateStr + 'T00:00:00Z').getTime();
}

function doExport(fmt) {
  var cfg = getSearchConfig();
  if (!cfg || !cfg.groups || !cfg.groups[0] || !cfg.groups[0].conditions.length) return;
  var params = 'exchange=' + cfg.exchange + '&symbol=' + cfg.symbol + '&timeframe=' + cfg.timeframe + '&lookahead=' + cfg.lookahead + '&format=' + fmt;
  var condParams = cfg.groups[0].conditions.map(function (c) { return c.metric + '_' + c.op + '=' + c.value; }).join('&');
  window.open('/api/edge/export?' + params + '&' + condParams, '_blank');
}

// ── Init ──
document.addEventListener('DOMContentLoaded', function () {
  var chatInput = document.getElementById('chatInput');
  if (!chatInput) return console.warn('chatInput not found');

  chatInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendChatMessage();
    }
  });
  chatInput.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 150) + 'px';
  });

  addChatMessage('system', '━━━ How the Strategy Lab works ━━━');
  addChatMessage('system', '1. Fill out the strategy config (header + trade cards) directly');
  addChatMessage('system', '2. Or describe your idea in the chat — OpenCode builds it for you');
  addChatMessage('system', '3. Add conditions, orders, and extra trades as needed');
  addChatMessage('system', '4. Click Run Search to backtest');
  addChatMessage('system', '━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  addChatMessage('ai', 'Ready. The strategy config is pre-filled with defaults — edit any field or describe changes in chat.');
  showDefaultConfig();
  connectWS();
});
</script>
<!-- ── Condition Browser Modal ── -->
<div class="modal-overlay" id="conditionModal">
  <div class="modal-content">
    <div class="modal-header">
      <h3>📊 Indicator Browser</h3>
      <button class="modal-close" onclick="closeConditionBrowser()">&times;</button>
    </div>
    <div class="modal-body">
      <div class="modal-cats" id="modalCats"></div>
      <div class="modal-panel" id="modalPanel">
        <div style="color:#555;font-size:12px;padding:20px;text-align:center">Select a category on the left</div>
      </div>
    </div>
  </div>
</div>

</body>
</html>"""


@router.get("/strategy-lab", response_class=HTMLResponse)
async def strategy_lab_page():
    return LAB_HTML
