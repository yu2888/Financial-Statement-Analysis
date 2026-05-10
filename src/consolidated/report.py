"""Generate a consolidated financial analysis report from all three statements."""

import json
from pathlib import Path

from src.shared.formatting import fmt, units_note
from src.balance_sheet.indicators import FinancialIndicators
from src.income_statement.indicators import IncomeStatementIndicators
from src.cash_flow.indicators import CashFlowIndicators
from .models import FullFinancialResult


def _cross_statement_indicators(bs: FinancialIndicators, is_ind: IncomeStatementIndicators, cf: CashFlowIndicators) -> dict:
    bs_data, is_data, cf_data = bs.data, is_ind.data, cf.data
    roa = (is_data.net_income / bs_data.total_assets * 100) if bs_data.total_assets else None
    roe = (is_data.net_income / bs_data.total_shareholders_equity * 100) if bs_data.total_shareholders_equity else None
    asset_turnover = (is_data.total_revenue / bs_data.total_assets) if bs_data.total_assets else None
    ebitda = is_data.operating_income + cf_data.depreciation_amortization
    total_debt = bs_data.short_term_debt + bs_data.long_term_debt
    debt_to_ebitda = (total_debt / ebitda) if ebitda else None
    fcf = cf.free_cash_flow()
    fcf_yield = (fcf / bs_data.total_shareholders_equity * 100) if bs_data.total_shareholders_equity else None
    ocf_to_debt = (cf_data.net_cash_from_operations / total_debt) if total_debt else None
    cf_interest_coverage = (cf_data.net_cash_from_operations / is_data.interest_expense) if is_data.interest_expense else None
    return {
        "return_on_assets": roa, "return_on_equity": roe, "asset_turnover": asset_turnover,
        "ebitda": ebitda, "debt_to_ebitda": debt_to_ebitda, "free_cash_flow": fcf,
        "fcf_yield": fcf_yield, "ocf_to_debt": ocf_to_debt, "cf_interest_coverage": cf_interest_coverage,
    }


