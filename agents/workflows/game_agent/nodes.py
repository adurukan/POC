"""Generator and validator nodes for the game subgraph.

The validator runs deterministic contract/interaction checks first, then a
qualitative LLM check.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm_factory import get_llm
from agents.workflows.game_agent.contract import (
    control_button_logic_errors,
    context_alignment_errors,
    initial_state_errors,
    interaction_evidence_errors,
    is_game_friendly_concept,
    layout_quality_errors,
    p5_canvas_size_errors,
    question_replay_errors,
    validate_game_artifact_schema,
)
from agents.workflows._shared import (
    Verdict,
    parse_artifact_json,
    parse_verdict,
)
from agents.workflows.game_agent.prompts import generator as gen_prompt
from agents.workflows.game_agent.prompts import validator as val_prompt
from agents.workflows.game_agent.state import GameState


def generator_node(state: GameState) -> dict:
    user_msg = gen_prompt.render_user_message(
        current_input=state["current_input"],
        prior_input=state.get("prior_input"),
        prior_output=state.get("prior_output"),
        feedback=state.get("feedback", ""),
    )
    llm = get_llm("generator_game")
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


def playwright_check(artifact: dict) -> Verdict | None:
    """Deterministic validation before LLM review."""
    if artifact.get("_unparseable"):
        return {
            "grade": "needs_improvement",
            "feedback": "Önceki çıktı JSON olarak ayrıştırılamadı. Geçerli JSON üret.",
        }
    schema_errors = validate_game_artifact_schema(artifact)
    if schema_errors:
        return {
            "grade": "needs_improvement",
            "feedback": "Şema hatası: " + " | ".join(schema_errors),
        }
    return None


def validator_node(state: GameState) -> dict:
    artifact = state["artifact"] or {}

    deterministic = playwright_check(artifact)
    if deterministic is not None:
        return _record(state, deterministic)

    replay_errors = question_replay_errors(
        artifact, current_input=state["current_input"]
    )
    if replay_errors:
        return _record(
            state,
            {
                "grade": "needs_improvement",
                "feedback": "Soru/şık tekrarı tespit edildi: "
                + " | ".join(replay_errors),
            },
        )

    alignment_errors = context_alignment_errors(
        artifact, current_input=state["current_input"]
    )
    if alignment_errors:
        return _record(
            state,
            {
                "grade": "needs_improvement",
                "feedback": "Bağlam uyumu zayıf: " + " | ".join(alignment_errors),
            },
        )

    # should_render=false is exceptional; enforce stricter behavior for
    # game-friendly concepts to bias toward playable outputs.
    if artifact.get("should_render") is False:
        rationale = str(artifact.get("rationale") or "").strip()
        if is_game_friendly_concept(state.get("current_input") or {}):
            return _record(
                state,
                {
                    "grade": "needs_improvement",
                    "feedback": "Bu konu etkileşimli oyun için uygun. should_render=true olacak şekilde yeniden üret.",
                },
            )
        if len(rationale) < 40:
            return _record(
                state,
                {
                    "grade": "needs_improvement",
                    "feedback": "should_render=false için daha somut/ikna edici bir rationale gerekli.",
                },
            )
        return _record(
            state,
            {
                "grade": "pass",
                "feedback": "should_render=false istisna yolu gerekçeyle kabul edildi.",
            },
        )

    interaction_errors = interaction_evidence_errors(str(artifact.get("p5_sketch", "")))
    if interaction_errors:
        return _record(
            state,
            {
                "grade": "needs_improvement",
                "feedback": "Etkileşim yetersiz: " + " | ".join(interaction_errors),
            },
        )

    canvas_errors = p5_canvas_size_errors(str(artifact.get("p5_sketch", "")), artifact)
    if canvas_errors:
        return _record(
            state,
            {
                "grade": "needs_improvement",
                "feedback": "Canvas/panel uyumu hatası: " + " | ".join(canvas_errors),
            },
        )

    layout_errors = layout_quality_errors(artifact)
    if layout_errors:
        return _record(
            state,
            {
                "grade": "needs_improvement",
                "feedback": "Yerleşim/okunabilirlik hatası: " + " | ".join(layout_errors),
            },
        )

    button_errors = control_button_logic_errors(str(artifact.get("p5_sketch", "")))
    if button_errors:
        return _record(
            state,
            {
                "grade": "needs_improvement",
                "feedback": "Buton etkileşimi hatası: " + " | ".join(button_errors),
            },
        )

    init_errors = initial_state_errors(artifact)
    if init_errors:
        return _record(
            state,
            {
                "grade": "needs_improvement",
                "feedback": "Başlangıç durumu hatası: " + " | ".join(init_errors),
            },
        )

    llm = get_llm("validator_game")
    user_msg = val_prompt.render_user_message(
        question_and_solution=state["current_input"], artifact=artifact
    )
    resp = llm.invoke(
        [SystemMessage(content=val_prompt.SYSTEM), HumanMessage(content=user_msg)]
    )
    verdict = parse_verdict(
        resp.content if isinstance(resp.content, str) else str(resp.content)
    )
    return _record(state, verdict)


def _record(state: GameState, verdict: Verdict) -> dict:
    trail = list(state.get("trail") or [])
    trail.append(
        {
            "attempt": state.get("attempt", 0),
            "artifact": state["artifact"] or {},
            "verdict": verdict,
        }
    )
    return {"verdict": verdict, "trail": trail, "feedback": verdict["feedback"]}
