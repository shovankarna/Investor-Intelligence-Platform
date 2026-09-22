"""
Conversational RAG Chat API Endpoint.

WHY BUFFERED CITATION DELIVERY (PROJECT.md §12):
For v1, delivering a complete structured response containing both the answer 
and citation metadata array ensures atomic provenance rendering on the frontend.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.llm.schemas import ChatResponse
from app.services.chat_service import ChatQueryRequest, ChatService

router = APIRouter()


@router.post(
    "/query",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit an investor question to the RAG Assistant",
)
async def chat_query(
    request: ChatQueryRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ChatResponse:
    """
    Dual-path RAG chat endpoint:
    - Automatically classifies intent (Structured vs Narrative vs Hybrid)
    - Retrieves verified SQL numbers and cross-encoder reranked narrative chunks
    - Returns citation-backed conversational answers
    """
    return await ChatService.process_chat_query(
        session=session,
        request=request,
    )
