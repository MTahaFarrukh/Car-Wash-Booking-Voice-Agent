"""Add admin_acknowledged_at on bookings for ops notification workflow."""

from alembic import op
import sqlalchemy as sa

revision = "j1k2l3m4n5o6"
down_revision = "i0j1k2l3m4n5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bookings",
        sa.Column("admin_acknowledged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_bookings_admin_acknowledged_at",
        "bookings",
        ["admin_acknowledged_at"],
    )
    # Existing rows are treated as already reviewed — only new bookings notify.
    op.execute(
        "UPDATE bookings SET admin_acknowledged_at = created_at WHERE admin_acknowledged_at IS NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_bookings_admin_acknowledged_at", table_name="bookings")
    op.drop_column("bookings", "admin_acknowledged_at")
