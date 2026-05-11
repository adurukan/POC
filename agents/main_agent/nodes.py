"""Orchestrator nodes.

The main agent does no LLM-based planning. The only LLM call here is the
feedback classifier. All other routing is deterministic Python.

Subgraph dispatch: each subgraph is compiled once at module load and invoked
inline as a node. Per the base plan, v1 runs serially (question -> solver ->
game in dependency order). The base plan calls for Send for first-class graph
events; that is a future-parallelism optimization and is not required for v1
correctness — flagged here so it isn't lost.
"""

import json
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import text

from agents.llm_factory import get_llm
from agents.main_agent.prompts import feedback_classifier as fc_prompt
from agents.state import AgentName, FeedbackClassification, OrchestratorState
from agents.workflows._shared import parse_artifact_json
from agents.workflows.game_agent.graph import build_game_graph
from agents.workflows.question_agent.graph import build_question_graph
from agents.workflows.solver_agent.graph import build_solver_graph
from db.database import SessionLocal

_question_subgraph = build_question_graph().compile()
_solver_subgraph = build_solver_graph().compile()
_game_subgraph = build_game_graph().compile()


# ---------- Generation flow ----------


def init_node(state: OrchestratorState) -> dict:
    """Initialize a new generation request."""
    return {
        "failures": list(state.get("failures") or []),
        "trails": dict(state.get("trails") or {}),
    }


def run_question(state: OrchestratorState) -> dict:
    feedback_classification = state.get("classification") or {}
    slices = (feedback_classification or {}).get("slices") or {}
    is_feedback = bool(state.get("feedback_text"))

    sub_input = {
        "current_input": state["topic"],
        "prior_input": state["topic"] if is_feedback else None,
        "prior_output": state.get("question") if is_feedback else None,
        "feedback": slices.get("question", ""),
        "grade": state.get("grade", ""),
        "subject": state.get("subject", ""),
    }
    result = _question_subgraph.invoke(sub_input)
    return _absorb_subgraph_result(state, "question", result, artifact_field="question")


def run_solver(state: OrchestratorState) -> dict:
    is_feedback = bool(state.get("feedback_text"))
    slices = (state.get("classification") or {}).get("slices") or {}
    new_question = state.get("question")

    # cascade: if question changed, prior_input is the prior question
    prior_input = None
    prior_output = None
    if is_feedback:
        prior_output = state.get("solution")
        prior_input = state.get(
            "question"
        )  # the prior question is what produced prior_output

    sub_input = {
        "current_input": new_question,
        "prior_input": prior_input,
        "prior_output": prior_output,
        "feedback": slices.get("solver", ""),
    }
    result = _solver_subgraph.invoke(sub_input)
    return _absorb_subgraph_result(state, "solver", result, artifact_field="solution")


def run_game(state: OrchestratorState) -> dict:
    is_feedback = bool(state.get("feedback_text"))
    slices = (state.get("classification") or {}).get("slices") or {}
    bundle = {"question": state.get("question"), "solution": state.get("solution")}

    prior_input = None
    prior_output = None
    if is_feedback:
        prior_output = state.get("game")
        # the prior bundle is whatever produced the prior game artifact;
        # we approximate as the prior (question, solution) — same shape.
        prior_input = bundle  # in practice equal unless we tracked snapshots

    sub_input = {
        "current_input": bundle,
        "prior_input": prior_input,
        "prior_output": prior_output,
        "feedback": slices.get("game", ""),
        "grade": state.get("grade", ""),
        "subject": state.get("subject", ""),
        "request_id": state.get("request_id", ""),
    }
    result = _game_subgraph.invoke(sub_input)
    update = _absorb_subgraph_result(state, "game", result, artifact_field="game")
    # Surface the rendered HTML's relative path onto orchestrator state so the
    # Accept endpoint can write it straight into questions.visual_path.
    update["game_visual_path"] = result.get("rendered_path")
    return update


