"""
Example config: PhD student / academic researcher.
Copy this file to ../config.py and edit paths/keywords.
"""

from pathlib import Path

VAULT_DIR       = Path.home() / "Documents" / "Obsidian Vault"
SESSIONS_SUBDIR = "claude-sessions"

JSONL_PROJECT_ROOTS = [
    Path.home() / ".claude" / "projects" / "-Users-YOURNAME",
]

SYNC_HOUR, SYNC_MINUTE = 17, 30

PROJECT_RULES = [
    ("Project-1",   ["project1", "manuscript", "main paper"]),
    ("Project-2",   ["project2", "follow-up", "extension"]),
    ("Dissertation",["dissertation", "proposal", "committee"]),
    ("Coursework", ["assignment", "homework", "lecture"]),
    ("Tools",      ["script", "config", "install"]),
    ("Personal",   ["family", "trip", "calendar"]),
]

TOPIC_RULES = {
    "Project-1": [
        ("Code & simulation", ["simulation", "monte carlo", "rcpp"]),
        ("Writing",           ["section", "intro", "discussion"]),
        ("Literature",        ["paper", "citation", "bib"]),
        ("General",           []),
    ],
    "Project-2": [
        ("Code & simulation", ["simulation", "code", "function"]),
        ("Writing",           ["section", "intro"]),
        ("General",           []),
    ],
    "Dissertation": [
        ("Timeline",   ["timeline", "schedule", "milestone"]),
        ("Committee",  ["committee", "advisor", "meeting"]),
        ("Progress",   ["progress", "report", "weekly"]),
        ("General",    []),
    ],
}

SUBTOPIC_RULES = {}
MIN_CROSSREF_SCORE = 3
CROSSPROJ_RATIO    = 0.4
MAX_CROSSREFS      = 5
PROJECT_ORDER      = ["Project-1", "Project-2", "Dissertation",
                      "Coursework", "Tools", "Personal", "Misc"]
