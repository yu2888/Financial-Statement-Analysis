"""Locate the income statement page in a 10-K PDF using keyword scoring."""

from src.shared.page_scoring import PageScore, score_page_generic, find_page_generic

TITLE_PHRASES = [
    "consolidated statements of operations",
    "consolidated statement of operations",
    "consolidated statements of income",
    "consolidated statement of income",
    "statements of operations",
    "statement of operations",
    "statements of income",
    "statement of income",
    "consolidated statements of earnings",
    "statements of comprehensive income",
]

POSITIVE_KEYWORDS = [
    "total revenue", "net sales", "net revenue", "cost of revenue",
    "cost of goods sold", "cost of sales", "gross profit",
    "operating income", "operating expenses", "research and development",
    "selling, general and administrative", "selling, general & administrative",
    "income from operations", "income before income taxes",
    "income tax expense", "income tax benefit", "net income", "net loss",
    "earnings per share", "basic earnings per share", "diluted earnings per share",
    "net income per share", "weighted average shares", "weighted-average shares",
    "interest income", "interest expense", "other income",
]

NEGATIVE_KEYWORDS = [
    "notes to consolidated financial statements", "notes to financial statements",
    "cash flows from operating", "cash flows from investing", "cash flows from financing",
    "total assets", "total liabilities",
    "stockholders' equity", "shareholders' equity",
    "stockholders\u2019 equity", "shareholders\u2019 equity",
    "balance sheet", "significant accounting policies", "revenue recognition",
]


def score_income_statement_page(text: str, page_num: int) -> PageScore:
    return score_page_generic(text, page_num, TITLE_PHRASES, POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS)


def find_income_statement_page(pdf_path: str) -> PageScore:
    return find_page_generic(pdf_path, TITLE_PHRASES, POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS, "income statement")

if __name__ == "__main__":
    print("AMZ:", find_income_statement_page(r"data/amz-10k.pdf"))
    print()
    print("NVDA:", find_income_statement_page(r"data/nvda-10k.pdf"))