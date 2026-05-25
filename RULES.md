# Rules — CANDLE-ANALYTICS

> Operational rules for AI-assisted development of the edge-detection pipeline.

## Project discipline

1. **No USDT** — French regulation forbids it. USDC only.
2. **Public endpoints first** — klines don't need API keys.
3. **SQLite + CSV dual storage** — structured queries + portability.
4. **One CLI to rule them** — `python -m candles` handles fetch, backfill, server.
5. **Edge first, code second** — every feature must answer: "Does this help discover or validate a trading edge?"
6. **Never destroy API keys** — comment them out instead of deleting. They stay inert but present in the file.

## Session workflow

7. **Every session logged** — see CHRONOLOGIE.md.
8. **Sessions auto-saved** — every message is auto-saved to `sessions_upload/` via the auto-export plugin. Terminal closure is intercepted gracefully.
9. **Auto-update ROADMAP + CHRONOLOGIE after each session** — after any significant build/fix session, update ROADMAP.md (task checkboxes) and CHRONOLOGIE.md (new session entry) before finishing.
10. **Update ERRORS.md after every bug fix** — append root cause + solution before finishing the session. The fix isn't done until it's documented. Before debugging an unfamiliar error, grep ERRORS.md for the component name or error message.

## Server

11. **Restart all 3 on session start** — on first message of every new session, kill old screen sessions and restart agent, vibe-agent, and server in order. Clean up stale `/tmp/*_chat_*.json` IPC files. Run the full restart block from the session-lifecycle skill.
12. **After every file change** — restart all 3 processes using screen sessions:
    ```bash
    screen -S agent -X quit 2>/dev/null; screen -S vibe-agent -X quit 2>/dev/null; screen -S candle -X quit 2>/dev/null
    sleep 1
    screen -dmS agent bash -c 'cd /home/anymous/PROJETS/candle-analytics && python3 api/agent.py'
    sleep 1
    screen -dmS vibe-agent bash -c 'cd /home/anymous/PROJETS/candle-analytics && python3 api/vibe_agent.py'
    sleep 1
    screen -dmS candle bash -c 'cd /home/anymous/PROJETS/candle-analytics && uvicorn api.main:app --host 0.0.0.0 --port 8001'
    sleep 3
    curl -s http://localhost:8001/api/health
    ```
13. **Secrets in `.env`** — loaded via `load_dotenv()` at module level, never hardcoded in source.

## Code

14. **Read before edit** — see current content before making any change.
15. **Prefer targeted edits** — use Edit tool for precise string replacement, not full-file rewrites.
16. **Match existing conventions** — same libraries, naming, imports as the file being edited.
17. **Test after every change** — curl the endpoint or run the relevant script.
18. **JS inside Python strings** — use ES5 syntax (no arrow/const/let/template literals), escape backslashes (`\\d` not `\d`) to avoid Python SyntaxWarnings.

## AI efficiency — Project docs

14. **RunSearch auto-mode** — every Engine Search Group feature (Monte Carlo, Walk-Forward, Sweep) runs automatically on every RunSearch unless the user explicitly disables it in the Engine Search Group UI.
15. **Use `USERS_DOCUMENT/project-docs/` for project knowledge** — All architecture, API, frontend, data, strategy engine docs are stored as concise `.md` files in this folder. Before starting new work, the AI reads the relevant `.md` first (not the source code) to reduce token consumption. When the AI needs to update a component, it reads the `.md` then the source file. If the user provides complex information, they can store it in `USERS_DOCUMENT/` for reference.

15. **Docs are concise** — Each `.md` is under 100 lines. Interfaces, not implementation.

| File | Purpose |
|------|---------|
| `USERS_DOCUMENT/project-docs/ARCHITECTURE.md` | System overview, data flow, layers |
| `USERS_DOCUMENT/project-docs/API.md` | All endpoints, WS protocol, file bridge |
| `USERS_DOCUMENT/project-docs/FRONTEND.md` | Pages, JS patterns, chart families |
| `USERS_DOCUMENT/project-docs/DATA.md` | DB schema, metrics, exchanges |
| `USERS_DOCUMENT/project-docs/STRATEGY_ENGINE.md` | Edge search, backtest, sandbox, indicators |
| `USERS_DOCUMENT/project-docs/AGENTS.md` | Agent configs, Groq, IPC |
| `USERS_DOCUMENT/project-docs/TEMPLATES.md` | Strategy config format, AI output schema |
| `USERS_DOCUMENT/project-docs/CONVENTIONS.md` | Naming, screen sessions, rules |

## Docs management

| File | Purpose | Updated |
|------|---------|---------|
| `ROADMAP.md` | Goals, phases, tasks, configuration | End of each session |
| `CHRONOLOGIE.md` | Session-by-session narrative log | End of each session |
| `ERRORS.md` | Bug fixes with root cause + solution | After every bug fix |
| `RULES.md` | Operational rules (this file) | As needed |
| `USERS_DOCUMENT/project-docs/*.md` | Component-level documentation | As needed (AI reads before work) |
| `.env` | Secrets (gitignored) | As needed |
