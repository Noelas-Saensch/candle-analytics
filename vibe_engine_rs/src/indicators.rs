use numpy::{PyArray, PyArray1, PyReadonlyArray1};
use pyo3::prelude::*;

fn typical_price(high: &[f64], low: &[f64], close: &[f64]) -> Vec<f64> {
    high.iter()
        .zip(low.iter())
        .zip(close.iter())
        .map(|((h, l), c)| (h + l + c) / 3.0)
        .collect()
}

fn compute_rsi(close: &[f64], period: usize) -> Vec<f64> {
    let n = close.len();
    if n <= period {
        return vec![50.0; n];
    }
    let mut gains = Vec::with_capacity(n);
    let mut losses = Vec::with_capacity(n);
    gains.push(0.0);
    losses.push(0.0);
    for i in 1..n {
        let diff = close[i] - close[i - 1];
        gains.push(if diff > 0.0 { diff } else { 0.0 });
        losses.push(if diff < 0.0 { -diff } else { 0.0 });
    }
    let mut avg_gain: f64 = gains[1..=period].iter().sum::<f64>() / period as f64;
    let mut avg_loss: f64 = losses[1..=period].iter().sum::<f64>() / period as f64;
    let mut result = Vec::with_capacity(n);
    result.push(50.0);
    for i in 1..n {
        if i <= period {
            result.push(50.0);
        } else if i == period + 1 {
            let rs = if avg_loss == 0.0 { 100.0 } else { avg_gain / avg_loss };
            result.push(100.0 - 100.0 / (1.0 + rs));
        } else {
            avg_gain = (avg_gain * (period as f64 - 1.0) + gains[i]) / period as f64;
            avg_loss = (avg_loss * (period as f64 - 1.0) + losses[i]) / period as f64;
            let rs = if avg_loss == 0.0 { 100.0 } else { avg_gain / avg_loss };
            result.push(100.0 - 100.0 / (1.0 + rs));
        }
    }
    result
}

fn compute_sma(values: &[f64], period: usize) -> Vec<f64> {
    let n = values.len();
    if n == 0 || period == 0 {
        return vec![0.0; n];
    }
    let mut result = Vec::with_capacity(n);
    let mut sum = 0.0;
    for i in 0..n {
        sum += values[i];
        if i >= period {
            sum -= values[i - period];
        }
        result.push(if i < period - 1 { f64::NAN } else { sum / period as f64 });
    }
    result
}

fn compute_ema(values: &[f64], period: usize) -> Vec<f64> {
    let n = values.len();
    if n == 0 || period == 0 {
        return vec![0.0; n];
    }
    let k = 2.0 / (period as f64 + 1.0);
    let mut result = Vec::with_capacity(n);
    let mut prev = values[0];
    result.push(prev);
    for i in 1..n {
        prev = values[i] * k + prev * (1.0 - k);
        result.push(prev);
    }
    result
}

#[pyfunction]
pub fn rsi<'py>(py: Python<'py>, close: PyReadonlyArray1<'py, f64>, period: usize) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let slice = close.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let result = compute_rsi(slice, period);
    Ok(PyArray::from_vec_bound(py, result))
}

#[pyfunction]
pub fn sma<'py>(py: Python<'py>, values: PyReadonlyArray1<'py, f64>, period: usize) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let slice = values.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let result = compute_sma(slice, period);
    Ok(PyArray::from_vec_bound(py, result))
}

#[pyfunction]
pub fn ema<'py>(py: Python<'py>, values: PyReadonlyArray1<'py, f64>, period: usize) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let slice = values.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let result = compute_ema(slice, period);
    Ok(PyArray::from_vec_bound(py, result))
}

#[pyfunction]
pub fn bbands<'py>(_py: Python<'py>, values: PyReadonlyArray1<'py, f64>, period: usize, std_dev: f64) -> PyResult<(Vec<f64>, Vec<f64>, Vec<f64>)> {
    let vals = values.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let n = vals.len();
    if n < period {
        return Ok((vec![0.0; n], vec![0.0; n], vec![0.0; n]));
    }
    let mut upper = Vec::with_capacity(n);
    let mut middle = Vec::with_capacity(n);
    let mut lower = Vec::with_capacity(n);
    for i in 0..n {
        if i < period - 1 {
            upper.push(f64::NAN);
            middle.push(f64::NAN);
            lower.push(f64::NAN);
        } else {
            let slice = &vals[i + 1 - period..=i];
            let mean: f64 = slice.iter().sum::<f64>() / period as f64;
            let variance: f64 = slice.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / period as f64;
            let sd = variance.sqrt();
            middle.push(mean);
            upper.push(mean + std_dev * sd);
            lower.push(mean - std_dev * sd);
        }
    }
    Ok((upper, middle, lower))
}

