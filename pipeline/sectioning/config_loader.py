from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class SectionSpec:
    title: str
    slug: str
    page_start: int
    page_end: int


@dataclass
class DocumentConfig:
    document: str  # e.g. "matematik_5_1.pdf"
    title: str
    grade: str
    subject: str
    language: str
    sections: list[SectionSpec]

    @property
    def slug(self) -> str:
        # "matematik_5_1.pdf" → "matematik_5_1"
        return Path(self.document).stem


def load_config(path: Path) -> DocumentConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    sections = [
        SectionSpec(
            title=s["title"],
            slug=s["slug"],
            page_start=int(s["page_start"]),
            page_end=int(s["page_end"]),
        )
        for s in data["sections"]
    ]
    return DocumentConfig(
        document=data["document"],
        title=data["title"],
        grade=str(data["grade"]),
        subject=data["subject"],
        language=data["language"],
        sections=sections,
    )
