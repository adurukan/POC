"""End-to-end orchestrator run.

Usage:
    uv run python -m agents.tests.manual.try_full_pipeline \
        --topic "kesirler" --count 1 [--request-id REQ_42] [--ephemeral] \
        [--render-game-html --render-out /tmp/game.html]

By default uses PostgresSaver so the resulting thread can later be exercised
with try_feedback. Pass --ephemeral to use an in-memory checkpointer (no
persistence; cannot resume).
"""

import os
import uuid

from langgraph.checkpoint.memory import InMemorySaver

from agents.main_agent.graph import (
    compile_with_checkpointer,
    open_postgres_checkpointer,
)
from agents.workflows.game_agent.contract import (
    interaction_evidence_errors,
    layout_quality_errors,
    p5_canvas_size_errors,
)
from agents.tests.manual._common import (
    apply_overrides,
    base_parser,
    stream_run,
    write_game_html_from_artifact,
)


def main() -> None:
    p = base_parser("Run the full orchestrator end-to-end.")
    p.add_argument("--topic", required=True)
    p.add_argument("--count", type=int, default=1)
    p.add_argument("--request-id", default=None, help="Defaults to a fresh uuid.")
    p.add_argument(
        "--ephemeral", action="store_true", help="Use InMemorySaver (no resume)."
    )
    p.add_argument(
        "--live",
        action="store_true",
        help="Print live node updates while running (default is quiet).",
    )
    p.add_argument(
        "--include-artifacts",
        action="store_true",
        help="When --live is used, include artifact previews in live logs.",
    )
    p.add_argument(
        "--full-state",
        action="store_true",
        help="Print full final state JSON (default prints a compact trails summary).",
    )
    p.add_argument(
        "--render-game-html",
        action="store_true",
        help="Export game artifact as HTML if should_render=true.",
    )
    p.add_argument("--render-out", type=str, default="/tmp/game.html")
    args = p.parse_args()
    apply_overrides(args)

    request_id = args.request_id or f"req_{uuid.uuid4().hex[:8]}"
    initial = {"request_id": request_id, "topic": args.topic, "count": args.count}
    config = {"configurable": {"thread_id": request_id}}

    if args.ephemeral:
        graph = compile_with_checkpointer(InMemorySaver())
        final = stream_run(
            graph,
            initial,
            config=config,
            live=args.live,
            include_artifacts=args.include_artifacts,
        )
    else:
        db_url = os.environ["DATABASE_URL"]
        with open_postgres_checkpointer(db_url) as saver:
            graph = compile_with_checkpointer(saver)
            final = stream_run(
                graph,
                initial,
                config=config,
                live=args.live,
                include_artifacts=args.include_artifacts,
            )

    if not isinstance(final, dict):
        print("\nNo final state produced.")
        return

    if args.full_state:
        from agents.tests.manual._common import print_final

        label = f"orchestrator final state ({'ephemeral' if args.ephemeral else 'persisted'}, thread_id={request_id})"
        print_final(label, final)
    else:
        compact = {
            "request_id": final.get("request_id", request_id),
            "failures": final.get("failures") or [],
            "trails": final.get("trails") or {},
        }
        from agents.tests.manual._common import print_final

        print_final(
            f"orchestrator trails summary ({'ephemeral' if args.ephemeral else 'persisted'}, thread_id={request_id})",
            compact,
        )

    exported_from = "none"
    exported_attempt: int | None = None
    game_artifact = (final.get("payload") or {}).get("game")
    if not isinstance(game_artifact, dict):
        game_artifact = final.get("game") if isinstance(final.get("game"), dict) else {}

    if args.render_game_html:
        from pathlib import Path

        exported_from = "final"
        exported = write_game_html_from_artifact(game_artifact, Path(args.render_out))
        if not exported:
            # Fallback: use the latest renderable attempt from game trail.
            trails = final.get("trails") or {}
            game_trail = trails.get("game") if isinstance(trails, dict) else None
            fallback, attempt = _latest_renderable_from_game_trail(game_trail)
            if isinstance(fallback, dict):
                print("Falling back to latest renderable game trail attempt...")
                exported_from = "trail"
                exported_attempt = attempt
                write_game_html_from_artifact(fallback, Path(args.render_out))
                game_artifact = fallback

    interactive_ok = (
        len(interaction_evidence_errors(str(game_artifact.get("p5_sketch", "")))) == 0
        if isinstance(game_artifact, dict)
        else False
    )
    layout_ok = (
        len(layout_quality_errors(game_artifact)) == 0
        and len(
            p5_canvas_size_errors(str(game_artifact.get("p5_sketch", "")), game_artifact)
        )
        == 0
        if isinstance(game_artifact, dict)
        else False
    )
    game_type = (
        game_artifact.get("game_type") if isinstance(game_artifact, dict) else None
    )
    print(
        "Game result: "
        f"export_source={exported_from}"
        f"{'' if exported_attempt is None else f' export_attempt={exported_attempt}'} "
        f"game_type={game_type or 'n/a'} interactive_checks_passed={interactive_ok} "
        f"layout_checks_passed={layout_ok}"
    )


def _latest_renderable_from_game_trail(game_trail) -> tuple[dict | None, int | None]:
    if not isinstance(game_trail, list):
        return None, None
    for step in reversed(game_trail):
        if not isinstance(step, dict):
            continue
        artifact = step.get("artifact")
        if not isinstance(artifact, dict):
            continue
        if artifact.get("should_render") and isinstance(artifact.get("p5_sketch"), str):
            if artifact["p5_sketch"].strip():
                return artifact, step.get("attempt")
    return None, None


if __name__ == "__main__":
    main()
