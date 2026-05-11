"""State for the question subgraph."""

from typing import TypedDict

from agents.workflows._shared import TrailEntry, Verdict


class QuestionInput(TypedDict, total=False):
    # Uniform 4-field generator input — see workflows/_shared.py docstring.
    current_input: str  # the topic to ground in
    prior_input: str | None  # prior topic that produced prior_output, if different
    prior_output: dict | None  # prior question artifact
    feedback: str  # validator suggestion or teacher slice or ""

    # RAG filters set by the orchestrator from the teacher's selectors.
    grade: str
    subject: str


class QuestionState(QuestionInput, total=False):
    # RAG context set by the generator on first attempt and re-used on retries.
    retrieved_pack: dict | None  # serialized RetrievedPack

    # Scratch.
    attempt: int
    artifact: dict | None
    verdict: Verdict | None
    trail: list[TrailEntry]

    # Output.
    succeeded: bool
