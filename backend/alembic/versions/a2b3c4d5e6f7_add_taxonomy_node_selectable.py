"""add taxonomy node selectable flag

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-06-07 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "taxonomy_nodes",
        sa.Column("is_selectable", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.alter_column("taxonomy_nodes", "is_selectable", server_default=None)


def downgrade() -> None:
    op.drop_column("taxonomy_nodes", "is_selectable")
