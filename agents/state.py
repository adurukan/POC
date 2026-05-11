"""Top-level orchestrator state.

Persisted per request_id by LangGraph's PostgresSaver. Feedback rounds resume
the same thread and read the prior artifacts as each agent's `prior_output`.
"""

from typing import Any, Literal, TypedDict

AgentName = Literal["question", "solver", "game"]


class FeedbackClassification(TypedDict):
    targets: list[AgentName]
    slices: dict[str, str]


class OrchestratorState(TypedDict, total=False):
    request_id: str
    topic: str
    count: int

    # Curriculum scope, set by the teacher's selectors. Threaded into the
    # question subgraph (for RAG filtering) and the game subgraph (for filename).
    grade: str
    subject: str

    # Latest artifacts for this thread. Carry across feedback rounds.
    question: dict | None
    solution: dict | None
    game: dict | None

    # Game agent's rendered HTML path, relative to api/visuals/.
    # Set on successful game generation; consumed by the Accept endpoint as
    # `questions.visual_path` so no post-insert update is needed.
    game_visual_path: str | None

    # Feedback-round inputs.
    feedback_text: str | None
    classification: FeedbackClassification | None
    dispatch_plan: list[AgentName]

    # Bookkeeping.
    failures: list[str]  # entries like "question:gave_up"
    payload: dict | None  # final assembled output
    trails: dict[str, list[Any]]
