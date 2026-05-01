"""
Example config: general-purpose / personal.
Copy this file to ../config.py and edit paths/keywords.
"""

from pathlib import Path

VAULT_DIR       = Path.home() / "Documents" / "Obsidian Vault"
SESSIONS_SUBDIR = "claude-sessions"

JSONL_PROJECT_ROOTS = [
    Path.home() / ".claude" / "projects" / "-Users-YOURNAME",
]

SYNC_HOUR, SYNC_MINUTE = 22, 0

PROJECT_RULES = [
    ("Writing",     ["essay", "draft", "blog", "newsletter"]),
    ("Side-Projects", ["side project", "personal project", "weekend"]),
    ("Health",      ["workout", "diet", "sleep", "habit"]),
    ("Finance",     ["budget", "invest", "tax"]),
    ("Travel",      ["trip", "flight", "booking", "itinerary"]),
    ("Learning",    ["course", "tutorial", "book"]),
    ("Tools",       ["script", "automation"]),
]

TOPIC_RULES = {
    "Writing": [
        ("Drafting",  ["draft", "outline"]),
        ("Editing",   ["revise", "edit"]),
        ("General",   []),
    ],
    "Side-Projects": [
        ("Planning",  ["plan", "design", "spec"]),
        ("Building",  ["code", "implement"]),
        ("General",   []),
    ],
}

SUBTOPIC_RULES = {}
MIN_CROSSREF_SCORE = 3
CROSSPROJ_RATIO    = 0.4
MAX_CROSSREFS      = 5
PROJECT_ORDER      = ["Writing", "Side-Projects", "Health",
                     "Finance", "Travel", "Learning", "Tools", "Misc"]
