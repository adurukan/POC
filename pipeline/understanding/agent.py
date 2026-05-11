"""Section Understanding Agent.

Uses OpenAI gpt-5.4-mini with streaming output. Single-pass for sections that fit
in a configurable token budget; map-reduce for sections that don't.

Design notes:
  - Streaming so partial Markdown can be persisted to a .partial file as it arrives.
  - System prompt is large + fixed → automatic prompt-prefix caching across calls.
  - Sequential per section (predictable RAM, predictable cost).
  - 2 attempts per call with exponential backoff on rate-limit / timeout.
"""

import gc
import time
from dataclasses import dataclass
from pathlib import Path

import tiktoken
from openai import APITimeoutError, OpenAI, RateLimitError

from .prompt import (
    MAP_INSTRUCTIONS,
    SYSTEM_INSTRUCTIONS,
    build_map_user_message,
    build_reduce_user_message,
    build_user_message,
)

UNDERSTANDING_MODEL = "gpt-5.4-mini"

# Reserve ~32k for instructions + reduce-side notes + completion headroom.
SINGLE_PASS_TOKEN_BUDGET = 60_000
MAP_CHUNK_TOKEN_BUDGET = 25_000

MAX_ATTEMPTS = 2
BACKOFF_SECONDS = (2, 8)


@dataclass
class AgentResult:
    markdown: str
    used_map_reduce: bool
    chunk_count: int
    error: str | None
    model: str


def _enc():
    # Encoder used for budget estimation. Newer models default to o200k_base.
    try:
        return tiktoken.encoding_for_model(UNDERSTANDING_MODEL)
    except KeyError:
        return tiktoken.get_encoding("o200k_base")


def _count_tokens(text: str) -> int:
    return len(_enc().encode(text))


def _split_by_pages(extracted: str, target_tokens: int) -> list[tuple[str, str]]:
    """Split extracted content (with <!-- PAGE N --> markers) into chunks ≤ target_tokens.

    Returns list of (chunk_text, page_range_str) tuples.
    """
    import re

    enc = _enc()
    parts = re.split(r"(<!-- PAGE \d+ -->)", extracted)
    # parts alternate between "" / non-marker and marker tokens. Reassemble into
    # (marker, body) pairs so each chunk starts with a page marker.
    blocks: list[tuple[int, str]] = []
    current_page = None
    current_body: list[str] = []
    for part in parts:
        m = re.fullmatch(r"<!-- PAGE (\d+) -->", part)
        if m:
            if current_page is not None:
                blocks.append((current_page, "".join(current_body)))
            current_page = int(m.group(1))
            current_body = [part, "\n"]
        else:
            current_body.append(part)
    if current_page is not None:
        blocks.append((current_page, "".join(current_body)))

    chunks: list[tuple[str, str]] = []
    buf: list[str] = []
    buf_pages: list[int] = []
    buf_tokens = 0
    for page, body in blocks:
        body_tokens = len(enc.encode(body))
        if buf and buf_tokens + body_tokens > target_tokens:
            chunks.append(
                (
                    "".join(buf),
                    f"{buf_pages[0]}-{buf_pages[-1]}" if buf_pages else "?",
                )
            )
            buf, buf_pages, buf_tokens = [], [], 0
        buf.append(body)
        buf_pages.append(page)
        buf_tokens += body_tokens
    if buf:
        chunks.append(
            (
                "".join(buf),
                f"{buf_pages[0]}-{buf_pages[-1]}" if buf_pages else "?",
            )
        )
    return chunks


