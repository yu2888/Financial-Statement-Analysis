"""Generate .json and .md report files for balance sheet results."""

import json
from pathlib import Path

from src.shared.formatting import fmt, fmt_pct, fmt_ratio, fmt_row, fmt_trend, units_note
from .indicators import FinancialIndicators, YoYComparison
from .models import BalanceSheetData, MultiPeriodResult


def _build_data_table(data: BalanceSheetData) -> list[str]:
    """Build extracted data tables, omitting zero-value non-total rows."""
    lines = ["### Assets", "", "| Item | Value |", "|------|------:|"]
    _asset_rows = [
        ("Cash & Equivalents", data.cash_and_equivalents, False),
        ("Accounts Receivable", data.accounts_receivable, False),
        ("Marketable Securities", data.marketable_securities, False),
        ("Inventory", data.inventory, False),
        ("Other Current Assets", data.other_current_assets, False),
        ("Total Current Assets", data.total_current_assets, True),
        ("PP&E (net)", data.ppe, False),
        ("Intangible Assets / Goodwill", data.intangible_assets, False),
        ("Operating Lease ROU Assets", data.operating_lease_right_of_use, False),
        ("Finance Lease ROU Assets", data.finance_lease_right_of_use, False),
        ("Equity Investments", data.equity_investments, False),
        ("Deferred Tax Assets", data.deferred_tax_assets, False),
        ("Other Non-Current Assets", data.other_non_current_assets, False),
        ("Total Assets", data.total_assets, True),
    ]
    for label, value, bold in _asset_rows:
        row = fmt_row(label, value, bold)
        if row:
            lines.append(row)

    lines += ["", "### Liabilities", "", "| Item | Value |", "|------|------:|"]
    _liab_rows = [
        ("Accounts Payable", data.accounts_payable, False),
        ("Short-Term Debt", data.short_term_debt, False),
        ("Accrued Expenses", data.accrued_expenses, False),
        ("Current Portion of Long-Term Debt", data.current_portion_long_term_debt, False),
        ("Operating Lease Liabilities (Current)", data.operating_lease_liabilities_current, False),
        ("Deferred Revenue", data.deferred_revenue, False),
        ("Other Current Liabilities", data.other_current_liabilities, False),
        ("Total Current Liabilities", data.total_current_liabilities, True),
        ("Long-Term Debt", data.long_term_debt, False),
        ("Operating Lease Liabilities (Non-Current)", data.operating_lease_liabilities_non_current, False),
        ("Other Non-Current Liabilities", data.other_non_current_liabilities, False),
        ("Total Liabilities", data.total_liabilities, True),
    ]
    for label, value, bold in _liab_rows:
        row = fmt_row(label, value, bold)
        if row:
            lines.append(row)

    lines += ["", "### Shareholders' Equity", "", "| Item | Value |", "|------|------:|"]
    _eq_rows = [
        ("Common Stock", data.common_stock, False),
        ("Additional Paid-In Capital", data.additional_paid_in_capital, False),
        ("Retained Earnings", data.retained_earnings, False),
        ("Treasury Stock", data.treasury_stock, False),
        ("Accumulated Other Comprehensive Income", data.accumulated_other_comprehensive_income, False),
        ("Other Equity", data.other_equity, False),
        ("Total Equity", data.total_shareholders_equity, True),
    ]
    for label, value, bold in _eq_rows:
        row = fmt_row(label, value, bold)
        if row:
            lines.append(row)

    return lines


