"""Lightweight structural validation for generated Markdown knowledge packs.

Returns (ok, reasons[]). The pipeline marks failing packs as 'needs_review'
and continues — it never re-runs the agent automatically (cost control).
"""

import re
from dataclasses import dataclass

import yaml

TURKISH_CHARS = set("çÇğĞıİöÖşŞüÜ")
REQUIRED_FIELDS = ("title", "grade", "subject", "language", "source_pages")
REQUIRED_HEADINGS = ("## Kısa Açıklama", "## Konunun Anlatımı")
MIN_WORDS = 600
TURKISH_CHAR_MIN_RATIO = 0.005  # ≥ 0.5% Turkish-specific letters
QUESTION_DENSITY_MAX = 0.04  # ? per word (catches accidental question generation)


@dataclass
class ValidationResult:
    ok: bool
    reasons: list[str]


def validate(markdown: str) -> ValidationResult:
    reasons: list[str] = []

    # YAML frontmatter
    fm_match = re.match(r"^---\n(.*?)\n---\n", markdown, re.DOTALL)
    if not fm_match:
        reasons.append("missing YAML frontmatter")
    else:
        try:
            fm = yaml.safe_load(fm_match.group(1)) or {}
        except yaml.YAMLError as e:
            fm = {}
            reasons.append(f"YAML parse error: {e}")
        for field in REQUIRED_FIELDS:
            if field not in fm or not str(fm.get(field, "")).strip():
                reasons.append(f"missing/empty frontmatter field: {field}")
        if fm.get("language") and fm["language"] != "tr":
            reasons.append(f"language must be 'tr', got {fm.get('language')!r}")

    # Required headings
    for h in REQUIRED_HEADINGS:
        if h not in markdown:
            reasons.append(f"missing heading: {h}")

    # Body length
    body = markdown.split("---\n", 2)[-1] if markdown.count("---\n") >= 2 else markdown
    word_count = len(body.split())
    if word_count < MIN_WORDS:
        reasons.append(f"body too short: {word_count} words (min {MIN_WORDS})")

    # Turkish character heuristic
    if word_count > 0:
        turkish_chars = sum(1 for c in body if c in TURKISH_CHARS)
        ratio = turkish_chars / max(len(body), 1)
        if ratio < TURKISH_CHAR_MIN_RATIO:
            reasons.append(f"low Turkish-character ratio: {ratio:.4f}")

    # Question-mark density (accidental question generation)
    if word_count > 0:
        qd = body.count("?") / max(word_count, 1)
        if qd > QUESTION_DENSITY_MAX:
            reasons.append(
                f"high question-mark density: {qd:.3f} (looks like generated questions)"
            )

    return ValidationResult(ok=len(reasons) == 0, reasons=reasons)
