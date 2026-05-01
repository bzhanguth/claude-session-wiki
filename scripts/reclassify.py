#!/usr/bin/env python3
"""
Re-scan all session .md files and update YAML frontmatter (project, topic,
subtopic, topics list, summary) using the current classifier rules.

Use after editing PROJECT_RULES / TOPIC_RULES / SUBTOPIC_RULES in config.py.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import config
from classifier import classify_session
from claude_to_obsidian import extract_text_blocks, JSONL_ROOTS

VAULT_DIR    = Path(config.VAULT_DIR).expanduser()
SESSIONS_DIR = VAULT_DIR / config.SESSIONS_SUBDIR

FM_RE = re.compile(r'^---\n(.*?)\n---\n', re.DOTALL)


def find_jsonl(sid: str):
    if not sid:
        return None
    for r in JSONL_ROOTS:
        p = r / f"{sid}.jsonl"
        if p.exists():
            return p
    return None


def read_jsonl_text(p: Path):
    title = ""
    parts = []
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "ai-title" and not title:
            title = obj.get("aiTitle", "").strip()
        elif obj.get("type") in ("user", "assistant"):
            msg = obj.get("message", {})
            t = extract_text_blocks(msg.get("content", []) if isinstance(msg, dict) else [])
            if t:
                parts.append(t)
    return title, " ".join(parts)[:80000]


def parse_fm(text: str):
    m = FM_RE.match(text)
    return (m.group(1), text[m.end():]) if m else (None, text)


def fm_to_dict(fm_text: str):
    out = {}
    cur = None
    for line in fm_text.splitlines():
        if line.startswith("  - "):
            if cur is not None:
                cur.append(line[4:].strip().strip('"'))
            continue
        if ":" in line:
            k, _, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if v == "":
                cur = []
                out[k] = cur
            else:
                out[k] = v.strip('"')
                cur = None
    return out


def render_fm(fm: dict) -> str:
    order = ["title", "date", "session_id", "project", "topic", "subtopic",
             "topics", "summary", "tags"]
    written = set()
    lines = ["---"]
    for k in order:
        if k not in fm:
            continue
        v = fm[k]
        if isinstance(v, list):
            lines.append(f"{k}:")
            for it in v:
                lines.append(f'  - "{it}"')
        elif k in ("title", "summary"):
            lines.append(f'{k}: "{v}"')
        else:
            lines.append(f"{k}: {v}")
        written.add(k)
    for k, v in fm.items():
        if k in written:
            continue
        if isinstance(v, list):
            lines.append(f"{k}:")
            for it in v:
                lines.append(f'  - "{it}"')
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    updated = no_jsonl = skipped = 0
    for md in sorted(SESSIONS_DIR.rglob("*.md")):
        if md.parent.name == "projects" or md.name in ("claude.md", "INDEX.md"):
            continue
        text = md.read_text(encoding="utf-8")
        fm_text, body = parse_fm(text)
        if fm_text is None:
            skipped += 1
            continue
        fm = fm_to_dict(fm_text)
        sid = fm.get("session_id", "")
        jsonl = find_jsonl(sid)
        if not jsonl:
            no_jsonl += 1
            continue
        title, full_text = read_jsonl_text(jsonl)
        if not title:
            title = fm.get("title", md.stem)
        cls = classify_session(title, full_text)
        fm["project"]  = cls["project"]
        fm["topic"]    = cls["topic"]
        fm["subtopic"] = cls["subtopic"]
        if cls["topics"]:
            fm["topics"] = cls["topics"]
        if cls["summary"]:
            fm["summary"] = cls["summary"]

        if args.dry_run:
            print(f"  [DRY] {md.relative_to(SESSIONS_DIR)}  → {cls['project']} / {cls['topic']}")
            continue
        md.write_text(render_fm(fm) + body, encoding="utf-8")
        updated += 1

    print(f"\nUpdated {updated} sessions. {no_jsonl} had no JSONL. {skipped} skipped.")


if __name__ == "__main__":
    main()
