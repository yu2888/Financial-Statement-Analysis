"""Cash flow statement extraction using OpenAI-compatible API."""

import json
import logging

from openai import OpenAI
from PIL import Image

from src.shared.llm import image_to_base64, parse_json_response, stream_response, MAX_RETRIES
from .models import CashFlowData, CashFlowMultiPeriod

logger = logging.getLogger(__name__)

CASH_FLOW_MULTI_PERIOD_PROMPT = """You are a financial data extraction assistant.
Analyze this cash flow statement image and extract ALL numerical values for BOTH periods shown.

Return ONLY a valid JSON object with two top-level keys: "current_period" and "prior_period".
Each key should contain an object with the exact fields listed below.
If only one period is present, set "prior_period" to null.

All monetary values should be plain numbers (no commas, no currency symbols).
Do NOT convert units — keep values as shown on the document (e.g. if stated in millions, keep the millions figure).
Use 0.0 for any field not found.
Use NEGATIVE numbers for cash outflows (e.g. capital expenditures, debt repaid, shares repurchased, dividends paid).

{
  "current_period": {
    "net_income": 0.0, "depreciation_amortization": 0.0, "stock_based_compensation": 0.0,
    "changes_in_working_capital": 0.0, "other_operating_adjustments": 0.0,
    "net_cash_from_operations": 0.0, "capital_expenditures": 0.0, "acquisitions": 0.0,
    "purchases_of_investments": 0.0, "sales_of_investments": 0.0,
    "other_investing_activities": 0.0, "net_cash_from_investing": 0.0,
    "debt_issued": 0.0, "debt_repaid": 0.0, "shares_issued": 0.0,
    "shares_repurchased": 0.0, "dividends_paid": 0.0,
    "other_financing_activities": 0.0, "net_cash_from_financing": 0.0,
    "net_change_in_cash": 0.0, "cash_beginning_of_period": 0.0, "cash_end_of_period": 0.0,
    "company_name": "Unknown", "period": "Unknown", "currency": "USD", "units": "millions"
  },
  "prior_period": null
}

IMPORTANT:
- Return ONLY the JSON directly, no markdown fences, no explanation.
- "current_period" is the MOST RECENT period shown.
- "prior_period" is the EARLIER comparative period, or null if only one period is shown.
- Map line items to the closest matching key above.
- Return 0.0 for any field not found.
- "period" should be the full date or range shown (e.g. "Year Ended December 31, 2024"), not just the year.
- "units" should reflect the scale stated on the document: "millions", "thousands", "billions", or "ones".
"""


def extract_cash_flow_from_image(
    img: Image.Image,
    model_name: str = "qwen3-vl:latest",
    base_url: str = "http://localhost:11434/v1/",
    api_key: str = "EMPTY",
    verbose: bool = False,
) -> CashFlowMultiPeriod:
    client = OpenAI(base_url=base_url, api_key=api_key)
    b64 = image_to_base64(img)
    messages = [{"role": "user", "content": [
        {"type": "text", "text": CASH_FLOW_MULTI_PERIOD_PROMPT},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
    ]}]

    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        if attempt > 1:
            logger.info("  Retry %d/%d...", attempt, MAX_RETRIES)
        logger.info("  --- LLM stream start (cash flow) ---")
        _, raw, usage = stream_response(client, model_name, messages, verbose=verbose)
        logger.info("  --- LLM stream end ---")
        if usage:
            logger.info("  Token usage: %s", json.dumps(usage))
        try:
            data = parse_json_response(raw)
            if "current_period" in data:
                current = CashFlowData(**data["current_period"])
                prior = CashFlowData(**data["prior_period"]) if data.get("prior_period") else None
                return CashFlowMultiPeriod(current_period=current, prior_period=prior)
            else:
                return CashFlowMultiPeriod(current_period=CashFlowData(**data), prior_period=None)
        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            logger.warning("  ⚠ Attempt %d: JSON parse failed: %s", attempt, e)

    raise ValueError(f"Failed to extract cash flow statement after {MAX_RETRIES} attempts: {last_error}")
