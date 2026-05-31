import asyncio
import bisect
import csv
from datetime import datetime
import io
import json
import logging
import math
import os
import random
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Query, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import yaml

from candles.config import settings
from candles.fetcher import fetch_and_store, parse_pairs, parse_timeframes
from candles.storage.db import query_candles, count_candles, get_candle_range, get_available_pairs
from api.vibe_lab import _log_vibe
from api.condition_registry import search_conditions, CONDITION_REGISTRY, FLAT_REGISTRY

logger = logging.getLogger(__name__)
router = APIRouter()

TIMEFRAMES_MS = {
    "1m": 60000, "5m": 300000, "15m": 900000, "30m": 1800000,
    "1H": 3600000, "2H": 7200000, "4H": 14400000, "6H": 21600000,
    "12H": 43200000, "1D": 86400000, "1W": 604800000, "1M": 2592000000,
}
TRAINING_CANDLES_DEFAULT = 5000


async def ensure_candle_pool(
    exchange: str, symbol: str, timeframe: str,
    target_count: int = TRAINING_CANDLES_DEFAULT,
) -> dict:
    now_ms = int(datetime.now().timestamp() * 1000)
    tf_ms = TIMEFRAMES_MS.get(timeframe, 3600000)
    ideal_start = now_ms - target_count * tf_ms

    result = {"ideal_start": ideal_start, "ideal_end": now_ms, "messages": [], "count": 0}

    rng = get_candle_range(exchange=exchange, symbol=symbol, timeframe=timeframe)
    have = rng["count"] if rng else 0

    if have >= target_count:
        result["count"] = have
        return result

    result["messages"].append(
        f"📡 {exchange}:{symbol} {timeframe} — only {have} candles, fetching {target_count} from {_fmt_ts(ideal_start)}"
    )

    fetch_r = await fetch_and_store(
        exchange_name=exchange, symbol=symbol, timeframe=timeframe,
        limit=target_count, start_time=ideal_start,
    )
    if fetch_r.get("status") == "ok":
        result["messages"].append(f"✅ Fetched {fetch_r['count']} new candles")
    else:
        result["messages"].append(f"⚠️ Fetch: {fetch_r.get('status')} — {fetch_r.get('reason', '?')}")

    rng2 = get_candle_range(exchange=exchange, symbol=symbol, timeframe=timeframe)
    actual = rng2["count"] if rng2 else 0
    result["count"] = actual

    if actual < target_count and rng2:
        result["messages"].append(
            f"ℹ️ Only {actual} candles available for {exchange}:{symbol} {timeframe} "
            f"(requested {target_count}). Using maximum range: {_fmt_ts(rng2['min_ts'])} → {_fmt_ts(rng2['max_ts'])}"
        )

    return result


