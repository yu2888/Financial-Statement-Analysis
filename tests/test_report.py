"""Unit tests for balance sheet report generation."""

import json
from pathlib import Path

import pytest

from src.balance_sheet.models import BalanceSheetData, MultiPeriodResult
from src.balance_sheet.report import save_json, save_report
from src.shared.formatting import fmt


@pytest.fixture
def sample_data():
    return BalanceSheetData(
        cash_and_equivalents=50000, total_current_assets=110000, total_assets=500000,
        total_current_liabilities=80000, total_liabilities=300000, total_shareholders_equity=200000,
        company_name="TestCorp", period="Dec 31, 2024", currency="USD",
    )


@pytest.fixture
def sample_result(sample_data):
    return MultiPeriodResult(current_period=sample_data)


class TestFmt:
    def test_formats_number(self):
        assert fmt(1234.5) == "1,234.50"

    def test_none_returns_na(self):
        assert fmt(None) == "N/A"

    def test_zero(self):
        assert fmt(0.0) == "0.00"


class TestSaveJson:
    def test_creates_json_file(self, tmp_path, sample_result):
        out = tmp_path / "test.json"
        result = save_json(sample_result, out)
        assert result == out
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["current_period"]["company_name"] == "TestCorp"
        assert data["current_period"]["total_assets"] == 500000

    def test_creates_parent_dirs(self, tmp_path, sample_result):
        out = tmp_path / "nested" / "dir" / "test.json"
        save_json(sample_result, out)
        assert out.exists()


class TestSaveReport:
    def test_creates_md_file(self, tmp_path, sample_result):
        out = tmp_path / "test.md"
        result = save_report(sample_result, out)
        assert result == out
        content = out.read_text(encoding="utf-8")
        assert "TestCorp" in content
        assert "PASS" in content

    def test_fail_status_on_discrepancy(self, tmp_path):
        data = BalanceSheetData(total_assets=500000, total_liabilities=300000, total_shareholders_equity=100000, company_name="BadCorp")
        result = MultiPeriodResult(current_period=data)
        out = tmp_path / "test.md"
        save_report(result, out)
        assert "FAIL" in out.read_text(encoding="utf-8")
