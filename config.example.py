"""
claude-session-wiki configuration.

Copy this file to `config.py` and edit the values for your setup.
The skill reads only `config.py`; this `config.example.py` stays as a reference.
"""

from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
# Where your Obsidian vault lives.
VAULT_DIR = Path.home() / "Documents" / "Obsidian Vault"

# Subfolder inside the vault where session files & MOCs go.
SESSIONS_SUBDIR = "claude-sessions"

# Where Claude Code stores JSONL transcripts. Add every project root you use.
# Find them under `~/.claude/projects/` — one folder per cwd you've launched
# Claude Code from. Example below; adapt to your machine.
JSONL_PROJECT_ROOTS = [
    Path.home() / ".claude" / "projects" / "-Users-YOURNAME",
]

# ── Scheduling ───────────────────────────────────────────────────────────────
# Daily sync time (24-hour clock). Used by `init` to register launchd/cron.
SYNC_HOUR   = 17
SYNC_MINUTE = 30

# ── Classification rules ─────────────────────────────────────────────────────
# Each session is auto-tagged with project / topic / subtopic by keyword
# matching against title + full conversation text.
#
# PROJECT_RULES: list of (project_name, [keywords]). First match wins.
PROJECT_RULES = [
    ("Work",      ["jira", "ticket", "stand-up", "sprint", "deploy"]),
    ("Research",  ["paper", "thesis", "dissertation", "experiment", "hypothesis"]),
    ("Personal",  ["family", "trip", "calendar", "shopping"]),
    ("Learning",  ["tutorial", "course", "book", "study"]),
    ("Tools",     ["script", "config", "install", "setup", "fix bug"]),
]

# TOPIC_RULES[project] = [(topic_name, [keywords])]. Empty keywords = catch-all.
# Each session within a project gets the FIRST matching topic.
TOPIC_RULES = {
    "Work": [
        ("Bug fixes",     ["bug", "fix", "error", "broken"]),
        ("Code review",   ["review", "feedback", "pr ", "pull request"]),
        ("Architecture",  ["design", "architecture", "schema"]),
        ("General",       []),
    ],
    "Research": [
        ("Literature",    ["paper", "citation", "bibliography"]),
        ("Code & data",   ["script", "data", "analysis", "plot"]),
        ("Writing",       ["draft", "manuscript", "section", "chapter"]),
        ("General",       []),
    ],
    "Tools": [
        ("Setup",         ["install", "configure", "setup"]),
        ("Debugging",     ["debug", "crash", "error"]),
        ("General",       []),
    ],
    # Catch-all projects can omit topic rules entirely.
}

# SUBTOPIC_RULES[(project, topic)] = [(subtopic_name, [keywords])]
# Optional. Use only when a (project, topic) row gets crowded; run
# `python3 scripts/suggest_topics.py` to surface candidate keywords.
SUBTOPIC_RULES = {
    # ("Research", "Code & data"): [
    #     ("Plotting",   ["matplotlib", "ggplot", "figure"]),
    #     ("Modeling",   ["regression", "model", "fit"]),
    # ],
}

# ── Classifier tuning ────────────────────────────────────────────────────────
MIN_CROSSREF_SCORE = 3      # min keyword hits to add a cross-reference
CROSSPROJ_RATIO    = 0.4    # cross-project ref must score ≥ this × primary
MAX_CROSSREFS      = 5      # max cross-reference projects per session

# ── Project rendering order in dashboard / MOCs ──────────────────────────────
PROJECT_ORDER = ["Work", "Research", "Personal", "Learning", "Tools", "Misc"]
