//! Generic finite-state machine engine for order types.
//! Evaluates state transitions bar-by-bar for custom order types
//! (simple, composite, complex).
//!
//! Each order type defines:
//! - states: list of states (e.g., ["idle", "triggered", "executed"])
//! - transitions: list of {from, to, trigger, condition}
//! - params: per-order parameters
//!
//! The engine steps through bars and applies transitions when conditions are met.

use pyo3::prelude::*;
use std::collections::HashMap;

/// A single transition rule
#[derive(Debug, Clone)]
pub struct Transition {
    pub from: String,
    pub to: String,
    pub trigger: String,
    pub condition: String, // formula expression evaluated on current bar
}

/// A running order instance with its current state
#[derive(Debug, Clone)]
pub struct OrderInstance {
    pub id: usize,
    pub order_type: String,
    pub current_state: String,
    pub entry_bar: usize,
    pub entry_price: f64,
    pub params: HashMap<String, f64>,
    pub executed_bar: Option<usize>,
    pub executed_price: Option<f64>,
    pub reason: String,
}

/// Evaluate a transition condition against current bar data.
/// Returns true if the condition is met.
#[allow(unused_variables)]
fn eval_transition_condition(
    condition: &str,
    bar_idx: usize,
    entry_bar: usize,
    entry_price: f64,
    _instance: &OrderInstance,
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    params: &HashMap<String, f64>,
) -> bool {
    if condition.is_empty() {
        return true; // immediate trigger
    }

    // Build variable context for formula evaluation
    let mut vars = HashMap::new();
    vars.insert("close".to_string(), closes.to_vec());
    vars.insert("high".to_string(), highs.to_vec());
    vars.insert("low".to_string(), lows.to_vec());

    // Inject order params as constant arrays
    for (k, v) in params {
        vars.insert(k.clone(), vec![*v; closes.len()]);
    }

    // Inject special variables
    let mut constants = HashMap::new();
    constants.insert("entry_price".to_string(), entry_price);
    constants.insert("entry_bar".to_string(), entry_bar as f64);
    constants.insert("current_bar".to_string(), bar_idx as f64);

    // Peak since entry tracking
    if bar_idx > entry_bar {
        let peak: f64 = (entry_bar..=bar_idx).map(|i| highs[i]).fold(f64::NEG_INFINITY, f64::max);
        let trough: f64 = (entry_bar..=bar_idx).map(|i| lows[i]).fold(f64::INFINITY, f64::min);
        constants.insert("peak_since_entry".to_string(), peak);
        constants.insert("trough_since_entry".to_string(), trough);
    } else {
        constants.insert("peak_since_entry".to_string(), entry_price);
        constants.insert("trough_since_entry".to_string(), entry_price);
    }

    // Evaluate via formula engine
    match crate::formula::eval_formula(condition, vars, constants) {
        Ok(results) => {
            if bar_idx < results.len() {
                results[bar_idx] != 0.0
            } else {
                false
            }
        }
        Err(_) => false,
    }
}

/// Run all order instances through one bar, applying transitions.
/// Returns list of orders that changed state (for logging/UI).
pub fn step_order_instances(
    instances: &mut Vec<OrderInstance>,
    bar_idx: usize,
    highs: &[f64],
    lows: &[f64],
    closes: &[f64],
    transitions: &[Transition],
) -> Vec<(usize, String, String)> {
    let mut changes = Vec::new();

    for inst in instances.iter_mut() {
        if inst.current_state == "executed" || inst.current_state == "cancelled" || inst.current_state == "killed" {
            continue;
        }

        for trans in transitions {
            if trans.from != inst.current_state {
                continue;
            }
            if eval_transition_condition(&trans.condition, bar_idx, inst.entry_bar, inst.entry_price, inst, highs, lows, closes, &inst.params) {
                let old_state = inst.current_state.clone();
                inst.current_state = trans.to.clone();
                inst.reason = trans.trigger.clone();
                if trans.to == "executed" {
                    inst.executed_bar = Some(bar_idx);
                    inst.executed_price = Some(closes[bar_idx]);
                }
                changes.push((inst.id, old_state, trans.to.clone()));
            }
        }
    }

    changes
}

