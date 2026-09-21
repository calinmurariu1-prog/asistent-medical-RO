"""Single-use MFA recovery codes."""
import sqlalchemy as sa

from alembic import op

revision = "c5e7a9b1d3f6"
down_revision = "b4d6f8a0c2e3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("mfa_recovery_codes",
        sa.Column("code_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_mfa_recovery_codes_user_id", "mfa_recovery_codes", ["user_id"])


def downgrade():
    op.drop_table("mfa_recovery_codes")
