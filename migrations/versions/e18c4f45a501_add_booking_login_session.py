"""add login session identifier to immutable tap bookings

Revision ID: e18c4f45a501
Revises: d75a2190b4ce
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e18c4f45a501"
down_revision: str | Sequence[str] | None = "d75a2190b4ce"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _drop_immutability_triggers() -> None:
    op.execute("DROP TRIGGER IF EXISTS tap_bookings_prevent_delete")
    op.execute("DROP TRIGGER IF EXISTS tap_bookings_prevent_update")


def _create_immutability_triggers() -> None:
    op.execute(
        """
        CREATE TRIGGER tap_bookings_prevent_update
        BEFORE UPDATE ON tap_bookings
        BEGIN
            SELECT RAISE(ABORT, 'completed tap bookings are immutable');
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER tap_bookings_prevent_delete
        BEFORE DELETE ON tap_bookings
        BEGIN
            SELECT RAISE(ABORT, 'completed tap bookings are immutable');
        END
        """
    )


def upgrade() -> None:
    _drop_immutability_triggers()
    op.add_column(
        "tap_bookings",
        sa.Column("login_session_id", sa.String(length=64), nullable=True),
    )
    op.execute(
        "UPDATE tap_bookings "
        "SET login_session_id = 'legacy-' || CAST(id AS TEXT) "
        "WHERE login_session_id IS NULL"
    )
    with op.batch_alter_table("tap_bookings", recreate="always") as batch_op:
        batch_op.alter_column(
            "login_session_id",
            existing_type=sa.String(length=64),
            nullable=False,
        )
        batch_op.create_index(
            "ix_tap_bookings_login_session",
            ["login_session_id"],
            unique=False,
        )
    _create_immutability_triggers()


def downgrade() -> None:
    _drop_immutability_triggers()
    with op.batch_alter_table("tap_bookings", recreate="always") as batch_op:
        batch_op.drop_index("ix_tap_bookings_login_session")
        batch_op.drop_column("login_session_id")
    _create_immutability_triggers()
