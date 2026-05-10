"""FastAPI backend for the Financial Analysis Web UI.

Serves the static frontend, accepts PDF uploads, runs the extraction pipeline
in a background thread, and exposes results via REST API.
"""

import json
import logging
import shutil
import tempfile
import threading
import uuid
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
import uvicorn

from src.shared.config import load_config
from src.shared.llm import pdf_page_to_image, image_to_base64
from src.balance_sheet.page_finder import find_balance_sheet_page
from src.balance_sheet.extractor import extract_multi_period_from_image
from src.balance_sheet.indicators import FinancialIndicators, YoYComparison
from src.income_statement.page_finder import find_income_statement_page
from src.income_statement.extractor import extract_income_statement_from_image
from src.income_statement.indicators import IncomeStatementIndicators, IncomeStatementYoY
from src.cash_flow.page_finder import find_cash_flow_page
from src.cash_flow.extractor import extract_cash_flow_from_image
from src.cash_flow.indicators import CashFlowIndicators, CashFlowYoY
from src.consolidated.report import _cross_statement_indicators, save_consolidated_json, save_consolidated_report
from src.consolidated.models import FullFinancialResult
from src.balance_sheet.models import BalanceSheetData, MultiPeriodResult as BSResult
from src.income_statement.models import IncomeStatementData, IncomeStatementMultiPeriod as ISResult
from src.cash_flow.models import CashFlowData, CashFlowMultiPeriod as CFResult

from web.models import (
    AnalysisItem,
    AnalysisListResponse,
    AnalysisRecord,
    ConsolidatedResult,
    RenameRequest,
    RenameResponse,
    StatementResult,
    StatementStatusEnum,
)

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# Directory paths for caching
OUTPUT_DIR = Path(__file__).parent.parent / "output"
DATA_DIR = Path(__file__).parent.parent / "data"

app = FastAPI(title="Financial Analysis Dashboard")

# In-memory store for analysis records
analyses: dict[str, AnalysisRecord] = {}


# ---------------------------------------------------------------------------
# Caching Helper Functions
# ---------------------------------------------------------------------------


def get_pdf_stem(filename: str) -> str:
    """Extract the base filename without .pdf extension.

    Args:
        filename: The PDF filename (e.g., "amz-10k.pdf")

    Returns:
        The stem of the filename (e.g., "amz-10k")

    Requirements: 1.1
    """
    return Path(filename).stem


def validate_statement_json(data: dict) -> bool:
    """Validate cached JSON has required keys: current_period, indicators.

    Args:
        data: The parsed JSON data to validate

    Returns:
        True if data has all required keys, False otherwise

    Requirements: 1.4
    """
    required_keys = {"current_period", "indicators"}
    return required_keys.issubset(data.keys())


def load_cached_statement(pdf_stem: str, statement_type: str) -> dict | None:
    """Load cached JSON from output/{pdf_stem}/{statement_type}.json.

    Args:
        pdf_stem: The PDF filename stem (e.g., "amz-10k")
        statement_type: The statement type (e.g., "balance_sheet")

    Returns:
        The cached JSON data if valid, None if file missing or invalid

    Requirements: 1.3, 1.4
    """
    path = OUTPUT_DIR / pdf_stem / f"{statement_type}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        if validate_statement_json(data):
            return data
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def get_cached_page_num(pdf_stem: str, statement_type: str) -> int | None:
    """Get the page_num from cached JSON if available.

    Args:
        pdf_stem: The PDF filename stem (e.g., "amz-10k")
        statement_type: The statement type (e.g., "balance_sheet")

    Returns:
        The page number if found in cache, None otherwise
    """
    data = load_cached_statement(pdf_stem, statement_type)
    if data and "page_num" in data:
        return data["page_num"]
    return None


def save_statement_result(pdf_stem: str, statement_type: str, result: dict) -> None:
    """Save JSON result to output/{pdf_stem}/{statement_type}.json.

    Creates the parent directory if it doesn't exist.

    Args:
        pdf_stem: The PDF filename stem (e.g., "amz-10k")
        statement_type: The statement type (e.g., "balance_sheet")
        result: The statement result dictionary to save

    Requirements: 1.2
    """
    path = OUTPUT_DIR / pdf_stem / f"{statement_type}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2))


