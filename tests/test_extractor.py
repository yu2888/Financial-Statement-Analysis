"""Unit tests for JSON parsing logic in the shared LLM module."""

import pytest

from src.shared.llm import parse_json_response


class TestParseJsonResponse:
    def test_clean_json(self):
        result = parse_json_response('{"cash_and_equivalents": 100.0, "total_assets": 500.0}')
        assert result["cash_and_equivalents"] == 100.0

    def test_markdown_fenced_json(self):
        assert parse_json_response('```json\n{"total_assets": 500.0}\n```')["total_assets"] == 500.0

    def test_markdown_fenced_no_lang(self):
        assert parse_json_response('```\n{"total_assets": 500.0}\n```')["total_assets"] == 500.0

    def test_json_with_surrounding_text(self):
        assert parse_json_response('Here is the data:\n{"total_assets": 500.0}\nHope this helps!')["total_assets"] == 500.0

    def test_whitespace_padded(self):
        assert parse_json_response('  \n  {"total_assets": 500.0}  \n  ')["total_assets"] == 500.0

    def test_no_json_raises(self):
        with pytest.raises(ValueError, match="No valid JSON"):
            parse_json_response("This is not JSON at all")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            parse_json_response("")
