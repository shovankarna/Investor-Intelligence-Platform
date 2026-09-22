"""
Unit tests for deterministic financial calculations (AGENT.md §10 & ADR-4).
Verifies Profit Margins, Free Cash Flow, Debt-to-Equity, ROE, ROA, and YoY Growth.
"""

from decimal import Decimal
from app.services.financial_math import FinancialMathService


def test_margin_calculations() -> None:
    """Test Gross, Operating, and Net Profit Margins with known figures."""
    # Test Data representing $383,285M revenue (Apple FY2023 sample)
    metrics = {
        "total_revenue": Decimal("383285"),
        "gross_profit": Decimal("169148"),
        "operating_income": Decimal("114301"),
        "net_income": Decimal("96995"),
    }

    ratios = FinancialMathService.calculate_ratios(metrics)

    # Gross Margin = (169148 / 383285) * 100 = 44.13%
    assert ratios.gross_margin_pct == Decimal("44.13")
    # Operating Margin = (114301 / 383285) * 100 = 29.82%
    assert ratios.operating_margin_pct == Decimal("29.82")
    # Net Margin = (96995 / 383285) * 100 = 25.31%
    assert ratios.net_margin_pct == Decimal("25.31")


def test_free_cash_flow() -> None:
    """Test Free Cash Flow: Operating Cash Flow - CapEx."""
    metrics = {
        "operating_cash_flow": Decimal("110543"),
        "capital_expenditures": Decimal("10959"),
    }

    ratios = FinancialMathService.calculate_ratios(metrics)
    assert ratios.free_cash_flow == Decimal("99584")


def test_debt_to_equity_and_roe() -> None:
    """Test balance sheet and return ratios (Debt-to-Equity, ROE, ROA)."""
    metrics = {
        "net_income": Decimal("96995"),
        "total_assets": Decimal("352583"),
        "total_liabilities": Decimal("290437"),
        "stockholders_equity": Decimal("62146"),
    }

    ratios = FinancialMathService.calculate_ratios(metrics)

    # Debt to Equity = 290437 / 62146 = 4.67
    assert ratios.debt_to_equity == Decimal("4.67")
    # ROE = (96995 / 62146) * 100 = 156.08%
    assert ratios.return_on_equity_pct == Decimal("156.08")
    # ROA = (96995 / 352583) * 100 = 27.51%
    assert ratios.return_on_assets_pct == Decimal("27.51")


def test_safe_division_by_zero() -> None:
    """Verify that zero revenue or zero equity returns None instead of raising an unhandled exception."""
    metrics = {
        "total_revenue": Decimal("0"),
        "gross_profit": Decimal("1000"),
        "stockholders_equity": Decimal("0"),
        "net_income": Decimal("500"),
    }

    ratios = FinancialMathService.calculate_ratios(metrics)
    assert ratios.gross_margin_pct is None
    assert ratios.debt_to_equity is None
    assert ratios.return_on_equity_pct is None


def test_yoy_growth_calculation() -> None:
    """Test Year-over-Year (YoY) Growth calculation between FY2023 and FY2024."""
    fy2023 = {
        "total_revenue": Decimal("383285"),
        "net_income": Decimal("96995"),
    }
    fy2024 = {
        "total_revenue": Decimal("391035"),
        "net_income": Decimal("93736"),
    }

    growth = FinancialMathService.calculate_yoy_growth(fy2024, fy2023)

    # Revenue growth: ((391035 - 383285) / 383285) * 100 = +2.02%
    assert growth["total_revenue"] == Decimal("2.02")
    # Net Income growth: ((93736 - 96995) / 96995) * 100 = -3.36%
    assert growth["net_income"] == Decimal("-3.36")
