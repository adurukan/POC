"""Teacher-studio endpoints: subjects, next, feedback, accept, reject.

All four teacher actions are plain SQL/file moves — no agent invocation here.
The orchestrator only runs from agents/cli.py.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.persistence import (
    accept_pending_to_questions,
    feedback_to_issues_folder,
    get_pending,
    next_pending,
    pending_row_to_response,
    reject_pending_to_issues_folder,
)
from db.database import get_db
from pipeline.models import SectionKnowledgePack

router = APIRouter(prefix="/teacher", tags=["teacher"])

DEFAULT_GRADE = "5"


# ----- subjects (Konu dropdown) -----


class SubjectOption(BaseModel):
    slug: str
    title: str
    subject: str | None
    grade: str | None


@router.get("/subjects", response_model=list[SubjectOption])
def list_subjects(grade: str = DEFAULT_GRADE, db: Session = Depends(get_db)):
    rows = db.execute(
        select(
            SectionKnowledgePack.slug,
            SectionKnowledgePack.title,
            SectionKnowledgePack.subject,
            SectionKnowledgePack.grade,
        )
        .where(SectionKnowledgePack.grade == grade)
        .order_by(SectionKnowledgePack.title.asc())
    ).all()
    seen: set[str] = set()
    out: list[SubjectOption] = []
    for slug, title, subject, g in rows:
        if slug in seen:
            continue
        seen.add(slug)
        out.append(SubjectOption(slug=slug, title=title, subject=subject, grade=g))
    return out


# ----- pending queue shapes -----


class PendingQuestion(BaseModel):
    request_id: str
    grade: str
    subject: str
    topic: str
    question_text: str | None
    solution_steps: list[dict[str, Any]] = []
    visual_path: str | None = None


# ----- /next: pull from queue -----


@router.get("/next")
def next_in_queue(
    grade: str = DEFAULT_GRADE,
    subject: str = "",
    response: Response = None,  # type: ignore[assignment]
):
    if not subject:
        raise HTTPException(status_code=400, detail="subject is required")
    row = next_pending(grade, subject)
    if row is None:
        return Response(status_code=204)
    return pending_row_to_response(row)


# ----- /feedback: move to issues/feedback/, return next -----


class FeedbackRequest(BaseModel):
    request_id: str
    feedback: str


@router.post("/feedback")
def feedback(body: FeedbackRequest):
    if not body.feedback.strip():
        raise HTTPException(status_code=400, detail="Geri bildirim boş olamaz.")
    pending = get_pending(body.request_id)
    if pending is None:
        raise HTTPException(
            status_code=404, detail=f"No pending row for request_id={body.request_id}"
        )

    feedback_to_issues_folder(pending, body.feedback)

    nxt = next_pending(pending["grade"], pending["subject"])
    if nxt is None:
        return Response(status_code=204)
    return pending_row_to_response(nxt)


# ----- /accept: move to questions, return next -----


class AcceptRequest(BaseModel):
    request_id: str


@router.post("/accept")
def accept(body: AcceptRequest):
    pending = get_pending(body.request_id)
    if pending is None:
        raise HTTPException(
            status_code=404, detail=f"No pending row for request_id={body.request_id}"
        )
    try:
        accept_pending_to_questions(pending)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    nxt = next_pending(pending["grade"], pending["subject"])
    if nxt is None:
        return Response(status_code=204)
    return pending_row_to_response(nxt)


# ----- /reject: move to issues/rejected/, return next -----


class RejectRequest(BaseModel):
    request_id: str
    comment: str


@router.post("/reject")
def reject(body: RejectRequest):
    if not body.comment.strip():
        raise HTTPException(status_code=400, detail="Açıklama zorunludur.")
    pending = get_pending(body.request_id)
    if pending is None:
        raise HTTPException(
            status_code=404, detail=f"No pending row for request_id={body.request_id}"
        )
    reject_pending_to_issues_folder(pending, body.comment)

    nxt = next_pending(pending["grade"], pending["subject"])
    if nxt is None:
        return Response(status_code=204)
    return pending_row_to_response(nxt)
