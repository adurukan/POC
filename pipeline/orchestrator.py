import gc
import shutil
from dataclasses import dataclass
from pathlib import Path

from pipeline.extraction import marker_extractor, pages, report
from pipeline.sectioning.builder import slice_section
from pipeline.sectioning.config_loader import load_config
from pipeline.sectioning.index import SectionIndexEntry, write_index
from pipeline.understanding.agent import UNDERSTANDING_MODEL, generate_knowledge_pack
from pipeline.understanding.validator import validate


@dataclass
class ProcessResult:
    processed_dir: Path
    section_index_json: Path
    section_index_md: Path
    section_count: int


def process_pdf(
    *,
    pdf_path: Path,
    sections_path: Path,
    processed_root: Path,
) -> ProcessResult:
    cfg = load_config(sections_path)
    processed_dir = (processed_root / cfg.slug).resolve()
    original_dir = processed_dir / "original"
    pages_dir = processed_dir / "pages"
    extraction_dir = processed_dir / "extraction"
    sections_dir = processed_dir / "sections"
    raw_sections_dir = processed_dir / "sections_raw"
    index_dir = processed_dir / "index"

    for d in (
        original_dir,
        pages_dir,
        extraction_dir / "marker",
        sections_dir,
        raw_sections_dir,
        index_dir,
    ):
        d.mkdir(parents=True, exist_ok=True)

    copied_pdf = original_dir / pdf_path.name
    shutil.copy2(pdf_path, copied_pdf)

    page_count = pages.render_pages(copied_pdf, pages_dir)
    marker_result = marker_extractor.extract(copied_pdf, extraction_dir / "marker")
    report_path = report.write_report(
        extraction_dir / "extraction_report.md",
        pdf_filename=pdf_path.name,
        marker=marker_result,
    )

    chosen_raw_path = marker_result.raw_markdown_path
    chosen_raw_text = chosen_raw_path.read_text(encoding="utf-8")

    entries: list[SectionIndexEntry] = []
    for i, section in enumerate(cfg.sections, start=1):
        raw_section = slice_section(chosen_raw_text, section)
        raw_section_rel = Path("sections_raw") / f"{i:03d}_{section.slug}.md"
        raw_section_path = processed_dir / raw_section_rel
        raw_section_path.write_text(raw_section, encoding="utf-8")

        out_rel = Path("sections") / f"{i:03d}_{section.slug}.md"
        out_path = processed_dir / out_rel

        if not raw_section.strip():
            entries.append(
                SectionIndexEntry(
                    section_index=i,
                    title=section.title,
                    slug=section.slug,
                    page_start=section.page_start,
                    page_end=section.page_end,
                    output_path=str(out_rel),
                    raw_section_path=str(raw_section_rel),
                    extraction_status="empty",
                    generation_status="skipped",
                    validation_status="n/a",
                    review_status="needs_review",
                    understanding_model=UNDERSTANDING_MODEL,
                    error_message="Section slice is empty for marker extraction output.",
                )
            )
            continue

        agent = generate_knowledge_pack(
            section_title=section.title,
            grade=cfg.grade,
            subject=cfg.subject,
            book_title=cfg.title,
            source_pdf=cfg.document,
            page_start=section.page_start,
            page_end=section.page_end,
            extracted_section_content=raw_section,
            partial_dir=sections_dir / ".partials",
        )

        if agent.error:
            entries.append(
                SectionIndexEntry(
                    section_index=i,
                    title=section.title,
                    slug=section.slug,
                    page_start=section.page_start,
                    page_end=section.page_end,
                    output_path=str(out_rel),
                    raw_section_path=str(raw_section_rel),
                    extraction_status="ok",
                    generation_status="error",
                    validation_status="n/a",
                    review_status="needs_review",
                    understanding_model=agent.model,
                    used_map_reduce=agent.used_map_reduce,
                    map_chunk_count=agent.chunk_count,
                    error_message=agent.error,
                )
            )
            continue

        out_path.write_text(agent.markdown, encoding="utf-8")
        validation = validate(agent.markdown)
        is_valid = validation.ok
        review_status = "validated" if is_valid else "needs_review"
        error_message = None if is_valid else "; ".join(validation.reasons)

        entries.append(
            SectionIndexEntry(
                section_index=i,
                title=section.title,
                slug=section.slug,
                page_start=section.page_start,
                page_end=section.page_end,
                output_path=str(out_rel),
                raw_section_path=str(raw_section_rel),
                extraction_status="ok",
                generation_status="generated",
                validation_status="validated" if is_valid else "needs_review",
                review_status=review_status,
                understanding_model=agent.model,
                used_map_reduce=agent.used_map_reduce,
                map_chunk_count=agent.chunk_count,
                error_message=error_message,
            )
        )
        del raw_section
        gc.collect()

    meta = {
        "source_pdf": str(copied_pdf),
        "source_pdf_name": pdf_path.name,
        "extractor_name": "marker",
        "understanding_model": UNDERSTANDING_MODEL,
        "page_count": page_count,
        "report_path": str(report_path),
        "extractor": {
            "name": "marker",
            "version": marker_result.version,
            "raw_output": str(marker_result.raw_markdown_path),
        },
    }
    json_path, md_path = write_index(index_dir, cfg.title, entries, metadata=meta)
    return ProcessResult(
        processed_dir=processed_dir,
        section_index_json=json_path,
        section_index_md=md_path,
        section_count=len(entries),
    )
