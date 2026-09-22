"""
Deterministic Financial Calculations Engine.

WHY PURE PYTHON ARITHMETIC (ADR-4 & AGENT.md §1 Rule 3):
1. Zero Hallucination: Standard LLMs frequently make simple math errors on large dollar amounts.
2. Decimal Precision: Floating-point numbers produce rounding artifacts (e.g. 0.1 + 0.2 = 0.30000000000000004).
   Python's Decimal guarantees exact arithmetic suitable for financial reporting.
3. High Performance: Computing 20 financial ratios in Python takes <1ms and incurs $0 API cost.
"""

from decimal import Decimal, DivisionByZero, InvalidOperation
from typing import Dict, Optional
from app.models.metrics import CalculatedRatios


class FinancialMathService:
    """Service computing margins, returns, cash flows, and growth rates."""

    @staticmethod
    def _safe_divide(numerator: Optional[Decimal], denominator: Optional[Decimal]) -> Optional[Decimal]:
        """Safely divides two Decimals, returning None if denominator is zero or values are missing."""
        if numerator is None or denominator is None:
            return None
        if denominator == Decimal("0"):
            return None
        try:
            return numerator / denominator
        except (DivisionByZero, InvalidOperation):
            return None

    @classmethod
    def calculate_ratios(cls, metrics: Dict[str, Decimal]) -> CalculatedRatios:
        """
        Calculates core financial ratios from a dictionary of raw line items.
        
        Args:
            metrics: Mapping of metric_name -> Decimal value
                     (e.g., {'total_revenue': Decimal('383285'), 'gross_profit': Decimal('170782'), ...})
        Returns:
            CalculatedRatios model containing margins, FCF, D/E, ROE, ROA.
        """
        rev = metrics.get("total_revenue")
        gross_profit = metrics.get("gross_profit")
        op_income = metrics.get("operating_income")
        net_income = metrics.get("net_income")
        op_cf = metrics.get("operating_cash_flow")
        capex = metrics.get("capital_expenditures")
        total_assets = metrics.get("total_assets")
        total_liabilities = metrics.get("total_liabilities")
        equity = metrics.get("stockholders_equity")

        # 1. Gross Margin (%) = (gross_profit / total_revenue) * 100
        gross_margin = None
        if rev and gross_profit:
            ratio = cls._safe_divide(gross_profit, rev)
            if ratio is not None:
                gross_margin = round(ratio * Decimal("100"), 2)

        # 2. Operating Margin (%) = (operating_income / total_revenue) * 100
        op_margin = None
        if rev and op_income:
            ratio = cls._safe_divide(op_income, rev)
            if ratio is not None:
                op_margin = round(ratio * Decimal("100"), 2)

        # 3. Net Margin (%) = (net_income / total_revenue) * 100
        net_margin = None
        if rev and net_income:
            ratio = cls._safe_divide(net_income, rev)
            if ratio is not None:
                net_margin = round(ratio * Decimal("100"), 2)

        # 4. Free Cash Flow = Operating Cash Flow - CapEx
        fcf = None
        if op_cf is not None and capex is not None:
            fcf = op_cf - capex

        # 5. Debt-to-Equity = Total Liabilities / Stockholders' Equity
        debt_to_equity = None
        if total_liabilities is not None and equity:
            ratio = cls._safe_divide(total_liabilities, equity)
            if ratio is not None:
                debt_to_equity = round(ratio, 2)

        # 6. Return on Equity (ROE %) = (Net Income / Stockholders' Equity) * 100
        roe = None
        if net_income is not None and equity:
            ratio = cls._safe_divide(net_income, equity)
            if ratio is not None:
                roe = round(ratio * Decimal("100"), 2)

        # 7. Return on Assets (ROA %) = (Net Income / Total Assets) * 100
        roa = None
        if net_income is not None and total_assets:
            ratio = cls._safe_divide(net_income, total_assets)
            if ratio is not None:
                roa = round(ratio * Decimal("100"), 2)

        return CalculatedRatios(
            gross_margin_pct=gross_margin,
            operating_margin_pct=op_margin,
            net_margin_pct=net_margin,
            free_cash_flow=fcf,
            debt_to_equity=debt_to_equity,
            return_on_equity_pct=roe,
            return_on_assets_pct=roa,
        )

    @classmethod
    def calculate_yoy_growth(
        cls, 
        current_year_metrics: Dict[str, Decimal], 
        prior_year_metrics: Dict[str, Decimal]
    ) -> Dict[str, Optional[Decimal]]:
        """
        Calculates Year-over-Year (YoY) Growth percentage for matching line items.
        Formula: ((Value_Current - Value_Prior) / |Value_Prior|) * 100
        
        Args:
            current_year_metrics: Metrics for Year T
            prior_year_metrics: Metrics for Year T-1
        Returns:
            Dictionary of metric_name -> YoY Growth % (e.g. {'total_revenue': Decimal('8.52')})
        """
        growth_rates: Dict[str, Optional[Decimal]] = {}

        for key, val_curr in current_year_metrics.items():
            val_prior = prior_year_metrics.get(key)
            if val_curr is None or val_prior is None or val_prior == Decimal("0"):
                growth_rates[key] = None
                continue

            # YoY Formula: ((curr - prior) / abs(prior)) * 100
            diff = val_curr - val_prior
            growth = cls._safe_divide(diff, abs(val_prior))
            if growth is not None:
                growth_rates[key] = round(growth * Decimal("100"), 2)
            else:
                growth_rates[key] = None

        return growth_rates
