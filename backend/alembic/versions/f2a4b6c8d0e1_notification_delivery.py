"""Durable notification delivery leases and retries."""
import sqlalchemy as sa

from alembic import op

revision = "f2a4b6c8d0e1"
down_revision = "e1f3a5b7c9d0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("notifications", sa.Column("delivery_token", sa.String(36), nullable=True))
    op.add_column("notifications", sa.Column("delivery_until", sa.DateTime(timezone=True)))
    op.add_column("notifications", sa.Column("next_delivery_at", sa.DateTime(timezone=True)))
    op.add_column("notifications", sa.Column("delivery_attempts", sa.Integer(),
                                            nullable=False, server_default="0"))


def downgrade():
    for name in ("delivery_attempts", "next_delivery_at", "delivery_until", "delivery_token"):
        op.drop_column("notifications", name)
