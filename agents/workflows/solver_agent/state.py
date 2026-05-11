"""State for the solver subgraph."""

from typing import TypedDict

from agents.workflows._shared import TrailEntry, Verdict


class SolverInput(TypedDict, total=False):
    # current_input is the question artifact (dict).
    current_input: dict
    prior_input: dict | None
    prior_output: dict | None
    feedback: str


class SolverState(SolverInput, total=False):
    attempt: int
    artifact: dict | None
    verdict: Verdict | None
    trail: list[TrailEntry]
    succeeded: bool
