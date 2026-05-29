# AGENTS.md — Comment optimiser l'utilisation d'opencode

> Guide utilisateur pour travailler efficacement avec l'IA sur ce projet.

---

## Commandes rapides

| Ce que tu veux faire | Dis à l'IA |
|----------------------|-----------|
| Audit complet du projet | `/audit` |
| Synthèse du travail fait | `/synthesis` |
| Nouvelle stratégie | "Crée une stratégie avec conditions SMA > 200 et RSI < 30" |
| Bug fixes | Décris le bug + URL si applicable |
| Setup Docker | `docker compose build && docker compose up` |
| Restart serveur | "Restart le serveur" (ou fais-le toi-même : voir ci-dessous) |

---

## Workflow optimal

### 1. Toujours commencer par "Continue if you have next steps"

Quand tu veux que je continue, dis juste ça. Si je suis bloqué, je demanderai.

### 2. Une tâche à la fois

- Tu peux donner **une liste de tâches** en un seul message
- Je les mettrai dans une todo list et les traiterai dans l'ordre
- Si tu veux changer l'ordre, dis-le explicitement

### 3. Messages longs = meilleur contexte

- Tu n'as pas besoin d'être formel
- Mais plus tu donnes de contexte (ce que tu as fait, ce que tu veux, pourquoi), plus vite j'arrive au bon résultat

### 4. Pour les bugs, donne :

```
Ce que j'ai fait : [étapes]
Ce qui s'est passé : [erreur]
Ce que j'attendais : [comportement attendu]
URL de la page (si UI) : http://localhost:8001/...
```

### 5. Demande des vérifications

À la fin d'une session, demande :
- "Vérifie que tout marche" → je lance les smoke tests
- "Audit complet" → je scanne tout
- "Met à jour les .md" → je synchronise les docs

---

## Quand Docker est indisponible (dev local rapide)

Si Docker n'est pas pratique pour du dev rapide, les commandes natives sont documentées dans `RULES.md`.

### Redémarrage rapide après modif de api/

```bash
# Arrêt
screen -S agent -X quit 2>/dev/null
screen -S vibe-agent -X quit 2>/dev/null
screen -S candle -X quit 2>/dev/null
sleep 1
find . -name '__pycache__' -exec rm -rf {} + 2>/dev/null

# Démarrage
screen -dmS agent .venv/bin/python api/agent.py
sleep 1
screen -dmS vibe-agent .venv/bin/python api/vibe_agent.py
sleep 1
screen -dmS candle .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8001
sleep 3
curl -sf http://localhost:8001/api/health
```

### Check santé

```bash
curl http://localhost:8001/api/health
curl http://localhost:8001/dashboard
curl http://localhost:8001/strategy-lab
curl http://localhost:8001/vibe-lab
```

---

## Pièges à éviter

- ❌ **python3** sans `.venv/` → les paquets ne seront pas trouvés
- ❌ **--reload** en screen → les logs deviennent illisibles
- ❌ **Nouveau terminal sans source .venv** → les commandes échouent
- ❌ **Modifier dashboard.py sans vérifier JS** → SyntaxError silencieuse
- ❌ **Oublier de restart après modif** → l'ancien code tourne encore
- ❌ **Cargo test** → linker error avec pyo3. Toujours `maturin develop --release`

---

## Structure des prompts efficaces

### Pour coder une feature

```
Ajoute [feature X] dans [fichier].
Elle doit faire [comportement].
Inspire-toi de [endroit similaire] dans le code.
Contrainte : [pas de dépendance supplémentaire / ES5 / etc.]
```

### Pour corriger un bug

```
[Fichier] : [description du bug].
J'ai essayé [ce que tu as fait].
Je pense que c'est dû à [ta théorie].
Peux-tu investiguer et corriger ?
```

### Pour une refactor

```
Refactor [fichier] : extrais [logique] dans [nouveau fichier].
Renomme [ancien_nom] → [nouveau_nom].
Mets à jour tous les imports.
Ne change pas le comportement.
```

---

## Utiliser les skills

L'IA a des skills spécialisés. Tu peux les invoquer :

```
"Run the chat-smoke test suite"
"Run code-quality pre-declaration checklist"
"Push to GitHub"  (invoque github-backup)
"Restart the server" (invoque server-lifecycle)
"New session"   (invoque session-lifecycle)
```

---

## Docker pour la portabilité

```bash
# Build (10-15 min la première fois à cause de Rust)
docker compose build

# Lancer tout
docker compose up -d

# Voir les logs
docker compose logs -f api

# Arrêter
docker compose down

# Rebuild après modif
docker compose build api && docker compose up -d
```

### Avantages Docker (vs dev natif)

1. **Reproductible** — pas de "chez moi ça marche"
2. **Isolé** — pas de conflit de version Python/packages
3. **Rust intégré** — compilation propre sans dépendre du toolchain local
4. **Port 8000** — pas de conflit avec un process root
5. **Healthcheck** — redémarrage automatique si le process crashe
6. **GROQ_KEY** — chargé depuis `.env` de façon garantie
7. **4 services** — api + stream + agent + vibe-agent, tout en 1 commande

---

## Si l'IA répond mal

- Reformule ton message en plus court
- Donne le fichier et la ligne exacte
- Demande-lui de chercher d'abord ("Cherche dans le code comment X est fait")
- Si c'est une question de stratégie trading : utilise `/strategy designer`

---

## À faire absolument avant de quitter une session

1. ✏️ Demander "Met à jour les .md" si pas fait automatiquement
2. 🧪 Vérifier que le serveur répond : `curl localhost:8001/api/health`
3. 📦 Git si besoin : `git status` + `git push`
4. 🐳 Optionnel : `docker compose build` pour figer l'état actuel
