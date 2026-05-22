#!/usr/bin/env python3
"""
Analyze session logs across all projects.
Finds repeated questions/topics using Ollama embeddings + cosine similarity clustering.

Usage:
    python3 scripts/analyze_sessions.py
    python3 scripts/analyze_sessions.py --project candle-analytics
    python3 scripts/analyze_sessions.py --threshold 0.7
"""

import argparse
import re
import sys
from pathlib import Path

import httpx
import numpy as np

OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
SEARCH_ROOTS = [
    Path("/home/anymous/PROJETS"),
    Path("/home/anymous/Documents/DEV & CODE"),
]
SIMILARITY_THRESHOLD = 0.65
MIN_MESSAGE_LENGTH = 15


def discover_sessions(project: str | None = None) -> list[dict]:
    sessions = []
    roots = [Path(p) for p in SEARCH_ROOTS]

    if project:
        found = False
        for r in roots:
            candidate = r / project
            if candidate.exists():
                roots = [candidate]
                found = True
                break
        if not found:
            p = Path(project)
            if p.exists():
                roots = [p]
            else:
                print(f"ERROR: project '{project}' not found at any known root.")
                sys.exit(1)

    for root in roots:
        for sess_dir in root.rglob("sessions_upload"):
            if not sess_dir.is_dir():
                continue
            rel = sess_dir.parent.relative_to(root) if sess_dir.parent != root else Path(sess_dir.parent.name)
            project_name = str(rel)
            for f in sorted(sess_dir.glob("*.md")):
                sessions.append({"project": project_name, "path": f})
    return sessions


def parse_user_messages(session: dict) -> list[dict]:
    text = session["path"].read_text(encoding="utf-8", errors="replace")
    messages = []
    blocks = re.split(r'^## User\s*$', text, flags=re.MULTILINE)

    for block in blocks[1:]:
        content = re.split(r'^## |^---', block, flags=re.MULTILINE)[0].strip()
        if not content:
            continue
        cleaned = clean_message(content)
        if len(cleaned) >= MIN_MESSAGE_LENGTH:
            messages.append({
                "project": session["project"],
                "file": str(session["path"]),
                "raw": content,
                "cleaned": cleaned,
            })
    return messages


def clean_message(text: str) -> str:
    text = re.sub(r'```.+?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`[^`]+`', '', text)
    text = re.sub(r'\*\*Tool:.*?\*\*.*?(?=\n\n|\Z)', '', text, flags=re.DOTALL)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def check_ollama() -> bool:
    try:
        r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        r.raise_for_status()
        models = [m["name"] for m in r.json().get("models", [])]
        if not any(EMBED_MODEL in m for m in models):
            print(f"WARNING: '{EMBED_MODEL}' not found. Pull it: ollama pull {EMBED_MODEL}")
            return False
        return True
    except httpx.ConnectError:
        print("ERROR: Ollama is not running. Start with: ollama serve")
        return False


def embed_texts(texts: list[str]) -> np.ndarray:
    valid, indices = [], []
    for i, t in enumerate(texts):
        if len(t) >= MIN_MESSAGE_LENGTH:
            valid.append(t)
            indices.append(i)

    if not valid:
        return np.zeros((len(texts), 768))

    resp = httpx.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": EMBED_MODEL, "input": valid},
        timeout=120,
    )
    resp.raise_for_status()
    all_embeddings = resp.json()["embeddings"]

    dim = len(all_embeddings[0]) if all_embeddings else 768
    result = np.zeros((len(texts), dim))
    for idx, emb in zip(indices, all_embeddings):
        result[idx] = emb
    return result


class UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x: int, y: int):
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        if self.rank[rx] < self.rank[ry]:
            self.parent[rx] = ry
        elif self.rank[rx] > self.rank[ry]:
            self.parent[ry] = rx
        else:
            self.parent[ry] = rx
            self.rank[rx] += 1


def cluster_messages(embeddings: np.ndarray, threshold: float) -> list[list[int]]:
    n = embeddings.shape[0]
    if n == 0:
        return []

    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = embeddings / norms
    sim = normalized @ normalized.T

    uf = UnionFind(n)
    for i in range(n):
        for j in range(i + 1, n):
            if sim[i, j] >= threshold:
                uf.union(i, j)

    groups: dict[int, list[int]] = {}
    for i in range(n):
        root = uf.find(i)
        groups.setdefault(root, []).append(i)

    return sorted(groups.values(), key=len, reverse=True)


