use pyo3::prelude::*;

pub mod indicators;
pub mod backtest;
pub mod metrics;
pub mod formula;
pub mod statemachine;
pub mod condeval;

#[pymodule]
fn vibe_engine(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Existing indicators
    m.add_function(wrap_pyfunction!(crate::indicators::rsi, m)?)?;
    m.add_function(wrap_pyfunction!(crate::indicators::sma, m)?)?;
    m.add_function(wrap_pyfunction!(crate::indicators::ema, m)?)?;
    m.add_function(wrap_pyfunction!(crate::indicators::bbands, m)?)?;
    m.add_function(wrap_pyfunction!(crate::indicators::atr, m)?)?;
    m.add_function(wrap_pyfunction!(crate::indicators::macd, m)?)?;
    m.add_function(wrap_pyfunction!(crate::indicators::stochastic, m)?)?;
    m.add_function(wrap_pyfunction!(crate::indicators::vwap, m)?)?;
    m.add_function(wrap_pyfunction!(crate::indicators::williams_r, m)?)?;
    m.add_function(wrap_pyfunction!(crate::indicators::obv, m)?)?;
    m.add_function(wrap_pyfunction!(crate::indicators::cci, m)?)?;
    m.add_function(wrap_pyfunction!(crate::indicators::mfi, m)?)?;
    m.add_function(wrap_pyfunction!(crate::indicators::adx, m)?)?;

    // Existing backtest + metrics
    m.add_function(wrap_pyfunction!(crate::backtest::run_backtest, m)?)?;
    m.add_function(wrap_pyfunction!(crate::metrics::compute_metrics, m)?)?;

    // New formula evaluator
    m.add_function(wrap_pyfunction!(crate::formula::eval_formula, m)?)?;
    m.add_function(wrap_pyfunction!(crate::formula::validate_formula, m)?)?;

    // New state machine for custom order types
    m.add_function(wrap_pyfunction!(crate::statemachine::run_state_machine_order, m)?)?;

    // New condition evaluator
    m.add_function(wrap_pyfunction!(crate::condeval::eval_condition_group_series, m)?)?;
    m.add_function(wrap_pyfunction!(crate::condeval::check_condition, m)?)?;

    Ok(())
}
