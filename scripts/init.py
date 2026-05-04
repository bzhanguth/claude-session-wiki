#!/usr/bin/env python3
"""
Set up the vault layout and (optionally) the daily sync cron.

Run this once after editing config.py:

    python3 scripts/init.py            # scaffold + register cron
    python3 scripts/init.py --no-cron  # scaffold only, skip cron
"""

import argparse
import getpass
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config

VAULT_DIR    = Path(config.VAULT_DIR).expanduser()
SESSIONS_DIR = VAULT_DIR / config.SESSIONS_SUBDIR
RAW_DIR      = SESSIONS_DIR / "raw"
PROJECTS_DIR = SESSIONS_DIR / "projects"

SESSIONS_PATH_REL = f"{config.SESSIONS_SUBDIR}"   # used inside Dataview FROM


def render_template(name: str, replacements: dict) -> str:
    text = (ROOT / "templates" / name).read_text(encoding="utf-8")
    for k, v in replacements.items():
        text = text.replace("{{" + k + "}}", v)
    return text


def project_names():
    seen = []
    for proj, _ in config.PROJECT_RULES:
        if proj not in seen:
            seen.append(proj)
    if "Misc" not in seen:
        seen.append("Misc")
    return seen


def scaffold_vault():
    if not VAULT_DIR.exists():
        print(f"ERROR: Vault dir does not exist: {VAULT_DIR}")
        print("Edit VAULT_DIR in config.py to point at your Obsidian vault.")
        sys.exit(1)

    SESSIONS_DIR.mkdir(exist_ok=True)
    RAW_DIR.mkdir(exist_ok=True)
    PROJECTS_DIR.mkdir(exist_ok=True)

    # Build dashboard
    proj_links = "\n".join(
        f"- [[{p.replace(' ', '-').replace('/', '-')}|{p}]]"
        for p in project_names()
    )
    dash = render_template("claude.md", {
        "PROJECT_LINKS": proj_links,
        "SESSIONS_PATH": SESSIONS_PATH_REL,
    })
    (SESSIONS_DIR / "claude.md").write_text(dash, encoding="utf-8")
    print(f"  ✓ Wrote {SESSIONS_DIR / 'claude.md'}")

    # Build per-project MOCs
    for proj in project_names():
        slug = proj.replace(' ', '-').replace('/', '-')
        moc = render_template("project_moc.md", {
            "PROJECT_NAME":        proj,
            "PROJECT_DESCRIPTION": f"Auto-rendered list of sessions classified as **{proj}**.",
            "SESSIONS_PATH":       SESSIONS_PATH_REL,
        })
        (PROJECTS_DIR / f"{slug}.md").write_text(moc, encoding="utf-8")
        print(f"  ✓ Wrote {PROJECTS_DIR / f'{slug}.md'}")

    print(f"\nVault scaffold ready at: {SESSIONS_DIR}")
    print("Open `claude.md` in Obsidian. Install the Dataview plugin if you haven't.")


def _install_plist(plist_path: Path, plist_text: str):
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    plist_path.write_text(plist_text, encoding="utf-8")
    subprocess.run(["launchctl", "unload", str(plist_path)],
                   stderr=subprocess.DEVNULL)
    subprocess.run(["launchctl", "load", str(plist_path)], check=True)


def register_cron_macos():
    user   = getpass.getuser()
    python = shutil.which("python3") or "/usr/bin/python3"
    log_path = Path.home() / "Library" / "Logs" / "claude-session-wiki.log"

    # Daily sync
    daily_plist = Path.home() / "Library" / "LaunchAgents" / f"com.{user}.claude-session-wiki.plist"
    _install_plist(daily_plist, render_template("launchd.plist", {
        "USER":        user,
        "PYTHON":      python,
        "SCRIPT_PATH": str(ROOT / "scripts" / "claude_to_obsidian.py"),
        "HOUR":        str(config.SYNC_HOUR),
        "MINUTE":      str(config.SYNC_MINUTE),
        "LOG_PATH":    str(log_path),
    }))
    print(f"  ✓ Daily sync registered: fires at {config.SYNC_HOUR:02d}:{config.SYNC_MINUTE:02d} → {daily_plist}")

    # Weekly summary (optional — only if WEEKLY_HOUR is set)
    if hasattr(config, "WEEKLY_HOUR"):
        weekly_plist = Path.home() / "Library" / "LaunchAgents" / f"com.{user}.claude-session-wiki-weekly.plist"
        weekly_log   = Path.home() / "Library" / "Logs" / "claude-session-wiki-weekly.log"
        _install_plist(weekly_plist, render_template("launchd-weekly.plist", {
            "USER":        user,
            "PYTHON":      python,
            "SCRIPT_PATH": str(ROOT / "scripts" / "weekly_summary.py"),
            "WEEKDAY":     str(getattr(config, "WEEKLY_WEEKDAY", 1)),
            "HOUR":        str(config.WEEKLY_HOUR),
            "MINUTE":      str(getattr(config, "WEEKLY_MINUTE", 0)),
            "LOG_PATH":    str(weekly_log),
        }))
        wd_name = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"][getattr(config, "WEEKLY_WEEKDAY", 1)]
        print(f"  ✓ Weekly summary registered: fires {wd_name} {config.WEEKLY_HOUR:02d}:"
              f"{getattr(config, 'WEEKLY_MINUTE', 0):02d} → {weekly_plist}")
    print(f"  ✓ Logs: {log_path}")


def register_cron_linux():
    cron_line = (
        f"{config.SYNC_MINUTE} {config.SYNC_HOUR} * * * "
        f"{shutil.which('python3') or 'python3'} "
        f"{ROOT / 'scripts' / 'claude_to_obsidian.py'} --since 2 "
        f">> {Path.home() / '.claude-session-wiki.log'} 2>&1"
    )
    print("\nAdd this line to your crontab (`crontab -e`):\n")
    print(f"  {cron_line}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--no-cron", action="store_true",
                   help="Skip cron/launchd registration")
    args = p.parse_args()

    print(f"Initializing claude-session-wiki at {VAULT_DIR}\n")
    scaffold_vault()

    if args.no_cron:
        return

    sysname = platform.system()
    print()
    if sysname == "Darwin":
        register_cron_macos()
    elif sysname == "Linux":
        register_cron_linux()
    else:
        print(f"  ! Auto-cron not supported on {sysname}. Run sync manually:")
        print(f"      python3 {ROOT / 'scripts' / 'claude_to_obsidian.py'} --since 2")


if __name__ == "__main__":
    main()
