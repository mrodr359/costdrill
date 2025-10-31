"""
Tests for utility formatters.
"""

import pytest

from costdrill.utils.formatters import format_currency, format_percentage, truncate_string


def test_format_currency():
    """Test currency formatting."""
    assert format_currency(100.0) == "$100.00"
    assert format_currency(1234.56) == "$1,234.56"
    assert format_currency(0.99) == "$0.99"


def test_format_percentage():
    """Test percentage formatting."""
    assert format_percentage(0.15) == "15.00%"
    assert format_percentage(0.5) == "50.00%"
    assert format_percentage(1.0) == "100.00%"


def test_truncate_string():
    """Test string truncation."""
    short_text = "Short"
    assert truncate_string(short_text, 10) == "Short"

    long_text = "This is a very long text that needs to be truncated"
    truncated = truncate_string(long_text, 20)
    assert len(truncated) == 20
    assert truncated.endswith("...")
