"""
Parsers for AWS Cost Explorer API responses.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from costdrill.core.models import (
    CostAmount,
    CostBreakdown,
    CostForecast,
    CostMetrics,
    CostSummary,
    TimeSeriesCost,
)

logger = logging.getLogger(__name__)


class CostExplorerParser:
    """Parser for AWS Cost Explorer API responses."""

    @staticmethod
    def parse_metrics(metrics_dict: Dict[str, Dict[str, str]]) -> CostMetrics:
        """
        Parse metrics dictionary from AWS response.

        Args:
            metrics_dict: Metrics dictionary from API response

        Returns:
            CostMetrics object
        """
        return CostMetrics(
            unblended_cost=CostAmount.from_aws_response(
                metrics_dict.get("UnblendedCost", {"Amount": "0", "Unit": "USD"})
            ),
            blended_cost=(
                CostAmount.from_aws_response(metrics_dict["BlendedCost"])
                if "BlendedCost" in metrics_dict
                else None
            ),
            amortized_cost=(
                CostAmount.from_aws_response(metrics_dict["AmortizedCost"])
                if "AmortizedCost" in metrics_dict
                else None
            ),
            net_unblended_cost=(
                CostAmount.from_aws_response(metrics_dict["NetUnblendedCost"])
                if "NetUnblendedCost" in metrics_dict
                else None
            ),
            net_amortized_cost=(
                CostAmount.from_aws_response(metrics_dict["NetAmortizedCost"])
                if "NetAmortizedCost" in metrics_dict
                else None
            ),
            usage_quantity=(
                float(metrics_dict["UsageQuantity"]["Amount"])
                if "UsageQuantity" in metrics_dict
                else None
            ),
        )

    @staticmethod
    def parse_time_series(result_by_time: Dict[str, Any]) -> TimeSeriesCost:
        """
        Parse a single time series result.

        Args:
            result_by_time: Single ResultByTime from API response

        Returns:
            TimeSeriesCost object
        """
        time_period = result_by_time["TimePeriod"]
        start_date = datetime.strptime(time_period["Start"], "%Y-%m-%d")
        end_date = datetime.strptime(time_period["End"], "%Y-%m-%d")

        metrics = CostExplorerParser.parse_metrics(
            result_by_time.get("Total", {})
        )

        groups = result_by_time.get("Groups", [])
        estimated = result_by_time.get("Estimated", False)

        return TimeSeriesCost(
            start_date=start_date,
            end_date=end_date,
            metrics=metrics,
            groups=groups,
            estimated=estimated,
        )

    @staticmethod
    def parse_cost_and_usage_response(response: Dict[str, Any]) -> CostSummary:
        """
        Parse complete GetCostAndUsage API response.

        Args:
            response: API response from get_cost_and_usage

        Returns:
            CostSummary object
        """
        results_by_time = response.get("ResultsByTime", [])

        if not results_by_time:
            logger.warning("No cost data returned from API")
            # Return empty summary
            now = datetime.now()
            return CostSummary(
                start_date=now,
                end_date=now,
                time_series=[],
                total_cost=CostAmount(0.0),
                breakdowns=[],
            )

        # Parse time series
        time_series = [
            CostExplorerParser.parse_time_series(result)
            for result in results_by_time
        ]

        # Calculate total cost
        total_amount = sum(ts.total_cost for ts in time_series)
        total_cost = CostAmount(total_amount)

        # Parse breakdowns if grouped
        breakdowns: List[CostBreakdown] = []
        for result in results_by_time:
            for group in result.get("Groups", []):
                keys = group.get("Keys", [])
                metrics = CostExplorerParser.parse_metrics(
                    group.get("Metrics", {})
                )

                # Keys are in format like ["SERVICE$Amazon EC2"]
                # Extract the dimension and value
                if keys:
                    key_parts = keys[0].split("$")
                    category = key_parts[0] if len(key_parts) > 1 else "UNKNOWN"
                    key = key_parts[1] if len(key_parts) > 1 else keys[0]

                    breakdowns.append(
                        CostBreakdown(
                            category=category,
                            key=key,
                            cost=metrics.unblended_cost,
                            metrics=metrics,
                        )
                    )

        # Get dimension values if available
        dimension_values = {}
        if "DimensionValueAttributes" in response:
            for dim_attr in response["DimensionValueAttributes"]:
                value = dim_attr.get("Value", "")
                attributes = dim_attr.get("Attributes", {})
                if value:
                    dimension_values[value] = attributes

        # Get date range
        first_result = results_by_time[0]
        last_result = results_by_time[-1]
        start_date = datetime.strptime(
            first_result["TimePeriod"]["Start"], "%Y-%m-%d"
        )
        end_date = datetime.strptime(last_result["TimePeriod"]["End"], "%Y-%m-%d")

        return CostSummary(
            start_date=start_date,
            end_date=end_date,
            time_series=time_series,
            total_cost=total_cost,
            breakdowns=breakdowns,
            dimension_values=dimension_values,
        )

    @staticmethod
    def parse_forecast_response(response: Dict[str, Any]) -> CostForecast:
        """
        Parse GetCostForecast API response.

        Args:
            response: API response from get_cost_forecast

        Returns:
            CostForecast object
        """
        total = response.get("Total", {})
        time_period = response.get("ForecastResultsByTime", [])

        # Parse date range
        period = response.get("TimePeriod", {})
        start_date = datetime.strptime(period["Start"], "%Y-%m-%d")
        end_date = datetime.strptime(period["End"], "%Y-%m-%d")

        # Parse mean and prediction intervals
        mean_value = CostAmount.from_aws_response(
            total.get("Amount", {"Amount": "0", "Unit": "USD"})
            if isinstance(total, dict) and "Amount" in total
            else {"Amount": str(total), "Unit": "USD"}
        )

        prediction_interval_lower = CostAmount(0.0)
        prediction_interval_upper = CostAmount(0.0)

        # Parse time series if available
        time_series: List[TimeSeriesCost] = []
        for forecast_result in time_period:
            ts_period = forecast_result.get("TimePeriod", {})
            ts_start = datetime.strptime(ts_period["Start"], "%Y-%m-%d")
            ts_end = datetime.strptime(ts_period["End"], "%Y-%m-%d")

            mean = CostAmount.from_aws_response(
                forecast_result.get("MeanValue", {"Amount": "0", "Unit": "USD"})
            )

            metrics = CostMetrics(unblended_cost=mean)

            time_series.append(
                TimeSeriesCost(
                    start_date=ts_start,
                    end_date=ts_end,
                    metrics=metrics,
                    estimated=True,
                )
            )

        return CostForecast(
            start_date=start_date,
            end_date=end_date,
            mean_value=mean_value,
            prediction_interval_lower=prediction_interval_lower,
            prediction_interval_upper=prediction_interval_upper,
            time_series=time_series,
        )

    @staticmethod
    def aggregate_costs_by_category(
        breakdowns: List[CostBreakdown],
    ) -> Dict[str, CostAmount]:
        """
        Aggregate costs by category.

        Args:
            breakdowns: List of cost breakdowns

        Returns:
            Dictionary mapping category to total cost
        """
        aggregated: Dict[str, float] = {}

        for breakdown in breakdowns:
            if breakdown.category not in aggregated:
                aggregated[breakdown.category] = 0.0
            aggregated[breakdown.category] += breakdown.cost.amount

        return {
            category: CostAmount(amount)
            for category, amount in aggregated.items()
        }
