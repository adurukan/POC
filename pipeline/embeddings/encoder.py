"""OpenAI text-embedding-3-small encoder (1536-dim).

Single class so future swaps (e.g. text-embedding-3-large at 3072-dim) only need
a new column / migration, not a code refactor downstream.
"""

import re
from dataclasses import dataclass

from openai import OpenAI

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536


@dataclass
class Encoder:
    name: str = EMBEDDING_MODEL
    dim: int = EMBEDDING_DIM
    _client: OpenAI | None = None

    def _ensure_client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI()
        return self._client

    def encode(self, texts: list[str]) -> list[list[float]]:
        client = self._ensure_client()
        resp = client.embeddings.create(model=self.name, input=texts)
        return [d.embedding for d in resp.data]


def build_searchable_text(
    *,
    title: str,
    subject: str,
    grade: str,
    source_pages: str,
    markdown_content: str,
) -> str:
    """Per the spec: title + subject + grade + pages + Kısa Açıklama + first chunk
    of Konunun Anlatımı. Full markdown stays separately in markdown_content."""
    short_desc = _extract_section(markdown_content, "Kısa Açıklama")
    body = _extract_section(markdown_content, "Konunun Anlatımı")
    return (
        f"{title} — {subject} — {grade}. sınıf — sayfa {source_pages}\n\n"
        f"{short_desc}\n\n"
        f"{body[:1500]}"
    )


def _extract_section(markdown: str, heading: str) -> str:
    pattern = rf"^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s|\Z)"
    m = re.search(pattern, markdown, re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""
