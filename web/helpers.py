"""Helper functions for frontend data rendering logic.

Pure functions used by the backend to prepare data for the frontend dashboard:
health zone classification, trend arrows, financial formatting, and YoY emphasis.
"""


def classify_health_zone(
    value: float | None,
    low_boundary: float,
    high_boundary: float,
    inverted: bool = False,
) -> str:
    """Classify a financial ratio into a health zone.

    For normal metrics (higher is better, inverted=False):
        value < low_boundary  → "concern"
        low_boundary ≤ value ≤ high_boundary → "adequate"
        value > high_boundary → "strong"

    For inverted metrics (lower is better, e.g. debt-to-equity, inverted=True):
        value < low_boundary  → "strong"
        low_boundary ≤ value ≤ high_boundary → "adequate"
        value > high_boundary → "concern"

    Returns "unknown" if value is None.
    """
    if value is None:
        return "unknown"

    if inverted:
        if value < low_boundary:
            return "strong"
        elif value <= high_boundary:
            return "adequate"
        else:
            return "concern"
    else:
        if value < low_boundary:
            return "concern"
        elif value <= high_boundary:
            return "adequate"
        else:
            return "strong"


def compute_trend_arrow(
    change_value: float | None,
    higher_is_better: bool = True,
) -> dict:
    """Compute trend arrow direction and color for a KPI metric.

    Returns a dict with:
        "direction": "up" if change > 0, "down" if change < 0, "flat" if 0
        "color": "green" if direction is favorable, "red" if unfavorable, "gray" if flat

    Favorable means: up + higher_is_better, or down + not higher_is_better.
    Returns direction="flat", color="gray" if change_value is None.
    """
    if change_value is None:
        return {"direction": "flat", "color": "gray"}

    if change_value > 0:
        direction = "up"
    elif change_value < 0:
        direction = "down"
    else:
        direction = "flat"

    if direction == "flat":
        color = "gray"
    elif (direction == "up" and higher_is_better) or (direction == "down" and not higher_is_better):
        color = "green"
    else:
        color = "red"

    return {"direction": direction, "color": color}


def format_financial_value(value: float | None) -> str:
    """Format a financial value with thousand separators and 2 decimal places.

    Examples:
        1234567.89 → "1,234,567.89"
        0.5        → "0.50"
        None       → "N/A"
    """
    if value is None:
        return "N/A"
    return f"{value:,.2f}"


def should_emphasize_yoy(pct_change: float | None) -> bool:
    """Return True if the year-over-year percentage change exceeds 10% in absolute value.

    Returns False if pct_change is None.
    """
    if pct_change is None:
        return False
    return abs(pct_change) > 10
