---
name: github-backup
description: >
  Push the current project state to GitHub. Checks for local changes, commits
  them with a descriptive message (date + summary), and pushes to origin main.
  Falls back from SSH to HTTPS with a token from .env if SSH fails.
---

# GitHub Backup

## Trigger phrases

- "backup"
- "push"
- "save to GitHub"
- "git push"
- "commit and push"
- "push to remote"

## Procedure

Run these steps **in order** in the project root (`/home/anymous/PROJETS/candle-analytics`).

### 1. Check for changes

```bash
git status
```

If the working tree is clean (nothing to commit), print `Nothing to push — working tree clean` and stop. No need to proceed further.

### 2. Stage all files

```bash
git add -A
```

### 3. Build commit message

Generate a short summary of what changed. Use the date + a compact description.

```bash
SUMMARY=$(git diff --cached --stat --name-only | head -20 | tr '\n' ' ')
DATE=$(date '+%Y-%m-%d')
git commit -m "backup $DATE — $SUMMARY"
```

If the diff is empty after `git add -A` (shouldn't happen if step 1 found changes), fall back to:

```bash
git commit -m "backup $(date '+%Y-%m-%d')"
```

### 4. Push to `origin main`

```bash
git push origin main 2>&1
```

Capture the exit code. If it succeeds → **done** (proceed to verification step 6).

### 5. SSH failure → fallback to HTTPS with token

If step 4 fails (SSH key unavailable, permission denied, etc.), fall back:

```bash
# Source .env to get GITHUB_TOKEN or GH_TOKEN
set -a
source .env 2>/dev/null || true
set +a

TOKEN="${GITHUB_TOKEN:-$GH_TOKEN}"
if [ -z "$TOKEN" ]; then
  echo "ERROR: SSH push failed and no GITHUB_TOKEN or GH_TOKEN found in .env"
  echo "Set GITHUB_TOKEN=<your-token> in .env and try again."
  exit 1
fi

# Build HTTPS remote (SSH-style URL -> HTTPS with token)
# git@github.com:Noelas-Saensch/candle-analytics.git
# -> https://<token>@github.com/Noelas-Saensch/candle-analytics.git
HTTPS_REMOTE="https://${TOKEN}@github.com/Noelas-Saensch/candle-analytics.git"
git push "$HTTPS_REMOTE" main 2>&1
```

### 6. Verify push succeeded

```bash
git log --oneline -3 origin/main
```

This should show your latest commit at the top. If the output contains your commit message from step 3, the backup is confirmed.

---

## Security note

`.env` is listed in `.gitignore` — tokens stored there are **never** committed to the repository. See `.gitignore` line 1.

---

## Rollback (if push fails irrecoverably)

If **both** SSH and HTTPS with token fail:

1. **Check remote URL** is correct:
   ```bash
   git remote -v
   ```
   Expected: `origin	git@github.com:Noelas-Saensch/candle-analytics.git (push)`

2. **Check SSH agent** has the key loaded:
   ```bash
   ssh-add -l
   ```
   If "The agent has no identities", load it:
   ```bash
   eval "$(ssh-agent -s)" && ssh-add ~/.ssh/id_ed25519
   ```

3. **Check token permissions** — the GitHub token needs `repo` scope.

4. If the remote has diverged (forced push needed), **do NOT force push** without asking the user. Present the situation:
   ```bash
   git log --oneline origin/main..HEAD   # commits you have that remote doesn't
   git log --oneline HEAD..origin/main   # commits remote has that you don't
   ```
   Ask the user how to proceed.
