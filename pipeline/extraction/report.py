from pathlib import Path

from .marker_extractor import MarkerResult


TURKISH_CHARS = set("çÇğĞıİöÖşŞüÜ")


def _has_turkish_chars(text: str) -> bool:
    return any(c in TURKISH_CHARS for c in text[:50_000])


def write_report(
    out_path: Path,
    pdf_filename: str,
    marker: MarkerResult,
) -> Path:
    marker_md = (
        marker.raw_markdown_path.read_text(encoding="utf-8")
        if marker.raw_markdown_path.exists()
        else ""
    )

    weak_pages = sorted(
        set(range(1, marker.total_pages + 1)) - set(marker.pages_with_text)
    )

    lines = [
        "# Extraction Report",
        "",
        f"- Source PDF: `{pdf_filename}`",
        "",
        "## Marker",
        f"- Version: `{marker.version}`",
        f"- Total pages detected: {marker.total_pages}",
        f"- Pages with extracted text: {len(marker.pages_with_text)}",
        f"- Likely weak / image-only pages: {len(weak_pages)}",
        f"- First 20 weak pages: {weak_pages[:20]}",
        f"- Turkish characters preserved: {_has_turkish_chars(marker_md)}",
        f"- Output size (chars): {len(marker_md)}",
        f"- Output: `{marker.raw_markdown_path}`",
        f"- Note: {marker.note}",
        "",
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
