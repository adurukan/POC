import re

from .config_loader import SectionSpec

PAGE_MARKER_RE = re.compile(r"<!-- PAGE (\d+) -->")


def slice_section(raw_markdown: str, section: SectionSpec) -> str:
    """Return Markdown text for a section's page range, based on <!-- PAGE N --> markers."""
    matches = list(PAGE_MARKER_RE.finditer(raw_markdown))
    if not matches:
        return raw_markdown  # no markers — return whole document and let agent handle

    start_idx = None
    end_idx = len(raw_markdown)
    for i, m in enumerate(matches):
        page = int(m.group(1))
        if start_idx is None and page >= section.page_start:
            start_idx = m.start()
        if page > section.page_end:
            end_idx = m.start()
            break
    if start_idx is None:
        return ""
    return raw_markdown[start_idx:end_idx].strip()
