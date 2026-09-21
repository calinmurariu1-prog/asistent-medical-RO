"""Invalidate legacy uncited explanations; original results remain unchanged."""
from alembic import op

revision = "a3c5e7f9b1d2"
down_revision = "f2a4b6c8d0e1"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE lab_results SET ai_explanation = NULL WHERE ai_explanation IS NOT NULL")


def downgrade():
    # Generated cache is deliberately not reconstructed on downgrade.
    pass
