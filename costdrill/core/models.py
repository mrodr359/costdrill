"""
Data models for AWS cost data.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class CostAmount:
    """Represents a cost amount with currency."""

    amount: float
    unit: str = "USD"

    def __str__(self) -> str:
        return f"${self.amount:.2f}"

    @classmethod
    def from_aws_response(cls, cost_dict: Dict[str, str]) -> "CostAmount":
        """
        Create CostAmount from AWS API response.

        Args:
            cost_dict: Dictionary with 'Amount' and 'Unit' keys

        Returns:
            CostAmount instance
        """
        return cls(
            amount=float(cost_dict.get("Amount", 0)),
            unit=cost_dict.get("Unit", "USD"),
        )


@dataclass
class CostMetrics:
    """Cost metrics for a time period."""

    unblended_cost: CostAmount
    blended_cost: Optional[CostAmount] = None
    amortized_cost: Optional[CostAmount] = None
    net_unblended_cost: Optional[CostAmount] = None
    net_amortized_cost: Optional[CostAmount] = None
    usage_quantity: Optional[float] = None


@dataclass
class TimeSeriesCost:
    """Cost data for a specific time period."""

    start_date: datetime
    end_date: datetime
    metrics: CostMetrics
    groups: List[Dict[str, str]] = field(default_factory=list)
    estimated: bool = False

    @property
    def total_cost(self) -> float:
        """Get the primary cost amount."""
        return self.metrics.unblended_cost.amount


@dataclass
class CostBreakdown:
    """Detailed cost breakdown by category."""

    category: str  # e.g., "USAGE_TYPE", "SERVICE", "REGION"
    key: str  # e.g., "BoxUsage:t3.micro", "EC2", "us-east-1"
    cost: CostAmount
    metrics: CostMetrics


@dataclass
class CostSummary:
    """Summary of costs over a time period."""

    start_date: datetime
    end_date: datetime
    time_series: List[TimeSeriesCost]
    total_cost: CostAmount
    breakdowns: List[CostBreakdown] = field(default_factory=list)
    dimension_values: Dict[str, List[str]] = field(default_factory=dict)

    def get_daily_costs(self) -> List[tuple[datetime, float]]:
        """
        Get list of (date, cost) tuples for daily costs.

        Returns:
            List of (date, cost) tuples
        """
        return [(ts.start_date, ts.total_cost) for ts in self.time_series]

    def get_breakdown_by_key(self, key: str) -> List[CostBreakdown]:
        """
        Get breakdowns filtered by specific key.

        Args:
            key: Key to filter by

        Returns:
            List of matching breakdowns
        """
        return [bd for bd in self.breakdowns if key.lower() in bd.key.lower()]


@dataclass
class CostForecast:
    """Cost forecast data."""

    start_date: datetime
    end_date: datetime
    mean_value: CostAmount
    prediction_interval_lower: CostAmount
    prediction_interval_upper: CostAmount
    time_series: List[TimeSeriesCost] = field(default_factory=list)


@dataclass
class AWSCredentials:
    """AWS credentials information."""

    account_id: str
    user_id: str
    arn: str
    region: Optional[str] = None
    profile: Optional[str] = None


@dataclass
class EC2CostDetails:
    """Detailed EC2 instance cost breakdown."""

    instance_id: str
    instance_type: str
    region: str
    total_cost: CostAmount
    compute_cost: CostAmount
    storage_cost: CostAmount
    data_transfer_cost: CostAmount
    other_costs: CostAmount
    running_hours: float
    cost_per_hour: float

    @property
    def cost_breakdown_percentage(self) -> Dict[str, float]:
        """
        Get cost breakdown as percentages.

        Returns:
            Dictionary of component: percentage
        """
        if self.total_cost.amount == 0:
            return {}

        total = self.total_cost.amount
        return {
            "compute": (self.compute_cost.amount / total) * 100,
            "storage": (self.storage_cost.amount / total) * 100,
            "data_transfer": (self.data_transfer_cost.amount / total) * 100,
            "other": (self.other_costs.amount / total) * 100,
        }
