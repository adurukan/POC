"""agents init: langgraph checkpoint tables + problems table

Revision ID: 20260509_0002
Revises: 20260509_0001
Create Date: 2026-05-09

"""

import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260509_0002"
down_revision: Union[str, Sequence[str], None] = "20260509_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "problems",
        sa.Column("request_id", sa.String(), nullable=False),
        sa.Column("topic", sa.String(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column(
            "payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False
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
        sa.PrimaryKeyConstraint("request_id"),
    )

    # LangGraph PostgresSaver owns its own checkpoint schema. We invoke its
    # setup() here (rather than at app start) so the DDL is part of the
    # alembic migration history. PostgresSaver uses psycopg v3 with a separate
    # connection, so this is outside the alembic transaction — but setup() is
    # idempotent, so re-running the migration is safe.
    from langgraph.checkpoint.postgres import PostgresSaver

    db_url = os.environ["DATABASE_URL"]
    with PostgresSaver.from_conn_string(db_url) as saver:
        saver.setup()


def downgrade() -> None:
    for tbl in (
        "checkpoint_writes",
        "checkpoint_blobs",
        "checkpoints",
        "checkpoint_migrations",
    ):
        op.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
    op.drop_table("problems")
