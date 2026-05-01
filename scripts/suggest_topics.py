#!/usr/bin/env python3
"""
Suggest sub-topic candidates for crowded (project, topic) groups.

For each group with > THRESHOLD sessions, ranks candidate technical terms
by TF-IDF (common in this group, rare in the rest of the vault) and prefers
identifiers (underscore/digit) over generic English words.

Adopt a suggestion by adding it to SUBTOPIC_RULES in config.py, then run
`python3 scripts/reclassify.py`.

Usage:
    python3 suggest_topics.py
    python3 suggest_topics.py --threshold 10
    python3 suggest_topics.py --project Research --topic "Code & data"
"""

import argparse
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import config

VAULT_DIR    = Path(config.VAULT_DIR).expanduser()
SESSIONS_DIR = VAULT_DIR / config.SESSIONS_SUBDIR
RAW_DIR      = SESSIONS_DIR / "raw"

STOPWORDS = {
    "the","a","an","and","or","to","of","in","for","on","with","is","this","that",
    "i","you","we","it","as","be","have","has","are","do","does","did","can",
    "could","should","will","would","what","when","where","how","why","but","so",
    "if","then","from","by","at","your","my","their","they","she","he","us","our",
    "claude","session","file","use","using","run","make","get","set","found","good",
    "need","want","let","see","look","check","first","last","next","more","less",
    "very","all","any","now","just","like","also","well","really","might","still",
    "only","much","many","over","under","into","out","off","up","down","new","old",
    "user","help","task","work","time","way","case","one","two","three","line",
    "code","file","data","model","value","function","return","print","test",
    "result","output","input","read","write","add","fix","issue","problem",
    "error","correct","wrong","right","yes","clear","mode","note","based","since",
    "actually","really","probably","likely","maybe","sure","fine","ready","done",
    "complete","start","end","begin","tool","tools","instead","update","change",
    "thing","real","local","locally","currently","behavior","defaults","speed",
    "find","computed","memory","files","verify","design","running","pass","fails",
    "calls","logic","mono","constraint","replace","regardless","smoke",
}

CAND_RE = re.compile(r'\b[A-Za-z][A-Za-z0-9_]{2,30}\b')


def parse_fm(path: Path) -> dict:
    out = {}
    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.startswith("---"):
        return out
    end = text.find("\n---", 3)
    if end == -1:
        return out
    for line in text[3:end].splitlines():
        if ":" in line and not line.startswith("  - "):
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip().strip('"')
    return out


def candidate_terms(text: str) -> set:
    out = set()
    for t in CAND_RE.findall(text):
        low = t.lower()
        if low in STOPWORDS or low.isdigit():
            continue
        out.add(low)
    return out


def session_text(path: Path, max_chars=30000) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]


def collect_groups(threshold: int, only_project=None, only_topic=None):
    """Return dict (proj, topic) → [path] for crowded groups."""
    groups = defaultdict(list)
    for f in RAW_DIR.glob("*.md"):
        fm = parse_fm(f)
        proj  = fm.get("project")
        topic = fm.get("topic")
        if not proj or not topic or proj == "Misc / Admin" or proj == "Misc":
            continue
        if only_project and proj != only_project:
            continue
        if only_topic and topic != only_topic:
            continue
        groups[(proj, topic)].append(f)
    return {k: v for k, v in groups.items() if len(v) > threshold}


def build_corpus_df():
    df = Counter()
    n = 0
    for f in RAW_DIR.glob("*.md"):
        n += 1
        for t in candidate_terms(session_text(f)):
            df[t] += 1
    return df, n


def existing_subtopic_kws(project: str, topic: str) -> set:
    out = set()
    rules = config.SUBTOPIC_RULES.get((project, topic), [])
    for _, kws in rules:
        for kw in kws:
            out.add(kw.lower())
    return out


def is_technical(term: str) -> bool:
    return "_" in term or any(c.isdigit() for c in term)


def analyze_group(project: str, topic: str, paths: list,
                  corpus_df: Counter, corpus_n: int, top_n: int):
    print(f"\n{'='*70}")
    print(f"## {project} / {topic}  ({len(paths)} sessions)")
    print(f"{'='*70}")

    existing = existing_subtopic_kws(project, topic)
    row_df = Counter()
    term_to_files = defaultdict(set)
    for f in paths:
        terms = candidate_terms(session_text(f))
        for t in terms:
            if t in existing:
                continue
            row_df[t] += 1
            term_to_files[t].add(f.stem)

    n = len(paths)
    upper = max(3, int(n * 0.7))
    scored = []
    for t, rc in row_df.items():
        if not (3 <= rc <= upper):
            continue
        cf = corpus_df.get(t, 1)
        idf = math.log((corpus_n + 1) / (cf + 1)) + 1
        scored.append((t, rc, cf, (rc / n) * idf))
    scored.sort(key=lambda x: -x[3])

    print(f"\n  {'term':<22}  {'in_row':>7}  {'corpus':>8}  {'score':>6}  example")
    for term, rc, cf, score in scored[:top_n]:
        sample = sorted(term_to_files[term])[0][:50]
        print(f"  {term:<22}  {rc:>3}/{n}  {cf:>5}/{corpus_n}  {score:>6.2f}  {sample}")

    if scored:
        print(f"\n  Suggested SUBTOPIC_RULES entries (technical identifiers preferred):\n")
        ranked = sorted(scored, key=lambda x: (not is_technical(x[0]), -x[3]))
        used = set()
        shown = 0
        for term, rc, cf, score in ranked:
            if shown >= 4:
                break
            sset = term_to_files[term]
            if len(used & sset) > len(sset) * 0.8:
                continue
            used.update(sset)
            name = term.replace("_", " ").title()
            tag  = "[tech]" if is_technical(term) else "[generic — review]"
            print(f'    ("{name}",  [{term!r}]),  {tag}')
            print(f"      → ~{len(sset)} sessions, e.g., {sorted(sset)[0][:55]}")
            shown += 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--threshold", type=int, default=12)
    p.add_argument("--project", help="Restrict to a single project")
    p.add_argument("--topic",   help="Restrict to a single topic")
    p.add_argument("--top",     type=int, default=12)
    args = p.parse_args()

    groups = collect_groups(args.threshold, args.project, args.topic)
    if not groups:
        print(f"No (project, topic) groups exceed {args.threshold} sessions.")
        return

    print(f"Building corpus document-frequency index over {RAW_DIR}...")
    corpus_df, corpus_n = build_corpus_df()
    print(f"Indexed {corpus_n} sessions, {len(corpus_df)} unique terms.")

    for (proj, topic), paths in groups.items():
        analyze_group(proj, topic, paths, corpus_df, corpus_n, args.top)

    print(f"\n{'='*70}")
    print("To adopt: add the printed entry to SUBTOPIC_RULES in config.py,")
    print("then run: python3 scripts/reclassify.py")


if __name__ == "__main__":
    main()
