#!/usr/bin/env python3
"""
Basic usage example for CostDrill Cost Explorer integration.

This example demonstrates how to:
1. Initialize the AWS client
2. Fetch EC2 costs
3. Get cost forecasts
4. Use caching for better performance
"""

import logging
from datetime import datetime, timedelta

from costdrill.core.aws_client import AWSClient
from costdrill.core.cached_cost_explorer import CachedCostExplorer
from costdrill.core.exceptions import (
    AWSAuthenticationError,
    CostExplorerNotEnabledException,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    """Main example function."""
    try:
        # Initialize AWS client
        # This will validate credentials automatically
        logger.info("Initializing AWS client...")
        aws_client = AWSClient(region="us-east-1")

        # Display authenticated account info
        if aws_client.credentials:
            logger.info(f"Authenticated as: {aws_client.credentials.arn}")
            logger.info(f"Account ID: {aws_client.credentials.account_id}")

        # Initialize cached Cost Explorer
        # Cache TTL is 1 hour by default
        logger.info("Initializing Cost Explorer with caching...")
        cost_explorer = CachedCostExplorer(
            aws_client=aws_client,
            cache_ttl=3600,
            enable_cache=True,
        )

        # Example 1: Get EC2 costs for the last 30 days
        logger.info("\n=== Example 1: EC2 Costs (Last 30 days) ===")
        ec2_costs = cost_explorer.get_ec2_costs(days=30)

        logger.info(f"Date Range: {ec2_costs.start_date.date()} to {ec2_costs.end_date.date()}")
        logger.info(f"Total EC2 Cost: {ec2_costs.total_cost}")
        logger.info(f"Number of days: {len(ec2_costs.time_series)}")

        # Show daily costs
        logger.info("\nDaily Costs:")
        for date, cost in ec2_costs.get_daily_costs()[:7]:  # Show first 7 days
            logger.info(f"  {date.date()}: ${cost:.2f}")

        # Show cost breakdowns by usage type
        if ec2_costs.breakdowns:
            logger.info("\nTop 5 Cost Breakdowns:")
            sorted_breakdowns = sorted(
                ec2_costs.breakdowns,
                key=lambda x: x.cost.amount,
                reverse=True,
            )
            for breakdown in sorted_breakdowns[:5]:
                logger.info(
                    f"  {breakdown.key}: {breakdown.cost} ({breakdown.category})"
                )

        # Example 2: Get costs for a specific EC2 instance
        logger.info("\n=== Example 2: Specific EC2 Instance ===")
        # Replace with your actual instance ID
        instance_id = "i-1234567890abcdef0"
        logger.info(f"Querying costs for instance: {instance_id}")

        try:
            instance_costs = cost_explorer.get_ec2_costs(
                instance_id=instance_id,
                days=7,
            )
            logger.info(f"Instance Cost (7 days): {instance_costs.total_cost}")
        except Exception as e:
            logger.warning(f"Could not fetch instance costs: {e}")

        # Example 3: Get EC2 costs by region
        logger.info("\n=== Example 3: EC2 Costs by Region ===")
        region = "us-west-2"
        regional_costs = cost_explorer.get_ec2_costs(
            region=region,
            days=30,
        )
        logger.info(f"EC2 Cost in {region}: {regional_costs.total_cost}")

        # Example 4: Get cost forecast
        logger.info("\n=== Example 4: Cost Forecast ===")
        forecast = cost_explorer.get_cost_forecast(days=30)

        logger.info(f"Forecast Period: {forecast.start_date.date()} to {forecast.end_date.date()}")
        logger.info(f"Predicted Mean Cost: {forecast.mean_value}")

        if forecast.time_series:
            logger.info("\nMonthly Forecast:")
            for ts in forecast.time_series:
                logger.info(
                    f"  {ts.start_date.strftime('%B %Y')}: {ts.metrics.unblended_cost}"
                )

        # Example 5: Get costs for other services
        logger.info("\n=== Example 5: S3 Costs ===")
        s3_costs = cost_explorer.get_service_costs(
            service="Amazon Simple Storage Service",
            days=30,
        )
        logger.info(f"Total S3 Cost: {s3_costs.total_cost}")

        # Example 6: Get all AWS costs
        logger.info("\n=== Example 6: All AWS Costs ===")
        all_costs = cost_explorer.get_cost_and_usage(
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
            granularity="MONTHLY",
        )
        logger.info(f"Total AWS Cost (30 days): {all_costs.total_cost}")

        # Cache management
        logger.info("\n=== Cache Management ===")
        expired_count = cost_explorer.clear_expired_cache()
        logger.info(f"Cleared {expired_count} expired cache entries")

        logger.info("\n✅ Examples completed successfully!")

    except AWSAuthenticationError as e:
        logger.error(f"Authentication failed: {e}")
        logger.error("Please check your AWS credentials configuration.")
        return 1

    except CostExplorerNotEnabledException as e:
        logger.error(f"Cost Explorer not enabled: {e}")
        logger.error("Please enable Cost Explorer in AWS Billing console.")
        return 1

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
