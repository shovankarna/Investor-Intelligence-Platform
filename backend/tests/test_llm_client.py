"""Unit tests for OpenRouter client, fallback chains, and structured output parsing."""

import pytest
from pydantic import BaseModel
from app.llm.client import OpenRouterClient
from app.llm.schemas import ChatResponse, CitationItem


class SimpleMetricOutput(BaseModel):
    metric_name: str
    value: float


@pytest.mark.asyncio
async def test_structured_output_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that valid JSON text is parsed into the expected Pydantic schema."""
    client = OpenRouterClient(api_key="mock_key")

    mock_json_str = '{"answer": "Total Revenue was $100M.", "citations": [{"chunk_id": "doc_p1_c1", "page_number": 1}]}'

    # Mock the internal generate call to return our mock JSON
    async def mock_generate(*args, **kwargs):
        from app.llm.schemas import LLMGenerationResult

        return LLMGenerationResult(
            raw_text=mock_json_str,
            model_used="deepseek/deepseek-v4-flash:free",
        )

    monkeypatch.setattr(client, "generate", mock_generate)

    response: ChatResponse = await client.generate_structured(
        messages=[{"role": "user", "content": "What was revenue?"}],
        schema=ChatResponse,
    )

    assert response.answer == "Total Revenue was $100M."
    assert len(response.citations) == 1
    assert response.citations[0].chunk_id == "doc_p1_c1"
    assert response.citations[0].page_number == 1
