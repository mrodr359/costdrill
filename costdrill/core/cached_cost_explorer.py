"""
Cached wrapper for Cost Explorer with automatic caching.
"""

import logging
from datetime import datetime
from typing import Optional

from costdrill.core.aws_client import AWSClient
from costdrill.core.cost_explorer import CostExplorer
from costdrill.core.models import CostForecast, CostSummary
from costdrill.utils.cache import SimpleCache, generate_cache_key

logger = logging.getLogger(__name__)


class CachedCostExplorer:
    """Cost Explorer with automatic response caching."""

    def __init__(
        self,
        aws_client: AWSClient,
        cache_ttl: int = 3600,
        enable_cache: bool = True,
    ):
        """
        Initialize cached Cost Explorer.

        Args:
            aws_client: AWS client instance
            cache_ttl: Cache time-to-live in seconds (default: 1 hour)
            enable_cache: Whether to enable caching (default: True)
        """
        self.cost_explorer = CostExplorer(aws_client)
        self.cache = SimpleCache(default_ttl=cache_ttl)
        self.enable_cache = enable_cache

    def get_cost_and_usage(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        granularity: str = "DAILY",
        **kwargs,
    ) -> CostSummary:
        """
        Get cost and usage data with caching.

        Args:
            start_date: Start date for cost data
            end_date: End date for cost data
            granularity: Data granularity
            **kwargs: Additional arguments passed to cost_explorer

        Returns:
            CostSummary object
        """
        if not self.enable_cache:
            return self.cost_explorer.get_cost_and_usage(
                start_date=start_date,
                end_date=end_date,
                granularity=granularity,
                **kwargs,
            )

        # Generate cache key
        cache_key = generate_cache_key(
            "cost_and_usage",
            start_date=start_date,
            end_date=end_date,
            granularity=granularity,
            **kwargs,
        )

        # Try to get from cache
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            logger.info("Returning cached cost and usage data")
            return cached_result

        # Fetch from API
        logger.info("Fetching fresh cost and usage data from API")
        result = self.cost_explorer.get_cost_and_usage(
            start_date=start_date,
            end_date=end_date,
            granularity=granularity,
            **kwargs,
        )

        # Cache the result
        self.cache.set(cache_key, result)

        return result

    def get_ec2_costs(
        self,
        instance_id: Optional[str] = None,
        region: Optional[str] = None,
        days: int = 30,
    ) -> CostSummary:
        """
        Get EC2 costs with caching.

        Args:
            instance_id: Specific EC2 instance ID
            region: AWS region filter
            days: Number of days to retrieve

        Returns:
            CostSummary with EC2 costs
        """
        if not self.enable_cache:
            return self.cost_explorer.get_ec2_costs(
                instance_id=instance_id,
                region=region,
                days=days,
            )

        cache_key = generate_cache_key(
            "ec2_costs",
            instance_id=instance_id,
            region=region,
            days=days,
        )

        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            logger.info("Returning cached EC2 costs")
            return cached_result

        logger.info("Fetching fresh EC2 costs from API")
        result = self.cost_explorer.get_ec2_costs(
            instance_id=instance_id,
            region=region,
            days=days,
        )

        self.cache.set(cache_key, result)
        return result

    def get_service_costs(
        self,
        service: str,
        days: int = 30,
        group_by_dimension: Optional[str] = None,
    ) -> CostSummary:
        """
        Get service costs with caching.

        Args:
            service: AWS service name
            days: Number of days to retrieve
            group_by_dimension: Optional dimension to group by

        Returns:
            CostSummary for the service
        """
        if not self.enable_cache:
            return self.cost_explorer.get_service_costs(
                service=service,
                days=days,
                group_by_dimension=group_by_dimension,
            )

        cache_key = generate_cache_key(
            "service_costs",
            service=service,
            days=days,
            group_by_dimension=group_by_dimension,
        )

        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            logger.info(f"Returning cached costs for service: {service}")
            return cached_result

        logger.info(f"Fetching fresh costs for service: {service}")
        result = self.cost_explorer.get_service_costs(
            service=service,
            days=days,
            group_by_dimension=group_by_dimension,
        )

        self.cache.set(cache_key, result)
        return result

    def get_cost_forecast(
        self,
        days: int = 30,
        metric: str = "UNBLENDED_COST",
    ) -> CostForecast:
        """
        Get cost forecast with caching.

        Args:
            days: Number of days to forecast
            metric: Metric to forecast

        Returns:
            CostForecast object
        """
        if not self.enable_cache:
            return self.cost_explorer.get_cost_forecast(
                days=days,
                metric=metric,
            )

        cache_key = generate_cache_key(
            "cost_forecast",
            days=days,
            metric=metric,
        )

        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            logger.info("Returning cached cost forecast")
            return cached_result

        logger.info("Fetching fresh cost forecast from API")
        result = self.cost_explorer.get_cost_forecast(
            days=days,
            metric=metric,
        )

        # Cache forecasts for shorter time (30 minutes)
        self.cache.set(cache_key, result, ttl=1800)
        return result

    def get_cost_by_tag(
        self,
        tag_key: str,
        tag_value: Optional[str] = None,
        days: int = 30,
    ) -> CostSummary:
        """
        Get costs by tag with caching.

        Args:
            tag_key: Tag key to filter/group by
            tag_value: Optional specific tag value
            days: Number of days to retrieve

        Returns:
            CostSummary grouped by tag
        """
        if not self.enable_cache:
            return self.cost_explorer.get_cost_by_tag(
                tag_key=tag_key,
                tag_value=tag_value,
                days=days,
            )

        cache_key = generate_cache_key(
            "cost_by_tag",
            tag_key=tag_key,
            tag_value=tag_value,
            days=days,
        )

        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            logger.info(f"Returning cached costs for tag: {tag_key}")
            return cached_result

        logger.info(f"Fetching fresh costs for tag: {tag_key}")
        result = self.cost_explorer.get_cost_by_tag(
            tag_key=tag_key,
            tag_value=tag_value,
            days=days,
        )

        self.cache.set(cache_key, result)
        return result

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self.cache.clear()
        logger.info("Cache cleared")

    def clear_expired_cache(self) -> int:
        """
        Clear expired cache entries.

        Returns:
            Number of entries cleared
        """
        return self.cache.clear_expired()
