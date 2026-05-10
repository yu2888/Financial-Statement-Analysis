"""Property-based test for consolidated output bug in web server mode.

This test demonstrates the bug condition where run_extraction() in web/server.py
does not save consolidated.json and consolidated.md files when all three
statements complete successfully.

**Validates: Requirements 2.1**

Bug Condition:
- mode == "web_server"
- all_statements_succeeded == true
- consolidated.json does NOT exist
- consolidated.md does NOT exist

Expected Behavior:
- Both consolidated.json and consolidated.md should exist after successful extraction
"""

import tempfile
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis.strategies import text, sampled_from

from web.models import AnalysisRecord, StatementResult, StatementStatusEnum, ConsolidatedResult


# Valid statement types
STATEMENT_TYPES = ["balance_sheet", "income_statement", "cash_flow"]


def create_successful_statement_result() -> dict:
    """Create a minimal successful statement result for testing."""
    return {
        "current_period": {
            "company_name": "TestCorp",
            "period": "Dec 31, 2024",
            "currency": "USD",
            "total_assets": 500000.0,
            "total_liabilities": 300000.0,
            "total_shareholders_equity": 200000.0,
            "cash_and_equivalents": 50000.0,
            "total_current_assets": 110000.0,
            "total_current_liabilities": 80000.0,
        },
        "prior_period": None,
        "indicators": {
            "current_ratio": 1.375,
            "quick_ratio": 0.625,
            "debt_to_equity": 1.5,
            "cash_ratio": 0.625,
            "equity_ratio": 0.4,
            "debt_ratio": 0.6,
            "working_capital": 30000.0,
        },
        "page_num": 1,
    }


def create_balance_sheet_result() -> dict:
    """Create a balance sheet result for testing."""
    return {
        "current_period": {
            "company_name": "TestCorp",
            "period": "Dec 31, 2024",
            "currency": "USD",
            "total_assets": 500000.0,
            "total_liabilities": 300000.0,
            "total_shareholders_equity": 200000.0,
            "cash_and_equivalents": 50000.0,
            "total_current_assets": 110000.0,
            "total_current_liabilities": 80000.0,
            "short_term_debt": 20000.0,
            "long_term_debt": 100000.0,
        },
        "prior_period": None,
        "indicators": {
            "current_ratio": 1.375,
            "quick_ratio": 0.625,
            "debt_to_equity": 1.5,
            "cash_ratio": 0.625,
            "equity_ratio": 0.4,
            "debt_ratio": 0.6,
            "working_capital": 30000.0,
        },
        "page_num": 1,
    }


def create_income_statement_result() -> dict:
    """Create an income statement result for testing."""
    return {
        "current_period": {
            "company_name": "TestCorp",
            "period": "Dec 31, 2024",
            "currency": "USD",
            "total_revenue": 1000000.0,
            "gross_profit": 400000.0,
            "operating_income": 200000.0,
            "net_income": 150000.0,
            "interest_expense": 10000.0,
        },
        "prior_period": None,
        "indicators": {
            "gross_margin": 40.0,
            "operating_margin": 20.0,
            "net_margin": 15.0,
        },
        "page_num": 2,
    }


def create_cash_flow_result() -> dict:
    """Create a cash flow result for testing."""
    return {
        "current_period": {
            "company_name": "TestCorp",
            "period": "Dec 31, 2024",
            "currency": "USD",
            "net_cash_from_operations": 200000.0,
            "net_cash_from_investing": -50000.0,
            "net_cash_from_financing": -30000.0,
            "depreciation_amortization": 25000.0,
            "capital_expenditures": 40000.0,
        },
        "prior_period": None,
        "indicators": {
            "free_cash_flow": 160000.0,
            "operating_cash_flow_ratio": 1.33,
            "capex_to_ocf": 20.0,
        },
        "page_num": 3,
    }


