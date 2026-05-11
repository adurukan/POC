"""Render the game artifact (p5.js sketch) to a self-contained HTML file.

This is the single source of truth for the rendered HTML. Both the orchestrator
(via the game subgraph's succeed_node) and the manual try_game CLI use this
module so the file format never drifts between contexts.

Filename scheme (see Teacher Studio plan §5):
    {grade}_{subject_slug}_{n}_{request_id}.html

`n` is the next id within (subject) — `MAX(id)+1` over the `questions` table
filtered by subject_name. The request_id suffix disambiguates parallel/rejected
attempts so `n` doesn't need to be globally unique; it's just a human label.
"""

from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy import func, select

from db.database import SessionLocal

P5_CDN = "https://cdn.jsdelivr.net/npm/p5@1.11.0/lib/p5.min.js"

_TURKISH_TRANSLIT = str.maketrans(
    {
        "ç": "c",
        "Ç": "c",
        "ğ": "g",
        "Ğ": "g",
        "ı": "i",
        "İ": "i",
        "ö": "o",
        "Ö": "o",
        "ş": "s",
        "Ş": "s",
        "ü": "u",
        "Ü": "u",
    }
)

_HTML_TEMPLATE = """<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <title>game</title>
  <style>
    html, body {{ margin: 0; padding: 0; background: #fff; }}
    body {{ display: flex; align-items: center; justify-content: center; min-height: 100vh; }}
  </style>
  <script src="{p5_cdn}"></script>
</head>
<body>
<script>
{sketch}
</script>
</body>
</html>
"""


def render_game_html(artifact: dict) -> str:
    """Return a complete HTML doc embedding the artifact's p5.js sketch."""
    sketch = artifact.get("p5_sketch") or ""
    return _HTML_TEMPLATE.format(p5_cdn=P5_CDN, sketch=sketch)


def slugify_subject(subject: str) -> str:
    """Filesystem-friendly subject slug. Lowercase ASCII, dashes for spaces."""
    translit = subject.translate(_TURKISH_TRANSLIT)
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", translit).strip("-").lower()
    return slug or "subject"


def next_question_number(subject: str) -> int:
    """Compute next 'question number' label within a subject bucket.

    Uses MAX(id) + 1 from the questions table filtered by subject_name. This is
    only a label — not a unique key. Uniqueness comes from the request_id suffix.
    """
    from api.models.question import Question

    with SessionLocal() as session:
        max_id = session.execute(
            select(func.max(Question.id)).where(Question.subject_name == subject)
        ).scalar_one_or_none()
    return int(max_id or 0) + 1


_REPO_ROOT = Path(__file__).resolve().parents[3]
_VISUALS_ROOT = _REPO_ROOT / "api" / "visuals"
_TEACHER_DIR = _VISUALS_ROOT / "teacher"


def write_game_html(
    artifact: dict,
    *,
    grade: str,
    subject: str,
    request_id: str,
) -> str:
    """Render the artifact to HTML and write under api/visuals/teacher/.

    Returns the path relative to api/visuals/ (e.g.
    "teacher/5_kesirler_42_req_ab12.html"), suitable for direct insertion into
    questions.visual_path.
    """
    _TEACHER_DIR.mkdir(parents=True, exist_ok=True)

    subject_slug = slugify_subject(subject)
    n = next_question_number(subject)
    filename = f"{grade}_{subject_slug}_{n}_{request_id}.html"
    out = _TEACHER_DIR / filename
    out.write_text(render_game_html(artifact), encoding="utf-8")
    return f"teacher/{filename}"


def absolute_path(relative_visual_path: str) -> Path:
    """Resolve a stored visual_path back to its absolute filesystem path."""
    return _VISUALS_ROOT / relative_visual_path
