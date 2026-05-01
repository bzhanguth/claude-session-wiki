---
title: Claude Sessions
tags: [moc, claude-sessions]
---

# Claude Sessions

Project → MOC → sessions. All sessions live in `raw/`; per-project pages render them via Dataview.

> Requires the **Dataview** plugin (Settings → Community plugins → Browse → install Dataview).

Sync new sessions: `python3 ~/.claude/skills/claude-session-wiki/scripts/claude_to_obsidian.py --since 2`

---

## Projects

{{PROJECT_LINKS}}

---

## Global stats

```dataview
TABLE WITHOUT ID
  project AS Project,
  length(rows) AS Sessions
FROM "{{SESSIONS_PATH}}/raw"
GROUP BY project
SORT length(rows) DESC
```

## Recent sessions (last 14)

```dataview
TABLE WITHOUT ID
  date AS Date,
  project AS Project,
  topic AS Topic,
  file.link AS Session,
  summary AS Summary
FROM "{{SESSIONS_PATH}}/raw"
SORT date DESC
LIMIT 14
```
