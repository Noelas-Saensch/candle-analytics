//! Vectorized formula evaluator for custom indicators.
//! Parses expressions like "rsi(14) < 30 AND sma_20 > sma_50"
//! and evaluates them element-wise across all bars.
//!
//! Core logic is in `eval_formula_inner` (pure Rust, no pyo3) so it's
//! testable via `cargo test`. The `#[pyfunction]` wrappers at the bottom
//! bridge to Python.

use pyo3::prelude::*;
use std::collections::HashMap;

// ---------- Tokenizer ----------

#[derive(Debug, Clone, PartialEq)]
enum Token {
    Number(f64),
    Ident(String),
    Plus, Minus, Star, Slash, Percent,
    Lt, Gt, Le, Ge, Eq, Ne,
    And, Or, Not,
    LParen, RParen, Comma,
    Question, Colon,
    Eof,
}

fn tokenize(s: &str) -> Vec<Token> {
    let mut tokens = Vec::new();
    let chars: Vec<char> = s.chars().collect();
    let mut i = 0;
    while i < chars.len() {
        if chars[i].is_whitespace() { i += 1; continue; }
        match chars[i] {
            '+' => { tokens.push(Token::Plus); i += 1; }
            '-' => { tokens.push(Token::Minus); i += 1; }
            '*' => { tokens.push(Token::Star); i += 1; }
            '/' => { tokens.push(Token::Slash); i += 1; }
            '%' => { tokens.push(Token::Percent); i += 1; }
            '(' => { tokens.push(Token::LParen); i += 1; }
            ')' => { tokens.push(Token::RParen); i += 1; }
            ',' => { tokens.push(Token::Comma); i += 1; }
            '?' => { tokens.push(Token::Question); i += 1; }
            ':' => { tokens.push(Token::Colon); i += 1; }
            '<' => {
                if i + 1 < chars.len() && chars[i + 1] == '=' {
                    tokens.push(Token::Le); i += 2;
                } else {
                    tokens.push(Token::Lt); i += 1;
                }
            }
            '>' => {
                if i + 1 < chars.len() && chars[i + 1] == '=' {
                    tokens.push(Token::Ge); i += 2;
                } else {
                    tokens.push(Token::Gt); i += 1;
                }
            }
            '=' => {
                if i + 1 < chars.len() && chars[i + 1] == '=' {
                    tokens.push(Token::Eq); i += 2;
                } else {
                    return vec![]; // invalid
                }
            }
            '!' => {
                if i + 1 < chars.len() && chars[i + 1] == '=' {
                    tokens.push(Token::Ne); i += 2;
                } else {
                    return vec![]; // invalid (use NOT instead of !)
                }
            }
            '0'..='9' | '.' => {
                let start = i;
                while i < chars.len() && (chars[i].is_ascii_digit() || chars[i] == '.') {
                    i += 1;
                }
                let n: f64 = s[start..i].parse().unwrap_or(0.0);
                tokens.push(Token::Number(n));
            }
            'a'..='z' | 'A'..='Z' | '_' => {
                let start = i;
                while i < chars.len() && (chars[i].is_ascii_alphanumeric() || chars[i] == '_' || chars[i] == '%') {
                    i += 1;
                }
                let word = &s[start..i];
                match word.to_uppercase().as_str() {
                    "AND" => tokens.push(Token::And),
                    "OR" => tokens.push(Token::Or),
                    "NOT" => tokens.push(Token::Not),
                    _ => tokens.push(Token::Ident(word.to_string())),
                }
            }
            _ => { i += 1; } // skip unknown
        }
    }
    tokens.push(Token::Eof);
    tokens
}

// ---------- AST ----------

#[derive(Debug, Clone)]
enum Expr {
    Number(f64),
    Ident(String),
    BinOp(Box<Expr>, Op, Box<Expr>),
    UnaryOp(UnOp, Box<Expr>),
    FuncCall(String, Vec<Expr>),
    Ternary(Box<Expr>, Box<Expr>, Box<Expr>),
}

