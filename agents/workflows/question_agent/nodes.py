"""Generator and validator nodes for the question subgraph."""

import re

from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm_factory import get_llm
from agents.workflows._shared import (
    Verdict,
    parse_artifact_json,
    parse_verdict,
)
from agents.workflows.question_agent.prompts import generator as gen_prompt
from agents.workflows.question_agent.prompts import validator as val_prompt
from agents.workflows.question_agent.rag import retrieve, retrieved_pack_to_dict
from agents.workflows.question_agent.state import QuestionState


def generator_node(state: QuestionState) -> dict:
    """Retrieve (on first attempt) and generate a question artifact."""
    retrieved = state.get("retrieved_pack")
    if retrieved is None:
        kwargs = {}
        if state.get("grade"):
            kwargs["grade"] = state["grade"]
        if state.get("subject"):
            kwargs["subject"] = state["subject"]
        pack = retrieve(state["current_input"], **kwargs)
        retrieved = retrieved_pack_to_dict(pack) if pack else None

    pack_md = (retrieved or {}).get("markdown_content", "")
    user_msg = gen_prompt.render_user_message(
        current_input=state["current_input"],
        prior_input=state.get("prior_input"),
        prior_output=state.get("prior_output"),
        feedback=state.get("feedback", ""),
        retrieved_pack_markdown=pack_md,
    )

    llm = get_llm("generator_question")
    resp = llm.invoke(
        [SystemMessage(content=gen_prompt.SYSTEM), HumanMessage(content=user_msg)]
    )

    try:
        artifact = parse_artifact_json(
            resp.content if isinstance(resp.content, str) else str(resp.content)
        )
    except ValueError:
        # Hard parse failure becomes an unparseable artifact; validator will
        # return give_up on the deterministic check.
        artifact = {"_unparseable": True, "raw": str(resp.content)[:500]}

    attempt = state.get("attempt", 0) + 1
    return {
        "retrieved_pack": retrieved,
        "artifact": artifact,
        "attempt": attempt,
    }


def validator_node(state: QuestionState) -> dict:
    """Run deterministic checks then a qualitative LLM check.

    NOTE: deterministic checks are placeholders (curriculum match, Turkish
    language, structural validity) — to be filled in by the follow-up plan.
    """
    artifact = state["artifact"] or {}
    pack_md = (state.get("retrieved_pack") or {}).get("markdown_content", "")

    # --- deterministic checks ---
    if artifact.get("_unparseable"):
        verdict: Verdict = {
            "grade": "needs_improvement",
            "feedback": "Önceki çıktı JSON olarak ayrıştırılamadı. Geçerli JSON üret.",
        }
        return _record(state, verdict)
    if (
        not isinstance(artifact.get("question_text"), str)
        or not artifact["question_text"].strip()
    ):
        verdict = {
            "grade": "needs_improvement",
            "feedback": "question_text boş veya geçersiz.",
        }
        return _record(state, verdict)
    if (
        not isinstance(artifact.get("expected_answer"), str)
        or not artifact["expected_answer"].strip()
    ):
        return _record(
            state,
            {
                "grade": "needs_improvement",
                "feedback": "expected_answer boş veya geçersiz.",
            },
        )

    question_text = artifact["question_text"]
    # Ban explicit multiple-choice style question format.
    if _looks_multiple_choice(question_text):
        return _record(
            state,
            {
                "grade": "needs_improvement",
                "feedback": "Çoktan seçmeli şık formatı yasak. Şıksız, muhakeme odaklı soru üret.",
            },
        )

    # Geometry concept questions should require reasoning, not recall only.
    topic = str(state.get("current_input") or "").lower()
    if any(k in topic for k in ("geometri", "şekil", "açı", "ücgen", "üçgen")):
        if not _asks_for_reasoning(question_text):
            return _record(
                state,
                {
                    "grade": "needs_improvement",
                    "feedback": "Geometri sorusu muhakeme istemeli (neden/nasıl/açıkla/göster).",
                },
            )

    # --- qualitative LLM check ---
    llm = get_llm("validator_question")
    user_msg = val_prompt.render_user_message(
        current_input=state["current_input"],
        artifact=artifact,
        retrieved_pack_markdown=pack_md,
    )
    resp = llm.invoke(
        [SystemMessage(content=val_prompt.SYSTEM), HumanMessage(content=user_msg)]
    )
    verdict = parse_verdict(
        resp.content if isinstance(resp.content, str) else str(resp.content)
    )
    return _record(state, verdict)


def _record(state: QuestionState, verdict: Verdict) -> dict:
    trail = list(state.get("trail") or [])
    trail.append(
        {
            "attempt": state.get("attempt", 0),
            "artifact": state["artifact"] or {},
            "verdict": verdict,
        }
    )
    return {"verdict": verdict, "trail": trail, "feedback": verdict["feedback"]}


def _looks_multiple_choice(text: str) -> bool:
    patterns = (
        r"\bA\)",
        r"\bB\)",
        r"\bC\)",
        r"\bD\)",
        r"\bşık\b",
        r"\bseçenek\b",
        r"\bhangisi\b",
    )
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)


def _asks_for_reasoning(text: str) -> bool:
    prompts = ("neden", "nasıl", "açıkla", "göster", "gerekçelendir", "kanıtla")
    lowered = text.lower()
    return any(p in lowered for p in prompts)
