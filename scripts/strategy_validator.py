"""
Local strategy response validator — zero LLM calls.
Validates agent responses for well-formed conditions, known metrics, valid values.

Usage:
    from strategy_validator import validate_strategy, VALID_METRICS, VALID_OPS
    errors = validate_strategy(response_dict)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.condition_registry import FLAT_REGISTRY

VALID_METRICS = set()
for e in FLAT_REGISTRY:
    VALID_METRICS.add(e["id"])
    if e["type"] == "indicator" and e.get("subcategory") == "threshold":
        VALID_METRICS.add(f"pctl_{e['id']}")

VALID_METRICS.update(["close", "high", "low", "open", "volume"])
VALID_METRICS.update(["oc", "oh", "ol", "hl", "hc", "lc", "vol"])
VALID_METRICS.update(["pctl_oc", "pctl_oh", "pctl_ol", "pctl_hl", "pctl_hc", "pctl_lc", "pctl_vol"])
# Pre-computed indicator names (not in FLAT_REGISTRY but computed by routes.py)
PRECOMPUTED_INDICATORS = [
    "rsi_14", "sma_10", "sma_20", "sma_50", "sma_200",
    "ema_12", "ema_26",
    "bbands_20_2", "bbands_upper_20_2", "bbands_middle_20_2", "bbands_lower_20_2",
    "bbands_upper_50_2", "bbands_middle_50_2", "bbands_lower_50_2",
    "atr_14",
    "macd_line_12_26_9", "macd_signal_12_26_9", "macd_histogram_12_26_9",
    "stoch_14", "stoch_k_14", "stoch_d_14",
    "vwap", "adx_14", "cci_20", "mfi_14", "williams_r_14", "obv",
    "ichimoku_tenkan_9", "ichimoku_kijun_26", "ichimoku_senkou_a", "ichimoku_senkou_b", "ichimoku_chikou_26",
]
VALID_METRICS.update(PRECOMPUTED_INDICATORS)

INDICATOR_ALIASES = {
    "tenkan": "ichimoku_tenkan_9",
    "kijun": "ichimoku_kijun_26",
    "senkou_a": "ichimoku_senkou_a",
    "senkou_b": "ichimoku_senkou_b",
    "chikou": "ichimoku_chikou_26",
    "sma20": "sma_20",
    "sma50": "sma_50",
    "sma10": "sma_10",
    "sma200": "sma_200",
    "ema12": "ema_12",
    "ema26": "ema_26",
    "rsi14": "rsi_14",
    "atr14": "atr_14",
    "ichimoku_tenkan": "ichimoku_tenkan_9",
    "ichimoku_kijun": "ichimoku_kijun_26",
    "ichimoku_senkou": "ichimoku_senkou_a",
    "ichimoku_chikou": "ichimoku_chikou_26",
    # Descriptive Ichimoku aliases from LLM output
    "ichimoku_lagging_span": "ichimoku_chikou_26",
    "ichimoku_base_line": "ichimoku_kijun_26",
    "ichimoku_leading_span_a": "ichimoku_senkou_a",
    "ichimoku_leading_span_b": "ichimoku_senkou_b",
    "ichimoku_kijun_sen": "ichimoku_kijun_26",
    "ichimoku_tenkan_sen": "ichimoku_tenkan_9",
    "lagging_span": "ichimoku_chikou_26",
    "leading_span_a": "ichimoku_senkou_a",
    "leading_span_b": "ichimoku_senkou_b",
    "base_line": "ichimoku_kijun_26",
    "turning_line": "ichimoku_tenkan_9",
    # Japanese naming variants (LLM training data)
    "tenkan_sen": "ichimoku_tenkan_9",
    "kijun_sen": "ichimoku_kijun_26",
    "senkou_span_a": "ichimoku_senkou_a",
    "senkou_span_b": "ichimoku_senkou_b",
    "senkou_span_a_26": "ichimoku_senkou_a",
    "senkou_span_b_26": "ichimoku_senkou_b",
    "chikou_span": "ichimoku_chikou_26",
    # Dotted variants (LLM retry with prefix)
    "ichimoku.tenkan_sen": "ichimoku_tenkan_9",
    "ichimoku.kijun_sen": "ichimoku_kijun_26",
    "ichimoku.senkou_span_a": "ichimoku_senkou_a",
    "ichimoku.senkou_span_b": "ichimoku_senkou_b",
    "ichimoku.chikou_span": "ichimoku_chikou_26",
    # Additional hallucinated/common LLM variants
    "ichimoku_conversion_line": "ichimoku_tenkan_9",
    "conversion_line": "ichimoku_tenkan_9",
    "ichimoku_a": "ichimoku_senkou_a",
    "ichimoku_b": "ichimoku_senkou_b",
    "ichimoku_leading_a": "ichimoku_senkou_a",
    "ichimoku_leading_b": "ichimoku_senkou_b",
    "cloud_a": "ichimoku_senkou_a",
    "cloud_b": "ichimoku_senkou_b",
    # Close offset aliases (chikou vs close 26 bars ago)
    "close_26_ago": "close",
    "close_26": "close",
    "close_ago_26": "close",
}

VALID_OPS = {"gt", "gte", "lt", "lte", "eq", "neq"}

VALID_SUBCATEGORIES = {"threshold", "pctl"}

EXPECTED_KEYS = {"exchange", "symbol", "timeframe", "direction", "lookahead",
                 "min_occurrences", "leverage", "trades"}


def _resolve_id(mid: str) -> str | None:
    if mid in VALID_METRICS:
        return mid
    if mid in INDICATOR_ALIASES:
        return INDICATOR_ALIASES[mid]
    return None


def validate_strategy(data: dict) -> list[str]:
    errors = []

    if not isinstance(data, dict):
        return ["response is not a dict"]

    rtype = data.get("type")
    if rtype != "config_update":
        errors.append(f"type should be 'config_update', got '{rtype}'")
        return errors

    ready = data.get("ready", False)
    if ready is not True:
        errors.append("ready is not True")

    resp = data.get("response") or data
    if not isinstance(resp, dict):
        errors.append("response field is not a dict")
        return errors

    for key in EXPECTED_KEYS:
        if key not in resp:
            errors.append(f"response missing '{key}'")

    trades = resp.get("trades", {})
    if not isinstance(trades, dict):
        errors.append("trades is not a dict")
        return errors

    sides_found = 0
    for side in ("long", "short"):
        trade_list = trades.get(side, [])
        if not isinstance(trade_list, list):
            errors.append(f"trades.{side} is not a list")
            continue
        if not trade_list:
            continue
        sides_found += 1
        for ti, trade in enumerate(trade_list):
            errors.extend(_validate_trade(trade, side, ti))

    if sides_found == 0:
        errors.append("no trades found (both long and short are empty)")

    return errors


def _validate_trade(trade: dict, side: str, ti: int) -> list[str]:
    errors = []
    for phase in ("open", "close"):
        phase_data = trade.get(phase)
        if not phase_data:
            errors.append(f"{side}[{ti}] missing '{phase}'")
            continue
        if not isinstance(phase_data, dict):
            errors.append(f"{side}[{ti}]/{phase} is not a dict")
            continue
        orders = phase_data.get("orders", [])
        if not orders:
            errors.append(f"{side}[{ti}]/{phase} has no orders")
        conds = phase_data.get("conditions", {})
        if not conds:
            errors.append(f"{side}[{ti}]/{phase} has no conditions")
            continue
        errors.extend(_validate_conditions(conds, f"{side}[{ti}]/{phase}"))
    return errors


def _validate_conditions(conds: dict, label: str) -> list[str]:
    errors = []
    logic = conds.get("logic", "")
    if logic not in ("AND", "OR"):
        errors.append(f"{label}: logic should be AND/OR, got '{logic}'")
    groups = conds.get("groups", [])
    if not groups:
        errors.append(f"{label}: no groups")
        return errors
    if not isinstance(groups, list):
        errors.append(f"{label}: groups is not a list")
        return errors
    for gi, group in enumerate(groups):
        if not isinstance(group, dict):
            errors.append(f"{label}/g{gi}: not a dict")
            continue
        glogic = group.get("logic", "")
        if glogic not in ("AND", "OR"):
            errors.append(f"{label}/g{gi}: logic should be AND/OR, got '{glogic}'")
        cond_list = group.get("conditions", [])
        if not cond_list:
            errors.append(f"{label}/g{gi}: no conditions in group")
            continue
        for ci, cond in enumerate(cond_list):
            errors.extend(_validate_cond(cond, f"{label}/g{gi}/c{ci}"))
    return errors


def _validate_cond(cond: dict, label: str) -> list[str]:
    errors = []
    if not isinstance(cond, dict):
        errors.append(f"{label}: not a dict")
        return errors

    metric = cond.get("metric", "")
    if not metric:
        errors.append(f"{label}: missing 'metric'")
    elif not _resolve_id(metric):
        errors.append(f"{label}: unknown metric '{metric}'")

    op = cond.get("op", "")
    if op not in VALID_OPS:
        errors.append(f"{label}: invalid op '{op}', expected one of {VALID_OPS}")

    subcat = cond.get("subcategory", "")
    if subcat and subcat not in VALID_SUBCATEGORIES:
        errors.append(f"{label}: invalid subcategory '{subcat}'")

    value = cond.get("value")
    if value is None:
        errors.append(f"{label}: missing 'value'")
    elif isinstance(value, str):
        resolved = _resolve_id(value)
        if not resolved:
            errors.append(f"{label}: value is string '{value}' but not a valid metric/indicator")
    elif not isinstance(value, (int, float)):
        errors.append(f"{label}: value has unexpected type {type(value).__name__}")

    return errors


def validate_prompt_response(prompt_name: str, data: dict) -> list[str]:
    errors = validate_strategy(data)
    if not errors:
        resp = data.get("response") or data
        trades = resp.get("trades", {})
        prompt_name_lower = prompt_name.lower()

        if "rsi" in prompt_name_lower:
            metrics_found = _collect_metrics(trades)
            if not any("rsi" in m for m in metrics_found):
                errors.append(f"[{prompt_name}] expected RSI condition but none found")

        if "ichimoku" in prompt_name_lower:
            metrics_found = _collect_metrics(trades)
            if not any("ichimoku" in m for m in metrics_found):
                errors.append(f"[{prompt_name}] expected Ichimoku condition but none found")

    return errors


def _collect_metrics(trades: dict) -> set[str]:
    metrics = set()
    for side in ("long", "short"):
        for t in trades.get(side, []):
            for phase in ("open", "close"):
                conds = t.get(phase, {}).get("conditions", {})
                for g in conds.get("groups", []):
                    for c in g.get("conditions", []):
                        metrics.add(c.get("metric", ""))
                        val = c.get("value", "")
                        if isinstance(val, str):
                            metrics.add(val)
    return metrics


if __name__ == "__main__":
    import json, sys
    data = json.load(sys.stdin)
    errors = validate_strategy(data)
    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("OK")
