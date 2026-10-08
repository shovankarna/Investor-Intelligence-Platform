"""
Financial Metrics API Endpoints.

WHY WE COMPUTE RATIOS DYNAMICALLY ON READ (ADR-1 & ADR-4):
We persist only raw extracted line items (e.g. revenue, net income) in PostgreSQL.
When the API is called, we compute the financial ratios (margins, FCF, ROE, YoY growth)
in plain Python code. This guarantees 100% mathematical integrity with zero extra LLM calls.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, FinancialMetric
from app.db.session import get_db_session
from app.models.metrics import (
    CalculatedRatios,
    CompanyFinancialSummary,
    RawMetricResponse,
)
from app.services.financial_math import FinancialMathService

router = APIRouter()


@router.get(
    "/{document_id}",
    response_model=CompanyFinancialSummary,
    summary="Get raw metrics and computed ratios for a specific document",
)
async def get_document_financials(
    document_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> CompanyFinancialSummary:
    """
    Returns all stored line items, computed financial ratios, and YoY growth
    for a single filing.
    """
    # 1. Fetch document metadata
    doc_query = select(Document).where(Document.id == document_id)
    doc_res = await session.execute(doc_query)
    doc = doc_res.scalars().first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document ID {document_id} not found.",
        )

    # 2. Fetch raw line items for this document
    metrics_query = select(FinancialMetric).where(FinancialMetric.document_id == document_id)
    metrics_res = await session.execute(metrics_query)
    metrics_list = metrics_res.scalars().all()

    # 3. Build dictionary of metric_name -> Decimal
    raw_dict: dict[str, RawMetricResponse] = {}
    math_dict: dict[str, Decimal] = {}
    for m in metrics_list:
        raw_dict[m.metric_name] = RawMetricResponse.model_validate(m)
        math_dict[m.metric_name] = m.value

    # 4. Compute ratios deterministically in Python
    ratios: CalculatedRatios = FinancialMathService.calculate_ratios(math_dict)

    # 5. Check if prior year document exists for YoY Growth
    yoy_growth: dict[str, Decimal | None] = {}
    prior_doc_query = select(Document).where(
        Document.company == doc.company, Document.fiscal_year == doc.fiscal_year - 1
    )
    prior_doc_res = await session.execute(prior_doc_query)
    prior_doc = prior_doc_res.scalars().first()

    if prior_doc:
        prior_metrics_query = select(FinancialMetric).where(
            FinancialMetric.document_id == prior_doc.id
        )
        prior_metrics_res = await session.execute(prior_metrics_query)
        prior_math_dict = {m.metric_name: m.value for m in prior_metrics_res.scalars().all()}
        yoy_growth = FinancialMathService.calculate_yoy_growth(math_dict, prior_math_dict)

    return CompanyFinancialSummary(
        document_id=doc.id,
        company=doc.company,
        fiscal_year=doc.fiscal_year,
        raw_metrics=raw_dict,
        ratios=ratios,
        yoy_growth=yoy_growth,
    )


@router.get(
    "/company/{company}",
    response_model=list[CompanyFinancialSummary],
    summary="Get multi-year financial history for a company",
)
async def get_company_history(
    company: str,
    session: AsyncSession = Depends(get_db_session),
) -> list[CompanyFinancialSummary]:
    """
    Returns multi-year financial summaries and computed ratios across all available
    fiscal years for a company.
    """
    # 1. Fetch all documents for this company ordered by year
    docs_query = (
        select(Document)
        .where(Document.company.ilike(company.strip()))
        .order_by(Document.fiscal_year.asc())
    )
    docs_res = await session.execute(docs_query)
    docs = docs_res.scalars().all()

    if not docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No filings found for company '{company}'.",
        )

    summaries: list[CompanyFinancialSummary] = []
    prior_math_dict: dict[str, Decimal] | None = None

    for doc in docs:
        m_query = select(FinancialMetric).where(FinancialMetric.document_id == doc.id)
        m_res = await session.execute(m_query)
        m_list = m_res.scalars().all()

        raw_dict = {m.metric_name: RawMetricResponse.model_validate(m) for m in m_list}
        math_dict = {m.metric_name: m.value for m in m_list}

        ratios = FinancialMathService.calculate_ratios(math_dict)
        yoy_growth = (
            FinancialMathService.calculate_yoy_growth(math_dict, prior_math_dict)
            if prior_math_dict
            else {}
        )

        summaries.append(
            CompanyFinancialSummary(
                document_id=doc.id,
                company=doc.company,
                fiscal_year=doc.fiscal_year,
                raw_metrics=raw_dict,
                ratios=ratios,
                yoy_growth=yoy_growth,
            )
        )
        prior_math_dict = math_dict

    return summaries