def _build_side_by_side_table(current: BalanceSheetData, prior: BalanceSheetData) -> list[str]:
    """Build a side-by-side comparison table for current vs prior period."""
    cur_label = current.period
    pri_label = prior.period
    lines = [
        f"| Item | {cur_label} | {pri_label} |",
        "|------|------:|------:|",
    ]
    _rows = [
        ("Cash & Equivalents", "cash_and_equivalents", False),
        ("Accounts Receivable", "accounts_receivable", False),
        ("Marketable Securities", "marketable_securities", False),
        ("Inventory", "inventory", False),
        ("Other Current Assets", "other_current_assets", False),
        ("Total Current Assets", "total_current_assets", True),
        ("PP&E (net)", "ppe", False),
        ("Intangible Assets / Goodwill", "intangible_assets", False),
        ("Operating Lease ROU Assets", "operating_lease_right_of_use", False),
        ("Finance Lease ROU Assets", "finance_lease_right_of_use", False),
        ("Equity Investments", "equity_investments", False),
        ("Deferred Tax Assets", "deferred_tax_assets", False),
        ("Other Non-Current Assets", "other_non_current_assets", False),
        ("Total Assets", "total_assets", True),
        ("———", None, False),
        ("Accounts Payable", "accounts_payable", False),
        ("Short-Term Debt", "short_term_debt", False),
        ("Accrued Expenses", "accrued_expenses", False),
        ("Current Portion of LT Debt", "current_portion_long_term_debt", False),
        ("Operating Lease Liab. (Current)", "operating_lease_liabilities_current", False),
        ("Deferred Revenue", "deferred_revenue", False),
        ("Other Current Liabilities", "other_current_liabilities", False),
        ("Total Current Liabilities", "total_current_liabilities", True),
        ("Long-Term Debt", "long_term_debt", False),
        ("Operating Lease Liab. (Non-Current)", "operating_lease_liabilities_non_current", False),
        ("Other Non-Current Liabilities", "other_non_current_liabilities", False),
        ("Total Liabilities", "total_liabilities", True),
        ("———", None, False),
        ("Common Stock", "common_stock", False),
        ("Additional Paid-In Capital", "additional_paid_in_capital", False),
        ("Retained Earnings", "retained_earnings", False),
        ("Treasury Stock", "treasury_stock", False),
        ("AOCI", "accumulated_other_comprehensive_income", False),
        ("Other Equity", "other_equity", False),
        ("Total Equity", "total_shareholders_equity", True),
    ]
    for label, field, bold in _rows:
        if field is None:
            lines.append(f"| {label} | | |")
            continue
        cur_val = getattr(current, field)
        pri_val = getattr(prior, field)
        if not bold and cur_val == 0.0 and pri_val == 0.0:
            continue
        if bold:
            lines.append(f"| **{label}** | **{fmt(cur_val)}** | **{fmt(pri_val)}** |")
        else:
            lines.append(f"| {label} | {fmt(cur_val)} | {fmt(pri_val)} |")
    return lines


def save_json(result: MultiPeriodResult, output_path: Path, page_num: int | None = None) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    current = result.current_period
    ind_current = FinancialIndicators(current)
    output: dict = {
        "current_period": current.model_dump(),
        "prior_period": None,
        "indicators": ind_current.summary(),
        "yoy": None,
        "page_num": page_num,
    }
    if result.prior_period is not None:
        prior = result.prior_period
        ind_prior = FinancialIndicators(prior)
        yoy = YoYComparison(current=ind_current, prior=ind_prior)
        output["prior_period"] = prior.model_dump()
        output["yoy"] = {
            "absolute_changes": yoy.absolute_changes(),
            "percentage_changes": yoy.percentage_changes(),
            "ratio_changes": yoy.ratio_changes(),
        }
    output_path.write_text(json.dumps(output, indent=2))
    return output_path


_RATIO_FAVORABLE = {
    "current_ratio": True,
    "quick_ratio": True,
    "debt_to_equity": False,
    "cash_ratio": True,
    "equity_ratio": True,
    "debt_ratio": False,
}

_YOY_ITEM_LABELS = {
    "total_assets": "Total Assets",
    "total_liabilities": "Total Liabilities",
    "total_shareholders_equity": "Total Equity",
    "total_current_assets": "Total Current Assets",
    "total_current_liabilities": "Total Current Liabilities",
    "cash_and_equivalents": "Cash & Equivalents",
    "long_term_debt": "Long-Term Debt",
}

_YOY_ITEM_FAVORABLE = {
    "total_assets": True,
    "total_liabilities": False,
    "total_shareholders_equity": True,
    "total_current_assets": True,
    "total_current_liabilities": False,
    "cash_and_equivalents": True,
    "long_term_debt": False,
}

