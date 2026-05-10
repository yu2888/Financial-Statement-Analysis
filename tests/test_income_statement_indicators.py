"""Unit tests for income statement indicator calculations."""

import pytest

from src.income_statement.indicators import IncomeStatementIndicators
from src.income_statement.models import IncomeStatementData


@pytest.fixture
def sample_data():
    return IncomeStatementData(
        total_revenue=1000000, cost_of_revenue=600000, gross_profit=400000,
        research_and_development=50000, selling_general_admin=100000,
        total_operating_expenses=750000, operating_income=250000,
        interest_expense=25000, income_before_tax=230000,
        income_tax_expense=46000, net_income=184000,
    )


class TestIncomeStatementIndicators:
    def test_gross_margin(self, sample_data):
        assert IncomeStatementIndicators(sample_data).gross_margin() == pytest.approx(40.0)

    def test_operating_margin(self, sample_data):
        assert IncomeStatementIndicators(sample_data).operating_margin() == pytest.approx(25.0)

    def test_net_margin(self, sample_data):
        assert IncomeStatementIndicators(sample_data).net_margin() == pytest.approx(18.4)

    def test_rd_to_revenue(self, sample_data):
        assert IncomeStatementIndicators(sample_data).rd_to_revenue() == pytest.approx(5.0)

    def test_sga_to_revenue(self, sample_data):
        assert IncomeStatementIndicators(sample_data).sga_to_revenue() == pytest.approx(10.0)

    def test_effective_tax_rate(self, sample_data):
        assert IncomeStatementIndicators(sample_data).effective_tax_rate() == pytest.approx(20.0)

    def test_interest_coverage(self, sample_data):
        assert IncomeStatementIndicators(sample_data).interest_coverage() == pytest.approx(10.0)

    def test_zero_revenue_returns_none(self):
        ind = IncomeStatementIndicators(IncomeStatementData(total_revenue=0))
        assert ind.gross_margin() is None
        assert ind.operating_margin() is None
        assert ind.net_margin() is None

    def test_gross_profit_check_valid(self, sample_data):
        ind = IncomeStatementIndicators(sample_data)
        assert ind.gross_profit_check() == 0.0
        assert ind.is_valid() is True

    def test_gross_profit_check_invalid(self):
        data = IncomeStatementData(total_revenue=1000000, cost_of_revenue=600000, gross_profit=300000)
        ind = IncomeStatementIndicators(data)
        assert ind.gross_profit_check() == 100000
        assert ind.is_valid() is False

    def test_summary_keys(self, sample_data):
        s = IncomeStatementIndicators(sample_data).summary()
        expected = {"gross_margin", "operating_margin", "net_margin", "rd_to_revenue", "sga_to_revenue", "effective_tax_rate", "interest_coverage", "gross_profit_check", "extraction_valid"}
        assert set(s.keys()) == expected
