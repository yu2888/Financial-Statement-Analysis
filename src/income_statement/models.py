"""Pydantic models for income statement data."""

from pydantic import BaseModel, Field


class IncomeStatementData(BaseModel):
    """Raw elements extracted from an income statement / statement of operations."""

    total_revenue: float = Field(0.0, description="Total Revenue / Net Sales")
    cost_of_revenue: float = Field(0.0, description="Cost of Revenue / COGS")
    gross_profit: float = Field(0.0, description="Gross Profit")
    research_and_development: float = Field(0.0, description="Research & Development")
    selling_general_admin: float = Field(0.0, description="Selling, General & Administrative")
    other_operating_expenses: float = Field(0.0, description="Other Operating Expenses")
    total_operating_expenses: float = Field(0.0, description="Total Operating Expenses")
    operating_income: float = Field(0.0, description="Operating Income / Loss")
    interest_income: float = Field(0.0, description="Interest Income")
    interest_expense: float = Field(0.0, description="Interest Expense")
    other_income_expense: float = Field(0.0, description="Other Income / Expense, Net")
    income_before_tax: float = Field(0.0, description="Income Before Income Taxes")
    income_tax_expense: float = Field(0.0, description="Income Tax Expense / Benefit")
    net_income: float = Field(0.0, description="Net Income / Loss")
    basic_eps: float = Field(0.0, description="Basic Earnings Per Share")
    diluted_eps: float = Field(0.0, description="Diluted Earnings Per Share")
    basic_shares_outstanding: float = Field(0.0, description="Basic Weighted Average Shares Outstanding")
    diluted_shares_outstanding: float = Field(0.0, description="Diluted Weighted Average Shares Outstanding")

    company_name: str = Field("Unknown", description="Company name")
    period: str = Field("Unknown", description="Reporting period (e.g. 'December 31, 2024')")
    currency: str = Field("USD", description="Currency used")
    units: str = Field("millions", description="Scale of monetary values (millions, thousands, billions, ones)")


class IncomeStatementMultiPeriod(BaseModel):
    current_period: IncomeStatementData
    prior_period: IncomeStatementData | None = None
