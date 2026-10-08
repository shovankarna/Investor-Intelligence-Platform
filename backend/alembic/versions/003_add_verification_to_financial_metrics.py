"""Add verified and low_confidence columns to financial_metrics table.

Revision ID: 003_add_verification
Revises: 002_add_form_type
Create Date: 2026-10-08 21:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003_add_verification'
down_revision: Union[str, None] = '002_add_form_type'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'financial_metrics',
        sa.Column('verified', sa.Boolean(), nullable=False, server_default=sa.text('true'))
    )
    op.add_column(
        'financial_metrics',
        sa.Column('low_confidence', sa.Boolean(), nullable=False, server_default=sa.text('false'))
    )


def downgrade() -> None:
    op.drop_column('financial_metrics', 'low_confidence')
    op.drop_column('financial_metrics', 'verified')
