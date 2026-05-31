# Règles globales d'opencode — Candle Analytics

## 1. Notification audio/visuelle

Après chaque bloc d'implémentation, ou quand une question/erreur survient :

```bash
./scripts/notify.sh done "Implémentation terminée"
./scripts/notify.sh question "Question en attente"
./scripts/notify.sh error "Échec du build"
```

Mécanismes disponibles :
- `aplay` → sons WAV dans `~/.config/opencode/sounds/` (ou terminal bell en fallback)
- `notify-send` → notification bureau Linux
- Log coloré terminal

## 2. Redémarrage complet (serveur + agents)

Après toute modification de `api/` ou `candles/` ou `vibe_engine/` :

```bash
# 0. Kill ALL old agents/servers — scripts/kill-agents.sh handles ALL duplicates
scripts/kill-agents.sh --all
sleep 1

# 1. Nettoyage cache Python
find . -name '__pycache__' -exec rm -rf {} + 2>/dev/null
find . -name '*.pyc' -delete 2>/dev/null

# 2. Démarrage agents
screen -dmS agent bash -c 'cd /home/anymous/PROJETS/candle-analytics && .venv/bin/python api/agent.py'
sleep 1
screen -dmS vibe-agent bash -c 'cd /home/anymous/PROJETS/candle-analytics && .venv/bin/python api/vibe_agent.py'
sleep 1

# 3. Nettoyage cache + démarrage serveur
find . -name '__pycache__' -exec rm -rf {} + 2>/dev/null
find . -name '*.pyc' -delete 2>/dev/null
scripts/server.sh start 8001

# 4. Vérification
curl -sf http://localhost:8001/api/health > /dev/null || ./scripts/notify.sh error "Server health check failed"
echo "agent: $(ps aux | grep '[a]pi/agent\.py' | grep -v SCREEN | wc -l) running"
echo "vibe-agent: $(ps aux | grep '[a]pi/vibe_agent\.py' | grep -v SCREEN | wc -l) running"
echo "candle: $(ps aux | grep '[u]vicorn' | wc -l) running"
./scripts/notify.sh done "Servers restarted"
```

### Port conflict handling

- **Port 8000 est souvent root** — un ancien `uvicorn` root peut bloquer le port. Impossible à tuer sans `sudo`.
- **Solution** : utiliser le port 8001 par défaut. Le port 8000 est réservé au déploiement Docker.
- Si un processus root bloque le port cible, `fuser -k` et `lsof -ti` échouent silencieusement. Utiliser `scripts/server.sh list` pour diagnostiquer.
- **`scripts/server.sh`** est l'outil centralisé : `kill|start|restart|health|list [PORT]`
- Toujours vérifier `curl -sf http://localhost:PORT/api/health` après démarrage.
- **⚠️ Stale process trap**: `screen -S candle -X quit` ne tue PAS toujours le processus uvicorn enfant. Le processus orphelin continue de servir sur le port avec l'ancien code. Toujours utiliser `fuser -k PORT/tcp` APRÈS avoir tué la session screen. Vérifier que le port est libre avec `lsof -ti:PORT` avant de redémarrer. Effacer les `__pycache__` après modification.
- **Best practice**: `fuser -k PORT/tcp && sleep 2 && screen -dmS candle ... && sleep 3 && curl -sf http://localhost:PORT/api/health`

### ⚠️ Zombie screen session accumulation

Each `screen -dmS agent ...` or `screen -S agent -X quit` + `screen -dmS agent` pair can create duplicate screen sessions if the old one wasn't killed properly. Over many server restarts, **dozens of zombie screen sessions** accumulate. **`screen -S agent -X quit` only kills the FIRST matching session — duplicates are invisible to this command.**

**Detection (add to session start checklist):**
```bash
scripts/kill-agents.sh --check   # reports counts, warns if > 1 of any process
```

Or manually (exclude SCREEN wrapper whose cmdline also contains `api/agent.py`):
```bash
ps aux | grep '[a]pi/agent\.py' | grep -v SCREEN | wc -l        # expected: 1
ps aux | grep '[a]pi/vibe_agent\.py' | grep -v SCREEN | wc -l   # expected: 1
screen -ls 2>/dev/null | grep -cE 'agent|vibe-agent'                         # expected: 2
```

