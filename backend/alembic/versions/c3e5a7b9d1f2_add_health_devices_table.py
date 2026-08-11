"""add health_devices table

Revision ID: c3e5a7b9d1f2
Revises: b2d4f6a8c0e1
Create Date: 2026-08-07 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'c3e5a7b9d1f2'
down_revision: str | None = 'b2d4f6a8c0e1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'health_devices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('model', sa.String(length=120), nullable=True),
        sa.Column('vendor', sa.String(length=60), nullable=True),
        sa.Column('metrics', sa.Text(), nullable=True),
        sa.Column('sample_count', sa.Integer(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('patient_id', 'source', 'name', name='uq_health_device_natural_key'),
    )
    op.create_index(op.f('ix_health_devices_patient_id'), 'health_devices', ['patient_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_health_devices_patient_id'), table_name='health_devices')
    op.drop_table('health_devices')
