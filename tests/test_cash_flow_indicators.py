"""Unit tests for cash flow indicator calculations."""

import pytest

from src.cash_flow.indicators import CashFlowIndicators
from src.cash_flow.models import CashFlowData


@pytest.fixture
def sample_data():
    return CashFlowData(
        net_income=184000, depreciation_amortization=50000, stock_based_compensation=20000,
        net_cash_from_operations=300000, capital_expenditures=-80000,
        net_cash_from_investing=-120000, debt_repaid=-50000,
        shares_repurchased=-30000, dividends_paid=-20000,
        net_cash_from_financing=-100000, net_change_in_cash=80000,
        cash_beginning_of_period=200000, cash_end_of_period=280000,
    )


class TestCashFlowIndicators:
    def test_free_cash_flow(self, sample_data):
        assert CashFlowIndicators(sample_data).free_cash_flow() == pytest.approx(220000)

    def test_operating_cash_flow_ratio(self, sample_data):
        assert CashFlowIndicators(sample_data).operating_cash_flow_ratio() == pytest.approx(300000 / 184000)

    def test_capex_to_ocf(self, sample_data):
        assert CashFlowIndicators(sample_data).capex_to_ocf() == pytest.approx(80000 / 300000 * 100)

    def test_debt_service_coverage(self, sample_data):
        assert CashFlowIndicators(sample_data).debt_service_coverage() == pytest.approx(300000 / 50000)

    def test_shareholder_return(self, sample_data):
        assert CashFlowIndicators(sample_data).shareholder_return() == pytest.approx(50000)

    def test_cash_reconciliation_valid(self, sample_data):
        ind = CashFlowIndicators(sample_data)
        assert ind.cash_reconciliation_check() == pytest.approx(0.0)
        assert ind.is_valid() is True

    def test_cash_reconciliation_invalid(self):
        data = CashFlowData(net_change_in_cash=80000, cash_beginning_of_period=200000, cash_end_of_period=300000)
        ind = CashFlowIndicators(data)
        assert ind.cash_reconciliation_check() == -20000
        assert ind.is_valid() is False

    def test_zero_net_income_returns_none(self):
        assert CashFlowIndicators(CashFlowData(net_income=0, net_cash_from_operations=100000)).operating_cash_flow_ratio() is None

    def test_summary_keys(self, sample_data):
        s = CashFlowIndicators(sample_data).summary()
        expected = {"free_cash_flow", "operating_cash_flow_ratio", "capex_to_ocf", "operating_pct", "debt_service_coverage", "shareholder_return", "cash_reconciliation_check", "extraction_valid"}
        assert set(s.keys()) == expected
