"""
Structured Financial Metric Extraction Service using OpenRouter.

WHY STRUCTURED EXTRACTION OVER FREE-FORM TEXT (AGENT.md §8):
1. Financial reports use different line item names ('Net Sales' vs 'Total Revenue', 
   'Additions to Property & Equipment' vs 'Capital Expenditures').
2. We provide an explicit Pydantic schema to OpenRouter models (DeepSeek / Kimi), 
   forcing the model to normalize naming variations to standard snake_case keys.
3. Strict Provenance: Every single metric MUST cite its source_page (ADR-2).
"""

from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field
from app.llm.client import llm_client
from app.models.metrics import RawMetricItem
from app.models.parser import ParsedTable


class ExtractedMetricList(BaseModel):
    """Container schema for structured LLM extraction output."""
    metrics: List[RawMetricItem] = Field(
        default_factory=list,
        description="List of extracted raw financial line items with page provenance"
    )


class MetricExtractionService:
    """Service that coordinates LLM-based extraction of the 13 core financial metrics."""

    EXTRACTION_SYSTEM_PROMPT = """
You are a precise financial data extraction analyst.
Analyze the provided financial statement table from an SEC 10-K filing.

Extract any of the following 13 target metrics if they appear in the table:
- Income Statement: total_revenue, cost_of_revenue, gross_profit, operating_expenses, operating_income, net_income, diluted_eps
- Balance Sheet: total_assets, total_liabilities, stockholders_equity, cash_and_equivalents
- Cash Flow: operating_cash_flow, capital_expenditures

RULES:
1. Return EXACT raw numeric values in the specified unit (e.g. if reported in millions, 383,285 represents $383,285M).
2. Parentheses indicate negative numbers: (1,234) -> -1234.
3. You MUST provide the exact source_page number provided in the table metadata.
4. If a metric is NOT in the table, DO NOT invent or guess it; simply omit it.
"""

    @classmethod
    async def extract_metrics_from_table(cls, table: ParsedTable) -> List[RawMetricItem]:
        """
        Extracts financial line items from a single parsed table.
        
        Args:
            table: ParsedTable instance with markdown content and page provenance.
        Returns:
            List of validated RawMetricItem instances.
        """
        user_prompt = f"""
Table Metadata:
- Page Number: {table.page_number}
- Section: {table.section_path}

Table Markdown:
{table.markdown_content}
"""

        messages = [
            {"role": "system", "content": cls.EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        try:
            result: ExtractedMetricList = await llm_client.generate_structured(
                messages=messages,
                schema=ExtractedMetricList,
                temperature=0.0,
            )
            # Ensure each metric carries the table's source_page and chunk reference
            for metric in result.metrics:
                if metric.source_page <= 0:
                    metric.source_page = table.page_number
                metric.source_chunk_id = f"p{table.page_number}_t{table.table_index}"
            return result.metrics
        except Exception as exc:
            print(f"⚠️ [Extraction] Failed to extract metrics from table on page {table.page_number}: {exc}")
            return []

    @classmethod
    async def extract_all_metrics(cls, tables: List[ParsedTable]) -> List[RawMetricItem]:
        """
        Iterates over all candidate tables in a document and extracts financial metrics.
        Deduplicates by metric_name, keeping the latest/most specific statement figure.
        """
        extracted_map = {}

        for table in tables:
            # Quick heuristic: Skip tiny non-financial tables (< 3 rows)
            if table.num_rows < 3:
                continue

            items = await cls.extract_metrics_from_table(table)
            for item in items:
                # Upsert by metric_name
                extracted_map[item.metric_name] = item

        return list(extracted_map.values())
