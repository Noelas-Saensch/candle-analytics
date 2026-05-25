"""
Strategy code validator — checks syntax, risk management, and required functions.
"""

import ast
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    has_decide: bool = False
    has_sl_tp: bool = False
    has_position_sizing: bool = False


def validate_strategy(code: str) -> ValidationResult:
    result = ValidationResult(valid=True)

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        result.valid = False
        result.errors.append(f"Syntax error: {e}")
        return result

    has_decide = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name == "decide":
                has_decide = True
                args = [arg.arg for arg in node.args.args]
                if "i" not in args or "ohlcv" not in args:
                    result.warnings.append("decide() should have signature (i, ohlcv)")
            if node.name in ("set_stop_loss", "set_take_profit"):
                result.has_sl_tp = True

    if not has_decide:
        result.errors.append("Missing required function: decide(i, ohlcv)")
        result.valid = False
    else:
        result.has_decide = True

    code_lower = code.lower()
    if "size_pct" not in code_lower:
        result.warnings.append("No position sizing (size_pct) found")
    else:
        result.has_position_sizing = True

    if "vibe_engine" not in code_lower:
        result.warnings.append("No vibe_engine indicators imported")

    dangerous = ["__import__", "eval(", "exec(", "open(", "os.", "subprocess", "shutil"]
    for d in dangerous:
        if d in code:
            result.errors.append(f"Security: {d} not allowed in strategy code")
            result.valid = False

    if result.valid and not result.errors:
        logger.info("Strategy validation passed (%d warnings)", len(result.warnings))

    return result