#[pyfunction]
pub fn atr<'py>(py: Python<'py>, high: PyReadonlyArray1<'py, f64>, low: PyReadonlyArray1<'py, f64>, close: PyReadonlyArray1<'py, f64>, period: usize) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let h = high.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let l = low.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let c = close.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let n = h.len();
    if n < 2 {
        return Ok(PyArray::from_vec_bound(py, vec![0.0; n]));
    }
    let mut tr = Vec::with_capacity(n);
    tr.push(h[0] - l[0]);
    for i in 1..n {
        let hl = h[i] - l[i];
        let hc = (h[i] - c[i - 1]).abs();
        let lc = (l[i] - c[i - 1]).abs();
        tr.push(hl.max(hc).max(lc));
    }
    let mut result = Vec::with_capacity(n);
    let mut prev_atr: f64 = tr[1..=period].iter().sum::<f64>() / period as f64;
    result.push(f64::NAN);
    for i in 1..n {
        if i < period {
            result.push(f64::NAN);
        } else if i == period {
            result.push(prev_atr);
        } else {
            prev_atr = (prev_atr * (period as f64 - 1.0) + tr[i]) / period as f64;
            result.push(prev_atr);
        }
    }
    Ok(PyArray::from_vec_bound(py, result))
}

#[pyfunction]
pub fn macd<'py>(_py: Python<'py>, values: PyReadonlyArray1<'py, f64>, fast: usize, slow: usize, signal: usize) -> PyResult<(Vec<f64>, Vec<f64>, Vec<f64>)> {
    let vals = values.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let n = vals.len();
    if n < slow {
        return Ok((vec![0.0; n], vec![0.0; n], vec![0.0; n]));
    }
    let k_fast = 2.0 / (fast as f64 + 1.0);
    let k_slow = 2.0 / (slow as f64 + 1.0);
    let mut ema_fast = Vec::with_capacity(n);
    let mut ema_slow = Vec::with_capacity(n);
    let mut f = vals[0];
    let mut s = vals[0];
    ema_fast.push(f);
    ema_slow.push(s);
    for i in 1..n {
        f = vals[i] * k_fast + f * (1.0 - k_fast);
        s = vals[i] * k_slow + s * (1.0 - k_slow);
        ema_fast.push(f);
        ema_slow.push(s);
    }
    let macd_line: Vec<f64> = ema_fast.iter().zip(ema_slow.iter()).map(|(f, s)| f - s).collect();
    let k_sig = 2.0 / (signal as f64 + 1.0);
    let mut sig = macd_line[0];
    let mut signal_line = Vec::with_capacity(n);
    signal_line.push(sig);
    for i in 1..n {
        sig = macd_line[i] * k_sig + sig * (1.0 - k_sig);
        signal_line.push(sig);
    }
    let histogram: Vec<f64> = macd_line.iter().zip(signal_line.iter()).map(|(m, s)| m - s).collect();
    Ok((macd_line, signal_line, histogram))
}

#[pyfunction]
pub fn stochastic<'py>(_py: Python<'py>, high: PyReadonlyArray1<'py, f64>, low: PyReadonlyArray1<'py, f64>, close: PyReadonlyArray1<'py, f64>, period: usize) -> PyResult<(Vec<f64>, Vec<f64>)> {
    let h = high.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let l = low.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let c = close.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let n = h.len();
    if n < period {
        return Ok((vec![50.0; n], vec![50.0; n]));
    }
    let mut k_vals = Vec::with_capacity(n);
    for i in 0..n {
        if i < period - 1 {
            k_vals.push(50.0);
        } else {
            let high_max = h[i + 1 - period..=i].iter().cloned().fold(f64::NEG_INFINITY, f64::max);
            let low_min = l[i + 1 - period..=i].iter().cloned().fold(f64::INFINITY, f64::min);
            if (high_max - low_min).abs() < 1e-12 {
                k_vals.push(50.0);
            } else {
                k_vals.push((c[i] - low_min) / (high_max - low_min) * 100.0);
            }
        }
    }
    let d_vec = compute_sma(&k_vals, 3);
    Ok((k_vals, d_vec))
}

#[pyfunction]
pub fn vwap<'py>(py: Python<'py>, high: PyReadonlyArray1<'py, f64>, low: PyReadonlyArray1<'py, f64>, close: PyReadonlyArray1<'py, f64>, volume: PyReadonlyArray1<'py, f64>) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let h = high.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let l = low.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let c = close.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let v = volume.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let n = h.len();
    if n == 0 {
        return Ok(PyArray::from_vec_bound(py, vec![]));
    }
    let tp: Vec<f64> = typical_price(h, l, c);
    let mut cum_pv = 0.0;
    let mut cum_vol = 0.0;
    let mut result = Vec::with_capacity(n);
    for i in 0..n {
        cum_pv += tp[i] * v[i];
        cum_vol += v[i];
        result.push(if cum_vol == 0.0 { tp[i] } else { cum_pv / cum_vol });
    }
    Ok(PyArray::from_vec_bound(py, result))
}

