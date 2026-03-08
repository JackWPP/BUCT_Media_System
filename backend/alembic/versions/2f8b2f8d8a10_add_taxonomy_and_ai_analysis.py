"""add taxonomy and ai analysis

Revision ID: 2f8b2f8d8a10
Revises: f9663193e169
Create Date: 2026-03-08 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2f8b2f8d8a10"
down_revision: Union[str, Sequence[str], None] = "f9663193e169"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("photos", sa.Column("views", sa.Integer(), nullable=True, server_default="0"))

    op.create_table(
        "taxonomy_facets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("selection_mode", sa.String(length=20), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_taxonomy_facets_key"), "taxonomy_facets", ["key"], unique=True)

    op.create_table(
        "taxonomy_nodes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("facet_id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["facet_id"], ["taxonomy_facets.id"]),
        sa.ForeignKeyConstraint(["parent_id"], ["taxonomy_nodes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("facet_id", "key", name="uq_taxonomy_node_facet_key"),
    )
    op.create_index(op.f("ix_taxonomy_nodes_facet_id"), "taxonomy_nodes", ["facet_id"], unique=False)
    op.create_index(op.f("ix_taxonomy_nodes_parent_id"), "taxonomy_nodes", ["parent_id"], unique=False)

    op.create_table(
        "taxonomy_aliases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(length=150), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["node_id"], ["taxonomy_nodes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_taxonomy_aliases_alias"), "taxonomy_aliases", ["alias"], unique=True)
    op.create_index(op.f("ix_taxonomy_aliases_node_id"), "taxonomy_aliases", ["node_id"], unique=False)

    op.create_table(
        "photo_classifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("photo_id", sa.String(length=36), nullable=False),
        sa.Column("facet_id", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["facet_id"], ["taxonomy_facets.id"]),
        sa.ForeignKeyConstraint(["node_id"], ["taxonomy_nodes.id"]),
        sa.ForeignKeyConstraint(["photo_id"], ["photos.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("photo_id", "facet_id", name="uq_photo_classification_photo_facet"),
    )
    op.create_index(op.f("ix_photo_classifications_photo_id"), "photo_classifications", ["photo_id"], unique=False)
    op.create_index(op.f("ix_photo_classifications_facet_id"), "photo_classifications", ["facet_id"], unique=False)
    op.create_index(op.f("ix_photo_classifications_node_id"), "photo_classifications", ["node_id"], unique=False)

    op.create_table(
        "ai_analysis_tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("photo_id", sa.String(length=36), nullable=False),
        sa.Column("requested_by_id", sa.String(length=36), nullable=True),
        sa.Column("reviewed_by_id", sa.String(length=36), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model_id", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("prompt_version", sa.String(length=20), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["photo_id"], ["photos.id"]),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_analysis_tasks_photo_id"), "ai_analysis_tasks", ["photo_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_analysis_tasks_photo_id"), table_name="ai_analysis_tasks")
    op.drop_table("ai_analysis_tasks")

    op.drop_index(op.f("ix_photo_classifications_node_id"), table_name="photo_classifications")
    op.drop_index(op.f("ix_photo_classifications_facet_id"), table_name="photo_classifications")
    op.drop_index(op.f("ix_photo_classifications_photo_id"), table_name="photo_classifications")
    op.drop_table("photo_classifications")

    op.drop_index(op.f("ix_taxonomy_aliases_node_id"), table_name="taxonomy_aliases")
    op.drop_index(op.f("ix_taxonomy_aliases_alias"), table_name="taxonomy_aliases")
    op.drop_table("taxonomy_aliases")

    op.drop_index(op.f("ix_taxonomy_nodes_parent_id"), table_name="taxonomy_nodes")
    op.drop_index(op.f("ix_taxonomy_nodes_facet_id"), table_name="taxonomy_nodes")
    op.drop_table("taxonomy_nodes")

    op.drop_index(op.f("ix_taxonomy_facets_key"), table_name="taxonomy_facets")
    op.drop_table("taxonomy_facets")

    op.drop_column("photos", "views")