**Cleanup (use the centralized script, NOT `screen -S ... -X quit`):**
```bash
scripts/kill-agents.sh --all   # kills ALL duplicates + servers + cleans IPC
sleep 1
# Then start fresh
screen -dmS agent bash -c 'cd /home/anymous/PROJETS/candle-analytics && .venv/bin/python api/agent.py'
screen -dmS vibe-agent bash -c 'cd /home/anymous/PROJETS/candle-analytics && .venv/bin/python api/vibe_agent.py'
screen -dmS candle bash -c 'cd /home/anymous/PROJETS/candle-analytics && .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8001'
sleep 3
curl -sf http://localhost:8001/api/health
```

**Prevention:**
- **NEVER** use `screen -S agent -X quit` alone — it only kills ONE of potentially many duplicates
- **NEVER** use `pkill -f` — the pattern matches `pkill` itself in /proc, causing a self-signal hang
- **ALWAYS** use `scripts/kill-agents.sh` which kills ALL matching Python processes by PID
- The `code-quality` skill checklist item 19 auto-detects duplicates at session start

## 3. Mise à jour des .md

Après chaque implémentation majeure :
- `CHRONOLOGIE.md` — nouvelle entrée de session avec résumé
- `ROADMAP.md` — cocher les tâches accomplies
- `ERRORS.md` — logger les bugs rencontrés + solutions
- `AGENTS.md` — si nouveau script/skill ajouté
- Tout autre `.md` affecté par le changement

## 4. Build Rust

Après modification de `vibe_engine/src/` :

```bash
cd vibe_engine && maturin develop --release
```

Vérifier l'import Python ensuite.

> **Note** : `cargo test` échoue avec linker error (pyo3 needs Python linking). Utiliser `maturin develop --release` pour tester.

## 5. Build Python / Dépendances

Ajouter toute nouvelle dépendance dans `requirements.txt`.
Préférer la stdlib ou Rust (via maturin) pour les nouvelles fonctionnalités.

## 6. Tests

- Rust : `maturin develop --release` puis import Python (pas `cargo test`, voir §4)
- Python : après `maturin develop`, importer et tester les nouvelles fonctions
- End-to-end : vérifier les endpoints API + UI (server health, endpoints principaux)

## 7. Priorité des dépendances

1. **Rust via maturin** (perf, sécurité)
2. **stdlib Python**
3. **pip packages** (dernier recours)

## 8. Docker First — Portabilité absolue

**Règle globale : pour tout projet (nouveau ou existant), créer un Dockerfile AVANT d'écrire la première ligne de code applicatif.**

### Procédure

```dockerfile
# 1. Créer le Dockerfile avec build multi-stage si nécessaire (Rust → Python)
# 2. Créer docker-compose.yml avec tous les services
# 3. Ajouter .dockerignore
# 4. Tester : docker compose build && docker compose up
# 5. Coder dans les volumes montés (bind mounts pour dev)
```

### Avantages concrets

| Problème | Sans Docker | Avec Docker |
|----------|-------------|-------------|
| **OS update** | `pip` cassé, `apt` packages incompatibles, Python version changée | Image figée — reproduit à l'identique |
| **PC change** | Réinstaller tout, versions différentes, bugs aléatoires | `docker compose up` = projet complet en 1 commande |
| **Python 3.14 PEP 668** | Bloque pip, besoin de venv, --break-system-packages | Conteneur isolé, pip libre |
| **Rust compilation** | Toolchain mismatch, linker errors | Build multi-stage isolé |
| **Team onboarding** | Docs de setup de 20 pages | `git clone && docker compose up` |
| **CI/CD** | Scripts dépendent de l'OS runner | Docker = même environnement partout |
| **Port conflicts** | 8000 root, 8001 déjà utilisé, fuser -k | Port mapping explicite, isolation |
| **GROQ_API_KEY** | .env chargé ou pas selon le shell | .env_file garanti chargé |
| **Screen/process** | Processus zombies, screen sessions à gérer | Docker restart=unless-stopped, healthcheck |
| **Rollback** | `git checkout` mais dépendances pas rétablies | `docker compose down && docker compose up` avec l'image précédente |

### Anti-patterns à éviter

- ❌ `--reload` en prod (bind mount de dev uniquement)
- ❌ Image unique sans multi-stage (le cache Rust explose la taille)
- ❌ `pip install` sans cache dans le Dockerfile final (garder `--no-cache-dir`)
- ❌ Variables d'env en dur dans le Dockerfile (toujours .env_file)
- ❌ `CMD` avec `python3` au lieu du chemin absolu

## 9. Custom Types Registry

