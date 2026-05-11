"""Thin wrapper around pipeline.storage.search.search.

The pipeline's SearchHit dataclass does not include markdown_content; it only
returns metadata + similarity. This module joins the hit to the underlying
SectionKnowledgePack row to return a RetrievedPack with the full markdown the
generator needs to ground in.
"""

from dataclasses import asdict, dataclass

from db.database import SessionLocal
from pipeline.models import SectionKnowledgePack
from pipeline.storage.search import search

DEFAULT_GRADE = "5"
DEFAULT_SUBJECT = "Matematik"


@dataclass
class RetrievedPack:
    pack_id: int
    title: str
    slug: str
    grade: str | None
    subject: str | None
    source_pages: str
    markdown_content: str
    markdown_file_path: str
    similarity: float


def retrieve(
    query: str,
    *,
    grade: str = DEFAULT_GRADE,
    subject: str = DEFAULT_SUBJECT,
    top_k: int = 1,
) -> RetrievedPack | None:
    hits = search(query, grade=grade, subject=subject, top_k=top_k)
    if not hits:
        return None
    top = hits[0]
    with SessionLocal() as session:
        pack = session.get(SectionKnowledgePack, top.id)
        if pack is None:
            return None
        return RetrievedPack(
            pack_id=pack.id,
            title=pack.title,
            slug=pack.slug,
            grade=pack.grade,
            subject=pack.subject,
            source_pages=pack.source_pages,
            markdown_content=pack.markdown_content,
            markdown_file_path=pack.markdown_file_path,
            similarity=top.similarity,
        )


def retrieved_pack_to_dict(pack: RetrievedPack) -> dict:
    return asdict(pack)
