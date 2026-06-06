"""add tagging item drafts

Revision ID: f1a2b3c4d5e6
Revises: e7f8a9b0c1d2
Create Date: 2026-06-06 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tagging_task_items", sa.Column("draft_tags", sa.JSON(), nullable=True))
    op.add_column("tagging_task_items", sa.Column("draft_classifications", sa.JSON(), nullable=True))
    op.add_column("tagging_task_items", sa.Column("draft_note", sa.Text(), nullable=True))
    op.add_column("tagging_task_items", sa.Column("draft_saved_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("tagging_task_items", "draft_saved_at")
    op.drop_column("tagging_task_items", "draft_note")
    op.drop_column("tagging_task_items", "draft_classifications")
    op.drop_column("tagging_task_items", "draft_tags")
