from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import typer
from sqlalchemy import text
from sqlalchemy.orm import Session

from db.database import SessionLocal

app = typer.Typer(no_args_is_help=True, add_completion=False)

DATA_DIR = Path(__file__).resolve().parent / "seeds" / "data"
MANIFEST_PATH = DATA_DIR / "manifest.json"
REPO_ROOT = Path(__file__).resolve().parent.parent

CANONICAL_TABLES = (
    "questions",
    "documents",
    "document_sections",
    "section_knowledge_packs",
    "pending_questions",
    "problems",
)


def _read_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Seed manifest missing: {MANIFEST_PATH}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("Seed manifest must be a JSON object.")
    if manifest.get("version") != 1:
        raise ValueError("Unsupported seed manifest version.")
    tables = manifest.get("tables")
    if not isinstance(tables, dict):
        raise ValueError("Seed manifest missing 'tables' object.")
    for t in CANONICAL_TABLES:
        if t not in tables:
            raise ValueError(f"Seed manifest missing table entry: {t}")
    return manifest


def _read_rows(table: str, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    spec = manifest["tables"][table]
    if not isinstance(spec, dict):
        raise ValueError(f"Invalid manifest table spec for {table}")

    rel_file = spec.get("file")
    required = spec.get("required", [])
    if not isinstance(rel_file, str) or not rel_file:
        raise ValueError(f"Manifest table {table} has invalid 'file'.")
    if not isinstance(required, list) or not all(isinstance(x, str) for x in required):
        raise ValueError(f"Manifest table {table} has invalid 'required' list.")

    path = DATA_DIR / rel_file
    if not path.exists():
        raise FileNotFoundError(f"Fixture file missing for {table}: {path}")

    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError(f"Fixture file must contain a JSON array: {path}")

    validated: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"{table}[{i}] must be an object.")
        missing = [k for k in required if k not in row]
        if missing:
            raise ValueError(f"{table}[{i}] missing required keys: {missing}")
        validated.append(row)
    return validated


def _json_param(value: Any) -> str:
    return json.dumps(value if value is not None else None, ensure_ascii=False)


def _delete_by_ids(session: Session, table: str, id_col: str, ids: Iterable[Any]) -> int:
    ids_list = list(ids)
    if not ids_list:
        return 0
    session.execute(
        text(f"DELETE FROM {table} WHERE {id_col} = ANY(:ids)"),
        {"ids": ids_list},
    )
    return len(ids_list)


def _set_serial_sequence(session: Session, table: str, id_col: str) -> None:
    session.execute(
        text(
            "SELECT setval(pg_get_serial_sequence(:table_name, :id_col), "
            "COALESCE((SELECT MAX(" + id_col + ") FROM " + table + "), 1), "
            "(SELECT MAX(" + id_col + ") IS NOT NULL FROM " + table + "))"
        ),
        {"table_name": table, "id_col": id_col},
    )


def _seed_questions(session: Session, rows: list[dict[str, Any]]) -> dict[str, int]:
    existing_ids = set(
        session.execute(text("SELECT id FROM questions")).scalars().all()
    )

    inserted = 0
    updated = 0
    expected_ids: set[int] = set()

    for row in sorted(rows, key=lambda r: int(r["id"])):
        qid = int(row["id"])
        expected_ids.add(qid)
        if qid in existing_ids:
            updated += 1
        else:
            inserted += 1

        session.execute(
            text(
                """
                INSERT INTO questions (id, subject_name, question_text, solution_steps, visual_path)
                VALUES (:id, :subject_name, :question_text, CAST(:solution_steps AS jsonb), :visual_path)
                ON CONFLICT (id) DO UPDATE SET
                  subject_name = EXCLUDED.subject_name,
                  question_text = EXCLUDED.question_text,
                  solution_steps = EXCLUDED.solution_steps,
                  visual_path = EXCLUDED.visual_path
                """
            ),
            {
                "id": qid,
                "subject_name": row["subject_name"],
                "question_text": row["question_text"],
                "solution_steps": _json_param(row["solution_steps"]),
                "visual_path": row.get("visual_path"),
            },
        )

    deleted = _delete_by_ids(session, "questions", "id", sorted(existing_ids - expected_ids))
    _set_serial_sequence(session, "questions", "id")
    return {"inserted": inserted, "updated": updated, "deleted": deleted}


