"""
RAG Chat Synthesis & Provenance Tracking Service.

WHY PROVENANCE CITATIONS ARE MANDATORY (ADR-2 & PROJECT.md §5.3):
In financial analysis, an unverified LLM claim is useless. Every response
must return structured citation pills linking directly to the source page number
and excerpt so analysts can verify claims against official SEC filings.
"""

from langfuse import observe
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import ChatLog, Document, FinancialMetric
from app.llm.client import llm_client
from app.llm.schemas import ChatResponse
from app.rag.retriever import HybridRetriever
from app.rag.router import QueryPlan, QueryRouter, QueryType


class ChatQueryRequest(BaseModel):
    """Schema for incoming user chat questions."""

    question: str = Field(
        ...,
        min_length=2,
        description="Investor question (e.g. 'What was Apple's 2024 revenue?')",
    )
    company: str | None = Field(None, description="Optional company filter")
    fiscal_year: int | None = Field(None, description="Optional fiscal year filter")


class ChatService:
    """Service that coordinates routing, retrieval, LLM synthesis, and citation tracking."""

    SYNTHESIS_SYSTEM_PROMPT = """
You are an expert financial analyst assistant for the Investor Intelligence Platform.
Your goal is to answer investor questions accurately based ONLY on the provided context.

RULES:
1. Base your answer strictly on the provided Structured Metrics and Narrative Context Chunks.
2. If exact numbers are available in the context, cite them accurately.
3. Every factual statement must cite its source chunk in the `citations` array.
4. If the context does not contain sufficient information to answer the question, state clearly what is missing rather than guessing.
"""

    @classmethod
    @observe(name="rag_chat_query")
    async def process_chat_query(
        cls,
        session: AsyncSession,
        request: ChatQueryRequest,
    ) -> ChatResponse:
        """
        Executes the dual-path RAG flow:
        1. Classifies query intent with QueryRouter.
        2. Retrieves structured metrics from SQL if needed.
        3. Retrieves and reranks narrative chunks from pgvector if needed.
        4. Synthesizes an answer with citation references.
        5. Logs the query/answer to chat_logs.
        """
        # Step 1: Route the query
        print(f"\n{'=' * 80}", flush=True)
        print(f"💬 [RAG QUERY] Incoming question: \"{request.question}\"", flush=True)
        plan: QueryPlan = await QueryRouter.route_query(request.question)
        target_company = request.company or (plan.companies[0] if plan.companies else None)
        target_year = request.fiscal_year or plan.fiscal_year

        print(f"   🧭 [Intent Router] Type: [{plan.query_type.value.upper()}] | Company: {target_company or 'Any'} | Fiscal Year: {target_year or 'Any'}", flush=True)

        context_blocks: list[str] = []
        retrieved_chunk_ids: list[str] = []

        # Step 2: Path A (Structured Metrics from Postgres)
        if plan.query_type in [QueryType.STRUCTURED, QueryType.HYBRID]:
            stmt = select(FinancialMetric).join(
                Document, FinancialMetric.document_id == Document.id
            )
            if target_company:
                stmt = stmt.where(Document.company.ilike(f"%{target_company}%"))
            if target_year:
                stmt = stmt.where(Document.fiscal_year == target_year)

            metrics_res = await session.execute(stmt)
            metrics = metrics_res.scalars().all()

            if metrics:
                metric_lines = [
                    f"- {m.metric_name}: {m.value} {m.unit} (Source Page: {m.source_page})"
                    for m in metrics
                ]
                context_blocks.append(
                    "### Structured Financial Line Items (from verified database):\n"
                    + "\n".join(metric_lines)
                )
                print(f"   📊 [Path A: Structured SQL] Retrieved {len(metrics)} verified financial metrics from PostgreSQL.", flush=True)
            else:
                print("   📊 [Path A: Structured SQL] No matching financial metrics found in database.", flush=True)

        # Step 3: Path B (Narrative Chunks via Hybrid Search + Cross-Encoder)
        if plan.query_type in [QueryType.NARRATIVE, QueryType.HYBRID]:
            candidates = await HybridRetriever.search_candidates(
                session=session,
                query=request.question,
                company=target_company,
                fiscal_year=target_year,
                top_k=settings.RETRIEVAL_TOP_K,
            )

            reranked = HybridRetriever.rerank_chunks(
                query=request.question,
                candidates=candidates,
                top_n=settings.RERANKER_TOP_N,
            )

            if reranked:
                narrative_lines = []
                for chunk, score in reranked:
                    retrieved_chunk_ids.append(chunk.id)
                    narrative_lines.append(
                        f"[Chunk {chunk.id} | Page {chunk.page_number} | Section: {chunk.section_path}]:\n{chunk.content}\n"
                    )
                context_blocks.append(
                    "### Qualitative & Narrative Filing Excerpts:\n" + "\n".join(narrative_lines)
                )
                print(f"   📚 [Path B: Vector Retrieval] Retrieved & Reranked top {len(reranked)} narrative chunks.", flush=True)
                for chunk, score in reranked[:2]:
                    print(f"      • [Score {score:.3f}] Page {chunk.page_number}: {chunk.section_path[:50]}...", flush=True)

        # Step 4: Construct LLM Prompt
        combined_context = (
            "\n\n".join(context_blocks)
            if context_blocks
            else "No relevant filings found for this query."
        )
        user_prompt = f"""
Investor Question: {request.question}

Available Context:
{combined_context}

Provide a comprehensive, accurate response with structured citations.
"""

        messages = [
            {"role": "system", "content": cls.SYNTHESIS_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        print(f"   🤖 [LLM Synthesis] Generating citation-backed answer...", flush=True)

        # Step 5: Generate answer via OpenRouter structured client
        chat_response: ChatResponse = await llm_client.generate_structured(
            messages=messages,
            schema=ChatResponse,
            temperature=0.1,
        )

        print(f"   ✨ [Synthesis Complete] Answer generated with {len(chat_response.citations)} citation pills.", flush=True)
        print(f"{'=' * 80}\n", flush=True)

        # Step 6: Log audit trail to chat_logs table (PROJECT.md §7)
        log_entry = ChatLog(
            question=request.question,
            answer=chat_response.answer,
            query_type=plan.query_type.value,
            retrieved_chunk_ids=retrieved_chunk_ids,
        )
        session.add(log_entry)
        await session.commit()

        return chat_response
