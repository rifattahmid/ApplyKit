import json
import os

import config
from constants import SPECIALIST_THRESHOLD, TITLE_MULTIPLIER


# =============================================================================
# Paths
# =============================================================================

_KEYWORDS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keywords.json")


# =============================================================================
# Keyword Loading
# =============================================================================

def load_keywords(path=None):
    keywords_path = path or _KEYWORDS_PATH
    if not os.path.exists(keywords_path):
        print("  WARNING: keywords.json not found -- all categories will score 0. Copy keywords.example.json to keywords.json to fix this.")
        return {}, set()
    with open(keywords_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    broad = {c.lower() for c in data.get("_broad_categories", [])}
    keywords = {k.lower(): v for k, v in data.items() if not k.startswith("_")}
    return keywords, broad


# =============================================================================
# Public Classification API
# =============================================================================

def classify_job(title, description, *, template_base=None, keyword_loader=load_keywords):
    """Match a job to an available template category and print score details."""
    title_text = (title or "").lower()
    desc_text = (description or "").lower()
    base = template_base or config.TEMPLATE_BASE
    available = [
        f for f in os.listdir(base)
        if os.path.isdir(os.path.join(base, f))
    ]

    keywords, broad_categories = keyword_loader()

    # Score only folders that actually exist, so classification cannot select a
    # category that has no templates.
    scores = {folder: 0 for folder in available}
    title_scores = {folder: 0 for folder in available}

    for folder in available:
        for kw in keywords.get(folder.lower(), []):
            if kw in title_text:
                scores[folder] += TITLE_MULTIPLIER
                title_scores[folder] += TITLE_MULTIPLIER
            if kw in desc_text:
                scores[folder] += 1

    best = max(scores, key=lambda f: scores[f]) if scores else available[0]

    # Title evidence is treated as stronger than description-only evidence. This
    # keeps broad job descriptions from overpowering a precise role title.
    title_override = False
    if title_scores.get(best, 0) == 0:
        title_candidates = [f for f in available if title_scores.get(f, 0) > 0]
        if title_candidates:
            best = max(title_candidates, key=lambda f: (title_scores[f], scores[f]))
            title_override = True

    if not title_override:
        top_score = scores[best]
        if sum(1 for v in scores.values() if v == top_score) > 1:
            title_tied = [
                f for f in available
                if scores.get(f, 0) == top_score and title_scores.get(f, 0) > 0
            ]
            if title_tied:
                best = max(title_tied, key=lambda f: (title_scores[f], scores[f]))
            else:
                available_lower = {f.lower(): f for f in available}
                for preferred in ("investment", "m&a", "finance", "accounting", "esg", "economics", "fund accounting"):
                    if preferred in available_lower and scores.get(available_lower[preferred], -1) == top_score:
                        best = available_lower[preferred]
                        break

    # If a broad category wins, allow a specialist category to override when it
    # has enough evidence. This keeps "Finance" from swallowing niche folders.
    if best.lower() in broad_categories:
        specialists = [
            f for f in available
            if f.lower() not in broad_categories and scores.get(f, 0) > 0
        ]
        if specialists:
            top_specialist = max(specialists, key=lambda f: (
                title_scores.get(f, 0),
                1 if f.lower() in title_text else 0,
                scores[f],
            ))
            specialist_has_title = title_scores.get(top_specialist, 0) > 0
            specialist_name_in_title = top_specialist.lower() in title_text
            broad_has_title = title_scores.get(best, 0) > 0
            if scores[top_specialist] >= scores[best] * SPECIALIST_THRESHOLD and (specialist_has_title or not broad_has_title):
                best = top_specialist
            elif specialist_has_title and specialist_name_in_title:
                best = top_specialist

    # Print the scorecard because the CLI lets the user override this choice.
    print(f"  Job classified as: {best}\n")
    print("  Scores:")
    for folder in sorted(scores):
        marker = " <--" if folder == best else ""
        print(f"    {folder:<20} {scores[folder]:>2}  (title: {title_scores.get(folder, 0)}){marker}")
    print()
    return best
