"""Balance sheet extraction using OpenAI-compatible API."""

import json
import logging
from pathlib import Path

from openai import OpenAI
from PIL import Image

from src.shared.llm import image_to_base64, parse_json_response, stream_response, pdf_page_to_image, MAX_RETRIES
from .models import BalanceSheetData, MultiPeriodResult

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are a financial data extraction assistant.
Analyze this balance sheet image and extract ALL numerical values you can find.

Return ONLY a valid JSON object with these exact keys (use 0.0 if a value is not found).
All monetary values should be plain numbers (no commas, no currency symbols).
Do NOT convert units — keep values as shown on the document (e.g. if stated in millions, keep the millions figure).

{
  "cash_and_equivalents": 0.0,
  "accounts_receivable": 0.0,
  "marketable_securities": 0.0,
  "inventory": 0.0,
  "other_current_assets": 0.0,
  "total_current_assets": 0.0,
  "ppe": 0.0,
  "intangible_assets": 0.0,
  "other_non_current_assets": 0.0,
  "operating_lease_right_of_use": 0.0,
  "finance_lease_right_of_use": 0.0,
  "equity_investments": 0.0,
  "deferred_tax_assets": 0.0,
  "total_assets": 0.0,
  "accounts_payable": 0.0,
  "short_term_debt": 0.0,
  "deferred_revenue": 0.0,
  "other_current_liabilities": 0.0,
  "accrued_expenses": 0.0,
  "current_portion_long_term_debt": 0.0,
  "operating_lease_liabilities_current": 0.0,
  "total_current_liabilities": 0.0,
  "long_term_debt": 0.0,
  "other_non_current_liabilities": 0.0,
  "operating_lease_liabilities_non_current": 0.0,
  "total_liabilities": 0.0,
  "common_stock": 0.0,
  "retained_earnings": 0.0,
  "other_equity": 0.0,
  "additional_paid_in_capital": 0.0,
  "treasury_stock": 0.0,
  "accumulated_other_comprehensive_income": 0.0,
  "total_shareholders_equity": 0.0,
  "company_name": "Unknown",
  "period": "Unknown",
  "currency": "USD",
  "units": "millions"
}

IMPORTANT:
- Return ONLY the JSON directly, no markdown fences, no explanation.
- Use the MOST RECENT period's data if multiple periods are shown.
- Map line items to the closest matching key above.
- Return 0.0 for any field not found on the balance sheet.
- "period" should be the full date shown (e.g. "December 31, 2024"), not just the year.
- "units" should reflect the scale stated on the document: "millions", "thousands", "billions", or "ones".
"""

MULTI_PERIOD_PROMPT = """You are a financial data extraction assistant.
Analyze this balance sheet image and extract ALL numerical values for BOTH periods shown.

Return ONLY a valid JSON object with two top-level keys: "current_period" and "prior_period".
Each key should contain an object with the exact fields listed below.
If only one period is present, set "prior_period" to null.

All monetary values should be plain numbers (no commas, no currency symbols).
Do NOT convert units — keep values as shown on the document (e.g. if stated in millions, keep the millions figure).
Use 0.0 for any field not found on the balance sheet.

{
  "current_period": {
    "cash_and_equivalents": 0.0, "accounts_receivable": 0.0, "marketable_securities": 0.0,
    "inventory": 0.0, "other_current_assets": 0.0, "total_current_assets": 0.0,
    "ppe": 0.0, "intangible_assets": 0.0, "other_non_current_assets": 0.0,
    "operating_lease_right_of_use": 0.0, "finance_lease_right_of_use": 0.0,
    "equity_investments": 0.0, "deferred_tax_assets": 0.0, "total_assets": 0.0,
    "accounts_payable": 0.0, "short_term_debt": 0.0, "deferred_revenue": 0.0,
    "other_current_liabilities": 0.0, "accrued_expenses": 0.0,
    "current_portion_long_term_debt": 0.0, "operating_lease_liabilities_current": 0.0,
    "total_current_liabilities": 0.0, "long_term_debt": 0.0,
    "other_non_current_liabilities": 0.0, "operating_lease_liabilities_non_current": 0.0,
    "total_liabilities": 0.0, "common_stock": 0.0, "retained_earnings": 0.0,
    "other_equity": 0.0, "additional_paid_in_capital": 0.0, "treasury_stock": 0.0,
    "accumulated_other_comprehensive_income": 0.0, "total_shareholders_equity": 0.0,
    "company_name": "Unknown", "period": "Unknown", "currency": "USD", "units": "millions"
  },
  "prior_period": null
}