def assemble_node(state: OrchestratorState) -> dict:
    """Pure-Python assembly of the final payload (no LLM).

    Partial payloads are valid output: the assembled payload includes whatever
    artifacts succeeded, plus the failures list.
    """
    payload = {
        "request_id": state["request_id"],
        "topic": state["topic"],
        "count": state["count"],
        "question": state.get("question"),
        "solution": state.get("solution"),
        "game": state.get("game"),
        "failures": list(state.get("failures") or []),
        "assembled_at": datetime.now(timezone.utc).isoformat(),
    }
    _upsert_problem(
        request_id=state["request_id"],
        topic=state["topic"],
        count=state["count"],
        payload=payload,
    )
    return {"payload": payload}


# ---------- Feedback flow ----------


def classify_feedback_node(state: OrchestratorState) -> dict:
    """One LLM call to split the teacher's message into per-agent slices."""
    feedback_text = state.get("feedback_text") or ""
    llm = get_llm("feedback_classifier")
    resp = llm.invoke(
        [
            SystemMessage(content=fc_prompt.SYSTEM),
            HumanMessage(content=fc_prompt.render_user_message(feedback_text)),
        ]
    )
    try:
        parsed = parse_artifact_json(
            resp.content if isinstance(resp.content, str) else str(resp.content)
        )
    except ValueError:
        parsed = {"targets": [], "slices": {}}

    targets_raw = parsed.get("targets") or []
    slices_raw = parsed.get("slices") or {}
    targets: list[AgentName] = [
        t for t in targets_raw if t in ("question", "solver", "game")
    ]
    slices = {
        k: str(v) for k, v in slices_raw.items() if k in ("question", "solver", "game")
    }

    classification: FeedbackClassification = {"targets": targets, "slices": slices}
    plan = _cascade_plan(targets)

    return {"classification": classification, "dispatch_plan": plan}


def _cascade_plan(targets: list[AgentName]) -> list[AgentName]:
    """Compute cascade closure in dependency order: question -> solver -> game.

    - question targeted -> solver and game also re-run (their input changed)
    - solver targeted   -> game also re-runs
    Cascade-implied agents get an empty feedback slice.
    """
    plan: list[AgentName] = []
    if "question" in targets:
        plan = ["question", "solver", "game"]
    elif "solver" in targets:
        plan = ["solver", "game"]
    elif "game" in targets:
        plan = ["game"]
    return plan


# ---------- Helpers ----------


def _absorb_subgraph_result(
    state: OrchestratorState,
    agent: str,
    result: dict,
    *,
    artifact_field: str,
) -> dict:
    succeeded = bool(result.get("succeeded"))
    artifact = result.get("artifact")
    failures = list(state.get("failures") or [])
    trails = dict(state.get("trails") or {})
    trails[agent] = result.get("trail") or []

    update: dict = {"failures": failures, "trails": trails}

    if succeeded:
        update[artifact_field] = artifact
    else:
        # Game agent: give_up means should_render=false, treated as success with a degraded artifact.
        if agent == "game":
            update[artifact_field] = {
                "should_render": False,
                "rationale": "validator give_up: pedagogically useful visualization not produced",
            }
        else:
            failures.append(f"{agent}:gave_up")
            update[artifact_field] = artifact  # keep the last attempt for inspection

    return update


def has_question(state: OrchestratorState) -> bool:
    q = state.get("question")
    return bool(q) and not any(
        f.startswith("question:") for f in (state.get("failures") or [])
    )


def has_solution(state: OrchestratorState) -> bool:
    s = state.get("solution")
    return bool(s) and not any(
        f.startswith("solver:") for f in (state.get("failures") or [])
    )


def _upsert_problem(*, request_id: str, topic: str, count: int, payload: dict) -> None:
    """Persist assembled output by request_id, updating in-place on feedback runs."""
    stmt = text(
        """
        INSERT INTO problems (request_id, topic, count, payload_json)
        VALUES (:request_id, :topic, :count, CAST(:payload_json AS jsonb))
        ON CONFLICT (request_id)
        DO UPDATE SET
            topic = EXCLUDED.topic,
            count = EXCLUDED.count,
            payload_json = EXCLUDED.payload_json,
            updated_at = now()
        """
    )
    with SessionLocal() as session:
        session.execute(
            stmt,
            {
                "request_id": request_id,
                "topic": topic,
                "count": count,
                "payload_json": json.dumps(payload, ensure_ascii=False),
            },
        )
        session.commit()
