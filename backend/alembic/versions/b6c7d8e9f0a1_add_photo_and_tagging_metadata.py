"""add photo and tagging metadata

Revision ID: b6c7d8e9f0a1
Revises: a2b3c4d5e6f7
Create Date: 2026-06-08 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b6c7d8e9f0a1"
down_revision: Union[str, Sequence[str], None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("photos", sa.Column("title", sa.String(length=200), nullable=True))
    op.add_column("photos", sa.Column("author", sa.String(length=100), nullable=True))

    op.add_column("tagging_task_items", sa.Column("original_title", sa.String(length=200), nullable=True))
    op.add_column("tagging_task_items", sa.Column("original_author", sa.String(length=100), nullable=True))
    op.add_column("tagging_task_items", sa.Column("submitted_title", sa.String(length=200), nullable=True))
    op.add_column("tagging_task_items", sa.Column("submitted_author", sa.String(length=100), nullable=True))
    op.add_column("tagging_task_items", sa.Column("draft_title", sa.String(length=200), nullable=True))
    op.add_column("tagging_task_items", sa.Column("draft_author", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("tagging_task_items", "draft_author")
    op.drop_column("tagging_task_items", "draft_title")
    op.drop_column("tagging_task_items", "submitted_author")
    op.drop_column("tagging_task_items", "submitted_title")
    op.drop_column("tagging_task_items", "original_author")
    op.drop_column("tagging_task_items", "original_title")

    op.drop_column("photos", "author")
    op.drop_column("photos", "title")
