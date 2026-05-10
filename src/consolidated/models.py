"""Consolidated result model spanning all three financial statements."""

from pydantic import BaseModel

from src.balance_sheet.models import MultiPeriodResult
from src.income_statement.models import IncomeStatementMultiPeriod
from src.cash_flow.models import CashFlowMultiPeriod


class FullFinancialResult(BaseModel):
    """Consolidated extraction result for all three financial statements."""

    balance_sheet: MultiPeriodResult | None = None
    income_statement: IncomeStatementMultiPeriod | None = None
    cash_flow: CashFlowMultiPeriod | None = None
