"""Financial indicator calculations from income statement data."""

from dataclasses import dataclass
from .models import IncomeStatementData


class IncomeStatementIndicators:
    def __init__(self, data: IncomeStatementData):
        self.data = data

    def gross_margin(self) -> float | None:
        if self.data.total_revenue == 0: return None
        return (self.data.gross_profit / self.data.total_revenue) * 100

    def operating_margin(self) -> float | None:
        if self.data.total_revenue == 0: return None
        return (self.data.operating_income / self.data.total_revenue) * 100

    def net_margin(self) -> float | None:
        if self.data.total_revenue == 0: return None
        return (self.data.net_income / self.data.total_revenue) * 100

    def rd_to_revenue(self) -> float | None:
        if self.data.total_revenue == 0: return None
        return (self.data.research_and_development / self.data.total_revenue) * 100

    def sga_to_revenue(self) -> float | None:
        if self.data.total_revenue == 0: return None
        return (self.data.selling_general_admin / self.data.total_revenue) * 100

    def effective_tax_rate(self) -> float | None:
        if self.data.income_before_tax == 0: return None
        return (self.data.income_tax_expense / self.data.income_before_tax) * 100

    def interest_coverage(self) -> float | None:
        if self.data.interest_expense == 0: return None
        return self.data.operating_income / self.data.interest_expense

    def gross_profit_check(self) -> float:
        return self.data.total_revenue - self.data.cost_of_revenue - self.data.gross_profit

    def is_valid(self, tolerance: float = 0.5) -> bool:
        return abs(self.gross_profit_check()) <= tolerance

    def summary(self) -> dict:
        return {
            "gross_margin": self.gross_margin(),
            "operating_margin": self.operating_margin(),
            "net_margin": self.net_margin(),
            "rd_to_revenue": self.rd_to_revenue(),
            "sga_to_revenue": self.sga_to_revenue(),
            "effective_tax_rate": self.effective_tax_rate(),
            "interest_coverage": self.interest_coverage(),
            "gross_profit_check": self.gross_profit_check(),
            "extraction_valid": self.is_valid(),
        }


_IS_YOY_KEY_ITEMS = [
    "total_revenue", "cost_of_revenue", "gross_profit",
    "operating_income", "net_income", "research_and_development", "selling_general_admin",
]
_IS_YOY_RATIOS = ["gross_margin", "operating_margin", "net_margin", "effective_tax_rate"]


@dataclass
class IncomeStatementYoY:
    current: IncomeStatementIndicators
    prior: IncomeStatementIndicators

    def absolute_changes(self) -> dict[str, float]:
        return {k: getattr(self.current.data, k) - getattr(self.prior.data, k) for k in _IS_YOY_KEY_ITEMS}

    def percentage_changes(self) -> dict[str, float | None]:
        result: dict[str, float | None] = {}
        for k in _IS_YOY_KEY_ITEMS:
            cur, pri = getattr(self.current.data, k), getattr(self.prior.data, k)
            result[k] = None if pri == 0 else ((cur - pri) / abs(pri)) * 100
        return result

    def ratio_changes(self) -> dict[str, float | None]:
        result: dict[str, float | None] = {}
        for name in _IS_YOY_RATIOS:
            cur, pri = getattr(self.current, name)(), getattr(self.prior, name)()
            result[name] = None if cur is None or pri is None else cur - pri
        return result
