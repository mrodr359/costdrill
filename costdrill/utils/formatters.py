"""
Utility functions for formatting cost data.
"""

from typing import Any


def format_currency(amount: float, currency: str = "USD") -> str:
    """
    Format amount as currency string.

    Args:
        amount: Amount to format
        currency: Currency code (default: USD)

    Returns:
        Formatted currency string
    """
    symbol = "$" if currency == "USD" else currency
    return f"{symbol}{amount:,.2f}"


def format_percentage(value: float) -> str:
    """
    Format value as percentage string.

    Args:
        value: Value to format (e.g., 0.15 for 15%)

    Returns:
        Formatted percentage string
    """
    return f"{value * 100:.2f}%"


def truncate_string(text: str, max_length: int = 50) -> str:
    """
    Truncate string to maximum length with ellipsis.

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."
