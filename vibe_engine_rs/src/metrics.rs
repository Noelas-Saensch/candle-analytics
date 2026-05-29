use pyo3::prelude::*;

#[pyfunction]
pub fn compute_metrics(returns: Vec<f64>, risk_free_rate: f64) -> PyResult<Vec<f64>> {
    let n = returns.len();
    if n == 0 {
        return Ok(vec![0.0; 12]);
    }

    let total_return = if returns[0] != 0.0 {
        (returns.last().unwrap_or(&0.0) - returns[0]) / returns[0].abs()
    } else {
        0.0
    };

    let mut daily_returns = Vec::with_capacity(n);
    for i in 1..n {
        if returns[i - 1] != 0.0 {
            daily_returns.push((returns[i] - returns[i - 1]) / returns[i - 1].abs());
        }
    }
    let dn = daily_returns.len();

    let avg_return = if dn > 0 { daily_returns.iter().sum::<f64>() / dn as f64 } else { 0.0 };

    let variance = if dn > 1 {
        daily_returns.iter().map(|r| (r - avg_return).powi(2)).sum::<f64>() / (dn - 1) as f64
    } else {
        0.0
    };
    let std_dev = variance.sqrt();

    let sharpe = if std_dev > 0.0 {
        (avg_return - risk_free_rate / 252.0) / std_dev * (252.0_f64).sqrt()
    } else {
        0.0
    };

    let downside_returns: Vec<f64> = daily_returns.iter().cloned().filter(|&r| r < 0.0).collect();
    let down_variance = if !downside_returns.is_empty() {
        let down_mean = downside_returns.iter().sum::<f64>() / downside_returns.len() as f64;
        downside_returns.iter().map(|r| (r - down_mean).powi(2)).sum::<f64>() / downside_returns.len() as f64
    } else {
        0.0
    };
    let down_dev = down_variance.sqrt();
    let sortino = if down_dev > 0.0 {
        (avg_return - risk_free_rate / 252.0) / down_dev * (252.0_f64).sqrt()
    } else {
        0.0
    };

    let mut peak = f64::NEG_INFINITY;
    let mut max_dd = 0.0;
    let mut max_dd_duration = 0;
    let mut current_dd_duration = 0;
    for &r in &returns {
        if r > peak {
            peak = r;
            current_dd_duration = 0;
        }
        let dd = if peak != 0.0 { (peak - r) / peak.abs() } else { 0.0 };
        if dd > max_dd {
            max_dd = dd;
        }
        if dd > 0.01 {
            current_dd_duration += 1;
            if current_dd_duration > max_dd_duration {
                max_dd_duration = current_dd_duration;
            }
        } else {
            current_dd_duration = 0;
        }
    }

    let calmar = if max_dd > 0.0 {
        avg_return * 252.0 / max_dd
    } else {
        0.0
    };

    let win_count = daily_returns.iter().filter(|&&r| r > 0.0).count() as f64;
    let loss_count = daily_returns.iter().filter(|&&r| r <= 0.0).count() as f64;
    let win_rate = if dn > 0 { win_count / dn as f64 * 100.0 } else { 0.0 };

    let avg_win = if win_count > 0.0 {
        daily_returns.iter().filter(|&&r| r > 0.0).sum::<f64>() / win_count
    } else {
        0.0
    };
    let avg_loss = if loss_count > 0.0 {
        daily_returns.iter().filter(|&&r| r <= 0.0).sum::<f64>() / loss_count
    } else {
        0.0
    };
    let profit_factor = if avg_loss.abs() > 0.0 {
        (avg_win * win_count) / (avg_loss.abs() * loss_count)
    } else if avg_win > 0.0 {
        f64::INFINITY
    } else {
        1.0
    };

    let max_consec_wins = daily_returns.iter().fold(0usize, |max, &r| {
        if r > 0.0 { max + 1 } else { 0 }
    }) as f64;
    let max_consec_losses = daily_returns.iter().fold(0usize, |max, &r| {
        if r <= 0.0 { max + 1 } else { 0 }
    }) as f64;

    Ok(vec![
        total_return * 100.0,
        avg_return * 252.0 * 100.0,
        sharpe,
        sortino,
        calmar,
        max_dd * 100.0,
        max_dd_duration as f64,
        win_rate,
        avg_win * 100.0,
        avg_loss * 100.0,
        profit_factor,
        max_consec_wins.max(max_consec_losses),
    ])
}
