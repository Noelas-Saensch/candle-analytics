//! Boolean condition evaluator for custom conditions.
//! Evaluates conditions against OHLCV data + indicator values.
//! Supports the same expression syntax as formula.rs but returns boolean (0.0/1.0).

use pyo3::prelude::*;
use std::collections::HashMap;

/// Evaluate a boolean condition expression on a specific bar.
/// Returns 1.0 if condition is true, 0.0 if false, -1.0 if error.
pub fn eval_condition_on_bar(
    expression: &str,
    bar_idx: usize,
    closes: &[f64],
    highs: &[f64],
    lows: &[f64],
    opens: &[f64],
    volumes: &[f64],
    indicators: &HashMap<String, Vec<f64>>,
    constants: &HashMap<String, f64>,
) -> f64 {
    // Build var map: merge raw price data + pre-computed indicators
    let mut vars = HashMap::new();
    vars.insert("close".to_string(), closes.to_vec());
    vars.insert("high".to_string(), highs.to_vec());
    vars.insert("low".to_string(), lows.to_vec());
    vars.insert("open".to_string(), opens.to_vec());
    vars.insert("volume".to_string(), volumes.to_vec());

    // Add pre-computed indicators
    for (name, values) in indicators {
        vars.insert(name.clone(), values.clone());
    }

    // Build constants context
    let mut ctx = constants.clone();
    ctx.insert("__bar".to_string(), bar_idx as f64);

    match crate::formula::eval_formula(expression, vars, ctx) {
        Ok(results) => {
            if bar_idx < results.len() {
                if results[bar_idx] != 0.0 { 1.0 } else { 0.0 }
            } else {
                -1.0
            }
        }
        Err(_) => -1.0,
    }
}

/// Evaluate a condition group (AND/OR logic).
/// Groups: [{ "operator": "AND", "conditions": [...] }, ...]
/// Each condition: { "metric_id": "...", "op": "...", "value": ..., "params": {...} }
/// OR: { "expression": "formula_string" }
pub fn eval_condition_group(
    group_json: &str,
    bar_idx: usize,
    closes: &[f64],
    highs: &[f64],
    lows: &[f64],
    opens: &[f64],
    volumes: &[f64],
    indicators: &HashMap<String, Vec<f64>>,
) -> bool {
    let group: serde_json::Value = match serde_json::from_str(group_json) {
        Ok(v) => v,
        Err(_) => return false,
    };

    let operator = group.get("operator").and_then(|v| v.as_str()).unwrap_or("AND");
    let conditions = group.get("conditions").and_then(|v| v.as_array()).map(|v| v.clone()).unwrap_or_default();

    if conditions.is_empty() {
        // Single condition as direct expression
        if let Some(expr) = group.get("expression").and_then(|v| v.as_str()) {
            let result = eval_condition_on_bar(expr, bar_idx, closes, highs, lows, opens, volumes, indicators, &HashMap::new());
            return result > 0.0;
        }
        // Single condition as { metric_id, op, value }
        if let (Some(metric_id), Some(op), Some(value)) = (
            group.get("metric_id").and_then(|v| v.as_str()),
            group.get("op").and_then(|v| v.as_str()),
            group.get("value").and_then(|v| v.as_f64()),
        ) {
            return check_single_condition(metric_id, op, value, bar_idx, closes, indicators);
        }
        return false;
    }

    match operator {
        "OR" => {
            for cond in &conditions {
                if eval_single_condition_value(cond, bar_idx, closes, highs, lows, opens, volumes, indicators) {
                    return true;
                }
            }
            false
        }
        _ => { // AND (default)
            for cond in &conditions {
                if !eval_single_condition_value(cond, bar_idx, closes, highs, lows, opens, volumes, indicators) {
                    return false;
                }
            }
            true
        }
    }
}

