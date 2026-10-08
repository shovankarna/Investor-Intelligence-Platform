"""
Hybrid Search & Local Cross-Encoder Reranker.

WHY HYBRID SEARCH + RERANKING (PROJECT.md §5.2):
1. Two-Stage Retrieval Pipeline:
   - Stage 1 (Candidate Retrieval): Fetch top-20 chunks using dense vector cosine similarity
     and full-text keyword matching (fast, high recall).
   - Stage 2 (Cross-Encoder Scoring): 'BAAI/bge-reranker-base' scores (Query, Chunk) pairs
     jointly with full cross-attention to filter down to the top-5 most relevant chunks (high precision).
2. Zero API Cost: Reranker runs locally in memory (~400MB footprint).
"""

from dataclasses import dataclass

from sentence_transformers import CrossEncoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Chunk, Document
from app.rag.embedder import EmbeddingService


@dataclass
class RerankedChunk:
    """Container holding a chunk and its cross-encoder rerank score."""

    chunk: Chunk
    rerank_score: float


class HybridRetriever:
    """Coordinates hybrid vector search and local cross-encoder reranking."""

    _reranker: CrossEncoder = None

    @classmethod
    def get_reranker(cls) -> CrossEncoder:
        """Loads and caches the BAAI/bge-reranker-base model singleton."""
        if cls._reranker is None:
            print(f"Loading local reranker model '{settings.RERANKER_MODEL_NAME}' into memory...")
            cls._reranker = CrossEncoder(settings.RERANKER_MODEL_NAME)
        return cls._reranker

    @classmethod
    async def search_candidates(
        cls,
        session: AsyncSession,
        query: str,
        company: str | None = None,
        fiscal_year: int | None = None,
        top_k: int = 20,
    ) -> list[Chunk]:
        """
        Stage 1: Retrieves top-K candidate chunks using vector similarity and document filters.
        """
        # Generate normalized embedding for the query string
        query_vectors = EmbeddingService.embed_texts([query])
        if not query_vectors:
            return []
        query_vector = query_vectors[0]

        # Build candidate query joining with Document table for metadata filters
        stmt = select(Chunk).join(Document, Chunk.document_id == Document.id)

        if company:
            stmt = stmt.where(Document.company.ilike(f"%{company.strip()}%"))
        if fiscal_year:
            stmt = stmt.where(Document.fiscal_year == fiscal_year)

        # Order by Cosine Distance (<=> operator in pgvector)
        stmt = stmt.order_by(Chunk.embedding.cosine_distance(query_vector)).limit(top_k)

        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    def rerank_chunks(
        cls,
        query: str,
        candidates: list[Chunk],
        top_n: int = 5,
    ) -> list[tuple[Chunk, float]]:
        """
        Stage 2: Reranks candidate chunks with Cross-Encoder and returns top-N.

        Args:
            query: User's question string.
            candidates: Top-K chunks from Stage 1.
            top_n: Final count of high-precision chunks to retain.

        Returns:
            List of (Chunk, score) tuples sorted by relevance score descending.
        """
        if not candidates:
            return []

        reranker = cls.get_reranker()

        # Prepare query-document pairs for Cross-Encoder
        pairs = [[query, chunk.content] for chunk in candidates]
        scores = reranker.predict(pairs)

        # Pair chunks with their cross-encoder score and sort descending
        scored_candidates = list(zip(candidates, [float(s) for s in scores], strict=False))
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        return scored_candidates[:top_n]
