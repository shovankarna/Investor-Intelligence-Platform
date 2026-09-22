"""
Structure-Aware Document Chunker.

WHY NAIVE CHARACTER-COUNT CHUNKING FAILS IN FINANCE (AGENT.md §6):
1. Financial reports are highly hierarchical (e.g. 'Item 7. MD&A > Liquidity and Capital Resources').
   If you chunk arbitrarily every 500 characters, you cut off the context of which department or metric
   is being discussed.
2. We prepend a 'Contextual Header' to every single chunk before embedding:
   e.g. '[Company: Apple | FY2024 | Section: Item 7. MD&A | Page: 34]'
   This guarantees the embedding captures the company and section context.
"""

from typing import List
from app.core.config import settings
from app.db.models import Chunk
from app.models.parser import ParsedDocumentResult, ParsedProse, ParsedTable


class DocumentChunker:
    """Chunks layout-aware document elements while preserving structural hierarchy."""

    @staticmethod
    def _create_contextual_header(company: str, fiscal_year: int, section_path: str, page_no: int) -> str:
        """
        Creates a structured header prepended to the chunk text.
        This solves the 'out-of-context retrieval' problem in RAG.
        """
        return f"[Company: {company} | FY{fiscal_year} | Section: {section_path} | Page: {page_no}]\n"

    @classmethod
    def chunk_document(cls, parsed_doc: ParsedDocumentResult) -> List[Chunk]:
        """
        Transforms parsed tables and prose into database Chunk models.
        
        Args:
            parsed_doc: Parsed output from Docling containing tables and prose blocks.
            
        Returns:
            List of database Chunk records ready for embedding and storage.
        """
        chunks: List[Chunk] = []
        doc_id = parsed_doc.document_id
        company = parsed_doc.company
        fiscal_year = parsed_doc.fiscal_year
        seq_id = 1

        # -------------------------------------------------------------
        # 1. Chunk Tables (Tables are kept WHOLE - AGENT.md §6)
        # -------------------------------------------------------------
        for table in parsed_doc.tables:
            header = cls._create_contextual_header(
                company, fiscal_year, table.section_path, table.page_number
            )
            table_content = f"{header}Table ({table.num_rows} rows x {table.num_cols} cols):\n{table.markdown_content}"
            
            chunk_id = f"{doc_id}_p{table.page_number}_t{table.table_index}"
            chunks.append(
                Chunk(
                    id=chunk_id,
                    document_id=doc_id,
                    page_number=table.page_number,
                    section_path=table.section_path,
                    element_type="table",
                    content=table_content,
                )
            )

        # -------------------------------------------------------------
        # 2. Chunk Narrative Prose (Respecting Section Boundaries)
        # -------------------------------------------------------------
        current_section = ""
        current_page = 1
        current_buffer: List[str] = []
        current_word_count = 0
        
        # Word budget approximation: 1 token ≈ 0.75 words (300-600 tokens ≈ 225-450 words)
        max_words = int(settings.CHUNK_MAX_TOKENS * 0.75)

        for prose in parsed_doc.prose_blocks:
            # When section changes or page changes significantly, flush buffer
            if current_buffer and (prose.section_path != current_section or current_word_count >= max_words):
                header = cls._create_contextual_header(
                    company, fiscal_year, current_section, current_page
                )
                chunk_body = " ".join(current_buffer)
                full_content = f"{header}{chunk_body}"

                chunk_id = f"{doc_id}_p{current_page}_c{seq_id}"
                chunks.append(
                    Chunk(
                        id=chunk_id,
                        document_id=doc_id,
                        page_number=current_page,
                        section_path=current_section,
                        element_type="prose",
                        content=full_content,
                    )
                )
                seq_id += 1
                current_buffer = []
                current_word_count = 0

            current_section = prose.section_path
            current_page = prose.page_number
            current_buffer.append(prose.content)
            current_word_count += len(prose.content.split())

        # Flush any remaining prose in the buffer
        if current_buffer:
            header = cls._create_contextual_header(
                company, fiscal_year, current_section, current_page
            )
            chunk_body = " ".join(current_buffer)
            full_content = f"{header}{chunk_body}"

            chunk_id = f"{doc_id}_p{current_page}_c{seq_id}"
            chunks.append(
                Chunk(
                    id=chunk_id,
                    document_id=doc_id,
                    page_number=current_page,
                    section_path=current_section,
                    element_type="prose",
                    content=full_content,
                )
            )

        return chunks
