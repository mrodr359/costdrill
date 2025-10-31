"""
Tests for data models.
"""

import pytest
from datetime import datetime

from costdrill.core.models import (
    CostAmount,
    CostBreakdown,
    CostMetrics,
    CostSummary,
    TimeSeriesCost,
)


def test_cost_amount_creation():
    """Test CostAmount creation and string representation."""
    cost = CostAmount(amount=123.45, unit="USD")
    assert cost.amount == 123.45
    assert cost.unit == "USD"
    assert str(cost) == "$123.45"


def test_cost_amount_from_aws_response():
    """Test CostAmount creation from AWS API response."""
    aws_response = {"Amount": "99.99", "Unit": "USD"}
    cost = CostAmount.from_aws_response(aws_response)
    assert cost.amount == 99.99
    assert cost.unit == "USD"


def test_cost_metrics_creation():
    """Test CostMetrics creation."""
    unblended = CostAmount(100.0)
    blended = CostAmount(95.0)

    metrics = CostMetrics(
        unblended_cost=unblended,
        blended_cost=blended,
        usage_quantity=50.5,
    )

    assert metrics.unblended_cost.amount == 100.0
    assert metrics.blended_cost.amount == 95.0
    assert metrics.usage_quantity == 50.5


def test_time_series_cost():
    """Test TimeSeriesCost model."""
    start = datetime(2025, 1, 1)
    end = datetime(2025, 1, 2)
    metrics = CostMetrics(unblended_cost=CostAmount(50.0))

    ts_cost = TimeSeriesCost(
        start_date=start,
        end_date=end,
        metrics=metrics,
        estimated=False,
    )

    assert ts_cost.start_date == start
    assert ts_cost.end_date == end
    assert ts_cost.total_cost == 50.0
    assert not ts_cost.estimated


def test_cost_breakdown():
    """Test CostBreakdown model."""
    cost = CostAmount(75.0)
    metrics = CostMetrics(unblended_cost=cost)

    breakdown = CostBreakdown(
        category="USAGE_TYPE",
        key="BoxUsage:t3.micro",
        cost=cost,
        metrics=metrics,
    )

    assert breakdown.category == "USAGE_TYPE"
    assert breakdown.key == "BoxUsage:t3.micro"
    assert breakdown.cost.amount == 75.0


def test_cost_summary():
    """Test CostSummary model."""
    start = datetime(2025, 1, 1)
    end = datetime(2025, 1, 31)

    time_series = [
        TimeSeriesCost(
            start_date=datetime(2025, 1, i),
            end_date=datetime(2025, 1, i + 1),
            metrics=CostMetrics(unblended_cost=CostAmount(10.0)),
        )
        for i in range(1, 6)
    ]

    summary = CostSummary(
        start_date=start,
        end_date=end,
        time_series=time_series,
        total_cost=CostAmount(50.0),
    )

    assert summary.start_date == start
    assert summary.end_date == end
    assert len(summary.time_series) == 5
    assert summary.total_cost.amount == 50.0

    # Test get_daily_costs
    daily_costs = summary.get_daily_costs()
    assert len(daily_costs) == 5
    assert all(cost == 10.0 for _, cost in daily_costs)


def test_cost_summary_get_breakdown_by_key():
    """Test filtering breakdowns by key."""
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
            category="USAGE_TYPE",
            key="DataTransfer-Out",
            cost=CostAmount(25.0),
            metrics=CostMetrics(unblended_cost=CostAmount(25.0)),
        ),
    ]

    summary = CostSummary(
        start_date=datetime(2025, 1, 1),
        end_date=datetime(2025, 1, 31),
        time_series=[],
        total_cost=CostAmount(175.0),
        breakdowns=breakdowns,
    )

    # Filter for t3 instances
    t3_breakdowns = summary.get_breakdown_by_key("t3")
    assert len(t3_breakdowns) == 2
    assert all("t3" in bd.key.lower() for bd in t3_breakdowns)

    # Filter for data transfer
    transfer_breakdowns = summary.get_breakdown_by_key("datatransfer")
    assert len(transfer_breakdowns) == 1
    assert "DataTransfer" in transfer_breakdowns[0].key
