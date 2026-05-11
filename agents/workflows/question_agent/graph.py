"""Question subgraph: evaluator-optimizer (generator + validator)."""

from langgraph.graph import END, START, StateGraph

from agents.workflows._shared import grade_to_route
from agents.workflows.question_agent.nodes import generator_node, validator_node
from agents.workflows.question_agent.state import QuestionState


def _route(state: QuestionState):
    decision = grade_to_route(state.get("verdict"), state.get("attempt", 0))
    if decision == "pass":
        return "succeed"
    if decision == "retry":
        return "generator"
    return "give_up"


def _succeed(state: QuestionState) -> dict:
    return {"succeeded": True}


def _give_up(state: QuestionState) -> dict:
    return {"succeeded": False}


def build_question_graph():
    g = StateGraph(QuestionState)
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
