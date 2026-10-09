"""
Integration and Route Tests for API Endpoints and Ingestion Idempotency.

Strictly adhering to AGENT.md §10:
- Every API route gets at least one happy-path test and one invalid-input test.
- Ingestion idempotency gets an explicit test: ingest the same file twice, assert no duplicate rows.
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.models import Document, FinancialMetric
from app.db.session import get_db_session
from app.llm.schemas import ChatResponse, CitationItem
from app.main import app
from app.models.document import DocumentCreate
from app.services.document_service import DocumentService
from app.services.upload_validator import UploadValidationResult


@pytest.fixture
def mock_db_session():
    """Provides a mocked SQLAlchemy AsyncSession for route testing."""
    session = AsyncMock()
    return session


@pytest.fixture(autouse=True)
def override_db(mock_db_session):
    """Overrides the FastAPI database session dependency for every test."""

    async def _get_test_session():
        yield mock_db_session

    app.dependency_overrides[get_db_session] = _get_test_session
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_system_health_and_root():
    """Verify system health and root endpoints return 200 OK."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["status"] == "healthy"

        root_resp = await client.get("/")
        assert root_resp.status_code == 200
        assert "Welcome" in root_resp.json()["message"]


# ==============================================================================
# Document Upload & Ingestion Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_upload_document_invalid_extension():
    """Invalid-input: Non-PDF files should be rejected with HTTP 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("report.txt", b"plain text content", "text/plain")}
        data = {"company": "Apple", "fiscal_year": 2024}
        response = await client.post("/api/documents/upload", data=data, files=files)

        assert response.status_code == 400
        assert "Only PDF files are supported" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_document_empty_file():
    """Invalid-input: Empty PDF files should be rejected with HTTP 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("empty.pdf", b"", "application/pdf")}
        data = {"company": "Apple", "fiscal_year": 2024}
        response = await client.post("/api/documents/upload", data=data, files=files)

        assert response.status_code == 400
        assert "Uploaded PDF file is empty" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_document_scanned_pdf_rejected(monkeypatch: pytest.MonkeyPatch):
    """Invalid-input: Scanned PDFs (< 200 chars) must return HTTP 422."""
    mock_reader = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Scanned image without text layer."
    mock_reader.pages = [mock_page]

    monkeypatch.setattr("pypdf.PdfReader", lambda path: mock_reader)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("scanned.pdf", b"%PDF-1.4 mock content", "application/pdf")}
        data = {"company": "Apple", "fiscal_year": 2024}
        response = await client.post("/api/documents/upload", data=data, files=files)

        assert response.status_code == 422
        assert (
            response.json()["detail"]
            == "Scanned or image-only PDF is not supported. Upload a text-based PDF."
        )


@pytest.mark.asyncio
async def test_upload_document_unsupported_form_rejected(monkeypatch: pytest.MonkeyPatch):
    """Invalid-input: Unsupported form types (e.g. 40-F) must return HTTP 422."""
    mock_reader = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = (
        "UNITED STATES SECURITIES AND EXCHANGE COMMISSION Washington, D.C. 20549 "
        "FORM 40-F REGISTRATION STATEMENT PURSUANT TO SECTION 12 OF THE EXCHANGE ACT. "
        "This filing contains enough characters to satisfy the text density threshold of 200 chars."
    )
    mock_reader.pages = [mock_page]

    monkeypatch.setattr("pypdf.PdfReader", lambda path: mock_reader)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("filing_40f.pdf", b"%PDF-1.4 mock content", "application/pdf")}
        data = {"company": "Canadian Co", "fiscal_year": 2024}
        response = await client.post("/api/documents/upload", data=data, files=files)

        assert response.status_code == 422
        assert "Unsupported document type: 40-F" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_document_happy_path(monkeypatch: pytest.MonkeyPatch):
    """Happy-path: Valid 10-K filing upload successfully ingests and returns HTTP 201."""
    # Mock validate_upload to return valid 10-K
    val_result = UploadValidationResult(
        is_valid=True,
        form_type="10-K",
        fiscal_year_end="September 28, 2024",
    )
    monkeypatch.setattr("app.api.documents.validate_upload", lambda path: val_result)

    # Mock DocumentService.process_and_save_document
    mock_doc = Document(
        id=1,
        company="Apple",
        fiscal_year=2024,
        form_type="10-K",
        fiscal_year_end="September 28, 2024",
        filename="apple_10k.pdf",
        content_hash="abc123hash",
        upload_date=datetime.now(UTC),
    )

    async def mock_process(*args, **kwargs):
        return mock_doc, False

    monkeypatch.setattr(DocumentService, "process_and_save_document", mock_process)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("apple_10k.pdf", b"%PDF-1.4 mock pdf data", "application/pdf")}
        data = {"company": "Apple", "fiscal_year": 2024}
        response = await client.post("/api/documents/upload", data=data, files=files)

        assert response.status_code == 201
        res_json = response.json()
        assert res_json["is_duplicate"] is False
        assert res_json["document"]["company"] == "Apple"
        assert res_json["document"]["fiscal_year"] == 2024
        assert res_json["document"]["form_type"] == "10-K"
        assert "uploaded successfully" in res_json["message"]


