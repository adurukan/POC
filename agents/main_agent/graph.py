"""Main orchestrator graph.

Two entry points wrapped in a single graph distinguished by `feedback_text`
in the input state:

  * Generation flow: init -> question -> solver -> game -> assemble
    (with conditional skips when a subgraph fails)

  * Feedback flow: classify_feedback -> dispatch via dispatch_plan ->
    question? -> solver? -> game? -> assemble

Both flows converge at `assemble`. The flow is selected at the entry edge
based on whether `feedback_text` is set.
"""

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph

from agents.main_agent.nodes import (
    assemble_node,
    classify_feedback_node,
    has_question,
    has_solution,
    init_node,
    run_game,
    run_question,
    run_solver,
)
from agents.state import OrchestratorState


def _entry_route(state: OrchestratorState) -> str:
    return "classify_feedback" if state.get("feedback_text") else "init"


def _after_question(state: OrchestratorState) -> str:
    if not has_question(state):
        return "assemble"
    return "run_solver"


def _after_solver(state: OrchestratorState) -> str:
    if not has_solution(state):
        return "assemble"
    return "run_game"


def _after_classify(state: OrchestratorState) -> str:
    plan = state.get("dispatch_plan") or []
    if "question" in plan:
        return "run_question"
    if "solver" in plan:
        return "run_solver"
    if "game" in plan:
        return "run_game"
    return "assemble"


def _after_question_feedback(state: OrchestratorState) -> str:
    plan = state.get("dispatch_plan") or []
    if not has_question(state):
        return "assemble"
    if "solver" in plan or "game" in plan:
        return "run_solver"
    return "assemble"


def _after_solver_feedback(state: OrchestratorState) -> str:
    plan = state.get("dispatch_plan") or []
    if not has_solution(state):
        return "assemble"
    if "game" in plan:
        return "run_game"
    return "assemble"


def build_orchestrator_graph():
    g = StateGraph(OrchestratorState)
    g.add_node("init", init_node)
    g.add_node("classify_feedback", classify_feedback_node)
    g.add_node("run_question", run_question)
    g.add_node("run_solver", run_solver)
    g.add_node("run_game", run_game)
    g.add_node("assemble", assemble_node)

    # Pick generation vs feedback based on input.
    g.add_conditional_edges(
        START,
        _entry_route,
        {"init": "init", "classify_feedback": "classify_feedback"},
    )

    # Generation flow.
    g.add_edge("init", "run_question")

    # Feedback flow uses different post-question / post-solver routing because
    # the dispatch plan determines which downstream agents re-run.
    def _post_question(state: OrchestratorState) -> str:
        if state.get("feedback_text"):
            return _after_question_feedback(state)
        return _after_question(state)

    def _post_solver(state: OrchestratorState) -> str:
        if state.get("feedback_text"):
            return _after_solver_feedback(state)
        return _after_solver(state)

    g.add_conditional_edges(
        "run_question",
        _post_question,
        {"run_solver": "run_solver", "assemble": "assemble"},
    )
    g.add_conditional_edges(
        "run_solver",
        _post_solver,
        {"run_game": "run_game", "assemble": "assemble"},
    )
    g.add_edge("run_game", "assemble")

    # Feedback flow entry routing.
    g.add_conditional_edges(
        "classify_feedback",
        _after_classify,
        {
            "run_question": "run_question",
            "run_solver": "run_solver",
            "run_game": "run_game",
            "assemble": "assemble",
        },
    )

    g.add_edge("assemble", END)
    return g


def compile_with_checkpointer(checkpointer=None):
    """Compile the orchestrator graph with the given checkpointer.

    Pass a langgraph.checkpoint.postgres.PostgresSaver for production. The
    manual-test CLIs may pass an InMemorySaver or None for ephemeral runs.
    """
    return build_orchestrator_graph().compile(checkpointer=checkpointer)


def open_postgres_checkpointer(conn_string: str):
    """Context-manager wrapper around PostgresSaver.from_conn_string.

    Usage:
        with open_postgres_checkpointer(DATABASE_URL) as saver:
            graph = compile_with_checkpointer(saver)
            graph.invoke(...)
    """
    return PostgresSaver.from_conn_string(conn_string)
