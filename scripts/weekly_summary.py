#!/usr/bin/env python3
"""
Generate a weekly summary of Claude Code sessions exported to Obsidian.

Reads session frontmatter from `claude-sessions/raw/`, looks up each
session's source JSONL to determine when it was last edited, groups by
project, optionally calls an LLM for narrative bullets, and writes
`claude-sessions/weekly/<YYYY-Wnn>.md`.

Two LLM backends are supported (set `WEEKLY_BACKEND` in `config.py`):
  - "nim"     — NVIDIA NIM hosted API (OpenAI-compatible). Fast, requires
                NVIDIA_API_KEY in env. Default model: deepseek-ai/deepseek-v4-pro.
  - "ollama"  — local Ollama daemon. Default model: llama3.2:latest (3B,
                tractable on CPU). Set OLLAMA_MODEL for a heavier model.

Usage:
    weekly_summary.py                        # previous ISO week
    weekly_summary.py --week 2026-W18        # specific week
    weekly_summary.py --no-llm               # skeleton only, no narrative
    weekly_summary.py --backend ollama --model llama3.2:latest
    weekly_summary.py --dry-run              # print to stdout

Designed to be safe to run repeatedly (overwrites the same file).
"""

import argparse
import datetime
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import config

VAULT_DIR    = Path(config.VAULT_DIR).expanduser()
SESSIONS_DIR = VAULT_DIR / config.SESSIONS_SUBDIR
RAW_DIR      = SESSIONS_DIR / "raw"
WEEKLY_DIR   = SESSIONS_DIR / "weekly"
JSONL_ROOTS  = [Path(p).expanduser() for p in config.JSONL_PROJECT_ROOTS]

USE_LLM       = getattr(config, "WEEKLY_USE_OLLAMA", True)  # legacy name kept for back-compat
BACKEND       = getattr(config, "WEEKLY_BACKEND",  "nim" if os.environ.get("NVIDIA_API_KEY") else "ollama")
NIM_URL       = getattr(config, "NIM_URL",         "https://integrate.api.nvidia.com/v1/chat/completions")
NIM_MODEL     = getattr(config, "NIM_MODEL",       "meta/llama-3.1-70b-instruct")
OLLAMA_URL    = getattr(config, "OLLAMA_URL",      "http://localhost:11434/api/generate")
OLLAMA_MODEL  = getattr(config, "OLLAMA_MODEL",    "llama3.2:latest")
PROJECT_ORDER = getattr(config, "PROJECT_ORDER",   [])

MAX_CHARS_PER_SESSION = 6000
LLM_TIMEOUT_S         = 120


def parse_iso_week(s: str):
    m = re.match(r"^(\d{4})-W(\d{1,2})$", s)
    if not m:
        raise ValueError(f"bad week format (expected YYYY-Wnn): {s}")
    year, week = int(m.group(1)), int(m.group(2))
    monday = datetime.date.fromisocalendar(year, week, 1)
    sunday = monday + datetime.timedelta(days=6)
    return year, week, monday, sunday


def previous_iso_week(today=None):
    today = today or datetime.date.today()
    last_sunday = today - datetime.timedelta(days=today.weekday() + 1)
    y, w, _ = last_sunday.isocalendar()
    return y, w


def parse_frontmatter(path: Path):
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None, ""
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return None, text
    fm_block = text[4:end]
    body = text[end + 5:]
    fields = {}
    list_key = None
    for line in fm_block.splitlines():
        if list_key and line.startswith("  - "):
            fields[list_key].append(line[4:].strip().strip('"'))
            continue
        list_key = None
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if not m:
            continue
        k, v = m.group(1).strip(), m.group(2).strip()
        if v == "":
            fields[k] = []
            list_key = k
        else:
            fields[k] = v.strip('"')
    return fields, body


def find_jsonl(session_id: str):
    for root in JSONL_ROOTS:
        for p in root.rglob(f"{session_id}.jsonl"):
            return p
    return None