def _seed_documents(session: Session, rows: list[dict[str, Any]]) -> dict[str, int]:
    existing = {
        r[0]: r[1]
        for r in session.execute(text("SELECT file_sha256, id FROM documents")).all()
    }

    inserted = 0
    updated = 0
    expected_sha: set[str] = set()

    for row in sorted(rows, key=lambda r: str(r["file_sha256"])):
        sha = str(row["file_sha256"])
        expected_sha.add(sha)
        if sha in existing:
            updated += 1
        else:
            inserted += 1

        session.execute(
            text(
                """
                INSERT INTO documents (
                  title, source_filename, source_path, file_sha256,
                  subject, grade, language, metadata_json
                )
                VALUES (
                  :title, :source_filename, :source_path, :file_sha256,
                  :subject, :grade, :language, CAST(:metadata_json AS jsonb)
                )
                ON CONFLICT (file_sha256) DO UPDATE SET
                  title = EXCLUDED.title,
                  source_filename = EXCLUDED.source_filename,
                  source_path = EXCLUDED.source_path,
                  subject = EXCLUDED.subject,
                  grade = EXCLUDED.grade,
                  language = EXCLUDED.language,
                  metadata_json = EXCLUDED.metadata_json,
                  updated_at = now()
                """
            ),
            {
                "title": row["title"],
                "source_filename": row["source_filename"],
                "source_path": row["source_path"],
                "file_sha256": sha,
                "subject": row.get("subject"),
                "grade": row.get("grade"),
                "language": row.get("language"),
                "metadata_json": _json_param(row.get("metadata_json")),
            },
        )

    extra_sha = sorted(set(existing.keys()) - expected_sha)
    deleted = 0
    if extra_sha:
        session.execute(
            text("DELETE FROM documents WHERE file_sha256 = ANY(:sha)"),
            {"sha": extra_sha},
        )
        deleted = len(extra_sha)

    return {"inserted": inserted, "updated": updated, "deleted": deleted}


def _document_id_map(session: Session) -> dict[str, int]:
    return {
        str(r[0]): int(r[1])
        for r in session.execute(text("SELECT file_sha256, id FROM documents")).all()
    }


def _section_id_map(session: Session) -> dict[tuple[str, str], int]:
    rows = session.execute(
        text(
            """
            SELECT d.file_sha256, s.slug, s.id
            FROM document_sections s
            JOIN documents d ON d.id = s.document_id
            """
        )
    ).all()
    return {(str(r[0]), str(r[1])): int(r[2]) for r in rows}


def _seed_document_sections(session: Session, rows: list[dict[str, Any]]) -> dict[str, int]:
    doc_ids = _document_id_map(session)
    existing = _section_id_map(session)

    inserted = 0
    updated = 0
    expected_keys: set[tuple[str, str]] = set()

    ordered = sorted(rows, key=lambda r: (str(r["document_file_sha256"]), str(r["slug"])))
    for row in ordered:
        doc_sha = str(row["document_file_sha256"])
        slug = str(row["slug"])
        if doc_sha not in doc_ids:
            raise ValueError(
                f"document_sections row references unknown document_file_sha256={doc_sha}"
            )

        key = (doc_sha, slug)
        expected_keys.add(key)
        if key in existing:
            updated += 1
        else:
            inserted += 1

        session.execute(
            text(
                """
                INSERT INTO document_sections (
                  document_id, section_index, title, slug,
                  page_start, page_end, raw_extracted_text, metadata_json
                )
                VALUES (
                  :document_id, :section_index, :title, :slug,
                  :page_start, :page_end, :raw_extracted_text, CAST(:metadata_json AS jsonb)
                )
                ON CONFLICT (document_id, slug) DO UPDATE SET
                  section_index = EXCLUDED.section_index,
                  title = EXCLUDED.title,
                  page_start = EXCLUDED.page_start,
                  page_end = EXCLUDED.page_end,
                  raw_extracted_text = EXCLUDED.raw_extracted_text,
                  metadata_json = EXCLUDED.metadata_json,
                  updated_at = now()
                """
            ),
            {
                "document_id": doc_ids[doc_sha],
                "section_index": int(row["section_index"]),
                "title": row["title"],
                "slug": slug,
                "page_start": int(row["page_start"]),
                "page_end": int(row["page_end"]),
                "raw_extracted_text": row.get("raw_extracted_text"),
                "metadata_json": _json_param(row.get("metadata_json")),
            },
        )

    extras = [sid for k, sid in existing.items() if k not in expected_keys]
    deleted = _delete_by_ids(session, "document_sections", "id", extras)
    return {"inserted": inserted, "updated": updated, "deleted": deleted}


