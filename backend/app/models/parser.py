"""
Pydantic Schemas for Layout-Aware Document Parsing (Docling stream fork).

WHY WE SEPARATE TABLES AND PROSE (AGENT.md §6):
1. Tables contain quantitative data and must never be split across chunks mid-row.
2. Narrative prose contains strategic insights and risk factors, which require
   hierarchical chunking with section breadcrumbs (e.g. 'Item 7 > Liquidity').
"""

from pydantic import BaseModel, Field


class ParsedTable(BaseModel):
    """
    Represents a structured table extracted from a financial filing.
    Preserves table structure in markdown/HTML format along with page provenance.
    """

    table_index: int = Field(..., description="0-indexed table sequence in document")
    page_number: int = Field(..., description="1-indexed physical page number in PDF")
    section_path: str = Field(
        ...,
        description="Hierarchical heading path, e.g. 'Item 8. Financial Statements'",
    )
    markdown_content: str = Field(..., description="Clean Markdown representation of the table")
    html_content: str | None = Field(
        None, description="HTML representation for complex tables with merged cells"
    )
    num_rows: int = Field(..., description="Number of rows in the table")
    num_cols: int = Field(..., description="Number of columns in the table")


class ParsedProse(BaseModel):
    """
    Represents a narrative prose block (paragraph, heading, or bullet point).
    """

    block_index: int = Field(..., description="0-indexed sequence of text element")
    page_number: int = Field(..., description="1-indexed physical page number in PDF")
    section_path: str = Field(
        ..., description="Hierarchical heading path, e.g. 'Item 1A. Risk Factors'"
    )
    content: str = Field(..., description="Extracted plain text of the paragraph or heading")
    is_heading: bool = Field(
        default=False,
        description="True if this block represents a section title/header",
    )


class ParsedDocumentResult(BaseModel):
    """
    The full output returned by the layout-aware parser service.
    Contains separate streams for tables and narrative text.
    """

    document_id: int = Field(..., description="Database ID of the filing")
    company: str = Field(..., description="Company name")
    fiscal_year: int = Field(..., description="Fiscal year")
    total_pages: int = Field(..., description="Total pages parsed")
    tables: list[ParsedTable] = Field(
        default_factory=list, description="All extracted financial and metadata tables"
    )
    prose_blocks: list[ParsedProse] = Field(
        default_factory=list, description="All narrative prose blocks"
    )
