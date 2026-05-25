use pyo3::prelude::*;

#[pyfunction]
pub fn run_backtest(
    _opens: Vec<f64>,
    highs: Vec<f64>,
    lows: Vec<f64>,
    closes: Vec<f64>,
    _volumes: Vec<f64>,
    strategy_type: &str,
    lookahead: usize,
    stop_loss_pct: f64,
    take_profit_pct: f64,
) -> PyResult<Vec<Vec<f64>>> {
    let n = closes.len();
    if n < lookahead + 1 {
        return Ok(vec![]);
    }

    let mut trades: Vec<Vec<f64>> = Vec::new();

    match strategy_type {
        "long_entry" => {
            for i in 0..n.saturating_sub(lookahead + 1) {
                let entry = closes[i];
                let mut exit = closes[i + 1];
                let mut exit_idx = i + 1;
                let mut reason = 0.0; // 0 = lookahead exit

                for j in (i + 1)..=std::cmp::min(i + lookahead, n - 1) {
                    let high = highs[j];
                    let low = lows[j];
                    if take_profit_pct > 0.0 && high >= entry * (1.0 + take_profit_pct / 100.0) {
                        exit = entry * (1.0 + take_profit_pct / 100.0);
                        exit_idx = j;
                        reason = 1.0; // take profit
                        break;
                    }
                    if stop_loss_pct > 0.0 && low <= entry * (1.0 - stop_loss_pct / 100.0) {
                        exit = entry * (1.0 - stop_loss_pct / 100.0);
                        exit_idx = j;
                        reason = 2.0; // stop loss
                        break;
                    }
                    exit = closes[j];
                    exit_idx = j;
                }

                let ret = (exit - entry) / entry * 100.0;
                trades.push(vec![i as f64, exit_idx as f64, entry, exit, ret, reason]);
            }
        }
        "short_entry" => {
            for i in 0..n.saturating_sub(lookahead + 1) {
                let entry = closes[i];
                let mut exit = closes[i + 1];
                let mut exit_idx = i + 1;
                let mut reason = 0.0;

                for j in (i + 1)..=std::cmp::min(i + lookahead, n - 1) {
                    let high = highs[j];
                    let low = lows[j];
                    if stop_loss_pct > 0.0 && high >= entry * (1.0 + stop_loss_pct / 100.0) {
                        exit = entry * (1.0 + stop_loss_pct / 100.0);
                        exit_idx = j;
                        reason = 2.0;
                        break;
                    }
                    if take_profit_pct > 0.0 && low <= entry * (1.0 - take_profit_pct / 100.0) {
                        exit = entry * (1.0 - take_profit_pct / 100.0);
                        exit_idx = j;
                        reason = 1.0;
                        break;
                    }
                    exit = closes[j];
                    exit_idx = j;
                }

                let ret = (entry - exit) / entry * 100.0;
                trades.push(vec![i as f64, exit_idx as f64, entry, exit, ret, reason]);
            }
        }
        _ => {}
    }

    Ok(trades)
}
