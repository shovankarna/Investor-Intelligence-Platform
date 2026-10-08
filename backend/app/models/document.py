"""
Pydantic Schemas for Document Ingestion & Responses.

WHY WE USE PYDANTIC SCHEMAS:
1. Data Validation: Ensures the incoming request has valid fields (e.g. valid fiscal year range).
2. Auto Documentation: FastAPI uses these schemas to generate Swagger interactive docs.
3. Serialization: Safely converts database ORM objects to JSON responses for the UI.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    """
    Schema for user-provided document metadata during upload.
    User tags the document with company name and fiscal year (ADR-3).
    """

    company: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Company name (e.g., Apple, Microsoft, Tesla)",
    )
    fiscal_year: int = Field(..., ge=1990, le=2100, description="Filing fiscal year (e.g., 2024)")
    form_type: str | None = Field(
        None, description="Detected or provided SEC form type (e.g., 10-K, 10-Q, 20-F)"
    )
    fiscal_year_end: str | None = Field(None, description="Extracted fiscal year end date string")


class DocumentResponse(BaseModel):
    """
    Schema returned to the client when a document record is queried.
    """

    # Enables Pydantic to read directly from SQLAlchemy ORM models (Document instance)
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique database document ID")
    company: str = Field(..., description="Company name")
    fiscal_year: int = Field(..., description="Fiscal year")
    form_type: str = Field(default="10-K", description="Filing Form type (10-K, 10-Q, 20-F)")
    fiscal_year_end: str | None = Field(None, description="Filing fiscal year end date")
    filename: str = Field(..., description="Uploaded PDF filename")
    content_hash: str = Field(..., description="SHA-256 hash for deduplication/idempotency")
    storage_path: str | None = Field(None, description="Storage location of the original PDF")
    upload_date: datetime = Field(..., description="Timestamp of document upload")


class DocumentUploadResult(BaseModel):
    """
    Response returned immediately after an upload request.
    Informs the client whether this document is brand new or was already in the database.
    """

    document: DocumentResponse
    is_duplicate: bool = Field(
        default=False,
        description="True if identical PDF was previously uploaded (idempotent skip)",
    )
    message: str = Field(..., description="User-friendly status message")