_RATIO_LABELS = {
    "current_ratio": "Current Ratio",
    "quick_ratio": "Quick Ratio",
    "debt_to_equity": "Debt-to-Equity",
    "cash_ratio": "Cash Ratio",
    "equity_ratio": "Equity Ratio",
    "debt_ratio": "Debt Ratio",
}


def save_report(result: MultiPeriodResult, output_path: Path) -> Path:
    data = result.current_period
    ind = FinancialIndicators(data)
    s = ind.summary()

    lines = [
        f"# Balance Sheet Analysis — {data.company_name}", "",
        f"- Period: {data.period}",
        f"- Currency: {data.currency}",
        f"- {units_note(data.units, data.currency)}",
        "",
        "## Extracted Data", "",
    ]
    lines += _build_data_table(data)
    lines += [
        "", "## Financial Indicators", "",
        "| Indicator | Value | Interpretation |",
        "|-----------|------:|----------------|",
        f"| Current Ratio | {fmt(s['current_ratio'])} | ≥ 1.0 healthy; < 1.0 red flag |",
        f"| Quick Ratio (Acid Test) | {fmt(s['quick_ratio'])} | Stricter liquidity; ignores inventory |",
        f"| Cash Ratio | {fmt(s['cash_ratio'])} | Most conservative liquidity measure |",
        f"| Debt-to-Equity | {fmt(s['debt_to_equity'])} | High = aggressive debt financing |",
        f"| Equity Ratio | {fmt(s['equity_ratio'])} | Proportion of assets funded by equity |",
        f"| Debt Ratio | {fmt(s['debt_ratio'])} | Proportion of assets funded by debt |",
        f"| Working Capital | {fmt(s['working_capital'])} | Current Assets − Current Liabilities |",
        f"| Net Debt | {fmt(s['net_debt'])} | Total debt minus cash |",
        f"| Tangible Book Value | {fmt(s['tangible_book_value'])} | Equity minus intangible assets |",
        "", "## Asset Composition", "",
        "| Category | Percentage |", "|----------|----------:|",
        f"| Current Assets | {fmt(s['current_asset_pct'])}% |",
        f"| Non-Current Assets | {fmt(s['non_current_asset_pct'])}% |",
        "", "## Validation", "",
        f"- Accounting Equation Check: Assets − (Liabilities + Equity) = **{fmt(s['accounting_equation_discrepancy'])}**",
    ]
    lines.append("- Status: ✓ **PASS**" if s["extraction_valid"] else "- Status: ✗ **FAIL** — discrepancy detected, review extraction or source document")

    if result.prior_period is not None:
        prior = result.prior_period
        ind_prior = FinancialIndicators(prior)
        yoy = YoYComparison(current=ind, prior=ind_prior)
        abs_c = yoy.absolute_changes()
        pct_c = yoy.percentage_changes()
        rat_c = yoy.ratio_changes()

        lines += [
            "", "## Period Comparison", "",
            f"Side-by-side: {data.period} vs {prior.period}", "",
        ]
        lines += _build_side_by_side_table(data, prior)

        lines += [
            "", "## Year-Over-Year Comparison", "",
            "### Key Item Changes", "",
            "| Item | Absolute Change | % Change | Trend |",
            "|------|----------------:|---------:|-------|",
        ]
        for k, label in _YOY_ITEM_LABELS.items():
            trend = fmt_trend(pct_c[k], higher_is_better=_YOY_ITEM_FAVORABLE[k])
            lines.append(f"| {label} | {fmt(abs_c[k])} | {fmt_pct(pct_c[k])} | {trend} |")

        lines += [
            "", "### Ratio Changes", "",
            "| Ratio | Change | Trend |",
            "|-------|-------:|-------|",
        ]
        for k, label in _RATIO_LABELS.items():
            trend = fmt_trend(rat_c[k], higher_is_better=_RATIO_FAVORABLE[k])
            lines.append(f"| {label} | {fmt_ratio(rat_c[k])} | {trend} |")

    lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
