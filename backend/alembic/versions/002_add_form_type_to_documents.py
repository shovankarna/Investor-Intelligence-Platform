"""Add form_type and fiscal_year_end columns to documents table.

Revision ID: 002_add_form_type
Revises: 001_initial_schema
Create Date: 2026-10-08 21:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_add_form_type'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'documents',
        sa.Column('form_type', sa.String(length=20), nullable=False, server_default='10-K')
    )
    op.add_column(
        'documents',
        sa.Column('fiscal_year_end', sa.String(length=100), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('documents', 'fiscal_year_end')
    op.drop_column('documents', 'form_type')
