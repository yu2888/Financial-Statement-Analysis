"""Generate .json and .md report files for cash flow statement results."""

import json
from pathlib import Path

from src.shared.formatting import fmt, fmt_pct, fmt_ratio, fmt_row, fmt_trend, units_note
from .indicators import CashFlowIndicators, CashFlowYoY
from .models import CashFlowData, CashFlowMultiPeriod


def _build_cash_flow_data_table(data: CashFlowData) -> list[str]:
    lines = ["### Operating Activities", "", "| Item | Value |", "|------|------:|"]
    for label, value, bold in [
        ("Net Income", data.net_income, False),
        ("Depreciation & Amortization", data.depreciation_amortization, False),
        ("Stock-Based Compensation", data.stock_based_compensation, False),
        ("Changes in Working Capital", data.changes_in_working_capital, False),
        ("Other Operating Adjustments", data.other_operating_adjustments, False),
        ("Net Cash from Operations", data.net_cash_from_operations, True),
    ]:
        row = fmt_row(label, value, bold)
        if row:
            lines.append(row)

    lines += ["", "### Investing Activities", "", "| Item | Value |", "|------|------:|"]
    for label, value, bold in [
        ("Capital Expenditures", data.capital_expenditures, False),
        ("Acquisitions", data.acquisitions, False),
        ("Purchases of Investments", data.purchases_of_investments, False),
        ("Sales of Investments", data.sales_of_investments, False),
        ("Other Investing Activities", data.other_investing_activities, False),
        ("Net Cash from Investing", data.net_cash_from_investing, True),
    ]:
        row = fmt_row(label, value, bold)
        if row:
            lines.append(row)

    lines += ["", "### Financing Activities", "", "| Item | Value |", "|------|------:|"]
    for label, value, bold in [
        ("Debt Issued", data.debt_issued, False),
        ("Debt Repaid", data.debt_repaid, False),
        ("Shares Issued", data.shares_issued, False),
        ("Shares Repurchased", data.shares_repurchased, False),
        ("Dividends Paid", data.dividends_paid, False),
        ("Other Financing Activities", data.other_financing_activities, False),
        ("Net Cash from Financing", data.net_cash_from_financing, True),
    ]:
        row = fmt_row(label, value, bold)
        if row:
            lines.append(row)

    lines += ["", "### Cash Summary", "", "| Item | Value |", "|------|------:|"]
    for label, value, bold in [
        ("Net Change in Cash", data.net_change_in_cash, False),
        ("Cash at Beginning", data.cash_beginning_of_period, False),
        ("Cash at End", data.cash_end_of_period, False),
    ]:
        row = fmt_row(label, value, bold)
        if row:
            lines.append(row)

    return lines


