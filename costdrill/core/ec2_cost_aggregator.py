"""
EC2 cost aggregator - combines instance metadata with cost data.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from costdrill.core.aws_client import AWSClient
from costdrill.core.cost_explorer import CostExplorer
from costdrill.core.ec2_cost_analyzer import EC2CostAnalyzer
from costdrill.core.ec2_models import (
    EC2Instance,
    EC2InstanceWithCosts,
    RegionalEC2Summary,
)
from costdrill.core.ec2_service import EC2Service
from costdrill.core.models import CostAmount

logger = logging.getLogger(__name__)


class EC2CostAggregator:
    """
    Aggregates EC2 instance metadata with cost data.

    This is the main interface for getting comprehensive EC2 cost information.
    """

    def __init__(
        self,
        aws_client: AWSClient,
        region: Optional[str] = None,
    ):
        """
        Initialize EC2 cost aggregator.

        Args:
            aws_client: AWS client instance
            region: Specific region (uses client's default if not specified)
        """
        self.aws_client = aws_client
        self.region = region or aws_client.region or "us-east-1"

        # Initialize services
        self.ec2_service = EC2Service(aws_client, region=self.region)
        self.cost_explorer = CostExplorer(aws_client)
        self.cost_analyzer = EC2CostAnalyzer()

    def get_instance_with_costs(
        self,
        instance_id: str,
        days: int = 30,
    ) -> EC2InstanceWithCosts:
        """
        Get EC2 instance with complete cost breakdown.

        Args:
            instance_id: EC2 instance ID
            days: Number of days of cost data to fetch

        Returns:
            EC2InstanceWithCosts object

        Raises:
            ResourceNotFoundError: If instance not found
        """
        logger.info(f"Fetching instance {instance_id} with costs")

        # Fetch instance metadata
        instance = self.ec2_service.get_instance(instance_id)

        # Enrich with volume details
        volumes = self.ec2_service.get_volumes_for_instance(instance_id)
        instance.ebs_volumes = volumes

        # Fetch cost data
        start_date = datetime.now() - timedelta(days=days)
        end_date = datetime.now()

        cost_summary = self.cost_explorer.get_ec2_costs(
            instance_id=instance_id,
            region=self.region,
            days=days,
        )

        # Analyze costs
        cost_breakdown = self.cost_analyzer.analyze_cost_breakdown(
            instance_id=instance_id,
            cost_summary=cost_summary,
        )

        return EC2InstanceWithCosts(
            instance=instance,
            cost_breakdown=cost_breakdown,
            start_date=start_date,
            end_date=end_date,
        )

    def get_all_instances_with_costs(
        self,
        days: int = 30,
        include_terminated: bool = False,
    ) -> RegionalEC2Summary:
        """
        Get all EC2 instances in region with cost data.

        Args:
            days: Number of days of cost data to fetch
            include_terminated: Whether to include terminated instances

        Returns:
            RegionalEC2Summary with all instances and costs
        """
        logger.info(f"Fetching all instances in {self.region} with costs")

        # Fetch all instances
        instances = self.ec2_service.list_instances(
            include_terminated=include_terminated
        )

        if not instances:
            logger.info("No instances found in region")
            return RegionalEC2Summary(
                region=self.region,
                instances=[],
                total_cost=CostAmount(0.0),
                start_date=datetime.now() - timedelta(days=days),
                end_date=datetime.now(),
            )

        # Fetch regional cost data
        start_date = datetime.now() - timedelta(days=days)
        end_date = datetime.now()

        regional_cost_summary = self.cost_explorer.get_ec2_costs(
            region=self.region,
            days=days,
        )

        # Build instances with costs
        instances_with_costs: List[EC2InstanceWithCosts] = []

        for instance in instances:
            # For each instance, we need to get its specific costs
            # This is more expensive but gives accurate per-instance data
            try:
                instance_with_costs = self._get_instance_costs_from_summary(
                    instance=instance,
                    regional_summary=regional_cost_summary,
                    start_date=start_date,
                    end_date=end_date,
                    days=days,
                )
                instances_with_costs.append(instance_with_costs)

            except Exception as e:
                logger.warning(f"Error fetching costs for {instance.instance_id}: {e}")
                # Create instance with zero costs as fallback
                zero_breakdown = self.cost_analyzer.analyze_cost_breakdown(
                    instance_id=instance.instance_id,
                    cost_summary=regional_cost_summary,  # Will result in zeros
                )
                instances_with_costs.append(
                    EC2InstanceWithCosts(
                        instance=instance,
                        cost_breakdown=zero_breakdown,
                        start_date=start_date,
                        end_date=end_date,
                    )
                )

        # Calculate total cost
        total_cost = CostAmount(
            sum(i.total_cost.amount for i in instances_with_costs)
        )

        return RegionalEC2Summary(
            region=self.region,
            instances=instances_with_costs,
            total_cost=total_cost,
            start_date=start_date,
            end_date=end_date,
        )

    def get_instances_by_tag_with_costs(
        self,
        tag_key: str,
        tag_value: Optional[str] = None,
        days: int = 30,
    ) -> RegionalEC2Summary:
        """
        Get EC2 instances filtered by tag with cost data.

        Args:
            tag_key: Tag key to filter by
            tag_value: Optional tag value
            days: Number of days of cost data to fetch

        Returns:
            RegionalEC2Summary with filtered instances and costs
        """
        logger.info(f"Fetching instances with tag {tag_key}={tag_value}")

        # Get all instances with costs, then filter
        summary = self.get_all_instances_with_costs(days=days)

        # Filter by tag
        filtered_instances = summary.get_instances_by_tag(tag_key, tag_value)

        # Recalculate total cost
        total_cost = CostAmount(
            sum(i.total_cost.amount for i in filtered_instances)
        )

        return RegionalEC2Summary(
            region=self.region,
            instances=filtered_instances,
            total_cost=total_cost,
            start_date=summary.start_date,
            end_date=summary.end_date,
        )

    def get_running_instances_with_costs(
        self,
        days: int = 30,
    ) -> RegionalEC2Summary:
        """
        Get only running EC2 instances with cost data.

        Args:
            days: Number of days of cost data to fetch

        Returns:
            RegionalEC2Summary with running instances and costs
        """
        # Get all instances with costs, then filter
        summary = self.get_all_instances_with_costs(days=days)

        # Filter for running instances
        running_instances = [
            i for i in summary.instances if i.instance.is_running
        ]

        # Recalculate total cost
        total_cost = CostAmount(
            sum(i.total_cost.amount for i in running_instances)
        )

        return RegionalEC2Summary(
            region=self.region,
            instances=running_instances,
            total_cost=total_cost,
            start_date=summary.start_date,
            end_date=summary.end_date,
        )

    def get_cost_comparison_for_instance(
        self,
        instance_id: str,
        period1_days: int = 30,
        period2_days: int = 30,
    ) -> Dict[str, any]:
        """
        Compare costs for an instance across two time periods.

        Args:
            instance_id: EC2 instance ID
            period1_days: Number of days for first period (most recent)
            period2_days: Number of days for second period (prior to first)

        Returns:
            Dictionary with comparison data
        """
        logger.info(f"Comparing costs for {instance_id}")

        # Fetch instance data for both periods
        # Period 1: Most recent
        instance_period1 = self.get_instance_with_costs(
            instance_id=instance_id,
            days=period1_days,
        )

        # Period 2: Prior period
        # This would require fetching costs for a different date range
        # For now, we'll just return the current period data
        # TODO: Implement proper period comparison

        return {
            "instance_id": instance_id,
            "instance_name": instance_period1.instance_name,
            "period1": {
                "start_date": instance_period1.start_date,
                "end_date": instance_period1.end_date,
                "total_cost": instance_period1.total_cost.amount,
                "breakdown": instance_period1.cost_breakdown.get_cost_breakdown_dict(),
            },
            # Period 2 comparison would go here
        }

    def _get_instance_costs_from_summary(
        self,
        instance: EC2Instance,
        regional_summary: any,
        start_date: datetime,
        end_date: datetime,
        days: int,
    ) -> EC2InstanceWithCosts:
        """
        Extract instance-specific costs from regional summary.

        This is an optimization to avoid individual API calls per instance.
        If the data isn't available in the summary, fall back to individual query.

        Args:
            instance: EC2Instance object
            regional_summary: Regional cost summary
            start_date: Start date for costs
            end_date: End date for costs
            days: Number of days

        Returns:
            EC2InstanceWithCosts object
        """
        try:
            # Try to get instance-specific costs
            instance_cost_summary = self.cost_explorer.get_ec2_costs(
                instance_id=instance.instance_id,
                region=self.region,
                days=days,
            )

            # Enrich with volume details
            volumes = self.ec2_service.get_volumes_for_instance(instance.instance_id)
            instance.ebs_volumes = volumes

            cost_breakdown = self.cost_analyzer.analyze_cost_breakdown(
                instance_id=instance.instance_id,
                cost_summary=instance_cost_summary,
            )

            return EC2InstanceWithCosts(
                instance=instance,
                cost_breakdown=cost_breakdown,
                start_date=start_date,
                end_date=end_date,
            )

        except Exception as e:
            logger.debug(f"Could not fetch individual costs for {instance.instance_id}: {e}")
            # Return with zero costs
            raise

    def get_cost_optimization_opportunities(
        self,
        days: int = 30,
    ) -> List[Dict[str, any]]:
        """
        Identify cost optimization opportunities in the region.

        Args:
            days: Number of days of data to analyze

        Returns:
            List of optimization opportunities
        """
        logger.info("Identifying cost optimization opportunities")

        summary = self.get_all_instances_with_costs(days=days)
        opportunities = []

        for instance_with_costs in summary.instances:
            instance = instance_with_costs.instance
            breakdown = instance_with_costs.cost_breakdown

            # Check for waste indicators
            waste_indicators = self.cost_analyzer.calculate_waste_indicators(
                breakdown=breakdown,
                instance_state=instance.state.value,
            )

            if waste_indicators["has_waste"]:
                opportunities.append({
                    "instance_id": instance.instance_id,
                    "instance_name": instance.name,
                    "instance_type": instance.instance_type,
                    "state": instance.state.value,
                    "total_cost": breakdown.total_cost.amount,
                    "indicators": waste_indicators,
                })

        # Sort by potential savings (highest cost first)
        opportunities.sort(key=lambda x: x["total_cost"], reverse=True)

        return opportunities
