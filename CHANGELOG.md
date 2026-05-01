# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows [SemVer](https://semver.org/).

## [1.0.0] - 2026-05-01

Initial public release.

### Features
- **Multi-topic classifier**: scores each session against `PROJECT_RULES`, `TOPIC_RULES`, and `SUBTOPIC_RULES` by keyword frequency over the full transcript.
- **Cross-references**: a session touching multiple projects appears in every relevant MOC, filtered by `MIN_CROSSREF_SCORE` and `CROSSPROJ_RATIO` to avoid false positives.
- **Auto-generated Obsidian Maps of Content**: per-project pages with Dataview queries. Add a session → it appears in the right MOC instantly. No rebuild step needed.
- **TF-IDF subtopic suggester** (`scripts/suggest_topics.py`): surfaces candidate sub-bucket terms for crowded rows; prefers technical identifiers over generic English.
- **Daily auto-sync**: macOS `launchd` agent (auto-registered by `init.py`) or Linux `crontab` line (printed by `init.py`).
- **3 example configs**: researcher, engineer, personal use cases.
- **Claude Code skill manifest** (`SKILL.md`): clone into `~/.claude/skills/claude-session-wiki/` and invoke from inside Claude Code.

### Privacy
- All session text is written as plaintext Markdown. README highlights this and recommends keeping the vault out of cloud sync if sessions contain sensitive content.
