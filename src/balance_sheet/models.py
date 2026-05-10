"""Pydantic models for balance sheet data."""

from pydantic import BaseModel, Field


class BalanceSheetData(BaseModel):
    """Raw elements extracted from a balance sheet PDF."""

    # --- Current Assets ---
    cash_and_equivalents: float = Field(0.0, description="Cash & Cash Equivalents")
    accounts_receivable: float = Field(0.0, description="Accounts Receivable")
    marketable_securities: float = Field(0.0, description="Marketable Securities")
    inventory: float = Field(0.0, description="Inventory")
    other_current_assets: float = Field(0.0, description="Other Current Assets")
    total_current_assets: float = Field(0.0, description="Total Current Assets")

    # --- Non-Current Assets ---
    ppe: float = Field(0.0, description="Property, Plant & Equipment (net)")
    intangible_assets: float = Field(0.0, description="Intangible Assets / Goodwill")
    other_non_current_assets: float = Field(0.0, description="Other Non-Current Assets")
    operating_lease_right_of_use: float = Field(0.0, description="Operating Lease Right-of-Use Assets")
    finance_lease_right_of_use: float = Field(0.0, description="Finance Lease Right-of-Use Assets")
    equity_investments: float = Field(0.0, description="Equity Method and Other Equity Investments")
    deferred_tax_assets: float = Field(0.0, description="Non-Current Deferred Tax Assets")
    total_assets: float = Field(0.0, description="Total Assets")

    # --- Current Liabilities ---
    accounts_payable: float = Field(0.0, description="Accounts Payable")
    short_term_debt: float = Field(0.0, description="Short-Term Debt")
    deferred_revenue: float = Field(0.0, description="Deferred Revenue")
    other_current_liabilities: float = Field(0.0, description="Other Current Liabilities")
    accrued_expenses: float = Field(0.0, description="Accrued Expenses and Other Current Liabilities")
    current_portion_long_term_debt: float = Field(0.0, description="Current Portion of Long-Term Debt")
    operating_lease_liabilities_current: float = Field(0.0, description="Current Operating Lease Liabilities")
    total_current_liabilities: float = Field(0.0, description="Total Current Liabilities")

    # --- Non-Current Liabilities ---
    long_term_debt: float = Field(0.0, description="Long-Term Debt")
    other_non_current_liabilities: float = Field(0.0, description="Other Non-Current Liabilities")
    operating_lease_liabilities_non_current: float = Field(0.0, description="Non-Current Operating Lease Liabilities")
    total_liabilities: float = Field(0.0, description="Total Liabilities")

    # --- Shareholders' Equity ---
    common_stock: float = Field(0.0, description="Common Stock")
    retained_earnings: float = Field(0.0, description="Retained Earnings")
    other_equity: float = Field(0.0, description="Other Equity Components")
    additional_paid_in_capital: float = Field(0.0, description="Additional Paid-In Capital")
    treasury_stock: float = Field(0.0, description="Treasury Stock")
    accumulated_other_comprehensive_income: float = Field(0.0, description="Accumulated Other Comprehensive Income/Loss")
    total_shareholders_equity: float = Field(0.0, description="Total Shareholders' Equity")

    # --- Meta ---
    company_name: str = Field("Unknown", description="Company name")
    period: str = Field("Unknown", description="Reporting period (e.g. 'December 31, 2024')")
    currency: str = Field("USD", description="Currency used")
    units: str = Field("millions", description="Scale of monetary values (millions, thousands, billions, ones)")


class MultiPeriodResult(BaseModel):
    """Holds extracted balance sheet data for current and optional prior period."""

    current_period: BalanceSheetData
    prior_period: BalanceSheetData | None = None
