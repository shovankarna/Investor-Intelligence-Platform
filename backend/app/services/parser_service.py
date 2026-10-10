"""
Layout-Aware PDF Parser Service using Docling.

WHY DOCLING OVER STANDARD OCR / PYPDF:
1. Layout Awareness: Docling understands reading order and distinguishes headers, paragraphs, and tables.
2. Clean Table Extraction: Exports tables directly to Markdown without garbling numeric columns.
3. Provenance Extraction: Captures page numbers and bounding box locations for every extracted element.
"""

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from app.models.parser import ParsedDocumentResult, ParsedProse, ParsedTable


class ParserService:
    """Service that converts raw PDF files into structured, layout-aware elements."""

    _converter: DocumentConverter = None

    @classmethod
    def get_converter(cls) -> DocumentConverter:
        """
        Initializes and caches the DocumentConverter singleton.
        Disables CPU-bound OCR since SEC filings are native digital text documents.
        """
        if cls._converter is None:
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = False  # Skip slow CPU OCR on digital PDFs
            pipeline_options.do_table_structure = True

            cls._converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )
        return cls._converter

    @classmethod
    def parse_pdf(
        cls,
        file_path_or_bytes: str,
        document_id: int,
        company: str,
        fiscal_year: int,
    ) -> ParsedDocumentResult:
        """
        Parses a PDF filing and separates its contents into structured tables and prose blocks.

        Args:
            file_path_or_bytes: Absolute file path of the PDF.
            document_id: Database ID of the parent document.
            company: Company name (e.g., 'Apple').
            fiscal_year: Fiscal year (e.g., 2024).

        Returns:
            ParsedDocumentResult with separate tables and prose_blocks lists.
        """
        converter = cls.get_converter()
        conv_result = converter.convert(file_path_or_bytes)
        doc = conv_result.document

        tables: list[ParsedTable] = []
        prose_blocks: list[ParsedProse] = []

        current_section = "General"
        table_idx = 0
        block_idx = 0

        # Iterate over all document elements preserving reading hierarchy
        for item, _level in doc.iterate_items():
            # Safely extract page number from provenance metadata
            page_no = 1
            if getattr(item, "prov", None) and len(item.prov) > 0:
                page_no = getattr(item.prov[0], "page_no", 1)

            # Check if element is a Table
            if hasattr(item, "export_to_markdown") and hasattr(item, "data"):
                try:
                    md_table = item.export_to_markdown(doc=doc)
                except TypeError:
                    md_table = item.export_to_markdown()
                try:
                    html_table = item.export_to_html(doc=doc) if hasattr(item, "export_to_html") else None
                except TypeError:
                    html_table = item.export_to_html() if hasattr(item, "export_to_html") else None

                num_rows = len(item.data.grid) if hasattr(item.data, "grid") else 0
                num_cols = (
                    len(item.data.grid[0]) if (num_rows > 0 and hasattr(item.data, "grid")) else 0
                )

                tables.append(
                    ParsedTable(
                        table_index=table_idx,
                        page_number=page_no,
                        section_path=current_section,
                        markdown_content=md_table,
                        html_content=html_table,
                        num_rows=num_rows,
                        num_cols=num_cols,
                    )
                )
                table_idx += 1

            # Check if element is a Heading/Section Title or Paragraph
            elif hasattr(item, "text"):
                text_content = item.text.strip()
                if not text_content:
                    continue

                # Determine if this element acts as a section header
                is_header = getattr(item, "label", "") in [
                    "section_header",
                    "title",
                    "heading",
                ]
                if is_header:
                    current_section = text_content

                prose_blocks.append(
                    ParsedProse(
                        block_index=block_idx,
                        page_number=page_no,
                        section_path=current_section,
                        content=text_content,
                        is_heading=is_header,
                    )
                )
                block_idx += 1

        total_pages = doc.num_pages() if hasattr(doc, "num_pages") else 1

        return ParsedDocumentResult(
            document_id=document_id,
            company=company,
            fiscal_year=fiscal_year,
            total_pages=total_pages,
            tables=tables,
            prose_blocks=prose_blocks,
        )
