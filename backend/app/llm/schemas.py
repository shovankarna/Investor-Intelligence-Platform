"""Pydantic schemas for LLM inputs, structured outputs, and citations."""

from typing import Any

from pydantic import BaseModel, Field


class CitationItem(BaseModel):
    """Represents a strict provenance citation back to a document chunk."""

    chunk_id: str = Field(description="Unique ID of the source chunk")
    page_number: int = Field(description="PDF page number of the source chunk")


class ChatResponse(BaseModel):
    """Structured response format returned by the RAG Chat Agent."""

    answer: str = Field(description="Synthesized conversational answer")
    citations: list[CitationItem] = Field(
        default_factory=list,
        description="Structured citations payload (PROJECT.md §12)",
    )
    confidence_score: float | None = Field(
        default=None,
        description="Internal grounding confidence score (0.0 to 1.0)",
    )


class LLMGenerationResult(BaseModel):
    """Metadata wrapper returned by the OpenRouter client."""

    raw_text: str
    parsed_json: dict[str, Any] | None = None
    model_used: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
