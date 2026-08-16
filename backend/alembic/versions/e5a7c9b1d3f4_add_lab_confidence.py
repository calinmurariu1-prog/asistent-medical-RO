"""add confidence to lab_results

Revision ID: e5a7c9b1d3f4
Revises: d4f6a8c0e2b3
Create Date: 2026-08-16 21:40:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'e5a7c9b1d3f4'
down_revision: str | None = 'd4f6a8c0e2b3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'lab_results',
        sa.Column(
            'confidence',
            sa.String(length=20),
            server_default='verified',
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('lab_results', 'confidence')
