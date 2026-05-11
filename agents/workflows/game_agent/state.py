"""State for the game subgraph.

Game artifact (v1 structured contract):
    {
      "should_render": bool,
      "game_type": "manipulation"|"button_step"|"mixed",
      "learning_goal": str,
      "instructions_short": str,
      "interaction_model": {
        "inputs": [str, ...],
        "affordances": [str, ...],
        "user_actions": [str, ...]
      },
      "success_condition": str,
      "feedback_model": {"on_correct": str, "on_incorrect": str},
      "state_model": {"tracked_vars": [str, ...]},
      "layout_model": {
        "target_panel": "top_right_30pct",
        "canvas_width": int,
        "canvas_height": int,
        "boxes": [{"id": str, "x": number, "y": number, "w": number, "h": number}, ...]
      },
      "p5_sketch": str,   # required when should_render=true
      "rationale": str,
    }
"""

from typing import TypedDict

from agents.workflows._shared import TrailEntry, Verdict


class GameInput(TypedDict, total=False):
    # current_input bundles the question and solution.
    current_input: dict
    prior_input: dict | None
    prior_output: dict | None
    feedback: str

    # Labelling metadata, threaded by the orchestrator from OrchestratorState.
    # Used to compute the rendered HTML filename on success.
    grade: str
    subject: str
    request_id: str


class GameState(GameInput, total=False):
    attempt: int
    artifact: dict | None
    verdict: Verdict | None
    trail: list[TrailEntry]
    succeeded: bool

    # Relative path under api/visuals/ to the rendered HTML, set by succeed_node
    # only when should_render=true and the artifact passed validation.
    rendered_path: str | None