// ── Williams %R ──
fn compute_williams_r(high: &[f64], low: &[f64], close: &[f64], period: usize) -> Vec<f64> {
    let n = high.len();
    if n < period {
        return vec![-50.0; n];
    }
    let mut result = Vec::with_capacity(n);
    for i in 0..n {
        if i < period - 1 {
            result.push(-50.0);
        } else {
            let high_max = high[i + 1 - period..=i].iter().cloned().fold(f64::NEG_INFINITY, f64::max);
            let low_min = low[i + 1 - period..=i].iter().cloned().fold(f64::INFINITY, f64::min);
            let range = high_max - low_min;
            if range.abs() < 1e-12 {
                result.push(-50.0);
            } else {
                result.push((high_max - close[i]) / range * -100.0);
            }
        }
    }
    result
}

#[pyfunction]
pub fn williams_r<'py>(py: Python<'py>, high: PyReadonlyArray1<'py, f64>, low: PyReadonlyArray1<'py, f64>, close: PyReadonlyArray1<'py, f64>, period: usize) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let h = high.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let l = low.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let c = close.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let result = compute_williams_r(h, l, c, period);
    Ok(PyArray::from_vec_bound(py, result))
}

// ── OBV (On-Balance Volume) ──
fn compute_obv(close: &[f64], volume: &[f64]) -> Vec<f64> {
    let n = close.len();
    if n == 0 {
        return vec![];
    }
    let mut result = Vec::with_capacity(n);
    result.push(volume[0]);
    for i in 1..n {
        if close[i] > close[i - 1] {
            result.push(result[i - 1] + volume[i]);
        } else if close[i] < close[i - 1] {
            result.push(result[i - 1] - volume[i]);
        } else {
            result.push(result[i - 1]);
        }
    }
    result
}

#[pyfunction]
pub fn obv<'py>(py: Python<'py>, close: PyReadonlyArray1<'py, f64>, volume: PyReadonlyArray1<'py, f64>) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let c = close.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let v = volume.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let result = compute_obv(c, v);
    Ok(PyArray::from_vec_bound(py, result))
}

// ── CCI (Commodity Channel Index) ──
fn compute_cci(high: &[f64], low: &[f64], close: &[f64], period: usize) -> Vec<f64> {
    let n = high.len();
    if n < period {
        return vec![0.0; n];
    }
    let tp: Vec<f64> = typical_price(high, low, close);
    let sma_tp = compute_sma(&tp, period);
    let mut result = Vec::with_capacity(n);
    for i in 0..n {
        if i < period - 1 {
            result.push(0.0);
        } else {
            let mean = sma_tp[i];
            let md: f64 = tp[i + 1 - period..=i].iter().map(|v| (v - mean).abs()).sum::<f64>() / period as f64;
            if md.abs() < 1e-12 {
                result.push(0.0);
            } else {
                result.push((tp[i] - mean) / (0.015 * md));
            }
        }
    }
    result
}

#[pyfunction]
pub fn cci<'py>(py: Python<'py>, high: PyReadonlyArray1<'py, f64>, low: PyReadonlyArray1<'py, f64>, close: PyReadonlyArray1<'py, f64>, period: usize) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let h = high.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let l = low.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let c = close.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let result = compute_cci(h, l, c, period);
    Ok(PyArray::from_vec_bound(py, result))
}

// ── MFI (Money Flow Index) ──
fn compute_mfi(high: &[f64], low: &[f64], close: &[f64], volume: &[f64], period: usize) -> Vec<f64> {
    let n = high.len();
    if n <= period {
        return vec![50.0; n];
    }
    let tp: Vec<f64> = typical_price(high, low, close);
    let mut pos_mf = Vec::with_capacity(n);
    let mut neg_mf = Vec::with_capacity(n);
    pos_mf.push(0.0);
    neg_mf.push(0.0);
    for i in 1..n {
        let mf = tp[i] * volume[i];
        if tp[i] > tp[i - 1] {
            pos_mf.push(mf);
            neg_mf.push(0.0);
        } else if tp[i] < tp[i - 1] {
            pos_mf.push(0.0);
            neg_mf.push(mf);
        } else {
            pos_mf.push(0.0);
            neg_mf.push(0.0);
        }
    }
    let mut result = Vec::with_capacity(n);
    result.push(50.0);
    for i in 1..n {
        if i <= period {
            result.push(50.0);
        } else {
            let sum_pos: f64 = pos_mf[i + 1 - period..=i].iter().sum();
            let sum_neg: f64 = neg_mf[i + 1 - period..=i].iter().sum();
            if sum_neg.abs() < 1e-12 {
                result.push(100.0);
            } else {
                let mr = sum_pos / sum_neg;
                result.push(100.0 - 100.0 / (1.0 + mr));
            }
        }
    }
    result
}