def _build_side_by_side_table(current: CashFlowData, prior: CashFlowData) -> list[str]:
    cur_label = current.period
    pri_label = prior.period
    lines = [
        f"| Item | {cur_label} | {pri_label} |",
        "|------|------:|------:|",
    ]
    _rows = [
        ("Net Income", "net_income", False),
        ("Depreciation & Amortization", "depreciation_amortization", False),
        ("Stock-Based Compensation", "stock_based_compensation", False),
        ("Changes in Working Capital", "changes_in_working_capital", False),
        ("Other Operating Adjustments", "other_operating_adjustments", False),
        ("Net Cash from Operations", "net_cash_from_operations", True),
        ("———", None, False),
        ("Capital Expenditures", "capital_expenditures", False),
        ("Acquisitions", "acquisitions", False),
        ("Purchases of Investments", "purchases_of_investments", False),
        ("Sales of Investments", "sales_of_investments", False),
        ("Other Investing Activities", "other_investing_activities", False),
        ("Net Cash from Investing", "net_cash_from_investing", True),
        ("———", None, False),
        ("Debt Issued", "debt_issued", False),
        ("Debt Repaid", "debt_repaid", False),
        ("Shares Issued", "shares_issued", False),
        ("Shares Repurchased", "shares_repurchased", False),
        ("Dividends Paid", "dividends_paid", False),
        ("Other Financing Activities", "other_financing_activities", False),
        ("Net Cash from Financing", "net_cash_from_financing", True),
        ("———", None, False),
        ("Net Change in Cash", "net_change_in_cash", False),
        ("Cash at Beginning", "cash_beginning_of_period", False),
        ("Cash at End", "cash_end_of_period", False),
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


def save_cash_flow_json(result: CashFlowMultiPeriod, output_path: Path, page_num: int | None = None) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    current = result.current_period
    ind_current = CashFlowIndicators(current)
    output: dict = {"current_period": current.model_dump(), "prior_period": None, "indicators": ind_current.summary(), "yoy": None, "page_num": page_num}
    if result.prior_period is not None:
        prior = result.prior_period
        ind_prior = CashFlowIndicators(prior)
        yoy = CashFlowYoY(current=ind_current, prior=ind_prior)
        output["prior_period"] = prior.model_dump()
        output["yoy"] = {"absolute_changes": yoy.absolute_changes(), "percentage_changes": yoy.percentage_changes(), "ratio_changes": yoy.ratio_changes()}
    output_path.write_text(json.dumps(output, indent=2))
    return output_path


_CF_ITEM_LABELS = {
    "net_cash_from_operations": "Operating Cash Flow",
    "net_cash_from_investing": "Investing Cash Flow",
    "net_cash_from_financing": "Financing Cash Flow",
    "capital_expenditures": "Capital Expenditures",
    "net_change_in_cash": "Net Change in Cash",
}

_CF_ITEM_FAVORABLE = {
    "net_cash_from_operations": True,
    "net_cash_from_investing": None,
    "net_cash_from_financing": None,
    "capital_expenditures": None,
    "net_change_in_cash": True,
}

_CF_RATIO_LABELS = {
    "operating_cash_flow_ratio": "OCF / Net Income",
    "capex_to_ocf": "CapEx to OCF",
}

_CF_RATIO_FAVORABLE = {
    "operating_cash_flow_ratio": True,
    "capex_to_ocf": False,
}


def save_cash_flow_report(result: CashFlowMultiPeriod, output_path: Path) -> Path:
    data = result.current_period
    ind = CashFlowIndicators(data)
    s = ind.summary()
    lines = [
        f"# Cash Flow Analysis — {data.company_name}", "",
        f"- Period: {data.period}",
        f"- Currency: {data.currency}",
        f"- {units_note(data.units, data.currency)}",
        "",
        "## Extracted Data", "",
    ]
    lines += _build_cash_flow_data_table(data)
    lines += [
        "", "## Financial Indicators", "",
        "| Indicator | Value | Interpretation |", "|-----------|------:|----------------|",
        f"| Free Cash Flow | {fmt(s['free_cash_flow'])} | OCF minus CapEx |",
        f"| OCF / Net Income | {fmt(s['operating_cash_flow_ratio'])} | >1.0 = high earnings quality |",
        f"| CapEx to OCF | {fmt(s['capex_to_ocf'])}% | Reinvestment rate |",
        f"| Operating % of Total | {fmt(s['operating_pct'])}% | Cash flow composition |",
        f"| Debt Service Coverage | {fmt(s['debt_service_coverage'])} | Ability to repay debt |",
        f"| Shareholder Return | {fmt(s['shareholder_return'])} | Buybacks + Dividends |",
        "", "## Validation", "",
        f"- Cash Reconciliation: Beginning + Net Change − Ending = **{fmt(s['cash_reconciliation_check'])}**",
    ]
    lines.append("- Status: ✓ **PASS**" if s["extraction_valid"] else "- Status: ✗ **FAIL** — cash reconciliation discrepancy detected")

    if result.prior_period is not None:
        prior = result.prior_period
        ind_prior = CashFlowIndicators(prior)
        yoy = CashFlowYoY(current=ind, prior=ind_prior)
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
        for k, label in _CF_ITEM_LABELS.items():
            fav = _CF_ITEM_FAVORABLE[k]
            trend = fmt_trend(pct_c[k], higher_is_better=fav) if fav is not None else "—"
            lines.append(f"| {label} | {fmt(abs_c[k])} | {fmt_pct(pct_c[k])} | {trend} |")

        lines += [
            "", "### Ratio Changes", "",
            "| Ratio | Change | Trend |",
            "|-------|-------:|-------|",
        ]
        for k, label in _CF_RATIO_LABELS.items():
            trend = fmt_trend(rat_c[k], higher_is_better=_CF_RATIO_FAVORABLE[k])
            lines.append(f"| {label} | {fmt_ratio(rat_c[k])} | {trend} |")

    lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
