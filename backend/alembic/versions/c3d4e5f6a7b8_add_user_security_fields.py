"""Add user security and audit fields

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-04-30 00:00:00.000000

Adds security-related columns to users table:
  - last_login_at        (timestamp of last successful login)
  - login_count          (cumulative login counter)
  - failed_login_attempts (consecutive failed attempts for lockout)
  - locked_until         (account lockout expiry)
  - token_version        (incremented on password change to invalidate old tokens)
  - email_verified       (whether email has been confirmed)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    insp = inspect(conn)
    columns = [c["name"] for c in insp.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    if not _column_exists("users", "last_login_at"):
        op.add_column(
            "users",
            sa.Column(
                "last_login_at",
                sa.DateTime(),
                nullable=True,
                comment="最后登录时间",
            ),
        )

    if not _column_exists("users", "login_count"):
        op.add_column(
            "users",
            sa.Column(
                "login_count",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
                comment="累计登录次数",
            ),
        )

    if not _column_exists("users", "failed_login_attempts"):
        op.add_column(
            "users",
            sa.Column(
                "failed_login_attempts",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
                comment="连续登录失败次数",
            ),
        )

    if not _column_exists("users", "locked_until"):
        op.add_column(
            "users",
            sa.Column(
                "locked_until",
                sa.DateTime(),
                nullable=True,
                comment="账号锁定截止时间",
            ),
        )

    if not _column_exists("users", "token_version"):
        op.add_column(
            "users",
            sa.Column(
                "token_version",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("1"),
                comment="Token 版本号，改密码后递增使旧 Token 失效",
            ),
        )

    if not _column_exists("users", "email_verified"):
        op.add_column(
            "users",
            sa.Column(
                "email_verified",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
                comment="邮箱是否已验证",
            ),
        )


def downgrade() -> None:
    if _column_exists("users", "email_verified"):
        op.drop_column("users", "email_verified")

    if _column_exists("users", "token_version"):
        op.drop_column("users", "token_version")

    if _column_exists("users", "locked_until"):
        op.drop_column("users", "locked_until")

    if _column_exists("users", "failed_login_attempts"):
        op.drop_column("users", "failed_login_attempts")

    if _column_exists("users", "login_count"):
        op.drop_column("users", "login_count")

    if _column_exists("users", "last_login_at"):
        op.drop_column("users", "last_login_at")