def _resolve_pdf_path(pdf_stem: str) -> str | None:
    """Resolve the PDF path for a given stem, with fallback search.

    First checks if the expected path (data/{pdf_stem}.pdf) exists.
    If not, searches the data/ directory for matching PDFs (case-insensitive).

    Args:
        pdf_stem: The PDF filename stem (e.g., "amz-10k")

    Returns:
        The resolved PDF path as string, or None if not found.

    Requirements: 2.4
    """
    # Check expected path first
    expected_path = DATA_DIR / f"{pdf_stem}.pdf"
    if expected_path.exists():
        return str(expected_path)
    
    # Search for matching PDFs in data/ directory (case-insensitive)
    pdf_stem_lower = pdf_stem.lower()
    for pdf_file in DATA_DIR.glob("*.pdf"):
        if pdf_file.stem.lower() == pdf_stem_lower:
            return str(pdf_file)
    
    # PDF not found - graceful degradation
    return None


def preload_analysis(pdf_stem: str) -> AnalysisRecord:
    """Load existing results from output/{pdf_stem}/ into memory.

    Creates an AnalysisRecord pre-populated with cached results from
    the output directory.

    Args:
        pdf_stem: The PDF filename stem (e.g., "amz-10k")

    Returns:
        An AnalysisRecord with pre-loaded results

    Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
    """
    analysis_id = f"preload-{pdf_stem}"
    
    # Validate PDF path exists, search if not found directly
    pdf_path = _resolve_pdf_path(pdf_stem)
    
    record = AnalysisRecord(
        analysis_id=analysis_id,
        filename=f"{pdf_stem}.pdf",
        status=StatementStatusEnum.completed,
        statements={
            "balance_sheet": StatementResult(),
            "income_statement": StatementResult(),
            "cash_flow": StatementResult(),
        },
        consolidated=ConsolidatedResult(),
        pdf_path=pdf_path,  # None if not found (graceful degradation)
        pdf_stem=pdf_stem,
    )

    for stmt_type in ["balance_sheet", "income_statement", "cash_flow"]:
        cached = load_cached_statement(pdf_stem, stmt_type)
        if cached:
            record.statements[stmt_type].result = cached
            record.statements[stmt_type].status = StatementStatusEnum.completed
            record.statements[stmt_type].cached = True
            # Load page_num from cached JSON
            if "page_num" in cached:
                record.statements[stmt_type].page_num = cached["page_num"]

    # Check if all statements loaded
    all_complete = all(
        s.status == StatementStatusEnum.completed for s in record.statements.values()
    )
    if all_complete:
        record.consolidated.status = StatementStatusEnum.completed
        
        # Bug 2 fix: Load consolidated.result from consolidated.json if it exists
        consolidated_path = OUTPUT_DIR / pdf_stem / "consolidated.json"
        if consolidated_path.exists():
            try:
                consolidated_data = json.loads(consolidated_path.read_text(encoding="utf-8"))
                record.consolidated.result = consolidated_data
            except (json.JSONDecodeError, OSError):
                pass  # Keep result as None, status remains completed

    return record


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------


@app.get("/api/analyses")
async def list_analyses() -> AnalysisListResponse:
    """Return a list of all valid analysis directories from the output folder.

    Scans OUTPUT_DIR for subdirectories containing at least one JSON result file.
    Returns list sorted by modification time (newest first).

    Requirements: 1.3, 1.4, 1.5, 1.6, 1.7
    """
    result_files = ["balance_sheet.json", "income_statement.json", "cash_flow.json", "consolidated.json"]
    analyses: list[AnalysisItem] = []

    # Handle missing output directory gracefully (Requirement: 1.7)
    if not OUTPUT_DIR.exists():
        return AnalysisListResponse(analyses=analyses)

    # Collect subdirectories with their modification times
    dir_entries: list[tuple[Path, float]] = []
    for entry in OUTPUT_DIR.iterdir():
        if entry.is_dir():
            # Check if directory contains at least one result file (Requirement: 1.5)
            has_results = any((entry / f).exists() for f in result_files)
            if has_results:
                # Use the directory's modification time
                mtime = entry.stat().st_mtime
                dir_entries.append((entry, mtime))

    # Sort by modification time, newest first
    dir_entries.sort(key=lambda x: x[1], reverse=True)

    # Build response list
    for entry, _ in dir_entries:
        analyses.append(AnalysisItem(
            id=entry.name,
            display_name=entry.name,
            has_results=True,
        ))

    return AnalysisListResponse(analyses=analyses)


