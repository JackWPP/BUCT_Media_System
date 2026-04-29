"""Add missing tables and columns

Revision ID: a1b2c3d4e5f6
Revises: 7b2d4e1f9c30
Create Date: 2026-04-29 00:00:00.000000

This migration catches up Alembic history with the current SQLAlchemy models.
It adds 5 tables and 3 columns that were missing from previous migrations.

Tables added:
  - system_configs     (key-value runtime settings)
  - audit_logs         (operation audit trail)
  - notifications      (in-app user notifications)
  - favorites          (user photo favorites)
  - resource_permissions (fine-grained resource access control)

Columns added to users:
  - student_id         (primary identity, non-null after backfill)
  - auth_provider      (local / university_sso)
  - sso_id             (SSO system identifier)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "7b2d4e1f9c30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    insp = inspect(conn)
    columns = [c["name"] for c in insp.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # ── users: add missing columns ──
    if not _column_exists("users", "student_id"):
        op.add_column(
            "users",
            sa.Column(
                "student_id",
                sa.String(length=20),
                nullable=True,  # Non-null after backfill
                comment="学号/工号，核心身份标识",
            ),
        )
        op.create_index(op.f("ix_users_student_id"), "users", ["student_id"], unique=True)

    if not _column_exists("users", "auth_provider"):
        op.add_column(
            "users",
            sa.Column(
                "auth_provider",
                sa.String(length=50),
                nullable=False,
                server_default=sa.text("'local'"),
                comment="认证方式：local=本地密码, university_sso=学校统一认证",
            ),
        )

    if not _column_exists("users", "sso_id"):
        op.add_column(
            "users",
            sa.Column(
                "sso_id",
                sa.String(length=255),
                nullable=True,
                comment="SSO 系统中的用户唯一标识",
            ),
        )
        op.create_index(op.f("ix_users_sso_id"), "users", ["sso_id"], unique=True)

    # ── users: fix nullable mismatches from initial migration ──
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.alter_column("users", "email", nullable=True, existing_type=sa.String(255))
        op.alter_column("users", "hashed_password", nullable=True, existing_type=sa.String(255))

    # ── system_configs ──
    op.create_table(
        "system_configs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_system_configs_key"), "system_configs", ["key"], unique=True)

    # ── audit_logs ──
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=True),
        sa.Column("resource_id", sa.String(length=36), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
    op.create_index(op.f("ix_audit_logs_resource_type"), "audit_logs", ["resource_type"], unique=False)
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"], unique=False)
    op.create_index("ix_audit_logs_created_action", "audit_logs", ["created_at", "action"])

    # ── notifications ──
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("related_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"], unique=False)
    op.create_index(op.f("ix_notifications_type"), "notifications", ["type"], unique=False)
    op.create_index(op.f("ix_notifications_created_at"), "notifications", ["created_at"], unique=False)
    op.create_index("ix_notifications_user_unread", "notifications", ["user_id", "is_read"])

    # ── favorites ──
    op.create_table(
        "favorites",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("photo_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["photo_id"], ["photos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "photo_id", name="uq_user_photo_favorite"),
    )
    op.create_index(op.f("ix_favorites_user_id"), "favorites", ["user_id"], unique=False)
    op.create_index(op.f("ix_favorites_photo_id"), "favorites", ["photo_id"], unique=False)

    # ── resource_permissions ──
    op.create_table(
        "resource_permissions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column(
            "resource_type",
            sa.Enum("category", "photo", "tag", name="resourcetype"),
            nullable=False,
        ),
        sa.Column("resource_key", sa.String(length=100), nullable=False),
        sa.Column(
            "permission_type",
            sa.Enum("view", "download", "upload", name="permissiontype"),
            nullable=False,
        ),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_resource_permissions_user_id"), "resource_permissions", ["user_id"], unique=False)
    op.create_index(op.f("ix_resource_permissions_resource_key"), "resource_permissions", ["resource_key"], unique=False)


def downgrade() -> None:
    # ── resource_permissions ──
    op.drop_index(op.f("ix_resource_permissions_resource_key"), table_name="resource_permissions")
    op.drop_index(op.f("ix_resource_permissions_user_id"), table_name="resource_permissions")
    op.drop_table("resource_permissions")
    op.execute("DROP TYPE IF EXISTS permissiontype")
    op.execute("DROP TYPE IF EXISTS resourcetype")

    # ── favorites ──
    op.drop_index(op.f("ix_favorites_photo_id"), table_name="favorites")
    op.drop_index(op.f("ix_favorites_user_id"), table_name="favorites")
    op.drop_table("favorites")

    # ── notifications ──
    op.drop_index("ix_notifications_user_unread", table_name="notifications")
    op.drop_index(op.f("ix_notifications_created_at"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_type"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_user_id"), table_name="notifications")
    op.drop_table("notifications")

    # ── audit_logs ──
    op.drop_index("ix_audit_logs_created_action", table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_resource_type"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_user_id"), table_name="audit_logs")
    op.drop_table("audit_logs")

    # ── system_configs ──
    op.drop_index(op.f("ix_system_configs_key"), table_name="system_configs")
    op.drop_table("system_configs")

    # ── users: revert added columns ──
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.alter_column("users", "hashed_password", nullable=False, existing_type=sa.String(255))
        op.alter_column("users", "email", nullable=False, existing_type=sa.String(255))

    # Note: auth_provider and student_id column removal is intentionally
    # omitted from downgrade — dropping NOT NULL columns is destructive
    # and would lose data on existing databases. These are additive changes.
