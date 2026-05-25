"""
Backtest results analyzer — LLM evaluates strategy performance and suggests improvements.
"""

import json
import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    score: float
    summary: str
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    suggestions: list[dict] = field(default_factory=list)


ANALYSIS_PROMPT = (
    "You are a trading strategy analyst. Evaluate the backtest results below.\n\n"
    "Score from 1-10 based on: risk-adjusted returns, consistency, drawdown control, win rate.\n"
    "Output ONLY valid JSON with fields: score, summary, strengths, weaknesses, recommendations.\n\n"
    "Backtest Results:\n{results}\n\n"
    "Strategy Code:\n{code}\n"
)


def analyze_results(results: dict, code: str, api_key: str | None = None) -> AnalysisResult:
    key = api_key or os.environ.get("GROQ_API_KEY", "")
    if not key:
        return _fallback_analysis(results)

    import httpx
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": "qwen/qwen3-32b",
                    "messages": [
                        {"role": "system", "content": ANALYSIS_PROMPT.format(
                            results=json.dumps(results, indent=2, default=str)[:3000],
                            code=code[:2000],
                        )},
                        {"role": "user", "content": "Analyze these backtest results."},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 1024,
                },
            )
        if resp.status_code == 200:
            raw = resp.json()["choices"][0]["message"]["content"]
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(raw)
            return AnalysisResult(
                score=data.get("score", 5),
                summary=data.get("summary", ""),
                strengths=data.get("strengths", []),
                weaknesses=data.get("weaknesses", []),
                recommendations=data.get("recommendations", []),
            )
    except Exception as e:
        logger.warning("Analysis LLM call failed: %s", e)

    return _fallback_analysis(results)


def _fallback_analysis(results: dict) -> AnalysisResult:
    metrics = results.get("metrics", {})
    wr = metrics.get("win_rate", 0)
    sharpe = metrics.get("sharpe", 0)
    dd = metrics.get("max_drawdown", 0)

    score = min(10, max(1, round(
        (wr / 10 if wr > 50 else wr / 20) +
        (sharpe * 2 if sharpe > 0 else 0) -
        (dd / 10)
    )))

    strengths = []
    weaknesses = []
    recommendations = []

    if wr > 55:
        strengths.append(f"Win rate of {wr:.1f}% is above average")
    else:
        weaknesses.append(f"Win rate of {wr:.1f}% could be improved")

    if sharpe > 1.0:
        strengths.append(f"Sharpe ratio of {sharpe:.2f} indicates good risk-adjusted returns")
    else:
        weaknesses.append(f"Sharpe ratio of {sharpe:.2f} is below 1.0")

    if dd > 20:
        weaknesses.append(f"Max drawdown of {dd:.1f}% is high")
        recommendations.append("Add a stop-loss or reduce position sizing")
    else:
        strengths.append(f"Controlled drawdown of {dd:.1f}%")

    return AnalysisResult(
        score=score,
        summary=f"Score: {score}/10. Strategy has {len(strengths)} strengths and {len(weaknesses)} areas to improve.",
        strengths=strengths,
        weaknesses=weaknesses,
        recommendations=recommendations,
    )