@app.post("/api/analyses/rename")
async def rename_analysis(request: RenameRequest) -> RenameResponse:
    """Rename an analysis directory.

    Validates the new name, checks for conflicts, and performs the rename.

    Requirements: 3.2, 3.3, 3.5, 3.6
    """
    import os

    # Validate new_name is not empty (Requirement: 3.2)
    if not request.new_name or not request.new_name.strip():
        raise HTTPException(status_code=400, detail="Invalid name: must not be empty")

    # Validate new_name contains no path separators (Requirement: 3.2)
    if os.sep in request.new_name or (os.altsep and os.altsep in request.new_name):
        raise HTTPException(status_code=400, detail="Invalid name: must not contain path separators")

    # Check current directory exists (Requirement: 3.5)
    current_path = OUTPUT_DIR / request.current_id
    if not current_path.exists() or not current_path.is_dir():
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Check for existing directory conflict (Requirement: 3.6)
    new_path = OUTPUT_DIR / request.new_name
    if new_path.exists():
        raise HTTPException(status_code=409, detail="An analysis with this name already exists")

    # Perform the rename (Requirement: 3.3)
    try:
        shutil.move(str(current_path), str(new_path))
        return RenameResponse(success=True, new_id=request.new_name)
    except PermissionError as e:
        raise HTTPException(status_code=500, detail=f"Failed to rename: {e}")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to rename: {e}")


@app.post("/api/upload", status_code=201)
async def upload_pdf(file: UploadFile = File(...)):
    """Accept a PDF upload, validate it, and start background extraction."""
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    if file.content_type and file.content_type != "application/pdf":
        # Some clients may not set content_type; only reject if explicitly non-PDF
        if file.content_type != "application/octet-stream":
            raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Read file content and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 50MB limit")

    # Save to temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.write(content)
    tmp.close()

    # Create analysis record
    analysis_id = str(uuid.uuid4())
    pdf_stem = get_pdf_stem(file.filename or "unknown.pdf")

    record = AnalysisRecord(
        analysis_id=analysis_id,
        filename=file.filename or "unknown.pdf",
        pdf_stem=pdf_stem,
        status=StatementStatusEnum.processing,
        statements={
            "balance_sheet": StatementResult(),
            "income_statement": StatementResult(),
            "cash_flow": StatementResult(),
        },
        consolidated=ConsolidatedResult(),
        pdf_path=tmp.name,
    )

    # Create output directory immediately
    output_dir = OUTPUT_DIR / pdf_stem
    output_dir.mkdir(parents=True, exist_ok=True)

    analyses[analysis_id] = record

    # Spawn background extraction thread
    thread = threading.Thread(target=run_extraction, args=(analysis_id,), daemon=True)
    thread.start()

    return {"analysis_id": analysis_id, "status": "processing"}


@app.get("/api/analysis/{analysis_id}")
async def get_analysis(analysis_id: str):
    """Return current status and results for an analysis.
    
    Supports preload IDs in the format 'preload-{pdf_stem}' to load
    cached results from the output directory.
    
    Requirements: 2.2
    """
    # Check if already in memory
    record = analyses.get(analysis_id)
    
    # If not found and this is a preload ID, load from cache
    if not record and analysis_id.startswith("preload-"):
        pdf_stem = analysis_id[8:]  # Remove "preload-" prefix
        record = preload_analysis(pdf_stem)
        analyses[analysis_id] = record
    
    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return record.model_dump()