IMPORTANT:
- Return ONLY the JSON directly, no markdown fences, no explanation.
- "current_period" is the MOST RECENT period shown on the balance sheet.
- "prior_period" is the EARLIER comparative period, or null if only one period is shown.
- Map line items to the closest matching key above.
- Return 0.0 for any field not found on the balance sheet.
- "period" should be the full date shown (e.g. "December 31, 2024"), not just the year.
- "units" should reflect the scale stated on the document: "millions", "thousands", "billions", or "ones".
"""


def extract_from_image(
    img: Image.Image,
    model_name: str = "qwen3-vl:latest",
    base_url: str = "http://localhost:11434/v1/",
    api_key: str = "EMPTY",
    verbose: bool = False,
) -> BalanceSheetData:
    """Send a single balance sheet image to a vision model and parse the response."""
    client = OpenAI(base_url=base_url, api_key=api_key)
    b64 = image_to_base64(img)
    messages = [{"role": "user", "content": [
        {"type": "text", "text": EXTRACTION_PROMPT},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
    ]}]

    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        if attempt > 1:
            logger.info("  Retry %d/%d...", attempt, MAX_RETRIES)
        logger.info("  --- LLM stream start ---")
        _, raw, usage = stream_response(client, model_name, messages, verbose=verbose)
        logger.info("  --- LLM stream end ---")
        if usage:
            logger.info("  Token usage: %s", json.dumps(usage))
        try:
            data = parse_json_response(raw)
            return BalanceSheetData(**data)
        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            logger.warning("  ⚠ Attempt %d: JSON parse failed: %s", attempt, e)

    raise ValueError(f"Failed to extract valid JSON after {MAX_RETRIES} attempts: {last_error}")


def extract_multi_period_from_image(
    img: Image.Image,
    model_name: str = "qwen3-vl:latest",
    base_url: str = "http://localhost:11434/v1/",
    api_key: str = "EMPTY",
    verbose: bool = False,
) -> MultiPeriodResult:
    """Send a balance sheet image to a vision model and extract both periods."""
    client = OpenAI(base_url=base_url, api_key=api_key)
    b64 = image_to_base64(img)
    messages = [{"role": "user", "content": [
        {"type": "text", "text": MULTI_PERIOD_PROMPT},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
    ]}]

    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        if attempt > 1:
            logger.info("  Retry %d/%d...", attempt, MAX_RETRIES)
        logger.info("  --- LLM stream start (multi-period) ---")
        _, raw, usage = stream_response(client, model_name, messages, verbose=verbose)
        logger.info("  --- LLM stream end ---")
        if usage:
            logger.info("  Token usage: %s", json.dumps(usage))
        try:
            data = parse_json_response(raw)
            if "current_period" in data:
                current = BalanceSheetData(**data["current_period"])
                prior = BalanceSheetData(**data["prior_period"]) if data.get("prior_period") else None
                return MultiPeriodResult(current_period=current, prior_period=prior)
            else:
                return MultiPeriodResult(current_period=BalanceSheetData(**data), prior_period=None)
        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            logger.warning("  ⚠ Attempt %d: JSON parse failed: %s", attempt, e)

    raise ValueError(f"Failed to extract valid JSON after {MAX_RETRIES} attempts: {last_error}")


def extract_from_pdf(
    pdf_path: str,
    model_name: str = "qwen3-vl:latest",
    base_url: str = "http://localhost:11434/v1/",
    api_key: str = "EMPTY",
    pages: list[int] | None = None,
    verbose: bool = False,
) -> list[BalanceSheetData]:
    """Extract balance sheet data from one or more pages of a PDF."""
    import fitz
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if pages is None:
        with fitz.open(str(path)) as doc:
            pages = list(range(len(doc)))
    results: list[BalanceSheetData] = []
    for idx, page_num in enumerate(pages):
        logger.info("  Processing page %d (%d/%d)...", page_num + 1, idx + 1, len(pages))
        try:
            img = pdf_page_to_image(str(path), page_num)
            data = extract_from_image(img, model_name=model_name, base_url=base_url, api_key=api_key, verbose=verbose)
            results.append(data)
        except Exception as e:
            logger.error("  ⚠ Page %d extraction failed: %s", page_num + 1, e)
    return results
