"""
Local strategy response fixer — zero LLM calls.
Applies automatic corrections to common errors found by strategy_validator.

Usage:
    from strategy_fixer import fix_errors
    fixed, remaining = fix_errors(response_dict, errors)
"""

import copy
import sys
import os

_SCRIPTS_DIR = os.path.dirname(__file__)
_PROJECT_ROOT = os.path.join(_SCRIPTS_DIR, "..")
for p in [_PROJECT_ROOT, _SCRIPTS_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from scripts.strategy_validator import INDICATOR_ALIASES, VALID_OPS
except ImportError:
    from strategy_validator import INDICATOR_ALIASES, VALID_OPS


DEFAULT_CLOSE_CONDITIONS = {
    "logic": "AND",
    "groups": [{
        "logic": "AND",
        "conditions": [{
            "subcategory": "threshold",
            "metric": "oc",
            "op": "gte",
            "value": 1.5
        }]
    }]
}

DEFAULT_OPEN_CONDITIONS = {
    "logic": "AND",
    "groups": [{
        "logic": "AND",
        "conditions": [{
            "subcategory": "threshold",
            "metric": "oc",
            "op": "gt",
            "value": 0.2
        }]
    }]
}


def fix_errors(data: dict, errors: list[str]) -> tuple[dict, list[str]]:
    d = copy.deepcopy(data)
    remaining = []

    for err in errors:
        fixed = False

        if "type should be 'config_update'" in err:
            fixed = _fix_type_to_config_update(d)

        if "unknown metric" in err:
            fixed = _fix_unknown_metric(d, err)

        if "value is string" in err or "not a valid metric/indicator" in err:
            fixed = _fix_value_string(d, err) or fixed

        if "missing 'close'" in err or "missing 'open'" in err:
            fixed = _fix_missing_phase(d, err)

        if "no conditions in group" in err or "no groups" in err:
            fixed = _fix_empty_groups(d, err)

        if "has no orders" in err or "has no conditions" in err:
            fixed = _fix_missing_orders_or_conditions(d, err)

        if "invalid subcategory" in err:
            fixed = _fix_invalid_subcategory(d, err)

        if "invalid op" in err:
            fixed = _fix_invalid_op(d, err)

        if "value has unexpected type" in err:
            fixed = _fix_value_type(d, err) or fixed

        if "missing 'value'" in err:
            fixed = _fix_missing_value(d, err)

        if "no trades found" in err:
            fixed = _fix_no_trades(d)

        if "ready is not True" in err:
            d["ready"] = True
            fixed = True

        if "missing " in err and any(k in err for k in ["exchange", "symbol", "timeframe",
                                                         "direction", "lookahead",
                                                         "min_occurrences", "leverage"]):
            fixed = _fix_missing_response_field(d, err)

        if not fixed:
            remaining.append(err)

    return d, remaining


def _fix_type_to_config_update(data: dict) -> bool:
    """Convert message type to config_update with defaults."""
    if data.get("type") != "message":
        return False
    content = data.get("content", "")
    data["type"] = "config_update"
    data.setdefault("response", {})
    resp = data["response"]
    resp.setdefault("name", "")
    resp.setdefault("exchange", "binance")
    resp.setdefault("symbol", "BTCUSDC")
    resp.setdefault("timeframe", "1H")
    resp.setdefault("leverage", 1)
    resp.setdefault("direction", "long_only")
    resp.setdefault("lookahead", 5)
    resp.setdefault("min_occurrences", 10)
    resp.setdefault("mc_shuffles", 500)
    resp.setdefault("walk_forward", True)
    resp.setdefault("walk_windows", 5)
    resp.setdefault("walk_train_pct", 0.7)
    resp.setdefault("start_time", None)
    resp.setdefault("end_time", None)
    resp["trades"] = {
        "long": [{
            "open": {"conditions": copy.deepcopy(DEFAULT_OPEN_CONDITIONS),
                     "orders": [{"type": "market", "size": 1, "size_type": "percent", "price": None}]},
            "close": {"conditions": copy.deepcopy(DEFAULT_CLOSE_CONDITIONS),
                      "orders": [{"type": "market", "size": 1, "size_type": "percent", "price": None}]},
        }],
        "short": [],
    }
    data["ready"] = True
    data["content"] = content or "Strategy configured"
    return True


def _fix_unknown_metric(data: dict, err: str) -> bool:
    label = err.split(":")[0] if ":" in err else ""
    for side in ("long", "short"):
        for t in data.get("response", data).get("trades", {}).get(side, []):
            for phase in ("open", "close"):
                conds = t.get(phase, {}).get("conditions", {})
                for g in conds.get("groups", []):
                    for c in g.get("conditions", []):
                        mid = c.get("metric", "")
                        resolved = INDICATOR_ALIASES.get(mid)
                        if resolved:
                            c["metric"] = resolved
                            return True
                        val = c.get("value", "")
                        if isinstance(val, str):
                            resolved_val = INDICATOR_ALIASES.get(val)
                            if resolved_val:
                                c["value"] = resolved_val
                                return True
    return False


def _resolve_label_phase(label: str):
    if "close" in label:
        return "close"
    if "open" in label:
        return "open"
    return None


def _fix_missing_phase(data: dict, err: str) -> bool:
    label = err.split(":")[0]
    parts = label.split("/")
    if len(parts) < 2:
        return False
    side_part = parts[0]
    side = "long" if "long" in side_part else "short"
    try:
        ti = int(side_part.split("[")[1].split("]")[0])
    except (IndexError, ValueError):
        return False
    phase = _resolve_label_phase(label)
    if not phase:
        return False
    trades = data.get("response", data).get("trades", {}).get(side, [])
    if ti >= len(trades):
        return False
    if phase not in trades[ti]:
        trades[ti][phase] = {}
    td = trades[ti][phase]
    if "conditions" not in td:
        td["conditions"] = copy.deepcopy(DEFAULT_CLOSE_CONDITIONS if phase == "close" else DEFAULT_OPEN_CONDITIONS)
    if "orders" not in td:
        td["orders"] = [{"type": "market", "size": 1, "size_type": "percent", "price": None}]
    return True


def _fix_empty_groups(data: dict, err: str) -> bool:
    label = err.split(":")[0]
    parts = label.split("/")
    side = "long" if "long" in parts[0] else "short"
    try:
        ti = int(parts[0].split("[")[1].split("]")[0])
    except (IndexError, ValueError):
        return False
    phase = _resolve_label_phase(label)
    if not phase:
        phase = "close" if "close" in parts else "open"
    trades = data.get("response", data).get("trades", {}).get(side, [])
    if ti >= len(trades):
        return False
    phase_data = trades[ti].get(phase, {})
    conds = phase_data.get("conditions", {})
    if not conds.get("groups"):
        conds["groups"] = [{"logic": "AND", "conditions": [{
            "subcategory": "threshold", "metric": "oc", "op": "gt", "value": 0.2
        }]}]
        conds["logic"] = "AND"
        return True
    for g in conds.get("groups", []):
        if not g.get("conditions"):
            g["conditions"] = [{"subcategory": "threshold", "metric": "oc", "op": "gt", "value": 0.2}]
    return True


def _fix_invalid_subcategory(data: dict, err: str) -> bool:
    label = err.split(":")[0]
    parts = label.split("/")
    side = "long" if "long" in parts[0] else "short"
    try:
        ti = int(parts[0].split("[")[1].split("]")[0])
    except (IndexError, ValueError):
        return False
    phase = "close" if "/close/" in label else "open"
    try:
        gi = int(parts[-2].replace("g", ""))
        ci = int(parts[-1].replace("c", ""))
    except (IndexError, ValueError):
        return False
    trades = data.get("response", data).get("trades", {}).get(side, [])
    if ti >= len(trades):
        return False
    clist = trades[ti].get(phase, {}).get("conditions", {}).get("groups", [])
    if gi >= len(clist):
        return False
    conds_list = clist[gi].get("conditions", [])
    if ci >= len(conds_list):
        return False
    conds_list[ci]["subcategory"] = "threshold"
    return True


def _fix_invalid_op(data: dict, err: str) -> bool:
    label = err.split(":")[0]
    parts = label.split("/")
    side = "long" if "long" in parts[0] else "short"
    try:
        ti = int(parts[0].split("[")[1].split("]")[0])
    except (IndexError, ValueError):
        return False
    phase = _resolve_label_phase(label) or "close"
    try:
        gi = int(parts[-2].replace("g", ""))
        ci = int(parts[-1].replace("c", ""))
    except (IndexError, ValueError):
        return False
    trades = data.get("response", data).get("trades", {}).get(side, [])
    if ti >= len(trades):
        return False
    conds = trades[ti].get(phase, {}).get("conditions", {}).get("groups", [])
    if gi >= len(conds):
        return False
    clist = conds[gi].get("conditions", [])
    if ci >= len(clist):
        return False
    clist[ci]["op"] = "gt"
    return True


def _fix_missing_orders_or_conditions(data: dict, err: str) -> bool:
    """Fix 'has no orders' or 'has no conditions' errors by adding defaults."""
    label = err.split(":")[0]
    parts = label.split("/")
    side = "long" if "long" in parts[0] else "short"
    try:
        ti = int(parts[0].split("[")[1].split("]")[0])
    except (IndexError, ValueError):
        return False
    phase = _resolve_label_phase(label) or "close"
    trades = data.get("response", data).get("trades", {}).get(side, [])
    if ti >= len(trades):
        return False
    phase_data = trades[ti].get(phase, {})
    if "has no orders" in err:
        if not phase_data.get("orders"):
            phase_data["orders"] = [{"type": "market", "size": 1, "size_type": "percent", "price": None}]
            return True
    if "has no conditions" in err:
        if not phase_data.get("conditions", {}).get("groups"):
            phase_data["conditions"] = copy.deepcopy(DEFAULT_CLOSE_CONDITIONS if phase == "close" else DEFAULT_OPEN_CONDITIONS)
            return True
    return False


def _fix_missing_value(data: dict, err: str) -> bool:
    label = err.split(":")[0]
    parts = label.split("/")
    side = "long" if "long" in parts[0] else "short"
    try:
        ti = int(parts[0].split("[")[1].split("]")[0])
    except (IndexError, ValueError):
        return False
    phase = _resolve_label_phase(label) or "close"
    try:
        gi = int(parts[-2].replace("g", ""))
        ci = int(parts[-1].replace("c", ""))
    except (IndexError, ValueError):
        return False
    trades = data.get("response", data).get("trades", {}).get(side, [])
    if ti >= len(trades):
        return False
    conds = trades[ti].get(phase, {}).get("conditions", {}).get("groups", [])
    if gi >= len(conds):
        return False
    clist = conds[gi].get("conditions", [])
    if ci >= len(clist):
        return False
    clist[ci]["value"] = 0.0
    return True


def _fix_value_string(data: dict, err: str) -> bool:
    """Fix 'value is string X but not a valid metric/indicator' by resolving alias."""
    label = err.split(":")[0]
    parts = label.split("/")
    side = "long" if "long" in parts[0] else "short"
    try:
        ti = int(parts[0].split("[")[1].split("]")[0])
    except (IndexError, ValueError):
        return False
    phase = _resolve_label_phase(label) or "close"
    try:
        gi = int(parts[-2].replace("g", ""))
        ci = int(parts[-1].replace("c", ""))
    except (IndexError, ValueError):
        return False
    trades = data.get("response", data).get("trades", {}).get(side, [])
    if ti >= len(trades):
        return False
    conds = trades[ti].get(phase, {}).get("conditions", {}).get("groups", [])
    if gi >= len(conds):
        return False
    clist = conds[gi].get("conditions", [])
    if ci >= len(clist):
        return False
    val = clist[ci].get("value", "")
    if isinstance(val, str):
        resolved = INDICATOR_ALIASES.get(val)
        if resolved:
            clist[ci]["value"] = resolved
            return True
    return False


def _fix_value_type(data: dict, err: str) -> bool:
    """Fix 'value has unexpected type dict' by replacing with a number."""
    label = err.split(":")[0]
    parts = label.split("/")
    side = "long" if "long" in parts[0] else "short"
    try:
        ti = int(parts[0].split("[")[1].split("]")[0])
    except (IndexError, ValueError):
        return False
    phase = _resolve_label_phase(label) or "close"
    try:
        gi = int(parts[-2].replace("g", ""))
        ci = int(parts[-1].replace("c", ""))
    except (IndexError, ValueError):
        return False
    trades = data.get("response", data).get("trades", {}).get(side, [])
    if ti >= len(trades):
        return False
    conds = trades[ti].get(phase, {}).get("conditions", {}).get("groups", [])
    if gi >= len(conds):
        return False
    clist = conds[gi].get("conditions", [])
    if ci >= len(clist):
        return False
    clist[ci]["value"] = 0.0
    return True


def _fix_no_trades(data: dict) -> bool:
    resp = data.get("response", data)
    resp["trades"] = {
        "long": [{
            "open": {"conditions": copy.deepcopy(DEFAULT_OPEN_CONDITIONS),
                     "orders": [{"type": "market", "size": 1, "size_type": "percent", "price": None}]},
            "close": {"conditions": copy.deepcopy(DEFAULT_CLOSE_CONDITIONS),
                      "orders": [{"type": "market", "size": 1, "size_type": "percent", "price": None}]},
        }],
        "short": [],
    }
    return True


def _fix_missing_response_field(data: dict, err: str) -> bool:
    DEFAULTS = {
        "exchange": "binance",
        "symbol": "BTCUSDC",
        "timeframe": "1H",
        "direction": "long_only",
        "lookahead": 5,
        "min_occurrences": 10,
        "leverage": 1,
    }
    resp = data.get("response", data)
    for key, val in DEFAULTS.items():
        if key not in resp:
            resp[key] = val
            return True
    return False


if __name__ == "__main__":
    import json, sys
    data = json.load(sys.stdin)
    from strategy_validator import validate_strategy
    errors = validate_strategy(data)
    if not errors:
        print("No errors to fix")
        sys.exit(0)
    fixed, remaining = fix_errors(data, errors)
    if remaining:
        print(f"Fixed {len(errors) - len(remaining)}/{len(errors)} errors")
        print(f"Remaining ({len(remaining)}):")
        for e in remaining:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print(f"Fixed all {len(errors)} errors")
        print(json.dumps(fixed, indent=2))