@app.get("/api/analysis/{analysis_id}/page/{statement}")
async def get_page_image(analysis_id: str, statement: str):
    """Return the rendered PDF page image for a specific statement."""
    record = analyses.get(analysis_id)
    
    # Handle preload IDs like get_analysis does
    if not record and analysis_id.startswith("preload-"):
        pdf_stem = analysis_id[8:]  # Remove "preload-" prefix
        record = preload_analysis(pdf_stem)
        analyses[analysis_id] = record
    
    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if statement not in record.statements:
        raise HTTPException(status_code=400, detail=f"Invalid statement type: {statement}")

    stmt = record.statements[statement]
    if stmt.page_num is None:
        raise HTTPException(status_code=404, detail="Page not yet available for this statement")

    # Bug 1 fix: Handle None pdf_path gracefully
    if record.pdf_path is None:
        raise HTTPException(status_code=404, detail="PDF file not available")

    try:
        img = pdf_page_to_image(record.pdf_path, stmt.page_num)
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return Response(content=buf.getvalue(), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to render page: {e}")


# ---------------------------------------------------------------------------
# Background Extraction
# ---------------------------------------------------------------------------

def _build_statement_result(result, indicators_cls, yoy_cls=None, page_num: int | None = None):
    """Build the result dict matching the save_json structure for a statement."""
    current = result.current_period
    ind_current = indicators_cls(current)
    output = {
        "current_period": current.model_dump(),
        "prior_period": None,
        "indicators": ind_current.summary(),
        "yoy": None,
        "page_num": page_num,
    }
    if result.prior_period is not None:
        prior = result.prior_period
        ind_prior = indicators_cls(prior)
        output["prior_period"] = prior.model_dump()
        if yoy_cls:
            yoy = yoy_cls(current=ind_current, prior=ind_prior)
            output["yoy"] = {
                "absolute_changes": yoy.absolute_changes(),
                "percentage_changes": yoy.percentage_changes(),
                "ratio_changes": yoy.ratio_changes(),
            }
    return output


def run_extraction(analysis_id: str):
    """Run all 3 statement extractions sequentially in a background thread."""
    record = analyses[analysis_id]
    config = load_config()
    pdf_path = record.pdf_path
    pdf_stem = record.pdf_stem

    # Statement extraction configs: (key, name, find_fn, extract_fn, indicators_cls, yoy_cls)
    statement_configs = [
        ("balance_sheet", "Balance Sheet", find_balance_sheet_page,
         extract_multi_period_from_image, FinancialIndicators, YoYComparison),
        ("income_statement", "Income Statement", find_income_statement_page,
         extract_income_statement_from_image, IncomeStatementIndicators, IncomeStatementYoY),
        ("cash_flow", "Cash Flow", find_cash_flow_page,
         extract_cash_flow_from_image, CashFlowIndicators, CashFlowYoY),
    ]

    results = {}  # Store raw extraction results for consolidated

    for key, name, find_fn, extract_fn, ind_cls, yoy_cls in statement_configs:
        stmt = record.statements[key]

        # Check for cached result FIRST (Requirements: 1.3, 4.1)
        cached = load_cached_statement(pdf_stem, key)
        if cached:
            stmt.result = cached
            stmt.status = StatementStatusEnum.completed
            stmt.cached = True
            # Restore page_num from cache if available
            cached_page_num = get_cached_page_num(pdf_stem, key)
            if cached_page_num is not None:
                stmt.page_num = cached_page_num
            logger.info("  ✓ %s loaded from cache", name)
            continue

        # Proceed with extraction
        stmt.status = StatementStatusEnum.processing
        try:
            # Find page
            page_result = find_fn(pdf_path)
            page_num = page_result.page_num
            stmt.page_num = page_num
            logger.info("  %s detected: page %d (score: %s)", name, page_num + 1, page_result.score)

            # Render page image and extract
            img = pdf_page_to_image(pdf_path, page_num)
            result = extract_fn(
                img,
                model_name=config.model,
                base_url=config.base_url,
                api_key=config.api_key,
            )

            # Build result dict matching save_json structure
            stmt.result = _build_statement_result(result, ind_cls, yoy_cls, page_num)
            stmt.status = StatementStatusEnum.completed
            results[key] = result

            # SAVE IMMEDIATELY after extraction (Requirement: 1.2)
            save_statement_result(pdf_stem, key, stmt.result)

            logger.info("  ✓ %s extraction completed", name)

        except Exception as e:
            stmt.status = StatementStatusEnum.error
            stmt.error = str(e)
            logger.error("  ⚠ %s extraction failed: %s", name, e)

    # Consolidated report — only if all 3 succeeded
    if all(record.statements[k].status == StatementStatusEnum.completed for k in ["balance_sheet", "income_statement", "cash_flow"]):
        try:
            record.consolidated.status = StatementStatusEnum.processing

            # Handle both cached results (need reconstruction) and freshly extracted results
            if "balance_sheet" in results:
                bs_ind = FinancialIndicators(results["balance_sheet"].current_period)
            else:
                # Reconstruct from cached data
                cached_bs = record.statements["balance_sheet"].result
                bs_data = BalanceSheetData.model_validate(cached_bs["current_period"])
                bs_ind = FinancialIndicators(bs_data)

            if "income_statement" in results:
                is_ind = IncomeStatementIndicators(results["income_statement"].current_period)
            else:
                # Reconstruct from cached data
                cached_is = record.statements["income_statement"].result
                is_data = IncomeStatementData.model_validate(cached_is["current_period"])
                is_ind = IncomeStatementIndicators(is_data)

            if "cash_flow" in results:
                cf_ind = CashFlowIndicators(results["cash_flow"].current_period)
            else:
                # Reconstruct from cached data
                cached_cf = record.statements["cash_flow"].result
                cf_data = CashFlowData.model_validate(cached_cf["current_period"])
                cf_ind = CashFlowIndicators(cf_data)

            cross = _cross_statement_indicators(bs_ind, is_ind, cf_ind)

            record.consolidated.result = {
                "balance_sheet": record.statements["balance_sheet"].result,
                "income_statement": record.statements["income_statement"].result,
                "cash_flow": record.statements["cash_flow"].result,
                "cross_statement_indicators": cross,
            }
            # Save consolidated outputs to disk (Requirements: 2.1)
            pdf_output_dir = OUTPUT_DIR / pdf_stem
            
            # Build FullFinancialResult for save functions
            full_result = FullFinancialResult()
            if "balance_sheet" in results:
                full_result.balance_sheet = results["balance_sheet"]
            else:
                # Reconstruct from cached data
                cached_bs = record.statements["balance_sheet"].result
                full_result.balance_sheet = BSResult(
                    current_period=BalanceSheetData.model_validate(cached_bs["current_period"]),
                    prior_period=BalanceSheetData.model_validate(cached_bs["prior_period"]) if cached_bs.get("prior_period") else None
                )
            if "income_statement" in results:
                full_result.income_statement = results["income_statement"]
            else:
                cached_is = record.statements["income_statement"].result
                full_result.income_statement = ISResult(
                    current_period=IncomeStatementData.model_validate(cached_is["current_period"]),
                    prior_period=IncomeStatementData.model_validate(cached_is["prior_period"]) if cached_is.get("prior_period") else None
                )
            if "cash_flow" in results:
                full_result.cash_flow = results["cash_flow"]
            else:
                cached_cf = record.statements["cash_flow"].result
                full_result.cash_flow = CFResult(
                    current_period=CashFlowData.model_validate(cached_cf["current_period"]),
                    prior_period=CashFlowData.model_validate(cached_cf["prior_period"]) if cached_cf.get("prior_period") else None
                )
            
            save_consolidated_json(full_result, pdf_output_dir / "consolidated.json")
            save_consolidated_report(full_result, pdf_output_dir / "consolidated.md")
            record.consolidated.status = StatementStatusEnum.completed
            logger.info("  ✓ Consolidated report completed")
        except Exception as e:
            record.consolidated.status = StatementStatusEnum.error
            logger.error("  ⚠ Consolidated report failed: %s", e)
    else:
        # Mark consolidated as error if any statement failed
        failed = [k for k in ["balance_sheet", "income_statement", "cash_flow"]
                  if record.statements[k].status == StatementStatusEnum.error]
        if failed:
            record.consolidated.status = StatementStatusEnum.error

    # Mark overall analysis as completed
    record.status = StatementStatusEnum.completed


# ---------------------------------------------------------------------------
# Static file serving — MUST be last so /api/* routes take priority
# ---------------------------------------------------------------------------

_static_dir = Path(__file__).parent / "static"
if _static_dir.exists():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")


if __name__ == "__main__":
    # Disable uvicorn access logs (HTTP request logging)
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="warning",  # Only show warnings and errors
        access_log=False,  # Disable access logging completely
    )
