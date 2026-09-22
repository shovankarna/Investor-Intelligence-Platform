"""SQLAlchemy database models strictly adhering to PROJECT.md §7 and AGENT.md §1."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative database models."""

    pass


class Document(Base):
    """Stores uploaded financial filing metadata."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company: Mapped[str] = mapped_column(String, nullable=False, index=True)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    storage_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    content_hash: Mapped[str] = mapped_column(
        String, nullable=False, unique=True, index=True
    )  # SHA-256 for idempotency
    upload_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    metrics: Mapped[List["FinancialMetric"]] = relationship(
        "FinancialMetric",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    chunks: Mapped[List["Chunk"]] = relationship(
        "Chunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class FinancialMetric(Base):
    """Stores extracted quantitative metrics with strict provenance metadata."""

    __tablename__ = "financial_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_name: Mapped[str] = mapped_column(
        String, nullable=False, index=True
    )  # e.g., 'total_revenue', 'net_income'
    value: Mapped[Decimal] = mapped_column(
        Numeric, nullable=False
    )  # NUMERIC/Decimal only, never float (AGENT.md §1 Rule 6)
    unit: Mapped[str] = mapped_column(
        String, nullable=False
    )  # e.g., 'USD_millions', 'USD_thousands'
    currency: Mapped[str] = mapped_column(String, nullable=False, default="USD")
    source_page: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # Strict non-nullable provenance (AGENT.md §1 Rule 2)
    source_chunk_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint("document_id", "metric_name", name="uq_document_metric"),
    )

    # Relationship
    document: Mapped["Document"] = relationship("Document", back_populates="metrics")


class Chunk(Base):
    """Stores parsed document elements with embeddings and full-text vectors."""

    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(
        String, primary_key=True
    )  # e.g., '{doc_id}_p{page}_c{seq}'
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # Strict non-nullable provenance
    section_path: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # e.g., 'Part I > Item 1. Business'
    element_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # 'prose' or 'table'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tsv_content: Mapped[Optional[str]] = mapped_column(
        TSVECTOR, nullable=True
    )  # Full-text search vector
    embedding: Mapped[Optional[List[float]]] = mapped_column(
        Vector(384), nullable=True
    )  # BAAI/bge-small-en-v1.5 (384-d)

    # Relationship
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")


class ChatLog(Base):
    """Audit log for questions, answers, and retrieval provenance."""

    __tablename__ = "chat_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    query_type: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # 'STRUCTURED', 'NARRATIVE', 'HYBRID'
    retrieved_chunk_ids: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