/// Create a new order instance from an order type definition and params.
pub fn create_order_instance(
    id: usize,
    order_type: &str,
    entry_bar: usize,
    entry_price: f64,
    params: HashMap<String, f64>,
) -> OrderInstance {
    OrderInstance {
        id,
        order_type: order_type.to_string(),
        current_state: "idle".to_string(),
        entry_bar,
        entry_price,
        params,
        executed_bar: None,
        executed_price: None,
        reason: String::new(),
    }
}

/// Parse order type JSON definition into a list of transitions.
/// Expected format (from custom_types/orders.json order_types[].state_model):
/// {
///   "states": ["idle", "triggered", "executed"],
///   "transitions": [
///     {"from": "idle", "to": "triggered", "trigger": "price_reached", "condition": "..."},
///     {"from": "triggered", "to": "executed", "trigger": "immediate", "condition": ""}
///   ]
/// }
pub fn parse_transitions_from_json(state_model: &str) -> Vec<Transition> {
    // Parse JSON to extract transitions
    match serde_json::from_str::<serde_json::Value>(state_model) {
        Ok(val) => {
            if let Some(transitions) = val.get("transitions").and_then(|t| t.as_array()) {
                transitions.iter().filter_map(|t| {
                    let from = t.get("from").and_then(|v| v.as_str()).unwrap_or("idle").to_string();
                    let to = t.get("to").and_then(|v| v.as_str()).unwrap_or("executed").to_string();
                    let trigger = t.get("trigger").and_then(|v| v.as_str()).unwrap_or("").to_string();
                    let condition = t.get("condition").and_then(|v| v.as_str()).unwrap_or("").to_string();
                    Some(Transition { from, to, trigger, condition })
                }).collect()
            } else {
                vec![]
            }
        }
        Err(_) => vec![
            // Default: single transition from idle to executed (simple order)
            Transition { from: "idle".to_string(), to: "executed".to_string(), trigger: "immediate".to_string(), condition: "".to_string() }
        ],
    }
}

/// Python-exposed function: run state machine for a single order through full series.
/// Returns Vec<[entry_bar, exit_bar, entry_price, exit_price, return_pct, reason_code]>
#[pyfunction]
pub fn run_state_machine_order(
    _opens: Vec<f64>,
    highs: Vec<f64>,
    lows: Vec<f64>,
    closes: Vec<f64>,
    _volumes: Vec<f64>,
    order_type: &str,
    state_model_json: &str,
    params_json: &str,
    entry_bar: usize,
    entry_price: f64,
) -> PyResult<Vec<f64>> {
    let transitions = parse_transitions_from_json(state_model_json);

    // Parse params from JSON
    let params: HashMap<String, f64> = match serde_json::from_str(params_json) {
        Ok(map) => map,
        Err(_) => HashMap::new(),
    };

    let mut instance = create_order_instance(0, order_type, entry_bar, entry_price, params);
    let n = closes.len();

    let mut exit_result = vec![entry_bar as f64, 0.0, entry_price, entry_price, 0.0, 0.0];

    for bar_idx in entry_bar..n {
        let changes = step_order_instances(
            &mut vec![instance.clone()],
            bar_idx, &highs, &lows, &closes, &transitions,
        );

        // Apply the change to our instance
        for (_, _, new_state) in &changes {
            instance.current_state = new_state.clone();
            if new_state == "executed" {
                instance.executed_bar = Some(bar_idx);
                instance.executed_price = Some(closes[bar_idx]);
            }
        }

        if instance.current_state == "executed" || instance.current_state == "cancelled" || instance.current_state == "killed" {
            let exit_price = instance.executed_price.unwrap_or(closes[bar_idx]);
            let exit_bar = instance.executed_bar.unwrap_or(bar_idx);
            let ret = (exit_price - entry_price) / entry_price * 100.0;
            let reason = if instance.current_state == "cancelled" { 3.0 } else if instance.current_state == "killed" { 4.0 } else { 1.0 };
            exit_result = vec![entry_bar as f64, exit_bar as f64, entry_price, exit_price, ret, reason];
            break;
        }
    }

    Ok(exit_result)
}
