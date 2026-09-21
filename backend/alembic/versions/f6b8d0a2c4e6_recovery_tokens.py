"""Persistent one-use recovery tokens."""
import sqlalchemy as sa

from alembic import op

revision = "f6b8d0a2c4e6"
down_revision = "e5a7c9b1d3f4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("recovery_tokens",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purpose", sa.String(24), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_recovery_tokens_user_id", "recovery_tokens", ["user_id"])


def downgrade():
    op.drop_table("recovery_tokens")
