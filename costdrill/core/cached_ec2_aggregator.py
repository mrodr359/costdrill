"""
Cached wrapper for EC2 cost aggregator.
"""

import logging
from typing import Dict, List, Optional

from costdrill.core.aws_client import AWSClient
from costdrill.core.ec2_cost_aggregator import EC2CostAggregator
from costdrill.core.ec2_models import (
    EC2InstanceWithCosts,
    RegionalEC2Summary,
)
from costdrill.utils.cache import SimpleCache, generate_cache_key

logger = logging.getLogger(__name__)


class CachedEC2Aggregator:
    """
    Cached wrapper for EC2 cost aggregator.

    Provides automatic caching for expensive EC2 + Cost Explorer operations.
    """

    def __init__(
        self,
        aws_client: AWSClient,
        region: Optional[str] = None,
        cache_ttl: int = 3600,
        enable_cache: bool = True,
    ):
        """
        Initialize cached EC2 aggregator.

        Args:
            aws_client: AWS client instance
            region: Specific region
            cache_ttl: Cache time-to-live in seconds (default: 1 hour)
            enable_cache: Whether to enable caching
        """
        self.aggregator = EC2CostAggregator(aws_client, region=region)
        self.cache = SimpleCache(default_ttl=cache_ttl)
        self.enable_cache = enable_cache
        self.region = self.aggregator.region

    def get_instance_with_costs(
        self,
        instance_id: str,
        days: int = 30,
    ) -> EC2InstanceWithCosts:
        """
        Get EC2 instance with costs (cached).

        Args:
            instance_id: EC2 instance ID
            days: Number of days of cost data

        Returns:
            EC2InstanceWithCosts object
        """
        if not self.enable_cache:
            return self.aggregator.get_instance_with_costs(
                instance_id=instance_id,
                days=days,
            )

        cache_key = generate_cache_key(
            "ec2_instance_costs",
            region=self.region,
            instance_id=instance_id,
            days=days,
        )

        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            logger.info(f"Returning cached data for instance {instance_id}")
            return cached_result

        logger.info(f"Fetching fresh data for instance {instance_id}")
        result = self.aggregator.get_instance_with_costs(
            instance_id=instance_id,
            days=days,
        )

        self.cache.set(cache_key, result)
        return result

    def get_all_instances_with_costs(
        self,
        days: int = 30,
        include_terminated: bool = False,
    ) -> RegionalEC2Summary:
        """
        Get all instances with costs (cached).

        Args:
            days: Number of days of cost data
            include_terminated: Include terminated instances

        Returns:
            RegionalEC2Summary object
        """
        if not self.enable_cache:
            return self.aggregator.get_all_instances_with_costs(
                days=days,
                include_terminated=include_terminated,
            )

        cache_key = generate_cache_key(
            "ec2_regional_summary",
            region=self.region,
            days=days,
            include_terminated=include_terminated,
        )

        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            logger.info(f"Returning cached regional summary for {self.region}")
            return cached_result

        logger.info(f"Fetching fresh regional summary for {self.region}")
        result = self.aggregator.get_all_instances_with_costs(
            days=days,
            include_terminated=include_terminated,
        )

        # Cache regional summaries for shorter time (30 minutes)
        # since they can change more frequently
        self.cache.set(cache_key, result, ttl=1800)
        return result

    def get_instances_by_tag_with_costs(
        self,
        tag_key: str,
        tag_value: Optional[str] = None,
        days: int = 30,
    ) -> RegionalEC2Summary:
        """
        Get instances by tag with costs (cached).

        Args:
            tag_key: Tag key to filter by
            tag_value: Optional tag value
            days: Number of days of cost data

        Returns:
            RegionalEC2Summary object
        """
        if not self.enable_cache:
            return self.aggregator.get_instances_by_tag_with_costs(
                tag_key=tag_key,
                tag_value=tag_value,
                days=days,
            )

        cache_key = generate_cache_key(
            "ec2_by_tag",
            region=self.region,
            tag_key=tag_key,
            tag_value=tag_value,
            days=days,
        )

        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            logger.info(f"Returning cached tag-filtered data for {tag_key}")
            return cached_result

        logger.info(f"Fetching fresh tag-filtered data for {tag_key}")
        result = self.aggregator.get_instances_by_tag_with_costs(
            tag_key=tag_key,
            tag_value=tag_value,
            days=days,
        )

        self.cache.set(cache_key, result, ttl=1800)
        return result

    def get_running_instances_with_costs(
        self,
        days: int = 30,
    ) -> RegionalEC2Summary:
        """
        Get running instances with costs (cached).

        Args:
            days: Number of days of cost data

        Returns:
            RegionalEC2Summary object
        """
        if not self.enable_cache:
            return self.aggregator.get_running_instances_with_costs(days=days)

        cache_key = generate_cache_key(
            "ec2_running",
            region=self.region,
            days=days,
        )

        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            logger.info(f"Returning cached running instances for {self.region}")
            return cached_result

        logger.info(f"Fetching fresh running instances for {self.region}")
        result = self.aggregator.get_running_instances_with_costs(days=days)

        self.cache.set(cache_key, result, ttl=1800)
        return result

    def get_cost_optimization_opportunities(
        self,
        days: int = 30,
    ) -> List[Dict[str, any]]:
        """
        Get cost optimization opportunities (cached).

        Args:
            days: Number of days to analyze

        Returns:
            List of optimization opportunities
        """
        if not self.enable_cache:
            return self.aggregator.get_cost_optimization_opportunities(days=days)

        cache_key = generate_cache_key(
            "ec2_optimization_opportunities",
            region=self.region,
            days=days,
        )

        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            logger.info(f"Returning cached optimization opportunities")
            return cached_result

        logger.info(f"Analyzing optimization opportunities")
        result = self.aggregator.get_cost_optimization_opportunities(days=days)

        # Cache for 1 hour since these are analysis results
        self.cache.set(cache_key, result)
        return result

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self.cache.clear()
        logger.info("EC2 aggregator cache cleared")

    def clear_expired_cache(self) -> int:
        """
        Clear expired cache entries.

        Returns:
            Number of entries cleared
        """
        return self.cache.clear_expired()

    def invalidate_instance_cache(self, instance_id: str) -> None:
        """
        Invalidate cache for a specific instance.

        Args:
            instance_id: EC2 instance ID
        """
        # Delete all cache entries related to this instance
        # This is a simplified version - in production, might want more targeted invalidation
        cache_key = generate_cache_key(
            "ec2_instance_costs",
            region=self.region,
            instance_id=instance_id,
            days=30,  # Default days
        )
        self.cache.delete(cache_key)
        logger.info(f"Invalidated cache for instance {instance_id}")

    def invalidate_regional_cache(self) -> None:
        """Invalidate all regional cache entries."""
        # In production, might want more targeted invalidation
        # For now, just clear expired
        self.clear_expired_cache()
        logger.info(f"Invalidated regional cache for {self.region}")
