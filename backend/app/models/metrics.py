"""
Pydantic Schemas for Financial Metrics & Computed Ratios.

WHY STRICT TARGET SCHEMAS (PROJECT.md §8 & ADR-1):
Standardizing the 13 core line items across all companies (Apple, Microsoft, Tesla)
allows universal ratio calculations and side-by-side comparative dashboards.
"""

from typing import Any
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RawMetricItem(BaseModel):
    """
    Schema for an extracted raw metric with strict citation provenance (ADR-2).
    """

    metric_name: str = Field(..., description="Standard snake_case key (e.g., 'total_revenue')")
    value: Decimal = Field(..., description="Raw metric value in Decimal (never float)")

    @field_validator("value", mode="before")
    @classmethod
    def sanitize_decimal_value(cls, v: Any) -> Decimal:
        """Parses and sanitizes strings with commas, dollar signs, and parentheses into Decimal."""
        if isinstance(v, Decimal):
            return v
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        if isinstance(v, str):
            clean = v.strip().replace("$", "").replace(",", "").replace(" ", "")
            # Support negative accounting notation: (1234) -> -1234
            if clean.startswith("(") and clean.endswith(")"):
                clean = f"-{clean[1:-1]}"
            try:
                return Decimal(clean)
            except Exception as e:
                raise ValueError(f"Cannot parse financial value '{v}' into Decimal: {e}")
        return Decimal(str(v))
    unit: str = Field(
        default="USD_millions",
        description="Unit scale: 'USD_millions', 'USD_thousands', 'USD_units'",
    )
    currency: str = Field(default="USD", description="Currency ISO code")
    fiscal_year: int | None = Field(None, description="Fiscal year (e.g., 2024)")
    source_page: int = Field(
        default=1, description="Physical PDF page number where this figure appears"
    )
    page_number: int | None = Field(
        None, description="Alias for source_page from extraction output"
    )
    source_chunk_id: str | None = Field(
        None, description="Optional reference to the source chunk/table"
    )
    verified: bool = Field(
        default=True, description="True if value appeared verbatim in source table text"
    )
    low_confidence: bool = Field(
        default=False,
        description="True if accounting equation or grounding check flagged this metric",
    )

    @model_validator(mode="after")
    def sync_page_number(self) -> "RawMetricItem":
        if self.page_number is not None and (self.source_page is None or self.source_page <= 0):
            self.source_page = self.page_number
        elif self.source_page is not None and self.page_number is None:
            self.page_number = self.source_page
        return self


class RawMetricResponse(RawMetricItem):
    """Schema returned when reading stored metrics from the database."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int


class CalculatedRatios(BaseModel):
    """
    Financial ratios deterministically computed in Python (ADR-4).
    All percentage values are scaled to 100 (e.g. 28.5 means 28.5%).
    """

    gross_margin_pct: Decimal | None = Field(
        None, description="(gross_profit / total_revenue) * 100"
    )
    operating_margin_pct: Decimal | None = Field(
        None, description="(operating_income / total_revenue) * 100"
    )
    net_margin_pct: Decimal | None = Field(None, description="(net_income / total_revenue) * 100")
    free_cash_flow: Decimal | None = Field(
        None, description="operating_cash_flow - capital_expenditures"
    )
    debt_to_equity: Decimal | None = Field(
        None, description="total_liabilities / stockholders_equity"
    )
    return_on_equity_pct: Decimal | None = Field(
        None, description="(net_income / stockholders_equity) * 100"
    )
    return_on_assets_pct: Decimal | None = Field(
        None, description="(net_income / total_assets) * 100"
    )


class CompanyFinancialSummary(BaseModel):
    """
    Full financial overview for a company in a specific fiscal year.
    Combines raw line items with deterministically calculated ratios.
    """

    document_id: int
    company: str
    fiscal_year: int
    raw_metrics: dict[str, RawMetricResponse] = Field(default_factory=dict)
    ratios: CalculatedRatios
    yoy_growth: dict[str, Decimal | None] = Field(
        default_factory=dict,
        description="Year-over-Year growth percentages compared to previous fiscal year",
    )
