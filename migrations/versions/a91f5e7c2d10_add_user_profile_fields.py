"""add user profile fields

Revision ID: a91f5e7c2d10
Revises: 830d216e8ba1
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a91f5e7c2d10"
down_revision: str | Sequence[str] | None = "830d216e8ba1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("first_name", sa.String(length=80), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(length=80), nullable=True))
    op.add_column("users", sa.Column("note", sa.Text(), nullable=True))
    op.execute("UPDATE users SET first_name = display_name")
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "first_name",
            existing_type=sa.String(length=80),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("note")
        batch_op.drop_column("last_name")
        batch_op.drop_column("first_name")
