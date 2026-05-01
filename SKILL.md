---
name: claude-session-wiki
description: Sync Claude Code conversation history into an Obsidian vault as a wiki, with auto-classified projects, topics, subtopics, and Dataview-rendered Maps of Content. Use when the user asks to back up Claude sessions, search past conversations, or build a personal knowledge base from their work with Claude.
---

# claude-session-wiki

Turns the user's Claude Code JSONL transcripts into a self-organizing Obsidian vault.

## Setup (first run)

1. Edit `config.py` (copy from `config.example.py`) — set `VAULT_DIR`, `JSONL_PROJECT_ROOTS`, and `PROJECT_RULES`.
2. Run `python3 scripts/init.py` from this skill's directory.
3. Open the user's Obsidian vault → install the **Dataview** community plugin → reload.

## Routine commands

| User intent | Run |
|---|---|
| "Sync new Claude sessions to Obsidian" | `python3 scripts/claude_to_obsidian.py --since 2` |
| "Re-classify everything after I edited the rules" | `python3 scripts/reclassify.py` |
| "A topic looks crowded — suggest subtopics" | `python3 scripts/suggest_topics.py` |
| "Set up automatic daily sync" | `python3 scripts/init.py` (registers macOS launchd or prints Linux crontab line) |

## How classification works

Each session is scored against `PROJECT_RULES` and `TOPIC_RULES` in `config.py` by keyword frequency over the **full** transcript. The session lands in:

- `project:` — highest-scoring project
- `topic:`   — highest-scoring topic within that project
- `subtopic:` — first matching `SUBTOPIC_RULES[(project, topic)]` entry, else `General`
- `topics:`  — list of cross-references where the cross-project's score ≥ `CROSSPROJ_RATIO × primary` (default 0.4) and topic score ≥ `MIN_CROSSREF_SCORE` (default 3)

These tags drive Dataview queries in the per-project MOC pages.

## Files

```
.
├── SKILL.md             # this file
├── config.example.py    # config template
├── scripts/             # Python tools
├── templates/           # MOC + dashboard templates
└── examples/            # sample configs (researcher, engineer, personal)
```

## When NOT to use

- The user wants live Claude integration inside Obsidian — use a different plugin.
- The user wants real-time chat, not retroactive sync.

## Privacy note to surface for the user

This skill writes the **full conversation text** to the vault as plaintext Markdown. If sessions contain credentials, private code, or sensitive info, advise the user to either filter those sessions out (delete the JSONL) or keep the vault out of any cloud sync.
