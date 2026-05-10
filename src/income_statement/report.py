"""Generate .json and .md report files for income statement results."""

import json
from pathlib import Path

from src.shared.formatting import fmt, fmt_pct, fmt_ratio, fmt_row, fmt_trend, units_note
from .indicators import IncomeStatementIndicators, IncomeStatementYoY
from .models import IncomeStatementData, IncomeStatementMultiPeriod


def _build_income_data_table(data: IncomeStatementData) -> list[str]:
    lines = ["### Revenue & Cost", "", "| Item | Value |", "|------|------:|"]
    for label, value, bold in [
        ("Total Revenue", data.total_revenue, False),
        ("Cost of Revenue", data.cost_of_revenue, False),
        ("Gross Profit", data.gross_profit, True),
    ]:
        row = fmt_row(label, value, bold)
        if row:
            lines.append(row)

    lines += ["", "### Operating Expenses", "", "| Item | Value |", "|------|------:|"]
    for label, value, bold in [
        ("Research & Development", data.research_and_development, False),
        ("Selling, General & Admin", data.selling_general_admin, False),
        ("Other Operating Expenses", data.other_operating_expenses, False),
        ("Total Operating Expenses", data.total_operating_expenses, True),
        ("Operating Income", data.operating_income, True),
    ]:
        row = fmt_row(label, value, bold)
        if row:
            lines.append(row)

    lines += ["", "### Non-Operating & Net Income", "", "| Item | Value |", "|------|------:|"]
    for label, value, bold in [
        ("Interest Income", data.interest_income, False),
        ("Interest Expense", data.interest_expense, False),
        ("Other Income/Expense", data.other_income_expense, False),
        ("Income Before Tax", data.income_before_tax, True),
        ("Income Tax Expense", data.income_tax_expense, False),
        ("Net Income", data.net_income, True),
    ]:
        row = fmt_row(label, value, bold)
        if row:
            lines.append(row)

    lines += ["", "### Per Share Data", "", "| Item | Value |", "|------|------:|"]
    for label, value, bold, dec in [
        ("Basic EPS", data.basic_eps, False, 2),
        ("Diluted EPS", data.diluted_eps, False, 2),
        ("Basic Shares Outstanding", data.basic_shares_outstanding, False, 0),
        ("Diluted Shares Outstanding", data.diluted_shares_outstanding, False, 0),
    ]:
        row = fmt_row(label, value, bold, dec)
        if row:
            lines.append(row)

    return lines


