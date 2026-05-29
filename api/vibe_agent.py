"""
Vibe Lab LLM Agent — generates strategy code via chat conversation.

Watches /tmp/vibe_chat_req_*.json for new messages, calls Groq API,
and writes response files back.

Run in a screen session:
  screen -dmS vibe-agent .venv/bin/python api/vibe_agent.py
"""

from dotenv import load_dotenv
load_dotenv(dotenv_path="/home/anymous/PROJETS/candle-analytics/.env")

import json
import os
import glob
import time
import logging
import re
import sys
import requests

# Ensure project root is on sys.path for api._lock import
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from api._lock import acquire_groq_lock, release_groq_lock

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("vibe_agent")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = "qwen/qwen3-32b"
CHAT_LOG = "/tmp/vibe_chat_log.md"
POLL_INTERVAL = 1.0
HISTORY_LINES = 40
MAX_REQ_AGE_SECONDS = 300

SYSTEM_PROMPT = """You are a trading strategy code generator. You converse with the user to understand their strategy, then generate Python code.

CORE RULES:
1. Guide the user step by step: market → conditions → entry → exit → risk
2. Ask clarifying questions when the user's description is vague
3. When the strategy is fully defined, generate the code
4. Output ONLY valid JSON. No markdown, no explanation outside the JSON.

AVAILABLE INDICATORS (from vibe_engine, import as 've'):
- ve.sma(values, period) -> array
- ve.ema(values, period) -> array
- ve.rsi(close, period=14) -> array
- ve.bbands(values, period=20, std_dev=2.0) -> (upper, middle, lower)
- ve.atr(high, low, close, period=14) -> array
- ve.macd(values, fast=12, slow=26, signal=9) -> (macd_line, signal_line, histogram)
- ve.stochastic(high, low, close, period=14) -> (k, d)
- ve.vwap(high, low, close, volume) -> array

SANDBOX FUNCTIONS (available in the strategy namespace):
- get_ohlcv(symbol, timeframe, limit=100) -> list[dict]
- get_price(symbol) -> float
- long(symbol, qty) -> dict
- short(symbol, qty) -> dict
- close_position(symbol) -> dict
- get_position(symbol) -> dict | None

DATA: ohlcv is a pd.DataFrame with columns: t, o, h, l, c, v

THE STRATEGY must define:
  def decide(i: int, ohlcv: pd.DataFrame) -> dict | None:
      ...
The decide() function is called on every bar i.
It should return {"action": "long"|"short"|"close"|"none", "size_pct": 100}
or None to do nothing.

RESPONSE FORMATS:

During conversation (not ready to generate):
{"type": "message", "content": "Your response text here"}

When generating final code:
{"type": "code_generated", "content": "Explanation text", "code": "full Python code", "description": "Brief strategy name"}

GENERATED CODE MUST:
- import vibe_engine as ve
- import pandas as pd
- define decide(i, ohlcv) that returns signal dicts or None
- use ohlcv['c'].values[:i+1] or similar to get price data up to current bar
- not use any external imports other than pandas and vibe_engine
- use simple bar-by-bar logic (no lookahead bias)
"""


def read_history() -> list[dict]:
    if not os.path.exists(CHAT_LOG):
        return []
    with open(CHAT_LOG) as f:
        lines = f.readlines()
    entries = []
    current_role = None
    current_text = []
    for line in lines[-HISTORY_LINES:]:
        m = re.match(r"^## .* — (User|OpenCode|Agent|→ Browser)", line)
        if m:
            if current_role and current_text:
                body = "".join(current_text).strip()
                if body and current_role in ("User",):
                    entries.append({"role": "user", "content": body})
                elif body and current_role in ("OpenCode", "Agent"):
                    entries.append({"role": "assistant", "content": body})
            current_role = m.group(1)
            current_text = []
        else:
            current_text.append(line)
    if current_role and current_text:
        body = "".join(current_text).strip()
        if body and current_role in ("User",):
            entries.append({"role": "user", "content": body})
        elif body and current_role in ("OpenCode", "Agent"):
            entries.append({"role": "assistant", "content": body})
    return entries[-10:]


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def call_groq(messages: list[dict]) -> str | None:
    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set")
        return None
    for attempt in range(3):
        try:
            resp = requests.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": messages,
                    "temperature": 0.4,
                    "max_tokens": 512,
                },
                timeout=60,
            )
            if resp.status_code == 401:
                logger.warning("Groq API: invalid API key")
                return None
            if resp.status_code == 429:
                logger.warning("Groq API: rate limited (attempt %d/3)", attempt + 1)
                time.sleep(2 ** attempt)
                continue
            if resp.status_code == 413:
                logger.warning("Groq API: request too large (413) — reduce history or max_tokens")
                return None
            if resp.status_code != 200:
                logger.warning("Groq API returned %d: %s", resp.status_code, resp.text[:200])
                if attempt < 2:
                    time.sleep(1)
                    continue
                return None
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            logger.warning("Groq API: request timed out (attempt %d/3)", attempt + 1)
            if attempt < 2:
                time.sleep(1)
                continue
            return None
        except requests.exceptions.ConnectionError:
            logger.warning("Groq API: cannot reach api.groq.com")
            return None
        except Exception as e:
            logger.warning("Groq API error: %s", e)
            return None
    return None


