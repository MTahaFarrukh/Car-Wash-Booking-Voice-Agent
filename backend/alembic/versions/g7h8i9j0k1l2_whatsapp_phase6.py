"""Phase 6 WhatsApp support: booking source and idempotency."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g7h8i9j0k1l2"
down_revision: Union[str, None] = "f8a2b1c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE booking_source ADD VALUE IF NOT EXISTS 'whatsapp'")

    op.create_table(
        "whatsapp_processed_messages",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", sa.String(length=128), nullable=False),
        sa.Column("sender_id", sa.String(length=128), nullable=False),
        sa.Column("response_message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_whatsapp_processed_messages_message_id"),
        "whatsapp_processed_messages",
        ["message_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_whatsapp_processed_messages_sender_id"),
        "whatsapp_processed_messages",
        ["sender_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_whatsapp_processed_messages_sender_id"), table_name="whatsapp_processed_messages")
    op.drop_index(op.f("ix_whatsapp_processed_messages_message_id"), table_name="whatsapp_processed_messages")
    op.drop_table("whatsapp_processed_messages")
    # PostgreSQL does not support removing enum values safely; leave booking_source as-is.
