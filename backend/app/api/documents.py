"""
Document API Endpoints.

WHY WE KEEP ROUTE HANDLERS THIN (AGENT.md §4):
Route handlers should ONLY handle HTTP concerns:
1. Parsing request parameters and multipart form-data.
2. Injecting database session dependencies.
3. Delegating the work to the service layer (`DocumentService`).
4. Returning formatted response schemas.

Business logic (hashing, file persistence, deduplication) belongs in `services/`.
"""

from typing import List
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Document
from app.db.session import get_db_session
from app.models.document import DocumentCreate, DocumentResponse, DocumentUploadResult
from app.services.document_service import DocumentService

# Create router instance for document resources
router = APIRouter()


@router.post(
    "/upload",
    response_model=DocumentUploadResult,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and register a financial report PDF",
)
async def upload_document(
    company: str = Form(..., description="Company name (e.g., Apple, Microsoft)"),
    fiscal_year: int = Form(..., description="Filing fiscal year (e.g., 2024)"),
    file: UploadFile = File(..., description="Financial report PDF file"),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentUploadResult:
    """
    Accepts a 10-K / Annual Report PDF with user tagging (ADR-3),
    computes its SHA-256 hash for idempotency, and records it in the database.
    """
    # 1. Package metadata into Pydantic schema for validation
    metadata = DocumentCreate(company=company, fiscal_year=fiscal_year)

    # 2. Delegate to DocumentService for hashing and database persistence
    doc, is_duplicate = await DocumentService.process_and_save_document(
        session=session,
        file=file,
        metadata=metadata,
    )

    # 3. Create context-aware status message for the user
    message = (
        f"Document '{doc.filename}' was already processed previously (idempotent skip)."
        if is_duplicate
        else f"Document '{doc.filename}' uploaded successfully for {doc.company} (FY{doc.fiscal_year})."
    )

    # 4. Return serialized response
    return DocumentUploadResult(
        document=DocumentResponse.model_validate(doc),
        is_duplicate=is_duplicate,
        message=message,
    )


@router.get(
    "/",
    response_model=List[DocumentResponse],
    summary="List all uploaded financial filings",
)
async def list_documents(
    session: AsyncSession = Depends(get_db_session),
) -> List[DocumentResponse]:
    """
    Returns all ingested financial filings stored in PostgreSQL,
    ordered by upload timestamp (newest first).
    """
    query = select(Document).order_by(Document.upload_date.desc())
    result = await session.execute(query)
    docs = result.scalars().all()

    return [DocumentResponse.model_validate(doc) for doc in docs]