fn eval_single_condition_value(
    cond: &serde_json::Value,
    bar_idx: usize,
    closes: &[f64],
    highs: &[f64],
    lows: &[f64],
    opens: &[f64],
    volumes: &[f64],
    indicators: &HashMap<String, Vec<f64>>,
) -> bool {
    // Recursive group
    if cond.get("conditions").is_some() {
        return eval_condition_group(
            &cond.to_string(), bar_idx, closes, highs, lows, opens, volumes, indicators,
        );
    }

    // Expression condition
    if let Some(expr) = cond.get("expression").and_then(|v| v.as_str()) {
        let result = eval_condition_on_bar(expr, bar_idx, closes, highs, lows, opens, volumes, indicators, &HashMap::new());
        return result > 0.0;
    }

    // Standard { metric_id, op, value }
    if let (Some(metric_id), Some(op), Some(value)) = (
        cond.get("metric_id").and_then(|v| v.as_str()),
        cond.get("op").and_then(|v| v.as_str()),
        cond.get("value").and_then(|v| v.as_f64()),
    ) {
        return check_single_condition(metric_id, op, value, bar_idx, closes, indicators);
    }

    false
}

fn check_single_condition(
    metric_id: &str,
    op: &str,
    value: f64,
    bar_idx: usize,
    closes: &[f64],
    indicators: &HashMap<String, Vec<f64>>,
) -> bool {
    let metric_value = if metric_id == "close" {
        if bar_idx < closes.len() { closes[bar_idx] } else { return false; }
    } else if metric_id == "high" {
        if bar_idx < closes.len() { closes[bar_idx] } else { return false; } // will be overridden
    } else {
        // Look up in indicators
        indicators.get(metric_id).and_then(|v| v.get(bar_idx)).copied().unwrap_or(f64::NAN)
    };

    if metric_value.is_nan() {
        return false;
    }

    match op {
        "gt" => metric_value > value,
        "gte" | "ge" => metric_value >= value,
        "lt" => metric_value < value,
        "lte" | "le" => metric_value <= value,
        "eq" => (metric_value - value).abs() < 1e-10,
        "neq" | "ne" => (metric_value - value).abs() >= 1e-10,
        "crossed_above" => bar_idx > 0 && metric_value > value && {
            let prev = indicators.get(metric_id).and_then(|v| v.get(bar_idx - 1)).copied().unwrap_or(f64::NAN);
            !prev.is_nan() && prev <= value
        },
        "crossed_below" => bar_idx > 0 && metric_value < value && {
            let prev = indicators.get(metric_id).and_then(|v| v.get(bar_idx - 1)).copied().unwrap_or(f64::NAN);
            !prev.is_nan() && prev >= value
        },
        _ => false,
    }
}

// ---------- Python API ----------

/// Evaluate a complete condition group (with AND/OR nesting) across all bars.
/// Returns Vec<f64> where 1.0 = condition met, 0.0 = not met for each bar.
#[pyfunction]
pub fn eval_condition_group_series(
    group_json: &str,
    closes: Vec<f64>,
    highs: Vec<f64>,
    lows: Vec<f64>,
    opens: Vec<f64>,
    volumes: Vec<f64>,
    indicators: HashMap<String, Vec<f64>>,
) -> PyResult<Vec<f64>> {
    let n = closes.len();
    if n == 0 {
        return Ok(vec![]);
    }

    let mut results = Vec::with_capacity(n);
    for i in 0..n {
        let r = eval_condition_group(group_json, i, &closes, &highs, &lows, &opens, &volumes, &indicators);
        results.push(if r { 1.0 } else { 0.0 });
    }
    Ok(results)
}

/// Evaluate a single condition on one bar (fast path).
#[pyfunction]
pub fn check_condition(
    metric_id: &str,
    op: &str,
    value: f64,
    bar_idx: usize,
    closes: Vec<f64>,
    indicators: HashMap<String, Vec<f64>>,
) -> PyResult<bool> {
    let mut ind_with_close = indicators.clone();
    ind_with_close.insert("close".to_string(), closes.clone());
    Ok(check_single_condition(metric_id, op, value, bar_idx, &closes, &ind_with_close))
}
