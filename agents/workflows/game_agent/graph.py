"""Game subgraph: evaluator-optimizer (generator + validator).

On `succeed`, materialize the artifact to a self-contained HTML file under
api/visuals/teacher/ and surface the relative path as `rendered_path` so the
orchestrator (and ultimately the Accept endpoint) can consume it directly with
no two-phase update.

Distinguishing rule: when MAX_ATTEMPTS is hit, the orchestrator treats the
result as success with should_render=false (legitimate "no useful
visualization") rather than as failure — see assemble logic in main_agent.
"""

from langgraph.graph import END, START, StateGraph

from agents.workflows._shared import grade_to_route
from agents.workflows.game_agent.nodes import generator_node, validator_node
from agents.workflows.game_agent.render import write_game_html
from agents.workflows.game_agent.state import GameState


def _route(state: GameState):
    decision = grade_to_route(state.get("verdict"), state.get("attempt", 0))
    if decision == "pass":
        return "succeed"
    if decision == "retry":
        return "generator"
    return "give_up"


def _succeed(state: GameState) -> dict:
    """Render artifact to disk if should_render=true; surface the path."""
    artifact = state.get("artifact") or {}
    out: dict = {"succeeded": True}

    if not artifact.get("should_render"):
        # Legitimate "no useful visualization" pass; nothing to render.
        return out

    grade = state.get("grade")
    subject = state.get("subject")
    request_id = state.get("request_id")
    if not (grade and subject and request_id):
        # Missing labelling metadata — fall back to success without a file.
        # The orchestrator forwards these from OrchestratorState; this guard
        # only fires for direct subgraph invocations (e.g. try_game.py without
        # the new flags). The CLI handles its own HTML write separately.
        return out

    try:
        rel_path = write_game_html(
            artifact, grade=grade, subject=subject, request_id=request_id
        )
        out["rendered_path"] = rel_path
    except Exception as exc:  # noqa: BLE001
        # Don't fail the run if disk write fails; surface as a soft warning in trail.
        out["rendered_path"] = None
        out["render_error"] = str(exc)
    return out


def _give_up(state: GameState) -> dict:
    # The orchestrator interprets give_up here as should_render=false.
    return {"succeeded": False}


def build_game_graph():
    g = StateGraph(GameState)
    g.add_node("generator", generator_node)
    g.add_node("validator", validator_node)
    g.add_node("succeed", _succeed)
    g.add_node("give_up", _give_up)

    g.add_edge(START, "generator")
    g.add_edge("generator", "validator")
    g.add_conditional_edges(
        "validator",
        _route,
        {"succeed": "succeed", "generator": "generator", "give_up": "give_up"},
    )
    g.add_edge("succeed", END)
    g.add_edge("give_up", END)
    return g
