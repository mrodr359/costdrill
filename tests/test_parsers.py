"""
Tests for Cost Explorer parsers.
"""

import pytest
from datetime import datetime

from costdrill.core.parsers import CostExplorerParser
from costdrill.core.models import CostAmount, CostMetrics


def test_parse_metrics():
    """Test parsing metrics from AWS response."""
    metrics_dict = {
        "UnblendedCost": {"Amount": "123.45", "Unit": "USD"},
        "BlendedCost": {"Amount": "120.00", "Unit": "USD"},
        "UsageQuantity": {"Amount": "100.5", "Unit": "N/A"},
    }

    metrics = CostExplorerParser.parse_metrics(metrics_dict)

    assert isinstance(metrics, CostMetrics)
    assert metrics.unblended_cost.amount == 123.45
    assert metrics.blended_cost.amount == 120.00
    assert metrics.usage_quantity == 100.5


def test_parse_time_series():
    """Test parsing a single time series result."""
    result_by_time = {
        "TimePeriod": {
            "Start": "2025-01-01",
            "End": "2025-01-02",
        },
        "Total": {
            "UnblendedCost": {"Amount": "50.00", "Unit": "USD"},
        },
        "Groups": [],
        "Estimated": False,
    }

    ts_cost = CostExplorerParser.parse_time_series(result_by_time)

    assert ts_cost.start_date == datetime(2025, 1, 1)
    assert ts_cost.end_date == datetime(2025, 1, 2)
    assert ts_cost.total_cost == 50.0
    assert not ts_cost.estimated


def test_parse_cost_and_usage_response():
    """Test parsing complete cost and usage response."""
    response = {
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2025-01-01", "End": "2025-01-02"},
                "Total": {
                    "UnblendedCost": {"Amount": "100.00", "Unit": "USD"},
                },
                "Groups": [],
                "Estimated": False,
            },
            {
                "TimePeriod": {"Start": "2025-01-02", "End": "2025-01-03"},
                "Total": {
                    "UnblendedCost": {"Amount": "150.00", "Unit": "USD"},
                },
                "Groups": [],
                "Estimated": False,
            },
        ]
    }

    summary = CostExplorerParser.parse_cost_and_usage_response(response)

    assert len(summary.time_series) == 2
    assert summary.total_cost.amount == 250.0
    assert summary.start_date == datetime(2025, 1, 1)
    assert summary.end_date == datetime(2025, 1, 3)


def test_parse_cost_and_usage_with_groups():
    """Test parsing response with grouped data."""
    response = {
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2025-01-01", "End": "2025-01-02"},
                "Total": {
                    "UnblendedCost": {"Amount": "200.00", "Unit": "USD"},
                },
                "Groups": [
                    {
                        "Keys": ["USAGE_TYPE$BoxUsage:t3.micro"],
                        "Metrics": {
                            "UnblendedCost": {"Amount": "80.00", "Unit": "USD"},
                        },
                    },
                    {
                        "Keys": ["USAGE_TYPE$DataTransfer-Out"],
                        "Metrics": {
                            "UnblendedCost": {"Amount": "120.00", "Unit": "USD"},
                        },
                    },
                ],
                "Estimated": False,
            }
        ]
    }

    summary = CostExplorerParser.parse_cost_and_usage_response(response)

    assert len(summary.breakdowns) == 2
    assert summary.breakdowns[0].category == "USAGE_TYPE"
    assert summary.breakdowns[0].key == "BoxUsage:t3.micro"
    assert summary.breakdowns[0].cost.amount == 80.0


def test_parse_empty_response():
    """Test parsing empty response."""
    response = {"ResultsByTime": []}

    summary = CostExplorerParser.parse_cost_and_usage_response(response)

    assert len(summary.time_series) == 0
    assert summary.total_cost.amount == 0.0


def test_aggregate_costs_by_category():
    """Test aggregating costs by category."""
    from costdrill.core.models import CostBreakdown

    breakdowns = [
        CostBreakdown(
            category="USAGE_TYPE",
            key="BoxUsage:t3.micro",
            cost=CostAmount(50.0),
            metrics=CostMetrics(unblended_cost=CostAmount(50.0)),
        ),
        CostBreakdown(
            category="USAGE_TYPE",
            key="BoxUsage:t3.large",
            cost=CostAmount(100.0),
            metrics=CostMetrics(unblended_cost=CostAmount(100.0)),
        ),
        CostBreakdown(
            category="REGION",
            key="us-east-1",
            cost=CostAmount(200.0),
            metrics=CostMetrics(unblended_cost=CostAmount(200.0)),
        ),
    ]

    aggregated = CostExplorerParser.aggregate_costs_by_category(breakdowns)

    assert "USAGE_TYPE" in aggregated
    assert "REGION" in aggregated
    assert aggregated["USAGE_TYPE"].amount == 150.0
    assert aggregated["REGION"].amount == 200.0