def _seed_section_knowledge_packs(
    session: Session, rows: list[dict[str, Any]]
) -> dict[str, int]:
    doc_ids = _document_id_map(session)
    section_ids = _section_id_map(session)
    existing = {
        int(r[0]): int(r[1])
        for r in session.execute(
            text("SELECT section_id, id FROM section_knowledge_packs")
        ).all()
    }

    inserted = 0
    updated = 0
    expected_section_ids: set[int] = set()

    ordered = sorted(rows, key=lambda r: (str(r["document_file_sha256"]), str(r["section_slug"])))
    for row in ordered:
        doc_sha = str(row["document_file_sha256"])
        section_slug = str(row["section_slug"])
        key = (doc_sha, section_slug)
        if key not in section_ids:
            raise ValueError(
                f"section_knowledge_packs row references unknown section key={key}"
            )

        section_id = section_ids[key]
        expected_section_ids.add(section_id)
        if section_id in existing:
            updated += 1
        else:
            inserted += 1

        session.execute(
            text(
                """
                INSERT INTO section_knowledge_packs (
                  document_id, section_id, title, slug, subject, grade, language,
                  source_pages, markdown_content, markdown_file_path,
                  embedding, embedding_model, review_status, metadata_json
                )
                VALUES (
                  :document_id, :section_id, :title, :slug, :subject, :grade, :language,
                  :source_pages, :markdown_content, :markdown_file_path,
                  :embedding, :embedding_model, :review_status, CAST(:metadata_json AS jsonb)
                )
                ON CONFLICT (section_id) DO UPDATE SET
                  document_id = EXCLUDED.document_id,
                  title = EXCLUDED.title,
                  slug = EXCLUDED.slug,
                  subject = EXCLUDED.subject,
                  grade = EXCLUDED.grade,
                  language = EXCLUDED.language,
                  source_pages = EXCLUDED.source_pages,
                  markdown_content = EXCLUDED.markdown_content,
                  markdown_file_path = EXCLUDED.markdown_file_path,
                  embedding = EXCLUDED.embedding,
                  embedding_model = EXCLUDED.embedding_model,
                  review_status = EXCLUDED.review_status,
                  metadata_json = EXCLUDED.metadata_json,
                  updated_at = now()
                """
            ),
            {
                "document_id": doc_ids[doc_sha],
                "section_id": section_id,
                "title": row["title"],
                "slug": row["slug"],
                "subject": row.get("subject"),
                "grade": row.get("grade"),
                "language": row.get("language"),
                "source_pages": row["source_pages"],
                "markdown_content": row["markdown_content"],
                "markdown_file_path": row["markdown_file_path"],
                "embedding": row.get("embedding"),
                "embedding_model": row.get("embedding_model"),
                "review_status": row["review_status"],
                "metadata_json": _json_param(row.get("metadata_json")),
            },
        )

    extras = [pid for sid, pid in existing.items() if sid not in expected_section_ids]
    deleted = _delete_by_ids(session, "section_knowledge_packs", "id", extras)
    return {"inserted": inserted, "updated": updated, "deleted": deleted}