def generate_report(
    messages: list[dict],
    clusters: list[list[int]],
    embeddings: np.ndarray,
) -> str:
    lines = []
    projects = len(set(m["project"] for m in messages))
    files = len(set(m["file"] for m in messages))
    total = len(messages)

    header = "Session Audit Report"
    sep = "=" * 50
    lines.append(sep)
    lines.append(f"  {header}")
    lines.append(f"  {projects} projects · {files} session files · {total} user messages")
    lines.append(sep)
    lines.append("")

    if not clusters:
        lines.append("No messages to analyze.")
        return "\n".join(lines)

    singles = 0
    for cluster in clusters:
        if len(cluster) == 1:
            singles += 1
            continue

        indices = cluster
        cluster_msgs = [messages[i] for i in indices]

        centroid = embeddings[indices].mean(axis=0)
        cn = np.linalg.norm(centroid)
        if cn > 0:
            centroid = centroid / cn

        norms = np.linalg.norm(embeddings[indices], axis=1)
        norms[norms == 0] = 1
        sims = (embeddings[indices] / norms[:, np.newaxis]) @ centroid
        rep_idx = indices[np.argmax(sims)]
        rep_msg = cluster_msgs[np.argmax(sims)]["cleaned"]
        if len(rep_msg) > 120:
            rep_msg = rep_msg[:117] + "..."

        count = len(indices)
        tag = {5: "HIGH", 3: "MEDIUM"}.get(next((k for k in (5, 3) if count >= k), 0), "LOW")
        icon = {5: "🔴", 3: "🟡"}.get(next((k for k in (5, 3) if count >= k), 0), "🟢")

        lines.append(f'{icon} [{tag}] Asked {count}× — "{rep_msg}"')
        for i in indices:
            m = messages[i]
            fname = Path(m["file"]).stem
            short = m["cleaned"][:80] + "..." if len(m["cleaned"]) > 80 else m["cleaned"]
            lines.append(f"     📍 {m['project']} / {fname}")
            lines.append(f"       → {short}")
        lines.append("")

    lines.append("-" * 50)
    repeated = len(clusters) - singles
    lines.append(f"{repeated} repeated topics · {singles} unique (one-off) messages")
    lines.append(f"Similarity threshold: > {SIMILARITY_THRESHOLD}")
    lines.append(f"Embedding model: {EMBED_MODEL} (Ollama)")

    return "\n".join(lines)


def main():
    global EMBED_MODEL, SIMILARITY_THRESHOLD

    parser = argparse.ArgumentParser(description="Analyze session logs for repeated topics")
    parser.add_argument("--project", help="Limit to a specific project name")
    parser.add_argument("--threshold", type=float, default=SIMILARITY_THRESHOLD,
                        help=f"Similarity threshold (default: {SIMILARITY_THRESHOLD})")
    parser.add_argument("--model", default=EMBED_MODEL,
                        help=f"Ollama embedding model (default: {EMBED_MODEL})")
    args = parser.parse_args()

    if args.model:
        EMBED_MODEL = args.model
    if args.threshold:
        SIMILARITY_THRESHOLD = args.threshold

    print("🔍 Discovering session files...")
    sessions = discover_sessions(args.project)
    if not sessions:
        print("No session files found.")
        return
    projects = set(s["project"] for s in sessions)
    print(f"   Found {len(sessions)} session files in {len(projects)} project(s): {', '.join(sorted(projects))}")

    print("📄 Parsing user messages...")
    all_messages = []
    for sess in sessions:
        all_messages.extend(parse_user_messages(sess))
    print(f"   Extracted {len(all_messages)} user messages (min {MIN_MESSAGE_LENGTH} chars)")

    if not all_messages:
        print("No user messages found.")
        return

    print(f"🧠 Embedding with '{EMBED_MODEL}' via Ollama...")
    if not check_ollama():
        sys.exit(1)
    cleaned = [m["cleaned"] for m in all_messages]
    embeddings = embed_texts(cleaned)
    print(f"   Got {len(embeddings)} embeddings, dim={embeddings.shape[1] if embeddings.ndim > 1 else '?'}")

    print(f"🔗 Clustering (threshold={SIMILARITY_THRESHOLD})...")
    clusters = cluster_messages(embeddings, SIMILARITY_THRESHOLD)
    print(f"   Found {len(clusters)} topic clusters")
    print()

    report = generate_report(all_messages, clusters, embeddings)
    print(report)


if __name__ == "__main__":
    main()
