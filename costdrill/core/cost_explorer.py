"""
Cost Explorer API interactions and data processing.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from costdrill.core.aws_client import AWSClient


class CostExplorer:
    """Handler for AWS Cost Explorer API operations."""

    def __init__(self, aws_client: AWSClient):
        """
        Initialize Cost Explorer.

        Args:
            aws_client: AWS client instance
        """
        self.client = aws_client.get_cost_explorer_client()

    def get_cost_and_usage(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        granularity: str = "DAILY",
        metrics: Optional[List[str]] = None,
        group_by: Optional[List[Dict[str, str]]] = None,
        filter_expression: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get cost and usage data from AWS Cost Explorer.

        Args:
            start_date: Start date for cost data (defaults to 30 days ago)
            end_date: End date for cost data (defaults to today)
            granularity: Data granularity (DAILY, MONTHLY, HOURLY)
            metrics: Metrics to retrieve (defaults to UnblendedCost)
            group_by: Grouping dimensions
            filter_expression: Filter for cost data

        Returns:
            Cost and usage data from AWS Cost Explorer API
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now()

        if metrics is None:
            metrics = ["UnblendedCost"]

        params: Dict[str, Any] = {
            "TimePeriod": {
                "Start": start_date.strftime("%Y-%m-%d"),
                "End": end_date.strftime("%Y-%m-%d"),
            },
            "Granularity": granularity,
            "Metrics": metrics,
        }

        if group_by:
            params["GroupBy"] = group_by

        if filter_expression:
            params["Filter"] = filter_expression

        return self.client.get_cost_and_usage(**params)

    def get_ec2_costs(
        self,
        instance_id: Optional[str] = None,
        region: Optional[str] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get EC2 costs with optional filtering.

        Args:
            instance_id: Specific EC2 instance ID
            region: AWS region filter
            days: Number of days to retrieve (defaults to 30)

        Returns:
            EC2 cost data
        """
        filter_expression: Dict[str, Any] = {
            "And": [
                {"Dimensions": {"Key": "SERVICE", "Values": ["Amazon Elastic Compute Cloud - Compute"]}}
            ]
        }

        if instance_id:
            filter_expression["And"].append(
                {"Dimensions": {"Key": "INSTANCE_ID", "Values": [instance_id]}}
            )

        if region:
            filter_expression["And"].append(
                {"Dimensions": {"Key": "REGION", "Values": [region]}}
            )

        start_date = datetime.now() - timedelta(days=days)
        end_date = datetime.now()

        return self.get_cost_and_usage(
            start_date=start_date,
            end_date=end_date,
            filter_expression=filter_expression,
            group_by=[{"Type": "DIMENSION", "Key": "USAGE_TYPE"}],
        )

    def get_cost_forecast(
        self,
        days: int = 30,
        metric: str = "UNBLENDED_COST",
    ) -> Dict[str, Any]:
        """
        Get cost forecast for specified period.

        Args:
            days: Number of days to forecast
            metric: Metric to forecast

        Returns:
            Cost forecast data
        """
        start_date = datetime.now()
        end_date = datetime.now() + timedelta(days=days)

        return self.client.get_cost_forecast(
            TimePeriod={
                "Start": start_date.strftime("%Y-%m-%d"),
                "End": end_date.strftime("%Y-%m-%d"),
            },
            Metric=metric,
            Granularity="MONTHLY",
        )
