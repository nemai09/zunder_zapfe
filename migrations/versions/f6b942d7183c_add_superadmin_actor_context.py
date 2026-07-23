"""add superadmin audit actor and userless maintenance context

Revision ID: f6b942d7183c
Revises: e18c4f45a501
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f6b942d7183c"
down_revision: str | Sequence[str] | None = "e18c4f45a501"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_COMPLETION = sa.Enum(
    "target_reached",
    "user_abort",
    "released",
    "limit_reached",
    "fault",
    "shutdown",
    name="booking_completion",
    native_enum=False,
    create_constraint=True,
)
NEW_COMPLETION = sa.Enum(
    "target_reached",
    "user_abort",
    "released",
    "limit_reached",
    "fault",
    "shutdown",
    "card_removed",
    name="booking_completion",
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


def upgrade() -> None:
    op.add_column(
        "admin_audit_entries",
        sa.Column("actor_kind", sa.String(length=20), nullable=True),
    )
    op.execute("UPDATE admin_audit_entries SET actor_kind = 'user_admin'")
    with op.batch_alter_table("admin_audit_entries", recreate="always") as batch_op:
        batch_op.alter_column(
            "actor_kind",
            existing_type=sa.String(length=20),
            nullable=False,
        )
        batch_op.alter_column(
            "admin_user_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.create_check_constraint(
            "ck_admin_audit_entries_actor",
            "(actor_kind = 'user_admin' AND admin_user_id IS NOT NULL) OR "
            "(actor_kind = 'superadmin' AND admin_user_id IS NULL)",
        )

    _drop_immutability_triggers()
    with op.batch_alter_table("tap_bookings", recreate="always") as batch_op:
        batch_op.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.alter_column(
            "login_session_id",
            existing_type=sa.String(length=64),
            nullable=True,
        )
        batch_op.alter_column(
            "completion",
            existing_type=OLD_COMPLETION,
            type_=NEW_COMPLETION,
            nullable=False,
        )
        batch_op.create_check_constraint(
            "ck_tap_bookings_actor_context",
            "(user_id IS NOT NULL AND login_session_id IS NOT NULL) OR "
            "(user_id IS NULL AND login_session_id IS NULL "
            "AND kind = 'maintenance' AND chargeable = 0)",
        )
    _create_immutability_triggers()


def downgrade() -> None:
    connection = op.get_bind()
    userless_count = connection.scalar(
        sa.text("SELECT COUNT(*) FROM tap_bookings WHERE user_id IS NULL")
    )
    superadmin_audit_count = connection.scalar(
        sa.text("SELECT COUNT(*) FROM admin_audit_entries WHERE actor_kind = 'superadmin'")
    )
    card_removed_count = connection.scalar(
        sa.text("SELECT COUNT(*) FROM tap_bookings WHERE completion = 'card_removed'")
    )
    if userless_count or superadmin_audit_count or card_removed_count:
        raise RuntimeError(
            "Downgrade would discard Superadmin actor information or userless maintenance data"
        )

    _drop_immutability_triggers()
    with op.batch_alter_table("tap_bookings", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_tap_bookings_actor_context", type_="check")
        batch_op.alter_column(
            "completion",
            existing_type=NEW_COMPLETION,
            type_=OLD_COMPLETION,
            nullable=False,
        )
        batch_op.alter_column(
            "login_session_id",
            existing_type=sa.String(length=64),
            nullable=False,
        )
        batch_op.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
    _create_immutability_triggers()

    with op.batch_alter_table("admin_audit_entries", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_admin_audit_entries_actor", type_="check")
        batch_op.alter_column(
            "admin_user_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.drop_column("actor_kind")
