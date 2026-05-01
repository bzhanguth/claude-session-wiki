#!/usr/bin/env python3
"""
Export Claude Code conversation sessions to Obsidian Markdown notes.

Usage:
    python3 claude_to_obsidian.py              # all sessions, skip existing
    python3 claude_to_obsidian.py --since 7    # only sessions from last N days
    python3 claude_to_obsidian.py --session ID # single session by id prefix
    python3 claude_to_obsidian.py --dry-run    # preview without writing
    python3 claude_to_obsidian.py --overwrite  # replace existing files
"""

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import config
from classifier import classify_session

VAULT_DIR    = Path(config.VAULT_DIR).expanduser()
SESSIONS_DIR = VAULT_DIR / config.SESSIONS_SUBDIR
RAW_DIR      = SESSIONS_DIR / "raw"

JSONL_ROOTS  = [Path(p).expanduser() for p in config.JSONL_PROJECT_ROOTS]

MIN_MESSAGES   = 2
MAX_TEXT_BLOCK = 4000


def extract_text_blocks(content):
    parts = []
    if isinstance(content, str):
        return content.strip()
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            t = block.get("text", "").strip()
            if t:
                parts.append(t)
    return "\n\n".join(parts)


def parse_session(path: Path):
    title = ""
    first_ts = None
    messages = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return None
    for raw in lines:
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        otype = obj.get("type", "")
        if otype == "ai-title" and not title:
            t = obj.get("aiTitle", "").strip()
            if t:
                title = t
        ts = obj.get("timestamp")
        if ts and first_ts is None:
            first_ts = ts
        if otype in ("user", "assistant"):
            msg = obj.get("message", {})
            content = msg.get("content", []) if isinstance(msg, dict) else []
            text = extract_text_blocks(content)
            if not text:
                continue
            if otype == "user" and (text.startswith("Base directory for this skill:") or len(text) >= 8000):
                continue
            if MAX_TEXT_BLOCK and len(text) > MAX_TEXT_BLOCK:
                text = text[:MAX_TEXT_BLOCK] + f"\n\n…*(truncated, {len(text)} chars total)*"
            messages.append((otype, text))
    if not title:
        title = path.stem[:40]
    return {"session_id": path.stem, "title": title,
            "timestamp": first_ts, "messages": messages, "path": path}


def ts_to_dt(ts):
    if not ts:
        return None
    try:
        return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def safe_filename(title, dt):
    date_prefix = dt.strftime("%Y-%m-%d") if dt else "0000-00-00"
    slug = re.sub(r'[^\w\s\-]', '', title).strip()
    slug = re.sub(r'\s+', ' ', slug)[:70]
    return f"{date_prefix} {slug}.md"


def render_markdown(session):
    dt = ts_to_dt(session["timestamp"])
    date_str = dt.strftime("%Y-%m-%d %H:%M UTC") if dt else "unknown"
    date_iso = dt.date().isoformat() if dt else ""
    title = session["title"]
    sid = session["session_id"]

    full_text = " ".join(t for _, t in session["messages"])[:80000]
    cls = classify_session(title, full_text)

    lines = [
        "---",
        f'title: "{title}"',
        f"date: {date_iso}",
        f"session_id: {sid}",
        f"project: {cls['project']}",
        f"topic: {cls['topic']}",
        f"subtopic: {cls['subtopic']}",
    ]
    if cls["topics"]:
        lines.append("topics:")
        for tp in cls["topics"]:
            lines.append(f'  - "{tp}"')
    if cls["summary"]:
        lines.append(f'summary: "{cls["summary"]}"')
    lines += [
        'tags: [claude, conversation]',
        "---",
        "",
        f"# {title}",
        "",
        f"*{date_str} — Session `{sid[:8]}`*",
        "",
        "---",
        "",
    ]
    for role, text in session["messages"]:
        lines.append("**You:**" if role == "user" else "**Claude:**")
        lines.append("")
        lines.append(text)
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--since", type=int, metavar="DAYS")
    p.add_argument("--session", type=str, metavar="ID")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--overwrite", action="store_true")
    args = p.parse_args()

    cutoff = None
    if args.since:
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=args.since)

    files = []
    for root in JSONL_ROOTS:
        if root.exists():
            files.extend(root.glob("*.jsonl"))

    if args.session:
        files = [f for f in files if f.stem.startswith(args.session)]

    print(f"Found {len(files)} JSONL files in {len(JSONL_ROOTS)} project roots")

    exported = skipped = too_short = 0
    for fpath in sorted(files):
        s = parse_session(fpath)
        if s is None:
            continue
        dt = ts_to_dt(s["timestamp"])
        if cutoff and dt and dt < cutoff:
            continue
        if len(s["messages"]) < MIN_MESSAGES:
            too_short += 1
            continue
        fname = safe_filename(s["title"], dt)
        if any(SESSIONS_DIR.rglob(fname)) and not args.overwrite:
            skipped += 1
            continue
        if args.dry_run:
            print(f"  [DRY] raw/{fname}  ({len(s['messages'])} msgs)")
            continue
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        (RAW_DIR / fname).write_text(render_markdown(s), encoding="utf-8")
        date = dt.strftime("%Y-%m-%d") if dt else "?"
        print(f"  ✓ {date}  {s['title'][:55]}")
        exported += 1

    print(f"\nDone: {exported} exported, {skipped} skipped, {too_short} too short")


if __name__ == "__main__":
    main()
