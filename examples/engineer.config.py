"""
Example config: software engineer.
Copy this file to ../config.py and edit paths/keywords.
"""

from pathlib import Path

VAULT_DIR       = Path.home() / "Documents" / "Obsidian Vault"
SESSIONS_SUBDIR = "claude-sessions"

JSONL_PROJECT_ROOTS = [
    Path.home() / ".claude" / "projects" / "-Users-YOURNAME",
    Path.home() / ".claude" / "projects" / "-Users-YOURNAME-projects-myrepo",
]

SYNC_HOUR, SYNC_MINUTE = 18, 0

PROJECT_RULES = [
    ("Backend",   ["api", "endpoint", "database", "schema", "migration"]),
    ("Frontend",  ["react", "component", "css", "tailwind", "ui"]),
    ("DevOps",    ["docker", "kubernetes", "ci/cd", "deploy", "terraform"]),
    ("Data",      ["pipeline", "etl", "airflow", "spark", "snowflake"]),
    ("Tools",     ["script", "automation", "config", "shell"]),
    ("Learning",  ["tutorial", "course", "book", "study"]),
]

TOPIC_RULES = {
    "Backend": [
        ("Bug fixes",    ["bug", "fix", "error", "broken"]),
        ("Architecture", ["design", "schema", "interface"]),
        ("Performance",  ["slow", "latency", "optimize", "profile"]),
        ("Tests",        ["test", "pytest", "jest", "mock"]),
        ("General",      []),
    ],
    "Frontend": [
        ("Bug fixes",    ["bug", "fix"]),
        ("Styling",      ["css", "tailwind", "responsive"]),
        ("State",        ["redux", "zustand", "context"]),
        ("General",      []),
    ],
    "DevOps": [
        ("Deployments",  ["deploy", "release", "rollback"]),
        ("Monitoring",   ["alert", "grafana", "prometheus"]),
        ("General",      []),
    ],
}

SUBTOPIC_RULES = {}
MIN_CROSSREF_SCORE = 3
CROSSPROJ_RATIO    = 0.4
MAX_CROSSREFS      = 5
PROJECT_ORDER      = ["Backend", "Frontend", "DevOps", "Data",
                      "Tools", "Learning", "Misc"]
