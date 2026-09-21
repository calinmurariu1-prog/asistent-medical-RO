"""Explicit daily medication reminder schedules."""
import sqlalchemy as sa

from alembic import op

revision = "b4d6f8a0c2e3"
down_revision = "a3c5e7f9b1d2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "medication_reminders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("medication_id", sa.Integer(),
                  sa.ForeignKey("medications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("local_time", sa.String(5), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("next_occurrence", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.UniqueConstraint("medication_id", "local_time", "timezone",
                            name="uq_medication_reminder_time"),
    )
    op.create_index("ix_medication_reminders_medication_id", "medication_reminders", ["medication_id"])
    op.create_index("ix_medication_reminders_next_occurrence", "medication_reminders",
                    ["next_occurrence"])


def downgrade():
    op.drop_table("medication_reminders")
