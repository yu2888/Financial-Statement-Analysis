"""Financial Analysis — Web UI (default) or CLI mode.

Usage:
    python main.py                          # Start web dashboard at http://localhost:8000
    python main.py --port 3000              # Start on a custom port
    python main.py --cli                    # Process all PDFs in data/ (CLI mode)
    python main.py --cli data/amz-10k.pdf   # Process a specific PDF (CLI mode)
"""

import argparse
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")


# ---------------------------------------------------------------------------
# CLI mode — preserved from original main.py
# ---------------------------------------------------------------------------

def _extract_statement(pdf_path, config, statement_name, find_page_fn, extract_fn, verbose=False):
    """Generic helper: find page → render image → extract via LLM."""
    from src.shared.llm import pdf_page_to_image

    try:
        page_result = find_page_fn(str(pdf_path))
        page_num = page_result.page_num
        logger.info("  %s detected: page %d (score: %s)", statement_name, page_num + 1, page_result.score)
    except ValueError as e:
        logger.error("  ⚠ %s: %s", statement_name, e)
        return None, None

    try:
        img = pdf_page_to_image(str(pdf_path), page_num)
    except IndexError as e:
        logger.error("  ⚠ %s: %s", statement_name, e)
        return None, None

    logger.info("  Extracting %s with %s...", statement_name, config.model)
    try:
        result = extract_fn(img, model_name=config.model, base_url=config.base_url, api_key=config.api_key, verbose=verbose)
    except Exception as e:
        logger.error("  ⚠ %s extraction failed: %s", statement_name, e)
        return None, None

    if hasattr(result, "prior_period") and result.prior_period is not None:
        logger.info("  ✓ %s: prior period data found (%s)", statement_name, result.prior_period.period)
    else:
        logger.info("  ℹ %s: no prior period data detected", statement_name)
    return result, page_num


def process_pdf(pdf_path: Path, config, verbose: bool = False) -> bool:
    from src.balance_sheet.extractor import extract_multi_period_from_image
    from src.balance_sheet.page_finder import find_balance_sheet_page
    from src.balance_sheet.report import save_json, save_report
    from src.income_statement.extractor import extract_income_statement_from_image
    from src.income_statement.page_finder import find_income_statement_page
    from src.income_statement.report import save_income_statement_json, save_income_statement_report
    from src.cash_flow.extractor import extract_cash_flow_from_image
    from src.cash_flow.page_finder import find_cash_flow_page
    from src.cash_flow.report import save_cash_flow_json, save_cash_flow_report
    from src.consolidated.models import FullFinancialResult
    from src.consolidated.report import save_consolidated_json, save_consolidated_report

    stem = pdf_path.stem
    pdf_output_dir = OUTPUT_DIR / stem
    print(f"\n{'=' * 60}")
    print(f"  {pdf_path.name}")
    print(f"{'=' * 60}")

    print(f"\n--- Balance Sheet ---")
    bs_result, bs_page_num = _extract_statement(pdf_path, config, "Balance Sheet", find_balance_sheet_page, extract_multi_period_from_image, verbose=verbose)
    if bs_result:
        save_json(bs_result, pdf_output_dir / "balance_sheet.json", page_num=bs_page_num)
        save_report(bs_result, pdf_output_dir / "balance_sheet.md")
        logger.info("  ✓ Balance sheet reports saved")

    print(f"\n--- Income Statement ---")
    is_result, is_page_num = _extract_statement(pdf_path, config, "Income Statement", find_income_statement_page, extract_income_statement_from_image, verbose=verbose)
    if is_result:
        save_income_statement_json(is_result, pdf_output_dir / "income_statement.json", page_num=is_page_num)
        save_income_statement_report(is_result, pdf_output_dir / "income_statement.md")
        logger.info("  ✓ Income statement reports saved")

    print(f"\n--- Cash Flow Statement ---")
    cf_result, cf_page_num = _extract_statement(pdf_path, config, "Cash Flow", find_cash_flow_page, extract_cash_flow_from_image, verbose=verbose)
    if cf_result:
        save_cash_flow_json(cf_result, pdf_output_dir / "cash_flow.json", page_num=cf_page_num)
        save_cash_flow_report(cf_result, pdf_output_dir / "cash_flow.md")
        logger.info("  ✓ Cash flow reports saved")

    if bs_result or is_result or cf_result:
        full = FullFinancialResult(balance_sheet=bs_result, income_statement=is_result, cash_flow=cf_result)
        save_consolidated_json(full, pdf_output_dir / "consolidated.json")
        save_consolidated_report(full, pdf_output_dir / "consolidated.md")
        logger.info("  ✓ Consolidated report saved")
        print(f"\n  ✓ Consolidated analysis complete")
        return True
    return False


