# Agents — candle-analytics

## Architecture

Both agents are **standalone Python scripts** (not FastAPI routes) that poll `/tmp/*.json` files via the file bridge IPC. They must be running in `screen` sessions.

## Strategy Lab agent (`api/agent.py`)

| Property | Value |
|----------|-------|
| Screen name | `agent` |
| Command | `python3 api/agent.py` |
| Poll pattern | `/tmp/strategy_chat_req_*.json` |
| Response pattern | `/tmp/strategy_chat_res_*.json` |
| Model | `qwen/qwen3-32b` (Groq) |
| Max tokens | 1024 |
| Temperature | 0.7 |
| System prompt | Loads `.opencode/skills/strategy-designer/SKILL.md` |
| Available metrics | OC%, OH%, OL%, HL%, HC%, LC%, Vol%, Pctl variants |
| Response types | `message`, `config_update` (populates Parameters panel) |

## Vibe Lab agent (`api/vibe_agent.py`)

| Property | Value |
|----------|-------|
| Screen name | `vibe-agent` |
| Command | `python3 api/vibe_agent.py` |
| Poll pattern | `/tmp/vibe_chat_req_*.json` |
| Response pattern | `/tmp/vibe_chat_res_*.json` |
| Model | `qwen/qwen3-32b` (Groq) |
| Max tokens | 2048 |
| Temperature | 0.4 |
| System prompt | Hardcoded (indicators, sandbox functions, response formats) |
| Response types | `message`, `code_generated` (fills Code tab) |
| Retry | 3 attempts, exponential backoff on 429 |

## How to start

```bash
screen -dmS agent bash -c 'cd ... && python3 api/agent.py'
screen -dmS vibe-agent bash -c 'cd ... && python3 api/vibe_agent.py'
```

Check: `screen -ls` or `ps aux | grep "api/agent"`

## Groq config

| Env var | Value |
|---------|-------|
| `GROQ_API_KEY` | Set in `.env` |
| Model | `qwen/qwen3-32b` (free tier) |
| Timeout | 30s (agent), 60s (vibe-agent, with retries) |

## External Sources Security

This project uses external/untrusted sources (GitHub repos, scripts, skills). Before importing or executing anything:

### Recommended security analysis tools

| Tool | Type | Purpose | Security | Ease | Update frequency |
|------|------|---------|----------|------|-----------------|
| **OpenSSF Scorecard** | CLI/GitHub Action | Repo security posture score (0-10) | ★★★★★ | ★★★★ | Weekly |
| **Trivy** | CLI | Vulnerability scan for files, deps, containers | ★★★★★ | ★★★★★ | Daily |
| **Semgrep** | CLI | Static analysis for code patterns & anti-patterns | ★★★★ | ★★★★ | Weekly |
| **Bandit** | CLI | Python-specific security linter | ★★★ | ★★★★★ | Monthly |

### Quick-check procedure before importing

```bash
# 1. Scorecard: assess the repo's security posture
npx @openssf/scorecard --repo=github.com/owner/repo

# 2. Trivy: scan the cloned directory for vulnerabilities
trivy fs /path/to/repo

# 3. Semgrep: check for security anti-patterns
semgrep --config=auto /path/to/repo
```

### If any tool scores LOW (< 5/10)
- Do NOT execute the code
- Review manually for obfuscation, network calls, file access
- Sandbox in Docker before trusting
