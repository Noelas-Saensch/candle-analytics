"""
Strategy Lab LLM Agent.

Watches /tmp/strategy_chat_req_*.json for new messages from the Strategy Lab,
calls Groq API (Llama 3.3 70B) and writes responses back.

Run in a screen session:
  screen -dmS agent python3 api/agent.py
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
logger = logging.getLogger("agent")

SKILL_PATH = os.path.join(os.path.dirname(__file__), "..", ".opencode", "skills", "strategy-designer", "SKILL.md")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = "qwen/qwen3-32b"  # Free tier, good for code generation
CHAT_LOG = "/tmp/strategy_chat_log.md"
POLL_INTERVAL = 1.0
HISTORY_LINES = 40
MAX_REQ_AGE_SECONDS = 300  # skip request files older than 5 minutes (stale tests)


def load_skill() -> str:
    with open(SKILL_PATH) as f:
        return f.read()


def build_system_prompt(skill: str) -> str:
    available = (
        "OC% (close-open)/open*100\n"
        "OH% (high-open)/open*100\n"
        "OL% (low-open)/open*100\n"
        "HL% (high-low)/open*100\n"
        "HC% (high-close)/open*100\n"
        "LC% (low-close)/open*100\n"
        "Vol% volume / max_volume * 100\n"
        "Pctl(OC%) percentile rank of OC%\n"
        "Pctl(OH%), Pctl(OL%), Pctl(HL%), Pctl(HC%), Pctl(LC%), Pctl(Vol%)\n\n"
        "Operators: gt (>), gte (>=), lt (<), lte (<=), eq (=), neq (!=)\n\n"
        "Each condition has a subcategory: 'threshold' (direct metric comparison) or 'pctl' (percentile rank).\n"
        "When subcategory is 'pctl', the metric gets a 'pctl_' prefix automatically."
    )
    template_schema = (
        "\n\nCONFIG UPDATE OUTPUT FORMAT — when the strategy is fully defined, respond with:\n"
        "{\"type\": \"config_update\", \"response\": {\n"
        "  \"name\": \"Strategy name (empty string OK)\",\n"
        "  \"exchange\": \"binance\",\n"
        "  \"symbol\": \"BTCUSDC\",\n"
        "  \"timeframe\": \"1H\",\n"
        "  \"leverage\": 1,\n"
        "  \"direction\": \"long_only\" | \"short_only\" | \"both\",\n"
        "  \"lookahead\": 5,\n"
        "  \"min_occurrences\": 10,\n"
        "  \"trades\": {\n"
        "    \"long\": [{\n"
        "      \"open\": {\n"
        "        \"conditions\": {\n"
        "          \"logic\": \"AND\",\n"
        "          \"groups\": [{\n"
        "            \"logic\": \"AND\",\n"
        "            \"conditions\": [{\"subcategory\": \"threshold\", \"metric\": \"oc\", \"op\": \"gt\", \"value\": 0.5}]\n"
        "          }]\n"
        "        },\n"
        "        \"orders\": [{\"type\": \"market\", \"size\": 1, \"size_type\": \"percent\", \"price\": null}]\n"
        "      },\n"
        "      \"close\": {\n"
        "        \"conditions\": {\"logic\": \"AND\", \"groups\": []},\n"
        "        \"orders\": [{\"type\": \"sl\", \"size\": 1, \"size_type\": \"percent\", \"price\": null}]\n"
        "      }\n"
        "    }],\n"
        "    \"short\": []\n"
        "  }\n"
        "}}\n"
        "ORDER TYPES: market, limit, stop_market, stop_limit, sl, tp, ts\n"
        "SIZE TYPES: percent, fixed, contracts\n"
        "Each trade has OPEN (entry) and CLOSE (exit) sections, each with conditions and orders.\n"
        "Multiple trades allow DCA-style scaling (multiple entries per direction).\n"
        "Each condition has subcategory: 'threshold' or 'pctl'. When pctl, metric gets pctl_ prefix.\n"
        "Fill all fields with defaults when not specified by the user."
    )
    return (
        "You are a trading strategy design assistant.\n\n"
        "USER DRIVES. You follow, collect, generate.\n\n"
        f"Strategy designer rules:\n{skill}\n\n"
        f"Available metrics:\n{available}\n\n"
        f"{template_schema}\n\n"
        "Output ONLY valid JSON. No markdown, no explanation."
    )


def read_history() -> list[dict]:
    """Parse the last N exchanges from the chat log for context."""
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
    return entries[-10:]  # max 10 exchanges


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def call_groq(messages: list[dict]) -> str | None:
    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set")
        return None
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
                "temperature": 0.7,
                "max_tokens": 1024,
            },
            timeout=30,
        )
        if resp.status_code == 401:
            logger.warning("Groq API: invalid API key")
            return None
        if resp.status_code == 429:
            logger.warning("Groq API: rate limited (429)")
            return None
        if resp.status_code != 200:
            logger.warning("Groq API returned %d: %s", resp.status_code, resp.text[:200])
            return None
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        logger.warning("Groq API: request timed out")
        return None
    except requests.exceptions.ConnectionError:
        logger.warning("Groq API: cannot reach api.groq.com")
        return None
    except Exception as e:
        logger.warning("Groq API error: %s", e)
        return None


def _normalize_response(data: dict) -> dict:
    """Fill missing fields in a config_update response."""
    if data.get("type") != "config_update":
        return data
    resp = data.get("response", data)
    resp.setdefault("name", "")
    resp.setdefault("exchange", "binance")
    resp.setdefault("symbol", "BTCUSDC")
    resp.setdefault("timeframe", "1H")
    resp.setdefault("leverage", 1)
    resp.setdefault("direction", "long_only")
    resp.setdefault("lookahead", 5)
    resp.setdefault("min_occurrences", 10)
    trades = resp.get("trades", {})
    if not isinstance(trades, dict):
        trades = {}
    trades.setdefault("long", [])
    trades.setdefault("short", [])
    if not trades["long"] and not trades["short"]:
        trades["long"] = [{
            "open": {"conditions": {"logic": "AND", "groups": [{"logic": "AND", "conditions": []}]}, "orders": [{"type": "market", "size": 1, "size_type": "percent", "price": None}]},
            "close": {"conditions": {"logic": "AND", "groups": []}, "orders": [{"type": "market", "size": 1, "size_type": "percent", "price": None}]},
        }]
    resp["trades"] = trades
    data["response"] = resp
    data.setdefault("content", "✓ Strategy loaded — review and edit in the config panel")
    return data


def parse_llm_output(raw: str) -> dict:
    """Try to parse JSON from LLM output, falling back to wrapping as message."""
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
        return _normalize_response(data)
    except (json.JSONDecodeError, ValueError):
        return {"type": "message", "content": raw}


def append_log(role: str, content: str, detail: str = ""):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    extra = f" ({detail})" if detail else ""
    with open(CHAT_LOG, "a") as f:
        f.write(f"\n## {ts} — {role}{extra}\n{content}\n")


def find_pending_requests(known: set) -> list[str]:
    now = time.time()
    all_files = glob.glob("/tmp/strategy_chat_req_*.json")
    # Filter: skip files older than MAX_REQ_AGE_SECONDS (stale test artifacts)
    fresh = []
    for f in all_files:
        try:
            age = now - os.path.getmtime(f)
            if age <= MAX_REQ_AGE_SECONDS:
                fresh.append(f)
            else:
                # Auto-clean stale files silently
                try:
                    os.remove(f)
                except OSError:
                    pass
        except OSError:
            pass
    # Newest first — user's latest message gets priority
    files = sorted(fresh, key=os.path.getmtime, reverse=True)
    return [f for f in files if f not in known]


def main():
    skill = load_skill()
    system_prompt = build_system_prompt(skill)
    known = set()

    logger.info("Agent started — watching /tmp/strategy_chat_req_*.json")
    logger.info("Model: %s (Groq), Poll interval: %.1fs", GROQ_MODEL, POLL_INTERVAL)

    while True:
        try:
            pending = find_pending_requests(known)
            # Process ONE file per cycle (newest first due to sort)
            if pending:
                req_path = pending[0]
                logger.info("Processing %s", os.path.basename(req_path))
                try:
                    with open(req_path) as f:
                        req = json.load(f)
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning("Skipping unreadable %s: %s", req_path, e)
                    known.add(req_path)

                req_id = req.get("id", "unknown")
                req_type = req.get("type", "message")
                content = req.get("content", "")

                if req_type == "deep_thinking":
                    config_str = json.dumps(req.get("config", {}), indent=2)
                    user_msg = (
                        f"Analyze this trading strategy critically. Give a score (1-10), "
                        f"strengths, weaknesses, and concrete recommendations.\n\n"
                        f"Strategy config:\n```json\n{config_str}\n```"
                    )
                elif req_type == "amelioration":
                    config_str = json.dumps(req.get("config", {}), indent=2)
                    results_str = json.dumps(req.get("results", {}), indent=2)
                    user_msg = (
                        f"Here are backtest results for a strategy. Suggest specific improvements "
                        f"based on actual performance data.\n\n"
                        f"Strategy config:\n```json\n{config_str}\n```\n\n"
                        f"Backtest results:\n```json\n{results_str}\n```"
                    )
                else:
                    user_msg = content

                # Build conversation
                history = read_history()
                messages = [
                    {"role": "system", "content": system_prompt},
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
                            "⚠️ Groq API is not responding. "
                            "Set GROQ_API_KEY or check console.groq.com"
                        ),
                    }
                else:
                    res = parse_llm_output(raw)

                # Write response
                res_path = f"/tmp/strategy_chat_res_{req_id}.json"
                with open(res_path, "w") as f:
                    json.dump(res, f)

                # Log
                log_body = res.get("response") or res.get("content", "")
                if len(log_body) > 500:
                    log_body = log_body[:500] + "..."
                append_log("Agent", log_body, detail=f"res_{req_id[:8]}")
                logger.info("Responded to %s", req_id[:8])

                # Cleanup
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
