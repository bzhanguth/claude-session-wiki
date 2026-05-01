---
title: {{PROJECT_NAME}}
tags: [moc, claude-sessions]
---

# {{PROJECT_NAME}}

{{PROJECT_DESCRIPTION}}

---

## Sessions by topic + subtopic

```dataview
TABLE WITHOUT ID
  topic AS Topic,
  subtopic AS Subtopic,
  file.link AS Session,
  summary AS Summary
FROM "{{SESSIONS_PATH}}/raw"
WHERE project = "{{PROJECT_NAME}}"
SORT topic ASC, subtopic ASC, date ASC
```

## Cross-referenced from other projects

```dataview
TABLE WITHOUT ID
  project AS "From project",
  topic AS Topic,
  file.link AS Session,
  summary AS Summary
FROM "{{SESSIONS_PATH}}/raw"
WHERE project != "{{PROJECT_NAME}}"
  AND contains(string(topics), "{{PROJECT_NAME}}")
SORT date DESC
```
