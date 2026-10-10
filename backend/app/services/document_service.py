"""
Document Ingestion & Full Pipeline Service.

CONNECTING THE DUAL-PATH INGESTION FLOW (PROJECT.md §4 & §5):
1. Verifies PDF format and computes SHA-256 content hash for idempotency.
2. If new:
   a. Parses layout tree using Docling into separate table and prose streams.
   b. Extracts 13 raw financial line items with page citations via OpenRouter (using US GAAP or IFRS alias maps).
   c. Chunks narrative text with contextual headers and computes 384-d vector embeddings.
   d. Atomically persists Document, FinancialMetrics, and Chunks to PostgreSQL.
"""

import hashlib
import os
import tempfile

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, FinancialMetric
from app.models.document import DocumentCreate
from app.rag.chunker import DocumentChunker
from app.rag.embedder import EmbeddingService
from app.services.metric_extractor import MetricExtractionService
from app.services.parser_service import ParserService


class DocumentService:
    """Service handling PDF verification, parsing, metric extraction, and vectorization."""

    @staticmethod
    def calculate_sha256(file_bytes: bytes) -> str:
        """Computes SHA-256 cryptographic hash of the PDF binary data."""
        hasher = hashlib.sha256()
        hasher.update(file_bytes)
        return hasher.hexdigest()

    @classmethod
    async def get_by_hash(cls, session: AsyncSession, content_hash: str) -> Document | None:
        """Queries the database for an existing document matching the SHA-256 hash."""
        query = select(Document).where(Document.content_hash == content_hash)
        result = await session.execute(query)
        return result.scalars().first()

    @classmethod
    async def get_by_id(cls, session: AsyncSession, document_id: int) -> Document | None:
        """Queries a document by its database primary key ID."""
        query = select(Document).where(Document.id == document_id)
        result = await session.execute(query)
        return result.scalars().first()

    @classmethod
    async def process_and_save_document(
        cls,
        session: AsyncSession,
        file: UploadFile,
        metadata: DocumentCreate,
        file_bytes: bytes | None = None,
    ) -> tuple[Document, bool]:
        """
        Runs the full ingestion pipeline:
        Deduplication -> Layout Parsing -> LLM Metric Extraction -> Chunking -> Embeddings -> DB Storage.
        """
        # Step 1: Format validation
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file format. Only PDF files are supported.",
            )

        # Step 2: Read binary content if not already provided
        if file_bytes is None:
            file_bytes = await file.read()

        if len(file_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded PDF file is empty.",
            )

        company_clean = metadata.company.strip()
        form_type = metadata.form_type or "10-K"
        print(f"\n{'=' * 80}", flush=True)
        print(f"🚀 [INGESTION PIPELINE] Starting for '{file.filename}'", flush=True)
        print(f"   🏢 Company: {company_clean} | 📅 Fiscal Year: {metadata.fiscal_year} | 📋 Form: {form_type}", flush=True)
        print(f"   📦 PDF File Size: {len(file_bytes) / 1024:.1f} KB", flush=True)
        print(f"{'=' * 80}", flush=True)

        # Step 3: Compute content hash for idempotency (ADR-4)
        content_hash = cls.calculate_sha256(file_bytes)
        print(f"📍 [Stage 1/5] SHA-256 Hash Computed: {content_hash[:16]}...", flush=True)

        # Step 4: Idempotent check
        existing_doc = await cls.get_by_hash(session, content_hash)
        if existing_doc:
            print(f"ℹ️ [Stage 1/5] Idempotency Match: Document already exists (ID: {existing_doc.id}). Skipping re-parsing.", flush=True)
            return existing_doc, True

        # Step 5: Save parent Document record
        new_doc = Document(
            company=company_clean,
            fiscal_year=metadata.fiscal_year,
            form_type=form_type,
            fiscal_year_end=metadata.fiscal_year_end,
            filename=file.filename,
            content_hash=content_hash,
            storage_path=f"filings/{company_clean.lower()}_{metadata.fiscal_year}_{content_hash[:8]}.pdf",
        )
        session.add(new_doc)
        await session.flush()  # Generates new_doc.id
        print(f"📍 [Stage 2/5] Created Document Record in PostgreSQL (ID: {new_doc.id})", flush=True)

        # Step 6: Layout-aware parsing with Docling using a temporary file
        print(f"📍 [Stage 3/5] Parsing PDF Layout with Docling (Fast Native Text + Table Extraction)...", flush=True)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(file_bytes)
            tmp_path = tmp_file.name

        try:
            parsed_result = ParserService.parse_pdf(
                file_path_or_bytes=tmp_path,
                document_id=new_doc.id,
                company=new_doc.company,
                fiscal_year=new_doc.fiscal_year,
            )
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        print(f"   ✅ Docling Parse Finished: {parsed_result.total_pages} Pages | {len(parsed_result.tables)} Tables | {len(parsed_result.prose_blocks)} Prose Blocks", flush=True)

        # Step 7: Path A - Extract raw financial metrics from tables via OpenRouter
        print(f"📍 [Stage 4/5] Extracting 13 Financial Metrics with LLM & Deterministic Verification...", flush=True)
        extracted_metrics = []
        if parsed_result.tables:
            try:
                extracted_metrics = await MetricExtractionService.extract_all_metrics(
                    parsed_result.tables,
                    form_type=new_doc.form_type,
                    fiscal_year=new_doc.fiscal_year,
                )
            except Exception as exc:
                print(f"⚠️ [Stage 4/5] [WARN] Metric extraction failed gracefully: {exc}", flush=True)
                extracted_metrics = []

            for m in extracted_metrics:
                metric_row = FinancialMetric(
                    document_id=new_doc.id,
                    metric_name=m.metric_name,
                    value=m.value,
                    unit=m.unit,
                    currency=m.currency,
                    source_page=m.source_page,
                    source_chunk_id=m.source_chunk_id,
                    verified=m.verified,
                    low_confidence=m.low_confidence,
                )
                session.add(metric_row)

            print(f"   ✅ Saved {len(extracted_metrics)} Extracted Metrics to PostgreSQL (verified & grounded).", flush=True)
        else:
            print(f"   ⚠️ No tables detected in PDF for metric extraction.", flush=True)

        # Step 8: Path B - Structure-aware chunking & local vector embedding
        print(f"📍 [Stage 5/5] Generating Vector Chunks & Embeddings (BAAI/bge-small-en-v1.5)...", flush=True)
        chunks = DocumentChunker.chunk_document(parsed_result)
        if chunks:
            embedded_chunks = EmbeddingService.embed_chunks(chunks)
            for ch in embedded_chunks:
                session.add(ch)
            print(f"   ✅ Vectorized & Saved {len(embedded_chunks)} Chunks into PostgreSQL pgvector table.", flush=True)

        # Step 9: Commit full transaction
        await session.commit()
        await session.refresh(new_doc)

        print(f"\n🎉 [INGESTION SUCCESS] Filing ID {new_doc.id} ('{new_doc.filename}') ready for Dashboard & RAG Assistant!", flush=True)
        print(f"{'=' * 80}\n", flush=True)

        return new_doc, False
