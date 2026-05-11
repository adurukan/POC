"""Idempotent upserts of documents, sections, and knowledge packs into Postgres.

Keys:
  - Document:        file_sha256 (unique)
  - DocumentSection: (document_id, slug)
  - SectionKnowledgePack: section_id (1:1 with section)
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from db.database import SessionLocal
from pipeline.embeddings.encoder import Encoder, build_searchable_text
from pipeline.models import (
    Document,
    DocumentSection,
    IngestionRun,
    SectionKnowledgePack,
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def upsert_document(
    session: Session,
    *,
    title: str,
    source_path: Path,
    subject: str | None,
    grade: str | None,
    language: str | None,
) -> Document:
    sha = sha256_file(source_path)
    doc = session.query(Document).filter_by(file_sha256=sha).one_or_none()
    if doc is None:
        doc = Document(
            title=title,
            source_filename=source_path.name,
            source_path=str(source_path),
            file_sha256=sha,
            subject=subject,
            grade=grade,
            language=language,
        )
        session.add(doc)
        session.flush()
    else:
        doc.title = title
        doc.source_path = str(source_path)
        doc.subject = subject
        doc.grade = grade
        doc.language = language
    return doc


def upsert_section(
    session: Session,
    *,
    document: Document,
    section_index: int,
    title: str,
    slug: str,
    page_start: int,
    page_end: int,
    raw_extracted_text: str | None,
) -> DocumentSection:
    sec = (
        session.query(DocumentSection)
        .filter_by(document_id=document.id, slug=slug)
        .one_or_none()
    )
    if sec is None:
        sec = DocumentSection(
            document_id=document.id,
            section_index=section_index,
            title=title,
            slug=slug,
            page_start=page_start,
            page_end=page_end,
            raw_extracted_text=raw_extracted_text,
        )
        session.add(sec)
        session.flush()
    else:
        sec.section_index = section_index
        sec.title = title
        sec.page_start = page_start
        sec.page_end = page_end
        sec.raw_extracted_text = raw_extracted_text
    return sec


def upsert_knowledge_pack(
    session: Session,
    *,
    document: Document,
    section: DocumentSection,
    title: str,
    slug: str,
    subject: str | None,
    grade: str | None,
    language: str | None,
    source_pages: str,
    markdown_content: str,
    markdown_file_path: Path,
    embedding: list[float],
    embedding_model: str,
    review_status: str,
) -> SectionKnowledgePack:
    pack = (
        session.query(SectionKnowledgePack)
        .filter_by(section_id=section.id)
        .one_or_none()
    )
    if pack is None:
        pack = SectionKnowledgePack(
            document_id=document.id,
            section_id=section.id,
            title=title,
            slug=slug,
            subject=subject,
            grade=grade,
            language=language,
            source_pages=source_pages,
            markdown_content=markdown_content,
            markdown_file_path=str(markdown_file_path),
            embedding=embedding,
            embedding_model=embedding_model,
            review_status=review_status,
        )
        session.add(pack)
    else:
        pack.title = title
        pack.slug = slug
        pack.subject = subject
        pack.grade = grade
        pack.language = language
        pack.source_pages = source_pages
        pack.markdown_content = markdown_content
        pack.markdown_file_path = str(markdown_file_path)
        pack.embedding = embedding
        pack.embedding_model = embedding_model
        pack.review_status = review_status
    return pack


def load_processed_dir(processed_dir: Path) -> dict:
    """Load section_index.json + Markdown files into Postgres. Returns a small report."""
    index_path = processed_dir / "index" / "section_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    meta = index.get("metadata", {}) if isinstance(index, dict) else {}

    pdf_path = _resolve_original_pdf(processed_dir, meta)
    encoder = Encoder()

    document_title = index.get("document_title", processed_dir.name)
    sections = index.get("sections", [])
    if not sections:
        raise ValueError(f"No sections found in {index_path}")

    session: Session = SessionLocal()
    extractor_name = _extractor_name_from_meta(meta)
    run = IngestionRun(
        status="running",
        extractor_name=extractor_name,
        extractor_version=_extractor_version_from_meta(meta),
        understanding_model=meta.get("understanding_model"),
        embedding_model=encoder.name,
    )
    session.add(run)
    session.flush()

    inserted = 0
    doc_id: int | None = None
    run_id = run.id
    try:
        # Subject/grade/language come from first available knowledge pack frontmatter.
        first_entry = next(
            (
                e
                for e in sections
                if e.get("generation_status") != "error"
                and (processed_dir / e["output_path"]).exists()
            ),
            None,
        )
        if first_entry is None:
            raise ValueError("No loadable section markdown files were found.")
        first_md_path = processed_dir / first_entry["output_path"]
        first_fm = _parse_frontmatter(first_md_path.read_text(encoding="utf-8"))
        doc = upsert_document(
            session,
            title=document_title,
            source_path=pdf_path,
            subject=first_fm.get("subject"),
            grade=str(first_fm.get("grade"))
            if first_fm.get("grade") is not None
            else None,
            language=first_fm.get("language"),
        )
        run.document_id = doc.id
        doc_id = doc.id

        for entry in sections:
            if entry.get("generation_status") == "error":
                continue
            md_path = processed_dir / entry["output_path"]
            if not md_path.exists():
                continue
            md = md_path.read_text(encoding="utf-8")
            fm = _parse_frontmatter(md)
            raw_text = _read_raw_section(processed_dir, entry)

            sec = upsert_section(
                session,
                document=doc,
                section_index=entry["section_index"],
                title=entry["title"],
                slug=entry["slug"],
                page_start=entry["page_start"],
                page_end=entry["page_end"],
                raw_extracted_text=raw_text,
            )

            searchable = build_searchable_text(
                title=fm.get("title", entry["title"]),
                subject=fm.get("subject", ""),
                grade=str(fm.get("grade", "")),
                source_pages=fm.get(
                    "source_pages", f"{entry['page_start']}-{entry['page_end']}"
                ),
                markdown_content=md,
            )
            [emb] = encoder.encode([searchable])

            review = entry.get("review_status")
            if not review:
                review = (
                    "validated"
                    if entry.get("validation_status") == "validated"
                    else "needs_review"
                )

            upsert_knowledge_pack(
                session,
                document=doc,
                section=sec,
                title=fm.get("title", entry["title"]),
                slug=entry["slug"],
                subject=fm.get("subject"),
                grade=str(fm.get("grade")) if fm.get("grade") is not None else None,
                language=fm.get("language"),
                source_pages=fm.get(
                    "source_pages", f"{entry['page_start']}-{entry['page_end']}"
                ),
                markdown_content=md,
                markdown_file_path=md_path,
                embedding=emb,
                embedding_model=encoder.name,
                review_status=review,
            )
            inserted += 1

        run.status = "ok"
        run.finished_at = datetime.now(timezone.utc)
        run.report_json = {
            "inserted": inserted,
            "extractor_name": extractor_name,
            "report_path": meta.get("report_path"),
        }
        session.commit()
    except Exception as e:
        session.rollback()
        run.status = "error"
        run.error_message = f"{type(e).__name__}: {e}"
        run.finished_at = datetime.now(timezone.utc)
        run.report_json = {"extractor_name": extractor_name}
        session.add(run)
        session.commit()
        raise
    finally:
        session.close()

    return {"inserted": inserted, "document_id": doc_id, "ingestion_run_id": run_id}


def _parse_frontmatter(markdown: str) -> dict:
    import re
    import yaml

    m = re.match(r"^---\n(.*?)\n---\n", markdown, re.DOTALL)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}


def _extractor_version_from_meta(meta: dict) -> str | None:
    extractor = meta.get("extractor")
    if isinstance(extractor, dict):
        version = extractor.get("version")
        if version is not None:
            return str(version)
    return None


def _extractor_name_from_meta(meta: dict) -> str | None:
    if isinstance(meta.get("extractor"), dict):
        name = meta["extractor"].get("name")
        if name is not None:
            return str(name)
    if meta.get("extractor_name") is not None:
        return str(meta["extractor_name"])
    return None


def _resolve_original_pdf(processed_dir: Path, meta: dict) -> Path:
    meta_source = meta.get("source_pdf")
    if meta_source:
        p = Path(meta_source)
        if p.exists():
            return p

    original_dir = processed_dir / "original"
    candidates = sorted(original_dir.glob("*.pdf"))
    if not candidates:
        raise FileNotFoundError(f"No PDF found under {original_dir}")
    return candidates[0]


def _read_raw_section(processed_dir: Path, entry: dict) -> str | None:
    rel = entry.get("raw_section_path")
    if not rel:
        return None
    path = processed_dir / rel
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")