def _fmt_ts(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M")


class IndicatorParam(BaseModel):
    name: str
    params: dict = {}

class IndicatorComputeRequest(BaseModel):
    exchange: str
    symbol: str
    timeframe: str
    indicators: list[IndicatorParam]
    limit: int = 500


class FilterCondition(BaseModel):
    metric: str
    op: str
    value: float | str = 0.0
    params: dict = {}
    output: str = ""


class FilterGroup(BaseModel):
    logic: str = "AND"
    conditions: list[FilterCondition] = []


class EdgeSearchRequest(BaseModel):
    exchange: str
    symbol: str
    timeframe: str
    lookahead: int = 5
    start_time: int | None = None
    end_time: int | None = None
    groups: list[FilterGroup] = []
    logic: str = "AND"
    min_occurrences: int = 5
    walk_forward: bool = False
    walk_windows: int = 5
    walk_train_pct: float = 0.7
    monte_carlo_shuffles: int = 0
    orders: list[dict] = []  # optional order config for state machine simulation
    sub_bar: dict | None = None  # {"enabled": true, "resolution": "1m"}


class SubBarConfig(BaseModel):
    enabled: bool = False
    resolution: str = "1m"


class SweepParam(BaseModel):
    metric: str
    op: str
    values: list[float]


class EdgeSweepRequest(BaseModel):
    exchange: str
    symbol: str
    timeframe: str
    lookahead_values: list[int] = [1, 3, 5, 10]
    min_occurrences: int = 5
    start_time: int | None = None
    end_time: int | None = None
    groups: list[FilterGroup] = []
    logic: str = "AND"
    sweep_params: list[SweepParam] = []


class SuggestRequest(BaseModel):
    field: str
    value: str
    config: dict = {}
    group_context: str = ""


class SuggestResponse(BaseModel):
    suggestions: list[dict] = []
    field: str = ""


class BatchSearchItem(BaseModel):
    label: str
    groups: list[FilterGroup]
    logic: str = "AND"
    lookahead: int = 5


class BatchSearchRequest(BaseModel):
    exchange: str
    symbol: str
    timeframe: str
    start_time: int | None = None
    end_time: int | None = None
    min_occurrences: int = 5
    searches: list[BatchSearchItem] = []


# ── Condition registry endpoints ──

@router.get("/conditions/categories")
async def conditions_categories():
    """Return all condition categories with subcategories."""
    result = []
    for cat_id, cat in CONDITION_REGISTRY.items():
        subs = []
        for sub_id, sub in cat.get("subcategories", {}).items():
            subs.append({
                "id": sub_id,
                "label": sub.get("label"),
                "description": sub.get("description"),
                "has_metrics": "metrics" in sub,
                "has_indicators": "indicators" in sub,
                "count": len(sub.get("metrics", {})) + len(sub.get("indicators", {})),
            })
        result.append({
            "id": cat_id,
            "label": cat["label"],
            "description": cat.get("description"),
            "icon": cat.get("icon", ""),
            "subcategories": subs,
            "count": sum(s["count"] for s in subs),
        })
    return {"categories": result}


@router.get("/conditions/catalog")
async def conditions_catalog():
    """Return the full condition registry hierarchy for the browser modal."""
    return CONDITION_REGISTRY


@router.get("/conditions/search")
async def conditions_search(q: str = "", max_results: int = 10):
    """Search conditions by keyword."""
    if not q:
        return {"results": FLAT_REGISTRY[:max_results], "total": len(FLAT_REGISTRY)}
    results = search_conditions(q, max_results)
    return {"results": results, "total": len(results)}


class InterpretRequest(BaseModel):
    text: str
    group_context: str = ""


class InterpretResponse(BaseModel):
    metric: str
    op: str
    value: float
    params: dict = {}
    output: str = ""
    label: str = ""
    description: str = ""
    fuzzy: bool = False


@router.post("/conditions/interpret")
async def conditions_interpret(req: InterpretRequest):
    """Parse a free-text condition string into a structured FilterCondition.

    Handles patterns like:
      - 'rsi < 30'
      - 'sma(20) > close'
      - 'adx > 25'
      - 'pctl_oc >= 80'
      - 'stoch_k_14 > 80'
    Falls back to AI interpretation if regex parsing fails.
    """
    text = req.text.strip()
    if not text:
        return InterpretResponse(metric="oc", op="gt", value=0.5, label="OC > 0.5%", fuzzy=True)

    # Try regex parsing
    result = _parse_condition_text(text)
    if result:
        return result

    # AI fallback
    result = _ai_interpret_condition(text, req.group_context)
    if result:
        return result

    return InterpretResponse(metric="oc", op="gt", value=0.5, label=text, fuzzy=True)


_CONDITION_RE = re.compile(
    r"^\s*(?P<metric>[a-zA-Z_][a-zA-Z0-9_]*)"       # metric name
    r"(?:\((?P<params>[^)]*)\))?"                     # optional params in parens
    r"\s*(?P<op>>=?|<=?|==?|!=?)\s*"                 # operator
    r"(?P<value>-?\d+\.?\d*)\s*$"                     # numeric value
)


def _parse_condition_text(text: str) -> dict | None:
    m = _CONDITION_RE.match(text)
    if not m:
        return None

    metric = m.group("metric")
    op = m.group("op")
    value = float(m.group("value"))
    params_str = m.group("params")

    # Normalize op
    op_map = {">": "gt", ">=": "gte", "<": "lt", "<=": "lte", "==": "eq", "=": "eq", "!=": "neq"}
    op = op_map.get(op, op)

    # Parse params from parens
    params = {}
    if params_str:
        for part in params_str.split(","):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                k = k.strip()
                try:
                    params[k] = int(v) if "." not in v else float(v)
                except ValueError:
                    params[k] = v.strip()
            else:
                try:
                    params["period"] = int(part) if "." not in part else float(part)
                except ValueError:
                    pass

    # Look up in registry for label
    label = text
    description = ""
    for entry in FLAT_REGISTRY:
        if entry["id"] == metric:
            label = f"{entry['label']} {op} {value}"
            description = entry["description"]
            # Merge default params
            for p in entry.get("params", []):
                pname = p["name"]
                if pname not in params:
                    params[pname] = p.get("default", 14 if pname == "period" else p.get("default", 1))
            break

    return InterpretResponse(metric=metric, op=op, value=value, params=params, label=label, description=description)


def _ai_interpret_condition(text: str, context: str = "") -> dict | None:
    """Fallback: use AI to interpret a condition text."""
    try:
        from api.agent import call_groq
        prompt = (
            "You are a trading condition parser. Given a natural-language condition string, "
            "output ONLY valid JSON with keys: metric, op, value, params.\n"
            f"Available metrics/indicators (use the id field): {[e['id'] for e in FLAT_REGISTRY[:60]]}\n"
            f"Operators: gt, gte, lt, lte, eq, neq\n"
            f"Input: \"{text}\"\n"
            f"Context: {context}\n"
            "Output JSON only: {\"metric\": \"...\", \"op\": \"...\", \"value\": ..., \"params\": {...}}"
        )
        resp = call_groq(prompt, max_tokens=200)
        data = json.loads(resp)
        metric = data.get("metric", "oc")
        op = data.get("op", "gt")
        value = float(data.get("value", 0.5))
        params = data.get("params", {})

        # Look up label
        label = text
        for entry in FLAT_REGISTRY:
            if entry["id"] == metric:
                label = f"{entry['label']} {op} {value}"
                break

        return InterpretResponse(metric=metric, op=op, value=value, params=params, label=label, fuzzy=True)
    except Exception:
        return None

_INDICATOR_FUNCS = None

def _get_indicator_funcs():
    global _INDICATOR_FUNCS
    if _INDICATOR_FUNCS is not None:
        return _INDICATOR_FUNCS
    import vibe_engine as ve
    _INDICATOR_FUNCS = {
        "rsi": {
            "func": lambda h,l,c,v,p: ve.rsi(c, p.get("period", 14)),
            "multi_output": False,
        },
        "sma": {
            "func": lambda h,l,c,v,p: ve.sma(c, p.get("period", 20)),
            "multi_output": False,
        },
        "ema": {
            "func": lambda h,l,c,v,p: ve.ema(c, p.get("period", 20)),
            "multi_output": False,
        },
        "bbands_upper": {
            "func": lambda h,l,c,v,p: ve.bbands(c, p.get("period", 20), p.get("stddev", 2.0))[0],
            "multi_output": False,
        },
        "bbands_middle": {
            "func": lambda h,l,c,v,p: ve.bbands(c, p.get("period", 20), p.get("stddev", 2.0))[1],
            "multi_output": False,
        },
        "bbands_lower": {
            "func": lambda h,l,c,v,p: ve.bbands(c, p.get("period", 20), p.get("stddev", 2.0))[2],
            "multi_output": False,
        },
        "atr": {
            "func": lambda h,l,c,v,p: ve.atr(h, l, c, p.get("period", 14)),
            "multi_output": False,
        },
        "macd_line": {
            "func": lambda h,l,c,v,p: ve.macd(c, p.get("fast", 12), p.get("slow", 26), p.get("signal", 9))[0],
            "multi_output": False,
        },
        "macd_signal": {
            "func": lambda h,l,c,v,p: ve.macd(c, p.get("fast", 12), p.get("slow", 26), p.get("signal", 9))[1],
            "multi_output": False,
        },
        "macd_histogram": {
            "func": lambda h,l,c,v,p: ve.macd(c, p.get("fast", 12), p.get("slow", 26), p.get("signal", 9))[2],
            "multi_output": False,
        },
        "stoch_k": {
            "func": lambda h,l,c,v,p: ve.stochastic(h, l, c, p.get("period", 14))[0],
            "multi_output": False,
        },
        "stoch_d": {
            "func": lambda h,l,c,v,p: ve.stochastic(h, l, c, p.get("period", 14))[1],
            "multi_output": False,
        },
        "vwap": {
            "func": lambda h,l,c,v,p: ve.vwap(h, l, c, v),
            "multi_output": False,
        },
        "williams_r": {
            "func": lambda h,l,c,v,p: ve.williams_r(h, l, c, p.get("period", 14)),
            "multi_output": False,
        },
        "obv": {
            "func": lambda h,l,c,v,p: ve.obv(c, v),
            "multi_output": False,
        },
        "cci": {
            "func": lambda h,l,c,v,p: ve.cci(h, l, c, p.get("period", 20)),
            "multi_output": False,
        },
        "mfi": {
            "func": lambda h,l,c,v,p: ve.mfi(h, l, c, v, p.get("period", 14)),
            "multi_output": False,
        },
        "adx": {
            "func": lambda h,l,c,v,p: ve.adx(h, l, c, p.get("period", 14)),
            "multi_output": False,
        },
    }
    return _INDICATOR_FUNCS


def _compute_indicators(candles):
    import numpy as np
    import vibe_engine as ve
    from api.condition_registry import FLAT_REGISTRY as _REG

    n = len(candles)
    high = np.array([c["h"] for c in candles], dtype=np.float64)
    low = np.array([c["l"] for c in candles], dtype=np.float64)
    close = np.array([c["c"] for c in candles], dtype=np.float64)
    volume = np.array([c["v"] for c in candles], dtype=np.float64)

    ind = {}
    alias = {}
    # Store the raw arrays for on-demand computation later
    ind["__raw__"] = {"high": high, "low": low, "close": close, "volume": volume}

    def _store(key, values, metric):
        ind[key] = _to_list(values, n)
        if metric not in alias:
            alias[metric] = key

    # Pre-compute common periods for each indicator
    _precompute_periods = {
        "rsi": [7, 14, 21],
        "sma": [10, 20, 50, 200],
        "ema": [10, 20, 50],
        "atr": [14, 21],
        "stoch": [7, 14, 21],
        "cci": [14, 20, 30],
        "mfi": [14, 21],
        "williams_r": [7, 14, 21],
    }

    for period in _precompute_periods["rsi"]:
        _store(f"rsi_{period}", ve.rsi(close, period), "rsi")
    for period in _precompute_periods["sma"]:
        _store(f"sma_{period}", ve.sma(close, period), "sma")
    for period in _precompute_periods["ema"]:
        _store(f"ema_{period}", ve.ema(close, period), "ema")
    for period in _precompute_periods["atr"]:
        _store(f"atr_{period}", ve.atr(high, low, close, period), "atr")
    for period in _precompute_periods["stoch"]:
        sk, sd = ve.stochastic(high, low, close, period)
        _store(f"stoch_k_{period}", sk, "stoch_k")
        _store(f"stoch_d_{period}", sd, "stoch_d")
    for period in _precompute_periods["cci"]:
        _store(f"cci_{period}", ve.cci(high, low, close, period), "cci")
    for period in _precompute_periods["mfi"]:
        _store(f"mfi_{period}", ve.mfi(high, low, close, volume, period), "mfi")
    for period in _precompute_periods["williams_r"]:
        _store(f"williams_r_{period}", ve.williams_r(high, low, close, period), "williams_r")

    # Default-period variants (already stored above, but ensure the canonical key exists)
    bb_u, bb_m, bb_l = ve.bbands(close, 20, 2.0)
    _store("bbands_upper_20_2", bb_u, "bbands_upper")
    _store("bbands_middle_20_2", bb_m, "bbands_middle")
    _store("bbands_lower_20_2", bb_l, "bbands_lower")
    # Also pre-compute a second BB period
    bb_u2, bb_m2, bb_l2 = ve.bbands(close, 50, 2.0)
    _store("bbands_upper_50_2", bb_u2, None)
    _store("bbands_middle_50_2", bb_m2, None)
    _store("bbands_lower_50_2", bb_l2, None)

    macd_line, sig_line, hist = ve.macd(close, 12, 26, 9)
    _store("macd_line_12_26_9", macd_line, "macd_line")
    _store("macd_signal_12_26_9", sig_line, "macd_signal")
    _store("macd_histogram_12_26_9", hist, "macd_histogram")
    _store("vwap", ve.vwap(high, low, close, volume), "vwap")
    _store("obv", ve.obv(close, volume), "obv")
    _store("adx_14", ve.adx(high, low, close, 14), "adx")

    alias["di_plus"] = "adx_14"
    alias["di_minus"] = "adx_14"

    # ── Ichimoku Cloud ──
    # Tenkan-sen (9): (rolling_max(high,9) + rolling_min(low,9)) / 2
    # Kijun-sen (26): (rolling_max(high,26) + rolling_min(low,26)) / 2
    # Senkou A: (tenkan + kijun) / 2  (normally shifted +26, kept aligned for backtest)
    # Senkou B (52): (rolling_max(high,52) + rolling_min(low,52)) / 2 (kept aligned)
    # Chikou: close shifted back 26 bars (close[i-26]), NaN for first 26 bars
    def _rolling_max(arr, period):
        out = np.empty_like(arr)
        for i in range(len(arr)):
            out[i] = np.max(arr[max(0, i-period+1):i+1])
        return out
    def _rolling_min(arr, period):
        out = np.empty_like(arr)
        for i in range(len(arr)):
            out[i] = np.min(arr[max(0, i-period+1):i+1])
        return out

    ichi_tenkan = (_rolling_max(high, 9) + _rolling_min(low, 9)) / 2.0
    ichi_kijun = (_rolling_max(high, 26) + _rolling_min(low, 26)) / 2.0
    ichi_senkou_a = (ichi_tenkan + ichi_kijun) / 2.0
    ichi_senkou_b = (_rolling_max(high, 52) + _rolling_min(low, 52)) / 2.0
    # Chikou: close shifted 26 bars back (for "chikou above current kijun" comparisons)
    ichi_chikou = np.roll(close, 26)
    ichi_chikou[:26] = np.nan

    _store("ichimoku_tenkan_9", ichi_tenkan, "ichimoku_tenkan")
    _store("ichimoku_kijun_26", ichi_kijun, "ichimoku_kijun")
    _store("ichimoku_senkou_a", ichi_senkou_a, "ichimoku_senkou_a")
    _store("ichimoku_senkou_b", ichi_senkou_b, "ichimoku_senkou_b")
    _store("ichimoku_chikou_26", ichi_chikou, "ichimoku_chikou")

    alias["tenkan"] = "ichimoku_tenkan_9"
    alias["kijun"] = "ichimoku_kijun_26"
    alias["senkou_a"] = "ichimoku_senkou_a"
    alias["senkou_b"] = "ichimoku_senkou_b"
    alias["chikou"] = "ichimoku_chikou_26"

    # Extended aliases matching strategy_validator INDICATOR_ALIASES
    # Ichimoku variants
    alias["ichimoku_tenkan"] = "ichimoku_tenkan_9"
    alias["ichimoku_kijun"] = "ichimoku_kijun_26"
    alias["ichimoku_senkou"] = "ichimoku_senkou_a"
    alias["ichimoku_chikou"] = "ichimoku_chikou_26"
    alias["ichimoku_lagging_span"] = "ichimoku_chikou_26"
    alias["ichimoku_base_line"] = "ichimoku_kijun_26"
    alias["ichimoku_leading_span_a"] = "ichimoku_senkou_a"
    alias["ichimoku_leading_span_b"] = "ichimoku_senkou_b"
    alias["ichimoku_kijun_sen"] = "ichimoku_kijun_26"
    alias["ichimoku_tenkan_sen"] = "ichimoku_tenkan_9"
    alias["lagging_span"] = "ichimoku_chikou_26"
    alias["leading_span_a"] = "ichimoku_senkou_a"
    alias["leading_span_b"] = "ichimoku_senkou_b"
    alias["base_line"] = "ichimoku_kijun_26"
    alias["turning_line"] = "ichimoku_tenkan_9"
    alias["tenkan_sen"] = "ichimoku_tenkan_9"
    alias["kijun_sen"] = "ichimoku_kijun_26"
    alias["senkou_span_a"] = "ichimoku_senkou_a"
    alias["senkou_span_b"] = "ichimoku_senkou_b"
    alias["senkou_span_a_26"] = "ichimoku_senkou_a"
    alias["senkou_span_b_26"] = "ichimoku_senkou_b"
    alias["chikou_span"] = "ichimoku_chikou_26"
    alias["ichimoku.tenkan_sen"] = "ichimoku_tenkan_9"
    alias["ichimoku.kijun_sen"] = "ichimoku_kijun_26"
    alias["ichimoku.senkou_span_a"] = "ichimoku_senkou_a"
    alias["ichimoku.senkou_span_b"] = "ichimoku_senkou_b"
    alias["ichimoku.chikou_span"] = "ichimoku_chikou_26"
    # Additional hallucinated/common LLM variants
    alias["ichimoku_conversion_line"] = "ichimoku_tenkan_9"
    alias["conversion_line"] = "ichimoku_tenkan_9"
    alias["ichimoku_a"] = "ichimoku_senkou_a"
    alias["ichimoku_b"] = "ichimoku_senkou_b"
    alias["ichimoku_leading_a"] = "ichimoku_senkou_a"
    alias["ichimoku_leading_b"] = "ichimoku_senkou_b"
    alias["cloud_a"] = "ichimoku_senkou_a"
    alias["cloud_b"] = "ichimoku_senkou_b"
    # SMA/EMA numeric aliases
    alias["sma20"] = "sma_20"
    alias["sma50"] = "sma_50"
    alias["sma10"] = "sma_10"
    alias["sma200"] = "sma_200"
    alias["ema12"] = "ema_12"
    alias["ema26"] = "ema_26"
    alias["rsi14"] = "rsi_14"
    alias["atr14"] = "atr_14"
    # Close offset aliases
    alias["close_26_ago"] = "close"
    alias["close_26"] = "close"
    alias["close_ago_26"] = "close"

    ind["__alias__"] = alias
    return ind


def _compute_indicator_on_demand(metric, params, high, low, close, volume, n):
    """Compute a single indicator on demand with the given params."""
    funcs = _get_indicator_funcs()
    if metric not in funcs:
        return None
    import numpy as np
    entry = funcs[metric]
    try:
        result = entry["func"](high, low, close, volume, params)
        return _to_list(result, n)
    except Exception:
        return None


def _to_list(arr, n):
    import numpy as np
    import math
    if hasattr(arr, 'shape'):
        result = arr.tolist()
        # Replace NaN/Inf with None for JSON safety
        if isinstance(result, list):
            for i in range(len(result)):
                if isinstance(result[i], float) and (math.isnan(result[i]) or math.isinf(result[i])):
                    result[i] = None
        return result
    if isinstance(arr, (list, tuple)):
        return [None if isinstance(v, float) and (math.isnan(v) or math.isinf(v)) else v for v in arr]
    return [None if (isinstance(arr, float) and (math.isnan(arr) or math.isinf(arr))) else float(arr)] * n if n else []


def _fetch_and_prepare(exchange, symbol, timeframe, start_time, end_time):
    rows = query_candles(
        exchange=exchange, symbol=symbol, timeframe=timeframe,
        limit=999999, start_time=start_time, end_time=end_time,
    )
    if not rows:
        return None, None, None, None

    candles = []
    for r in rows:
        o, h, l, cl, v = r["open"], r["high"], r["low"], r["close"], r["volume"]
        if r.get("metrics"):
            metrics = json.loads(r["metrics"])
        else:
            metrics = {
                "oc": (cl - o) / o * 100,
                "oh": (h - o) / o * 100,
                "ol": (l - o) / o * 100,
                "hl": (h - l) / o * 100,
                "hc": (h - cl) / o * 100,
                "lc": (l - cl) / o * 100,
            }
        candles.append({
            "t": r["timestamp"],
            "o": o, "h": h, "l": l, "c": cl, "v": v,
            "metrics": metrics,
        })

    max_vol = max(c["v"] for c in candles) or 1
    for c in candles:
        c["metrics"]["vol"] = c["v"] / max_vol * 100

    metric_keys = ["oc", "oh", "ol", "hl", "hc", "lc", "vol"]
    pctls = {}
    for mk in metric_keys:
        vals = sorted(c["metrics"][mk] for c in candles)
        n = len(vals)
        pctls[mk] = [bisect.bisect_left(vals, c["metrics"][mk]) / n * 100 for c in candles]

    indicators = _compute_indicators(candles)

    return candles, pctls, metric_keys, indicators


def _resolve_indicator(cond, indicators):
    """Resolve an indicator condition to a value array. Computes on-demand if needed."""
    if not indicators:
        return None
    alias = indicators.get("__alias__", {})
    key = alias.get(cond.metric) or cond.metric
    if key in indicators:
        return indicators[key]
    # Try building a longer key from params (e.g. rsi_7)
    if cond.params:
        vals = [str(v) for v in cond.params.values()]
        trial = f"{cond.metric}_{'_'.join(vals)}"
        if trial in indicators:
            return indicators[trial]
    # Try on-demand computation
    raw = indicators.get("__raw__")
    if raw is not None:
        n = len(next(iter(raw.values())))
        result = _compute_indicator_on_demand(
            cond.metric, cond.params or {},
            raw["high"], raw["low"], raw["close"], raw["volume"], n,
        )
        if result is not None:
            # Cache for reuse
            cache_key = f"{cond.metric}_{'_'.join(str(v) for v in (cond.params or {}).values())}" if cond.params else cond.metric
            indicators[cache_key] = result
            return result
    return None


def _resolve_value(metric_or_ref, candles, pctls, indicators, i, params=None):
    """Resolve a metric name or indicator reference to a numeric value at index i."""
    c = candles[i]
    raw_price_map = {"open": "o", "high": "h", "low": "l", "close": "c", "volume": "v"}
    if metric_or_ref in raw_price_map:
        return c[raw_price_map[metric_or_ref]]
    if metric_or_ref in c["metrics"]:
        return c["metrics"][metric_or_ref]
    if metric_or_ref.startswith("pctl_") and metric_or_ref[5:] in pctls:
        return pctls[metric_or_ref[5:]][i]
    if indicators:
        arr = indicators.get(metric_or_ref)
        if arr is not None:
            return arr[i]
        alias = indicators.get("__alias__", {})
        key = alias.get(metric_or_ref, metric_or_ref)
        arr = indicators.get(key)
        if arr is not None:
            return arr[i]
        # Try building key from params (e.g. rsi + {period:7} → rsi_7)
        if params:
            vals = [str(v) for v in params.values()]
            trial = f"{metric_or_ref}_{'_'.join(vals)}"
            arr = indicators.get(trial)
            if arr is not None:
                return arr[i]
            trial_key = alias.get(trial, trial)
            arr = indicators.get(trial_key)
            if arr is not None:
                return arr[i]
        # Try on-demand computation
        raw = indicators.get("__raw__")
        if raw is not None:
            n = len(next(iter(raw.values())))
            result = _compute_indicator_on_demand(metric_or_ref, params or {}, raw["high"], raw["low"], raw["close"], raw["volume"], n)
            if result is not None:
                return result[i]
    return None


def _eval_cond(cond, candles, pctls, indicators, i):
    val = _resolve_value(cond.metric, candles, pctls, indicators, i, cond.params)
    if val is None:
        return False
    rhs = cond.value
    if isinstance(rhs, str):
        rhs_val = _resolve_value(rhs, candles, pctls, indicators, i)
        if rhs_val is not None:
            rhs = rhs_val
    if cond.op == "gt":    return val > rhs
    if cond.op == "gte":   return val >= rhs
    if cond.op == "lt":    return val < rhs
    if cond.op == "lte":   return val <= rhs
    if cond.op == "eq":    return abs(val - rhs) < 1e-9
    if cond.op == "neq":   return abs(val - rhs) >= 1e-9
    return False


def _find_matches(candles, pctls, groups, logic, indicators=None):
    match_indices = []
    for i in range(len(candles)):
        if not groups:
            match_indices.append(i)
            continue
        group_results = []
        for g in groups:
            if not g.conditions:
                group_results.append(True)
                continue
            cond_results = [_eval_cond(c, candles, pctls, indicators, i) for c in g.conditions]
            group_results.append(all(cond_results) if g.logic.upper() == "AND" else any(cond_results))
        if logic.upper() == "AND":
            if all(group_results):
                match_indices.append(i)
        else:
            if any(group_results):
                match_indices.append(i)
    return match_indices


def _forward_returns(candles, indices, lookahead):
    la = max(1, lookahead)
    results = []
    for i in indices:
        j = i + la
        if j >= len(candles):
            continue
        ret = (candles[j]["c"] - candles[i]["c"]) / candles[i]["c"] * 100
        results.append({"i": i, "entry_t": candles[i]["t"], "entry": candles[i]["c"],
                        "exit_t": candles[j]["t"], "exit": candles[j]["c"], "ret": ret})
    return results


def _forward_returns_with_state_machine(candles, indices, lookahead, orders, direction):
    """Simulate forward returns using Rust state machine for given order types."""
    import vibe_engine
    closes = [c["c"] for c in candles]
    highs = [c["h"] for c in candles]
    lows = [c["l"] for c in candles]
    opens = [c["o"] for c in candles]
    volumes = [c["v"] for c in candles]
    la = max(1, lookahead)

    results = []
    for i in indices:
        if i + 1 >= len(candles):
            continue
        end_bar = min(i + la, len(candles) - 1)
        # Determine which order to simulate
        ot = orders[0].get("type", "market") if orders else "market"
        if ot in ("market", "limit", "stop_market", "stop_limit", "sl", "tp", "ts"):
            # Simple order: use standard forward return at lookahead
            # (state machine for simple orders = immediate fill, use lookahead exit)
            exit_price = candles[end_bar]["c"]
            entry_price = candles[i]["c"]
            ret = (exit_price - entry_price) / entry_price * 100
            if direction == "short":
                ret = -ret
            results.append({
                "i": i,
                "entry_t": candles[i]["t"],
                "entry": entry_price,
                "exit_t": candles[end_bar]["t"],
                "exit": exit_price,
                "ret": ret,
            })
        else:
            # Custom order: run state machine simulation bounded by lookahead
            state_model = '{"states": ["idle", "executed"], "transitions": [{"from": "idle", "to": "executed", "trigger": "immediate"}]}'
            order_params = "{}"
            try:
                from custom_types.registry import get_order_type_definitions
                defs = get_order_type_definitions()
                for d in defs:
                    if d["id"] == ot:
                        sm = d.get("state_model", {})
                        state_model = json.dumps(sm)
                        order_params = json.dumps(orders[0].get("params", {}))
                        break
            except Exception:
                pass

            # Run SM on full data but limit iteration by slicing to end_bar+1
            slice_end = end_bar + 1
            result = vibe_engine.run_state_machine_order(
                opens[:slice_end], highs[:slice_end], lows[:slice_end],
                closes[:slice_end], volumes[:slice_end],
                "custom",
                state_model,
                order_params,
                i, closes[i]
            )
            if result and len(result) == 6:
                raw_exit_bar = int(result[1])
                exit_bar = raw_exit_bar if raw_exit_bar > i else end_bar
                if exit_bar >= len(candles):
                    exit_bar = len(candles) - 1
                entry_price = result[2]
                exit_price = result[3] if result[3] != entry_price else candles[exit_bar]["c"]
                ret = (exit_price - entry_price) / entry_price * 100
                if direction == "short":
                    ret = -ret
                results.append({
                    "i": i,
                    "entry_t": candles[i]["t"],
                    "entry": entry_price,
                    "exit_t": candles[exit_bar]["t"],
                    "exit": exit_price,
                    "ret": ret,
                })

    return results


def _compute_stats(forward_results, occurrences):
    if not forward_results:
        return {"occurrences": occurrences, "forward_count": 0, "wins": 0, "losses": 0,
                "win_rate": 0, "avg_return": 0, "avg_win": 0, "avg_loss": 0,
                "profit_factor": 0, "sharpe": 0, "max_drawdown": 0, "histogram": {"bins": [], "counts": []},
                "forward_returns": []}

    returns = [r["ret"] for r in forward_results]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    total = len(returns)
    win_rate = len(wins) / total * 100
    avg_return = sum(returns) / total
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 0
    profit_factor = abs(sum(wins) / sum(losses)) if sum(losses) != 0 else (float("inf") if sum(wins) > 0 else 0)

    mean_r = avg_return
    std_r = math.sqrt(sum((r - mean_r) ** 2 for r in returns) / total) if total > 1 else 0
    sharpe = (mean_r / std_r * math.sqrt(252)) if std_r > 0 else 0

    peak = -float("inf")
    max_dd = 0.0
    for r in returns:
        if r > peak:
            peak = r
        dd = peak - r
        if dd > max_dd:
            max_dd = dd

    bins_n = 20
    min_r = min(returns) if returns else 0
    max_r = max(returns) if returns else 0
    bin_w = (max_r - min_r) / bins_n if max_r > min_r else 1
    hist_counts = [0] * bins_n
    for r in returns:
        idx = min(int((r - min_r) / bin_w), bins_n - 1)
        hist_counts[idx] += 1
    hist_edges = [min_r + i * bin_w for i in range(bins_n + 1)]

    return {
        "occurrences": occurrences,
        "forward_count": total,
        "wins": len(wins), "losses": len(losses),
        "win_rate": round(win_rate, 2),
        "avg_return": round(avg_return, 4),
        "avg_win": round(avg_win, 4),
        "avg_loss": round(avg_loss, 4),
        "profit_factor": round(profit_factor, 4) if isinstance(profit_factor, float) else profit_factor,
        "sharpe": round(sharpe, 4),
        "max_drawdown": round(max_dd, 4),
        "histogram": {"bins": hist_edges, "counts": hist_counts},
        "forward_returns": [round(r, 4) for r in returns[:1000]],
    }


def _monte_carlo_pvalue(returns, n_shuffles):
    if len(returns) < 5 or n_shuffles < 1:
        return None, None
    actual_wr = sum(1 for r in returns if r > 0) / len(returns)
    actual_avg = sum(returns) / len(returns)
    count_extreme_wr = 0
    count_extreme_avg = 0
    for _ in range(n_shuffles):
        shuffled = random.sample(returns, len(returns))
        swr = sum(1 for r in shuffled if r > 0) / len(shuffled)
        savg = sum(shuffled) / len(shuffled)
        if swr >= actual_wr:
            count_extreme_wr += 1
        if savg >= actual_avg:
            count_extreme_avg += 1
    return count_extreme_wr / n_shuffles, count_extreme_avg / n_shuffles


def _walk_forward(candles, pctls, groups, logic, lookahead, windows, train_pct, min_occ, indicators=None):
    n = len(candles)
    window_size = n // windows
    results = []
    for w in range(windows):
        train_end = min((w + 1) * window_size, n)
        test_start = train_end - int(window_size * (1 - train_pct)) if w > 0 else train_end
        test_end = min(test_start + int(window_size * (1 - train_pct)), n)

        # Train on the first part of this window
        train_indices = _find_matches(candles[:train_end], pctls, groups, logic, indicators)
        train_fwd = _forward_returns(candles[:train_end], train_indices, lookahead)
        train_stats = _compute_stats(train_fwd, len(train_indices))

        # Test on the OOS part
        if test_start < test_end:
            test_indices = _find_matches(candles[test_start:test_end], pctls, groups, logic, indicators)
            test_fwd = _forward_returns(candles[test_start:test_end], test_indices, lookahead)
            test_stats = _compute_stats(test_fwd, len(test_indices))
        else:
            test_stats = {"win_rate": 0, "sharpe": 0, "occurrences": 0}

        results.append({
            "window": w,
            "train_start": candles[0]["t"] if w == 0 else candles[w * window_size]["t"],
            "train_end": candles[train_end - 1]["t"] if train_end > 0 else 0,
            "test_start": candles[test_start]["t"] if test_start < n else 0,
            "test_end": candles[test_end - 1]["t"] if test_end > 0 and test_end <= n else 0,
            "train": {
                "occurrences": train_stats["occurrences"],
                "win_rate": train_stats["win_rate"],
                "sharpe": train_stats["sharpe"],
                "avg_return": train_stats["avg_return"],
            },
            "test": {
                "occurrences": test_stats["occurrences"],
                "win_rate": test_stats["win_rate"],
                "sharpe": test_stats["sharpe"],
                "avg_return": test_stats["avg_return"],
            },
        })

    # Aggregate
    train_wrs = [r["train"]["win_rate"] for r in results]
    test_wrs = [r["test"]["win_rate"] for r in results]
    valid_windows = sum(1 for r in results if r["test"]["occurrences"] >= min_occ)

    return {
        "windows": results,
        "summary": {
            "valid_windows": valid_windows,
            "avg_train_win_rate": round(sum(train_wrs) / len(train_wrs), 2) if train_wrs else 0,
            "avg_test_win_rate": round(sum(test_wrs) / len(test_wrs), 2) if test_wrs else 0,
            "avg_train_sharpe": round(sum(r["train"]["sharpe"] for r in results) / len(results), 4) if results else 0,
            "avg_test_sharpe": round(sum(r["test"]["sharpe"] for r in results) / len(results), 4) if results else 0,
            "degradation": round((sum(train_wrs) / len(train_wrs) - sum(test_wrs) / len(test_wrs)) if test_wrs else 0, 2),
        },
    }


def _validate_conditions(groups, logic, metric_keys, pctls, indicators=None):
    """Validate all conditions against available metrics/indicators. Returns list of error messages."""
    from api.condition_registry import FLAT_REGISTRY
    valid_ids = {e["id"] for e in FLAT_REGISTRY}
    valid_ids.update(metric_keys)
    valid_ids.update({f"pctl_{k}" for k in metric_keys})
    # Raw price fields that _resolve_value supports
    valid_ids.update(["close", "high", "low", "open", "volume"])
    _funcs = _get_indicator_funcs()

    # Add indicator keys and aliases to valid IDs
    if indicators:
        ind_aliases = indicators.get("__alias__", {})
        valid_ids.update(ind_aliases.keys())
        valid_ids.update(ind_aliases.values())
        for k in indicators:
            if k != "__alias__" and k != "__raw__":
                valid_ids.add(k)

    errors = []
    for gi, group in enumerate(groups):
        for ci, cond in enumerate(group.conditions):
            m = cond.metric
            if m in valid_ids:
                continue
            if m in _funcs:
                continue
            # Check if it could be a pctl variant
            if m.startswith("pctl_") and m[5:] in metric_keys:
                continue
            # Check if it could be an indicator with params
            if cond.params:
                vals = [str(v) for v in cond.params.values()]
                if f"{m}_{'_'.join(vals)}" in valid_ids or f"{m}_{'_'.join(vals)}" in _funcs:
                    continue
            # Check if it's reachable via alias
            if indicators:
                alias = indicators.get("__alias__", {})
                if m in alias or alias.get(m) in indicators:
                    continue
            errors.append(f"Condition #{ci+1} (group {gi+1}): unknown metric '{m}'")
    return errors


def _run_single_search(exchange, symbol, timeframe, start_time, end_time,
                       groups, logic, lookahead, min_occurrences, orders=None):
    candles, pctls, _, indicators = _fetch_and_prepare(exchange, symbol, timeframe, start_time, end_time)
    if candles is None:
        return {"occurrences": 0, "error": "no data"}

    # Validate conditions before running search
    errs = _validate_conditions(groups, logic, ["oc", "oh", "ol", "hl", "hc", "lc", "vol"], pctls or {}, indicators)
    if errs:
        return {
            "occurrences": 0, "error": "; ".join(errs),
            "wins": 0, "losses": 0, "win_rate": 0, "avg_return": 0,
            "avg_win": 0, "avg_loss": 0, "profit_factor": 0, "sharpe": 0,
            "max_drawdown": 0, "forward_returns": [], "histogram": {"bins": [], "counts": []},
        }

    indices = _find_matches(candles, pctls, groups, logic, indicators)
    if len(indices) < min_occurrences:
        return {
            "occurrences": len(indices),
            "error": f"only {len(indices)} matches, need {min_occurrences}",
            "wins": 0, "losses": 0, "win_rate": 0, "avg_return": 0,
            "avg_win": 0, "avg_loss": 0, "profit_factor": 0, "sharpe": 0,
            "max_drawdown": 0, "forward_returns": [], "histogram": {"bins": [], "counts": []},
        }

    # Use state machine simulation if orders are provided
    if orders and len(orders) > 0:
        fwd = _forward_returns_with_state_machine(candles, indices, lookahead, orders, "long")
    else:
        fwd = _forward_returns(candles, indices, lookahead)

    if not fwd:
        return {
            "occurrences": len(indices), "error": "no forward data",
            "wins": 0, "losses": 0, "win_rate": 0, "avg_return": 0,
            "avg_win": 0, "avg_loss": 0, "profit_factor": 0, "sharpe": 0,
            "max_drawdown": 0, "forward_returns": [], "histogram": {"bins": [], "counts": []},
        }

    stats = _compute_stats(fwd, len(indices))
    return stats


# ── Sub-bar resolution helpers ──

def _align_indices_to_sub(main_candles, sub_candles, main_indices):
    """Map main-candle match indices to sub-bar entry indices."""
    if len(main_candles) < 2 or not main_indices:
        return []
    period_ms = main_candles[1]["t"] - main_candles[0]["t"]
    sub_ts = [c["t"] for c in sub_candles]
    pairs = []
    for i in main_indices:
        close_ts = main_candles[i]["t"] + period_ms
        entry = bisect.bisect_left(sub_ts, close_ts)
        if entry < len(sub_candles):
            pairs.append((i, entry))
    return pairs


def _forward_returns_intra_bar(main_candles, sub_candles, aligned_pairs,
                               sub_lookahead, orders, direction):
    """Forward simulation with intra-bar order fills (limit/stop within entry candle)."""
    if len(sub_candles) < 2 or not aligned_pairs:
        return []
    period_ms = main_candles[1]["t"] - main_candles[0]["t"]
    sub_ts = [c["t"] for c in sub_candles]
    results = []

    for main_i, entry_idx in aligned_pairs:
        entry_price = None
        ot = orders[0].get("type", "market") if orders else "market"
        execution = orders[0].get("execution", "close") if orders else "close"

        if execution == "intra" and ot == "limit":
            limit_price = orders[0].get("price", 0)
            main_open_ts = main_candles[main_i]["t"]
            first_in = bisect.bisect_left(sub_ts, main_open_ts)
            last_in = min(bisect.bisect_left(sub_ts, main_open_ts + period_ms) - 1, len(sub_candles) - 1)
            for sj in range(first_in, last_in + 1):
                if direction == "long":
                    if sub_candles[sj]["l"] <= limit_price <= sub_candles[sj]["h"]:
                        entry_price = limit_price
                        break
                else:
                    if sub_candles[sj]["l"] <= limit_price <= sub_candles[sj]["h"]:
                        entry_price = limit_price
                        break

        if entry_price is None:
            entry_price = sub_candles[entry_idx]["c"]

        exit_idx = min(entry_idx + sub_lookahead, len(sub_candles) - 1)
        exit_price = sub_candles[exit_idx]["c"]
        ret = (exit_price - entry_price) / entry_price * 100
        if direction == "short":
            ret = -ret

        results.append({
            "i": main_i,
            "entry_t": sub_candles[entry_idx]["t"],
            "entry": entry_price,
            "exit_t": sub_candles[exit_idx]["t"],
            "exit": exit_price,
            "ret": ret,
        })

    return results


def _run_single_search_sub_bar(exchange, symbol, timeframe, sub_resolution,
                               start_time, end_time, groups, logic,
                               lookahead, min_occurrences, orders=None):
    # Main candles for pattern matching
    candles, pctls, _, indicators = _fetch_and_prepare(
        exchange, symbol, timeframe, start_time, end_time)
    if candles is None:
        return {"occurrences": 0, "error": "no main data"}

    # Sub-bar candles for execution
    sub_candles, _, _, _ = _fetch_and_prepare(
        exchange, symbol, sub_resolution, start_time, end_time)
    if sub_candles is None:
        return {"occurrences": 0, "error": "no sub-bar data"}

    errs = _validate_conditions(
        groups, logic, ["oc", "oh", "ol", "hl", "hc", "lc", "vol"],
        pctls or {}, indicators)
    if errs:
        return {"occurrences": 0, "error": "; ".join(errs),
                "wins": 0, "losses": 0, "win_rate": 0, "avg_return": 0,
                "avg_win": 0, "avg_loss": 0, "profit_factor": 0, "sharpe": 0,
                "max_drawdown": 0, "forward_returns": [], "histogram": {"bins": [], "counts": []}}

    indices = _find_matches(candles, pctls, groups, logic, indicators)
    if len(indices) < min_occurrences:
        return {"occurrences": len(indices),
                "error": f"only {len(indices)} matches, need {min_occurrences}",
                "wins": 0, "losses": 0, "win_rate": 0, "avg_return": 0,
                "avg_win": 0, "avg_loss": 0, "profit_factor": 0, "sharpe": 0,
                "max_drawdown": 0, "forward_returns": [], "histogram": {"bins": [], "counts": []}}

    # Align indices to sub-bar
    aligned = _align_indices_to_sub(candles, sub_candles, indices)
    if not aligned:
        return {"occurrences": len(indices), "error": "no sub-bar alignment",
                "wins": 0, "losses": 0, "win_rate": 0, "avg_return": 0,
                "avg_win": 0, "avg_loss": 0, "profit_factor": 0, "sharpe": 0,
                "max_drawdown": 0, "forward_returns": [], "histogram": {"bins": [], "counts": []}}

    # Convert lookahead: main candles → sub-bar candles
    tf_ms = TIMEFRAMES_MS.get(timeframe, 3600000)
    sub_tf_ms = TIMEFRAMES_MS.get(sub_resolution, 60000)
    ratio = tf_ms // sub_tf_ms
    sub_la = max(1, lookahead * ratio) if lookahead > 0 else len(sub_candles)

    # Run forward simulation
    has_intra = any(o.get("execution") == "intra" for o in (orders or []))
    if orders and len(orders) > 0 and has_intra:
        fwd = _forward_returns_intra_bar(
            candles, sub_candles, aligned, sub_la, orders, "long")
    else:
        sub_indices = [p[1] for p in aligned]
        fwd = _forward_returns(sub_candles, sub_indices, sub_la)

    if not fwd:
        return {"occurrences": len(indices), "error": "no forward data (sub-bar)",
                "wins": 0, "losses": 0, "win_rate": 0, "avg_return": 0,
                "avg_win": 0, "avg_loss": 0, "profit_factor": 0, "sharpe": 0,
                "max_drawdown": 0, "forward_returns": [], "histogram": {"bins": [], "counts": []}}

    stats = _compute_stats(fwd, len(indices))
    return stats


# ── ENDPOINTS ──

class AutoDateRequest(BaseModel):
    exchange: str
    symbol: str
    timeframe: str
    target_count: int = TRAINING_CANDLES_DEFAULT


@router.post("/edge/auto-date")
async def edge_auto_date(req: AutoDateRequest):
    result = await ensure_candle_pool(req.exchange, req.symbol, req.timeframe, req.target_count)
    return result


@router.post("/edge/search")
async def edge_search(req: EdgeSearchRequest):
    # Ensure candle data exists before searching
    pool = await ensure_candle_pool(req.exchange, req.symbol, req.timeframe)
    # If no start_time set, use the ideal start from the data pool
    if req.start_time is None:
        req.start_time = pool["ideal_start"]
    if req.end_time is None:
        req.end_time = pool.get("ideal_end", int(datetime.now().timestamp() * 1000))

    sub_bar = req.sub_bar or {}
    if sub_bar.get("enabled") and sub_bar.get("resolution", "1m") != req.timeframe:
        await ensure_candle_pool(req.exchange, req.symbol, sub_bar.get("resolution", "1m"))
        result = _run_single_search_sub_bar(
            req.exchange, req.symbol, req.timeframe, sub_bar.get("resolution", "1m"),
            req.start_time, req.end_time,
            req.groups, req.logic, req.lookahead, req.min_occurrences,
            orders=req.orders,
        )
        result["sub_bar"] = True
    else:
        result = _run_single_search(
        req.exchange, req.symbol, req.timeframe,
        req.start_time, req.end_time,
        req.groups, req.logic, req.lookahead, req.min_occurrences,
        orders=req.orders,
    )

    # Walk-forward
    if req.walk_forward and result.get("occurrences", 0) >= req.min_occurrences:
        candles, pctls, _, indicators = _fetch_and_prepare(
            req.exchange, req.symbol, req.timeframe, req.start_time, req.end_time)
        if candles:
            wf = _walk_forward(
                candles, pctls, req.groups, req.logic,
                req.lookahead, req.walk_windows, req.walk_train_pct, req.min_occurrences, indicators)
            result["walk_forward"] = wf

    # Monte Carlo
    if req.monte_carlo_shuffles > 0 and result.get("forward_count", 0) > 5:
        returns = _run_single_search(
            req.exchange, req.symbol, req.timeframe,
            req.start_time, req.end_time,
            req.groups, req.logic, req.lookahead, req.min_occurrences,
        ).get("forward_returns", [])
        p_wr, p_avg = _monte_carlo_pvalue(returns, req.monte_carlo_shuffles)
        result["monte_carlo"] = {
            "shuffles": req.monte_carlo_shuffles,
            "p_win_rate": p_wr,
            "p_avg_return": p_avg,
        }

    return result


@router.post("/edge/batch-search")
async def edge_batch_search(req: BatchSearchRequest):
    results = []
    for item in req.searches:
        r = _run_single_search(
            req.exchange, req.symbol, req.timeframe,
            req.start_time, req.end_time,
            item.groups, item.logic, item.lookahead, req.min_occurrences,
        )
        r["label"] = item.label
        results.append(r)
    return {"results": results}


@router.post("/edge/sweep")
async def edge_sweep(req: EdgeSweepRequest):
    candles, pctls, _, indicators = _fetch_and_prepare(
        req.exchange, req.symbol, req.timeframe, req.start_time, req.end_time)
    if candles is None:
        return {"error": "no data", "results": []}

    # Generate all param combinations
    sweep_params = []
    for sp in req.sweep_params:
        for v in sp.values:
            sweep_params.append({"metric": sp.metric, "op": sp.op, "value": v})

    lookaheads = [max(1, la) for la in req.lookahead_values]
    results = []
    total_combs = len(sweep_params) * len(lookaheads)

    for sp in sweep_params:
        test_groups = [FilterGroup(logic="AND", conditions=[
            FilterCondition(metric=sp["metric"], op=sp["op"], value=sp["value"])
        ])] if not req.groups else [
            FilterGroup(logic="AND", conditions=list(req.groups[0].conditions) + [
                FilterCondition(metric=sp["metric"], op=sp["op"], value=sp["value"])
            ])
        ]

        for la in lookaheads:
            indices = _find_matches(candles, pctls, test_groups, req.logic, indicators)
            if len(indices) < req.min_occurrences:
                continue
            fwd = _forward_returns(candles, indices, la)
            if not fwd:
                continue
            stats = _compute_stats(fwd, len(indices))
            stats["sweep_metric"] = sp["metric"]
            stats["sweep_op"] = sp["op"]
            stats["sweep_value"] = sp["value"]
            stats["sweep_lookahead"] = la
            results.append(stats)

    results.sort(key=lambda x: x.get("sharpe", 0), reverse=True)
    return {"total_combinations": total_combs, "results_count": len(results), "results": results}


@router.get("/edge/export")
async def edge_export(
    exchange: str, symbol: str, timeframe: str,
    lookahead: int = 5, format: str = "yaml",
    oc_gt: float | None = None, oc_lt: float | None = None,
    hl_gt: float | None = None,
):
    # Build filter from query params
    conditions = []
    if oc_gt is not None:
        conditions.append(FilterCondition(metric="oc", op="gt", value=oc_gt))
    if oc_lt is not None:
        conditions.append(FilterCondition(metric="oc", op="lt", value=oc_lt))
    if hl_gt is not None:
        conditions.append(FilterCondition(metric="hl", op="gt", value=hl_gt))

    if not conditions:
        return {"error": "no conditions"}

    groups = [FilterGroup(logic="AND", conditions=conditions)]
    result = _run_single_search(
        exchange, symbol, timeframe, None, None,
        groups, "AND", lookahead, 1,
    )

    if result.get("error"):
        return {"error": result["error"]}

    edge_data = {
        "edge": {
            "name": f"{symbol}-{timeframe}-edge",
            "generated": __import__("datetime").datetime.now().isoformat(),
            "data": {"exchange": exchange, "symbol": symbol, "timeframe": timeframe},
            "conditions": {
                "logic": "AND",
                "groups": [{
                    "logic": "AND",
                    "conditions": [{"metric": c.metric, "op": c.op, "value": c.value} for c in conditions],
                }],
                "lookahead": lookahead,
            },
            "stats": {
                "occurrences": result["occurrences"],
                "forward_count": result["forward_count"],
                "win_rate": result["win_rate"],
                "sharpe": result["sharpe"],
                "profit_factor": result["profit_factor"],
                "avg_return": result["avg_return"],
                "max_drawdown": result["max_drawdown"],
            },
        }
    }

    if format == "yaml":
        text = yaml.dump(edge_data, default_flow_style=False)
        return Response(content=text, media_type="text/yaml",
                        headers={"Content-Disposition": f"attachment; filename={symbol}-{timeframe}-edge.yaml"})
    elif format == "json":
        return Response(content=json.dumps(edge_data, indent=2), media_type="application/json",
                        headers={"Content-Disposition": f"attachment; filename={symbol}-{timeframe}-edge.json"})
    elif format == "csv":
        # Re-run to get full forward detail
        candles, pctls, _, indicators = _fetch_and_prepare(exchange, symbol, timeframe, None, None)
        if candles:
            indices = _find_matches(candles, pctls, groups, "AND", indicators)
            fwd = _forward_returns(candles, indices, lookahead)
            output = io.StringIO()
            w = csv.writer(output)
            w.writerow(["entry_timestamp", "entry_price", "exit_price", "forward_return_pct", "result"])
            for r in fwd[:10000]:
                w.writerow([r["entry_t"], r["entry"], r["exit"], round(r["ret"], 4), "WIN" if r["ret"] > 0 else "LOSS"])
            return Response(content=output.getvalue(), media_type="text/csv",
                            headers={"Content-Disposition": f"attachment; filename={symbol}-{timeframe}-returns.csv"})
        return {"error": "no data"}
    return edge_data


@router.post("/edge/suggest", response_model=SuggestResponse)
async def edge_suggest(req: SuggestRequest):
    """AI-powered suggestion for a single field value."""
    suggestions = []

    # For numeric fields, suggest nearby values
    if req.field in ("cfgLookahead", "cfgMinOcc", "cfgMCShuffles", "cfgWFWindows", "cfgWFTrainPct", "cfgLeverage"):
        try:
            v = float(req.value) if req.value else 0
            suggestions = [
                {"label": f"↕ {v * 0.5:.1f} (half)", "value": str(v * 0.5)},
                {"label": f"↕ {v * 2:.1f} (double)", "value": str(v * 2)},
                {"label": f"→ {v:.1f} (keep)", "value": str(v)},
            ]
        except (ValueError, TypeError):
            pass

    # For condition text, use the interpret endpoint
    elif req.field.startswith("cond"):
        try:
            from api.condition_registry import FLAT_REGISTRY
            # Try to interpret and suggest alternatives
            for entry in FLAT_REGISTRY[:5]:
                if entry.get("presets"):
                    for p in entry["presets"][:3]:
                        suggestions.append({
                            "label": f"{entry['label']}: {p['label']}",
                            "value": f"{entry['id']} {p['op']} {p['value']}",
                        })
                elif entry.get("default_op") and entry.get("default_value") is not None:
                    suggestions.append({
                        "label": f"{entry['label']} {entry['default_op']} {entry['default_value']}",
                        "value": f"{entry['id']} {entry['default_op']} {entry['default_value']}",
                    })
        except Exception:
            pass
        if not suggestions:
            suggestions = [
                {"label": "OC% > 0.5%", "value": "oc gt 0.5"},
                {"label": "RSI Oversold (< 30)", "value": "rsi lt 30"},
                {"label": "ADX Strong trend (> 25)", "value": "adx gt 25"},
            ]

    # For dates, suggest recent ranges
    elif req.field in ("cfgStartDate", "cfgEndDate"):
        from datetime import datetime, timedelta
        today = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if "Start" in req.field:
            suggestions = [
                {"label": f"Last week ({week_ago})", "value": week_ago},
                {"label": f"Last month ({month_ago})", "value": month_ago},
                {"label": "Clear (all data)", "value": ""},
            ]
        else:
            suggestions = [
                {"label": f"Today ({today})", "value": today},
                {"label": "Clear (latest)", "value": ""},
            ]

    # For name field, suggest naming conventions
    elif req.field == "cfgName":
        suggestions = [
            {"label": "SMA Crossover + RSI", "value": "SMA Crossover + RSI"},
            {"label": "BB Mean Reversion", "value": "BB Mean Reversion"},
            {"label": "ADX Trend Following", "value": "ADX Trend Following"},
            {"label": "MACD Momentum", "value": "MACD Momentum"},
        ]

    return SuggestResponse(suggestions=suggestions[:6], field=req.field)


@router.get("/candles")
async def get_candles(
    exchange: str | None = None,
    symbol: str | None = None,
    timeframe: str | None = None,
    limit: int = Query(default=100),
    since: int | None = None,
    start_time: int | None = None,
    end_time: int | None = None,
):
    if limit < 1 or limit > 99999:
        limit = 99999
    rows = query_candles(
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        since=since,
        start_time=start_time,
        end_time=end_time,
    )
    return {"count": len(rows), "candles": rows}


@router.get("/candles/count")
async def get_candle_count(
    exchange: str | None = None,
    symbol: str | None = None,
    timeframe: str | None = None,
    start_time: int | None = None,
    end_time: int | None = None,
):
    cnt = count_candles(
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        start_time=start_time,
        end_time=end_time,
    )
    return {"count": cnt}


@router.get("/pairs")
async def list_pairs():
    return {"pairs": get_available_pairs()}


@router.get("/events")
async def candle_events(
    exchange: str,
    symbol: str,
    timeframe: str,
    since: int | None = None,
):
    async def event_stream():
        last_ts = since or 0
        while True:
            try:
                rows = query_candles(
                    exchange=exchange,
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=100,
                    since=last_ts + 1,
                )
                if rows:
                    last_ts = rows[-1]["timestamp"]
                    yield f"data: {json.dumps({'count': len(rows), 'candles': rows})}\n\n"
            except Exception:
                pass
            await asyncio.sleep(5)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/fetch")
async def api_fetch(
    exchange: str,
    symbol: str,
    timeframe: str,
    limit: int = Query(default=5000),
    start_time: int | None = None,
    end_time: int | None = None,
):
    result = await fetch_and_store(
        exchange_name=exchange,
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        start_time=start_time,
        end_time=end_time,
    )
    return result


# ── Strategy Chat Bridge (WebSocket + HTTP fallback) ──

CHAT_LOG_FILE = "/tmp/strategy_chat_log.md"


def _log_to_chat(role: str, content: str, detail: str = ""):
    """Append a message to the persistent chat log."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    extra = f" ({detail})" if detail else ""
    with open(CHAT_LOG_FILE, "a") as f:
        f.write(f"\n## {ts} — {role}{extra}\n{content}\n")


async def _poll_and_send(ws: WebSocket, res_path: str, req_id: str):
    """Poll for a response file and send it over WebSocket."""
    status_sent = False
    for i in range(60):
        await asyncio.sleep(1)
        try:
            if os.path.exists(res_path):
                with open(res_path) as f:
                    data = json.load(f)
                os.remove(res_path)
                data.setdefault("_original_type", data.get("type", "message"))
                await ws.send_json({"id": req_id, **data, "type": "response"})
                _log_to_chat("→ Browser", json.dumps(data)[:300], detail=f"delivered_{req_id[:8]}")
                return
        except Exception:
            pass
        if not status_sent and i >= 5:
            status_sent = True
            try:
                await ws.send_json({"type": "status", "id": req_id, "content": "⏳ L'IA réfléchit toujours... Les stratégies complexes avec Ichimoku ou plusieurs conditions peuvent prendre 30-60s."})
            except Exception:
                pass
    try:
        await ws.send_json({
            "type": "timeout", "id": req_id,
            "content": "⏰ L'IA n'a pas répondu après 60s. Causes possibles :\n• Limite de tokens Groq dépassée — réessaie avec une description plus courte\n• Problème réseau — vérifie ta connexion\n• L'agent agent.py n'est pas en marche — vérifie avec `screen -ls`"
        })
    except Exception:
        pass


# ── Vibe Lab chat (code-generation agent) ──


async def _vibe_poll_and_send(ws: WebSocket, res_path: str, req_id: str):
    status_sent = False
    for i in range(60):
        await asyncio.sleep(1)
        try:
            if os.path.exists(res_path):
                with open(res_path) as f:
                    data = json.load(f)
                os.remove(res_path)
                data.setdefault("_original_type", data.get("type", "message"))
                await ws.send_json({"id": req_id, **data, "type": "response"})
                _log_vibe("→ Browser", json.dumps(data)[:300], detail=f"delivered_{req_id[:8]}")
                return
        except Exception:
            pass
        if not status_sent and i >= 5:
            status_sent = True
            try:
                await ws.send_json({"type": "status", "id": req_id, "content": "⏳ L'IA génère la stratégie... Les stratégies complexes peuvent prendre 30-60s."})
            except Exception:
                pass
    try:
        await ws.send_json({
            "type": "timeout", "id": req_id,
            "content": "⏰ L'IA n'a pas répondu après 60s. Causes possibles :\n• Limite de tokens Groq dépassée — réessaie avec une description plus courte\n• L'agent vibe-agent n'est pas en marche — vérifie avec `screen -ls`\n• Problème réseau — vérifie ta connexion"
        })
    except Exception:
        pass


@router.websocket("/ws/vibe-chat")
async def vibe_chat_ws(ws: WebSocket):
    await ws.accept()
    active_poll = None
    try:
        while True:
            raw = await ws.receive_json()
            msg_type = raw.get("type", "message")
            if msg_type not in ("message", "code_generation"):
                continue

            if active_poll and not active_poll.done():
                active_poll.cancel()

            req_id = str(uuid.uuid4())
            content = raw.get("content", "")
            req_data = {
                "id": req_id, "type": msg_type, "content": content,
                "exchange": raw.get("exchange", "binance"),
                "symbol": raw.get("symbol", "BTCUSDC"),
                "timeframe": raw.get("timeframe", "1H"),
                "timestamp": asyncio.get_event_loop().time(),
            }

            req_path = f"/tmp/vibe_chat_req_{req_id}.json"
            res_path = f"/tmp/vibe_chat_res_{req_id}.json"

            with open(req_path, "w") as f:
                json.dump(req_data, f)

            _log_vibe("User", content, detail=f"req_{req_id[:8]}")
            await ws.send_json({"type": "ack", "id": req_id})

            active_poll = asyncio.create_task(_vibe_poll_and_send(ws, res_path, req_id))
    except WebSocketDisconnect:
        if active_poll and not active_poll.done():
            active_poll.cancel()
    except Exception:
        if active_poll and not active_poll.done():
            active_poll.cancel()
        raise


@router.websocket("/ws/strategy-chat")
async def strategy_chat_ws(ws: WebSocket):
    await ws.accept()
    active_poll = None
    try:
        while True:
            raw = await ws.receive_json()
            msg_type = raw.get("type", "message")
            if msg_type not in ("message", "deep_thinking", "amelioration"):
                continue

            if active_poll and not active_poll.done():
                active_poll.cancel()

            req_id = str(uuid.uuid4())
            content = raw.get("content", "")
            req_data = {"id": req_id, "type": msg_type, "content": content, "timestamp": asyncio.get_event_loop().time()}
            if msg_type in ("deep_thinking", "amelioration"):
                req_data["config"] = raw.get("config", {})
                if msg_type == "amelioration":
                    req_data["results"] = raw.get("results", {})

            req_path = f"/tmp/strategy_chat_req_{req_id}.json"
            res_path = f"/tmp/strategy_chat_res_{req_id}.json"

            with open(req_path, "w") as f:
                json.dump(req_data, f)

            _log_to_chat("User", content, detail=f"req_{req_id[:8]}")
            await ws.send_json({"type": "ack", "id": req_id})

            active_poll = asyncio.create_task(_poll_and_send(ws, res_path, req_id))
    except WebSocketDisconnect:
        if active_poll and not active_poll.done():
            active_poll.cancel()
    except Exception:
        if active_poll and not active_poll.done():
            active_poll.cancel()
        raise


class ChatRequest(BaseModel):
    content: str


class ChatResponse(BaseModel):
    id: str


@router.post("/edge/chat")
async def strategy_chat_post(req: ChatRequest):
    """HTTP fallback: submit a chat message. Poll GET /api/edge/chat/{id} for response."""
    req_id = str(uuid.uuid4())
    req_path = f"/tmp/strategy_chat_req_{req_id}.json"
    with open(req_path, "w") as f:
        json.dump({"id": req_id, "content": req.content, "timestamp": asyncio.get_event_loop().time()}, f)
    _log_to_chat("User", req.content, detail=f"http_req_{req_id[:8]}")
    return {"id": req_id}


@router.get("/edge/chat/{req_id}")
async def strategy_chat_poll(req_id: str):
    """HTTP fallback: poll for a response by ID."""
    res_path = f"/tmp/strategy_chat_res_{req_id}.json"
    if os.path.exists(res_path):
        with open(res_path) as f:
            data = json.load(f)
        os.remove(res_path)
        return {"status": "ready", "data": data}
    return {"status": "pending"}


class ChatRespondRequest(BaseModel):
    """JSON body for complex responses (config_update with strategy data)."""
    req_id: str
    type: str = "message"
    content: str = ""
    response: dict | None = None


@router.post("/edge/chat/respond")
async def strategy_chat_respond(
    body: ChatRespondRequest | None = None,
    req_id: str | None = Query(None),
    type: str | None = Query(None),
    content: str | None = Query(None),
):
    """HTTP endpoint for OpenCode to write a response.
    
    Simple messages: curl via query params:
      curl -X POST '/api/edge/chat/respond?req_id=...&content=hello'
    
    Complex configs: curl with JSON body:
      curl -X POST /api/edge/chat/respond \\
        -H 'Content-Type: application/json' \\
        -d '{"req_id":"...","type":"config_update","response":{...}}'
    """
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
    
    res_path = f"/tmp/strategy_chat_res_{rid}.json"
    with open(res_path, "w") as f:
        json.dump(payload, f)
    log_content = payload.get("response", payload.get("content", ""))
    if isinstance(log_content, dict):
        log_content = json.dumps(log_content, indent=2)[:500]
    _log_to_chat("OpenCode", str(log_content), detail=f"res_{rid[:8]}")
    return {"status": "ok", "id": rid}


class IndicatorSeriesRequest(BaseModel):
    exchange: str
    symbol: str
    timeframe: str
    indicators: list[IndicatorParam]
    limit: int = 0


@router.post("/indicators/compute")
async def compute_indicators(req: IndicatorSeriesRequest):
    """Compute indicators for chart overlay."""
    import numpy as np
    import vibe_engine as ve

    result = {"candles": [], "indicators": {}}
    try:
        pairs = get_available_pairs()
        var_limit = req.limit if req.limit > 0 else 5000
        candles = query_candles(req.exchange, req.symbol, req.timeframe, limit=var_limit, desc=True)
        if not candles:
            return result

        candles.reverse()
        result["candles"] = [{
            "t": c["timestamp"], "o": c["open"], "h": c["high"],
            "l": c["low"], "c": c["close"], "v": c["volume"]
        } for c in candles]

        n = len(candles)
        high = np.array([c["high"] for c in candles], dtype=np.float64)
        low = np.array([c["low"] for c in candles], dtype=np.float64)
        close = np.array([c["close"] for c in candles], dtype=np.float64)
        volume = np.array([c["volume"] for c in candles], dtype=np.float64)
        times = [c["timestamp"] for c in candles]

        funcs = _get_indicator_funcs()
        for ind in req.indicators:
            name = ind.name
            params = ind.params
            values = None

            if name in funcs:
                try:
                    raw = funcs[name]["func"](high, low, close, volume, params)
                    values = _to_list(raw, n)
                except Exception as e:
                    result["indicators"][name] = {"error": str(e)}
                    continue
            elif name in ("bbands",):
                try:
                    period = int(params.get("period", 20))
                    stddev = float(params.get("stddev", 2.0))
                    u, m, l = ve.bbands(close, period, stddev)
                    result["indicators"][f"{name}_upper"] = {
                        "values": _to_list(u, n),
                        "label": f"BB Upper ({period},{stddev})",
                        "pane": 0, "style": "line", "color": params.get("color", "#e94560"),
                    }
                    result["indicators"][f"{name}_middle"] = {
                        "values": _to_list(m, n),
                        "label": f"BB Middle ({period},{stddev})",
                        "pane": 0, "style": "line", "color": params.get("color", "#e94560"),
                    }
                    result["indicators"][f"{name}_lower"] = {
                        "values": _to_list(l, n),
                        "label": f"BB Lower ({period},{stddev})",
                        "pane": 0, "style": "line", "color": params.get("color", "#e94560"),
                    }
                    continue
                except Exception as e:
                    result["indicators"][name] = {"error": str(e)}
                    continue
            elif name in ("macd",):
                try:
                    fast = int(params.get("fast", 12))
                    slow = int(params.get("slow", 26))
                    signal = int(params.get("signal", 9))
                    ml, sl, hi = ve.macd(close, fast, slow, signal)
                    result["indicators"][f"{name}_line"] = {
                        "values": _to_list(ml, n),
                        "label": f"MACD ({fast},{slow},{signal})",
                        "pane": 1, "style": "line", "color": params.get("color", "#26a69a"),
                    }
                    result["indicators"][f"{name}_signal"] = {
                        "values": _to_list(sl, n),
                        "label": "Signal",
                        "pane": 1, "style": "line", "color": params.get("color", "#e94560"),
                    }
                    result["indicators"][f"{name}_histogram"] = {
                        "values": _to_list(hi, n),
                        "label": "Histogram",
                        "pane": 1, "style": "histogram", "color": params.get("color", "#7b1fa2"),
                    }
                    continue
                except Exception as e:
                    result["indicators"][name] = {"error": str(e)}
                    continue
            elif name in ("stoch",):
                try:
                    period = int(params.get("period", 14))
                    k, d = ve.stochastic(high, low, close, period)
                    result["indicators"][f"{name}_k"] = {
                        "values": _to_list(k, n),
                        "label": f"%K ({period})",
                        "pane": 1, "style": "line", "color": params.get("color", "#26a69a"),
                    }
                    result["indicators"][f"{name}_d"] = {
                        "values": _to_list(d, n),
                        "label": f"%D ({period})",
                        "pane": 1, "style": "line", "color": params.get("color", "#e94560"),
                    }
                    continue
                except Exception as e:
                    result["indicators"][name] = {"error": str(e)}
                    continue
            elif name in ("adx",):
                try:
                    period = int(params.get("period", 14))
                    a = ve.adx(high, low, close, period)
                    result["indicators"][name] = {
                        "values": _to_list(a, n),
                        "label": f"ADX ({period})",
                        "pane": 1, "style": "line", "color": params.get("color", "#f9a825"),
                    }
                    continue
                except Exception as e:
                    result["indicators"][name] = {"error": str(e)}
                    continue
            elif name in ("ichimoku",):
                try:
                    tenkan_p = int(params.get("tenkan", 9))
                    kijun_p = int(params.get("kijun", 26))
                    senkou_p = int(params.get("senkou", 52))

                    def _rolling_max(arr, period):
                        out = np.empty_like(arr)
                        for i in range(len(arr)):
                            out[i] = np.max(arr[max(0, i - period + 1):i + 1])
                        return out

                    def _rolling_min(arr, period):
                        out = np.empty_like(arr)
                        for i in range(len(arr)):
                            out[i] = np.min(arr[max(0, i - period + 1):i + 1])
                        return out

                    tenkan = (_rolling_max(high, tenkan_p) + _rolling_min(low, tenkan_p)) / 2.0
                    kijun = (_rolling_max(high, kijun_p) + _rolling_min(low, kijun_p)) / 2.0
                    senkou_a = (tenkan + kijun) / 2.0
                    senkou_b = (_rolling_max(high, senkou_p) + _rolling_min(low, senkou_p)) / 2.0
                    chikou = close.copy()

                    result["indicators"]["ichimoku_tenkan"] = {
                        "values": _to_list(tenkan, n),
                        "label": f"Tenkan ({tenkan_p})",
                        "pane": 0, "style": "line", "color": params.get("color", "#e94560"),
                        "shift": 0,
                    }
                    result["indicators"]["ichimoku_kijun"] = {
                        "values": _to_list(kijun, n),
                        "label": f"Kijun ({kijun_p})",
                        "pane": 0, "style": "line", "color": params.get("color", "#26a69a"),
                        "shift": 0,
                    }
                    result["indicators"]["ichimoku_senkou_a"] = {
                        "values": _to_list(senkou_a, n),
                        "label": f"Senkou A ({tenkan_p},{kijun_p})",
                        "pane": 0, "style": "line", "color": params.get("color", "#42a5f5"),
                        "shift": kijun_p,
                    }
                    result["indicators"]["ichimoku_senkou_b"] = {
                        "values": _to_list(senkou_b, n),
                        "label": f"Senkou B ({senkou_p})",
                        "pane": 0, "style": "line", "color": params.get("color", "#ef5350"),
                        "shift": kijun_p,
                    }
                    result["indicators"]["ichimoku_chikou"] = {
                        "values": _to_list(chikou, n),
                        "label": f"Chikou ({kijun_p})",
                        "pane": 0, "style": "line", "color": params.get("color", "#ab47bc"),
                        "shift": -kijun_p,
                    }
                    result["indicator_groups"] = result.get("indicator_groups", {})
                    result["indicator_groups"]["ichimoku"] = {
                        "label": "Ichimoku Cloud",
                        "members": ["ichimoku_tenkan", "ichimoku_kijun", "ichimoku_senkou_a", "ichimoku_senkou_b", "ichimoku_chikou"],
                        "cloud": {"top": "ichimoku_senkou_a", "bottom": "ichimoku_senkou_b"},
                    }
                    result["indicator_groups"] = result.get("indicator_groups", {})
                    result["indicator_groups"]["bbands"] = {
                        "label": "Bollinger Bands",
                        "members": ["bbands_upper", "bbands_middle", "bbands_lower"],
                        "cloud": {"top": "bbands_upper", "bottom": "bbands_lower"},
                    }
                    continue
                except Exception as e:
                    result["indicators"][name] = {"error": str(e)}
                    continue

            if values is not None:
                label = params.get("label", name.upper())
                pane = 1 if name in ("rsi", "cci", "mfi", "williams_r", "atr", "obv") else 0
                if name in ("sma", "ema"):
                    pane = 0
                result["indicators"][name] = {
                    "values": values,
                    "label": f"{label} ({params.get('period', 14)})" if "period" in params else label,
                    "pane": pane,
                    "style": "line",
                    "color": params.get("color", "#26a69a"),
                }

        return result
    except Exception as e:
        return {"error": str(e)}
