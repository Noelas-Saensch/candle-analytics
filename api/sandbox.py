"""
Strategy execution sandbox — runs generated strategy code in a restricted environment.
"""

import logging
import math
import sys
from io import StringIO
from contextlib import redirect_stdout

logger = logging.getLogger(__name__)


class StrategySandbox:
    def __init__(self, ohlcv: list[dict], metrics: list[dict] | None = None):
        import pandas as pd
        self.ohlcv = pd.DataFrame(ohlcv).rename(columns={
            "open": "o", "high": "h", "low": "l", "close": "c", "volume": "v", "timestamp": "t",
        })
        self.metrics = metrics or []
        self.position = None
        self.trades = []
        self.equity_curve = []
        self.balance = 10000.0
        self.peak = 10000.0
        self.current_idx = 0

    def _get_price(self, symbol: str | None = None) -> float:
        idx = self.current_idx
        if len(self.ohlcv) > 0 and 0 <= idx < len(self.ohlcv):
            return float(self.ohlcv["c"].iloc[idx])
        return float(self.ohlcv["c"].iloc[-1]) if len(self.ohlcv) > 0 else 0.0

    def _get_ohlcv(self, symbol: str | None = None, timeframe: str | None = None, limit: int = 100) -> list[dict]:
        start = max(0, self.current_idx - limit + 1)
        return self.ohlcv.iloc[start:self.current_idx + 1].to_dict("records")

    def _get_metrics(self, symbol: str | None = None, timeframe: str | None = None, limit: int = 100) -> list[dict]:
        if self.metrics:
            return self.metrics[-limit:]
        return []

    def _long(self, symbol: str, qty: float) -> dict:
        price = self._get_price(symbol)
        self.position = {"side": "long", "qty": qty, "entry": price}
        return {"status": "ok", "action": "long", "qty": qty, "price": price}

    def _short(self, symbol: str, qty: float) -> dict:
        price = self._get_price(symbol)
        self.position = {"side": "short", "qty": qty, "entry": price}
        return {"status": "ok", "action": "short", "qty": qty, "price": price}

    def _close_position(self, symbol: str) -> dict:
        if self.position is None:
            return {"status": "ok", "action": "close", "reason": "no_position"}
        exit_price = self._get_price(symbol)
        if self.position["side"] == "long":
            pnl = (exit_price - self.position["entry"]) / self.position["entry"] * 100
        else:
            pnl = (self.position["entry"] - exit_price) / self.position["entry"] * 100
        trade = {**self.position, "exit": exit_price, "pnl_pct": pnl, "pnl_usd": self.position["qty"] * pnl / 100}
        self.trades.append(trade)
        self.balance += trade["pnl_usd"]
        self.position = None
        return {"status": "ok", "action": "close", "pnl_pct": pnl}

    def _get_position(self, symbol: str) -> dict | None:
        return self.position

    def run(self, code: str) -> dict:
        local_vars = {
            "pd": __import__("pandas"),
            "np": __import__("numpy"),
            "ve": __import__("vibe_engine"),
        }

        sandbox_funcs = {
            "get_ohlcv": self._get_ohlcv,
            "get_metrics": self._get_metrics,
            "get_price": self._get_price,
            "long": self._long,
            "short": self._short,
            "close_position": self._close_position,
            "get_position": self._get_position,
        }
        local_vars.update(sandbox_funcs)

        try:
            exec(code, local_vars)
        except Exception as e:
            return {"error": f"Execution error: {e}", "trades": [], "equity_curve": [], "balance": self.balance}

        if "decide" not in local_vars:
            return {"error": "No decide() function found", "trades": [], "equity_curve": [], "balance": self.balance}

        decide = local_vars["decide"]
        n = len(self.ohlcv)
        self.equity_curve.append({"step": 0, "balance": self.balance, "equity": self.balance, "position": 0})

        for i in range(1, n):
            self.current_idx = i
            try:
                ohlcv_slice = self.ohlcv.iloc[:i + 1]
                signal = decide(i, ohlcv_slice)
            except Exception as e:
                logger.debug("decide() error at %d: %s", i, e)
                continue

            if signal and isinstance(signal, dict):
                action = signal.get("action", "none")
                size_pct = signal.get("size_pct", 0)
                qty = self.balance * size_pct / 100.0 / self._get_price()

                if action == "long" and self.position is None:
                    self._long("", qty)
                elif action == "short" and self.position is None:
                    self._short("", qty)
                elif action == "close" and self.position is not None:
                    self._close_position("")

            equity = self.balance
            if self.position:
                price = self._get_price()
                if self.position["side"] == "long":
                    unrealized = (price - self.position["entry"]) / self.position["entry"] * self.position["qty"]
                else:
                    unrealized = (self.position["entry"] - price) / self.position["entry"] * self.position["qty"]
                equity += unrealized / 100 * self.balance

            self.equity_curve.append({
                "step": i, "balance": self.balance, "equity": equity, "position": 1 if self.position else 0,
            })

            if equity > self.peak:
                self.peak = equity

        metrics = self._compute_metrics()
        return {
            "trades": self.trades,
            "equity_curve": self.equity_curve,
            "final_balance": self.balance,
            "total_trades": len(self.trades),
            "metrics": metrics,
            "error": None,
        }

    def _compute_metrics(self) -> dict:
        if len(self.equity_curve) < 2:
            return _empty_metrics()

        equity_vals = [e["equity"] for e in self.equity_curve]
        returns = []
        for i in range(1, len(equity_vals)):
            prev = equity_vals[i - 1]
            if prev != 0:
                returns.append((equity_vals[i] - prev) / prev)

        if not returns:
            return _empty_metrics()

        n = len(returns)
        avg_ret = sum(returns) / n
        variance = sum((r - avg_ret) ** 2 for r in returns) / max(n - 1, 1)
        std = math.sqrt(variance)

        sharpe = (avg_ret / std * math.sqrt(252)) if std > 0 else 0.0

        total_ret = (equity_vals[-1] - equity_vals[0]) / equity_vals[0] * 100

        wins = [r for r in returns if r > 0]
        losses = [r for r in returns if r <= 0]
        win_rate = len(wins) / n * 100 if n else 0
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        profit_factor = abs(sum(wins) / sum(losses)) if sum(losses) != 0 else (float("inf") if sum(wins) > 0 else 0)

        peak = equity_vals[0]
        max_dd = 0.0
        max_dd_dur = 0
        dur = 0
        for v in equity_vals:
            if v > peak:
                peak = v
                dur = 0
            dd = (peak - v) / peak * 100 if peak else 0
            if dd > max_dd:
                max_dd = dd
            if dd > 1:
                dur += 1
                max_dd_dur = max(max_dd_dur, dur)
            else:
                dur = 0

        downside = [r for r in returns if r < 0]
        down_var = sum((r - avg_ret) ** 2 for r in downside) / max(len(downside), 1) if downside else 0
        down_std = math.sqrt(down_var)
        sortino = (avg_ret / down_std * math.sqrt(252)) if down_std > 0 else 0.0
        calmar = (avg_ret * 252 / max_dd * 100) if max_dd > 0 else 0.0

        max_consec_wins = 0
        max_consec_losses = 0
        cur_wins = 0
        cur_losses = 0
        for r in returns:
            if r > 0:
                cur_wins += 1
                cur_losses = 0
                max_consec_wins = max(max_consec_wins, cur_wins)
            else:
                cur_losses += 1
                cur_wins = 0
                max_consec_losses = max(max_consec_losses, cur_losses)

        return {
            "total_return_pct": round(total_ret, 4),
            "sharpe": round(sharpe, 4),
            "sortino": round(sortino, 4),
            "calmar": round(calmar, 4),
            "max_drawdown_pct": round(max_dd, 4),
            "max_drawdown_duration": max_dd_dur,
            "win_rate": round(win_rate, 2),
            "avg_return": round(avg_ret * 100, 4),
            "avg_win_pct": round(avg_win * 100, 4),
            "avg_loss_pct": round(avg_loss * 100, 4),
            "profit_factor": round(profit_factor, 4) if isinstance(profit_factor, float) else profit_factor,
            "total_trades": len(self.trades),
            "max_consecutive_wins": max_consec_wins,
            "max_consecutive_losses": max_consec_losses,
            "final_balance": round(self.balance, 2),
        }


def _empty_metrics() -> dict:
    return {
        "total_return_pct": 0, "sharpe": 0, "sortino": 0, "calmar": 0,
        "max_drawdown_pct": 0, "max_drawdown_duration": 0, "win_rate": 0,
        "avg_return": 0, "avg_win_pct": 0, "avg_loss_pct": 0,
        "profit_factor": 0, "total_trades": 0,
        "max_consecutive_wins": 0, "max_consecutive_losses": 0,
        "final_balance": 0,
    }