#[derive(Debug, Clone)]
enum Op { Add, Sub, Mul, Div, Mod, Lt, Gt, Le, Ge, Eq, Ne, And, Or }

#[derive(Debug, Clone)]
enum UnOp { Neg, Not }

// ---------- Parser ----------

struct Parser {
    tokens: Vec<Token>,
    pos: usize,
}

impl Parser {
    fn new(tokens: Vec<Token>) -> Self { Parser { tokens, pos: 0 } }

    fn peek(&self) -> &Token { &self.tokens[self.pos] }

    fn advance(&mut self) -> Token {
        let t = self.tokens[self.pos].clone();
        self.pos += 1;
        t
    }

    fn expect(&mut self, tok: &Token) -> bool {
        if std::mem::discriminant(self.peek()) == std::mem::discriminant(tok) {
            self.pos += 1;
            return true;
        }
        false
    }

    // Lowest precedence: ternary (?:)
    fn parse_ternary(&mut self) -> Expr {
        let mut e = self.parse_or();
        if let Token::Question = self.peek() {
            self.advance();
            let then = self.parse_ternary();
            self.expect(&Token::Colon);
            let els = self.parse_ternary();
            e = Expr::Ternary(Box::new(e), Box::new(then), Box::new(els));
        }
        e
    }

    fn parse_or(&mut self) -> Expr {
        let mut e = self.parse_and();
        while let Token::Or = self.peek() {
            self.advance();
            let rhs = self.parse_and();
            e = Expr::BinOp(Box::new(e), Op::Or, Box::new(rhs));
        }
        e
    }

    fn parse_and(&mut self) -> Expr {
        let mut e = self.parse_comparison();
        while let Token::And = self.peek() {
            self.advance();
            let rhs = self.parse_comparison();
            e = Expr::BinOp(Box::new(e), Op::And, Box::new(rhs));
        }
        e
    }

    fn parse_comparison(&mut self) -> Expr {
        let e = self.parse_add_sub();
        match self.peek() {
            Token::Lt => { self.advance(); Expr::BinOp(Box::new(e), Op::Lt, Box::new(self.parse_add_sub())) }
            Token::Gt => { self.advance(); Expr::BinOp(Box::new(e), Op::Gt, Box::new(self.parse_add_sub())) }
            Token::Le => { self.advance(); Expr::BinOp(Box::new(e), Op::Le, Box::new(self.parse_add_sub())) }
            Token::Ge => { self.advance(); Expr::BinOp(Box::new(e), Op::Ge, Box::new(self.parse_add_sub())) }
            Token::Eq => { self.advance(); Expr::BinOp(Box::new(e), Op::Eq, Box::new(self.parse_add_sub())) }
            Token::Ne => { self.advance(); Expr::BinOp(Box::new(e), Op::Ne, Box::new(self.parse_add_sub())) }
            _ => e,
        }
    }

    fn parse_add_sub(&mut self) -> Expr {
        let mut e = self.parse_mul_div();
        loop {
            match self.peek() {
                Token::Plus => { self.advance(); e = Expr::BinOp(Box::new(e), Op::Add, Box::new(self.parse_mul_div())); }
                Token::Minus => { self.advance(); e = Expr::BinOp(Box::new(e), Op::Sub, Box::new(self.parse_mul_div())); }
                _ => break,
            }
        }
        e
    }

    fn parse_mul_div(&mut self) -> Expr {
        let mut e = self.parse_unary();
        loop {
            match self.peek() {
                Token::Star => { self.advance(); e = Expr::BinOp(Box::new(e), Op::Mul, Box::new(self.parse_unary())); }
                Token::Slash => { self.advance(); e = Expr::BinOp(Box::new(e), Op::Div, Box::new(self.parse_unary())); }
                Token::Percent => { self.advance(); e = Expr::BinOp(Box::new(e), Op::Mod, Box::new(self.parse_unary())); }
                _ => break,
            }
        }
        e
    }