def _seed_pending_questions(session: Session, rows: list[dict[str, Any]]) -> dict[str, int]:
    existing_ids = set(
        str(x)
        for x in session.execute(text("SELECT request_id FROM pending_questions")).scalars().all()
    )
    expected_ids: set[str] = set()
    inserted = 0
    updated = 0

    for row in sorted(rows, key=lambda r: str(r["request_id"])):
        rid = str(row["request_id"])
        expected_ids.add(rid)
        if rid in existing_ids:
            updated += 1
        else:
            inserted += 1

        session.execute(
            text(
                """
                INSERT INTO pending_questions (
                  request_id, grade, subject, topic, question_text,
                  solution_steps, visual_path, status, trails, feedback_history
                )
                VALUES (
                  :request_id, :grade, :subject, :topic, :question_text,
                  CAST(:solution_steps AS jsonb), :visual_path, :status,
                  CAST(:trails AS jsonb), CAST(:feedback_history AS jsonb)
                )
                ON CONFLICT (request_id) DO UPDATE SET
                  grade = EXCLUDED.grade,
                  subject = EXCLUDED.subject,
                  topic = EXCLUDED.topic,
                  question_text = EXCLUDED.question_text,
                  solution_steps = EXCLUDED.solution_steps,
                  visual_path = EXCLUDED.visual_path,
                  status = EXCLUDED.status,
                  trails = EXCLUDED.trails,
                  feedback_history = EXCLUDED.feedback_history,
                  updated_at = now()
                """
            ),
            {
                "request_id": rid,
                "grade": row["grade"],
                "subject": row["subject"],
                "topic": row["topic"],
                "question_text": row.get("question_text"),
                "solution_steps": _json_param(row.get("solution_steps", [])),
                "visual_path": row.get("visual_path"),
                "status": row.get("status", "pending"),
                "trails": _json_param(row.get("trails", {})),
                "feedback_history": _json_param(row.get("feedback_history", [])),
            },
        )

    extras = sorted(existing_ids - expected_ids)
    deleted = 0
    if extras:
        session.execute(
            text("DELETE FROM pending_questions WHERE request_id = ANY(:ids)"),
            {"ids": extras},
        )
        deleted = len(extras)

    return {"inserted": inserted, "updated": updated, "deleted": deleted}


def _seed_problems(session: Session, rows: list[dict[str, Any]]) -> dict[str, int]:
    existing_ids = set(
        str(x) for x in session.execute(text("SELECT request_id FROM problems")).scalars().all()
    )
    expected_ids: set[str] = set()
    inserted = 0
    updated = 0

    for row in sorted(rows, key=lambda r: str(r["request_id"])):
        rid = str(row["request_id"])
        expected_ids.add(rid)
        if rid in existing_ids:
            updated += 1
        else:
            inserted += 1

        session.execute(
            text(
                """
                INSERT INTO problems (request_id, topic, count, payload_json)
                VALUES (:request_id, :topic, :count, CAST(:payload_json AS jsonb))
                ON CONFLICT (request_id) DO UPDATE SET
                  topic = EXCLUDED.topic,
                  count = EXCLUDED.count,
                  payload_json = EXCLUDED.payload_json,
                  updated_at = now()
                """
            ),
            {
                "request_id": rid,
                "topic": row["topic"],
                "count": int(row["count"]),
                "payload_json": _json_param(row["payload_json"]),
            },
        )

    extras = sorted(existing_ids - expected_ids)
    deleted = 0
    if extras:
        session.execute(text("DELETE FROM problems WHERE request_id = ANY(:ids)"), {"ids": extras})
        deleted = len(extras)

    return {"inserted": inserted, "updated": updated, "deleted": deleted}


