"""Shared types for subgraphs.

Each subgraph (question, solver, game) implements the evaluator-optimizer
pattern with the same uniform state shape. The shape is:

    current_input  - the input this run is generating from
    prior_input    - what produced prior_output (None on first generation,
                     equal to current_input on internal retry / direct teacher
                     correction, different on cascade re-run)
    prior_output   - this agent's most recent artifact for the thread
    feedback       - validator suggestion on retry, classified teacher slice
                     on external dispatch, or empty on cascade-only re-run

Plus internal scratch (attempt, artifact, verdict, trail) and an output flag
(succeeded). Each subgraph defines its own TypedDict but conforms to this shape.
"""

import json
import re
from typing import Literal, TypedDict

Grade = Literal["pass", "needs_improvement", "give_up"]

# Validator runs at most this many times per subgraph invocation. Resets on
# every external feedback round (each round is a fresh authoring pass).
MAX_ATTEMPTS = 5


class Verdict(TypedDict):
    grade: Grade
    feedback: str


class TrailEntry(TypedDict, total=False):
    attempt: int
    artifact: dict
    verdict: Verdict


def parse_verdict(text: str) -> Verdict:
    """Parse the validator LLM's JSON output. Tolerates fenced code blocks.

    Falls back to ``give_up`` with the raw text in feedback if parsing fails;
    the orchestrator records this in `failures`.
    """
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if fenced:
        cleaned = fenced.group(1)
    try:
        obj = json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "grade": "give_up",
            "feedback": f"validator output unparseable: {text[:200]}",
        }

    grade = obj.get("grade")
    if grade not in ("pass", "needs_improvement", "give_up"):
        return {
            "grade": "give_up",
            "feedback": f"validator returned invalid grade: {grade!r}",
        }
    return {"grade": grade, "feedback": str(obj.get("feedback", ""))}


def parse_artifact_json(text: str) -> dict:
    """Parse a generator's JSON-in-prompt response.

    Tolerates fenced code blocks. Raises ValueError on hard parse failure;
    the validator's deterministic checks will catch this and route to retry.
    """
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if fenced:
        cleaned = fenced.group(1)
    return json.loads(cleaned)


def grade_to_route(
    verdict: Verdict | None, attempt: int
) -> Literal["pass", "retry", "give_up"]:
    """Route from validator verdict + attempt count to the conditional edge.

    Caller passes the attempt number that just completed. If the validator
    asked for improvement but we've exhausted MAX_ATTEMPTS, demote to give_up.
    """
    if verdict is None:
        return "give_up"
    grade = verdict["grade"]
    if grade == "pass":
        return "pass"
    if grade == "give_up":
        return "give_up"
    if attempt >= MAX_ATTEMPTS:
        return "give_up"
    return "retry"
