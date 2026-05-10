"""Locate the balance sheet page in a 10-K PDF using keyword scoring."""

from src.shared.page_scoring import PageScore, score_page_generic, find_page_generic

TITLE_PHRASES = [
    "consolidated balance sheets",
    "consolidated balance sheet",
    "balance sheets",
    "balance sheet",
    "statement of financial position",
    "statements of financial position",
]

POSITIVE_KEYWORDS = [
    "total assets",
    "total liabilities",
    "total current assets",
    "total current liabilities",
    "stockholders' equity",
    "shareholders' equity",
    "stockholders\u2019 equity",
    "shareholders\u2019 equity",
    "cash and cash equivalents",
    "accounts receivable",
    "inventories",
    "inventory",
    "property, plant and equipment",
    "property and equipment",
    "goodwill",
    "intangible assets",
    "prepaid expenses",
    "other current assets",
    "accounts payable",
    "accrued expenses",
    "accrued liabilities",
    "long-term debt",
    "current portion of long-term debt",
    "deferred revenue",
    "operating lease liabilities",
    "retained earnings",
    "common stock",
    "additional paid-in capital",
    "treasury stock",
    "accumulated other comprehensive",
]

NEGATIVE_KEYWORDS = [
    "notes to consolidated financial statements",
    "notes to financial statements",
    "cash flows from operating",
    "cash flows from investing",
    "cash flows from financing",
    "net cash provided by",
    "net cash used in",
    "income from operations",
    "cost of revenue",
    "cost of goods sold",
    "gross profit",
    "operating expenses",
    "earnings per share",
    "net income per share",
    "diluted earnings per share",
    "revenue recognition",
    "significant accounting policies",
]


def score_page(text: str, page_num: int) -> PageScore:
    """Score a single page's likelihood of being the balance sheet."""
    return score_page_generic(text, page_num, TITLE_PHRASES, POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS)


def find_balance_sheet_page(pdf_path: str) -> PageScore:
    """Find the single most likely balance sheet page in a PDF."""
    return find_page_generic(pdf_path, TITLE_PHRASES, POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS, "balance sheet")


# if __name__ == "__main__":
#     print(find_balance_sheet_page(r"data/amz-10k.pdf"))