    fn parse_unary(&mut self) -> Expr {
        match self.peek() {
            Token::Minus => { self.advance(); Expr::UnaryOp(UnOp::Neg, Box::new(self.parse_unary())) }
            Token::Not => { self.advance(); Expr::UnaryOp(UnOp::Not, Box::new(self.parse_unary())) }
            _ => self.parse_primary(),
        }
    }

    fn parse_primary(&mut self) -> Expr {
        match self.peek().clone() {
            Token::Number(n) => { self.advance(); Expr::Number(n) }
            Token::Ident(name) => {
                self.advance();
                if let Token::LParen = self.peek() {
                    self.advance();
                    let mut args = Vec::new();
                    if let Token::RParen = self.peek() {
                        self.advance();
                    } else {
                        args.push(self.parse_ternary());
                        while let Token::Comma = self.peek() {
                            self.advance();
                            args.push(self.parse_ternary());
                        }
                        self.expect(&Token::RParen);
                    }
                    Expr::FuncCall(name, args)
                } else {
                    Expr::Ident(name)
                }
            }
            Token::LParen => {
                self.advance();
                let e = self.parse_ternary();
                self.expect(&Token::RParen);
                e
            }
            _ => Expr::Number(0.0),
        }
    }
}

fn parse(s: &str) -> Expr {
    let tokens = tokenize(s);
    let mut parser = Parser::new(tokens);
    parser.parse_ternary()
}

// ---------- Evaluator ----------

