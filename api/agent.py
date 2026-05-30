"""
Strategy Lab LLM Agent.

Watches /tmp/strategy_chat_req_*.json for new messages from the Strategy Lab,
calls Groq API (Llama 3.3 70B) and writes responses back.

Run in a screen session:
  screen -dmS agent .venv/bin/python api/agent.py
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
GROQ_MODEL = "qwen/qwen3-32b"  # Supports JSON mode on Groq free tier
CHAT_LOG = "/tmp/strategy_chat_log.md"
POLL_INTERVAL = 1.0
HISTORY_LINES = 10
MAX_PROMPT_CHARS = 6000  # max total chars for system + history (leaves room for overhead)
MAX_HISTORY_ENTRY_CHARS = 600  # truncate each history entry to this
MAX_REQ_AGE_SECONDS = 300  # skip request files older than 5 minutes (stale tests)


def load_skill() -> str:
    with open(SKILL_PATH) as f:
        return f.read()


def _load_custom_types_summary() -> str:
    """Build a compact summary of available custom types for the system prompt."""
    try:
        from custom_types.registry import load_custom_types
        types = load_custom_types()
        max_chars = 1500
        parts = []
        order_types_list = types.get("order_types", [])
        parts.append("\n\n=== ORDER TYPES ===\n")
        for o in order_types_list[:10]:
            parts.append(f"{o['id']} ")
        inds = types.get("custom_indicators", [])
        parts.append(f"\n=== INDICATORS ({len(inds)} avail) ===\n")
        for ind in inds[:8]:
            parts.append(f"{ind['id']} ")
        conds = types.get("custom_conditions", [])
        if conds:
            parts.append(f"\n=== CUSTOM CONDITIONS ===\n")
            for c in conds[:5]:
                parts.append(f"{c['id']} ")
        cdls = types.get("cdl_patterns", [])
        if cdls:
            parts.append(f"\n=== CANDLESTICK PATTERNS ({len(cdls)} avail) ===\n")
            for c in cdls[:5]:
                parts.append(f"{c['id']} ")
        summary = "".join(parts)
        if len(summary) > max_chars:
            summary = summary[:max_chars] + "..."
        return summary
    except Exception:
        return ""


PROMPT_CATEGORIES = {
    "core": (
        "You are a trading strategy design assistant. User drives — you follow, collect, generate.\n"
        "Rules: don't ask unnecessary questions. Group unknowns. Infer AND/OR from language. Use defaults silently (RSI→14, SL→1%). "
        "Generate as soon as exchange+pair+TF+1 condition known. Set ready:true only when ALL fields present including close conditions.\n"
        "CRITICAL: ALWAYS include BOTH open AND close in EVERY trade. Fill defaults when user omits.\n"
        "Respond in user's language. Output ONLY valid JSON. No markdown, no explanation.\n"
    ),
    "metrics": (
        "Metrics (use as condition.metric):\n"
        "OC% (close-open)/open*100, OH%, OL%, HL%, HC%, LC%, Vol% volume/max*100\n"
        "Pctls: prefix metric with 'pctl_' (e.g. pctl_oc). Operators: gt/gte/lt/lte/eq/neq\n"
        "subcategory: 'threshold' or 'pctl'\n"
    ),
    "indicators": (
        "Pre-computed indicators (use as condition.metric, value can be NUMBER or metric name):\n"
        "  rsi_14, sma_10, sma_20, sma_50, sma_200, ema_12, ema_26\n"
        "  bbands_20_2, atr_14, macd_12_26_9, stoch_14, vwap, adx_14, cci_20, mfi_14, williams_r_14, obv\n"
        "  ichimoku_tenkan_9 (alias: tenkan), ichimoku_kijun_26 (kijun)\n"
        "  ichimoku_senkou_a (senkou_a), ichimoku_senkou_b (senkou_b), ichimoku_chikou_26 (chikou)\n"
    ),
    "conditions_rules": (
        "CONDITION RULES:\n"
        "- IMPORTANT: Use CANONICAL metric names ONLY from the list below. Never invent names like 'ichimoku_conversion_line' or 'ichimoku_a'. Use: ichimoku_tenkan_9, ichimoku_kijun_26, ichimoku_senkou_a, ichimoku_senkou_b, ichimoku_chikou_26.\n"
        "- NEVER leave conditions partial. If a rule says 'above all lines', generate ALL 4 comparisons (close > tenkan, kijun, senkou_a, senkou_b AND lagging_span > tenkan, kijun, senkou_a, senkou_b). Always complete every group.\n"
        "- value: NUMBER for thresholds (e.g. value:30), or metric/indicator name for cross-comparison (e.g. value:\"ichimoku_tenkan_9\")\n"
        "- Threshold: {\"metric\":\"rsi_14\",\"op\":\"lt\",\"value\":30}\n"
        "- Cross-indicator: {\"metric\":\"close\",\"op\":\"gt\",\"value\":\"ichimoku_tenkan_9\"}\n"
        "- Cross-indicator: {\"metric\":\"ichimoku_tenkan_9\",\"op\":\"gt\",\"value\":\"ichimoku_kijun_26\"}\n"
        "Available metrics: oc, oh, ol, hl, hc, lc, vol, close, high, low, open, "
        "rsi_14, sma_10, sma_20, sma_50, sma_200, ema_12, ema_26, bbands_20_2, atr_14, "
        "macd_12_26_9, stoch_14, vwap, adx_14, cci_20, mfi_14, williams_r_14, obv,\n"
        "ichimoku_tenkan_9, ichimoku_kijun_26, ichimoku_senkou_a, ichimoku_senkou_b, ichimoku_chikou_26\n"
    ),
    "orders": (
        "ORDER TYPES: market, limit, stop_market, stop_limit, sl, tp, ts.\n"
        "SIZE TYPES: percent, fixed, contracts.\n"
    ),
    "output_format": (
        "Output formats:\n"
        "1) While collecting: {\"type\": \"message\", \"content\": \"your text here\"}\n"
        "2) Strategy ready: {\"type\": \"config_update\", \"ready\": true/false, \"content\": \"text\", \"response\": {\n"
        "  \"name\": \"\", \"exchange\": \"binance\", \"symbol\": \"BTCUSDC\", \"timeframe\": \"1H\", \"leverage\": 1,\n"
        "  \"direction\": \"long_only|short_only|both\", \"lookahead\": 5, \"min_occurrences\": 10, \"mc_shuffles\": 500,\n"
        "  \"walk_forward\": true, \"walk_windows\": 5, \"walk_train_pct\": 0.7, \"start_time\": null, \"end_time\": null,\n"
        "  \"custom_orders\": [], \"custom_indicators\": [], \"custom_conditions\": [],\n"
        "  \"trades\": {\"long\": [{\"open\": {\"conditions\": {\"logic\":\"AND\",\"groups\":[{\"logic\":\"AND\",\"conditions\":[{\"subcategory\":\"threshold\",\"metric\":\"rsi_14\",\"op\":\"lt\",\"value\":30}]}]},\"orders\":[{\"type\":\"market\",\"size\":1,\"size_type\":\"percent\",\"price\":null}]},\"close\":{\"conditions\":{\"logic\":\"AND\",\"groups\":[{\"logic\":\"AND\",\"conditions\":[{\"subcategory\":\"threshold\",\"metric\":\"rsi_14\",\"op\":\"gte\",\"value\":70}]}]},\"orders\":[{\"type\":\"market\",\"size\":1,\"size_type\":\"percent\",\"price\":null}]}}]}}\n"
        "  NOTE: Only output 'trades.long'. The system will automatically mirror to 'trades.short' with inverted operators when the user asks for both sides.\n"
        "  Leave 'short' as empty array []. Do NOT generate trades.short yourself.\n"
        "}}\n"
    ),
    "custom_types": _load_custom_types_summary(),
}


def _select_categories(user_message: str) -> list[str]:
    msg = user_message.lower()
    keys = ["core", "output_format"]
    indicator_kw = ["rsi", "sma", "ema", "bb", "ichimoku", "indicator", "stoch",
                    "macd", "adx", "atr", "mfi", "williams", "cci", "vwap", "obv",
                    "cross", "tenkan", "kijun", "senkou", "chikou"]
    order_kw = ["stop", "limit", "order", "sl", "tp", "trailing", "entry", "exit"]
    condition_kw = ["buy", "sell", "entry", "exit", "condition", "gt", "lt",
                    "cross", "above", "below", "overbought", "oversold"]
    if any(w in msg for w in indicator_kw):
        keys.append("indicators")
        keys.append("conditions_rules")
    if any(w in msg for w in condition_kw):
        keys.append("conditions_rules")
    if any(w in msg for w in order_kw):
        keys.append("orders")
        keys.append("conditions_rules")
    if any(w in msg for w in ["custom", "strategy", "template"]):
        keys.append("custom_types")
    keys.append("metrics")
    return list(dict.fromkeys(keys))


def build_system_prompt(user_message: str = "") -> str:
    categories = _select_categories(user_message)
    parts = [PROMPT_CATEGORIES[k] for k in categories if PROMPT_CATEGORIES.get(k)]
    prompt = "\n".join(parts)
    # Also include custom types even if not requested
    if "custom_types" not in categories and PROMPT_CATEGORIES.get("custom_types", "").strip():
        prompt += "\n" + PROMPT_CATEGORIES["custom_types"]
    HARD_MAX = 4500
    if len(prompt) > HARD_MAX:
        prompt = prompt[:HARD_MAX] + "\n...(truncated)"
    return prompt


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
                if len(body) > MAX_HISTORY_ENTRY_CHARS:
                    body = body[:MAX_HISTORY_ENTRY_CHARS] + "..."
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
        if len(body) > MAX_HISTORY_ENTRY_CHARS:
            body = body[:MAX_HISTORY_ENTRY_CHARS] + "..."
        if body and current_role in ("User",):
            entries.append({"role": "user", "content": body})
        elif body and current_role in ("OpenCode", "Agent"):
            entries.append({"role": "assistant", "content": body})
    return entries[-10:]  # max 10 exchanges


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def call_groq(messages: list[dict]) -> tuple[str | None, str | None]:
    """
    Returns (content, error_msg).
    - content: the LLM response text, or None on failure
    - error_msg: user-facing explanation of the failure, or None if success
    """
    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set")
        return None, "GROQ_API_KEY manquante dans .env. Ajoute ta clé API Groq."
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
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "response_format": {"type": "json_object"},
                },
                timeout=30,
            )
            if resp.status_code == 401:
                logger.warning("Groq API: invalid API key")
                return None, "Clé API Groq invalide (401). Vérifie GROQ_API_KEY dans .env."
            if resp.status_code == 429:
                logger.warning("Groq API: rate limited (429), attempt %d/3", attempt + 1)
                if attempt < 2:
                    time.sleep((attempt + 1) * 2)
                    continue
                return None, "Limite de taux Groq atteinte (429). Attends une minute avant de réessayer."
            if resp.status_code == 413:
                logger.warning("Groq API: request too large (413) — reduce history or max_tokens")
                return None, "Requête trop volumineuse (413). Le système prompt + historique dépasse la limite Groq. Réessaie avec un message plus court."
            if resp.status_code != 200:
                logger.warning("Groq API returned %d: %s", resp.status_code, resp.text[:200])
                return None, f"Erreur Groq API ({resp.status_code}). Consulte les logs de l'agent."
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            if not content or not content.strip():
                logger.warning("Groq API returned empty content")
                return content, "L'IA a répondu vide. Le modèle a peut-être atteint sa limite de tokens. Réessaie avec une description plus courte."
            return content, None
        except requests.exceptions.Timeout:
            logger.warning("Groq API: request timed out, attempt %d/3", attempt + 1)
            if attempt < 2:
                time.sleep((attempt + 1) * 2)
                continue
            return None, "L'appel Groq a expiré (timeout 30s). Le serveur est peut-être surchargé. Réessaie."
        except requests.exceptions.ConnectionError:
            logger.warning("Groq API: cannot reach api.groq.com")
            return None, "Impossible de joindre l'API Groq (api.groq.com). Vérifie ta connexion Internet."
        except Exception as e:
            logger.warning("Groq API error: %s", e)
            return None, f"Erreur inattendue de l'API Groq : {e}"
    return None, "L'appel Groq a échoué après 3 tentatives. Réessaie plus tard."


def _persist_custom_types(resp: dict):
    """Save AI-generated custom types to custom_types/ai_generated.json."""
    custom_orders = resp.get("custom_orders") or []
    custom_indicators = resp.get("custom_indicators") or []
    custom_conditions = resp.get("custom_conditions") or []
    if not (custom_orders or custom_indicators or custom_conditions):
        return
    try:
        path = os.path.join(os.path.dirname(__file__), "..", "custom_types", "ai_generated.json")
        existing = {"orders": [], "indicators": [], "conditions": []}
        if os.path.exists(path):
            with open(path) as f:
                existing = json.load(f)
        if custom_orders:
            existing.setdefault("orders", []).extend(custom_orders)
        if custom_indicators:
            existing.setdefault("indicators", []).extend(custom_indicators)
        if custom_conditions:
            existing.setdefault("conditions", []).extend(custom_conditions)
        with open(path, "w") as f:
            json.dump(existing, f, indent=2)
        logger.info("Persisted %d orders, %d indicators, %d conditions to %s",
                     len(custom_orders), len(custom_indicators), len(custom_conditions), path)
    except Exception as e:
        logger.warning("Failed to persist custom types: %s", e)


def _normalize_response(data: dict) -> dict:
    """Fill missing fields in a config_update response."""
    if data.get("type") != "config_update":
        return data
    resp = data.get("response", data)
    if not isinstance(resp, dict):
        # LLM returned a string in the "response" field instead of a config object
        data["type"] = "message"
        data["content"] = str(resp)
        return data
    resp.setdefault("name", "")
    resp.setdefault("exchange", "binance")
    resp.setdefault("symbol", "BTCUSDC")
    resp.setdefault("timeframe", "1H")
    resp.setdefault("leverage", 1)
    resp.setdefault("direction", "long_only")
    resp.setdefault("lookahead", 5)
    resp.setdefault("min_occurrences", 10)
    resp.setdefault("mc_shuffles", 500)
    resp.setdefault("walk_forward", True)
    resp.setdefault("walk_windows", 5)
    resp.setdefault("walk_train_pct", 0.7)
    resp.setdefault("start_time", None)
    resp.setdefault("end_time", None)
    trades = resp.get("trades", {})
    if not isinstance(trades, dict):
        trades = {}
    trades.setdefault("long", [])
    trades.setdefault("short", [])
    if not trades["long"] and not trades["short"]:
        trades["long"] = [{
            "open": {"conditions": {"logic": "AND", "groups": [{"logic": "AND", "conditions": [{"subcategory": "threshold", "metric": "oc", "op": "gt", "value": 0.2}]}]}, "orders": [{"type": "market", "size": 1, "size_type": "percent", "price": null}]},
            "close": {"conditions": {"logic": "AND", "groups": [{"logic": "AND", "conditions": [{"subcategory": "threshold", "metric": "oc", "op": "gte", "value": 1.5}]}]}, "orders": [{"type": "sl", "size": 1, "size_type": "percent", "price": 1.0}, {"type": "tp", "size": 1, "size_type": "percent", "price": 2.5}]},
        }]

    # Mirror long → short when short is empty but long has conditions
    _has_short_conds = any(
        c.get("conditions", {}).get("groups")
        for t in trades.get("short", [])
        for section in ("open", "close")
        for g in t.get(section, {}).get("conditions", {}).get("groups", [])
        if g.get("conditions")
    )
    if trades["long"] and not _has_short_conds:
        import copy
        OP_INVERT = {"gt": "lt", "lt": "gt", "gte": "lte", "lte": "gte", "eq": "eq", "neq": "neq"}
        def _invert_cond(c):
            c = copy.deepcopy(c)
            c["op"] = OP_INVERT.get(c.get("op", "gt"), "gt")
            return c
        def _invert_section(s):
            s = copy.deepcopy(s)
            conds = s.get("conditions", {})
            for g in conds.get("groups", []):
                g["conditions"] = [_invert_cond(c) for c in g.get("conditions", [])]
            return s
        trades["short"] = [{
            "open": _invert_section(t.get("open", {})),
            "close": _invert_section(t.get("close", {})),
        } for t in trades["long"]]
    resp["trades"] = trades
    # Persist any custom types to disk
    _persist_custom_types(resp)
    # Safety: never set ready:true if strategy has no close conditions
    has_close = False
    for side in ("long", "short"):
        for t in trades.get(side, []):
            c = t.get("close", {})
            g = c.get("conditions", {}).get("groups", [])
            if g and any(conds.get("conditions") for conds in g):
                has_close = True
    if not has_close:
        data["ready"] = False
    data.setdefault("content", "✓ Strategy loaded — review and edit in the config panel")
    return data


def parse_llm_output(raw: str) -> dict:
    """Try to parse JSON from LLM output, falling back to wrapping as message."""
    raw = raw.strip()
    if not raw:
        logger.warning("LLM returned empty response — possible token limit or context overflow")
        return {"type": "message", "content": "⚠️ L'IA n'a pas pu générer de configuration. Le modèle a peut-être atteint sa limite de tokens. Réessaie avec une description plus courte ou simplifie ta stratégie."}
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
        pass
    # Retry with regex extraction: find the outermost JSON object
    brace_start = raw.find('{')
    if brace_start >= 0:
        depth = 0
        for i in range(brace_start, len(raw)):
            if raw[i] == '{':
                depth += 1
            elif raw[i] == '}':
                depth -= 1
                if depth == 0:
                    try:
                        data = json.loads(raw[brace_start:i+1])
                        if isinstance(data, dict):
                            if "type" not in data:
                                data["type"] = "message"
                            return _normalize_response(data)
                    except (json.JSONDecodeError, ValueError):
                        pass
                    break
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
    system_prompt = build_system_prompt()
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
                    {"role": "user", "content": user_msg + "\n\nRespond with valid JSON."},
                ]
                # Estimate total size and trim history from oldest if too large
                total_chars = sum(len(m.get("content", "")) for m in messages)
                while total_chars > MAX_PROMPT_CHARS and len(messages) > 2:
                    # Remove the oldest history entry (index 1, after system)
                    rm = messages.pop(1)
                    total_chars -= len(rm.get("content", ""))

                # Try up to 2 times on truncation/malformed output
                res = None
                for attempt in range(2):
                    acquire_groq_lock()
                    try:
                        raw, error_msg = call_groq(messages)
                    finally:
                        release_groq_lock()
                    if raw is None:
                        error_text = error_msg or "Erreur inconnue de l'API Groq. Vérifie les logs."
                        logger.warning("Groq error for %s: %s", req_id[:8], error_text)
                        res = {"type": "message", "content": f"⚠️ {error_text}"}
                        append_log("Agent", f"[ERROR] {error_text}", detail=f"res_{req_id[:8]}")
                        break
                    res = parse_llm_output(raw)
                    # If the output looks like a truncated config_update, retry with simpler prompt
                    is_message = res.get("type") == "message"
                    looks_truncated = (
                        is_message
                        and ("config_update" in res.get("content", "") or '"response"' in res.get("content", ""))
                    )
                    if looks_truncated and attempt == 0:
                        logger.warning("Output looks truncated, retry %s with simpler prompt", req_id[:8])
                        # Append a stronger instruction for the retry
                        messages.append({"role": "assistant", "content": raw[:500]})
                        messages.append({"role": "user", "content": "Your previous response was too long and got truncated. Output ONLY valid JSON without markdown. Keep the strategy config SHORT — max 3 conditions total. Use ONLY 'oc','oh','ol','hl','hc','lc','vol','rsi_14' as metrics. Value MUST be a number."})
                        continue
                    break

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