def _seed_pipeline_group(
    session: Session,
    docs_rows: list[dict[str, Any]],
    sec_rows: list[dict[str, Any]],
    pack_rows: list[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    docs_stats = _seed_documents(session, docs_rows)
    sec_stats = _seed_document_sections(session, sec_rows)
    pack_stats = _seed_section_knowledge_packs(session, pack_rows)
    return {
        "documents": docs_stats,
        "document_sections": sec_stats,
        "section_knowledge_packs": pack_stats,
    }


def seed_exact_sync() -> dict[str, Any]:
    manifest = _read_manifest()
    rows = {t: _read_rows(t, manifest) for t in CANONICAL_TABLES}

    report: dict[str, Any] = {}

    with SessionLocal.begin() as session:
        report["questions"] = _seed_questions(session, rows["questions"])

    with SessionLocal.begin() as session:
        report.update(
            _seed_pipeline_group(
                session,
                rows["documents"],
                rows["document_sections"],
                rows["section_knowledge_packs"],
            )
        )

    with SessionLocal.begin() as session:
        report["pending_questions"] = _seed_pending_questions(
            session, rows["pending_questions"]
        )

    with SessionLocal.begin() as session:
        report["problems"] = _seed_problems(session, rows["problems"])

    return report


def _ensure_data_dir(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _normalize_embedding(val: Any) -> list[float] | None:
    if val is None:
        return None
    if isinstance(val, list):
        return [float(x) for x in val]
    if isinstance(val, tuple):
        return [float(x) for x in val]
    return None


def _normalize_repo_path(value: str | None) -> str | None:
    if not value:
        return value
    p = Path(value)
    try:
        rel = p.resolve().relative_to(REPO_ROOT.resolve())
        return str(rel)
    except Exception:
        return value


def export_seed_data(out_dir: Path = DATA_DIR) -> dict[str, int]:
    _ensure_data_dir(out_dir)

    manifest = {
        "version": 1,
        "tables": {
            "questions": {
                "file": "questions.json",
                "required": ["id", "subject_name", "question_text", "solution_steps"],
            },
            "documents": {
                "file": "documents.json",
                "required": ["file_sha256", "title", "source_filename", "source_path"],
            },
            "document_sections": {
                "file": "document_sections.json",
                "required": [
                    "document_file_sha256",
                    "slug",
                    "section_index",
                    "title",
                    "page_start",
                    "page_end",
                ],
            },
            "section_knowledge_packs": {
                "file": "section_knowledge_packs.json",
                "required": [
                    "document_file_sha256",
                    "section_slug",
                    "slug",
                    "title",
                    "source_pages",
                    "markdown_content",
                    "markdown_file_path",
                    "review_status",
                ],
            },
            "pending_questions": {
                "file": "pending_questions.json",
                "required": ["request_id", "grade", "subject", "topic"],
            },
            "problems": {
                "file": "problems.json",
                "required": ["request_id", "topic", "count", "payload_json"],
            },
        },
    }

    with SessionLocal() as session:
        questions = [
            {
                "id": int(r.id),
                "subject_name": r.subject_name,
                "question_text": r.question_text,
                "solution_steps": r.solution_steps,
                "visual_path": r.visual_path,
            }
            for r in session.execute(
                text(
                    "SELECT id, subject_name, question_text, solution_steps, visual_path "
                    "FROM questions ORDER BY id"
                )
            )
        ]

        documents = [
            {
                "file_sha256": r.file_sha256,
                "title": r.title,
                "source_filename": r.source_filename,
                "source_path": _normalize_repo_path(r.source_path),
                "subject": r.subject,
                "grade": r.grade,
                "language": r.language,
                "metadata_json": r.metadata_json,
            }
            for r in session.execute(
                text(
                    """
                    SELECT file_sha256, title, source_filename, source_path,
                           subject, grade, language, metadata_json
                    FROM documents
                    ORDER BY file_sha256
                    """
                )
            )
        ]

        document_sections = [
            {
                "document_file_sha256": r.file_sha256,
                "section_index": int(r.section_index),
                "title": r.title,
                "slug": r.slug,
                "page_start": int(r.page_start),
                "page_end": int(r.page_end),
                "raw_extracted_text": r.raw_extracted_text,
                "metadata_json": r.metadata_json,
            }
            for r in session.execute(
                text(
                    """
                    SELECT d.file_sha256, s.section_index, s.title, s.slug,
                           s.page_start, s.page_end, s.raw_extracted_text, s.metadata_json
                    FROM document_sections s
                    JOIN documents d ON d.id = s.document_id
                    ORDER BY d.file_sha256, s.slug
                    """
                )
            )
        ]

        section_knowledge_packs = [
            {
                "document_file_sha256": r.file_sha256,
                "section_slug": r.section_slug,
                "title": r.title,
                "slug": r.slug,
                "subject": r.subject,
                "grade": r.grade,
                "language": r.language,
                "source_pages": r.source_pages,
                "markdown_content": r.markdown_content,
                "markdown_file_path": _normalize_repo_path(r.markdown_file_path),
                "embedding": _normalize_embedding(r.embedding),
                "embedding_model": r.embedding_model,
                "review_status": r.review_status,
                "metadata_json": r.metadata_json,
            }
            for r in session.execute(
                text(
                    """
                    SELECT d.file_sha256,
                           s.slug AS section_slug,
                           p.title, p.slug, p.subject, p.grade, p.language,
                           p.source_pages, p.markdown_content, p.markdown_file_path,
                           p.embedding, p.embedding_model, p.review_status, p.metadata_json
                    FROM section_knowledge_packs p
                    JOIN document_sections s ON s.id = p.section_id
                    JOIN documents d ON d.id = p.document_id
                    ORDER BY d.file_sha256, s.slug
                    """
                )
            )
        ]

        pending_questions = [
            {
                "request_id": r.request_id,
                "grade": r.grade,
                "subject": r.subject,
                "topic": r.topic,
                "question_text": r.question_text,
                "solution_steps": r.solution_steps,
                "visual_path": r.visual_path,
                "status": r.status,
                "trails": r.trails,
                "feedback_history": r.feedback_history,
            }
            for r in session.execute(
                text(
                    """
                    SELECT request_id, grade, subject, topic, question_text,
                           solution_steps, visual_path, status, trails, feedback_history
                    FROM pending_questions
                    ORDER BY request_id
                    """
                )
            )
        ]

        problems = [
            {
                "request_id": r.request_id,
                "topic": r.topic,
                "count": int(r.count),
                "payload_json": r.payload_json,
            }
            for r in session.execute(
                text(
                    "SELECT request_id, topic, count, payload_json FROM problems ORDER BY request_id"
                )
            )
        ]

    _write_json(out_dir / "manifest.json", manifest)
    _write_json(out_dir / "questions.json", questions)
    _write_json(out_dir / "documents.json", documents)
    _write_json(out_dir / "document_sections.json", document_sections)
    _write_json(out_dir / "section_knowledge_packs.json", section_knowledge_packs)
    _write_json(out_dir / "pending_questions.json", pending_questions)
    _write_json(out_dir / "problems.json", problems)

    return {
        "questions": len(questions),
        "documents": len(documents),
        "document_sections": len(document_sections),
        "section_knowledge_packs": len(section_knowledge_packs),
        "pending_questions": len(pending_questions),
        "problems": len(problems),
    }


@app.command("questions")
def seed_questions_only() -> None:
    """Exact-sync only the questions table from canonical fixtures."""
    manifest = _read_manifest()
    rows = _read_rows("questions", manifest)
    with SessionLocal.begin() as session:
        stats = _seed_questions(session, rows)
    typer.echo(f"questions: {stats}")


@app.command("all")
def seed_all() -> None:
    """Exact-sync all canonical seed tables from fixture files."""
    report = seed_exact_sync()
    typer.echo("Seed completed (exact-sync):")
    for table in CANONICAL_TABLES:
        stats = report.get(table, {})
        typer.echo(f"  - {table}: {stats}")


@app.command("export")
def export_cmd(
    out_dir: Path = typer.Option(DATA_DIR, "--out-dir", file_okay=False, dir_okay=True)
) -> None:
    """Export current DB rows into canonical fixture files."""
    report = export_seed_data(out_dir.resolve())
    typer.echo(f"Wrote seed fixtures to: {out_dir.resolve()}")
    for table in CANONICAL_TABLES:
        typer.echo(f"  - {table}: {report.get(table, 0)} rows")


if __name__ == "__main__":
    app()
