import json
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class SectionIndexEntry:
    section_index: int
    title: str
    slug: str
    page_start: int
    page_end: int
    output_path: str
    extraction_status: str  # ok | empty | error
    generation_status: str  # generated | skipped | error
    validation_status: str  # validated | needs_review | n/a
    raw_section_path: str | None = None
    review_status: str | None = None
    understanding_model: str | None = None
    used_map_reduce: bool | None = None
    map_chunk_count: int | None = None
    error_message: str | None = None


def write_index(
    out_dir: Path,
    document_title: str,
    entries: list[SectionIndexEntry],
    metadata: dict | None = None,
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "section_index.json"
    md_path = out_dir / "section_index.md"

    json_path.write_text(
        json.dumps(
            {
                "document_title": document_title,
                "metadata": metadata or {},
                "sections": [asdict(e) for e in entries],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    lines = [f"# Section Index: {document_title}", ""]
    for e in entries:
        lines += [
            f"## {e.section_index}. {e.title}",
            f"- Pages: {e.page_start}–{e.page_end}",
            f"- Output: `{e.output_path}`",
            f"- Extraction: {e.extraction_status}",
            f"- Generation: {e.generation_status}",
            f"- Validation: {e.validation_status}",
        ]
        if e.review_status:
            lines.append(f"- Review Status: {e.review_status}")
        if e.used_map_reduce is not None:
            lines.append(
                f"- Map-Reduce: {e.used_map_reduce} (chunks={e.map_chunk_count})"
            )
        if e.error_message:
            lines.append(f"- Error: {e.error_message}")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