def _build_side_by_side_table(current: IncomeStatementData, prior: IncomeStatementData) -> list[str]:
    cur_label = current.period
    pri_label = prior.period
    lines = [
        f"| Item | {cur_label} | {pri_label} |",
        "|------|------:|------:|",
    ]
    _rows = [
        ("Total Revenue", "total_revenue", True),
        ("Cost of Revenue", "cost_of_revenue", False),
        ("Gross Profit", "gross_profit", True),
        ("———", None, False),
        ("Research & Development", "research_and_development", False),
        ("Selling, General & Admin", "selling_general_admin", False),
        ("Other Operating Expenses", "other_operating_expenses", False),
        ("Total Operating Expenses", "total_operating_expenses", True),
        ("Operating Income", "operating_income", True),
        ("———", None, False),
        ("Interest Income", "interest_income", False),
        ("Interest Expense", "interest_expense", False),
        ("Other Income/Expense", "other_income_expense", False),
        ("Income Before Tax", "income_before_tax", True),
        ("Income Tax Expense", "income_tax_expense", False),
        ("Net Income", "net_income", True),
        ("———", None, False),
        ("Basic EPS", "basic_eps", False),
        ("Diluted EPS", "diluted_eps", False),
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


def save_income_statement_json(result: IncomeStatementMultiPeriod, output_path: Path, page_num: int | None = None) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    current = result.current_period
    ind_current = IncomeStatementIndicators(current)
    output: dict = {"current_period": current.model_dump(), "prior_period": None, "indicators": ind_current.summary(), "yoy": None, "page_num": page_num}
    if result.prior_period is not None:
        prior = result.prior_period
        ind_prior = IncomeStatementIndicators(prior)
        yoy = IncomeStatementYoY(current=ind_current, prior=ind_prior)
        output["prior_period"] = prior.model_dump()
        output["yoy"] = {"absolute_changes": yoy.absolute_changes(), "percentage_changes": yoy.percentage_changes(), "ratio_changes": yoy.ratio_changes()}
    output_path.write_text(json.dumps(output, indent=2))
    return output_path


_IS_ITEM_LABELS = {
    "total_revenue": "Total Revenue",
    "cost_of_revenue": "Cost of Revenue",
    "gross_profit": "Gross Profit",
    "operating_income": "Operating Income",
    "net_income": "Net Income",
    "research_and_development": "R&D",
    "selling_general_admin": "SG&A",
}

_IS_ITEM_FAVORABLE = {
    "total_revenue": True,
    "cost_of_revenue": False,
    "gross_profit": True,
    "operating_income": True,
    "net_income": True,
    "research_and_development": None,
    "selling_general_admin": False,
}

_IS_RATIO_LABELS = {
    "gross_margin": "Gross Margin",
    "operating_margin": "Operating Margin",
    "net_margin": "Net Margin",
    "effective_tax_rate": "Effective Tax Rate",
}

_IS_RATIO_FAVORABLE = {
    "gross_margin": True,
    "operating_margin": True,
    "net_margin": True,
    "effective_tax_rate": False,
}


def save_income_statement_report(result: IncomeStatementMultiPeriod, output_path: Path) -> Path:
    data = result.current_period
    ind = IncomeStatementIndicators(data)
    s = ind.summary()
    lines = [
        f"# Income Statement Analysis — {data.company_name}", "",
        f"- Period: {data.period}",
        f"- Currency: {data.currency}",
        f"- {units_note(data.units, data.currency)}",
        "",
        "## Extracted Data", "",
    ]
    lines += _build_income_data_table(data)
    lines += [
        "", "## Financial Indicators", "",
        "| Indicator | Value | Interpretation |", "|-----------|------:|----------------|",
        f"| Gross Margin | {fmt(s['gross_margin'])}% | Revenue retained after COGS |",
        f"| Operating Margin | {fmt(s['operating_margin'])}% | Profitability from core operations |",
        f"| Net Margin | {fmt(s['net_margin'])}% | Bottom-line profitability |",
        f"| R&D to Revenue | {fmt(s['rd_to_revenue'])}% | Innovation investment intensity |",
        f"| SG&A to Revenue | {fmt(s['sga_to_revenue'])}% | Overhead efficiency |",
        f"| Effective Tax Rate | {fmt(s['effective_tax_rate'])}% | Actual tax burden |",
        f"| Interest Coverage | {fmt(s['interest_coverage'])} | Ability to service debt |",
        "", "## Validation", "",
        f"- Gross Profit Check: Revenue − COGS − Gross Profit = **{fmt(s['gross_profit_check'])}**",
    ]
    lines.append("- Status: ✓ **PASS**" if s["extraction_valid"] else "- Status: ✗ **FAIL** — discrepancy detected")

    if result.prior_period is not None:
        prior = result.prior_period
        ind_prior = IncomeStatementIndicators(prior)
        yoy = IncomeStatementYoY(current=ind, prior=ind_prior)
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
        for k, label in _IS_ITEM_LABELS.items():
            fav = _IS_ITEM_FAVORABLE[k]
            trend = fmt_trend(pct_c[k], higher_is_better=fav) if fav is not None else "—"
            lines.append(f"| {label} | {fmt(abs_c[k])} | {fmt_pct(pct_c[k])} | {trend} |")

        lines += [
            "", "### Margin Changes (pp)", "",
            "| Ratio | Change | Trend |",
            "|-------|-------:|-------|",
        ]
        for k, label in _IS_RATIO_LABELS.items():
            trend = fmt_trend(rat_c[k], higher_is_better=_IS_RATIO_FAVORABLE[k])
            lines.append(f"| {label} | {fmt_ratio(rat_c[k])} | {trend} |")

    lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