#[pyfunction]
pub fn mfi<'py>(py: Python<'py>, high: PyReadonlyArray1<'py, f64>, low: PyReadonlyArray1<'py, f64>, close: PyReadonlyArray1<'py, f64>, volume: PyReadonlyArray1<'py, f64>, period: usize) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let h = high.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let l = low.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let c = close.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let v = volume.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let result = compute_mfi(h, l, c, v, period);
    Ok(PyArray::from_vec_bound(py, result))
}

// ── ADX (Average Directional Index) ──
fn true_range(high: &[f64], low: &[f64], prev_close: &[f64]) -> Vec<f64> {
    let n = high.len();
    let mut tr = Vec::with_capacity(n);
    tr.push(high[0] - low[0]);
    for i in 1..n {
        let hl = high[i] - low[i];
        let hc = (high[i] - prev_close[i - 1]).abs();
        let lc = (low[i] - prev_close[i - 1]).abs();
        tr.push(hl.max(hc).max(lc));
    }
    tr
}

fn wilder_smooth(values: &[f64], period: usize) -> Vec<f64> {
    let n = values.len();
    if n <= period {
        return vec![0.0; n];
    }
    let k = 1.0 / period as f64;
    let mut result = Vec::with_capacity(n);
    for _ in 0..period {
        result.push(f64::NAN);
    }
    let first: f64 = values[1..=period].iter().sum::<f64>() / period as f64;
    let mut prev = first;
    result.push(first);
    for i in period + 1..n {
        prev = (values[i] - prev) * k + prev;
        result.push(prev);
    }
    result
}

fn compute_adx(high: &[f64], low: &[f64], close: &[f64], period: usize) -> Vec<f64> {
    let n = high.len();
    if n <= period * 2 {
        return vec![25.0; n];
    }
    let tr = true_range(high, low, close);
    let mut plus_dm = Vec::with_capacity(n);
    let mut minus_dm = Vec::with_capacity(n);
    plus_dm.push(0.0);
    minus_dm.push(0.0);
    for i in 1..n {
        let up = high[i] - high[i - 1];
        let down = low[i - 1] - low[i];
        if up > down && up > 0.0 {
            plus_dm.push(up);
        } else {
            plus_dm.push(0.0);
        }
        if down > up && down > 0.0 {
            minus_dm.push(down);
        } else {
            minus_dm.push(0.0);
        }
    }
    let smooth_tr = wilder_smooth(&tr, period);
    let smooth_plus = wilder_smooth(&plus_dm, period);
    let smooth_minus = wilder_smooth(&minus_dm, period);
    let mut di_plus = Vec::with_capacity(n);
    let mut di_minus = Vec::with_capacity(n);
    for i in 0..n {
        if i < period || smooth_tr[i].is_nan() || smooth_tr[i].abs() < 1e-12 {
            di_plus.push(f64::NAN);
            di_minus.push(f64::NAN);
        } else {
            di_plus.push(100.0 * smooth_plus[i] / smooth_tr[i]);
            di_minus.push(100.0 * smooth_minus[i] / smooth_tr[i]);
        }
    }
    let mut dx = Vec::with_capacity(n);
    for i in 0..n {
        if di_plus[i].is_nan() || di_minus[i].is_nan() || (di_plus[i] + di_minus[i]).abs() < 1e-12 {
            dx.push(f64::NAN);
        } else {
            let diff = (di_plus[i] - di_minus[i]).abs();
            let sum = di_plus[i] + di_minus[i];
            dx.push(100.0 * diff / sum);
        }
    }
    // ADX = SMA of DX over period
    let mut valid_dx = Vec::with_capacity(n);
    for i in 0..n {
        if dx[i].is_nan() {
            valid_dx.push(0.0);
        } else {
            valid_dx.push(dx[i]);
        }
    }
    compute_sma(&valid_dx, period)
}

#[pyfunction]
pub fn adx<'py>(py: Python<'py>, high: PyReadonlyArray1<'py, f64>, low: PyReadonlyArray1<'py, f64>, close: PyReadonlyArray1<'py, f64>, period: usize) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let h = high.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let l = low.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let c = close.as_slice().map_err(|_| pyo3::exceptions::PyValueError::new_err("non-contiguous array"))?;
    let result = compute_adx(h, l, c, period);
    Ok(PyArray::from_vec_bound(py, result))
}
