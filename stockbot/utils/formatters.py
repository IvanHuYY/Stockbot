"""Display formatting utilities."""

from __future__ import annotations


def format_currency(amount: float) -> str:
    """Format as USD currency."""
    if amount >= 0:
        return f"${amount:,.2f}"
    return f"-${abs(amount):,.2f}"


def format_pct(value: float, decimals: int = 2) -> str:
    """Format as percentage."""
    return f"{value * 100:.{decimals}f}%"


def format_number(value: float, decimals: int = 2) -> str:
    """Format a number with commas."""
    return f"{value:,.{decimals}f}"
