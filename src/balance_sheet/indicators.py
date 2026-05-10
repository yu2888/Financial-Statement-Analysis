"""Financial indicator calculations from extracted balance sheet data."""

from dataclasses import dataclass

from .models import BalanceSheetData


class FinancialIndicators:
    """Calculates liquidity, solvency, and validation indicators."""

    def __init__(self, data: BalanceSheetData):
        self.data = data

    def current_ratio(self) -> float | None:
        if self.data.total_current_liabilities == 0:
            return None
        return self.data.total_current_assets / self.data.total_current_liabilities

    def quick_ratio(self) -> float | None:
        if self.data.total_current_liabilities == 0:
            return None
        quick_assets = (
            self.data.cash_and_equivalents
            + self.data.marketable_securities
            + self.data.accounts_receivable
        )
        return quick_assets / self.data.total_current_liabilities

    def debt_to_equity(self) -> float | None:
        if self.data.total_shareholders_equity == 0:
            return None
        return self.data.total_liabilities / self.data.total_shareholders_equity

    def working_capital(self) -> float:
        return self.data.total_current_assets - self.data.total_current_liabilities

    def cash_ratio(self) -> float | None:
        if self.data.total_current_liabilities == 0:
            return None
        return (self.data.cash_and_equivalents + self.data.marketable_securities) / self.data.total_current_liabilities

    def equity_ratio(self) -> float | None:
        if self.data.total_assets == 0:
            return None
        return self.data.total_shareholders_equity / self.data.total_assets

    def debt_ratio(self) -> float | None:
        if self.data.total_assets == 0:
            return None
        return self.data.total_liabilities / self.data.total_assets

    def net_debt(self) -> float:
        total_debt = self.data.short_term_debt + self.data.long_term_debt + self.data.current_portion_long_term_debt
        return total_debt - self.data.cash_and_equivalents

    def tangible_book_value(self) -> float:
        return self.data.total_shareholders_equity - self.data.intangible_assets

    def current_asset_pct(self) -> float | None:
        if self.data.total_assets == 0:
            return None
        return (self.data.total_current_assets / self.data.total_assets) * 100

    def non_current_asset_pct(self) -> float | None:
        if self.data.total_assets == 0:
            return None
        return ((self.data.total_assets - self.data.total_current_assets) / self.data.total_assets) * 100

    def accounting_equation_check(self) -> float:
        return self.data.total_assets - (self.data.total_liabilities + self.data.total_shareholders_equity)

    def is_valid(self, tolerance: float = 0.5) -> bool:
        return abs(self.accounting_equation_check()) <= tolerance

    def summary(self) -> dict:
        return {
            "current_ratio": self.current_ratio(),
            "quick_ratio": self.quick_ratio(),
            "debt_to_equity": self.debt_to_equity(),
            "working_capital": self.working_capital(),
            "accounting_equation_discrepancy": self.accounting_equation_check(),
            "extraction_valid": self.is_valid(),
            "cash_ratio": self.cash_ratio(),
            "equity_ratio": self.equity_ratio(),
            "debt_ratio": self.debt_ratio(),
            "net_debt": self.net_debt(),
            "tangible_book_value": self.tangible_book_value(),
            "current_asset_pct": self.current_asset_pct(),
            "non_current_asset_pct": self.non_current_asset_pct(),
        }


_YOY_KEY_ITEMS = [
    "total_assets", "total_liabilities", "total_shareholders_equity",
    "total_current_assets", "total_current_liabilities",
    "cash_and_equivalents", "long_term_debt",
]

_YOY_RATIOS = [
    "current_ratio", "quick_ratio", "debt_to_equity",
    "cash_ratio", "equity_ratio", "debt_ratio",
]


@dataclass
class YoYComparison:
    current: FinancialIndicators
    prior: FinancialIndicators

    def absolute_changes(self) -> dict[str, float]:
        return {k: getattr(self.current.data, k) - getattr(self.prior.data, k) for k in _YOY_KEY_ITEMS}

    def percentage_changes(self) -> dict[str, float | None]:
        result: dict[str, float | None] = {}
        for k in _YOY_KEY_ITEMS:
            cur, pri = getattr(self.current.data, k), getattr(self.prior.data, k)
            result[k] = None if pri == 0 else ((cur - pri) / abs(pri)) * 100
        return result

    def ratio_changes(self) -> dict[str, float | None]:
        result: dict[str, float | None] = {}
        for name in _YOY_RATIOS:
            cur, pri = getattr(self.current, name)(), getattr(self.prior, name)()
            result[name] = None if cur is None or pri is None else cur - pri
        return result
