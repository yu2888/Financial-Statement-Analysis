"""Unit tests for balance sheet financial indicator calculations."""

import pytest

from src.balance_sheet.indicators import FinancialIndicators
from src.balance_sheet.models import BalanceSheetData


@pytest.fixture
def sample_data():
    return BalanceSheetData(
        cash_and_equivalents=50000, accounts_receivable=30000, marketable_securities=10000,
        inventory=20000, total_current_assets=110000, total_current_liabilities=80000,
        total_assets=500000, total_liabilities=300000, total_shareholders_equity=200000,
        long_term_debt=100000,
    )


class TestFinancialIndicators:
    def test_current_ratio(self, sample_data):
        assert FinancialIndicators(sample_data).current_ratio() == pytest.approx(110000 / 80000)

    def test_current_ratio_zero_liabilities(self):
        data = BalanceSheetData(total_current_assets=100, total_current_liabilities=0)
        assert FinancialIndicators(data).current_ratio() is None

    def test_quick_ratio(self, sample_data):
        assert FinancialIndicators(sample_data).quick_ratio() == pytest.approx((50000 + 10000 + 30000) / 80000)

    def test_debt_to_equity(self, sample_data):
        assert FinancialIndicators(sample_data).debt_to_equity() == pytest.approx(300000 / 200000)

    def test_debt_to_equity_zero_equity(self):
        data = BalanceSheetData(total_liabilities=100, total_shareholders_equity=0)
        assert FinancialIndicators(data).debt_to_equity() is None

    def test_working_capital(self, sample_data):
        assert FinancialIndicators(sample_data).working_capital() == 30000

    def test_accounting_equation_valid(self, sample_data):
        ind = FinancialIndicators(sample_data)
        assert ind.accounting_equation_check() == 0.0
        assert ind.is_valid() is True

    def test_accounting_equation_invalid(self):
        data = BalanceSheetData(total_assets=500000, total_liabilities=300000, total_shareholders_equity=100000)
        ind = FinancialIndicators(data)
        assert ind.accounting_equation_check() == 100000
        assert ind.is_valid() is False

    def test_summary_keys(self, sample_data):
        s = FinancialIndicators(sample_data).summary()
        expected_keys = {
            "current_ratio", "quick_ratio", "debt_to_equity", "working_capital",
            "accounting_equation_discrepancy", "extraction_valid", "cash_ratio",
            "equity_ratio", "debt_ratio", "net_debt", "tangible_book_value",
            "current_asset_pct", "non_current_asset_pct",
        }
        assert set(s.keys()) == expected_keys