fn eval_expr(expr: &Expr, bar_idx: usize, vars: &HashMap<String, Vec<f64>>, constants: &HashMap<String, f64>) -> f64 {
    match expr {
        Expr::Number(n) => *n,
        Expr::Ident(name) => {
            if let Some(val) = constants.get(name) {
                return *val;
            }
            if let Some(arr) = vars.get(name) {
                if bar_idx < arr.len() {
                    return arr[bar_idx];
                }
            }
            f64::NAN
        }
        Expr::BinOp(lhs, op, rhs) => {
            let l = eval_expr(lhs, bar_idx, vars, constants);
            let r = eval_expr(rhs, bar_idx, vars, constants);
            match op {
                Op::Add => l + r,
                Op::Sub => l - r,
                Op::Mul => l * r,
                Op::Div => if r != 0.0 { l / r } else { f64::NAN },
                Op::Mod => if r != 0.0 { l % r } else { f64::NAN },
                Op::Lt => if l < r { 1.0 } else { 0.0 },
                Op::Gt => if l > r { 1.0 } else { 0.0 },
                Op::Le => if l <= r { 1.0 } else { 0.0 },
                Op::Ge => if l >= r { 1.0 } else { 0.0 },
                Op::Eq => if (l - r).abs() < 1e-10 { 1.0 } else { 0.0 },
                Op::Ne => if (l - r).abs() >= 1e-10 { 1.0 } else { 0.0 },
                Op::And => if l != 0.0 && r != 0.0 { 1.0 } else { 0.0 },
                Op::Or => if l != 0.0 || r != 0.0 { 1.0 } else { 0.0 },
            }
        }
        Expr::UnaryOp(op, e) => {
            let v = eval_expr(e, bar_idx, vars, constants);
            match op {
                UnOp::Neg => -v,
                UnOp::Not => if v == 0.0 { 1.0 } else { 0.0 },
            }
        }
        Expr::FuncCall(name, args) => {
            let evaluated: Vec<f64> = args.iter().map(|a| eval_expr(a, bar_idx, vars, constants)).collect();
            match name.to_uppercase().as_str() {
                "ABS" => evaluated[0].abs(),
                "MIN" => evaluated.iter().cloned().fold(f64::INFINITY, f64::min),
                "MAX" => evaluated.iter().cloned().fold(f64::NEG_INFINITY, f64::max),
                "SUM" => evaluated.iter().sum(),
                "AVG" => { let s: f64 = evaluated.iter().sum(); s / evaluated.len() as f64 }
                "SQRT" => evaluated[0].sqrt(),
                "FLOOR" => evaluated[0].floor(),
                "CEIL" => evaluated[0].ceil(),
                "ROUND" => evaluated[0].round(),
                "SIGN" => evaluated[0].signum(),
                "IF" => if evaluated[0] != 0.0 { evaluated[1] } else { evaluated[2] },
                "LAG" => {
                    let n = evaluated.get(1).copied().unwrap_or(1.0) as usize;
                    if bar_idx >= n {
                        if let Expr::Ident(ref name) = args[0] {
                            if let Some(arr) = vars.get(name) {
                                if bar_idx - n < arr.len() {
                                    return arr[bar_idx - n];
                                }
                            }
                        }
                    }
                    0.0
                }
                "CROSSOVER" => {
                    // CROSSOVER(a, b) = 1 if a[t] > b[t] AND a[t-1] <= b[t-1]
                    if bar_idx == 0 { return 0.0; }
                    let a_t = eval_expr(&args[0], bar_idx, vars, constants);
                    let b_t = eval_expr(&args[1], bar_idx, vars, constants);
                    let a_prev = eval_expr(&args[0], bar_idx - 1, vars, constants);
                    let b_prev = eval_expr(&args[1], bar_idx - 1, vars, constants);
                    if a_t > b_t && a_prev <= b_prev { 1.0 } else { 0.0 }
                }
                "CROSSUNDER" => {
                    if bar_idx == 0 { return 0.0; }
                    let a_t = eval_expr(&args[0], bar_idx, vars, constants);
                    let b_t = eval_expr(&args[1], bar_idx, vars, constants);
                    let a_prev = eval_expr(&args[0], bar_idx - 1, vars, constants);
                    let b_prev = eval_expr(&args[1], bar_idx - 1, vars, constants);
                    if a_t < b_t && a_prev >= b_prev { 1.0 } else { 0.0 }
                }
                "ROLLING" => {
                    // ROLLING(var, period) = average of var over last N bars
                    let period = evaluated.get(1).copied().unwrap_or(5.0) as usize;
                    let start = if bar_idx + 1 >= period { bar_idx + 1 - period } else { 0 };
                    let mut sum = 0.0;
                    let mut count = 0;
                    for i in start..=bar_idx {
                        sum += eval_expr(&args[0], i, vars, constants);
                        count += 1;
                    }
                    if count > 0 { sum / count as f64 } else { 0.0 }
                }
                "STDDEV" => {
                    let period = evaluated.get(1).copied().unwrap_or(20.0) as usize;
                    let start = if bar_idx + 1 >= period { bar_idx + 1 - period } else { 0 };
                    let mut vals = Vec::new();
                    for i in start..=bar_idx {
                        vals.push(eval_expr(&args[0], i, vars, constants));
                    }
                    let n = vals.len() as f64;
                    let mean: f64 = vals.iter().sum::<f64>() / n;
                    let variance: f64 = vals.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / n;
                    variance.sqrt()
                }
                _ => 0.0,
            }
        }
        Expr::Ternary(cond, then_val, else_val) => {
            let c = eval_expr(cond, bar_idx, vars, constants);
            if c != 0.0 {
                eval_expr(then_val, bar_idx, vars, constants)
            } else {
                eval_expr(else_val, bar_idx, vars, constants)
            }
        }
    }
}

// ---------- Pure Rust API (testable without Python) ----------

/// Evaluate a formula expression over vectors of data.
/// Returns `Ok(Vec<f64>)` with one result per bar on success,
/// or `Err(String)` on parse/evaluation error.
pub fn eval_formula_inner(
    formula: &str,
    vars: HashMap<String, Vec<f64>>,
    constants: HashMap<String, f64>,
) -> Result<Vec<f64>, String> {
    let n = vars.values().next().map(|v| v.len()).unwrap_or(0);
    if n == 0 {
        return Ok(vec![]);
    }

    let expr = parse(formula);
    let mut results = Vec::with_capacity(n);
    for i in 0..n {
        results.push(eval_expr(&expr, i, &vars, &constants));
    }
    Ok(results)
}

