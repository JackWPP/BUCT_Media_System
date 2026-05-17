"""add tagging tasks

Revision ID: d4e5f6a7b8c9
Revises: a1b2c3d4e5f6
Create Date: 2026-05-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tag_aliases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tag_aliases_tag_id"), "tag_aliases", ["tag_id"], unique=False)
    op.create_index(op.f("ix_tag_aliases_alias"), "tag_aliases", ["alias"], unique=True)

    op.create_table(
        "tagging_tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("creator_id", sa.String(length=36), nullable=False),
        sa.Column("assignee_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tagging_tasks_creator_id"), "tagging_tasks", ["creator_id"], unique=False)
    op.create_index(op.f("ix_tagging_tasks_assignee_id"), "tagging_tasks", ["assignee_id"], unique=False)
    op.create_index(op.f("ix_tagging_tasks_status"), "tagging_tasks", ["status"], unique=False)

    op.create_table(
        "tagging_task_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("photo_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("original_tags", sa.JSON(), nullable=True),
        sa.Column("submitted_tags", sa.JSON(), nullable=True),
        sa.Column("original_classifications", sa.JSON(), nullable=True),
        sa.Column("submitted_classifications", sa.JSON(), nullable=True),
        sa.Column("submitter_note", sa.Text(), nullable=True),
        sa.Column("reviewer_id", sa.String(length=36), nullable=True),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["photo_id"], ["photos.id"]),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tagging_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "photo_id", name="uq_tagging_task_item_photo"),
    )
    op.create_index(op.f("ix_tagging_task_items_task_id"), "tagging_task_items", ["task_id"], unique=False)
    op.create_index(op.f("ix_tagging_task_items_photo_id"), "tagging_task_items", ["photo_id"], unique=False)
    op.create_index(op.f("ix_tagging_task_items_status"), "tagging_task_items", ["status"], unique=False)
    op.create_index(op.f("ix_tagging_task_items_reviewer_id"), "tagging_task_items", ["reviewer_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tagging_task_items_reviewer_id"), table_name="tagging_task_items")
    op.drop_index(op.f("ix_tagging_task_items_status"), table_name="tagging_task_items")
    op.drop_index(op.f("ix_tagging_task_items_photo_id"), table_name="tagging_task_items")
    op.drop_index(op.f("ix_tagging_task_items_task_id"), table_name="tagging_task_items")
    op.drop_table("tagging_task_items")

    op.drop_index(op.f("ix_tagging_tasks_status"), table_name="tagging_tasks")
    op.drop_index(op.f("ix_tagging_tasks_assignee_id"), table_name="tagging_tasks")
    op.drop_index(op.f("ix_tagging_tasks_creator_id"), table_name="tagging_tasks")
    op.drop_table("tagging_tasks")

    op.drop_index(op.f("ix_tag_aliases_alias"), table_name="tag_aliases")
    op.drop_index(op.f("ix_tag_aliases_tag_id"), table_name="tag_aliases")
    op.drop_table("tag_aliases")

