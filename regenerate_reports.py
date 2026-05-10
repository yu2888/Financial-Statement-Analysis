"""Regenerate .md reports from existing .json output files (no LLM calls needed).

Usage:
    python regenerate_reports.py                # regenerate all in output/
    python regenerate_reports.py output/amz-10k/balance_sheet.json
"""

import argparse
import json
import sys
from pathlib import Path

from src.balance_sheet.models import BalanceSheetData, MultiPeriodResult
from src.balance_sheet.report import save_report, save_json
from src.income_statement.models import IncomeStatementData, IncomeStatementMultiPeriod
from src.income_statement.report import save_income_statement_report, save_income_statement_json
from src.cash_flow.models import CashFlowData, CashFlowMultiPeriod
from src.cash_flow.report import save_cash_flow_report, save_cash_flow_json
from src.consolidated.models import FullFinancialResult
from src.consolidated.report import save_consolidated_json, save_consolidated_report

OUTPUT_DIR = Path("output")

STATEMENT_TYPES = {
    "balance_sheet": {
        "data_cls": BalanceSheetData,
        "multi_cls": MultiPeriodResult,
        "save_md": save_report,
        "save_json": save_json,
    },
    "income_statement": {
        "data_cls": IncomeStatementData,
        "multi_cls": IncomeStatementMultiPeriod,
        "save_md": save_income_statement_report,
        "save_json": save_income_statement_json,
    },
    "cash_flow": {
        "data_cls": CashFlowData,
        "multi_cls": CashFlowMultiPeriod,
        "save_md": save_cash_flow_report,
        "save_json": save_cash_flow_json,
    },
}


def detect_type(path: Path) -> str | None:
    for key in STATEMENT_TYPES:
        if key in path.stem:
            return key
    return None


def load_statement(json_path: Path, stmt_type: str):
    raw = json.loads(json_path.read_text())
    cfg = STATEMENT_TYPES[stmt_type]
    current = cfg["data_cls"](**raw["current_period"])
    prior = cfg["data_cls"](**raw["prior_period"]) if raw.get("prior_period") else None
    return cfg["multi_cls"](current_period=current, prior_period=prior)


def regenerate_one(json_path: Path, force: bool = False) -> bool:
    stmt_type = detect_type(json_path)
    if stmt_type is None:
        if "consolidated" in json_path.stem:
            return regenerate_consolidated(json_path, force=force)
        print(f"  skip: {json_path.name} (unknown type)")
        return False

    md_path = json_path.with_suffix(".md")
    
    # Skip if .md already exists and not forced
    if not force and md_path.exists():
        print(f"  skip: {json_path.name} (.md already exists)")
        return False

    result = load_statement(json_path, stmt_type)
    cfg = STATEMENT_TYPES[stmt_type]

    cfg["save_md"](result, md_path)
    # Don't overwrite JSON - we only regenerate .md
    print(f"  ✓ {json_path.name} → {md_path.name}")
    return True


def regenerate_consolidated(json_path: Path, force: bool = False) -> bool:
    md_path = json_path.with_suffix(".md")
    
    # Skip if .md already exists and not forced
    if not force and md_path.exists():
        print(f"  skip: {json_path.name} (.md already exists)")
        return False

    raw = json.loads(json_path.read_text())

    bs = is_stmt = cf = None
    bs_json = json_path.parent / "balance_sheet.json"
    is_json = json_path.parent / "income_statement.json"
    cf_json = json_path.parent / "cash_flow.json"

    if bs_json.exists():
        bs = load_statement(bs_json, "balance_sheet")
    if is_json.exists():
        is_stmt = load_statement(is_json, "income_statement")
    if cf_json.exists():
        cf = load_statement(cf_json, "cash_flow")

    if not (bs or is_stmt or cf):
        print(f"  skip: {json_path.name} (no source statement JSONs found)")
        return False

    full = FullFinancialResult(balance_sheet=bs, income_statement=is_stmt, cash_flow=cf)
    # Don't overwrite JSON - we only regenerate .md
    save_consolidated_report(full, md_path)
    print(f"  ✓ {json_path.name} → {md_path.name}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Regenerate reports from existing JSON output.")
    parser.add_argument("files", nargs="*", help="Specific JSON files. If omitted, processes all in output/")
    parser.add_argument("--force", "-f", action="store_true", help="Overwrite existing .md files")
    args = parser.parse_args()

    if args.files:
        json_files = [Path(f) for f in args.files]
    else:
        if not OUTPUT_DIR.exists():
            print(f"No output/ directory found.", file=sys.stderr)
            sys.exit(1)
        json_files = sorted(OUTPUT_DIR.glob("**/*.json"))
        if not json_files:
            print(f"No JSON files in {OUTPUT_DIR}/", file=sys.stderr)
            sys.exit(1)

    # Process individual statements first, consolidated last
    consolidated = [f for f in json_files if "consolidated" in f.stem]
    statements = [f for f in json_files if "consolidated" not in f.stem]

    count = 0
    for f in statements + consolidated:
        if not f.exists():
            print(f"  not found: {f}", file=sys.stderr)
            continue
        if regenerate_one(f, force=args.force):
            count += 1

    print(f"\nRegenerated {count} report(s).")


if __name__ == "__main__":
    main()
