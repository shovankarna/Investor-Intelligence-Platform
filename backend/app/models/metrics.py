"""
Pydantic Schemas for Financial Metrics & Computed Ratios.

WHY STRICT TARGET SCHEMAS (PROJECT.md §8 & ADR-1):
Standardizing the 13 core line items across all companies (Apple, Microsoft, Tesla)
allows universal ratio calculations and side-by-side comparative dashboards.
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class RawMetricItem(BaseModel):
    """
    Schema for an extracted raw metric with strict citation provenance (ADR-2).
    """

    metric_name: str = Field(..., description="Standard snake_case key (e.g., 'total_revenue')")
    value: Decimal = Field(..., description="Raw metric value in Decimal (never float)")
    unit: str = Field(
        default="USD_millions",
        description="Unit scale: 'USD_millions', 'USD_thousands', 'USD_units'",
    )
    currency: str = Field(default="USD", description="Currency ISO code")
    source_page: int = Field(..., description="Physical PDF page number where this figure appears")
    source_chunk_id: str | None = Field(
        None, description="Optional reference to the source chunk/table"
    )


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
