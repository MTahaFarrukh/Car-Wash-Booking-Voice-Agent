"""Alembic migration: add provider column to call_logs (Phase 8.1)."""

from alembic import op
import sqlalchemy as sa

revision = "h9i0j1k2l3m4"
down_revision = "g7h8i9j0k1l2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "call_logs",
        sa.Column("provider", sa.String(length=32), nullable=True),
    )
    op.create_index("ix_call_logs_provider", "call_logs", ["provider"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_call_logs_provider", table_name="call_logs")
    op.drop_column("call_logs", "provider")
