"""allow multi taxonomy classifications

Revision ID: e7f8a9b0c1d2
Revises: d4e5f6a7b8c9
Create Date: 2026-06-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_photo_classification_photo_facet",
        "photo_classifications",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_photo_classification_photo_facet_node",
        "photo_classifications",
        ["photo_id", "facet_id", "node_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_photo_classification_photo_facet_node",
        "photo_classifications",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_photo_classification_photo_facet",
        "photo_classifications",
        ["photo_id", "facet_id"],
    )
