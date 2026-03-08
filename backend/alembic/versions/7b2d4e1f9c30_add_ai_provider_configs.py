"""add ai provider configs

Revision ID: 7b2d4e1f9c30
Revises: 2f8b2f8d8a10
Create Date: 2026-03-08 23:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7b2d4e1f9c30"
down_revision: Union[str, Sequence[str], None] = "2f8b2f8d8a10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_provider_configs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider_type", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("model_id", sa.String(length=200), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("extra_headers_json", sa.JSON(), nullable=True),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("daily_budget", sa.Integer(), nullable=False),
        sa.Column("last_test_status", sa.String(length=20), nullable=True),
        sa.Column("last_test_message", sa.Text(), nullable=True),
        sa.Column("last_tested_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_provider_configs_provider_type"), "ai_provider_configs", ["provider_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_provider_configs_provider_type"), table_name="ai_provider_configs")
    op.drop_table("ai_provider_configs")
