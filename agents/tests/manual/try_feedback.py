"""Exercise the feedback path against a checkpointed thread.

Usage:
    uv run python -m agents.tests.manual.try_feedback \
        --request-id REQ_42 --feedback "Yaptığın oyun çalışmıyor, soruyu xxx şeklinde değiştir."

Prints the classifier's slices per agent, the dispatch plan (including
cascade-implied agents), and the updated payload after re-running.
"""

import os

from agents.main_agent.graph import (
    compile_with_checkpointer,
    open_postgres_checkpointer,
)
from agents.tests.manual._common import (
    apply_overrides,
    base_parser,
    print_final,
    stream_run,
)


def main() -> None:
    p = base_parser("Run a feedback round against an existing thread.")
    p.add_argument(
        "--request-id", required=True, help="The thread/request_id to resume."
    )
    p.add_argument(
        "--feedback", required=True, help="Turkish feedback message from the teacher."
    )
    args = p.parse_args()
    apply_overrides(args)

    db_url = os.environ["DATABASE_URL"]
    with open_postgres_checkpointer(db_url) as saver:
        graph = compile_with_checkpointer(saver)
        config = {"configurable": {"thread_id": args.request_id}}
        # The orchestrator sees feedback_text and routes through classify_feedback.
        final = stream_run(graph, {"feedback_text": args.feedback}, config=config)
        print_final("orchestrator final state after feedback", final)


if __name__ == "__main__":
    main()