def collect_sessions(monday: datetime.date, sunday: datetime.date):
    """Walk RAW_DIR, dedupe by session_id (keep newest .md file), filter by week."""
    by_sid = {}
    if not RAW_DIR.exists():
        return []
    for f in sorted(RAW_DIR.glob("*.md")):
        fm, body = parse_frontmatter(f)
        if not fm or "session_id" not in fm:
            continue
        try:
            first_date = datetime.date.fromisoformat(fm.get("date", ""))
        except Exception:
            continue
        sid = fm["session_id"]
        # Dedupe: keep the .md file with the latest mtime (most recent export).
        prev = by_sid.get(sid)
        if prev and prev["file"].stat().st_mtime >= f.stat().st_mtime:
            continue
        jsonl = find_jsonl(sid)
        if jsonl:
            last_date = datetime.datetime.fromtimestamp(jsonl.stat().st_mtime).date()
        else:
            last_date = first_date
        by_sid[sid] = {
            "session_id": sid,
            "title":      fm.get("title", sid),
            "project":    fm.get("project", "Misc / Admin"),
            "topic":      fm.get("topic", "General"),
            "subtopic":   fm.get("subtopic", "General"),
            "first_date": first_date,
            "last_date":  last_date,
            "file":       f,
            "body":       body,
        }
    # Filter by activity window
    return [
        s for s in by_sid.values()
        if s["first_date"] <= sunday and s["last_date"] >= monday
    ]


def _build_prompt(body: str, title: str, project: str) -> str:
    snippet = body[-MAX_CHARS_PER_SESSION:] if len(body) > MAX_CHARS_PER_SESSION else body
    return (
        "You are summarizing a Claude Code coding/research session for a weekly research log.\n\n"
        f"SESSION TITLE: {title}\n"
        f"PROJECT: {project}\n\n"
        "SESSION CONTENT (most recent portion of conversation):\n"
        f"{snippet}\n\n"
        "Write 2-3 concise bullets describing what was actually accomplished, "
        "decisions made, bugs fixed, or open questions raised. Use past tense. "
        "No preamble, no header, no closing remarks. Bullets only, each starting with '- '."
    )


def _post_json(url: str, payload: dict, headers: dict, timeout: int) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def summarize_nim(body: str, title: str, project: str, model: str) -> str:
    """Call NIM via streaming SSE.

    Two NIM-specific quirks handled here:
      1. The non-stream endpoint hangs intermittently on free-tier accounts.
         We always use stream=true and consume SSE chunks.
      2. DeepSeek-v4 reasoning models hang indefinitely unless
         `chat_template_kwargs.thinking` is set explicitly. We force
         `thinking: false` (non-reasoning mode) for any deepseek-v4 model
         since the reasoning path is currently broken on NIM.
    """
    api_key = os.environ.get("NVIDIA_API_KEY", "")
    if not api_key:
        return "- _(LLM unavailable: NVIDIA_API_KEY not set)_"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": _build_prompt(body, title, project)}],
        "max_tokens": 300, "temperature": 0.2, "stream": True,
    }
    if "deepseek" in model.lower():
        payload["chat_template_kwargs"] = {"thinking": False}
    req = urllib.request.Request(
        NIM_URL, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Accept": "text/event-stream",
                 "Authorization": f"Bearer {api_key}"},
    )
    try:
        chunks = []
        with urllib.request.urlopen(req, timeout=LLM_TIMEOUT_S) as resp:
            for raw in resp:
                line = raw.decode("utf-8", errors="ignore").strip()
                if not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    obj = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                delta = obj.get("choices", [{}])[0].get("delta", {})
                tok = delta.get("content")
                if tok:
                    chunks.append(tok)
        return ("".join(chunks)).strip()
    except Exception as e:
        return f"- _(LLM unavailable via NIM: {e.__class__.__name__})_"


def summarize_ollama(body: str, title: str, project: str, model: str) -> str:
    payload = {
        "model": model,
        "prompt": _build_prompt(body, title, project),
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 300},
    }
    try:
        data = _post_json(OLLAMA_URL, payload, {}, LLM_TIMEOUT_S)
        return data.get("response", "").strip()
    except Exception as e:
        return f"- _(LLM unavailable via Ollama: {e.__class__.__name__})_"


def summarize(body: str, title: str, project: str, backend: str, model: str) -> str:
    if backend == "nim":
        return summarize_nim(body, title, project, model)
    return summarize_ollama(body, title, project, model)


