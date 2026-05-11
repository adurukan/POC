"""pending_questions queue table

Revision ID: 20260511_0003
Revises: 20260509_0002
Create Date: 2026-05-11

Backs the queue-based teacher studio: agents pre-generate questions via the
CLI into this table; the teacher's studio pulls one at a time and either
accepts (move to questions), rejects (move to issues/rejected), or gives
feedback (move to issues/feedback for later operator-run replay).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260511_0003"
down_revision: Union[str, Sequence[str], None] = "20260509_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pending_questions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("request_id", sa.String(), nullable=False),
        sa.Column("grade", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("topic", sa.String(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=True),
        sa.Column(
            "solution_steps", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("visual_path", sa.String(), nullable=True),
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("trails", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "feedback_history",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", name="uq_pending_questions_request_id"),
        sa.CheckConstraint(
            "status IN ('pending', 'in_feedback')",
            name="ck_pending_questions_status",
        ),
    )

    op.create_index(
        "ix_pending_questions_queue",
        "pending_questions",
        ["subject", "status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_pending_questions_queue", table_name="pending_questions")
    op.drop_table("pending_questions")
