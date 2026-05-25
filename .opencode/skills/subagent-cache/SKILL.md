---
name: subagent-cache
description: >
  Caches task/explore sub-agent results to timestamped files so they can be
  reused instead of re-running expensive searches. Checks cache before
  launching new agents and returns cached results if fresh (<7 days old).
---

# Sub-agent Cache

## Trigger

This skill activates **before** and **after** every `task` or `explore` agent invocation:

- **After** the agent returns results → save to cache
- **Before** launching a new agent → check cache first

---

## Procedure

### 1. Before running any sub-agent

Search the cache for matching results before launching:

```bash
grep -riL "<topic-keyword>" .opencode/cache/subagent/ 2>/dev/null
```

If a cached file exists **and is less than 7 days old**, read it and return its contents instead of running the agent:

```bash
CACHE_DIR=".opencode/cache/subagent"
TOPIC="$1"
MATCH=$(grep -ril "$TOPIC" "$CACHE_DIR" 2>/dev/null | head -1)
if [ -n "$MATCH" ] && [ $(($(date +%s) - $(date -r "$MATCH" +%s))) -lt $((7*24*3600)) ]; then
  cat "$MATCH"
  exit 0
fi
```

### 2. After agent returns results

Save agent output via the helper script:

```bash
bash scripts/cache-subagent.sh "<topic>" "<tags>" /path/to/agent/output
```

Or manually write the cached file (see format below).

### 3. Cache file format

Each cached result is a timestamped markdown file:

```markdown
# <topic> — YYYY-MM-DD HH:MM:SS

## Summary
<brief summary of what was found>

## Full Results
<full agent output>

## Tags
<comma-separated tags for search>
```

The filename convention is: `YYYY-MM-DD_HHMMSS_<topic-slug>.md`

### 4. Cache expiry

Cache entries older than **7 days** are considered stale. Check age with:

```bash
find .opencode/cache/subagent/ -name "*.md" -mtime +7 -ls
```

### 5. Clearing the cache

Delete all cached results at any time:

```bash
rm -rf .opencode/cache/subagent/
```

After clearing, re-create the directory:

```bash
mkdir -p .opencode/cache/subagent/
```

---

## Quick reference

| Action | Command |
|--------|---------|
| Search cache for a topic | `grep -ril "<keyword>" .opencode/cache/subagent/` |
| Check cache entry age | `find .opencode/cache/subagent/ -name "*.md" -mtime +7 -ls` |
| Save agent output | `bash scripts/cache-subagent.sh "<topic>" "<tags>" <input_file>` |
| Clear all cache | `rm -rf .opencode/cache/subagent/` |
| Count cached entries | `ls .opencode/cache/subagent/*.md 2>/dev/null \| wc -l` |
