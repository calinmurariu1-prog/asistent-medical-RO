"""Unconfirmed extracted numbers must not produce reference classifications."""
from alembic import op

revision = "e1f3a5b7c9d0"
down_revision = "d0f2a4b6c8e0"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE lab_results SET flag = 'UNKNOWN' WHERE confidence = 'unverified'")
    op.execute("UPDATE lab_results SET ai_explanation = NULL")


def downgrade():
    # No safe reconstruction of prior cached interpretations or classifications.
    pass
