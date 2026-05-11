"""Generator and validator nodes for the solver subgraph.

The validator runs a SymPy-based deterministic check (PLACEHOLDER stub here;
the real implementation lives in a sandboxed subprocess per the base plan)
followed by a qualitative LLM check.
"""

import re

from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm_factory import get_llm
from agents.workflows._shared import (
    Verdict,
    parse_artifact_json,
    parse_verdict,
)
from agents.workflows.solver_agent.prompts import generator as gen_prompt
from agents.workflows.solver_agent.prompts import validator as val_prompt
from agents.workflows.solver_agent.state import SolverState


def generator_node(state: SolverState) -> dict:
    user_msg = gen_prompt.render_user_message(
        current_input=state["current_input"],
        prior_input=state.get("prior_input"),
        prior_output=state.get("prior_output"),
        feedback=state.get("feedback", ""),
    )
    llm = get_llm("generator_solver")
    resp = llm.invoke(
        [SystemMessage(content=gen_prompt.SYSTEM), HumanMessage(content=user_msg)]
    )
    try:
        artifact = parse_artifact_json(
            resp.content if isinstance(resp.content, str) else str(resp.content)
        )
    except ValueError:
        artifact = {"_unparseable": True, "raw": str(resp.content)[:500]}

    return {"artifact": artifact, "attempt": state.get("attempt", 0) + 1}


def sympy_check(artifact: dict, question: dict) -> Verdict | None:
    """Deterministic SymPy verification of the solution.

    PLACEHOLDER stub: returns None (defer to LLM check) unless the artifact
    fails basic structural checks. The follow-up plan implements:
      - parse each step's `expression` as a SymPy equation
      - verify intermediate equalities chain to the final answer
      - run inside a sandboxed subprocess with a timeout
    """
    if artifact.get("_unparseable"):
        return {
            "grade": "needs_improvement",
            "feedback": "Önceki çıktı JSON olarak ayrıştırılamadı. Geçerli JSON üret.",
        }
    steps = artifact.get("steps")
    if not isinstance(steps, list) or not steps:
        return {
            "grade": "needs_improvement",
            "feedback": "steps listesi boş veya geçersiz.",
        }
    for i, s in enumerate(steps):
        if not isinstance(s, dict) or "description" not in s or "expression" not in s:
            return {
                "grade": "needs_improvement",
                "feedback": f"steps[{i}] eksik alan: description ve expression gerekli.",
            }
    if not artifact.get("final_answer"):
        return {
            "grade": "needs_improvement",
            "feedback": "final_answer boş veya geçersiz.",
        }

    # Require a minimum explanatory depth, especially for geometry/angle topics.
    if len(steps) < 3:
        return {
            "grade": "needs_improvement",
            "feedback": "En az 3 adımlı öğretici çözüm gerekli.",
        }

    question_text = _extract_question_text(question).lower()
    geom_topic = any(k in question_text for k in ("açı", "ücgen", "üçgen", "geometr"))
    if geom_topic:
        all_desc = " ".join(str(s.get("description", "")) for s in steps).lower()
        all_expr = " ".join(str(s.get("expression", "")) for s in steps).lower()
        # Ensure there is an explicit reasoning reference, not only final statement.
        if not any(
            k in (all_desc + " " + all_expr)
            for k in ("180", "doğru açı", "doğrusal", "iç açı", "paralel", "toplam")
        ):
            return {
                "grade": "needs_improvement",
                "feedback": "Geometri çözümünde kural/gerekçe açıkça gösterilmeli (örn. 180° ilişkisi).",
            }
        if _is_answer_only_solution(steps, artifact.get("final_answer", "")):
            return {
                "grade": "needs_improvement",
                "feedback": "Çözüm sonucu söylemekle kalmış; ara gerekçeyi ve ilişkiyi adımlarla göster.",
            }
    return None


def validator_node(state: SolverState) -> dict:
    artifact = state["artifact"] or {}
    deterministic = sympy_check(artifact, state["current_input"])
    if deterministic is not None:
        return _record(state, deterministic)

    llm = get_llm("validator_solver")
    user_msg = val_prompt.render_user_message(
        question=state["current_input"], artifact=artifact
    )
    resp = llm.invoke(
        [SystemMessage(content=val_prompt.SYSTEM), HumanMessage(content=user_msg)]
    )
    verdict = parse_verdict(
        resp.content if isinstance(resp.content, str) else str(resp.content)
    )
    return _record(state, verdict)


def _record(state: SolverState, verdict: Verdict) -> dict:
    trail = list(state.get("trail") or [])
    trail.append(
        {
            "attempt": state.get("attempt", 0),
            "artifact": state["artifact"] or {},
            "verdict": verdict,
        }
    )
    return {"verdict": verdict, "trail": trail, "feedback": verdict["feedback"]}


def _extract_question_text(question: dict) -> str:
    if isinstance(question, dict):
        if isinstance(question.get("question_text"), str):
            return question["question_text"]
    return str(question)


def _is_answer_only_solution(steps: list[dict], final_answer: str) -> bool:
    # Heuristic: if descriptions are tiny and mostly restate final answer, flag it.
    desc_join = " ".join(str(s.get("description", "")) for s in steps).lower()
    expr_join = " ".join(str(s.get("expression", "")) for s in steps).lower()
    dense = re.sub(r"\s+", " ", (desc_join + " " + expr_join)).strip()
    exprs = [str(s.get("expression", "")).strip().lower() for s in steps]
    unique_exprs = {e for e in exprs if e}

    if len(dense) < 70:
        return True
    fa = str(final_answer).lower().strip()
    if fa and dense.count(fa) >= 2 and len(dense) < 140:
        return True
    # Repeating same expression across all steps is typically non-explanatory.
    if len(unique_exprs) <= 1 and len(steps) >= 3:
        return True
    # Causal connectors suggest explanation quality.
    if not any(
        token in dense for token in ("çünkü", "bu nedenle", "dolayısıyla", "önce", "sonra", "bundan")
    ):
        if len(unique_exprs) <= 2:
            return True
    return False
