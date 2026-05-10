"""Financial indicator calculations from cash flow statement data."""

from dataclasses import dataclass
from .models import CashFlowData


class CashFlowIndicators:
    def __init__(self, data: CashFlowData):
        self.data = data

    def operating_cash_flow_ratio(self) -> float | None:
        if self.data.net_income == 0: return None
        return self.data.net_cash_from_operations / self.data.net_income

    def free_cash_flow(self) -> float:
        return self.data.net_cash_from_operations + self.data.capital_expenditures

    def capex_to_ocf(self) -> float | None:
        if self.data.net_cash_from_operations == 0: return None
        return (abs(self.data.capital_expenditures) / self.data.net_cash_from_operations) * 100

    def operating_pct(self) -> float | None:
        total = abs(self.data.net_cash_from_operations) + abs(self.data.net_cash_from_investing) + abs(self.data.net_cash_from_financing)
        if total == 0: return None
        return (self.data.net_cash_from_operations / total) * 100

    def debt_service_coverage(self) -> float | None:
        if self.data.debt_repaid == 0: return None
        return self.data.net_cash_from_operations / abs(self.data.debt_repaid)

    def shareholder_return(self) -> float:
        return abs(self.data.shares_repurchased) + abs(self.data.dividends_paid)

    def cash_reconciliation_check(self) -> float:
        return self.data.cash_beginning_of_period + self.data.net_change_in_cash - self.data.cash_end_of_period

    def is_valid(self, tolerance: float = 0.5) -> bool:
        return abs(self.cash_reconciliation_check()) <= tolerance

    def summary(self) -> dict:
        return {
            "free_cash_flow": self.free_cash_flow(),
            "operating_cash_flow_ratio": self.operating_cash_flow_ratio(),
            "capex_to_ocf": self.capex_to_ocf(),
            "operating_pct": self.operating_pct(),
            "debt_service_coverage": self.debt_service_coverage(),
            "shareholder_return": self.shareholder_return(),
            "cash_reconciliation_check": self.cash_reconciliation_check(),
            "extraction_valid": self.is_valid(),
        }


_CF_YOY_KEY_ITEMS = ["net_cash_from_operations", "net_cash_from_investing", "net_cash_from_financing", "capital_expenditures", "net_change_in_cash"]
_CF_YOY_RATIOS = ["operating_cash_flow_ratio", "capex_to_ocf"]


@dataclass
class CashFlowYoY:
    current: CashFlowIndicators
    prior: CashFlowIndicators

    def absolute_changes(self) -> dict[str, float]:
        return {k: getattr(self.current.data, k) - getattr(self.prior.data, k) for k in _CF_YOY_KEY_ITEMS}

    def percentage_changes(self) -> dict[str, float | None]:
        result: dict[str, float | None] = {}
        for k in _CF_YOY_KEY_ITEMS:
            cur, pri = getattr(self.current.data, k), getattr(self.prior.data, k)
            result[k] = None if pri == 0 else ((cur - pri) / abs(pri)) * 100
        return result

    def ratio_changes(self) -> dict[str, float | None]:
        result: dict[str, float | None] = {}
        for name in _CF_YOY_RATIOS:
            cur, pri = getattr(self.current, name)(), getattr(self.prior, name)()
            result[name] = None if cur is None or pri is None else cur - pri
        return result
