from dataclasses import dataclass
from pathlib import Path
import re


@dataclass
class MarkerResult:
    raw_markdown_path: Path
    pages_with_text: list[int]
    total_pages: int
    version: str
    note: str


def extract(pdf_path: Path, out_dir: Path) -> MarkerResult:
    """Extract the full PDF with Marker, writing raw_extraction.md.

    Marker output is requested with pagination and then normalized to
    <!-- PAGE N --> markers so section slicers can use page ranges reliably.
    """
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    import marker

    out_dir.mkdir(parents=True, exist_ok=True)
    page_separator = "<<MARKER_PAGE_BREAK>>"
    converter = PdfConverter(
        artifact_dict=create_model_dict(),
        config={"paginate_output": True, "page_separator": page_separator},
    )
    rendered = converter(str(pdf_path))

    md = getattr(rendered, "markdown", None) or ""
    md = _normalize_marker_markdown(md, page_separator=page_separator)
    raw_path = out_dir / "raw_extraction.md"
    raw_path.write_text(md, encoding="utf-8")

    page_count = 0
    meta = getattr(rendered, "metadata", None)
    if isinstance(meta, dict):
        page_stats = meta.get("page_stats")
        if isinstance(page_stats, list):
            page_count = len(page_stats)

    version = getattr(marker, "__version__", "unknown")
    note = (
        "Marker output has been normalized with <!-- PAGE N --> markers so section "
        "page-range slicing works deterministically."
    )

    pages_with_text = _extract_pages_with_text(md)
    if page_count <= 0:
        page_count = max(pages_with_text, default=0)

    return MarkerResult(
        raw_markdown_path=raw_path,
        pages_with_text=pages_with_text,
        total_pages=page_count,
        version=version,
        note=note,
    )


def _normalize_marker_markdown(markdown: str, *, page_separator: str) -> str:
    """Convert Marker paginate output to <!-- PAGE N --> chunks."""
    marker_re = re.compile(rf"\{{(\d+)\}}{re.escape(page_separator)}")
    matches = list(marker_re.finditer(markdown))
    if not matches:
        # Fallback: keep content but still make slicing helpers deterministic.
        body = markdown.strip()
        return f"<!-- PAGE 1 -->\n\n{body}\n" if body else ""

    chunks: list[tuple[int, str]] = []
    for idx, m in enumerate(matches):
        raw_page_id = int(m.group(1))
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(markdown)
        body = markdown[start:end].strip()
        chunks.append((raw_page_id, body))

    page_ids = [pid for pid, _ in chunks]
    min_id = min(page_ids)
    max_id = max(page_ids)
    looks_zero_based = min_id == 0 and max_id == len(set(page_ids)) - 1
    offset = 1 if looks_zero_based else 0

    by_page: dict[int, list[str]] = {}
    for raw_pid, body in chunks:
        page_no = raw_pid + offset
        by_page.setdefault(page_no, []).append(body)

    page_numbers = sorted(by_page.keys())
    out_chunks: list[str] = []
    for page in range(page_numbers[0], page_numbers[-1] + 1):
        body = "\n\n".join(s for s in by_page.get(page, []) if s.strip()).strip()
        out_chunks.append(f"<!-- PAGE {page} -->\n\n{body}\n")
    return "\n".join(out_chunks)


def _extract_pages_with_text(markdown: str) -> list[int]:
    pages: list[int] = []
    for match in re.finditer(r"<!-- PAGE (\d+) -->", markdown):
        page = int(match.group(1))
        next_match = re.search(r"<!-- PAGE \d+ -->", markdown[match.end() :])
        end = len(markdown) if next_match is None else match.end() + next_match.start()
        body = markdown[match.end() : end].strip()
        if body:
            pages.append(page)
    return pages