def project_sort_key(name: str) -> tuple:
    if name in PROJECT_ORDER:
        return (0, PROJECT_ORDER.index(name))
    return (1, name)


def render(week_str, monday, sunday, sessions, prev_week, use_llm, backend, model):
    by_project = {}
    for s in sessions:
        by_project.setdefault(s["project"], []).append(s)

    days_active = len({s["last_date"] for s in sessions}) if sessions else 0
    carryover  = [s for s in sessions if s["first_date"] < monday]
    new_closed = [s for s in sessions if s["first_date"] >= monday and s["last_date"] <= sunday]

    out = [
        "---",
        f"week: {week_str}",
        f"date_range: {monday.isoformat()} → {sunday.isoformat()}",
        f"sessions: {len(sessions)}",
        f"active_days: {days_active}",
        f"projects: {len(by_project)}",
        f'prev: "[[{prev_week}]]"',
        "tags: [claude, weekly-summary]",
        "---",
        "",
        f"# Week of {monday.strftime('%b %d')} – {sunday.strftime('%b %d, %Y')} ({week_str})",
        "",
        f"**Sessions:** {len(sessions)} · **Active days:** {days_active} · "
        f"**Projects:** {len(by_project)} · **Carryover:** {len(carryover)} · "
        f"**New & closed:** {len(new_closed)}",
        "",
    ]

    if not sessions:
        out += ["_No Claude Code sessions active during this week._", ""]
        return "\n".join(out)

    if carryover:
        out += ["## Carryover threads (continued from prior weeks)", ""]
        for s in sorted(carryover, key=lambda x: x["first_date"]):
            out.append(
                f"- [[{s['file'].stem}]] — started **{s['first_date']}**, "
                f"last edit **{s['last_date']}** *({s['project']} / {s['topic']})*"
            )
        out.append("")

    out += ["## By project", ""]
    for proj in sorted(by_project, key=project_sort_key):
        out.append(f"### {proj}")
        out.append("")
        for s in sorted(by_project[proj], key=lambda x: x["first_date"]):
            tag = "↻" if s in carryover else "•"
            out.append(
                f"- {tag} **[[{s['file'].stem}|{s['title']}]]** "
                f"*({s['topic']} · {s['first_date']}→{s['last_date']})*"
            )
            if use_llm:
                summary = summarize(s["body"], s["title"], s["project"], backend, model)
                for ln in summary.splitlines():
                    ln = ln.rstrip()
                    if not ln.strip():
                        continue
                    if not ln.lstrip().startswith("-"):
                        ln = "- " + ln.lstrip()
                    out.append("    " + ln)
        out.append("")

    out += ["## Next week", "", "_to fill in Monday morning_", ""]
    return "\n".join(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--week", help="ISO week, e.g. 2026-W18 (default: previous week)")
    p.add_argument("--no-llm", action="store_true", help="skip narrative generation")
    p.add_argument("--backend", choices=["nim", "ollama"], default=BACKEND,
                   help=f"LLM backend (default: {BACKEND})")
    p.add_argument("--model", default=None,
                   help="model id (default depends on backend)")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if args.week:
        year, week, monday, sunday = parse_iso_week(args.week)
    else:
        year, week = previous_iso_week()
        monday = datetime.date.fromisocalendar(year, week, 1)
        sunday = monday + datetime.timedelta(days=6)
    week_str = f"{year}-W{week:02d}"

    prev = monday - datetime.timedelta(days=7)
    py, pw, _ = prev.isocalendar()
    prev_week = f"{py}-W{pw:02d}"

    backend = args.backend
    model   = args.model or (NIM_MODEL if backend == "nim" else OLLAMA_MODEL)
    use_llm = USE_LLM and not args.no_llm

    print(f"Generating summary for {week_str}: {monday} → {sunday}  "
          f"(backend={backend if use_llm else 'none'}, model={model if use_llm else '-'})")

    sessions = collect_sessions(monday, sunday)
    print(f"Found {len(sessions)} sessions active during the week")

    md = render(week_str, monday, sunday, sessions, prev_week, use_llm, backend, model)

    if args.dry_run:
        print("--- DRY RUN ---")
        print(md)
        return

    WEEKLY_DIR.mkdir(parents=True, exist_ok=True)
    out_path = WEEKLY_DIR / f"{week_str}.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
