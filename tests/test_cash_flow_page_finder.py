"""Tests for cash flow page detection — uses real 10-K PDFs."""

from pathlib import Path

import pytest

from src.cash_flow.page_finder import find_cash_flow_page, score_cash_flow_page

DATA_DIR = Path("data")
PDFS = sorted(DATA_DIR.glob("*.pdf")) if DATA_DIR.exists() else []


@pytest.mark.parametrize("pdf_path", PDFS, ids=[p.name for p in PDFS])
class TestFindCashFlowPage:
    def test_finds_page(self, pdf_path):
        result = find_cash_flow_page(str(pdf_path))
        assert result.score > 0
        assert result.page_num >= 0

    def test_has_title_hit(self, pdf_path):
        result = find_cash_flow_page(str(pdf_path))
        assert len(result.title_hits) > 0, "Expected at least one cash flow title phrase"

    def test_has_keyword_hits(self, pdf_path):
        result = find_cash_flow_page(str(pdf_path))
        total_hits = len(result.title_hits) + len(result.keyword_hits)
        assert total_hits >= 2, "Expected at least a couple of cash flow signal phrases"


class TestScoreCashFlowEdgeCases:
    def test_empty_page(self):
        assert score_cash_flow_page("", 0).score == 0

    def test_title_weight_dominates(self):
        assert score_cash_flow_page("Consolidated Statements of Cash Flows", 0).score >= 10

    def test_balance_sheet_page_penalized(self):
        text = "CONSOLIDATED BALANCE SHEETS\nTotal Assets  500,000\nTotal Liabilities  300,000\nStockholders' Equity  200,000"
        assert len(score_cash_flow_page(text, 3).negative_hits) >= 2
