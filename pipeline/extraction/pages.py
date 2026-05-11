from pathlib import Path

import pypdfium2 as pdfium


def render_pages(pdf_path: Path, out_dir: Path, scale: float = 2.0) -> int:
    """Render every PDF page to out_dir/page_NNN.png. Idempotent; skips existing files."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf = pdfium.PdfDocument(str(pdf_path))
    n = len(pdf)
    for i in range(n):
        out_path = out_dir / f"page_{i + 1:03d}.png"
        if out_path.exists():
            continue
        page = pdf[i]
        bitmap = page.render(scale=scale)
        pil = bitmap.to_pil()
        pil.save(out_path)
    pdf.close()
    return n
