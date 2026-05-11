"""Run only the question subgraph.

Usage:
    uv run python -m agents.tests.manual.try_question --topic "kesirler" \
        [--seed 42] [--provider anthropic] [--model claude-opus-4-7]

Prints the retrieved pack reference, generated question, validator verdict,
and the per-attempt retry trail.
"""

from agents.tests.manual._common import (
    apply_overrides,
    base_parser,
    print_final,
    stream_run,
)
from agents.workflows.question_agent.graph import build_question_graph


def main() -> None:
    p = base_parser("Run the question subgraph in isolation.")
    p.add_argument(
        "--topic", required=True, help="Turkish topic, e.g. 'kesirler', 'tam sayılar'."
    )
    args = p.parse_args()
    apply_overrides(args)

    graph = build_question_graph().compile()
    final = stream_run(graph, {"current_input": args.topic, "feedback": ""})
    print_final("question subgraph final state", final)


if __name__ == "__main__":
    main()
