"""Semantic + metadata search over section_knowledge_packs."""

from dataclasses import dataclass

from sqlalchemy import select

from db.database import SessionLocal
from pipeline.embeddings.encoder import Encoder
from pipeline.models import SectionKnowledgePack


@dataclass
class SearchHit:
    id: int
    title: str
    slug: str
    grade: str | None
    subject: str | None
    source_pages: str
    review_status: str
    file_path: str
    similarity: float


def search(
    query: str,
    *,
    grade: str | None = None,
    subject: str | None = None,
    only_validated: bool = False,
    top_k: int = 5,
) -> list[SearchHit]:
    encoder = Encoder()
    [q_emb] = encoder.encode([query])

    session = SessionLocal()
    try:
        # cosine_distance is 1 - cosine_similarity; convert at the end.
        distance = SectionKnowledgePack.embedding.cosine_distance(q_emb).label("dist")
        stmt = select(SectionKnowledgePack, distance).order_by(distance).limit(top_k)
        if grade is not None:
            stmt = stmt.where(SectionKnowledgePack.grade == str(grade))
        if subject is not None:
            stmt = stmt.where(SectionKnowledgePack.subject == subject)
        if only_validated:
            stmt = stmt.where(
                SectionKnowledgePack.review_status.in_(("validated", "approved"))
            )
        # Embedding model match — guards against silent dim mismatch when the
        # configured encoder differs from what was used at ingest.
        stmt = stmt.where(SectionKnowledgePack.embedding_model == encoder.name)

        hits: list[SearchHit] = []
        for pack, dist in session.execute(stmt):
            hits.append(
                SearchHit(
                    id=pack.id,
                    title=pack.title,
                    slug=pack.slug,
                    grade=pack.grade,
                    subject=pack.subject,
                    source_pages=pack.source_pages,
                    review_status=pack.review_status,
                    file_path=pack.markdown_file_path,
                    similarity=float(1.0 - dist),
                )
            )
        return hits
    finally:
        session.close()
