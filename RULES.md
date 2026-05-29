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
# 1. Arrêt des agents + nettoyage
screen -S agent -X quit 2>/dev/null
screen -S vibe-agent -X quit 2>/dev/null
sleep 1
rm -f /tmp/strategy_chat_req_*.json /tmp/strategy_chat_res_*.json
rm -f /tmp/vibe_chat_req_*.json /tmp/vibe_chat_res_*.json
rm -f /tmp/groq_busy.lock

# 2. Nettoyage cache Python
find . -name '__pycache__' -exec rm -rf {} + 2>/dev/null
find . -name '*.pyc' -delete 2>/dev/null

# 3. Démarrage agents
screen -dmS agent bash -c 'cd /home/anymous/PROJETS/candle-analytics && .venv/bin/python api/agent.py'
sleep 1
screen -dmS vibe-agent bash -c 'cd /home/anymous/PROJETS/candle-analytics && .venv/bin/python api/vibe_agent.py'
sleep 1

# 4. Démarrage serveur
scripts/server.sh start 8001

# 5. Vérification
curl -sf http://localhost:8001/api/health > /dev/null || ./scripts/notify.sh error "Server health check failed"
./scripts/notify.sh done "Servers restarted"
```

### Port conflict handling

- **Port 8000 est souvent root** — un ancien `uvicorn` root peut bloquer le port. Impossible à tuer sans `sudo`.
- **Solution** : utiliser le port 8001 par défaut. Le port 8000 est réservé au déploiement Docker.
- Si un processus root bloque le port cible, `fuser -k` et `lsof -ti` échouent silencieusement. Utiliser `scripts/server.sh list` pour diagnostiquer.
- **`scripts/server.sh`** est l'outil centralisé : `kill|start|restart|health|list [PORT]`
- Toujours vérifier `curl -sf http://localhost:PORT/api/health` après démarrage.

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

## 9. AI-generated custom types

Types créés par l'agent AI via `config_update` persistent dans :
- `custom_types/ai_generated.json` (séparé des fichiers pré-populés)
- Les types AI ont `"source": "ai_generated"` dans leurs métadonnées
- Ne PAS écraser `orders.json`, `indicators.json`, `conditions.json` — ils sont réinitialisés à chaque `maturin develop`

Les ordres custom utilisent le Rust state machine (`run_state_machine_order()` dans `vibe_engine`). Signature :
`(_opens, highs, lows, closes, _volumes, order_type, state_model_json, params_json, entry_bar, entry_price, lookahead)`
Retourne `[entry_bar, exit_bar, entry_price, exit_price, ret, reason]`.
