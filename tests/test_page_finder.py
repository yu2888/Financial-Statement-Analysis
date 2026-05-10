"""Tests for balance sheet page detection — uses real 10-K PDFs."""

from pathlib import Path

import pytest

from src.balance_sheet.page_finder import find_balance_sheet_page, score_page

DATA_DIR = Path("data")
PDFS = sorted(DATA_DIR.glob("*.pdf")) if DATA_DIR.exists() else []


@pytest.mark.parametrize("pdf_path", PDFS, ids=[p.name for p in PDFS])
class TestFindBalanceSheetPage:
    def test_finds_page(self, pdf_path):
        result = find_balance_sheet_page(str(pdf_path))
        assert result.score > 0
        assert result.page_num >= 0

    def test_has_title_hit(self, pdf_path):
        result = find_balance_sheet_page(str(pdf_path))
        assert len(result.title_hits) > 0, "Expected at least one balance sheet title phrase"

    def test_has_keyword_hits(self, pdf_path):
        result = find_balance_sheet_page(str(pdf_path))
        total_hits = len(result.title_hits) + len(result.keyword_hits)
        assert total_hits >= 3, "Expected several balance sheet signal phrases"



class TestScorePageEdgeCases:
    def test_empty_page(self):
        assert score_page("", 0).score == 0

    def test_title_weight_dominates(self):
        assert score_page("Consolidated Balance Sheets", 0).score >= 10

    def test_income_statement_not_confused(self):
        text = "CONSOLIDATED STATEMENTS OF OPERATIONS\nNet income per share\nCost of revenue\nGross profit\nEarnings per share\nDiluted earnings per share"
        result = score_page(text, 3)
        assert result.score < 0
        assert len(result.title_hits) == 0
