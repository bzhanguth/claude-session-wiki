# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows [SemVer](https://semver.org/).

## [1.1.2] - 2026-05-04

### Added

- **GLM-4.7 (z-ai) support on NIM.** The script now auto-injects `chat_template_kwargs: {"enable_thinking": false}` for any model id starting with `z-ai/` or containing `glm`. Without this flag GLM hangs the same way DeepSeek did. Tested: `z-ai/glm4.7` returns in ~44s on a real 6KB session (~3× slower than llama-70b but better technical detail in tested outputs).

### Fixed

- **SSE parser handles empty `choices` arrays** sent by some NIM models (notably z-ai). Previously raised `IndexError` and the session would fall back to a skeleton bullet.

## [1.1.1] - 2026-05-04

### Fixed

- **DeepSeek-v4 models on NIM** now work. The script auto-injects `chat_template_kwargs: {"thinking": false}` for any model id containing `deepseek` — without this flag NIM hangs indefinitely on every request (a reasoning-mode quirk). `deepseek-ai/deepseek-v4-flash` returns in ~14s warm. Note: `deepseek-v4-pro` still times out today due to a provider-side outage; switch to `flash` or `meta/llama-3.1-70b-instruct` if you hit it.

## [1.1.0] - 2026-05-04

### Added

- **Weekly summary generator** (`scripts/weekly_summary.py`). Reads exported sessions from the vault, groups them by project for an ISO week, and writes `<vault>/<sessions>/weekly/YYYY-Wnn.md`. Optional Ollama integration produces 2-3 narrative bullets per session ("what was accomplished, decisions made, bugs fixed"). Cross-week continuity comes from a `prev:` frontmatter link, an auto-detected "Carryover threads" section (sessions started in prior weeks that advanced this week), and per-session `first_date → last_date` ranges in the output.
- **Weekly launchd job** (`templates/launchd-weekly.plist`). `init.py` now optionally registers a Monday 06:00 cron (configurable via `WEEKLY_WEEKDAY` / `WEEKLY_HOUR` / `WEEKLY_MINUTE`). Comment out `WEEKLY_HOUR` in `config.py` to skip the weekly job.
- **Two LLM backends** for narrative generation, selectable via `WEEKLY_BACKEND`:
  - `nim` — NVIDIA hosted OpenAI-compatible API (uses `NVIDIA_API_KEY` env). Default model `meta/llama-3.1-70b-instruct`. Streams SSE so cold-start latency is bounded; recommended on CPU-only machines.
  - `ollama` — local Ollama daemon. Default model `llama3.2:latest` (3B; the prior 14B default was intractable on Intel Mac CPUs).
  - Auto-detection: if `NVIDIA_API_KEY` is set the script defaults to NIM, otherwise Ollama. Either backend falls back to a skeleton bullet (`_(LLM unavailable: …)_`) on error so the rest of the summary still renders.

### Fixed

- **Daily sync now refreshes ongoing sessions.** `--since N` previously filtered by the session's *first* timestamp, so any session started before the cutoff was skipped even if it had been edited within the window. It now uses the *last* message timestamp.
- **Existing notes are auto-rewritten when the source JSONL is newer.** Previously the script skipped any filename that already existed in the vault, leaving long-running sessions frozen at their first export. The skip now compares mtimes, so updated sessions are refreshed in place without needing `--overwrite`.

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