def run_cli(pdf_args: list[str], verbose: bool = False):
    """Run the original CLI extraction pipeline."""
    from src.shared.config import load_config

    config = load_config()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if pdf_args:
        pdf_paths = [Path(p) for p in pdf_args]
    else:
        if not DATA_DIR.exists():
            print(f"No PDFs specified and {DATA_DIR}/ not found.", file=sys.stderr)
            sys.exit(1)
        pdf_paths = sorted(DATA_DIR.glob("*.pdf"))
        if not pdf_paths:
            print(f"No PDF files found in {DATA_DIR}/", file=sys.stderr)
            sys.exit(1)

    for p in pdf_paths:
        if not p.exists():
            print(f"Error: {p} not found", file=sys.stderr)
            sys.exit(1)

    print(f"Model: {config.model} | URL: {config.base_url}")
    print(f"PDFs to process: {len(pdf_paths)}")
    print(f"Output directory: {OUTPUT_DIR}/")
    print(f"Statements: Balance Sheet, Income Statement, Cash Flow")

    success = sum(1 for p in pdf_paths if process_pdf(p, config, verbose=verbose))
    print(f"\nDone: {success}/{len(pdf_paths)} PDFs processed successfully.")
    print(f"Results in {OUTPUT_DIR}/")


def run_web_server(port: int = 8000, preload: str | None = None):
    """Start the FastAPI web dashboard server."""
    import uvicorn
    from web.server import app, preload_analysis, analyses  # noqa: F401 — imported for uvicorn

    # Pre-load analysis if specified
    if preload:
        try:
            record = preload_analysis(preload)
            analyses[record.analysis_id] = record
            print(f"  ✓ Pre-loaded analysis: {preload}")
            print(f"    Analysis ID: {record.analysis_id}")
            loaded = sum(1 for s in record.statements.values() if s.cached)
            print(f"    Statements loaded from cache: {loaded}/3")
        except Exception as e:
            print(f"  ⚠ Failed to pre-load {preload}: {e}")

    print()
    print("  Financial Analysis Dashboard")
    print(f"  Starting server at http://localhost:{port}")
    print("  Press Ctrl+C to stop")
    print()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning", access_log=False)


def main():
    parser = argparse.ArgumentParser(
        description="Financial Analysis — Web dashboard (default) or CLI extraction."
    )
    parser.add_argument(
        "--cli", action="store_true",
        help="Run in CLI mode: process PDFs and output JSON/Markdown reports"
    )
    parser.add_argument(
        "pdfs", nargs="*",
        help="PDF file(s) to process (CLI mode only). If omitted, processes all PDFs in data/"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", default=False,
        help="Print streaming LLM tokens to stdout (CLI mode only)"
    )
    parser.add_argument(
        "--port", type=int, default=8000,
        help="Server port for web mode (default: 8000)"
    )
    parser.add_argument(
        "--preload", type=str, metavar="PDF_STEM",
        help="Pre-load cached results from output/{PDF_STEM}/ on server start"
    )
    args = parser.parse_args()

    if args.cli:
        run_cli(args.pdfs, verbose=args.verbose)
    else:
        run_web_server(port=args.port, preload=args.preload)


if __name__ == "__main__":
    main()
