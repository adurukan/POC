"""Shared utilities for the manual-test CLIs.

Each CLI uses argparse, accepts --provider/--model overrides, prints the full
final state on exit, and writes JSON-friendly output.
"""

import argparse
import json
import os
import random
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def base_parser(description: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=description)
    p.add_argument(
        "--seed", type=int, default=None, help="Random seed for reproducibility."
    )
    p.add_argument(
        "--provider",
        choices=["anthropic", "openai"],
        default=None,
        help="Override LLM provider for this run.",
    )
    p.add_argument(
        "--model", type=str, default=None, help="Override model id for this run."
    )
    return p


def apply_overrides(args: argparse.Namespace) -> None:
    """Apply --provider / --model / --seed at process scope.

    Provider/model are applied by setting AGENT_*_PROVIDER / AGENT_*_MODEL env
    vars across all roles. The llm_factory reads these via Pydantic Settings
    on each get_llm() call after we clear its lru_cache.
    """
    load_dotenv(REPO_ROOT / ".env")
    if args.seed is not None:
        random.seed(args.seed)
    if args.provider or args.model:
        from agents.config import ROLE_NAMES, get_settings

        for role in ROLE_NAMES:
            if args.provider:
                os.environ[f"AGENT_{role.upper()}__PROVIDER"] = args.provider
            if args.model:
                os.environ[f"AGENT_{role.upper()}__MODEL"] = args.model
        get_settings.cache_clear()


def print_final(label: str, state: Any) -> None:
    print(f"\n=== {label} ===")
    print(json.dumps(_jsonable(state), indent=2, ensure_ascii=False))


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return repr(obj)


def load_fixture_json(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# ----- streaming / live observation -----

# Truncate long preview strings printed inline so the terminal stays readable.
_PREVIEW_MAX = 220

# Render template is owned by agents.workflows.game_agent.render — single source
# of truth shared with the orchestrator's game subgraph. Imported lazily inside
# write_game_html_from_artifact to keep the import surface tight.


def _shorten(s: str) -> str:
    s = s.replace("\n", " ⏎ ")
    return s if len(s) <= _PREVIEW_MAX else s[:_PREVIEW_MAX] + "…"


def _agent_label(ns_path: tuple[str, ...]) -> str:
    """Translate a langgraph namespace path into a short agent label.

    Top-level orchestrator nodes appear with an empty namespace; subgraph
    nodes appear with namespaces like ('run_question:abcd',). We strip the
    suffix and rename to the agent.
    """
    if not ns_path:
        return "main"
    head = ns_path[-1].split(":", 1)[0]
    return {
        "run_question": "question",
        "run_solver": "solver",
        "run_game": "game",
    }.get(head, head)


def _format_update(
    agent: str, node: str, update: dict, *, include_artifacts: bool
) -> list[str]:
    lines: list[str] = []
    if not isinstance(update, dict):
        lines.append(f"[{agent}/{node}] {_shorten(repr(update))}")
        return lines

    # Subgraph generator/validator: surface attempt + verdict + artifact preview.
    if node == "generator":
        attempt = update.get("attempt", "?")
        if include_artifacts:
            artifact = update.get("artifact")
            preview = (
                json.dumps(artifact, ensure_ascii=False)
                if artifact is not None
                else "(none)"
            )
            lines.append(f"[{agent}/gen #{attempt}] artifact: {_shorten(preview)}")
        else:
            lines.append(f"[{agent}/gen #{attempt}]")
    elif node == "validator":
        verdict = update.get("verdict") or {}
        grade = verdict.get("grade", "?")
        feedback = verdict.get("feedback", "")
        lines.append(f"[{agent}/val] grade={grade}  feedback={_shorten(feedback)}")
    elif node in ("succeed", "give_up"):
        lines.append(f"[{agent}/{node}] succeeded={update.get('succeeded')}")
    # Orchestrator nodes.
    elif node == "init":
        lines.append("[main/init]")
    elif node == "classify_feedback":
        cls = update.get("classification") or {}
        plan = update.get("dispatch_plan") or []
        lines.append(f"[main/classify] targets={cls.get('targets')} plan={plan}")
        slices = cls.get("slices") or {}
        for who, slc in slices.items():
            lines.append(f"  slice[{who}]: {_shorten(slc)}")
    elif node == "assemble":
        payload = update.get("payload") or {}
        failures = payload.get("failures") or []
        keys = [k for k in ("question", "solution", "game") if payload.get(k)]
        lines.append(f"[main/assemble] artifacts={keys} failures={failures}")
    elif node in ("run_question", "run_solver", "run_game"):
        # Orchestrator wrapping subgraph: the noteworthy bit is which artifact got set.
        which = node.split("_", 1)[1]
        if which in update and update[which] is not None:
            lines.append(f"[main/{node}] {which} artifact updated")
        if update.get("failures"):
            lines.append(f"[main/{node}] failures={update['failures']}")
    else:
        keys = list(update.keys())
        lines.append(f"[{agent}/{node}] keys={keys}")
    return lines


def stream_run(
    graph,
    inputs: dict,
    config: dict | None = None,
    *,
    live: bool = True,
    include_artifacts: bool = True,
) -> dict | None:
    """Run the graph with stream_mode='updates' and pretty-print events live.

    Returns the final state (the last accumulated values), or None if the
    graph did not yield any values event. Subgraph events are surfaced too so
    you can see each generator/validator step inside question/solver/game.
    """
    final_values: dict | None = None
    for event in graph.stream(
        inputs, config=config, stream_mode=["updates", "values"], subgraphs=True
    ):
        # Event shape with subgraphs=True + multiple modes: (ns_path, mode, payload)
        ns_path, mode, payload = event
        if mode == "values":
            final_values = payload
            continue
        # mode == "updates"; payload is {node_name: node_update}
        agent = _agent_label(tuple(ns_path))
        for node, update in payload.items():
            if live:
                for line in _format_update(
                    agent, node, update, include_artifacts=include_artifacts
                ):
                    print(line, flush=True)
    return final_values


def write_game_html_from_artifact(artifact: dict, out: Path) -> bool:
    """Write a renderable HTML file if the artifact contains a p5 sketch."""
    from agents.workflows.game_agent.render import render_game_html

    sketch = artifact.get("p5_sketch")
    if artifact.get("should_render") and isinstance(sketch, str) and sketch.strip():
        out.write_text(render_game_html(artifact), encoding="utf-8")
        print(f"\nWrote render to: {out} (open in a browser to inspect)")
        return True

    print(
        "\nGame artifact is not renderable (should_render false or missing p5_sketch)."
    )
    return False
