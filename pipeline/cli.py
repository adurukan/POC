from pathlib import Path
from pipeline.orchestrator import process_pdf as run_process_pdf
from pipeline.storage.loader import load_processed_dir
from pipeline.storage.search import search as search_packs
import typer
from dotenv import load_dotenv

_PIPELINE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PIPELINE_DIR.parent


# Ensure OPENAI_API_KEY/DATABASE_URL are available for all CLI subcommands.
# Load root .env first, then optional pipeline-local .env.
load_dotenv(_REPO_ROOT / ".env")
load_dotenv(_PIPELINE_DIR / ".env")

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("process-pdf")
def process_pdf_cmd(
    pdf: Path = typer.Option(..., "--pdf", exists=True, readable=True),
    sections: Path = typer.Option(..., "--sections", exists=True, readable=True),
    processed_root: Path = typer.Option(
        Path("../processed"), "--processed-root", file_okay=False, dir_okay=True
    ),
) -> None:
    result = run_process_pdf(
        pdf_path=pdf,
        sections_path=sections,
        processed_root=processed_root,
    )
    typer.echo(f"Processed dir: {result.processed_dir}")
    typer.echo(f"Sections processed: {result.section_count}")
    typer.echo("Extractor: marker")
    typer.echo(f"Index JSON: {result.section_index_json}")
    typer.echo(f"Index MD: {result.section_index_md}")


@app.command("load-packs")
def load_packs_cmd(
    processed_dir: Path = typer.Option(
        ..., "--processed-dir", exists=True, file_okay=False, readable=True
    ),
) -> None:
    report = load_processed_dir(processed_dir.resolve())
    typer.echo(f"Load completed: inserted/updated={report['inserted']}")
    typer.echo(f"Document ID: {report['document_id']}")
    typer.echo(f"Ingestion Run ID: {report['ingestion_run_id']}")


@app.command("search")
def search_cmd(
    query: str = typer.Option(..., "--query"),
    grade: str | None = typer.Option(None, "--grade"),
    subject: str | None = typer.Option(None, "--subject"),
    only_validated: bool = typer.Option(False, "--only-validated"),
    top_k: int = typer.Option(5, "--top-k"),
) -> None:
    hits = search_packs(
        query=query,
        grade=grade,
        subject=subject,
        only_validated=only_validated,
        top_k=top_k,
    )
    if not hits:
        typer.echo("No results.")
        return
    for i, hit in enumerate(hits, start=1):
        typer.echo(f"{i}. {hit.title}")
        typer.echo(
            f"   slug={hit.slug} | grade={hit.grade} | subject={hit.subject} | similarity={hit.similarity:.4f}"
        )
        typer.echo(
            f"   pages={hit.source_pages} | review_status={hit.review_status} | file={hit.file_path}"
        )


if __name__ == "__main__":
    app()
