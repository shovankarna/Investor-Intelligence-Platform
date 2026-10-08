"""
Document API Endpoints.

WHY WE KEEP ROUTE HANDLERS THIN (AGENT.md §4):
Route handlers handle HTTP concerns:
1. Parsing request parameters and multipart form-data.
2. Invoking upload validation before ingestion.
3. Injecting database session dependencies.
4. Delegating the work to the service layer (`DocumentService`).
5. Returning formatted response schemas.
"""

import os
import tempfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document
from app.db.session import get_db_session
from app.models.document import DocumentCreate, DocumentResponse, DocumentUploadResult
from app.services.document_service import DocumentService
from app.services.upload_validator import validate_upload

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
    Accepts a 10-K / 10-Q / 20-F Annual Report PDF with user tagging (ADR-3),
    validates the text layer and form type (returning 422 if invalid),
    computes its SHA-256 hash for idempotency, and ingests it into the platform.
    """
    # 1. Basic format validation
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF files are supported.",
        )

    # 2. Read file content
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded PDF file is empty.",
        )

    # 3. Save temporarily and run pre-ingestion upload validation (Check 1: text layer, Check 2: form type, Check 3: fiscal year end)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(file_bytes)
        tmp_path = tmp_file.name

    try:
        val_result = validate_upload(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    # 4. Package validated metadata into Pydantic schema
    metadata = DocumentCreate(
        company=company,
        fiscal_year=fiscal_year,
        form_type=val_result.form_type,
        fiscal_year_end=val_result.fiscal_year_end,
    )

    # 5. Delegate to DocumentService for hashing, metric extraction, embedding, and persistence
    doc, is_duplicate = await DocumentService.process_and_save_document(
        session=session,
        file=file,
        metadata=metadata,
        file_bytes=file_bytes,
    )

    # 6. Create context-aware status message for the user
    message = (
        f"Document '{doc.filename}' ({doc.form_type}) was already processed previously (idempotent skip)."
        if is_duplicate
        else f"Document '{doc.filename}' ({doc.form_type}) uploaded successfully for {doc.company} (FY{doc.fiscal_year})."
    )

    # 7. Return serialized response
    return DocumentUploadResult(
        document=DocumentResponse.model_validate(doc),
        is_duplicate=is_duplicate,
        message=message,
    )


@router.get(
    "/",
    response_model=list[DocumentResponse],
    summary="List all uploaded financial filings",
)
async def list_documents(
    session: AsyncSession = Depends(get_db_session),
) -> list[DocumentResponse]:
    """
    Returns all ingested financial filings stored in PostgreSQL,
    ordered by upload timestamp (newest first).
    """
    query = select(Document).order_by(Document.upload_date.desc())
    result = await session.execute(query)
    docs = result.scalars().all()

    return [DocumentResponse.model_validate(doc) for doc in docs]
