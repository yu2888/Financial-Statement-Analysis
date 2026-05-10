"""Shared formatting helpers for report generation."""


def fmt(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{value:,.{decimals}f}"


def fmt_pct(value: float | None) -> str:
    """Format a percentage change value."""
    if value is None:
        return "N/A"
    return f"{value:+,.2f}%"


def fmt_ratio(value: float | None, decimals: int = 4) -> str:
    """Format a ratio change with higher precision (basis-point level)."""
    if value is None:
        return "N/A"
    return f"{value:+,.{decimals}f}"


def fmt_trend(value: float | None, higher_is_better: bool = True) -> str:
    """Return a directional arrow with label based on change direction."""
    if value is None or value == 0.0:
        return "—"
    positive = value > 0
    favorable = positive if higher_is_better else not positive
    arrow = "↑" if positive else "↓"
    label = "Improving" if favorable else "Deteriorating"
    return f"{arrow} {label}"


def fmt_row(label: str, value: float, bold: bool = False, decimals: int = 2) -> str | None:
    """Build a markdown table row, returning None if value is 0.0 (not reported).

    Totals / subtotals (bold=True) are always shown.
    """
    if not bold and value == 0.0:
        return None
    formatted = fmt(value, decimals)
    if bold:
        return f"| **{label}** | **{formatted}** |"
    return f"| {label} | {formatted} |"


def units_note(units: str, currency: str = "USD") -> str:
    """Return a human-readable note about the value scale."""
    label_map = {
        "millions": "in millions",
        "thousands": "in thousands",
        "billions": "in billions",
        "ones": "in absolute value",
    }
    scale = label_map.get(units.lower(), f"in {units}")
    return f"All values {scale} of {currency} unless otherwise noted."
