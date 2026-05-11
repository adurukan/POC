"""Operator CLI for the teacher studio queue.

Three subcommands:

* generate-batch  — run the orchestrator N times for a (grade, subject, topic)
                    and INSERT each successful artifact into pending_questions.
* queue-status    — show the pending count per subject + how many feedback
                    items are waiting to be replayed under issues/feedback/.
* replay-feedback — walk issues/feedback/, resume each LangGraph thread with
                    its stored feedback text, INSERT the regenerated artifact
                    back into pending_questions, and move the folder to
                    issues/replayed/.

The CLI opens its own PostgresSaver per invocation so it doesn't compete with
the FastAPI lifespan's saver. Both use the same checkpoint tables.
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from sqlalchemy import text

from agents.main_agent.graph import (
    compile_with_checkpointer,
    open_postgres_checkpointer,
)
from db.database import SessionLocal

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ISSUES_ROOT = _REPO_ROOT / "issues"

app = typer.Typer(add_completion=False, help="Teacher Studio operator CLI.")


def _attempt_counts(state: dict) -> dict[str, int]:
    trails = state.get("trails") or {}
    return {k: len(v) for k, v in trails.items() if isinstance(v, list)}


def _insert_pending(state: dict) -> None:
    """Insert a freshly-generated payload into pending_questions."""
    question = state.get("question") or {}
    solution = state.get("solution") or {}
    stmt = text(
        """
        INSERT INTO pending_questions
            (request_id, grade, subject, topic, question_text,
             solution_steps, visual_path, trails)
        VALUES
            (:request_id, :grade, :subject, :topic, :question_text,
             CAST(:solution_steps AS jsonb), :visual_path, CAST(:trails AS jsonb))
        """
    )
    with SessionLocal() as session:
        session.execute(
            stmt,
            {
                "request_id": state.get("request_id"),
                "grade": state.get("grade"),
                "subject": state.get("subject"),
                "topic": state.get("topic"),
                "question_text": question.get("question_text"),
                "solution_steps": json.dumps(
                    solution.get("steps") or [], ensure_ascii=False
                ),
                "visual_path": state.get("game_visual_path"),
                "trails": json.dumps(state.get("trails") or {}, ensure_ascii=False),
            },
        )
        session.commit()


@app.command("generate-batch")
def generate_batch(
    grade: str = typer.Option(..., "--grade"),
    subject: str = typer.Option(
        ..., "--subject", help="Stored as questions.subject_name."
    ),
    topic: str = typer.Option(..., "--topic", help="Free-text topic fed to the agent."),
    count: int = typer.Option(1, "--count", min=1),
) -> None:
    """Run the orchestrator `count` times and queue the results."""
    load_dotenv(_REPO_ROOT / ".env")
    db_url = os.environ["DATABASE_URL"]

    typer.echo(f"generate-batch: grade={grade} subject={subject!r} count={count}")
    with open_postgres_checkpointer(db_url) as saver:
        graph = compile_with_checkpointer(saver)
        for i in range(count):
            request_id = f"req_{uuid.uuid4().hex[:8]}"
            initial = {
                "request_id": request_id,
                "topic": topic,
                "grade": grade,
                "subject": subject,
                "count": 1,
            }
            config = {"configurable": {"thread_id": request_id}}
            try:
                final = graph.invoke(initial, config=config) or {}
            except Exception as exc:  # noqa: BLE001
                typer.echo(f"  [{i + 1}/{count}] {request_id}: ERROR {exc}", err=True)
                continue

            try:
                _insert_pending(final)
            except Exception as exc:  # noqa: BLE001
                typer.echo(
                    f"  [{i + 1}/{count}] {request_id}: orchestrator OK but DB insert failed: {exc}",
                    err=True,
                )
                continue

            typer.echo(
                f"  [{i + 1}/{count}] {request_id}: queued (attempts={_attempt_counts(final)}, "
                f"visual={'yes' if final.get('game_visual_path') else 'no'})"
            )


@app.command("queue-status")
def queue_status(grade: Optional[str] = typer.Option(None, "--grade")) -> None:
    """Show pending queue depth per subject + feedback backlog."""
    load_dotenv(_REPO_ROOT / ".env")

    where = ""
    params: dict = {}
    if grade:
        where = "WHERE grade = :grade"
        params["grade"] = grade

    with SessionLocal() as session:
        rows = session.execute(
            text(
                f"""
                SELECT subject, grade, COUNT(*) AS n
                FROM pending_questions
                {where}
                GROUP BY subject, grade
                ORDER BY grade, subject
                """
            ),
            params,
        ).all()

    typer.echo("Pending queue:")
    if not rows:
        typer.echo("  (empty)")
    else:
        for subject, g, n in rows:
            typer.echo(f"  grade={g}  subject={subject!r}  pending={n}")

    fb_count = 0
    fb_root = _ISSUES_ROOT / "feedback"
    if fb_root.exists():
        for grade_dir in fb_root.iterdir():
            if not grade_dir.is_dir():
                continue
            for subj_dir in grade_dir.iterdir():
                if not subj_dir.is_dir():
                    continue
                for rid_dir in subj_dir.iterdir():
                    if rid_dir.is_dir():
                        fb_count += 1

    typer.echo(f"\nFeedback items waiting to be replayed: {fb_count}")


@app.command("replay-feedback")
def replay_feedback(
    grade: Optional[str] = typer.Option(None, "--grade"),
    subject: Optional[str] = typer.Option(None, "--subject"),
    limit: int = typer.Option(50, "--limit", min=1),
) -> None:
    """Walk issues/feedback/ and resume each thread with its stored feedback."""
    load_dotenv(_REPO_ROOT / ".env")
    db_url = os.environ["DATABASE_URL"]

    fb_root = _ISSUES_ROOT / "feedback"
    if not fb_root.exists():
        typer.echo("No issues/feedback/ directory; nothing to replay.")
        return

    folders: list[Path] = []
    for grade_dir in sorted(fb_root.iterdir()):
        if not grade_dir.is_dir():
            continue
        if grade is not None and grade_dir.name != grade:
            continue
        for subj_dir in sorted(grade_dir.iterdir()):
            if not subj_dir.is_dir():
                continue
            if subject is not None and subj_dir.name != subject:
                continue
            for rid_dir in sorted(subj_dir.iterdir()):
                if rid_dir.is_dir():
                    folders.append(rid_dir)
                if len(folders) >= limit:
                    break

    if not folders:
        typer.echo("No feedback folders matched the filters.")
        return

    typer.echo(f"replay-feedback: {len(folders)} folder(s) to process")
    replayed_root = _ISSUES_ROOT / "replayed"

    with open_postgres_checkpointer(db_url) as saver:
        graph = compile_with_checkpointer(saver)
        for folder in folders:
            rid = folder.name
            subject_name = folder.parent.name
            grade_name = folder.parent.parent.name
            feedback_path = folder / "feedback.txt"
            if not feedback_path.exists():
                typer.echo(f"  {rid}: missing feedback.txt, skipping", err=True)
                continue
            feedback = feedback_path.read_text(encoding="utf-8")
            config = {"configurable": {"thread_id": rid}}
            try:
                final = graph.invoke({"feedback_text": feedback}, config=config) or {}
            except Exception as exc:  # noqa: BLE001
                typer.echo(f"  {rid}: ERROR during invoke: {exc}", err=True)
                continue

            try:
                _insert_pending(final)
            except Exception as exc:  # noqa: BLE001
                typer.echo(
                    f"  {rid}: agent ran but pending insert failed: {exc}", err=True
                )
                continue

            dest_dir = replayed_root / grade_name / subject_name / rid
            dest_dir.parent.mkdir(parents=True, exist_ok=True)
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.move(str(folder), str(dest_dir))
            meta_path = dest_dir / "meta.json"
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    meta = {}
                meta["replayed_at"] = datetime.now(timezone.utc).isoformat()
                meta_path.write_text(
                    json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
                )

            typer.echo(
                f"  {rid}: replayed (attempts={_attempt_counts(final)}, "
                f"visual={'yes' if final.get('game_visual_path') else 'no'})"
            )


if __name__ == "__main__":
    app()