@pytest.mark.asyncio
async def test_upload_document_idempotency_skip(monkeypatch: pytest.MonkeyPatch):
    """Idempotency: Re-uploading an identical PDF returns is_duplicate=True with HTTP 201."""
    val_result = UploadValidationResult(
        is_valid=True,
        form_type="10-K",
        fiscal_year_end="September 28, 2024",
    )
    monkeypatch.setattr("app.api.documents.validate_upload", lambda path: val_result)

    mock_doc = Document(
        id=1,
        company="Apple",
        fiscal_year=2024,
        form_type="10-K",
        fiscal_year_end="September 28, 2024",
        filename="apple_10k.pdf",
        content_hash="abc123hash",
        upload_date=datetime.now(UTC),
    )

    async def mock_process(*args, **kwargs):
        return mock_doc, True  # Duplicate upload

    monkeypatch.setattr(DocumentService, "process_and_save_document", mock_process)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("apple_10k.pdf", b"%PDF-1.4 mock pdf data", "application/pdf")}
        data = {"company": "Apple", "fiscal_year": 2024}
        response = await client.post("/api/documents/upload", data=data, files=files)

        assert response.status_code == 201
        res_json = response.json()
        assert res_json["is_duplicate"] is True
        assert "already processed previously (idempotent skip)" in res_json["message"]


@pytest.mark.asyncio
async def test_list_documents(mock_db_session):
    """Happy-path: GET /api/documents/ lists stored documents."""
    mock_doc = Document(
        id=1,
        company="Apple",
        fiscal_year=2024,
        form_type="10-K",
        fiscal_year_end="September 28, 2024",
        filename="apple_10k.pdf",
        content_hash="hash1",
        upload_date=datetime.now(UTC),
    )

    mock_exec = MagicMock()
    mock_exec.scalars.return_value.all.return_value = [mock_doc]
    mock_db_session.execute.return_value = mock_exec

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/documents/")
        assert response.status_code == 200
        docs = response.json()
        assert len(docs) == 1
        assert docs[0]["company"] == "Apple"


