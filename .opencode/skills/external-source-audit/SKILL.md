# Skill: external-source-audit

> Analyse de sécurité pour scripts, skills, outils externes (sources non fiables par défaut).

## Quand utiliser

- Avant d'importer ou exécuter un script, skill, ou outil externe
- Après `git clone` d'un dépôt inconnu
- Avant d'exécuter un fichier téléchargé (`.sh`, `.py`, `.js`, binaire)
- Pour auditer un skill opencode avant de l'activer
- En complément de la section "External Sources Security" dans `AGENTS.md`

## Utilisation

```bash
# Analyser un fichier
./scripts/analyze-external-source.sh /tmp/untrusted-script.sh

# Analyser un dossier (dépôt cloné, skill complet)
./scripts/analyze-external-source.sh /path/to/some-repo/

# Analyser le projet lui-même (auto-audit)
./scripts/analyze-external-source.sh /home/anymous/PROJETS/candle-analytics

# Analyser plusieurs sources
./scripts/analyze-external-source.sh script1.py script2.sh /some/dir/
```

## Codes de sortie

| Code | Risque | Action recommandée |
|------|--------|-------------------|
| 0 | LOW | Peut être exécuté après revue rapide |
| 1 | MEDIUM | Examiner manuellement les warnings avant exécution |
| 2 | HIGH | Ne PAS exécuter. Revoir en détail ou sandboxer dans Docker |

## Checks effectués

### Par type de fichier

- **Python (`.py`)** : eval, exec, __import__, subprocess, os.system, socket, ctypes, pickle, crypto, network calls, file I/O
- **Shell (`.sh`)** : curl/wget, /dev/tcp, eval, chmod 777, cron/startup persistence, disk access, sudo, iptables
- **JavaScript (`.js`)** : eval, Function constructor, DOM injection, Node.js system modules, fetch/XHR, crypto
- **YAML (`.yml`)** : priviliged containers, host network, system volume binds, latest tags
- **Binaires** : détection de type, analyse strings pour patterns suspects
- **SKILL.md** : écriture dans /etc/ /var/ /tmp/, rm -rf, sudo, curl/wget

### Checks globaux

- Obfuscation : base64 strings, hex constants, lignes minifiées (>400 chars)
- Signatures malware : coin miners, ransomware, backdoor, C2, keylogger, process injection
- Fichiers cachés/suspects : `.`files, exécutables non-shell
- Structure : fichiers vides, binaires pré-compilés, présence README/license

## Exemples

```bash
# Analyser un skill téléchargé
cd /tmp && git clone https://github.com/example/some-skill
~/PROJETS/candle-analytics/scripts/analyze-external-source.sh some-skill/

# Analyser un script avant de l'exécuter
~/PROJETS/candle-analytics/scripts/analyze-external-source.sh ./downloaded-script.sh
echo $?  # 0 = OK, 1 = médium, 2 = HIGH
```

## Intégration

Ce skill est le complément pratique de la section "External Sources Security" dans `USERS_DOCUMENT/project-docs/AGENTS.md` (OpenSSF Scorecard, Trivy, Semgrep, Bandit). Il fournit une analyse rapide sans dépendances externes, utilisable immédiatement.

Pour une analyse approfondie des dépôts GitHub, utiliser aussi :
```bash
npx @openssf/scorecard --repo=github.com/owner/repo
trivy fs /path/to/repo
semgrep --config=auto /path/to/repo
```

## Base

- Script: `scripts/analyze-external-source.sh`
- Skill: `.opencode/skills/external-source-audit/SKILL.md`
