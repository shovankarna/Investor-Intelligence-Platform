"""
Intent Classification & Query Router.

WHY QUERY ROUTING IS CRITICAL (ADR-1 & PROJECT.md §5.1):
1. Financial questions are diverse:
   - "What was 2024 revenue?" -> Must NEVER be answered by vector search (hallucination risk).
   - "What are the key antitrust risks?" -> Cannot be answered by SQL tables.
2. The router inspects the user query, extracts company/year filters, and assigns
   the optimal retrieval strategy: STRUCTURED, NARRATIVE, or HYBRID.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from app.llm.client import llm_client


class QueryType(str, Enum):
    STRUCTURED = "STRUCTURED"  # Quantitative/metric lookups -> SQL
    NARRATIVE = "NARRATIVE"    # Qualitative, risk, strategy -> Vector search
    HYBRID = "HYBRID"          # Analytical questions needing numbers + context


class QueryPlan(BaseModel):
    """Execution plan generated for an incoming user question."""
    query_type: QueryType = Field(..., description="Chosen retrieval strategy")
    companies: List[str] = Field(default_factory=list, description="Target company names identified in query")
    fiscal_year: Optional[int] = Field(None, description="Target fiscal year if specified")
    metrics: List[str] = Field(default_factory=list, description="Target metric keys (e.g. ['total_revenue'])")
    reasoning: str = Field(..., description="Brief rationale for this routing decision")


class QueryRouter:
    """Classifies user queries into the appropriate RAG retrieval path."""

    ROUTER_SYSTEM_PROMPT = """
You are a senior financial research assistant query router.
Analyze the user's financial question and determine the optimal retrieval plan.

Classification Taxonomy:
1. STRUCTURED: Questions asking ONLY for quantitative financial numbers, ratios, or comparisons.
   Examples: "What was Microsoft's revenue in 2024?", "Show me Tesla's Debt-to-Equity ratio."
2. NARRATIVE: Questions asking for qualitative context, strategy, risks, lawsuits, or management commentary.
   Examples: "What are Apple's supply chain risks?", "Explain Microsoft's cloud strategy."
3. HYBRID: Questions requiring BOTH exact numbers and narrative explanation.
   Examples: "Why did net income decline despite revenue growth?", "How did R&D spending impact margins?"

Identify target company names (e.g. Apple, Microsoft) and fiscal years (e.g. 2024).
"""

    @classmethod
    async def route_query(cls, user_question: str) -> QueryPlan:
        """
        Routes the user's question to STRUCTURED, NARRATIVE, or HYBRID plan.
        """
        messages = [
            {"role": "system", "content": cls.ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": f"User Question: {user_question}"},
        ]

        try:
            plan = await llm_client.generate_structured(
                messages=messages,
                schema=QueryPlan,
                temperature=0.0,
            )
            return plan
        except Exception as exc:
            print(f"⚠️ [Router] Router fallback to HYBRID due to error: {exc}")
            # Safe fallback: If router fails, default to HYBRID to retrieve both streams
            return QueryPlan(
                query_type=QueryType.HYBRID,
                companies=[],
                fiscal_year=None,
                metrics=[],
                reasoning="Fallback to HYBRID due to router exception.",
            )
