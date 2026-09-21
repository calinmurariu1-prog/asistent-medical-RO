"""Durable encrypted storage cleanup queue."""
import sqlalchemy as sa

from alembic import op

revision = "b8d0f2a4c6e8"
down_revision = "a7c9e1f3b5d7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("storage_deletions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("encrypted_key", sa.Text(), nullable=False),
        sa.Column("backend", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT COUNT(*) FROM storage_deletions")):
        raise RuntimeError("Process pending storage deletions before downgrading.")
    op.drop_table("storage_deletions")
