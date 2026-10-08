"""
Local Embedding Service using Sentence-Transformers.

WHY LOCAL IN-PROCESS EMBEDDINGS (ADR-5 & PROJECT.md §12):
1. Zero Cost & Zero Rate Limits: Embedding 100 pages with an external API would hit rate limits.
   Running 'BAAI/bge-small-en-v1.5' in-process costs $0 and runs in ~130MB RAM.
2. Fast Similarity: Vectors are normalized so Cosine Similarity is equivalent to an inner product.
3. Singleton Pattern: Model is loaded ONCE at startup to avoid re-instantiation latency.
"""

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.db.models import Chunk


class EmbeddingService:
    """Service managing local dense embedding generation and normalization."""

    _model: SentenceTransformer = None

    @classmethod
    def get_model(cls) -> SentenceTransformer:
        """
        Loads and caches the SentenceTransformer model singleton.
        """
        if cls._model is None:
            print(f"Loading embedding model '{settings.EMBEDDING_MODEL_NAME}' into memory...")
            cls._model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        return cls._model

    @classmethod
    def embed_texts(cls, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """
        Generates normalized vector embeddings for a list of text strings.

        Args:
            texts: List of text chunks to embed.
            batch_size: Number of texts to process in parallel per batch.

        Returns:
            List of 384-dimensional float lists normalized to unit length.
        """
        if not texts:
            return []

        model = cls.get_model()
        # encode with normalize_embeddings=True for exact cosine distance via dot product
        embeddings: np.ndarray = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )

        return embeddings.tolist()

    @classmethod
    def embed_chunks(cls, chunks: list[Chunk], batch_size: int = 32) -> list[Chunk]:
        """
        Populates the .embedding field for each Chunk in-place.

        Args:
            chunks: List of Chunk database models.
            batch_size: Batch size for parallel vector encoding.

        Returns:
            The same list of Chunks with the 384-d embedding vectors populated.
        """
        if not chunks:
            return chunks

        texts_to_embed = [chunk.content for chunk in chunks]
        vectors = cls.embed_texts(texts_to_embed, batch_size=batch_size)

        for chunk, vector in zip(chunks, vectors, strict=False):
            chunk.embedding = vector

        return chunks