def save_consolidated_json(result: FullFinancialResult, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output: dict = {"balance_sheet": None, "income_statement": None, "cash_flow": None, "cross_statement_indicators": None}
    bs_ind = is_ind = cf_ind = None
    if result.balance_sheet:
        bs = result.balance_sheet.current_period
        bs_ind = FinancialIndicators(bs)
        output["balance_sheet"] = {"current_period": bs.model_dump(), "prior_period": result.balance_sheet.prior_period.model_dump() if result.balance_sheet.prior_period else None, "indicators": bs_ind.summary()}
    if result.income_statement:
        is_cur = result.income_statement.current_period
        is_ind = IncomeStatementIndicators(is_cur)
        output["income_statement"] = {"current_period": is_cur.model_dump(), "prior_period": result.income_statement.prior_period.model_dump() if result.income_statement.prior_period else None, "indicators": is_ind.summary()}
    if result.cash_flow:
        cf_cur = result.cash_flow.current_period
        cf_ind = CashFlowIndicators(cf_cur)
        output["cash_flow"] = {"current_period": cf_cur.model_dump(), "prior_period": result.cash_flow.prior_period.model_dump() if result.cash_flow.prior_period else None, "indicators": cf_ind.summary()}
    if bs_ind and is_ind and cf_ind:
        output["cross_statement_indicators"] = _cross_statement_indicators(bs_ind, is_ind, cf_ind)
    output_path.write_text(json.dumps(output, indent=2))
    return output_path


def save_consolidated_report(result: FullFinancialResult, output_path: Path) -> Path:
    company, period, currency, units_str = "Unknown", "Unknown", "USD", "millions"
    for stmt in [result.balance_sheet, result.income_statement, result.cash_flow]:
        if stmt:
            cur = stmt.current_period
            company, period, currency = cur.company_name, cur.period, cur.currency
            units_str = getattr(cur, "units", "millions")
            if company != "Unknown":
                break

    lines = [
        f"# Consolidated Financial Analysis — {company}", "",
        f"- Period: {period}",
        f"- Currency: {currency}",
        f"- {units_note(units_str, currency)}",
        "",
    ]
    bs_ind = is_ind = cf_ind = None

    if result.balance_sheet:
        bs = result.balance_sheet.current_period
        bs_ind = FinancialIndicators(bs)
        s = bs_ind.summary()
        lines += ["## Balance Sheet Summary", "", "| Indicator | Value |", "|-----------|------:|",
                   f"| Total Assets | {fmt(bs.total_assets)} |", f"| Total Liabilities | {fmt(bs.total_liabilities)} |",
                   f"| Total Equity | {fmt(bs.total_shareholders_equity)} |", f"| Current Ratio | {fmt(s['current_ratio'])} |",
                   f"| Quick Ratio | {fmt(s['quick_ratio'])} |", f"| Debt-to-Equity | {fmt(s['debt_to_equity'])} |",
                   f"| Working Capital | {fmt(s['working_capital'])} |", ""]

    if result.income_statement:
        is_cur = result.income_statement.current_period
        is_ind = IncomeStatementIndicators(is_cur)
        s = is_ind.summary()
        lines += ["## Income Statement Summary", "", "| Indicator | Value |", "|-----------|------:|",
                   f"| Total Revenue | {fmt(is_cur.total_revenue)} |", f"| Gross Profit | {fmt(is_cur.gross_profit)} |",
                   f"| Operating Income | {fmt(is_cur.operating_income)} |", f"| Net Income | {fmt(is_cur.net_income)} |",
                   f"| Gross Margin | {fmt(s['gross_margin'])}% |", f"| Operating Margin | {fmt(s['operating_margin'])}% |",
                   f"| Net Margin | {fmt(s['net_margin'])}% |", ""]

    if result.cash_flow:
        cf_cur = result.cash_flow.current_period
        cf_ind = CashFlowIndicators(cf_cur)
        s = cf_ind.summary()
        lines += ["## Cash Flow Summary", "", "| Indicator | Value |", "|-----------|------:|",
                   f"| Operating Cash Flow | {fmt(cf_cur.net_cash_from_operations)} |",
                   f"| Investing Cash Flow | {fmt(cf_cur.net_cash_from_investing)} |",
                   f"| Financing Cash Flow | {fmt(cf_cur.net_cash_from_financing)} |",
                   f"| Free Cash Flow | {fmt(s['free_cash_flow'])} |",
                   f"| OCF / Net Income | {fmt(s['operating_cash_flow_ratio'])} |",
                   f"| CapEx to OCF | {fmt(s['capex_to_ocf'])}% |", ""]

    if bs_ind and is_ind and cf_ind:
        cross = _cross_statement_indicators(bs_ind, is_ind, cf_ind)
        lines += ["## Cross-Statement Indicators", "",
                   "| Indicator | Value | Interpretation |", "|-----------|------:|----------------|",
                   f"| Return on Assets (ROA) | {fmt(cross['return_on_assets'])}% | Net Income / Total Assets |",
                   f"| Return on Equity (ROE) | {fmt(cross['return_on_equity'])}% | Net Income / Total Equity |",
                   f"| Asset Turnover | {fmt(cross['asset_turnover'])} | Revenue / Total Assets |",
                   f"| EBITDA | {fmt(cross['ebitda'])} | Operating Income + D&A |",
                   f"| Debt-to-EBITDA | {fmt(cross['debt_to_ebitda'])} | Total Debt / EBITDA |",
                   f"| Free Cash Flow | {fmt(cross['free_cash_flow'])} | OCF − CapEx |",
                   f"| FCF Yield | {fmt(cross['fcf_yield'])}% | FCF / Total Equity |",
                   f"| OCF-to-Debt | {fmt(cross['ocf_to_debt'])} | Operating CF / Total Debt |",
                   f"| CF Interest Coverage | {fmt(cross['cf_interest_coverage'])} | OCF / Interest Expense |", ""]

    lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