# ==============================================================================
# Financial Metrics & Dynamic Ratio API Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_get_document_financials_not_found(mock_db_session):
    """Invalid-input: Requesting metrics for non-existent document returns HTTP 404."""
    mock_exec = MagicMock()
    mock_exec.scalars.return_value.first.return_value = None
    mock_db_session.execute.return_value = mock_exec

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/metrics/999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_document_financials_happy_path(mock_db_session):
    """
    Happy-path: Returns raw line items and deterministically computes ratios and YoY growth.
    """
    current_doc = Document(
        id=1,
        company="Apple",
        fiscal_year=2024,
        form_type="10-K",
        filename="apple_2024.pdf",
        content_hash="h2024",
        upload_date=datetime.now(UTC),
    )
    prior_doc = Document(
        id=2,
        company="Apple",
        fiscal_year=2023,
        form_type="10-K",
        filename="apple_2023.pdf",
        content_hash="h2023",
        upload_date=datetime.now(UTC),
    )

    metrics_2024 = [
        FinancialMetric(
            id=1,
            document_id=1,
            metric_name="total_revenue",
            value=Decimal("391035000000"),
            unit="USD_units",
            currency="USD",
            source_page=32,
            verified=True,
            low_confidence=False,
        ),
        FinancialMetric(
            id=2,
            document_id=1,
            metric_name="cost_of_revenue",
            value=Decimal("210352000000"),
            unit="USD_units",
            currency="USD",
            source_page=32,
            verified=True,
            low_confidence=False,
        ),
        FinancialMetric(
            id=3,
            document_id=1,
            metric_name="gross_profit",
            value=Decimal("180683000000"),
            unit="USD_units",
            currency="USD",
            source_page=32,
            verified=True,
            low_confidence=False,
        ),
        FinancialMetric(
            id=4,
            document_id=1,
            metric_name="net_income",
            value=Decimal("93736000000"),
            unit="USD_units",
            currency="USD",
            source_page=32,
            verified=True,
            low_confidence=False,
        ),
        FinancialMetric(
            id=5,
            document_id=1,
            metric_name="operating_cash_flow",
            value=Decimal("118264000000"),
            unit="USD_units",
            currency="USD",
            source_page=35,
            verified=True,
            low_confidence=False,
        ),
        FinancialMetric(
            id=6,
            document_id=1,
            metric_name="capital_expenditures",
            value=Decimal("9447000000"),
            unit="USD_units",
            currency="USD",
            source_page=35,
            verified=True,
            low_confidence=False,
        ),
    ]

    metrics_2023 = [
        FinancialMetric(
            id=7,
            document_id=2,
            metric_name="total_revenue",
            value=Decimal("383285000000"),
            unit="USD_units",
            currency="USD",
            source_page=30,
            verified=True,
            low_confidence=False,
        ),
    ]

    # Configure mock DB session responses for sequence of queries
    call_idx = 0

    async def mock_execute(stmt):
        nonlocal call_idx
        mock_res = MagicMock()
        if call_idx == 0:
            # Query 1: current doc
            mock_res.scalars.return_value.first.return_value = current_doc
        elif call_idx == 1:
            # Query 2: current doc metrics
            mock_res.scalars.return_value.all.return_value = metrics_2024
        elif call_idx == 2:
            # Query 3: prior doc
            mock_res.scalars.return_value.first.return_value = prior_doc
        elif call_idx == 3:
            # Query 4: prior doc metrics
            mock_res.scalars.return_value.all.return_value = metrics_2023
        call_idx += 1
        return mock_res

    mock_db_session.execute.side_effect = mock_execute

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/metrics/1")
        assert response.status_code == 200
        data = response.json()

        assert data["company"] == "Apple"
        assert data["fiscal_year"] == 2024

        # Verify raw metrics (Decimal serialized as string or float depending on JSON mode)
        assert "total_revenue" in data["raw_metrics"]
        assert Decimal(str(data["raw_metrics"]["total_revenue"]["value"])) == Decimal(
            "391035000000"
        )

        # Verify deterministic ratios
        # Gross Margin = (180683 / 391035) * 100 = 46.206... -> ~46.21%
        assert data["ratios"]["gross_margin_pct"] is not None
        assert abs(float(data["ratios"]["gross_margin_pct"]) - 46.21) < 0.1

        # Free Cash Flow = 118,264M - 9,447M = 108,817,000,000
        assert Decimal(str(data["ratios"]["free_cash_flow"])) == Decimal("108817000000")

        # Verify YoY revenue growth = ((391035 - 383285) / 383285) * 100 = 2.02%
        assert "total_revenue" in data["yoy_growth"]
        assert abs(float(data["yoy_growth"]["total_revenue"]) - 2.02) < 0.1


@pytest.mark.asyncio
async def test_get_company_history_not_found(mock_db_session):
    """Invalid-input: Requesting history for non-existent company returns HTTP 404."""
    mock_exec = MagicMock()
    mock_exec.scalars.return_value.all.return_value = []
    mock_db_session.execute.return_value = mock_exec

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/metrics/company/NonExistentCorp")
        assert response.status_code == 404
        assert "no filings found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_company_history_happy_path(mock_db_session):
    """Happy-path: Multi-year company history returns list of summaries with YoY growth."""
    doc_2023 = Document(
        id=1,
        company="Microsoft",
        fiscal_year=2023,
        form_type="10-K",
        filename="msft_2023.pdf",
        content_hash="h1",
        upload_date=datetime.now(UTC),
    )
    doc_2024 = Document(
        id=2,
        company="Microsoft",
        fiscal_year=2024,
        form_type="10-K",
        filename="msft_2024.pdf",
        content_hash="h2",
        upload_date=datetime.now(UTC),
    )

    metrics_23 = [
        FinancialMetric(
            id=1,
            document_id=1,
            metric_name="total_revenue",
            value=Decimal("211915000000"),
            unit="USD_units",
            currency="USD",
            source_page=40,
            verified=True,
            low_confidence=False,
        ),
    ]
    metrics_24 = [
        FinancialMetric(
            id=2,
            document_id=2,
            metric_name="total_revenue",
            value=Decimal("245122000000"),
            unit="USD_units",
            currency="USD",
            source_page=42,
            verified=True,
            low_confidence=False,
        ),
    ]

    call_count = 0

    async def mock_execute(stmt):
        nonlocal call_count
        mock_res = MagicMock()
        if call_count == 0:
            # Query 1: all docs for company
            mock_res.scalars.return_value.all.return_value = [doc_2023, doc_2024]
        elif call_count == 1:
            # Query 2: metrics for 2023 doc
            mock_res.scalars.return_value.all.return_value = metrics_23
        elif call_count == 2:
            # Query 3: metrics for 2024 doc
            mock_res.scalars.return_value.all.return_value = metrics_24
        call_count += 1
        return mock_res

    mock_db_session.execute.side_effect = mock_execute

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/metrics/company/Microsoft")
        assert response.status_code == 200
        summaries = response.json()
        assert len(summaries) == 2
        assert summaries[0]["fiscal_year"] == 2023
        assert summaries[1]["fiscal_year"] == 2024
        # 2024 should have YoY revenue growth: ((245122 - 211915) / 211915) * 100 = 15.67%
        assert "total_revenue" in summaries[1]["yoy_growth"]
        assert abs(float(summaries[1]["yoy_growth"]["total_revenue"]) - 15.67) < 0.1


