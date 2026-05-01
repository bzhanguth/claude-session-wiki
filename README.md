# claude-session-wiki

Turn your Claude Code conversation history into a self-organizing Obsidian wiki.

Every session you've had with Claude Code lives as a JSONL file under `~/.claude/projects/`. This tool:

1. Exports them as Markdown notes with rich YAML frontmatter
2. Auto-classifies each session into **project / topic / subtopic** by keyword matching against the full transcript
3. Adds **cross-references** when a session touches multiple projects
4. Generates Obsidian Map-of-Content pages that use **Dataview** to render dynamic per-project tables — no rebuild step needed

## Why

Searching `~/.claude/projects/*.jsonl` directly is brutal. Existing Claude+Obsidian tools focus on live integration; this one focuses on **retroactive sync** of every session you ever had, with multi-topic indexing so you can find that one BOR-Platform discussion three weeks later.

## Architecture

```
your-vault/
└── claude-sessions/
    ├── claude.md                  ← dashboard: recent + global stats
    ├── projects/                  ← one MOC page per project, all auto-rendered
    │   ├── Work.md
    │   ├── Research.md
    │   └── Personal.md
    └── raw/                       ← all session files, flat
        ├── 2026-04-13 Found the bug.md
        └── ...
```

Sessions stay in `raw/` flat; project pages query them by YAML frontmatter via Dataview. Add a new session → it appears in the right MOC instantly.

## Install (as a Claude Code skill)

```bash
git clone https://github.com/YOUR_USERNAME/claude-session-wiki ~/.claude/skills/claude-session-wiki
cd ~/.claude/skills/claude-session-wiki
cp config.example.py config.py
# edit config.py: VAULT_DIR, JSONL_PROJECT_ROOTS, PROJECT_RULES
python3 scripts/init.py
```

Then in Obsidian: **Settings → Community plugins → Browse → install Dataview → enable**.

## Sample config snippet

```python
PROJECT_RULES = [
    ("Work",      ["jira", "ticket", "deploy", "sprint"]),
    ("Research",  ["paper", "thesis", "experiment"]),
    ("Personal",  ["family", "trip", "shopping"]),
]
TOPIC_RULES = {
    "Work": [
        ("Bug fixes",     ["bug", "fix", "error"]),
        ("Code review",   ["review", "pr", "pull request"]),
        ("General",       []),     # catch-all (always last)
    ],
}
```

See `examples/` for full sample configs.

## Routine commands

| Task | Command |
|---|---|
| Sync new sessions (last N days) | `python3 scripts/claude_to_obsidian.py --since 2` |
| Re-classify after editing rules | `python3 scripts/reclassify.py` |
| Find candidate subtopics for crowded rows | `python3 scripts/suggest_topics.py` |
| Re-scaffold MOC pages | `python3 scripts/init.py --no-cron` |

`init.py` also registers a daily macOS launchd job by default. On Linux it prints a crontab line. Windows = run manually.

## How classification works

Each session is scored across all `PROJECT_RULES` by keyword frequency over the full conversation text (capped at 80k chars). Two filters keep cross-references useful:

- **`MIN_CROSSREF_SCORE`** (default 3) — incidental mentions don't count
- **`CROSSPROJ_RATIO`** (default 0.4) — a cross-project ref must score ≥ 40% of the primary project's score (prevents a Work session with one passing mention of "research" from polluting the Research MOC)

Subtopics are detected per-`(project, topic)` from `SUBTOPIC_RULES`. Run `suggest_topics.py` to find candidate subtopic keywords for crowded rows — uses TF-IDF, prefers technical identifiers (underscore/digit) over generic English words.

## Privacy

⚠ This tool writes the **full conversation text** to your vault as plaintext Markdown.

If your sessions contain credentials, private code, or anything sensitive:
- Either delete those JSONL files from `~/.claude/projects/` before running, or
- Keep the vault out of cloud sync (iCloud / Dropbox / OneDrive), or
- Encrypt the vault folder

## License

MIT — see [LICENSE](./LICENSE).

## Inspired by

- [Karpathy's LLM Wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- [Maps of Content](https://github.com/seqis/ObsidianMOC) pattern
- [Dataview](https://blacksmithgu.github.io/obsidian-dataview/) plugin
