"""Dynamic custom types registry — loads and merges custom_types/*.json
with the built-in CONDITION_REGISTRY.

Provides:
- Dynamic indicator/condition/order registration
- Category CUSTOM auto-generation
- Pre-populated from research catalogs
- AI-defined type persistence
"""

import json
import os
from pathlib import Path

CUSTOM_TYPES_DIR = Path(__file__).parent

# Optional lock file to prevent overwriting AI-generated types
_CUSTOM_TYPES_RELOAD_LOCK = False


def _normalize_params(params: list) -> list:
    """Ensure every param has a 'label' field (derived from 'name' if missing)."""
    out = []
    for p in params:
        p = dict(p)
        if "label" not in p and "name" in p:
            p["label"] = p["name"].replace("_", " ").title()
        out.append(p)
    return out


def load_custom_types() -> dict:
    """Load all custom type definition files from custom_types/ directory."""
    registry = {
        "order_types": [],
        "custom_indicators": [],
        "custom_conditions": [],
        "cdl_patterns": [],
    }
    files = {
        "orders.json": "order_types",
        "indicators.json": "custom_indicators",
        "conditions.json": "custom_conditions",
        "candles.json": "cdl_patterns",
    }
    for filename, key in files.items():
        path = CUSTOM_TYPES_DIR / filename
        if not path.exists():
            continue
        try:
            with open(path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"[custom_types] Warning: failed to load {filename}: {e}")
            continue

        try:
            if "order_types" in data:
                registry["order_types"] = data["order_types"]
            elif "condition_templates" in data:
                registry["custom_conditions"] = list(data["condition_templates"].values())
            elif "cdl_single" in data or any(k.startswith("cdl_") for k in data):
                patterns = []
                for cat_key in data:
                    if cat_key.startswith("cdl_") and isinstance(data[cat_key], dict):
                        patterns.extend(data[cat_key].get("patterns", []))
                registry["cdl_patterns"] = patterns
            else:
                for cat_key in data:
                    if cat_key.startswith("_"):
                        continue
                    cat = data[cat_key]
                    if isinstance(cat, dict) and "indicators" in cat:
                        for ind_id, ind_def in cat["indicators"].items():
                            entry = {
                                "id": ind_id,
                                "label": ind_def["label"],
                                "description": ind_def.get("description", ""),
                                "category": cat_key,
                                "category_label": cat.get("label", cat_key),
                                "type": "custom_indicator",
                                "params": _normalize_params(ind_def.get("params", [])),
                                "outputs": ind_def.get("outputs", [{"name": "value", "label": ind_def["label"]}]),
                                "ops": ind_def.get("ops", ["gt", "gte", "lt", "lte"]),
                                "comparisons": ind_def.get("comparisons", []),
                                "presets": ind_def.get("presets", []),
                                "is_custom": True,
                            }
                            registry["custom_indicators"].append(entry)
        except (KeyError, TypeError) as e:
            print(f"[custom_types] Warning: failed to process {filename}: {e}")

    return registry


def flatten_custom_for_registry() -> list[dict]:
    """Convert custom types to the same format as FLAT_REGISTRY entries
    so they can be merged seamlessly."""
    raw = load_custom_types()
    entries = []

    # Custom indicators
    for ind in raw["custom_indicators"]:
        entries.append({
            "id": ind["id"],
            "label": ind["label"],
            "description": ind["description"],
            "category": "custom",
            "category_label": "Custom Indicators",
            "subcategory": ind.get("category", "custom"),
            "subcategory_label": ind.get("category_label", "Custom"),
            "type": "custom_indicator",
            "params": _normalize_params(ind.get("params", [])),
            "outputs": ind.get("outputs", [{"name": "value", "label": ind["label"]}]),
            "ops": ind.get("ops", ["gt", "gte", "lt", "lte"]),
            "comparisons": ind.get("comparisons", []),
            "presets": ind.get("presets", []),
            "is_custom": True,
            "origin": "research_catalog",
        })

    # CDL patterns
    for cdl in raw["cdl_patterns"]:
        entries.append({
            "id": cdl["id"],
            "label": cdl["label"],
            "description": cdl["description"],
            "category": "custom_candles",
            "category_label": "CDL Patterns (Custom)",
            "subcategory": "custom_candles",
            "subcategory_label": "Candlestick Patterns",
            "type": "custom_cdl",
            "params": [],
            "outputs": [{"name": "value", "label": cdl["label"]}],
            "ops": ["eq"],
            "comparisons": [],
            "presets": [],
            "is_custom": True,
            "origin": "ta_lib",
        })

    return entries


def get_order_type_definitions() -> list[dict]:
    """Return all order type definitions with their state models."""
    raw = load_custom_types()
    return raw["order_types"]


def get_order_types_by_category(category: str) -> list[dict]:
    """Filter order types by category: simple, composite, complex, execution, algorithmic."""
    return [o for o in get_order_type_definitions() if o.get("category") == category]


def save_custom_indicators(indicators: list[dict]):
    """Save AI-generated custom indicators to a dedicated file
    (separate from the pre-populated catalog to avoid overwriting)."""
    custom_file = CUSTOM_TYPES_DIR / "ai_generated.json"
    existing = []
    if custom_file.exists():
        with open(custom_file) as f:
            existing = json.load(f).get("custom_indicators", [])
    # Merge: update existing by id, append new
    ids = {e["id"] for e in existing}
    for ind in indicators:
        if ind["id"] not in ids:
            existing.append(ind)
    with open(custom_file, "w") as f:
        json.dump({"custom_indicators": existing, "order_types": [], "custom_conditions": [], "cdl_patterns": []}, f, indent=2)


def search_custom_conditions(query: str, max_results: int = 5) -> list[dict]:
    """Search custom condition templates by name/description."""
    raw = load_custom_types()
    query = query.lower()
    results = []
    for tmpl in raw["custom_conditions"]:
        score = 0
        if query in tmpl.get("label", "").lower():
            score = 80
        elif query in tmpl.get("description", "").lower():
            score = 50
        elif query in tmpl.get("id", "").lower():
            score = 70
        if score > 0:
            results.append((score, tmpl))
    results.sort(key=lambda x: -x[0])
    return [r[1] for r in results[:max_results]]


def get_condition_template(template_id: str) -> dict | None:
    """Get a specific condition template by id."""
    raw = load_custom_types()
    for tmpl in raw["custom_conditions"]:
        if tmpl.get("id") == template_id:
            return tmpl
    return None


def export_full_catalog() -> dict:
    """Export the complete catalog for AI research and pre-population."""
    custom = load_custom_types()
    return {
        "total_order_types": len(custom["order_types"]),
        "total_custom_indicators": len(custom["custom_indicators"]),
        "total_custom_conditions": len(custom["custom_conditions"]),
        "total_cdl_patterns": len(custom["cdl_patterns"]),
        "order_categories": {
            cat: len(get_order_types_by_category(cat))
            for cat in ["simple", "composite", "complex", "execution", "algorithmic"]
        },
        "indicator_sources": list(set(
            ind.get("category", "unknown")
            for ind in custom["custom_indicators"]
        )),
    }
