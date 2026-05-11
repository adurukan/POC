from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, asc

from db.database import get_db
from api.models.question import Question
from api.schemas.question import QuestionResponse

router = APIRouter()


@router.get("/subjects", response_model=list[str])
def get_subjects(db: Session = Depends(get_db)):
    rows = db.execute(select(Question.subject_name).distinct()).scalars().all()
    return rows


@router.get("", response_model=list[QuestionResponse])
def get_questions(subject: str, db: Session = Depends(get_db)):
    rows = (
        db.execute(
            select(Question)
            .where(Question.subject_name == subject)
            .order_by(asc(Question.id))
        )
        .scalars()
        .all()
    )
    return rows


@router.get("/{id}/visual")
def get_visual(id: int, db: Session = Depends(get_db)):
    question = db.get(Question, id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    if not question.visual_path:
        raise HTTPException(status_code=404, detail="No visual for this question")
    return FileResponse(question.visual_path)
