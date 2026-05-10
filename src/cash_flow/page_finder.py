"""Locate the cash flow statement page in a 10-K PDF using keyword scoring."""

from src.shared.page_scoring import PageScore, score_page_generic, find_page_generic

TITLE_PHRASES = [
    "consolidated statements of cash flows",
    "consolidated statement of cash flows",
    "statements of cash flows",
    "statement of cash flows",
    "cash flow statement",
    "cash flow statements",
]

POSITIVE_KEYWORDS = [
    # Section headers (both styles: "cash flows from ..." and bare "... activities:")
    "cash flows from operating activities",
    "cash flows from investing activities",
    "cash flows from financing activities",
    "operating activities:",
    "investing activities:",
    "financing activities:",
    # Net cash totals (various phrasings)
    "net cash provided by operating",
    "net cash used in operating",
    "net cash provided by investing",
    "net cash used in investing",
    "net cash provided by financing",
    "net cash used in financing",
    "net cash provided by (used in) operating",
    "net cash provided by (used in) investing",
    "net cash provided by (used in) financing",
    # Common line items
    "depreciation and amortization",
    "depreciation & amortization",
    "stock-based compensation",
    "deferred income taxes",
    "capital expenditures",
    "purchases of property and equipment",
    "purchases of property, plant and equipment",
    "purchases related to property and equipment",
    # Financing items
    "repayment of debt",
    "repayments of long-term debt",
    "repayments of short-term debt",
    "proceeds from long-term debt",
    "proceeds from short-term debt",
    "proceeds from debt",
    "repurchases of common stock",
    "payments related to repurchases of common stock",
    "principal repayments of finance leases",
    "principal repayments of financing obligations",
    "proceeds related to employee stock plans",
    "payments related to tax on restricted stock units",
    "dividends paid",
    # Cash beginning/end
    "net change in cash",
    "net increase (decrease) in cash",
    "change in cash and cash equivalents",
    "cash at beginning of period",
    "cash at end of period",
    "cash and cash equivalents at beginning of period",
    "cash and cash equivalents at end of period",
    "cash, cash equivalents, and restricted cash",
    "cash, cash equivalents, and restricted cash, beginning of period",
    # Supplemental
    "supplemental disclosures of cash flow information",
    "cash paid for income taxes",
    "cash paid for interest",
]

NEGATIVE_KEYWORDS = [
    "notes to consolidated financial statements", "notes to financial statements",
    "total assets", "total liabilities",
    "stockholders' equity", "shareholders' equity",
    "stockholders\u2019 equity", "shareholders\u2019 equity",
    "balance sheet", "earnings per share", "diluted earnings per share",
    "cost of revenue", "gross profit",
    "significant accounting policies", "revenue recognition",
]


def score_cash_flow_page(text: str, page_num: int) -> PageScore:
    return score_page_generic(text, page_num, TITLE_PHRASES, POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS)


def find_cash_flow_page(pdf_path: str) -> PageScore:
    return find_page_generic(pdf_path, TITLE_PHRASES, POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS, "cash flow statement")

if __name__ == "__main__":
    print("AMZ:", find_cash_flow_page(r"data/amz-10k.pdf"))
    print()
    print("NVDA:", find_cash_flow_page(r"data/nvda-10k.pdf"))