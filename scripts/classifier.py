"""
Multi-topic classifier. Loads rules from user config and scores a session
across project / topic / subtopic by keyword frequency.
"""

import sys
from pathlib import Path

# Allow `from config import ...` from the repo root regardless of cwd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    import config
except ImportError:
    raise SystemExit(
        "ERROR: config.py not found. Copy config.example.py to config.py "
        f"in {ROOT} and edit it for your setup."
    )


def classify_session(title: str, full_text: str) -> dict:
    """
    Multi-topic classification by keyword frequency.

    Returns:
        {
            "project":  primary project name,
            "topic":    primary topic within that project,
            "subtopic": subtopic (if SUBTOPIC_RULES match), else "General",
            "topics":   [str] — list of "Project | Topic" cross-references,
            "summary":  short one-line topic summary,
        }
    """
    text = (title + " " + full_text).lower()

    # 1. Score every project by keyword frequency
    proj_scores = {}
    for proj, kws in config.PROJECT_RULES:
        score = sum(text.count(kw.lower()) for kw in kws)
        if score > 0:
            proj_scores[proj] = score

    if not proj_scores:
        return {"project": "Misc", "topic": "General",
                "subtopic": "General", "topics": [], "summary": ""}

    primary_project = max(proj_scores, key=proj_scores.get)
    primary_score   = proj_scores[primary_project]

    # 2. Score every topic in every scoring project
    matched = []   # (project, topic, score)
    for proj in proj_scores:
        for top, kws in config.TOPIC_RULES.get(proj, []):
            if not kws:
                continue
            score = sum(text.count(kw.lower()) for kw in kws)
            if score > 0:
                matched.append((proj, top, score))

    # 3. Primary topic = top-scoring topic within primary project
    primary_topic = "General"
    best_topic_score = -1
    for p, t, s in matched:
        if p == primary_project and s > best_topic_score:
            primary_topic, best_topic_score = t, s
    if best_topic_score < 0:
        # fall back to declared catch-all topic
        for top, kws in config.TOPIC_RULES.get(primary_project, []):
            if not kws:
                primary_topic = top
                break

    # 4. Cross-references with two filters:
    #    (a) topic score >= MIN_CROSSREF_SCORE
    #    (b) cross-project's project score must be >= CROSSPROJ_RATIO × primary
    matched.sort(key=lambda x: -x[2])
    seen = set()
    topics_list = []
    for p, t, s in matched:
        if s < config.MIN_CROSSREF_SCORE:
            continue
        if p != primary_project:
            if proj_scores[p] < config.CROSSPROJ_RATIO * primary_score:
                continue
        key = (p, t)
        if key in seen:
            continue
        seen.add(key)
        topics_list.append(f"{p} | {t}")
        if len(topics_list) >= config.MAX_CROSSREFS:
            break

    # 5. Subtopic detection
    subtopic = "General"
    rules = config.SUBTOPIC_RULES.get((primary_project, primary_topic))
    if rules:
        for name, kws in rules:
            if any(kw.lower() in text for kw in kws):
                subtopic = name
                break

    summary = " · ".join(t.split(" | ")[1] for t in topics_list[:4])

    return {
        "project":  primary_project,
        "topic":    primary_topic,
        "subtopic": subtopic,
        "topics":   topics_list,
        "summary":  summary,
    }