class TestConsolidatedOutputBugCondition:
    """
    Bug Condition Exploration Test for Web Server Missing Consolidated Output.
    
    This test demonstrates the bug where run_extraction() builds the consolidated
    result in-memory but never saves consolidated.json or consolidated.md to disk.
    
    **Expected Outcome on UNFIXED code**: Test FAILS (proves bug exists)
    **Expected Outcome on FIXED code**: Test PASSES (confirms bug is fixed)
    """

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_pdf_dir(self):
        """Create a temporary directory with a minimal PDF for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a minimal PDF file (just for path existence)
            pdf_path = Path(tmpdir) / "test.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n")  # Minimal PDF header
            yield Path(tmpdir)

    def test_consolidated_files_created_on_successful_extraction(
        self, temp_output_dir, temp_pdf_dir
    ):
        """
        **Property 1: Bug Condition - Web Server Missing Consolidated Output**
        
        WHEN running the web server and all three statements complete successfully,
        THEN the system SHALL save both consolidated.json and consolidated.md to
        the output directory.
        
        **Validates: Requirements 2.1**
        
        This test should:
        - FAIL on unfixed code (bug exists - consolidated files not saved)
        - PASS on fixed code (bug fixed - consolidated files saved)
        """
        # Arrange: Set up the analysis record with all statements completed
        analysis_id = "test-analysis-123"
        pdf_stem = "test-company"
        pdf_path = str(temp_pdf_dir / "test.pdf")
        
        record = AnalysisRecord(
            analysis_id=analysis_id,
            filename="test.pdf",
            status=StatementStatusEnum.processing,
            statements={
                "balance_sheet": StatementResult(
                    status=StatementStatusEnum.completed,
                    page_num=1,
                    result=create_balance_sheet_result(),
                ),
                "income_statement": StatementResult(
                    status=StatementStatusEnum.completed,
                    page_num=2,
                    result=create_income_statement_result(),
                ),
                "cash_flow": StatementResult(
                    status=StatementStatusEnum.completed,
                    page_num=3,
                    result=create_cash_flow_result(),
                ),
            },
            consolidated=ConsolidatedResult(status=StatementStatusEnum.pending),
            pdf_path=pdf_path,
            pdf_stem=pdf_stem,
        )
        
        # Set up the output directory path
        pdf_output_dir = temp_output_dir / pdf_stem
        pdf_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Mock the analyses dict and required functions
        with patch("web.server.analyses", {analysis_id: record}):
            with patch("web.server.load_config") as mock_config:
                mock_config.return_value = MagicMock(
                    model="test-model",
                    base_url="http://localhost",
                    api_key="test-key"
                )
                
                # Mock extraction functions to return successful results
                with patch("web.server.find_balance_sheet_page") as mock_bs_find:
                    with patch("web.server.find_income_statement_page") as mock_is_find:
                        with patch("web.server.find_cash_flow_page") as mock_cf_find:
                            with patch("web.server.pdf_page_to_image") as mock_img:
                                with patch("web.server.extract_multi_period_from_image") as mock_bs_extract:
                                    with patch("web.server.extract_income_statement_from_image") as mock_is_extract:
                                        with patch("web.server.extract_cash_flow_from_image") as mock_cf_extract:
                                            # Set up mocks
                                            mock_bs_find.return_value = MagicMock(page_num=1, score=0.9)
                                            mock_is_find.return_value = MagicMock(page_num=2, score=0.9)
                                            mock_cf_find.return_value = MagicMock(page_num=3, score=0.9)
                                            mock_img.return_value = MagicMock()
                                            
                                            # Create mock results with proper structure
                                            from src.balance_sheet.models import BalanceSheetData, MultiPeriodResult
                                            from src.income_statement.models import IncomeStatementData, IncomeStatementMultiPeriod
                                            from src.cash_flow.models import CashFlowData, CashFlowMultiPeriod
                                            
                                            bs_data = BalanceSheetData(
                                                company_name="TestCorp",
                                                period="Dec 31, 2024",
                                                currency="USD",
                                                total_assets=500000.0,
                                                total_liabilities=300000.0,
                                                total_shareholders_equity=200000.0,
                                                cash_and_equivalents=50000.0,
                                                total_current_assets=110000.0,
                                                total_current_liabilities=80000.0,
                                                short_term_debt=20000.0,
                                                long_term_debt=100000.0,
                                            )
                                            mock_bs_extract.return_value = MultiPeriodResult(current_period=bs_data)
                                            
                                            is_data = IncomeStatementData(
                                                company_name="TestCorp",
                                                period="Dec 31, 2024",
                                                currency="USD",
                                                total_revenue=1000000.0,
                                                gross_profit=400000.0,
                                                operating_income=200000.0,
                                                net_income=150000.0,
                                                interest_expense=10000.0,
                                            )
                                            mock_is_extract.return_value = IncomeStatementMultiPeriod(current_period=is_data)
                                            
                                            cf_data = CashFlowData(
                                                company_name="TestCorp",
                                                period="Dec 31, 2024",
                                                currency="USD",
                                                net_cash_from_operations=200000.0,
                                                net_cash_from_investing=-50000.0,
                                                net_cash_from_financing=-30000.0,
                                                depreciation_amortization=25000.0,
                                                capital_expenditures=40000.0,
                                            )
                                            mock_cf_extract.return_value = CashFlowMultiPeriod(current_period=cf_data)
                                            
                                            # Mock save_statement_result to save to temp dir
                                            def mock_save_statement(pdf_stem, stmt_type, result):
                                                out_path = temp_output_dir / pdf_stem / f"{stmt_type}.json"
                                                out_path.parent.mkdir(parents=True, exist_ok=True)
                                                import json
                                                out_path.write_text(json.dumps(result))
                                            
                                            with patch("web.server.save_statement_result", side_effect=mock_save_statement):
                                                with patch("web.server.OUTPUT_DIR", temp_output_dir):
                                                    # Act: Run the extraction
                                                    from web.server import run_extraction
                                                    run_extraction(analysis_id)
                                                    
                                                    # Assert: Check consolidated status completed
                                                    assert record.consolidated.status == StatementStatusEnum.completed, \
                                                        "Consolidated status should be completed when all statements succeed"
                                                    
                                                    # Assert: Check consolidated files exist
                                                    # THIS IS THE BUG - on unfixed code, these files will NOT exist
                                                    consolidated_json_path = temp_output_dir / pdf_stem / "consolidated.json"
                                                    consolidated_md_path = temp_output_dir / pdf_stem / "consolidated.md"
                                                    
                                                    # BUG CONDITION: These assertions will FAIL on unfixed code
                                                    assert consolidated_json_path.exists(), \
                                                        f"BUG: consolidated.json should exist at {consolidated_json_path} but was not saved by run_extraction()"
                                                    
                                                    assert consolidated_md_path.exists(), \
                                                        f"BUG: consolidated.md should exist at {consolidated_md_path} but was not saved by run_extraction()"
                                                    
                                                    # Verify files are not empty
                                                    if consolidated_json_path.exists():
                                                        import json
                                                        data = json.loads(consolidated_json_path.read_text())
                                                        assert "balance_sheet" in data
                                                        assert "income_statement" in data
                                                        assert "cash_flow" in data
                                                    
                                                    if consolidated_md_path.exists():
                                                        content = consolidated_md_path.read_text(encoding="utf-8")
                                                        assert "Consolidated Financial Analysis" in content

    def test_consolidated_not_created_on_partial_failure(
        self, temp_output_dir, temp_pdf_dir
    ):
        """
        **Preservation Test: Partial Failure Handling**
        
        WHEN running the web server and one or more statements fail,
        THEN the system SHALL NOT save consolidated files and SHALL
        mark consolidated status as error.
        
        **Validates: Requirements 3.1**
        """
        # Arrange: Set up the analysis record with one statement failed
        analysis_id = "test-analysis-partial"
        pdf_stem = "test-partial"
        pdf_path = str(temp_pdf_dir / "test.pdf")
        
        record = AnalysisRecord(
            analysis_id=analysis_id,
            filename="test.pdf",
            status=StatementStatusEnum.processing,
            statements={
                "balance_sheet": StatementResult(
                    status=StatementStatusEnum.completed,
                    page_num=1,
                    result=create_balance_sheet_result(),
                ),
                "income_statement": StatementResult(
                    status=StatementStatusEnum.error,
                    error="Extraction failed",
                ),
                "cash_flow": StatementResult(
                    status=StatementStatusEnum.completed,
                    page_num=3,
                    result=create_cash_flow_result(),
                ),
            },
            consolidated=ConsolidatedResult(status=StatementStatusEnum.pending),
            pdf_path=pdf_path,
            pdf_stem=pdf_stem,
        )
        
        # Set up the output directory path
        pdf_output_dir = temp_output_dir / pdf_stem
        pdf_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Mock the analyses dict
        with patch("web.server.analyses", {analysis_id: record}):
            with patch("web.server.load_config") as mock_config:
                mock_config.return_value = MagicMock(
                    model="test-model",
                    base_url="http://localhost",
                    api_key="test-key"
                )
                
                # Mock only the balance sheet extraction (income statement will fail)
                with patch("web.server.find_balance_sheet_page") as mock_bs_find:
                    with patch("web.server.find_cash_flow_page") as mock_cf_find:
                        with patch("web.server.pdf_page_to_image") as mock_img:
                            with patch("web.server.extract_multi_period_from_image") as mock_bs_extract:
                                with patch("web.server.extract_cash_flow_from_image") as mock_cf_extract:
                                    with patch("web.server.find_income_statement_page") as mock_is_find:
                                        # Income statement extraction will fail
                                        mock_is_find.side_effect = ValueError("Page not found")
                                        
                                        mock_bs_find.return_value = MagicMock(page_num=1, score=0.9)
                                        mock_cf_find.return_value = MagicMock(page_num=3, score=0.9)
                                        mock_img.return_value = MagicMock()
                                        
                                        from src.balance_sheet.models import BalanceSheetData, MultiPeriodResult
                                        from src.cash_flow.models import CashFlowData, CashFlowMultiPeriod
                                        
                                        bs_data = BalanceSheetData(
                                            company_name="TestCorp",
                                            period="Dec 31, 2024",
                                            currency="USD",
                                            total_assets=500000.0,
                                            total_liabilities=300000.0,
                                            total_shareholders_equity=200000.0,
                                        )
                                        mock_bs_extract.return_value = MultiPeriodResult(current_period=bs_data)
                                        
                                        cf_data = CashFlowData(
                                            company_name="TestCorp",
                                            period="Dec 31, 2024",
                                            currency="USD",
                                            net_cash_from_operations=200000.0,
                                            net_cash_from_investing=-50000.0,
                                            net_cash_from_financing=-30000.0,
                                            depreciation_amortization=25000.0,
                                            capital_expenditures=40000.0,
                                        )
                                        mock_cf_extract.return_value = CashFlowMultiPeriod(current_period=cf_data)
                                        
                                        def mock_save_statement(pdf_stem, stmt_type, result):
                                            out_path = temp_output_dir / pdf_stem / f"{stmt_type}.json"
                                            out_path.parent.mkdir(parents=True, exist_ok=True)
                                            import json
                                            out_path.write_text(json.dumps(result))
                                        
                                        with patch("web.server.save_statement_result", side_effect=mock_save_statement):
                                            with patch("web.server.OUTPUT_DIR", temp_output_dir):
                                                # Act
                                                from web.server import run_extraction
                                                run_extraction(analysis_id)
                                                
                                                # Assert: consolidated should be error
                                                assert record.consolidated.status == StatementStatusEnum.error, \
                                                    "Consolidated status should be error when any statement fails"
                                                
                                                # Assert: consolidated files should NOT exist
                                                consolidated_json_path = temp_output_dir / pdf_stem / "consolidated.json"
                                                consolidated_md_path = temp_output_dir / pdf_stem / "consolidated.md"
                                                
                                                assert not consolidated_json_path.exists(), \
                                                    "Consolidated JSON should NOT be created when statements fail"
                                                assert not consolidated_md_path.exists(), \
                                                    "Consolidated MD should NOT be created when statements fail"


# ============================================================================
# PRESERVATION PROPERTY TESTS (Task 2)
# ============================================================================
# These tests verify that existing behavior is preserved for non-buggy inputs.
# They should PASS on UNFIXED code, confirming baseline behavior to preserve.
# ============================================================================


class TestPreservationPartialFailure:
    """
    Preservation Test for Web Server Partial Failure Handling.
    
    WHEN running the web server and one or more statements fail,
    THEN the system SHALL CONTINUE TO mark consolidated status as error
    and NOT save consolidated files.
    
    **Validates: Requirements 3.1**
    
    **Expected Outcome on UNFIXED code**: Test PASSES (confirms baseline behavior)
    """

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_pdf_dir(self):
        """Create a temporary directory with a minimal PDF for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "test.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n")
            yield Path(tmpdir)

    @given(
        failing_statement=sampled_from(["balance_sheet", "income_statement", "cash_flow"])
    )
    @settings(max_examples=3, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    def test_consolidated_error_on_single_statement_failure(
        self, temp_output_dir, temp_pdf_dir, failing_statement
    ):
        """
        **Property: Preservation - Single Statement Failure**
        
        For any single statement failure, the consolidated status SHALL be
        marked as error and consolidated files SHALL NOT be created.
        
        **Validates: Requirements 3.1**
        """
        # Arrange: Set up the analysis record with one statement failed
        analysis_id = f"test-partial-{failing_statement}"
        pdf_stem = f"test-{failing_statement}"
        pdf_path = str(temp_pdf_dir / "test.pdf")
        
        # Create statements with one failing
        statements = {
            "balance_sheet": StatementResult(
                status=StatementStatusEnum.completed,
                page_num=1,
                result=create_balance_sheet_result(),
            ),
            "income_statement": StatementResult(
                status=StatementStatusEnum.completed,
                page_num=2,
                result=create_income_statement_result(),
            ),
            "cash_flow": StatementResult(
                status=StatementStatusEnum.completed,
                page_num=3,
                result=create_cash_flow_result(),
            ),
        }
        # Mark the failing statement
        statements[failing_statement] = StatementResult(
            status=StatementStatusEnum.error,
            error="Extraction failed",
        )
        
        record = AnalysisRecord(
            analysis_id=analysis_id,
            filename="test.pdf",
            status=StatementStatusEnum.processing,
            statements=statements,
            consolidated=ConsolidatedResult(status=StatementStatusEnum.pending),
            pdf_path=pdf_path,
            pdf_stem=pdf_stem,
        )
        
        # Set up the output directory path
        pdf_output_dir = temp_output_dir / pdf_stem
        pdf_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Mock the analyses dict
        with patch("web.server.analyses", {analysis_id: record}):
            with patch("web.server.load_config") as mock_config:
                mock_config.return_value = MagicMock(
                    model="test-model",
                    base_url="http://localhost",
                    api_key="test-key"
                )
                
                # Mock find functions for successful statements only
                with patch("web.server.find_balance_sheet_page") as mock_bs_find:
                    with patch("web.server.find_income_statement_page") as mock_is_find:
                        with patch("web.server.find_cash_flow_page") as mock_cf_find:
                            with patch("web.server.pdf_page_to_image") as mock_img:
                                with patch("web.server.extract_multi_period_from_image") as mock_bs_extract:
                                    with patch("web.server.extract_income_statement_from_image") as mock_is_extract:
                                        with patch("web.server.extract_cash_flow_from_image") as mock_cf_extract:
                                            # Make the failing statement's find function raise an error
                                            if failing_statement == "balance_sheet":
                                                mock_bs_find.side_effect = ValueError("Page not found")
                                            elif failing_statement == "income_statement":
                                                mock_is_find.side_effect = ValueError("Page not found")
                                            else:
                                                mock_cf_find.side_effect = ValueError("Page not found")
                                            
                                            # Set up successful mocks for other statements
                                            mock_bs_find.return_value = MagicMock(page_num=1, score=0.9)
                                            mock_is_find.return_value = MagicMock(page_num=2, score=0.9)
                                            mock_cf_find.return_value = MagicMock(page_num=3, score=0.9)
                                            mock_img.return_value = MagicMock()
                                            
                                            from src.balance_sheet.models import BalanceSheetData, MultiPeriodResult
                                            from src.income_statement.models import IncomeStatementData, IncomeStatementMultiPeriod
                                            from src.cash_flow.models import CashFlowData, CashFlowMultiPeriod
                                            
                                            bs_data = BalanceSheetData(
                                                company_name="TestCorp",
                                                period="Dec 31, 2024",
                                                currency="USD",
                                                total_assets=500000.0,
                                                total_liabilities=300000.0,
                                                total_shareholders_equity=200000.0,
                                            )
                                            mock_bs_extract.return_value = MultiPeriodResult(current_period=bs_data)
                                            
                                            is_data = IncomeStatementData(
                                                company_name="TestCorp",
                                                period="Dec 31, 2024",
                                                currency="USD",
                                                total_revenue=1000000.0,
                                                gross_profit=400000.0,
                                                operating_income=200000.0,
                                                net_income=150000.0,
                                                interest_expense=10000.0,
                                            )
                                            mock_is_extract.return_value = IncomeStatementMultiPeriod(current_period=is_data)
                                            
                                            cf_data = CashFlowData(
                                                company_name="TestCorp",
                                                period="Dec 31, 2024",
                                                currency="USD",
                                                net_cash_from_operations=200000.0,
                                                net_cash_from_investing=-50000.0,
                                                net_cash_from_financing=-30000.0,
                                                depreciation_amortization=25000.0,
                                                capital_expenditures=40000.0,
                                            )
                                            mock_cf_extract.return_value = CashFlowMultiPeriod(current_period=cf_data)
                                            
                                            def mock_save_statement(pdf_stem, stmt_type, result):
                                                out_path = temp_output_dir / pdf_stem / f"{stmt_type}.json"
                                                out_path.parent.mkdir(parents=True, exist_ok=True)
                                                import json
                                                out_path.write_text(json.dumps(result))
                                            
                                            with patch("web.server.save_statement_result", side_effect=mock_save_statement):
                                                with patch("web.server.OUTPUT_DIR", temp_output_dir):
                                                    # Act
                                                    from web.server import run_extraction
                                                    run_extraction(analysis_id)
                                                    
                                                    # Assert: consolidated should be error
                                                    assert record.consolidated.status == StatementStatusEnum.error, \
                                                        f"Consolidated status should be error when {failing_statement} fails"
                                                    
                                                    # Assert: consolidated files should NOT exist
                                                    consolidated_json_path = temp_output_dir / pdf_stem / "consolidated.json"
                                                    consolidated_md_path = temp_output_dir / pdf_stem / "consolidated.md"
                                                    
                                                    assert not consolidated_json_path.exists(), \
                                                        "Consolidated JSON should NOT be created when any statement fails"
                                                    assert not consolidated_md_path.exists(), \
                                                        "Consolidated MD should NOT be created when any statement fails"


class TestPreservationStatementCaching:
    """
    Preservation Test for Statement Caching Behavior.
    
    WHEN loading cached statement JSON files, the system SHALL CONTINUE TO
    use the cached result instead of re-extracting.
    
    **Validates: Requirements 3.4**
    
    **Expected Outcome on UNFIXED code**: Test PASSES (confirms baseline behavior)
    """

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_pdf_dir(self):
        """Create a temporary directory with a minimal PDF for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "test.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n")
            yield Path(tmpdir)

    @given(statement_type=sampled_from(["balance_sheet", "income_statement", "cash_flow"]))
    @settings(max_examples=3, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_cached_statement_used_without_re_extraction(
        self, temp_output_dir, temp_pdf_dir, statement_type
    ):
        """
        **Property: Preservation - Statement Caching**
        
        For any cached statement JSON file that exists, the system SHALL
        use the cached result instead of re-extracting.
        
        **Validates: Requirements 3.4**
        """
        # Arrange: Set up cached statement file
        analysis_id = f"test-cached-{statement_type}"
        pdf_stem = f"test-cached-{statement_type}"
        pdf_path = str(temp_pdf_dir / "test.pdf")
        
        # Create the output directory with a cached statement file
        pdf_output_dir = temp_output_dir / pdf_stem
        pdf_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create cached statement JSON
        cached_result = {
            "current_period": {
                "company_name": "CachedCorp",
                "period": "Dec 31, 2024",
                "currency": "USD",
                "total_assets": 999999.0,  # Unique value to verify cache is used
                "total_liabilities": 500000.0,
                "total_shareholders_equity": 499999.0,
            },
            "prior_period": None,
            "indicators": {
                "current_ratio": 2.0,
                "quick_ratio": 1.0,
                "debt_to_equity": 1.0,
                "cash_ratio": 0.5,
                "equity_ratio": 0.5,
                "debt_ratio": 0.5,
                "working_capital": 100000.0,
            },
            "page_num": 42,  # Unique value to verify cache is used
        }
        
        if statement_type == "balance_sheet":
            cached_path = pdf_output_dir / "balance_sheet.json"
            cached_path.write_text(json.dumps(cached_result))
        elif statement_type == "income_statement":
            cached_result["current_period"] = {
                "company_name": "CachedCorp",
                "period": "Dec 31, 2024",
                "currency": "USD",
                "total_revenue": 888888.0,
                "gross_profit": 400000.0,
                "operating_income": 200000.0,
                "net_income": 150000.0,
                "interest_expense": 10000.0,
            }
            cached_result["indicators"] = {
                "gross_margin": 40.0,
                "operating_margin": 20.0,
                "net_margin": 15.0,
            }
            cached_path = pdf_output_dir / "income_statement.json"
            cached_path.write_text(json.dumps(cached_result))
        else:  # cash_flow
            cached_result["current_period"] = {
                "company_name": "CachedCorp",
                "period": "Dec 31, 2024",
                "currency": "USD",
                "net_cash_from_operations": 777777.0,
                "net_cash_from_investing": -50000.0,
                "net_cash_from_financing": -30000.0,
                "depreciation_amortization": 25000.0,
                "capital_expenditures": 40000.0,
            }
            cached_result["indicators"] = {
                "free_cash_flow": 160000.0,
                "operating_cash_flow_ratio": 1.33,
                "capex_to_ocf": 20.0,
            }
            cached_path = pdf_output_dir / "cash_flow.json"
            cached_path.write_text(json.dumps(cached_result))
        
        # Create the analysis record
        record = AnalysisRecord(
            analysis_id=analysis_id,
            filename="test.pdf",
            status=StatementStatusEnum.processing,
            statements={
                "balance_sheet": StatementResult(),
                "income_statement": StatementResult(),
                "cash_flow": StatementResult(),
            },
            consolidated=ConsolidatedResult(status=StatementStatusEnum.pending),
            pdf_path=pdf_path,
            pdf_stem=pdf_stem,
        )
        
        # Mock the analyses dict
        with patch("web.server.analyses", {analysis_id: record}):
            with patch("web.server.load_config") as mock_config:
                mock_config.return_value = MagicMock(
                    model="test-model",
                    base_url="http://localhost",
                    api_key="test-key"
                )
                
                # Mock extraction functions - these should NOT be called for cached statement
                with patch("web.server.find_balance_sheet_page") as mock_bs_find:
                    with patch("web.server.find_income_statement_page") as mock_is_find:
                        with patch("web.server.find_cash_flow_page") as mock_cf_find:
                            with patch("web.server.pdf_page_to_image") as mock_img:
                                with patch("web.server.extract_multi_period_from_image") as mock_bs_extract:
                                    with patch("web.server.extract_income_statement_from_image") as mock_is_extract:
                                        with patch("web.server.extract_cash_flow_from_image") as mock_cf_extract:
                                            with patch("web.server.OUTPUT_DIR", temp_output_dir):
                                                # Act
                                                from web.server import run_extraction
                                                run_extraction(analysis_id)
                                                
                                                # Assert: The cached statement should be marked as cached
                                                assert record.statements[statement_type].cached == True, \
                                                    f"{statement_type} should be marked as cached when loaded from cache"
                                                
                                                # Assert: The cached statement should be completed
                                                assert record.statements[statement_type].status == StatementStatusEnum.completed, \
                                                    f"{statement_type} should be completed when loaded from cache"
                                                
                                                # Assert: The page_num should match the cached value
                                                assert record.statements[statement_type].page_num == 42, \
                                                    f"{statement_type} page_num should match cached value (42)"
                                                
                                                # Assert: The extraction functions should NOT have been called
                                                # for the cached statement type
                                                if statement_type == "balance_sheet":
                                                    mock_bs_find.assert_not_called()
                                                    mock_bs_extract.assert_not_called()
                                                elif statement_type == "income_statement":
                                                    mock_is_find.assert_not_called()
                                                    mock_is_extract.assert_not_called()
                                                else:
                                                    mock_cf_find.assert_not_called()
                                                    mock_cf_extract.assert_not_called()


class TestPreservationCLIMode:
    """
    Preservation Test for CLI Mode Operation.
    
    WHEN running CLI mode and all statements succeed, the system SHALL
    CONTINUE TO save individual statement JSON and MD files.
    
    **Validates: Requirements 3.2**
    
    **Expected Outcome on UNFIXED code**: Test PASSES (confirms baseline behavior)
    """

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_pdf_dir(self):
        """Create a temporary directory with a minimal PDF for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "test.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n")
            yield Path(tmpdir)

    @given(
        company_name=sampled_from(["TestCorp", "AcmeInc", "FinanceCo", "DataCorp"]),
    )
    @settings(max_examples=3, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_cli_mode_saves_all_statement_files(
        self, temp_output_dir, temp_pdf_dir, company_name
    ):
        """
        **Property: Preservation - CLI Mode File Saving**
        
        For any PDF processed via CLI mode where all statements succeed,
        the system SHALL save individual JSON and MD files for each statement
        plus consolidated files.
        
        **Validates: Requirements 3.2**
        """
        # Note: This test verifies the observed behavior of CLI mode.
        # We test the process_pdf function from main.py indirectly by
        # testing the save functions that it calls.
        
        # Arrange: Create mock statement results
        from src.balance_sheet.models import BalanceSheetData, MultiPeriodResult
        from src.income_statement.models import IncomeStatementData, IncomeStatementMultiPeriod
        from src.cash_flow.models import CashFlowData, CashFlowMultiPeriod
        from src.consolidated.models import FullFinancialResult
        from src.balance_sheet.report import save_json, save_report
        from src.income_statement.report import save_income_statement_json, save_income_statement_report
        from src.cash_flow.report import save_cash_flow_json, save_cash_flow_report
        from src.consolidated.report import save_consolidated_json, save_consolidated_report
        
        pdf_stem = f"test-cli-{company_name.replace(' ', '-')}"
        pdf_output_dir = temp_output_dir / pdf_stem
        pdf_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create mock data
        bs_data = BalanceSheetData(
            company_name=company_name,
            period="Dec 31, 2024",
            currency="USD",
            total_assets=500000.0,
            total_liabilities=300000.0,
            total_shareholders_equity=200000.0,
            cash_and_equivalents=50000.0,
            total_current_assets=110000.0,
            total_current_liabilities=80000.0,
        )
        bs_result = MultiPeriodResult(current_period=bs_data)
        
        is_data = IncomeStatementData(
            company_name=company_name,
            period="Dec 31, 2024",
            currency="USD",
            total_revenue=1000000.0,
            gross_profit=400000.0,
            operating_income=200000.0,
            net_income=150000.0,
            interest_expense=10000.0,
        )
        is_result = IncomeStatementMultiPeriod(current_period=is_data)
        
        cf_data = CashFlowData(
            company_name=company_name,
            period="Dec 31, 2024",
            currency="USD",
            net_cash_from_operations=200000.0,
            net_cash_from_investing=-50000.0,
            net_cash_from_financing=-30000.0,
            depreciation_amortization=25000.0,
            capital_expenditures=40000.0,
        )
        cf_result = CashFlowMultiPeriod(current_period=cf_data)
        
        # Act: Save all files as CLI mode does
        save_json(bs_result, pdf_output_dir / "balance_sheet.json", page_num=1)
        save_report(bs_result, pdf_output_dir / "balance_sheet.md")
        save_income_statement_json(is_result, pdf_output_dir / "income_statement.json", page_num=2)
        save_income_statement_report(is_result, pdf_output_dir / "income_statement.md")
        save_cash_flow_json(cf_result, pdf_output_dir / "cash_flow.json", page_num=3)
        save_cash_flow_report(cf_result, pdf_output_dir / "cash_flow.md")
        
        full = FullFinancialResult(balance_sheet=bs_result, income_statement=is_result, cash_flow=cf_result)
        save_consolidated_json(full, pdf_output_dir / "consolidated.json")
        save_consolidated_report(full, pdf_output_dir / "consolidated.md")
        
        # Assert: All files should exist
        expected_files = [
            "balance_sheet.json",
            "balance_sheet.md",
            "income_statement.json",
            "income_statement.md",
            "cash_flow.json",
            "cash_flow.md",
            "consolidated.json",
            "consolidated.md",
        ]
        
        for filename in expected_files:
            file_path = pdf_output_dir / filename
            assert file_path.exists(), f"CLI mode should save {filename}"
            assert file_path.stat().st_size > 0, f"{filename} should not be empty"
        
        # Assert: JSON files have valid structure
        bs_json = json.loads((pdf_output_dir / "balance_sheet.json").read_text())
        assert "current_period" in bs_json
        assert "indicators" in bs_json
        assert bs_json["current_period"]["company_name"] == company_name
        
        is_json = json.loads((pdf_output_dir / "income_statement.json").read_text())
        assert "current_period" in is_json
        assert "indicators" in is_json
        
        cf_json = json.loads((pdf_output_dir / "cash_flow.json").read_text())
        assert "current_period" in cf_json
        assert "indicators" in cf_json
        
        consolidated_json = json.loads((pdf_output_dir / "consolidated.json").read_text())
        assert "balance_sheet" in consolidated_json
        assert "income_statement" in consolidated_json
        assert "cash_flow" in consolidated_json
        
        # Assert: MD files have content
        bs_md = (pdf_output_dir / "balance_sheet.md").read_text(encoding="utf-8")
        assert "Balance Sheet Analysis" in bs_md
        assert company_name in bs_md
        
        consolidated_md = (pdf_output_dir / "consolidated.md").read_text(encoding="utf-8")
        assert "Consolidated Financial Analysis" in consolidated_md