Les clés du registry `custom_types/registry.py` diffèrent de celles des fichiers JSON pré-populés :

| Registry key | JSON file |
|-------------|-----------|
| `order_types` | `orders.json` (pas `orders`) |
| `custom_indicators` | `indicators.json` (pas `indicators`) |
| `custom_conditions` | `conditions.json` (pas `conditions`) |
| `cdl_patterns` | N/A (intégré) |

**Toujours utiliser les clés du registry** dans le code Python (`load_custom_types()`) et les fichiers AI (`ai_generated.json`).

## 9. Systematic tool execution before final answer

**Every script or tool created to resolve a problem MUST be run during code quality checks, before the final answer to the user.** This includes (but is not limited to):

- `scripts/check-pyjs-quotes.sh` — Python-to-JS quoting validation (after every `.py` edit)
- `scripts/chat_e2e.py smoke --port 8001` — E2E smoke test (after any server-side change)
- Scripts referenced in the `code-quality` skill checklist
- Any diagnostic tool created ad-hoc during a debugging session

### Why

Tools sitting unused are worthless. A bug is not fixed until the tool that would have caught it passes. Running the tool proves the fix is real and prevents regression.

### Integration

The `code-quality` skill's pre-declaration checklist already includes item 15 (`pyjs-quote check`). Always run the full checklist before declaring a build complete. If a new tool was created during the session, add it to the checklist.

### Enforcement

When a new diagnostic script/tool is created or discovered during a session:
1. Add a RULES.md entry in this section
2. Add a corresponding item to the `code-quality` checklist
3. Run it immediately to verify the current fix

## 10. Subscription cleanup — event listener hygiene

**Every subscription MUST have a matching cleanup.** Never leave dangling event listeners or timers.

### Common patterns

| Subscription | Cleanup |
|-------------|---------|
| `chart.subscribeCrosshairMove(handler)` | `chart.unsubscribeCrosshairMove(handler)` |
| `chart.timeScale().subscribeVisibleTimeRangeChange(handler)` | `chart.timeScale().unsubscribeVisibleTimeRangeChange(handler)` |
| `element.addEventListener('input', handler)` | `element.removeEventListener('input', handler)` |
| `new ResizeObserver(callback)` | `observer.disconnect()` |
| `setTimeout(fn, ms)` | `clearTimeout(timerId)` |
| `setInterval(fn, ms)` | `clearInterval(intervalId)` |
| `new EventSource(url)` | `eventSource.close()` |

### Enforcement

- Always store the handler reference (not an anonymous function) when cleanup is needed
- Use a `_unsub` / `_disconnect` / `_cleanup` field on the data object for pairing
- When re-initializing a feature (e.g. chart, indicators), remove old subscriptions BEFORE adding new ones
- The `project-audit` skill Phase 9 scans for subscription/cleanup mismatches

## 11. AI-generated custom types

Types créés par l'agent AI via `config_update` persistent dans :
- `custom_types/ai_generated.json` (séparé des fichiers pré-populés)
- Les types AI ont `"source": "ai_generated"` dans leurs métadonnées
- Ne PAS écraser `orders.json`, `indicators.json`, `conditions.json` — ils sont réinitialisés à chaque `maturin develop`

Les ordres custom utilisent le Rust state machine (`run_state_machine_order()` dans `vibe_engine`). Signature :
`(_opens, highs, lows, closes, _volumes, order_type, state_model_json, params_json, entry_bar, entry_price, lookahead)`
Retourne `[entry_bar, exit_bar, entry_price, exit_price, ret, reason]`.

## 12. End-of-session closeout

When the session ends (user says `exit`, `/exit`, `/quit`, `stop`, `restart`):

### A. Update markdown docs
- CHRONOLOGIE.md — log the session
- ERRORS.md — log all bugs fixed
- ROADMAP.md — check off done items
- RULES.md — add any new rules created this session
- AGENTS.md, CONVENTIONS.md — update as needed

### B. Generate session synthesis
Write a topic-organized summary to `USERS_DOCUMENT/synthesis/synthesis-<topic>-<date>.md`.
This distills what was done across the session into a thematic, cross-referenceable document.

### C. Run project audit
Execute the `project-audit` skill to scan the full project tree, dependencies, git state,
doc sync, file organization, and propose improvements. Fix any issues found.

### D. GitHub backup
Push all changes to `origin main` via the github-backup skill.

### E. Full server shutdown
Kill ALL remaining processes so nothing is left active:
```bash
scripts/kill-agents.sh --all
```
