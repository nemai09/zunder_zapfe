"""add web admin sessions

Revision ID: c4e9f72a1b06
Revises: a91f5e7c2d10
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c4e9f72a1b06"
down_revision: str | Sequence[str] | None = "a91f5e7c2d10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "web_admin_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idle_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("absolute_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        op.f("ix_web_admin_sessions_token_hash"),
        "web_admin_sessions",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_web_admin_sessions_user_id"),
        "web_admin_sessions",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_web_admin_sessions_user_id"), table_name="web_admin_sessions")
    op.drop_index(op.f("ix_web_admin_sessions_token_hash"), table_name="web_admin_sessions")
    op.drop_table("web_admin_sessions")
