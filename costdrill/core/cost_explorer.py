"""
Cost Explorer API interactions and data processing.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError

from costdrill.core.aws_client import AWSClient
from costdrill.core.exceptions import (
    CostExplorerAPIError,
    CostExplorerNotEnabledException,
    InvalidDateRangeError,
    RateLimitExceededError,
)
from costdrill.core.models import CostForecast, CostSummary
from costdrill.core.parsers import CostExplorerParser

logger = logging.getLogger(__name__)


class CostExplorer:
    """Handler for AWS Cost Explorer API operations."""

    # AWS Cost Explorer service codes
    EC2_SERVICE = "Amazon Elastic Compute Cloud - Compute"
    S3_SERVICE = "Amazon Simple Storage Service"
    RDS_SERVICE = "Amazon Relational Database Service"

    def __init__(self, aws_client: AWSClient):
        """
        Initialize Cost Explorer.

        Args:
            aws_client: AWS client instance
        """
        self.aws_client = aws_client
        self.client = aws_client.get_cost_explorer_client()
        self.parser = CostExplorerParser()

    def _validate_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> None:
        """
        Validate date range for Cost Explorer API.

        Args:
            start_date: Start date
            end_date: End date

        Raises:
            InvalidDateRangeError: If date range is invalid
        """
        if start_date >= end_date:
            raise InvalidDateRangeError(
                "Start date must be before end date"
            )

        # AWS Cost Explorer has data going back only ~14 months
        max_past = datetime.now() - timedelta(days=425)
        if start_date < max_past:
            raise InvalidDateRangeError(
                "Start date too far in the past. AWS Cost Explorer "
                "data is available for approximately 14 months."
            )

        # Can't query future dates (except for forecasts)
        if start_date > datetime.now():
            raise InvalidDateRangeError(
                "Start date cannot be in the future"
            )

    def _handle_api_error(self, error: ClientError) -> None:
        """
        Handle Cost Explorer API errors.

        Args:
            error: ClientError from boto3

        Raises:
            Appropriate CostDrill exception
        """
        error_code = error.response.get("Error", {}).get("Code", "")
        error_message = error.response.get("Error", {}).get("Message", "")

        logger.error(f"Cost Explorer API error: {error_code} - {error_message}")

        if error_code == "AccessDeniedException":
            raise CostExplorerNotEnabledException() from error
        elif error_code == "ThrottlingException":
            raise RateLimitExceededError() from error
        elif error_code == "DataUnavailableException":
            raise CostExplorerAPIError(
                "Cost data is not yet available for this time period",
                error_code
            ) from error
        elif error_code == "InvalidNextTokenException":
            raise CostExplorerAPIError(
                "Invalid pagination token", error_code
            ) from error
        else:
            raise CostExplorerAPIError(error_message, error_code) from error

    def get_cost_and_usage(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        granularity: str = "DAILY",
        metrics: Optional[List[str]] = None,
        group_by: Optional[List[Dict[str, str]]] = None,
        filter_expression: Optional[Dict[str, Any]] = None,
    ) -> CostSummary:
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
            Parsed CostSummary object

        Raises:
            InvalidDateRangeError: If date range is invalid
            CostExplorerAPIError: If API call fails
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now()

        # Validate date range
        self._validate_date_range(start_date, end_date)

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

        try:
            logger.info(
                f"Fetching cost data from {start_date.date()} to {end_date.date()}"
            )
            response = self.client.get_cost_and_usage(**params)
            return self.parser.parse_cost_and_usage_response(response)

        except ClientError as e:
            self._handle_api_error(e)

    def get_ec2_costs(
        self,
        instance_id: Optional[str] = None,
        region: Optional[str] = None,
        days: int = 30,
    ) -> CostSummary:
        """
        Get EC2 costs with optional filtering and breakdown by usage type.

        Args:
            instance_id: Specific EC2 instance ID
            region: AWS region filter
            days: Number of days to retrieve (defaults to 30)

        Returns:
            CostSummary with EC2 costs broken down by usage type

        Raises:
            InvalidDateRangeError: If days is invalid
            CostExplorerAPIError: If API call fails
        """
        if days <= 0:
            raise InvalidDateRangeError("Days must be greater than 0")

        filters = []

        # Always filter by EC2 service
        filters.append({
            "Dimensions": {
                "Key": "SERVICE",
                "Values": [self.EC2_SERVICE]
            }
        })

        if instance_id:
            filters.append({
                "Dimensions": {
                    "Key": "RESOURCE_ID",
                    "Values": [instance_id]
                }
            })

        if region:
            filters.append({
                "Dimensions": {
                    "Key": "REGION",
                    "Values": [region]
                }
            })

        # Construct filter expression
        filter_expression: Dict[str, Any]
        if len(filters) == 1:
            filter_expression = filters[0]
        else:
            filter_expression = {"And": filters}

        start_date = datetime.now() - timedelta(days=days)
        end_date = datetime.now()

        logger.info(f"Fetching EC2 costs for instance={instance_id}, region={region}")

        return self.get_cost_and_usage(
            start_date=start_date,
            end_date=end_date,
            filter_expression=filter_expression,
            group_by=[{"Type": "DIMENSION", "Key": "USAGE_TYPE"}],
        )

    def get_service_costs(
        self,
        service: str,
        days: int = 30,
        group_by_dimension: Optional[str] = None,
    ) -> CostSummary:
        """
        Get costs for a specific AWS service.

        Args:
            service: AWS service name (e.g., "Amazon EC2", "Amazon S3")
            days: Number of days to retrieve (defaults to 30)
            group_by_dimension: Optional dimension to group by (e.g., "USAGE_TYPE", "REGION")

        Returns:
            CostSummary for the service

        Raises:
            InvalidDateRangeError: If days is invalid
            CostExplorerAPIError: If API call fails
        """
        if days <= 0:
            raise InvalidDateRangeError("Days must be greater than 0")

        filter_expression = {
            "Dimensions": {
                "Key": "SERVICE",
                "Values": [service]
            }
        }

        group_by = None
        if group_by_dimension:
            group_by = [{"Type": "DIMENSION", "Key": group_by_dimension}]

        start_date = datetime.now() - timedelta(days=days)
        end_date = datetime.now()

        logger.info(f"Fetching costs for service: {service}")

        return self.get_cost_and_usage(
            start_date=start_date,
            end_date=end_date,
            filter_expression=filter_expression,
            group_by=group_by,
        )

    def get_cost_forecast(
        self,
        days: int = 30,
        metric: str = "UNBLENDED_COST",
    ) -> CostForecast:
        """
        Get cost forecast for specified period.

        Args:
            days: Number of days to forecast (default: 30)
            metric: Metric to forecast (default: UNBLENDED_COST)

        Returns:
            CostForecast object with prediction data

        Raises:
            InvalidDateRangeError: If forecast period is invalid
            CostExplorerAPIError: If API call fails
        """
        if days <= 0 or days > 365:
            raise InvalidDateRangeError(
                "Forecast days must be between 1 and 365"
            )

        start_date = datetime.now()
        end_date = datetime.now() + timedelta(days=days)

        try:
            logger.info(f"Fetching cost forecast for next {days} days")
            response = self.client.get_cost_forecast(
                TimePeriod={
                    "Start": start_date.strftime("%Y-%m-%d"),
                    "End": end_date.strftime("%Y-%m-%d"),
                },
                Metric=metric,
                Granularity="MONTHLY",
            )
            return self.parser.parse_forecast_response(response)

        except ClientError as e:
            self._handle_api_error(e)

    def get_cost_by_tag(
        self,
        tag_key: str,
        tag_value: Optional[str] = None,
        days: int = 30,
    ) -> CostSummary:
        """
        Get costs grouped by tag.

        Args:
            tag_key: Tag key to filter/group by
            tag_value: Optional specific tag value to filter
            days: Number of days to retrieve (defaults to 30)

        Returns:
            CostSummary grouped by tag

        Raises:
            InvalidDateRangeError: If days is invalid
            CostExplorerAPIError: If API call fails
        """
        if days <= 0:
            raise InvalidDateRangeError("Days must be greater than 0")

        start_date = datetime.now() - timedelta(days=days)
        end_date = datetime.now()

        filter_expression = None
        if tag_value:
            filter_expression = {
                "Tags": {
                    "Key": tag_key,
                    "Values": [tag_value]
                }
            }

        group_by = [{"Type": "TAG", "Key": tag_key}]

        logger.info(f"Fetching costs by tag: {tag_key}")

        return self.get_cost_and_usage(
            start_date=start_date,
            end_date=end_date,
            filter_expression=filter_expression,
            group_by=group_by,
        )
