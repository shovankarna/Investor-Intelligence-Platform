"""Initial database schema with pgvector, documents, financial_metrics, chunks, and chat_logs.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-08 21:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 1. documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('company', sa.String(), nullable=False),
        sa.Column('fiscal_year', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('storage_path', sa.String(), nullable=True),
        sa.Column('content_hash', sa.String(), nullable=False),
        sa.Column('upload_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_documents_company'), 'documents', ['company'], unique=False)
    op.create_index(op.f('ix_documents_content_hash'), 'documents', ['content_hash'], unique=True)
    op.create_index(op.f('ix_documents_fiscal_year'), 'documents', ['fiscal_year'], unique=False)

    # 2. financial_metrics table
    op.create_table(
        'financial_metrics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('metric_name', sa.String(), nullable=False),
        sa.Column('value', sa.Numeric(), nullable=False),
        sa.Column('unit', sa.String(), nullable=False),
        sa.Column('currency', sa.String(), nullable=False),
        sa.Column('source_page', sa.Integer(), nullable=False),
        sa.Column('source_chunk_id', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', 'metric_name', name='uq_document_metric'),
    )
    op.create_index(op.f('ix_financial_metrics_document_id'), 'financial_metrics', ['document_id'], unique=False)
    op.create_index(op.f('ix_financial_metrics_metric_name'), 'financial_metrics', ['metric_name'], unique=False)

    # 3. chunks table
    op.create_table(
        'chunks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('section_path', sa.Text(), nullable=False),
        sa.Column('element_type', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tsv_content', postgresql.TSVECTOR(), nullable=True),
        sa.Column('embedding', Vector(384), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_chunks_document_id'), 'chunks', ['document_id'], unique=False)

    # 4. chat_logs table
    op.create_table(
        'chat_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('query_type', sa.String(), nullable=True),
        sa.Column('retrieved_chunk_ids', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('chat_logs')
    op.drop_table('chunks')
    op.drop_table('financial_metrics')
    op.drop_table('documents')