def _stream_completion(
    client: OpenAI,
    *,
    system_text: str,
    user_text: str,
    partial_path: Path | None,
) -> str:
    """Run a streamed chat completion, optionally writing deltas to partial_path."""
    last_error: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            stream = client.chat.completions.create(
                model=UNDERSTANDING_MODEL,
                messages=[
                    {"role": "system", "content": system_text},
                    {"role": "user", "content": user_text},
                ],
                stream=True,
            )
            collected: list[str] = []
            if partial_path is not None:
                partial_path.parent.mkdir(parents=True, exist_ok=True)
                partial_path.write_text("", encoding="utf-8")
            for event in stream:
                if not event.choices:
                    continue
                delta = event.choices[0].delta
                content = getattr(delta, "content", None)
                if content:
                    collected.append(content)
                    if partial_path is not None:
                        with partial_path.open("a", encoding="utf-8") as f:
                            f.write(content)
            return "".join(collected)
        except (RateLimitError, APITimeoutError) as e:
            last_error = e
            if attempt + 1 < MAX_ATTEMPTS:
                time.sleep(BACKOFF_SECONDS[attempt])
            else:
                raise
    raise last_error or RuntimeError("unreachable")


def generate_knowledge_pack(
    *,
    section_title: str,
    grade: str,
    subject: str,
    book_title: str,
    source_pdf: str,
    page_start: int,
    page_end: int,
    extracted_section_content: str,
    partial_dir: Path | None = None,
    client: OpenAI | None = None,
) -> AgentResult:
    """Generate one Turkish Markdown knowledge pack for a section.

    Single pass when extracted content fits in SINGLE_PASS_TOKEN_BUDGET.
    Otherwise: map (per chunk) → reduce (consolidated notes → final Markdown).
    """
    if client is None:
        client = OpenAI()

    extracted_tokens = _count_tokens(extracted_section_content)
    used_map_reduce = extracted_tokens > SINGLE_PASS_TOKEN_BUDGET

    try:
        if not used_map_reduce:
            user = build_user_message(
                section_title=section_title,
                grade=grade,
                subject=subject,
                book_title=book_title,
                source_pdf=source_pdf,
                page_start=page_start,
                page_end=page_end,
                extracted_section_content=extracted_section_content,
            )
            partial = (
                (partial_dir / f"{_slug(section_title)}.partial.md")
                if partial_dir
                else None
            )
            md = _stream_completion(
                client,
                system_text=SYSTEM_INSTRUCTIONS,
                user_text=user,
                partial_path=partial,
            )
            return AgentResult(
                markdown=md,
                used_map_reduce=False,
                chunk_count=1,
                error=None,
                model=UNDERSTANDING_MODEL,
            )

        # ── Map-reduce ──────────────────────────────────────────────────────
        chunks = _split_by_pages(extracted_section_content, MAP_CHUNK_TOKEN_BUDGET)
        notes: list[str] = []
        for i, (chunk_text, page_range_str) in enumerate(chunks, start=1):
            user = build_map_user_message(
                section_title=section_title,
                chunk_index=i,
                total_chunks=len(chunks),
                page_range_str=page_range_str,
                extracted_chunk=chunk_text,
            )
            partial = (
                (partial_dir / f"{_slug(section_title)}.map_{i}.partial.md")
                if partial_dir
                else None
            )
            note = _stream_completion(
                client,
                system_text=MAP_INSTRUCTIONS,
                user_text=user,
                partial_path=partial,
            )
            notes.append(f"### Parça {i} ({page_range_str})\n\n{note}\n")
            del chunk_text
            gc.collect()

        consolidated = "\n".join(notes)
        reduce_user = build_reduce_user_message(
            section_title=section_title,
            grade=grade,
            subject=subject,
            book_title=book_title,
            source_pdf=source_pdf,
            page_start=page_start,
            page_end=page_end,
            consolidated_notes=consolidated,
        )
        partial = (
            (partial_dir / f"{_slug(section_title)}.reduce.partial.md")
            if partial_dir
            else None
        )
        md = _stream_completion(
            client,
            system_text=SYSTEM_INSTRUCTIONS,
            user_text=reduce_user,
            partial_path=partial,
        )
        return AgentResult(
            markdown=md,
            used_map_reduce=True,
            chunk_count=len(chunks),
            error=None,
            model=UNDERSTANDING_MODEL,
        )
    except Exception as e:
        return AgentResult(
            markdown="",
            used_map_reduce=used_map_reduce,
            chunk_count=0,
            error=f"{type(e).__name__}: {e}",
            model=UNDERSTANDING_MODEL,
        )


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in s.lower())[:60]