def parse_llm_output(raw: str) -> dict:
    raw = raw.strip()
    if '</think>' in raw:
        raw = re.sub(r'^<think>.*?</think>\s*', '', raw, flags=re.DOTALL)
    else:
        idx = raw.find('<think>')
        if idx >= 0:
            raw = ''
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("not a dict")
        if "type" not in data:
            data["type"] = "message"
        return data
    except (json.JSONDecodeError, ValueError):
        return {"type": "message", "content": raw}


def append_log(role: str, content: str, detail: str = ""):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    extra = f" ({detail})" if detail else ""
    with open(CHAT_LOG, "a") as f:
        f.write(f"\n## {ts} — {role}{extra}\n{content}\n")


def find_pending_requests(known: set) -> list[str]:
    now = time.time()
    all_files = glob.glob("/tmp/vibe_chat_req_*.json")
    fresh = []
    for f in all_files:
        try:
            age = now - os.path.getmtime(f)
            if age <= MAX_REQ_AGE_SECONDS:
                fresh.append(f)
            else:
                try:
                    os.remove(f)
                except OSError:
                    pass
        except OSError:
            pass
    files = sorted(fresh, key=os.path.getmtime, reverse=True)
    return [f for f in files if f not in known]


def main():
    known = set()
    logger.info("Vibe agent started — watching /tmp/vibe_chat_req_*.json")
    logger.info("Model: %s (Groq), Poll interval: %.1fs", GROQ_MODEL, POLL_INTERVAL)

    while True:
        try:
            pending = find_pending_requests(known)
            if pending:
                req_path = pending[0]
                logger.info("Processing %s", os.path.basename(req_path))
                try:
                    with open(req_path) as f:
                        req = json.load(f)
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning("Skipping unreadable %s: %s", req_path, e)
                    known.add(req_path)
                    time.sleep(POLL_INTERVAL)
                    continue

                req_id = req.get("id", "unknown")
                content = req.get("content", "")
                exchange = req.get("exchange", "binance")
                symbol = req.get("symbol", "BTCUSDC")
                timeframe = req.get("timeframe", "1H")

                user_msg = (
                    f"User is describing a strategy for {exchange}/{symbol} ({timeframe}).\n\n"
                    f"User message: {content}\n\n"
                    f"If the user has given enough detail to generate code, output a code_generated response. "
                    f"Otherwise, ask clarifying questions."
                )

                history = read_history()
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    *history,
                    {"role": "user", "content": user_msg},
                ]

                acquire_groq_lock()
                try:
                    raw = call_groq(messages)
                finally:
                    release_groq_lock()
                if raw is None:
                    res = {
                        "type": "message",
                        "content": (
                            "⚠️ Groq API error. "
                            "Check agent log or console.groq.com"
                        ),
                    }
                else:
                    res = parse_llm_output(raw)

                res_path = f"/tmp/vibe_chat_res_{req_id}.json"
                with open(res_path, "w") as f:
                    json.dump(res, f)

                log_body = res.get("code", res.get("content", ""))
                if len(str(log_body)) > 500:
                    log_body = str(log_body)[:500] + "..."
                append_log("Agent", log_body, detail=f"res_{req_id[:8]}")
                logger.info("Responded to %s", req_id[:8])

                try:
                    os.remove(req_path)
                except OSError:
                    pass
                known.add(req_path)

        except Exception as e:
            logger.error("Unexpected error: %s", e)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
