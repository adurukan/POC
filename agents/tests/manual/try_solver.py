"""Run only the solver subgraph against a saved question artifact.

Usage:
    uv run python -m agents.tests.manual.try_solver --question fixtures/question_sample.json
"""

import json
from pathlib import Path

from agents.tests.manual._common import (
    apply_overrides,
    base_parser,
    print_final,
    stream_run,
)
from agents.workflows.solver_agent.graph import build_solver_graph


def main() -> None:
    p = base_parser("Run the solver subgraph in isolation.")
    p.add_argument(
        "--question",
        required=True,
        type=Path,
        help="Path to a JSON file with the question artifact.",
    )
    args = p.parse_args()
    apply_overrides(args)

    question = json.loads(args.question.read_text(encoding="utf-8"))
    graph = build_solver_graph().compile()
    final = stream_run(graph, {"current_input": question, "feedback": ""})
    print_final("solver subgraph final state", final)


if __name__ == "__main__":
    main()
