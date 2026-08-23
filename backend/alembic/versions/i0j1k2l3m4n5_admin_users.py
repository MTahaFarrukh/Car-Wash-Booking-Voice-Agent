"""Alembic migration: admin_users for Supabase Auth authorization (Phase 10A)."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "i0j1k2l3m4n5"
down_revision = "h9i0j1k2l3m4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("auth_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="ADMIN"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_admin_users_auth_user_id", "admin_users", ["auth_user_id"], unique=True)
    op.create_index("ix_admin_users_email", "admin_users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_admin_users_email", table_name="admin_users")
    op.drop_index("ix_admin_users_auth_user_id", table_name="admin_users")
    op.drop_table("admin_users")
