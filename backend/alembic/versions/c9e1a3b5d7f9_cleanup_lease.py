"""Prevent simultaneous cleanup attempts and recover abandoned work."""
import sqlalchemy as sa

from alembic import op

revision = "c9e1a3b5d7f9"
down_revision = "b8d0f2a4c6e8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("storage_deletions", sa.Column("claimed_until", sa.DateTime(timezone=True)))


def downgrade():
    op.drop_column("storage_deletions", "claimed_until")
