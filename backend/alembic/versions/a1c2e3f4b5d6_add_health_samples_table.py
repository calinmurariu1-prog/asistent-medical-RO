"""add health_samples table

Revision ID: a1c2e3f4b5d6
Revises: 9fb6b0dbbec0
Create Date: 2026-08-07 10:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'a1c2e3f4b5d6'
down_revision: str | None = '9fb6b0dbbec0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'health_samples',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('metric_type', sa.String(length=30), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(length=20), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('patient_id', 'source', 'metric_type', 'recorded_at', name='uq_health_sample_natural_key'),
    )
    op.create_index(op.f('ix_health_samples_patient_id'), 'health_samples', ['patient_id'], unique=False)
    op.create_index('ix_health_samples_patient_metric', 'health_samples', ['patient_id', 'metric_type'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_health_samples_patient_metric', table_name='health_samples')
    op.drop_index(op.f('ix_health_samples_patient_id'), table_name='health_samples')
    op.drop_table('health_samples')