/// Verify a formula string is syntactically valid (pure Rust).
pub fn validate_formula_inner(formula: &str) -> Result<bool, String> {
    let tokens = tokenize(formula);
    if tokens.is_empty() {
        return Ok(false);
    }
    let mut parser = Parser::new(tokens);
    let expr = parser.parse_ternary();
    Ok(matches!(&expr, Expr::Number(_) | Expr::Ident(_) | Expr::BinOp(..) | Expr::UnaryOp(..) | Expr::FuncCall(..) | Expr::Ternary(..)))
}

// ---------- Python API (thin wrappers) ----------

/// Evaluate a formula expression over vectors of data.
/// Returns a Vec<f64> with one result per bar.
///
/// `formula`: expression string like "rsi_14 < 30 AND close > sma_20"
/// `vars`: dict of variable_name -> Vec<f64> (indicator values, each must have same length)
///
/// Special vars: open, high, low, close, volume are automatically available.
/// `constants`: dict of constant values (optional, e.g. {"stop_pct": 2.0})
#[pyfunction]
pub fn eval_formula(
    formula: &str,
    vars: HashMap<String, Vec<f64>>,
    constants: HashMap<String, f64>,
) -> PyResult<Vec<f64>> {
    eval_formula_inner(formula, vars, constants)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e))
}

/// Verify a formula string is syntactically valid.
#[pyfunction]
pub fn validate_formula(formula: &str) -> PyResult<bool> {
    validate_formula_inner(formula)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_simple_arithmetic() {
        let mut vars = HashMap::new();
        vars.insert("close".to_string(), vec![10.0, 20.0, 30.0]);
        let result = eval_formula_inner("close * 2", vars.clone(), HashMap::new()).unwrap();
        assert_eq!(result, vec![20.0, 40.0, 60.0]);
    }

    #[test]
    fn test_comparison() {
        let mut vars = HashMap::new();
        vars.insert("rsi".to_string(), vec![25.0, 50.0, 75.0]);
        let result = eval_formula_inner("rsi < 30", vars.clone(), HashMap::new()).unwrap();
        assert_eq!(result, vec![1.0, 0.0, 0.0]);
    }

    #[test]
    fn test_and_or() {
        let mut vars = HashMap::new();
        vars.insert("rsi".to_string(), vec![25.0, 50.0, 75.0]);
        vars.insert("close".to_string(), vec![100.0, 100.0, 100.0]);
        let result = eval_formula_inner("rsi < 30 AND close > 50", vars, HashMap::new()).unwrap();
        assert_eq!(result, vec![1.0, 0.0, 0.0]);
    }

    #[test]
    fn test_ternary() {
        let mut vars = HashMap::new();
        vars.insert("rsi".to_string(), vec![25.0, 50.0, 75.0]);
        let result = eval_formula_inner("rsi < 30 ? -1 : (rsi > 70 ? 1 : 0)", vars, HashMap::new()).unwrap();
        assert_eq!(result, vec![-1.0, 0.0, 1.0]);
    }

    #[test]
    fn test_crossover() {
        let mut vars = HashMap::new();
        vars.insert("fast".to_string(), vec![1.0, 2.0, 3.0, 4.0]);
        vars.insert("slow".to_string(), vec![3.0, 3.0, 3.0, 3.0]);
        let result = eval_formula_inner("CROSSOVER(fast, slow)", vars, HashMap::new()).unwrap();
        // crossover at bar 3: fast[3]=4 > slow[3]=3 AND fast[2]=3 <= slow[2]=3
        assert_eq!(result, vec![0.0, 0.0, 0.0, 1.0]);
    }
}
