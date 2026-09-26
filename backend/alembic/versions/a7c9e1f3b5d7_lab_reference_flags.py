"""Remove unsupported critical thresholds and identify unevaluable results."""
import sqlalchemy as sa

from alembic import op

revision = "a7c9e1f3b5d7"
down_revision = "f6b8d0a2c4e6"
branch_labels = None
depends_on = None


def upgrade():
    # Non-native enums store member names, in the existing VARCHAR(13) column.
    op.execute(sa.text("""
        UPDATE lab_results SET flag = CASE
            WHEN value IS NULL OR (ref_low IS NULL AND ref_high IS NULL)
                OR ref_low > ref_high THEN 'UNKNOWN'
            WHEN value > ref_high THEN 'HIGH'
            WHEN value < ref_low THEN 'LOW'
            ELSE 'NORMAL' END,
            ai_explanation = NULL
    """))


def downgrade():
    # The unsupported critical inference is deliberately not reconstructed.
    op.execute(sa.text("UPDATE lab_results SET flag = 'NORMAL' WHERE flag = 'UNKNOWN'"))
