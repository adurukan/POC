"""Pending-row persistence helpers for the teacher studio.

All three teacher actions are pure SQL moves over a pending_questions row:

* Accept   → INSERT into questions, DELETE pending row.
* Reject   → write 4 files to issues/rejected/, delete pending row + rendered HTML.
* Feedback → write 4 files to issues/feedback/, delete pending row.
              The replay-feedback CLI later resumes the LangGraph thread.

No orchestrator invocation happens in this module; the agents run only from
agents/cli.py.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text

from api.models.question import Question
from db.database import SessionLocal

_REPO_ROOT = Path(__file__).resolve().parent.parent
_ISSUES_ROOT = _REPO_ROOT / "issues"
_TEACHER_VISUALS_DIR = _REPO_ROOT / "api" / "visuals" / "teacher"


# ---------- Pending row reader ----------


def get_pending(request_id: str) -> dict | None:
    """Read a pending_questions row by request_id. Returns a dict or None."""
    with SessionLocal() as session:
        row = (
            session.execute(
                text(
                    """
                SELECT request_id, grade, subject, topic, question_text,
                       solution_steps, visual_path, status, trails,
                       feedback_history, created_at, updated_at
                FROM pending_questions
                WHERE request_id = :rid
                """
                ),
                {"rid": request_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row is not None else None


# ---------- Accept ----------


def accept_pending_to_questions(pending: dict) -> dict:
    """Move a pending row into the questions table.

    The corresponding `problems` audit row (written by assemble_node during
    generation) is left in place as the historical record.
    """
    subject = pending.get("subject") or ""
    question_text = pending.get("question_text") or ""
    solution_steps = pending.get("solution_steps") or []
    visual_path = pending.get("visual_path")
    request_id = pending.get("request_id") or ""

    if not subject:
        raise ValueError("pending row has no subject")
    if not question_text:
        raise ValueError("pending row has no question_text")

    with SessionLocal() as session:
        row = Question(
            subject_name=subject,
            question_text=question_text,
            solution_steps=solution_steps,
            visual_path=visual_path,
        )
        session.add(row)
        session.flush()
        new_id = row.id
        session.execute(
            text("DELETE FROM pending_questions WHERE request_id = :rid"),
            {"rid": request_id},
        )
        session.commit()

    return {"question_id": new_id, "visual_path": visual_path}


# ---------- Feedback (move to issues/feedback/) ----------


def feedback_to_issues_folder(pending: dict, feedback_text: str) -> dict:
    """Park a pending row's full state under issues/feedback/ for later replay."""
    request_id = pending.get("request_id") or "unknown"
    grade = str(pending.get("grade") or "unknown")
    subject = pending.get("subject") or "unknown"

    issue_dir = _ISSUES_ROOT / "feedback" / grade / subject / request_id
    issue_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "request_id": request_id,
        "topic": pending.get("topic"),
        "grade": grade,
        "subject": subject,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    artifact = {
        "question_text": pending.get("question_text"),
        "solution_steps": pending.get("solution_steps"),
        "visual_path": pending.get("visual_path"),
    }
    trails = pending.get("trails") or {}

    (issue_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (issue_dir / "artifact.json").write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (issue_dir / "trails.json").write_text(
        json.dumps(trails, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (issue_dir / "feedback.txt").write_text(feedback_text, encoding="utf-8")

    with SessionLocal() as session:
        session.execute(
            text("DELETE FROM pending_questions WHERE request_id = :rid"),
            {"rid": request_id},
        )
        session.commit()

    return {"issue_path": str(issue_dir.relative_to(_REPO_ROOT))}


# ---------- Reject (move to issues/rejected/) ----------


def reject_pending_to_issues_folder(pending: dict, comment: str) -> dict:
    """Park a pending row's full state under issues/rejected/ with the teacher comment."""
    request_id = pending.get("request_id") or "unknown"
    grade = str(pending.get("grade") or "unknown")
    subject = pending.get("subject") or "unknown"
    visual_path = pending.get("visual_path")

    issue_dir = _ISSUES_ROOT / "rejected" / grade / subject / request_id
    issue_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "request_id": request_id,
        "topic": pending.get("topic"),
        "grade": grade,
        "subject": subject,
        "rejected_at": datetime.now(timezone.utc).isoformat(),
    }
    artifact = {
        "question_text": pending.get("question_text"),
        "solution_steps": pending.get("solution_steps"),
        "visual_path": visual_path,
    }
    trails = pending.get("trails") or {}

    (issue_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (issue_dir / "artifact.json").write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (issue_dir / "trails.json").write_text(
        json.dumps(trails, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (issue_dir / "teacher_comment.txt").write_text(comment, encoding="utf-8")

    _delete_visual(visual_path)

    with SessionLocal() as session:
        session.execute(
            text("DELETE FROM pending_questions WHERE request_id = :rid"),
            {"rid": request_id},
        )
        session.commit()

    return {"issue_path": str(issue_dir.relative_to(_REPO_ROOT))}


# ---------- Queue read ----------


def next_pending(grade: str, subject: str) -> dict | None:
    """Return the next-in-line pending row for (grade, subject)."""
    with SessionLocal() as session:
        row = (
            session.execute(
                text(
                    """
                SELECT request_id, grade, subject, topic, question_text,
                       solution_steps, visual_path
                FROM pending_questions
                WHERE grade = :grade
                  AND subject = :subject
                  AND status = 'pending'
                ORDER BY created_at ASC
                LIMIT 1
                """
                ),
                {"grade": grade, "subject": subject},
            )
            .mappings()
            .first()
        )
        return dict(row) if row is not None else None


# ---------- helpers ----------


def _delete_visual(visual_path: str | None) -> None:
    if not visual_path:
        return
    p = (
        _TEACHER_VISUALS_DIR.parent / visual_path
    )  # visual_path begins with "teacher/..."
    if p.is_file():
        try:
            p.unlink()
        except OSError:
            pass


def pending_row_to_response(row: dict) -> dict[str, Any]:
    """Trim a pending row to the shape the frontend consumes."""
    return {
        "request_id": row.get("request_id"),
        "grade": row.get("grade"),
        "subject": row.get("subject"),
        "topic": row.get("topic"),
        "question_text": row.get("question_text"),
        "solution_steps": row.get("solution_steps") or [],
        "visual_path": row.get("visual_path"),
    }
