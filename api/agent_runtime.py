"""FastAPI lifespan-managed orchestrator graph + PostgresSaver.

The orchestrator graph is compiled once at app startup with a long-lived
PostgresSaver. Endpoints take the compiled graph via a FastAPI dependency
rather than opening a new saver context per request — that avoids both
connection overhead and the foot-gun of nested context managers in handlers.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from langgraph.checkpoint.postgres import PostgresSaver

from agents.main_agent.graph import build_orchestrator_graph

_GRAPH = None  # set on app startup; cleared on shutdown.


@asynccontextmanager
async def agent_lifespan(_app: FastAPI):
    """Open the PostgresSaver for the lifetime of the app, compile the graph."""
    global _GRAPH
    db_url = os.environ["DATABASE_URL"]
    with PostgresSaver.from_conn_string(db_url) as saver:
        _GRAPH = build_orchestrator_graph().compile(checkpointer=saver)
        try:
            yield
        finally:
            _GRAPH = None


def get_graph():
    """FastAPI dependency: returns the compiled graph, or 503 if not ready."""
    if _GRAPH is None:
        raise HTTPException(status_code=503, detail="Agent graph not initialized")
    return _GRAPH


def read_thread_state(graph, request_id: str) -> dict:
    """Read the latest checkpointed state for a thread, raise 404 if missing."""
    config = {"configurable": {"thread_id": request_id}}
    snapshot = graph.get_state(config)
    if snapshot is None or not snapshot.values:
        raise HTTPException(
            status_code=404, detail=f"No thread state for request_id={request_id}"
        )
    return dict(snapshot.values)


def iter_feedback_history(graph, request_id: str) -> list[dict]:
    """Walk the checkpoint history and return per-round feedback records.

    Returns a list of `{feedback_text, classification, dispatch_plan}` dicts in
    chronological order, one per external feedback round on this thread.
    """
    config = {"configurable": {"thread_id": request_id}}
    history = list(graph.get_state_history(config))
    history.reverse()  # chronological

    rounds: list[dict] = []
    seen_feedback_texts: set[str] = set()
    for snap in history:
        v = snap.values or {}
        ft = v.get("feedback_text")
        if not ft or ft in seen_feedback_texts:
            continue
        seen_feedback_texts.add(ft)
        rounds.append(
            {
                "feedback_text": ft,
                "classification": v.get("classification"),
                "dispatch_plan": v.get("dispatch_plan"),
            }
        )
    return rounds
