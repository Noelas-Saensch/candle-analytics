# Système d'Alertes / Conditions / Automation

> Phase 3 du roadmap — Remplacer TradingView Alerts + Webhooks + Paper Trading par un système **free, self-hosted, modulable, évolutif**.
>
> **Principe** : Chaque condition évalue des expressions sur les valeurs d'indicateurs à chaque close de bougie → déclenche des actions (highlight, notification, webhook, ordre).

---

## Table des matières

1. [Architecture générale](#1-architecture-générale)
2. [A — Infrastructure : parseur d'expression, moteur de triggers, persistence](#a--infrastructure)
3. [B — Canaux de livraison](#b--canaux-de-livraison)
4. [C — Exécution d'ordres](#c--exécution-dordres)
5. [D — Chart & UI](#d--chart--ui)
6. [E — Filtres statistiques (HAUTE PRIORITÉ)](#e--filtres-statistiques)
7. [Première condition : Ichimoku Trend](#première-condition--ichimoku-trend)
8. [Sources d'inspiration](#sources-dinspiration)
9. [Glossaire](#glossaire)

---

## 1. Architecture générale

```
┌─────────────────────────────────────────────────────────┐
│                    DATA LAYER                           │
│  Binance WS ──→ SQLite ──→ query_candles(limit, desc)  │
└──────────────────────┬──────────────────────────────────┘
                       │ new candle close
                       ▼
┌─────────────────────────────────────────────────────────┐
│              INDICATOR COMPUTE LAYER                    │
│  Rust (vibe_engine) → Python bindings → indicator values │
│  POST /api/indicators/compute                           │
└──────────────────────┬──────────────────────────────────┘
                       │ indicator values at candle N
                       ▼
┌─────────────────────────────────────────────────────────┐
│              CONDITION ENGINE (A)                       │
│  Parseur d'expression → evaluate(condition, values)      │
│  true / false + metadata                                │
└──────────────────────┬──────────────────────────────────┘
                       │ if true
                       ▼
┌─────────────────────────────────────────────────────────┐
│              TRIGGER PIPELINE (A)                       │
│  Pour chaque action configurée sur cette condition :     │
│  → Vérifier cooldown                                    │
│  → Dispatcher l'action                                  │
│  → Logger dans l'historique SQLite                      │
└──┬───────┬───────┬───────┬───────┬───────┬──────────────┘
   │       │       │       │       │       │
   ▼       ▼       ▼       ▼       ▼       ▼
 ┌───┐  ┌────┐  ┌────┐  ┌────┐  ┌────┐  ┌─────┐
 │BG │  │SSE │  │Tgrm│  │Disc│  │Mail│  │Ordre│
 │Bar│  │Toast│  │ Bot│  │Webh│  │SMTP│  │CCXT │
 └───┘  └────┘  └────┘  └────┘  └────┘  └─────┘
```

### Flux de données complet

1. **Data layer** → Nouvelle bougie fermée (SSE `candle_closed` event)
2. **Compute layer** → Calcul des indicateurs pour cette bougie
3. **Condition engine** → Évalue les conditions actives
4. **Trigger pipeline** → Si true → dispatche les actions configurées
5. **Delivery layer** → Envoie les notifications, exécute les ordres

### Types de trigger

| Type | Déclencheur | Usage |
|------|-------------|-------|
| `on_close` | À chaque close de bougie si condition est true | Régulier |
| `on_cross` | Quand la condition passe de false→true ou true→false | Entrées/Sorties |
| `realtime` | Sur chaque tick/mise à jour si condition est true | Haute fréquence |
| `once`| Ne se déclenche qu'une seule fois (puis se désactive) | Alertes uniques |

---

## A — Infrastructure

### A.1 Parseur d'expressions de conditions

**Endpoint** : `POST /api/conditions/evaluate`

**Payload** :
```json
{
  "expression": {
    "operator": "AND",
    "conditions": [
      { "left": "ichimoku_chikou", "op": "gt", "right": "ichimoku_tenkan" },
      { "left": "ichimoku_chikou", "op": "gt", "right": "ichimoku_kijun" },
      { "left": "close", "op": "gt", "right": "ichimoku_tenkan" },
      { "left": "close", "op": "gt", "right": "ichimoku_kijun" }
    ]
  },
  "indicator_values": { ... },
  "trigger_type": "on_close"
}
```

**Opérateurs supportés** :
- `gt` (greater than), `gte` (≥), `lt` (less than), `lte` (≤), `eq` (==)
- `cross_above` (croise au-dessus), `cross_below` (croise en-dessous)
- `between` (entre deux valeurs), `outside` (en dehors)
- `true` / `false` (condition toujours vraie/fausse, pour debug)

**Niveaux de nesting** :
- Support des parenthèses : `(A AND B) OR (C AND D)`
- Support du NOT : `NOT (A AND B)`
- Support des précédences : AND avant OR (ou explicite via parenthèses)

**Retour** :
```json
{
  "result": true,
  "metadata": {
    "triggered_at": "2026-05-31T12:00:00Z",
    "candle_index": 4999,
    "triggered_conditions": ["ichimoku_chikou > ichimoku_tenkan", "close > ichimoku_kijun"],
    "values_at_trigger": {
      "ichimoku_chikou": 65432.1,
      "ichimoku_tenkan": 65000.0,
      "close": 65500.0
    }
  }
}
```

#### Tâches détaillées A.1

- [ ] **A.1.1** — Définir le format d'expression de condition (JSON structuré, support AND/OR/NOT/parenthèses)
- [ ] **A.1.2** — Implémenter le parseur d'expression (arbre syntaxique → évaluation récursive)
- [ ] **A.1.3** — Implémenter l'évaluateur : compare left op right avec les valeurs d'indicateurs fournies
- [ ] **A.1.4** — Implémenter `cross_above` / `cross_below` : compare valeur bougie N vs N-1
- [ ] **A.1.5** — Gérer les valeurs manquantes (NaN, None) → condition = false, log warning
- [ ] **A.1.6** — Endpoint `POST /api/conditions/evaluate` avec validation
- [ ] **A.1.7** — Tests unitaires pour le parseur + évaluateur (tous les opérateurs, nesting, edge cases)

### A.2 Moteur de triggers

**Boucle principale** (s'exécute à chaque nouvelle bougie fermée) :

```python
def evaluate_all_active_conditions(candle_data):
    for condition in active_conditions:
        indicator_values = compute_indicators_for_candle(candle_data)
        result = condition_engine.evaluate(condition.expression, indicator_values)

        if result.result == True:
            if should_trigger(condition, result, condition.trigger_type):
                for action in condition.actions:
                    dispatch(action, condition, result)
                    log_trigger(condition, action, result)
```

**Règles de déclenchement** :
- `on_close` : true → dispatcher
- `on_cross` : comparer avec le résultat précédent (stocké en mémoire/SQLite). Si false→true ou true→false → dispatcher
- `realtime` : idem mais évalué à chaque tick SSE, pas seulement au close
- `once` : dispatcher puis désactiver la condition

**File d'attente** :
- Les actions sont dispatchées de manière asynchrone (pas de blocage de la boucle)
- Les échecs de livraison sont loggués et réessayés (max 3 tentatives, backoff exponentiel)
- Timeout par action : 5s pour webhook, 10s pour ordre

#### Tâches détaillées A.2

- [ ] **A.2.1** — Boucle d'évaluation principale (`evaluate_all_active_conditions`) appelée sur `candle_closed`
- [ ] **A.2.2** — Gestion des types de trigger (on_close, on_cross, realtime, once)
- [ ] **A.2.3** — Stockage du dernier état de chaque condition (pour détection de cross)
- [ ] **A.2.4** — File d'attente asynchrone pour le dispatch des actions (asyncio queue ou threading)
- [ ] **A.2.5** — Système de retry (3 tentatives, backoff exponentiel, timeout)
- [ ] **A.2.6** — Logger d'historique des triggers (timestamp, condition_id, action_type, success/fail, message)

### A.3 Persistance des conditions

**Table SQLite `conditions`** :
```sql
CREATE TABLE conditions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    expression TEXT NOT NULL,        -- JSON de l'expression
    enabled BOOLEAN DEFAULT 1,
    trigger_type TEXT DEFAULT 'on_close',  -- on_close | on_cross | realtime | once
    cooldown_ms INTEGER DEFAULT 60000,    -- 1 minute par défaut
    last_triggered_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Table SQLite `condition_actions`** :
```sql
CREATE TABLE condition_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    condition_id INTEGER REFERENCES conditions(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,        -- telegram | discord | email | webhook | order | bgcolor | sse_toast
    config JSON NOT NULL,             -- configuration spécifique à l'action
    enabled BOOLEAN DEFAULT 1
);
```

**Table SQLite `trigger_history`** :
```sql
CREATE TABLE trigger_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    condition_id INTEGER REFERENCES conditions(id),
    action_id INTEGER REFERENCES condition_actions(id),
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    result_json TEXT,                  -- metadata du trigger (valeurs au moment du déclenchement)
    success BOOLEAN,
    error_message TEXT
);
```

**API CRUD** :
- `GET /api/conditions` — liste toutes les conditions avec leurs actions
- `POST /api/conditions` — créer une condition
- `PUT /api/conditions/{id}` — modifier une condition
- `DELETE /api/conditions/{id}` — supprimer une condition + ses actions (CASCADE)
- `POST /api/conditions/{id}/toggle` — activer/désactiver
- `PUT /api/conditions/{id}/actions` — remplacer la liste des actions
- `GET /api/conditions/history` — historique des triggers (paginé, filtrable par condition_id)

#### Tâches détaillées A.3

- [ ] **A.3.1** — Créer les tables SQLite (`conditions`, `condition_actions`, `trigger_history`)
- [ ] **A.3.2** — CRUD complet pour les conditions (5 endpoints REST)
- [ ] **A.3.3** — CRUD pour les actions d'une condition
- [ ] **A.3.4** — Endpoint historique des triggers (paginé, filtres)
- [ ] **A.3.5** — Script d'init / migration pour créer les tables au démarrage

---

## B — Canaux de livraison

### B.1 Coloration de bougie (bar highlighting)

**Principe** : Quand une condition est true, la bougie correspondante sur le chart change de couleur de fond.

**Implémentation** :
- Utiliser `candleSeries.createPriceLine()` ou un marqueur de série
- Alternative : canvas overlay similaire au cloud Ichimoku
- Couleur configurable par condition (vert = bullish, rouge = bearish, bleu = neutre)
- Multiple conditions actives → priorité ou mélange de couleurs (ex : condition la plus récente gagne, ou les deux s'affichent)

#### Tâches détaillées B.1

- [ ] **B.1.1** — Définir le format des données de highlighting (couleur, index de bougie, condition_id)
- [ ] **B.1.2** — Endpoint `GET /api/conditions/highlights?symbol=X&tf=1H` retourne les zones à colorer
- [ ] **B.1.3** — Coté JS : fetch les highlights au chargement + SSE push pour les nouveaux triggers
- [ ] **B.1.4** — Rendu : marqueurs, price lines, ou canvas overlay (choisir le plus performant)
- [ ] **B.1.5** — Gestion des conditions multiples sur la même bougie (ordre de priorité, transparence)

### B.2 Notification in-app (SSE Toast)

**Principe** : Une notification toast apparaît dans le dashboard quand une condition se déclenche.

**Implémentation** :
- SSE event `condition_triggered` avec payload JSON
- Toast JS avec titre, message, icône, son optionnel
- Configuration : durée d'affichage, son ON/OFF, position

#### Tâches détaillées B.2

- [ ] **B.2.1** — Événement SSE `condition_triggered` côté serveur
- [ ] **B.2.2** — Écouteur JS côté client qui reçoit l'événement et affiche un toast
- [ ] **B.2.3** — Design du toast : titre (nom de la condition), message (valeur, paire), icône, durée
- [ ] **B.2.4** — Son optionnel (notification HTML5 Audio ou Web Audio API)
- [ ] **B.2.5** — Paramètres utilisateur : son ON/OFF, durée, position

### B.3 Telegram Bot

**Principe** : Un bot Telegram envoie un message à un chat/groupe configuré.

**Implémentation** :
- Bibliothèque : `python-telegram-bot` (asynchrone) ou simple `requests.post` vers Bot API
- Configuration : token du bot + chat_id
- Message : texte formaté avec le nom de la condition, la paire, le timeframe, les valeurs, timestamp
- Option : image du chart (capture d'écran ou générée côté serveur avec matplotlib/plotly)

#### Tâches détaillées B.3

- [ ] **B.3.1** — Endpoint `POST /api/actions/telegram/test` pour tester la connexion
- [ ] **B.3.2** — Module d'envoi Telegram (token + chat_id en config)
- [ ] **B.3.3** — Template de message formaté (Markdown ou HTML)
- [ ] **B.3.4** — Gestion des erreurs (token invalide, rate limit Telegram, timeout)
- [ ] **B.3.5** — Option : envoyer une image du chart au moment du trigger

### B.4 Discord Webhook

**Principe** : POST vers un webhook Discord avec un embed.

**Implémentation** :
- `requests.post(webhook_url, json=payload)`
- Embed Discord : titre, description, fields (condition, paire, timeframe, valeurs), couleur, timestamp
- Configuration : webhook URL

#### Tâches détaillées B.4

- [ ] **B.4.1** — Endpoint `POST /api/actions/discord/test`
- [ ] **B.4.2** — Module d'envoi Discord avec embed formaté
- [ ] **B.4.3** — Gestion des erreurs (webhook invalide, rate limit Discord)

### B.5 Email (SMTP)

**Principe** : Envoi d'un email via SMTP configurable.

**Implémentation** :
- `smtplib` avec support TLS/SSL
- Configuration : host, port, user, password, from, to
- Message : sujet = nom de la condition, corps = HTML ou texte avec les détails
- Support Gmail App password, Outlook, serveur SMTP personnalisé

#### Tâches détaillées B.5

- [ ] **B.5.1** — Endpoint `POST /api/actions/email/test`
- [ ] **B.5.2** — Module d'envoi SMTP avec config complète
- [ ] **B.5.3** — Template HTML + texte pour l'email
- [ ] **B.5.4** — Gestion des erreurs (auth failed, timeout, quota exceeded)

### B.6 Webhook (TradingView-compatible)

**Principe** : POST à une URL configurable avec payload JSON formaté comme TradingView.

**Payload TradingView-compatible** :
```json
{
  "passThrough": "user-defined-value",
  "condition": "Ichimoku Trend Bullish",
  "symbol": "BTCUSDC",
  "exchange": "BINANCE",
  "price": 65500.0,
  "time": "2026-05-31T12:00:00Z",
  "interval": "1H",
  "tickers": ["BTCUSDC"]
}
```

**Configuration** :
- Webhook URL (obligatoire)
- Pass-through value (optionnel, pour identifier la source)
- Headers personnalisés (optionnel, pour auth)

#### Tâches détaillées B.6

- [ ] **B.6.1** — Endpoint `POST /api/actions/webhook/test`
- [ ] **B.6.2** — Module d'envoi webhook avec payload TradingView-compatible
- [ ] **B.6.3** — Support headers personnalisés (Authorization, etc.)
- [ ] **B.6.4** — Gestion des erreurs (timeout, non-200, DNS failure)
- [ ] **B.6.5** — Option : retry avec backoff si 5xx

### B.7 WhatsApp (optionnel, priorité basse)

**Principe** : Envoi via Twilio API.

**Implémentation** :
- `twilio.rest.Client` → `messages.create()`
- Configuration : account_sid, auth_token, from_number, to_number
- Limité à 160 caractères (ou utiliser Media API pour plus)

#### Tâches détaillées B.7

- [ ] **B.7.1** — Module d'envoi WhatsApp via Twilio
- [ ] **B.7.2** — Gestion des erreurs Twilio

---

## C — Exécution d'ordres

### C.1 Paper Trading

**Principe** : Simulation d'exécution sans envoyer d'ordres réels.

**Implémentation** :
- Étendre `StrategySandbox` existant (dans `vibe_engine/`)
- Prendre en charge les ordres déclenchés par conditions (pas seulement les backtests)
- Config : frais (%), slippage (%), capital initial
- Ordres supportés : market, limit, stop-loss, take-profit, trailing stop

**Position management** :
- Long / Short
- Entry price, quantity, fees
- Current P&L (non réalisé + réalisé)
- Trade history (entries / exits avec timestamps)

#### Tâches détaillées C.1

- [ ] **C.1.1** — Étendre `StrategySandbox` pour accepter des ordres en temps réel (pas seulement historique)
- [ ] **C.1.2** — Types d'ordres : market entry, limit entry, stop-loss, take-profit, trailing stop
- [ ] **C.1.3** — Position manager : long/short, taille de position (% du capital)
- [ ] **C.1.4** — P&L tracker : non réalisé, réalisé, frais cumulés
- [ ] **C.1.5** — Trade history : toutes les entries/exits avec timestamps, prix, quantité
- [ ] **C.1.6** — Endpoint `GET /api/paper/positions` — positions ouvertes
- [ ] **C.1.7** — Endpoint `GET /api/paper/history` — historique des trades
- [ ] **C.1.8** — Endpoint `GET /api/paper/equity` — courbe d'equity
- [ ] **C.1.9** — Endpoint `POST /api/paper/reset` — réinitialiser le compte paper

### C.2 Live Trading (CCXT)

**Principe** : Exécution réelle via une API d'exchange.

**Implémentation** :
- Bibliothèque : `ccxt` (support 100+ exchanges)
- Configuration : exchange, apiKey, secret, passphrase (pour certains exchanges)
- Mécanismes de sécurité : clés stockées dans .env, jamais exposées
- Ordres : `create_order()` de CCXT avec les paramètres standards

**Sécurité renforcée** :
- Limite de taille d'ordre max configurable
- Confirmation manuelle requise pour le premier ordre (option)
- Kill switch : arrête tous les ordres si une condition de risque est remplie

#### Tâches détaillées C.2

- [ ] **C.2.1** — Module CCXT wrapper (initialisation exchange, validation des clés)
- [ ] **C.2.2** — `POST /api/live/test` — test de connexion à l'exchange (balance, permissions)
- [ ] **C.2.3** — Ordres market entry/exit via CCXT
- [ ] **C.2.4** — Ordres limit entry/exit
- [ ] **C.2.5** — Stop-loss et take-profit (si supporté par l'exchange, sinon géré localement)
- [ ] **C.2.6** — Endpoint `GET /api/live/balance` — balance du compte
- [ ] **C.2.7** — Endpoint `GET /api/live/positions` — positions ouvertes
- [ ] **C.2.8** — Endpoint `GET /api/live/orders` — ordres en cours
- [ ] **C.2.9** — Endpoint `POST /api/live/cancel/{order_id}` — annuler un ordre
- [ ] **C.2.10** — Endpoint `POST /api/live/kill` — kill switch (annule tous les ordres)

### C.3 Kill Switch

**Principe** : Arrêt d'urgence de toute activité de trading.

**Déclencheurs** :
- Manuel : bouton "KILL" dans le dashboard
- Drawdown max : % de perte max depuis le peak
- Perte journalière max : limite de perte par jour
- Pertes consécutives max : N trades perdants d'affilée
- Erreur API exchange : N erreurs consécutives

**Comportement** :
- Annule tous les ordres ouverts sur l'exchange
- Ferme toutes les positions (market exit)
- Désactive toutes les conditions actives
- Log l'événement avec timestamp + raison
- Envoie une notification d'urgence (Telegram + Email)
- Ne peut être réarmé que manuellement

#### Tâches détaillées C.3

- [ ] **C.3.1** — Module kill switch avec tous les déclencheurs
- [ ] **C.3.2** — Monitoring continu des métriques de risque (drawdown, pertes, erreurs)
- [ ] **C.3.3** — Bouton KILL dans le dashboard
- [ ] **C.3.4** — Notification d'urgence (Telegram + Email prioritaire)
- [ ] **C.3.5** — Log des événements de kill switch
- [ ] **C.3.6** — Procédure de réarmement (bouton, endpoint API)

### C.4 Position Sizing

**Principe** : Calcul de la taille de position selon des règles définies.

**Méthodes** :
- Fixe : X unités ou X % du capital par trade
- Kelly : fraction de Kelly basée sur le win rate historique
- Risk-based : risque X % du capital, stop-loss détermine la taille
- Martingale / Anti-martingale (optionnel, risqué)

#### Tâches détaillées C.4

- [ ] **C.4.1** — Position sizing calculator (support fixe, risk-based)
- [ ] **C.4.2** — Kelly fraction optionnelle (basée sur les stats de la stratégie)
- [ ] **C.4.3** — Config par condition/stratégie

---

## D — Chart & UI

### D.1 Condition triggers sur le chart

**Principe** : Visualisation des zones où les conditions ont été vraies.

**Implémentation** :
- Marqueurs verts/rouges sur la time scale (comme TradingView)
- Zones de fond colorées sur les bougies
- Légende : couleur = condition, cliquer pour voir les détails
- Filtre : afficher/masquer les triggers par condition

#### Tâches détaillées D.1

- [ ] **D.1.1** — Endpoint `GET /api/conditions/highlights` avec paramètres de filtre
- [ ] **D.1.2** — Rendu des zones colorées sur le chart (marqueurs, price lines, ou overlay)
- [ ] **D.1.3** — Légende interactive (cliquer → détails de la condition, hover → valeurs)
- [ ] **D.1.4** — Toggle ON/OFF pour chaque condition dans la légende
- [ ] **D.1.5** — Mise à jour en temps réel via SSE

### D.2 Panneau de configuration des conditions

**Principe** : Interface utilisateur pour créer/gérer les conditions et leurs actions.

**Composants** :
- Liste des conditions avec ON/OFF toggle
- Éditeur d'expression (textuel pour commencer, visuel plus tard)
- Onglet Actions pour chaque condition (checkboxes : Telegram, Discord, etc.)
- Config de chaque action (token, URL, etc.)
- Historique des triggers (tableau paginé)

#### Tâches détaillées D.2

- [ ] **D.2.1** — Page ou modal "Conditions" dans le dashboard
- [ ] **D.2.2** — Liste des conditions avec toggle, nom, statut
- [ ] **D.2.3** — Éditeur d'expression (textarea ou inputs structurés)
- [ ] **D.2.4** — Sélecteur d'actions par condition (checkboxes + config inline)
- [ ] **D.2.5** — Formulaire de configuration pour chaque canal (Telegram token, webhook URL, etc.)
- [ ] **D.2.6** — Test d'action (bouton "Test" → envoie un message de test)
- [ ] **D.2.7** — Historique des triggers (tableau avec timestamp, condition, action, statut)

### D.3 Live trigger log

**Principe** : Flux en temps réel des évaluations de conditions dans le dashboard.

**Implémentation** :
- SSE endpoint `/api/conditions/live-log`
- Panel dédié dans le dashboard avec scroll automatique
- Chaque ligne : timestamp, condition, résultat (✅ / ❌), action dispatchée
- Filtre : par condition, par résultat (true/false)

#### Tâches détaillées D.3

- [ ] **D.3.1** — SSE endpoint pour le live log des triggers
- [ ] **D.3.2** — Panel UI avec scroll infini
- [ ] **D.3.3** — Filtres (condition, résultat, action)
- [ ] **D.3.4** — Nettoyage automatique (garder les N dernières entrées en mémoire)

### D.4 Performance dashboard

**Principe** : Tableau de bord de performance pour le trading paper et live.

**Métriques** :
- Equity curve
- Drawdown curve
- Win rate, avg win, avg loss
- Profit factor, Sharpe ratio, Sortino ratio
- Trade frequency, avg holding time
- Monthly/Weekly/Daily returns

#### Tâches détaillées D.4

- [ ] **D.4.1** — Endpoint `GET /api/paper/stats` — métriques de performance
- [ ] **D.4.2** — Graphique equity curve (LightweightCharts area series)
- [ ] **D.4.3** — Graphique drawdown
- [ ] **D.4.4** — Cartes de métriques (win rate, profit factor, Sharpe)
- [ ] **D.4.5** — Tableau des trades récents

---

## E — Filtres statistiques

> **HAUTE PRIORITÉ** — Ces filtres permettent de qualifier statistiquement chaque bougie avant de décider si une condition est valide.

### E.1 Amplitude OHLCV %

**Principe** : Calculer `(high - low) / open * 100` pour chaque bougie.

**Implémentation** :
- Pré-calculé au moment de l'insertion des données (stocké en DB)
- Configurable : utiliser `HL%` (déjà calculé) ou d'autres combinaisons
- Utilisation : "ne déclencher que si l'amplitude est > X%" (filtrer les bougies plates)

#### Tâches détaillées E.1

- [ ] **E.1.1** — Vérifier que OL% / HL% est déjà pré-calculé en DB (metrics layer)
- [ ] **E.1.2** — Rendre disponible comme opérande dans les expressions de conditions
- [ ] **E.1.3** — Ajouter des opérateurs de comparaison configurable (% > X, % < Y, % entre X et Y)

### E.2 Percentile rank

**Principe** : Classer la valeur actuelle d'une métrique par rapport à son historique récent.

**Implémentation** :
- Fenêtre glissante (rolling window, ex: 500 bougies)
- Pour chaque métrique/indicateur, calculer le percentile de la valeur actuelle
- Exemple : RSI à 75 → 95e percentile → fortement suracheté
- Utilisation : "déclencher si OC% > 90e percentile"

**Métriques candidats** :
- OC%, OH%, OL%, HL%, HC%, LC%, Vol%
- RSI, Stoch, Williams %R, CCI, MFI
- BB width, BB position (%)
- Volume relatif (volume actuel / moyenne volume N périodes)

#### Tâches détaillées E.2

- [ ] **E.2.1** — Module de calcul de percentile rank sur fenêtre glissante
- [ ] **E.2.2** — API `GET /api/metrics/percentile?metric=oc_pct&window=500`
- [ ] **E.2.3** — Mettre à disposition comme fonction dans les expressions de conditions : `percentile("oc_pct", 500) > 90`
- [ ] **E.2.4** — Cache des percentiles (éviter de recalculer à chaque close)

### E.3 Bar highlighting conditionnel

**Principe** : Colorer les bougies qui satisfont des critères statistiques spécifiques.

**Implémentation** :
- Même mécanisme que D.1 (marqueurs / zones colorées)
- Couleurs configurables par condition (ex: OC% > 90e percentile → fond violet)
- Utilisable indépendamment des conditions de trading (pour l'analyse visuelle)

#### Tâches détaillées E.3

- [ ] **E.3.1** — Étendre le highlighting pour les filtres statistiques
- [ ] **E.3.2** — Palette de couleurs configurables par condition/filtre
- [ ] **E.3.3** — Toggle ON/OFF par filtre
- [ ] **E.3.4** — Légende des couleurs sur le chart

### E.4 Éditeur de métriques

**Principe** : Interface pour configurer les métriques sources des filtres.

**Implémentation** :
- Menu déroulant : sélectionner la métrique source (OC%, HL%, volume, RSI, BB width, etc.)
- Sélection du point de comparaison (BB low→high, RSI lowest→highest, etc.)
- Seuils configurables (sliders : "> 90e percentile", "< 10e percentile")

#### Tâches détaillées E.4

- [ ] **E.4.1** — UI de sélection de métrique source (dropdown)
- [ ] **E.4.2** — Comparateur configurable (>, <, between, outside)
- [ ] **E.4.3** — Sliders pour les seuils
- [ ] **E.4.4** — Persistance de la configuration

### E.5 Seuils utilisateur

**Principe** : Inputs pour définir ce qui constitue un percentile "haut" ou "bas".

**Implémentation** :
- Pour chaque métrique : champ "seuil haut" (ex: 90), champ "seuil bas" (ex: 10)
- Sliders avec valeurs par défaut (90/10)
- Persistance par paire/timeframe ou globale

#### Tâches détaillées E.5

- [ ] **E.5.1** — Inputs de configuration des seuils (sliders ou number inputs)
- [ ] **E.5.2** — Persistance des seuils (localStorage ou API)
- [ ] **E.5.3** — Application des seuils dans l'évaluateur de conditions

---

## Première condition : Ichimoku Trend

### Définition

```python
ichimoku_chikou > ichimoku_tenkan
AND ichimoku_chikou > ichimoku_kijun
AND ichimoku_chikou > ichimoku_senkou_a
AND ichimoku_chikou > ichimoku_senkou_b
AND close > ichimoku_tenkan
AND close > ichimoku_kijun
AND close > ichimoku_senkou_a
AND close > ichimoku_senkou_b
```

**Bullish** (toutes vraies) → ✅ bar highlighting vert
**Bearish** (toutes inversées : chikou + close < toutes les lignes) → ❌ bar highlighting rouge
**Neutre** → pas de highlighting

### Configuration par défaut

| Propriété | Valeur |
|-----------|--------|
| trigger_type | `on_close` (par défaut) |
| Actions activées par défaut | bar highlighting ONLY |
| Notifications | OFF (user doit activer) |
| Webhook | OFF (user doit configurer) |
| Cooldown | 60 secondes |

### Expression en JSON

```json
{
  "name": "Ichimoku Trend Bullish",
  "trigger_type": "on_close",
  "expression": {
    "operator": "AND",
    "conditions": [
      { "left": "ichimoku_chikou", "op": "gt", "right": "ichimoku_tenkan" },
      { "left": "ichimoku_chikou", "op": "gt", "right": "ichimoku_kijun" },
      { "left": "ichimoku_chikou", "op": "gt", "right": "ichimoku_senkou_a" },
      { "left": "ichimoku_chikou", "op": "gt", "right": "ichimoku_senkou_b" },
      { "left": "close", "op": "gt", "right": "ichimoku_tenkan" },
      { "left": "close", "op": "gt", "right": "ichimoku_kijun" },
      { "left": "close", "op": "gt", "right": "ichimoku_senkou_a" },
      { "left": "close", "op": "gt", "right": "ichimoku_senkou_b" }
    ]
  },
  "actions": [
    {
      "action_type": "bgcolor",
      "config": {
        "bull_color": "#00ff0044",
        "bear_color": "#ff000044"
      },
      "enabled": true
    }
  ]
}
```

### Expression Bearish (inversée)

```json
{
  "name": "Ichimoku Trend Bearish",
  "trigger_type": "on_cross",
  "expression": {
    "operator": "AND",
    "conditions": [
      { "left": "ichimoku_chikou", "op": "lt", "right": "ichimoku_tenkan" },
      { "left": "ichimoku_chikou", "op": "lt", "right": "ichimoku_kijun" },
      { "left": "ichimoku_chikou", "op": "lt", "right": "ichimoku_senkou_a" },
      { "left": "ichimoku_chikou", "op": "lt", "right": "ichimoku_senkou_b" },
      { "left": "close", "op": "lt", "right": "ichimoku_tenkan" },
      { "left": "close", "op": "lt", "right": "ichimoku_kijun" },
      { "left": "close", "op": "lt", "right": "ichimoku_senkou_a" },
      { "left": "close", "op": "lt", "right": "ichimoku_senkou_b" }
    ]
  },
  "actions": [ ... ]
}
```

---

## Sources d'inspiration

| Projet | Fonctionnalité à emprunter |
|--------|---------------------------|
| **TradingView** | Format webhook JSON, UI des alertes, cooldown, templates de message |
| **Jesse** | Système de conditions par filtres, multi-timeframe, boucle live |
| **3Commas** | SmartTrade (entry + SL + TP), bots DCA, gestion des stoploss |
| **Freqtrade** | Pairlist filters, hyperopt, intégration Telegram, backtesting avancé |
| **OctoBot** | Évaluateurs multiples, interfaces web, stratégies composites |
| **Gekko** | Interface utilisateur simple, trading en arrière-plan |

---

## Glossaire

| Terme | Définition |
|-------|-----------|
| **Condition** | Expression logique évaluée sur des valeurs d'indicateurs (ex: `chikou > tenkan AND close > kijun`) |
| **Action** | Effet déclenché quand une condition est vraie (bar highlight, notification, ordre) |
| **Trigger** | Événement qui déclenche l'évaluation (close de bougie, cross, tick) |
| **Canal de livraison** | Moyen de recevoir une notification (Telegram, Discord, Email, Webhook) |
| **Bar highlighting** | Coloration du fond d'une bougie sur le chart |
| **Kill switch** | Arrêt d'urgence de toute activité de trading |
| **Paper trading** | Simulation d'exécution sans argent réel |
| **Percentile rank** | Classement d'une valeur par rapport à son historique (0-100) |
| **Rolling window** | Fenêtre glissante de N bougies pour les calculs statistiques |
| **Cooldown** | Temps minimum entre deux déclenchements d'une même condition |

---

*Document généré le 31 mai 2026 — Phase 3 du roadmap*