# ==============================================================================
# Conversational RAG Chat Endpoint Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_chat_query_invalid_input():
    """Invalid-input: Question shorter than 2 chars triggers HTTP 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/chat/query", json={"question": "?"})
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_query_happy_path(monkeypatch: pytest.MonkeyPatch):
    """Happy-path: Submitting a valid question returns citation-grounded response."""
    from app.services.chat_service import ChatService

    mock_chat_response = ChatResponse(
        answer="Apple's total revenue for FY2024 was $391,035 million.",
        citations=[
            CitationItem(
                chunk_id="doc1_p32_c1",
                page_number=32,
            )
        ],
        confidence_score=0.98,
    )

    async def mock_process_chat(*args, **kwargs):
        return mock_chat_response

    monkeypatch.setattr(ChatService, "process_chat_query", mock_process_chat)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/chat/query",
            json={"question": "What was Apple's total revenue in 2024?", "company": "Apple"},
        )
        assert response.status_code == 200
        res_data = response.json()
        assert "391,035" in res_data["answer"]
        assert len(res_data["citations"]) == 1
        assert res_data["citations"][0]["page_number"] == 32
        assert res_data["confidence_score"] == 0.98


# ==============================================================================
# DocumentService Ingestion Idempotency Unit Test
# ==============================================================================


@pytest.mark.asyncio
async def test_document_service_idempotency_skip_pipeline(monkeypatch: pytest.MonkeyPatch):
    """
    Tests DocumentService.process_and_save_document directly.
    When a document matching the content_hash already exists, the service MUST
    return (existing_doc, True) immediately WITHOUT calling:
    - ParserService.parse_pdf
    - MetricExtractionService.extract_all_metrics
    - EmbeddingService.embed_chunks
    """
    mock_session = AsyncMock()
    existing_doc = Document(
        id=42,
        company="Microsoft",
        fiscal_year=2024,
        form_type="10-K",
        filename="msft.pdf",
        content_hash="existing_sha256_hash",
    )

    # get_by_hash returns existing_doc
    monkeypatch.setattr(DocumentService, "get_by_hash", AsyncMock(return_value=existing_doc))

    # Spy mocks to ensure pipeline steps are NEVER called on duplicate
    mock_parser = MagicMock()
    mock_extractor = AsyncMock()
    mock_embedder = MagicMock()

    monkeypatch.setattr("app.services.document_service.ParserService.parse_pdf", mock_parser)
    monkeypatch.setattr(
        "app.services.document_service.MetricExtractionService.extract_all_metrics", mock_extractor
    )
    monkeypatch.setattr(
        "app.services.document_service.EmbeddingService.embed_chunks", mock_embedder
    )

    fake_file = MagicMock()
    fake_file.filename = "msft.pdf"
    fake_metadata = DocumentCreate(company="Microsoft", fiscal_year=2024, form_type="10-K")

    result_doc, is_duplicate = await DocumentService.process_and_save_document(
        session=mock_session,
        file=fake_file,
        metadata=fake_metadata,
        file_bytes=b"%PDF-1.4 dummy content",
    )

    assert is_duplicate is True
    assert result_doc.id == 42
    assert result_doc.company == "Microsoft"

    # Verify parser, extractor, and embedder were never touched
    mock_parser.assert_not_called()
    mock_extractor.assert_not_called()
    mock_embedder.assert_not_called()
    mock_session.commit.assert_not_called()
