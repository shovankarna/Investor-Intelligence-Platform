"""
Unit tests for Upload Validator and Form Type Classification (Change 1).
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.services.metric_extractor import (
    IFRS_ALIASES,
    US_GAAP_ALIASES,
    MetricExtractionService,
)
from app.services.upload_validator import (
    UploadValidationResult,
    validate_upload,
)


def test_alias_map_selection() -> None:
    """Verify that US GAAP is picked for 10-K/10-Q and IFRS for 20-F."""
    us_gaap_10k = MetricExtractionService.get_alias_map("10-K")
    us_gaap_10q = MetricExtractionService.get_alias_map("10-Q")
    ifrs_20f = MetricExtractionService.get_alias_map("20-F")

    assert us_gaap_10k == US_GAAP_ALIASES
    assert us_gaap_10q == US_GAAP_ALIASES
    assert ifrs_20f == IFRS_ALIASES
    assert "Gross margin" in us_gaap_10k["gross_profit"]
    assert "Profit for the year" in ifrs_20f["net_income"]


def test_validator_rejects_short_scanned_pdf(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check 1: Reject PDFs with < 200 characters in first 3 pages."""
    mock_reader = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Short scanned text snippet."
    mock_reader.pages = [mock_page]

    monkeypatch.setattr("pypdf.PdfReader", lambda path: mock_reader)

    with pytest.raises(HTTPException) as exc_info:
        validate_upload("dummy.pdf")

    assert exc_info.value.status_code == 422
    assert (
        exc_info.value.detail
        == "Scanned or image-only PDF is not supported. Upload a text-based PDF."
    )


def test_validator_rejects_unsupported_form_40f(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Check 2: Reject 40-F or other unsupported forms with exact required error message."""
    mock_reader = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = (
        "UNITED STATES SECURITIES AND EXCHANGE COMMISSION Washington, D.C. 20549 "
        "FORM 40-F "
        "ANNUAL REPORT PURSUANT TO SECTION 12 OF THE SECURITIES EXCHANGE ACT OF 1934 "
        "For the fiscal year ended December 31, 2023. "
        + ("Extra corporate text filling the page to exceed two hundred characters count. " * 3)
    )
    mock_reader.pages = [mock_page]

    monkeypatch.setattr("pypdf.PdfReader", lambda path: mock_reader)

    with pytest.raises(HTTPException) as exc_info:
        validate_upload("dummy.pdf")

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Unsupported document type: 40-F. Supported: 10-K, 10-Q, 20-F."


def test_validator_rejects_unknown_document_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Check 2: Reject document without recognized FORM pattern."""
    mock_reader = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = (
        "This is an investor presentation and quarterly earnings slide deck. "
        "We are discussing forward looking projections and revenue targets for next year. "
        "No official SEC form designation is present in this entire document header. "
        + ("Additional presentation narrative content for length requirement. " * 3)
    )
    mock_reader.pages = [mock_page]

    monkeypatch.setattr("pypdf.PdfReader", lambda path: mock_reader)

    with pytest.raises(HTTPException) as exc_info:
        validate_upload("dummy.pdf")

    assert exc_info.value.status_code == 422
    assert (
        exc_info.value.detail == "Unsupported document type: unknown. Supported: 10-K, 10-Q, 20-F."
    )


def test_validator_accepts_form_10k_with_fiscal_year_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Check 2 & 3: Successfully validate 10-K and extract fiscal year end date."""
    mock_reader = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = (
        "UNITED STATES SECURITIES AND EXCHANGE COMMISSION Washington, D.C. 20549 "
        "FORM 10-K "
        "ANNUAL REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES EXCHANGE ACT OF 1934 "
        "For the fiscal year ended September 28, 2024 "
        "Commission file number: 001-36743 "
        "Apple Inc. One Apple Park Way, Cupertino, California 95014 "
        + ("Additional business descriptions and corporate filing overview text. " * 3)
    )
    mock_reader.pages = [mock_page]

    monkeypatch.setattr("pypdf.PdfReader", lambda path: mock_reader)

    result = validate_upload("apple_10k.pdf")

    assert isinstance(result, UploadValidationResult)
    assert result.form_type == "10-K"
    assert result.fiscal_year_end == "September 28, 2024"


def test_validator_accepts_form_20f_ifrs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check 2 & 3: Successfully validate 20-F foreign filing."""
    mock_reader = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = (
        "UNITED STATES SECURITIES AND EXCHANGE COMMISSION Washington, D.C. 20549 "
        "FORM 20-F "
        "REGISTRATION STATEMENT PURSUANT TO SECTION 12(b) OR 12(g) OF THE SECURITIES EXCHANGE ACT OF 1934 "
        "For the fiscal year ended December 31, 2023 "
        "ASML Holding N.V. De Run 6501, 5504 DR Veldhoven, The Netherlands "
        + ("Additional corporate governance and foreign private issuer details. " * 3)
    )
    mock_reader.pages = [mock_page]

    monkeypatch.setattr("pypdf.PdfReader", lambda path: mock_reader)

    result = validate_upload("asml_20f.pdf")

    assert result.form_type == "20-F"
    assert result.fiscal_year_end == "December 31, 2023"


def test_validator_accepts_form_10q_without_fiscal_year_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Check 2 & 3: Successfully validate 10-Q (quarterly filing, nullable fiscal_year_end)."""
    mock_reader = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = (
        "UNITED STATES SECURITIES AND EXCHANGE COMMISSION Washington, D.C. 20549 "
        "FORM 10-Q "
        "QUARTERLY REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES EXCHANGE ACT OF 1934 "
        "For the quarterly period ended June 30, 2024 "
        "Microsoft Corporation, One Microsoft Way, Redmond, Washington "
        + ("Quarterly unaudited consolidated financial information and MD&A prose. " * 3)
    )
    mock_reader.pages = [mock_page]

    monkeypatch.setattr("pypdf.PdfReader", lambda path: mock_reader)

    result = validate_upload("msft_10q.pdf")

    assert result.form_type == "10-Q"
    assert result.fiscal_year_end is None
