# Synthèse — Planification Phase 3 : Alertes / Conditions / Automation

> Généré le 31 mai 2026

## Résumé

Session de planification pure (zéro code) dédiée à la documentation complète du système d'Alertes/Conditions/Automation qui remplacera TradingView Alerts + Webhooks + Paper Trading.

## Document créé

**`USERS_DOCUMENT/project-docs/ALERTES_CONDITIONS_AUTOMATION.md`** (300+ lignes)

### Architecture (5 layers)
Data Layer → Indicator Compute → Condition Engine → Trigger Pipeline → Delivery Layer

### 5 sections de tâches
- **A — Infrastructure** : Parseur d'expressions, moteur de triggers (on_close/on_cross/realtime/once), persistence SQLite (3 tables : conditions, actions, historique), CRUD API
- **B — Canaux de livraison** : Bar highlighting (chart), SSE Toast, Telegram Bot, Discord Webhook, Email SMTP, Webhook TradingView-compatible, WhatsApp (optionnel)
- **C — Exécution d'ordres** : Paper Trading (extension StrategySandbox), Live CCXT, Kill Switch (drawdown/pertes/erreurs), Position Sizing
- **D — Chart & UI** : Triggers visuels, panneau de configuration, live trigger log, performance dashboard (equity curve, drawdown)
- **E — Filtres statistiques (HAUTE PRIORITÉ)** : Amplitude OHLCV%, Percentile rank (rolling window), Bar highlighting conditionnel, éditeur de métriques, seuils utilisateur

### Première condition
Ichimoku Trend (8 clauses AND, bull/bear, expression JSON complète fournie)

### ROADMAP
Phase 3 refondue avec 5 sous-sections (A-E) et liens vers le document dédié.

## Prochaine session
Commencer l'implémentation selon les priorités définies par l'utilisateur.
