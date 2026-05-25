"""
Strategy code generator — converts natural language → executable Python strategy.
"""

import json
import os
import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a trading strategy code generator. Output ONLY valid JSON.

Generate a Python trading strategy based on the user's description. The strategy will run
in a sandbox with these functions available:

INDICATORS (imported from vibe_engine):
- rsi(close, period=14) -> array
- sma(values, period) -> array
- ema(values, period) -> array
- bbands(values, period=20, std_dev=2.0) -> (upper, middle, lower)
- atr(high, low, close, period=14) -> array
- macd(values, fast=12, slow=26, signal=9) -> (macd_line, signal_line, histogram)
- stochastic(high, low, close, period=14) -> (k, d)
- vwap(high, low, close, volume) -> array

SANDBOX FUNCTIONS (available in strategy namespace):
- get_ohlcv(symbol, timeframe, limit=100) -> list[dict] (keys: t, o, h, l, c, v)
- get_metrics(symbol, timeframe, limit=100) -> list[dict] (keys: oc, oh, ol, hl, hc, lc, vol)
- long(symbol, qty) -> dict
- short(symbol, qty) -> dict
- close_position(symbol) -> dict
- get_position(symbol) -> dict | None
- get_price(symbol) -> float

DATA AVAILABLE:
- ohlcv: pd.DataFrame with columns t, o, h, l, c, v (already loaded at execution time)

The strategy must define a function `decide(i: int, ohlcv: pd.DataFrame) -> dict | None`
that returns a signal dict:
  {"action": "long"|"short"|"close"|"none", "size_pct": 100}

Output JSON format:
{
  "code": "full Python strategy code as a string",
  "description": "brief description of the strategy",
  "indicators_used": ["rsi", "sma"],
  "parameters": {"rsi_period": 14, "sma_fast": 10, "sma_slow": 30}
}
"""


def build_generation_prompt(description: str, exchange: str, symbol: str, timeframe: str) -> str:
    return f"""Generate a trading strategy for this description:

USER: {description}

Exchange: {exchange}
Symbol: {symbol}
Timeframe: {timeframe}

Output ONLY valid JSON with the code, description, indicators_used, and parameters fields.
The code must define a `decide(i, ohlcv)` function that returns signal dicts.
"""


def generate_via_groq(description: str, exchange: str, symbol: str, timeframe: str,
                       api_key: str | None = None) -> dict[str, Any] | None:
    """Call Groq API to generate strategy code from description."""
    import httpx

    key = api_key or os.environ.get("GROQ_API_KEY", "")
    if not key:
        logger.warning("GROQ_API_KEY not set, using template fallback")
        return None

    GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": "qwen/qwen3-32b",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_generation_prompt(description, exchange, symbol, timeframe)},
        ],
        "temperature": 0.3,
        "max_tokens": 4096,
    }

    for attempt in range(3):
        try:
            with httpx.Client(timeout=60) as client:
                resp = client.post(GROQ_URL, headers=headers, json=payload)

            if resp.status_code == 429:
                logger.warning("Groq rate limited (attempt %d/3)", attempt + 1)
                import time
                time.sleep(2 ** attempt)
                continue

            if resp.status_code != 200:
                logger.warning("Groq returned %d (attempt %d/3): %s",
                               resp.status_code, attempt + 1, resp.text[:300])
                if attempt < 2:
                    import time
                    time.sleep(1)
                    continue
                return None

            raw = resp.json()["choices"][0]["message"]["content"]
            raw = raw.strip()
            if '</think>' in raw:
                raw = re.sub(r'^<think>.*?</think>\s*', '', raw, flags=re.DOTALL)
            else:
                # Cut off mid-think: remove everything from <think> onward
                idx = raw.find('<think>')
                if idx >= 0:
                    raw = ''
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)
            if not raw.startswith('{'):
                logger.warning("Groq response not JSON (attempt %d/3): %s...", attempt + 1, raw[:200])
                if attempt < 2:
                    import time
                    time.sleep(1)
                    continue
                return None
            return json.loads(raw)

        except Exception as e:
            logger.warning("Generation error (attempt %d/3): %s", attempt + 1, e)
            if attempt < 2:
                import time
                time.sleep(1)
                continue
            return None

    return None


TEMPLATES: dict[str, str] = {
    "sma_crossover": """import pandas as pd
import vibe_engine as ve

FAST = {sma_fast}
SLOW = {sma_slow}

def decide(i, ohlcv):
    if i < SLOW:
        return None
    close = ohlcv['c'].values[:i+1]
    fast = ve.sma(close, FAST)
    slow = ve.sma(close, SLOW)
    if fast[-1] > slow[-1] and fast[-2] <= slow[-2]:
        return {{"action": "long", "size_pct": 100}}
    if fast[-1] < slow[-1] and fast[-2] >= slow[-2]:
        return {{"action": "close", "size_pct": 0}}
    return None
""",
    "rsi_oversold": """import pandas as pd
import vibe_engine as ve

RSI_PERIOD = {rsi_period}
OVERSOLD = {oversold}
OVERBOUGHT = {overbought}

def decide(i, ohlcv):
    if i < RSI_PERIOD + 1:
        return None
    close = ohlcv['c'].values[:i+1]
    r = ve.rsi(close, RSI_PERIOD)
    if r[-1] < OVERSOLD:
        return {{"action": "long", "size_pct": 100}}
    if r[-1] > OVERBOUGHT:
        return {{"action": "close", "size_pct": 0}}
    return None
""",
    "bb_mean_reversion": """import pandas as pd
import vibe_engine as ve

BB_PERIOD = {bb_period}
BB_STD = {bb_std}

def decide(i, ohlcv):
    if i < BB_PERIOD:
        return None
    close = ohlcv['c'].values[:i+1]
    upper, middle, lower = ve.bbands(close, BB_PERIOD, BB_STD)
    price = close[-1]
    if price < lower[-1]:
        return {{"action": "long", "size_pct": 100}}
    if price > upper[-1]:
        return {{"action": "close", "size_pct": 0}}
    return None
""",
    "macd_crossover": """import pandas as pd
import vibe_engine as ve

FAST = {macd_fast}
SLOW = {macd_slow}
SIGNAL = {macd_signal}

def decide(i, ohlcv):
    if i < SLOW + SIGNAL:
        return None
    close = ohlcv['c'].values[:i+1]
    macd_line, signal_line, hist = ve.macd(close, FAST, SLOW, SIGNAL)
    if hist[-1] > 0 and hist[-2] <= 0:
        return {{"action": "long", "size_pct": 100}}
    if hist[-1] < 0 and hist[-2] >= 0:
        return {{"action": "close", "size_pct": 0}}
    return None
""",
}


def generate_from_template(template_name: str, params: dict[str, int | float] | None = None) -> dict[str, Any]:
    if template_name not in TEMPLATES:
        return {"code": "", "description": "Unknown template", "indicators_used": [], "parameters": {}}

    defaults = {
        "sma_fast": 10, "sma_slow": 30,
        "rsi_period": 14, "oversold": 30, "overbought": 70,
        "bb_period": 20, "bb_std": 2.0,
        "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
    }
    p = {**defaults, **(params or {})}
    code = TEMPLATES[template_name].format(**p)

    return {
        "code": code,
        "description": template_name.replace("_", " ").title(),
        "indicators_used": [template_name.split("_")[0]],
        "parameters": p,
    }
