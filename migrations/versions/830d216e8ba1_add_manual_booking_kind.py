"""add manual booking kind

Revision ID: 830d216e8ba1
Revises: 665c808f8308
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "830d216e8ba1"
down_revision: str | Sequence[str] | None = "665c808f8308"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_KINDS = ("portion", "top_up", "maintenance", "free_admin")
NEW_KINDS = ("manual", *OLD_KINDS)


def _booking_kind(values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(
        *values,
        name="booking_kind",
        native_enum=False,
        create_constraint=True,
    )


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


def _replace_kind_enum(old_values: tuple[str, ...], new_values: tuple[str, ...]) -> None:
    _drop_immutability_triggers()
    with op.batch_alter_table("tap_bookings", recreate="always") as batch_op:
        batch_op.alter_column(
            "kind",
            existing_type=_booking_kind(old_values),
            type_=_booking_kind(new_values),
            existing_nullable=False,
        )
    _create_immutability_triggers()


def upgrade() -> None:
    _replace_kind_enum(OLD_KINDS, NEW_KINDS)


def downgrade() -> None:
    # SQLite rejects the table copy if manual bookings exist. This deliberately
    # prevents a downgrade from silently deleting immutable accounting data.
    _replace_kind_enum(NEW_KINDS, OLD_KINDS)
