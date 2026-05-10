"""Generic page scoring utilities for locating financial statements in PDFs."""

from dataclasses import dataclass

import fitz  # PyMuPDF

TITLE_WEIGHT = 10
KEYWORD_WEIGHT = 2
NEGATIVE_WEIGHT = -3


@dataclass
class PageScore:
    page_num: int  # 0-indexed
    score: float
    title_hits: list[str]
    keyword_hits: list[str]
    negative_hits: list[str]


def count_phrase_hits(text: str, phrases: list[str]) -> list[str]:
    """Return which phrases appear in the text (case-insensitive)."""
    text_lower = text.lower()
    return [p for p in phrases if p in text_lower]


def score_page_generic(
    text: str,
    page_num: int,
    title_phrases: list[str],
    positive_keywords: list[str],
    negative_keywords: list[str],
) -> PageScore:
    """Score a page against provided keyword lists."""
    title_hits = count_phrase_hits(text, title_phrases)
    keyword_hits = count_phrase_hits(text, positive_keywords)
    negative_hits = count_phrase_hits(text, negative_keywords)

    score = (
        len(title_hits) * TITLE_WEIGHT
        + len(keyword_hits) * KEYWORD_WEIGHT
        + len(negative_hits) * NEGATIVE_WEIGHT
    )

    return PageScore(
        page_num=page_num,
        score=score,
        title_hits=title_hits,
        keyword_hits=keyword_hits,
        negative_hits=negative_hits,
    )


def find_page_generic(
    pdf_path: str,
    title_phrases: list[str],
    positive_keywords: list[str],
    negative_keywords: list[str],
    statement_name: str = "financial statement",
) -> PageScore:
    """Find the single most likely page for a given statement type."""
    with fitz.open(pdf_path) as doc:
        best: PageScore | None = None
        for i, page in enumerate(doc):
            text = page.get_text()
            ps = score_page_generic(text, i, title_phrases, positive_keywords, negative_keywords)
            if best is None or ps.score > best.score:
                best = ps

    if best is None or best.score <= 0:
        raise ValueError(
            f"No {statement_name} page detected in {pdf_path}. "
            f"The PDF may not contain a standard {statement_name}."
        )
    return best
