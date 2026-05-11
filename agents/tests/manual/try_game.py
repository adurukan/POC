"""Run only the game subgraph against a saved question + solution.

Usage:
    uv run python -m agents.tests.manual.try_game \
        --question fixtures/question_sample.json \
        --solution fixtures/solution_sample.json \
        [--render-out /tmp/game.html]

When the artifact's should_render is true, the CLI also writes the rendered
sketch (p5.js + the generated code) to --render-out so it can be opened in a
browser to confirm visually that the game corresponds to the question.
"""

import json
from pathlib import Path

from agents.tests.manual._common import (
    apply_overrides,
    base_parser,
    print_final,
    stream_run,
    write_game_html_from_artifact,
)
from agents.workflows.game_agent.graph import build_game_graph


def main() -> None:
    p = base_parser("Run the game subgraph in isolation.")
    p.add_argument("--question", required=True, type=Path)
    p.add_argument("--solution", required=True, type=Path)
    p.add_argument("--render-out", type=Path, default=Path("/tmp/game.html"))
    args = p.parse_args()
    apply_overrides(args)

    question = json.loads(args.question.read_text(encoding="utf-8"))
    solution = json.loads(args.solution.read_text(encoding="utf-8"))
    bundle = {"question": question, "solution": solution}

    graph = build_game_graph().compile()
    final = stream_run(graph, {"current_input": bundle, "feedback": ""})
    print_final("game subgraph final state", final)

    artifact = (final or {}).get("artifact") or {}
    write_game_html_from_artifact(artifact, args.render_out)


if __name__ == "__main__":
    main()
