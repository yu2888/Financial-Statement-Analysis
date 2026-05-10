"""Pydantic models for cash flow statement data."""

from pydantic import BaseModel, Field


class CashFlowData(BaseModel):
    """Raw elements extracted from a cash flow statement."""

    net_income: float = Field(0.0, description="Net Income")
    depreciation_amortization: float = Field(0.0, description="Depreciation & Amortization")
    stock_based_compensation: float = Field(0.0, description="Stock-Based Compensation")
    changes_in_working_capital: float = Field(0.0, description="Changes in Working Capital")
    other_operating_adjustments: float = Field(0.0, description="Other Operating Adjustments")
    net_cash_from_operations: float = Field(0.0, description="Net Cash from Operating Activities")
    capital_expenditures: float = Field(0.0, description="Capital Expenditures (CapEx)")
    acquisitions: float = Field(0.0, description="Acquisitions, Net of Cash")
    purchases_of_investments: float = Field(0.0, description="Purchases of Investments")
    sales_of_investments: float = Field(0.0, description="Sales / Maturities of Investments")
    other_investing_activities: float = Field(0.0, description="Other Investing Activities")
    net_cash_from_investing: float = Field(0.0, description="Net Cash from Investing Activities")
    debt_issued: float = Field(0.0, description="Proceeds from Debt Issuance")
    debt_repaid: float = Field(0.0, description="Repayment of Debt")
    shares_issued: float = Field(0.0, description="Proceeds from Stock Issuance")
    shares_repurchased: float = Field(0.0, description="Share Repurchases / Buybacks")
    dividends_paid: float = Field(0.0, description="Dividends Paid")
    other_financing_activities: float = Field(0.0, description="Other Financing Activities")
    net_cash_from_financing: float = Field(0.0, description="Net Cash from Financing Activities")
    net_change_in_cash: float = Field(0.0, description="Net Change in Cash")
    cash_beginning_of_period: float = Field(0.0, description="Cash at Beginning of Period")
    cash_end_of_period: float = Field(0.0, description="Cash at End of Period")

    company_name: str = Field("Unknown", description="Company name")
    period: str = Field("Unknown", description="Reporting period (e.g. 'December 31, 2024')")
    currency: str = Field("USD", description="Currency used")
    units: str = Field("millions", description="Scale of monetary values (millions, thousands, billions, ones)")


class CashFlowMultiPeriod(BaseModel):
    current_period: CashFlowData
    prior_period: CashFlowData | None = None
