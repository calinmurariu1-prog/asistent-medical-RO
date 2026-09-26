"""Recover abandoned document processing and fence superseded workers."""
import sqlalchemy as sa

from alembic import op

revision = "d0f2a4b6c8e0"
down_revision = "c9e1a3b5d7f9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("documents", sa.Column("processing_token", sa.String(36)))
    op.add_column("documents", sa.Column("processing_until", sa.DateTime(timezone=True)))


def downgrade():
    op.drop_column("documents", "processing_until")
    op.drop_column("documents", "processing_token")
