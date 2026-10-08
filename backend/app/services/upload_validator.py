"""
Upload Validator for SEC & Corporate Financial Filings.

Strict validation before running full ingestion:
1. Text layer check: Verifies at least 200 characters exist in the first 3 pages (rejects scanned/image-only PDFs).
2. Form type check: Validates supported SEC forms (10-K, 10-Q, 20-F).
3. Metadata extraction: Extracts the filing fiscal year end date if present.
"""

import re

import pypdf
from fastapi import HTTPException, status
from pydantic import BaseModel, Field


class UploadValidationResult(BaseModel):
    """Result of successful pre-ingestion validation."""

    form_type: str = Field(..., description="Detected SEC Form type (10-K, 10-Q, 20-F)")
    fiscal_year_end: str | None = Field(
        None,
        description="Extracted fiscal year end date string (e.g. 'September 28, 2024')",
    )


SUPPORTED_FORM_TYPES = {"10-K", "10-Q", "20-F"}


def validate_upload(path: str) -> UploadValidationResult:
    """
    Validates an uploaded PDF document before ingestion.

    Args:
        path: File path of the uploaded PDF file.

    Returns:
        UploadValidationResult with form_type and fiscal_year_end.

    Raises:
        HTTPException(422) if the file lacks text layer or is an unsupported form type.
    """
    # 1. Text layer check
    try:
        reader = pypdf.PdfReader(path)
        pages_to_check = reader.pages[:3]
        if not pages_to_check:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Scanned or image-only PDF is not supported. Upload a text-based PDF.",
            )

        extracted_pages = [page.extract_text() or "" for page in pages_to_check]
        combined_text = "\n".join(extracted_pages).strip()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Scanned or image-only PDF is not supported. Upload a text-based PDF.",
        ) from exc

    if len(combined_text) < 200:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Scanned or image-only PDF is not supported. Upload a text-based PDF.",
        )

    # 2. Form type check (regex on cover pages): FORM\s+(10-K|10-Q|20-F|40-F)
    form_pattern = re.compile(r"\bFORM\s+(10-K|10-Q|20-F|40-F)\b", re.IGNORECASE)
    match = form_pattern.search(combined_text)

    if match:
        detected_form = match.group(1).upper()
        if detected_form not in SUPPORTED_FORM_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Unsupported document type: {detected_form}. Supported: 10-K, 10-Q, 20-F.",
            )
        form_type = detected_form
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported document type: unknown. Supported: 10-K, 10-Q, 20-F.",
        )

    # 3. Metadata check: extract fiscal year end date if present
    fye_pattern = re.compile(r"fiscal year ended\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})", re.IGNORECASE)
    fye_match = fye_pattern.search(combined_text)
    fiscal_year_end: str | None = fye_match.group(1).strip() if fye_match else None

    return UploadValidationResult(
        form_type=form_type,
        fiscal_year_end=fiscal_year_end,
    )
