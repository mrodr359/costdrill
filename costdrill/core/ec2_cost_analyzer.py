"""
EC2 cost analysis and breakdown utilities.
"""

import logging
import re
from typing import Dict, List

from costdrill.core.ec2_models import EC2CostBreakdown
from costdrill.core.models import CostAmount, CostBreakdown, CostSummary

logger = logging.getLogger(__name__)


class EC2CostAnalyzer:
    """Analyzer for EC2 cost breakdowns."""

    # Patterns for categorizing usage types
    COMPUTE_PATTERNS = [
        r"BoxUsage",
        r"HeavyUsage",
        r"SpotUsage",
        r"ReservedInstanceUsage",
        r"UnusedBox",
        r"UnusedDed",
    ]

    STORAGE_PATTERNS = [
        r"EBS:VolumeUsage",
        r"EBS:VolumeP-IOPS",
        r"EBS:SnapshotUsage",
        r"EBS:Volume.*",
    ]

    DATA_TRANSFER_PATTERNS = [
        r"DataTransfer",
        r"InterRegion",
        r"PublicIP",
    ]

    SNAPSHOT_PATTERNS = [
        r"EBS:SnapshotUsage",
    ]

    ELASTIC_IP_PATTERNS = [
        r"ElasticIP",
        r"IdleAddress",
    ]

    def __init__(self):
        """Initialize cost analyzer."""
        self.compute_regex = self._compile_patterns(self.COMPUTE_PATTERNS)
        self.storage_regex = self._compile_patterns(self.STORAGE_PATTERNS)
        self.data_transfer_regex = self._compile_patterns(self.DATA_TRANSFER_PATTERNS)
        self.snapshot_regex = self._compile_patterns(self.SNAPSHOT_PATTERNS)
        self.elastic_ip_regex = self._compile_patterns(self.ELASTIC_IP_PATTERNS)

    @staticmethod
    def _compile_patterns(patterns: List[str]) -> re.Pattern:
        """
        Compile list of patterns into single regex.

        Args:
            patterns: List of regex patterns

        Returns:
            Compiled regex pattern
        """
        combined = "|".join(f"({pattern})" for pattern in patterns)
        return re.compile(combined, re.IGNORECASE)

    def analyze_cost_breakdown(
        self,
        instance_id: str,
        cost_summary: CostSummary,
    ) -> EC2CostBreakdown:
        """
        Analyze cost summary and create detailed breakdown.

        Args:
            instance_id: EC2 instance ID
            cost_summary: Cost summary from Cost Explorer

        Returns:
            EC2CostBreakdown with categorized costs
        """
        # Initialize cost categories
        compute_cost = 0.0
        storage_cost = 0.0
        data_transfer_cost = 0.0
        snapshot_cost = 0.0
        elastic_ip_cost = 0.0
        other_costs = 0.0

        usage_type_breakdown: Dict[str, CostAmount] = {}

        # Categorize each cost breakdown
        for breakdown in cost_summary.breakdowns:
            amount = breakdown.cost.amount
            usage_type = breakdown.key

            # Store in usage type breakdown
            usage_type_breakdown[usage_type] = breakdown.cost

            # Categorize
            if self.compute_regex.search(usage_type):
                compute_cost += amount
            elif self.snapshot_regex.search(usage_type):
                snapshot_cost += amount
            elif self.storage_regex.search(usage_type):
                storage_cost += amount
            elif self.data_transfer_regex.search(usage_type):
                data_transfer_cost += amount
            elif self.elastic_ip_regex.search(usage_type):
                elastic_ip_cost += amount
            else:
                other_costs += amount
                logger.debug(f"Uncategorized usage type: {usage_type}")

        # Calculate usage metrics
        running_hours = self._calculate_running_hours(cost_summary.breakdowns)
        storage_gb_hours = self._calculate_storage_gb_hours(cost_summary.breakdowns)

        # Calculate per-unit costs
        cost_per_hour = compute_cost / running_hours if running_hours > 0 else 0.0
        cost_per_gb_month = storage_cost / (storage_gb_hours / 730) if storage_gb_hours > 0 else 0.0

        return EC2CostBreakdown(
            instance_id=instance_id,
            total_cost=cost_summary.total_cost,
            compute_cost=CostAmount(compute_cost),
            storage_cost=CostAmount(storage_cost),
            data_transfer_cost=CostAmount(data_transfer_cost),
            snapshot_cost=CostAmount(snapshot_cost),
            elastic_ip_cost=CostAmount(elastic_ip_cost),
            other_costs=CostAmount(other_costs),
            running_hours=running_hours,
            storage_gb_hours=storage_gb_hours,
            cost_per_hour=cost_per_hour,
            cost_per_gb_month=cost_per_gb_month,
            usage_type_breakdown=usage_type_breakdown,
        )

    def analyze_regional_breakdown(
        self,
        cost_summary: CostSummary,
    ) -> EC2CostBreakdown:
        """
        Analyze cost summary for all instances in a region.

        Args:
            cost_summary: Cost summary from Cost Explorer

        Returns:
            EC2CostBreakdown with aggregated costs
        """
        # Use empty instance ID for regional summary
        return self.analyze_cost_breakdown("all", cost_summary)

    def _calculate_running_hours(self, breakdowns: List[CostBreakdown]) -> float:
        """
        Estimate running hours from usage type breakdowns.

        Args:
            breakdowns: List of cost breakdowns

        Returns:
            Estimated running hours
        """
        # Look for BoxUsage entries which typically include hours
        for breakdown in breakdowns:
            if "BoxUsage" in breakdown.key:
                # Try to extract hours from usage quantity if available
                # For now, estimate from cost using typical hourly rates
                # This is a rough estimate
                if breakdown.metrics.usage_quantity:
                    return breakdown.metrics.usage_quantity

        # Fallback: estimate from total time period
        # This is very rough and should be improved with actual usage data
        return 720.0  # Assume 30 days * 24 hours

    def _calculate_storage_gb_hours(self, breakdowns: List[CostBreakdown]) -> float:
        """
        Estimate storage GB-hours from usage type breakdowns.

        Args:
            breakdowns: List of cost breakdowns

        Returns:
            Estimated storage GB-hours
        """
        total_gb_hours = 0.0

        for breakdown in breakdowns:
            if "VolumeUsage" in breakdown.key:
                if breakdown.metrics.usage_quantity:
                    total_gb_hours += breakdown.metrics.usage_quantity

        return total_gb_hours

    def calculate_waste_indicators(
        self,
        breakdown: EC2CostBreakdown,
        instance_state: str,
    ) -> Dict[str, any]:
        """
        Calculate indicators of potential cost waste.

        Args:
            breakdown: EC2 cost breakdown
            instance_state: Current instance state

        Returns:
            Dictionary with waste indicators
        """
        indicators = {
            "has_waste": False,
            "stopped_with_costs": False,
            "high_storage_ratio": False,
            "high_data_transfer": False,
            "elastic_ip_charges": False,
            "recommendations": [],
        }

        # Check if instance is stopped but still incurring costs
        if instance_state == "stopped" and breakdown.total_cost.amount > 0:
            indicators["stopped_with_costs"] = True
            indicators["has_waste"] = True
            indicators["recommendations"].append(
                f"Instance is stopped but incurring ${breakdown.total_cost.amount:.2f} in costs. "
                "Consider terminating if not needed."
            )

        # Check if storage costs are high relative to compute
        if breakdown.compute_cost.amount > 0:
            storage_ratio = breakdown.storage_cost.amount / breakdown.compute_cost.amount
            if storage_ratio > 1.0:
                indicators["high_storage_ratio"] = True
                indicators["has_waste"] = True
                indicators["recommendations"].append(
                    f"Storage costs (${breakdown.storage_cost.amount:.2f}) exceed compute costs. "
                    "Review attached volumes for optimization opportunities."
                )

        # Check for high data transfer costs
        if breakdown.data_transfer_cost.amount > breakdown.compute_cost.amount * 0.3:
            indicators["high_data_transfer"] = True
            indicators["has_waste"] = True
            indicators["recommendations"].append(
                f"Data transfer costs are {breakdown.data_transfer_percentage:.1f}% of total. "
                "Consider optimizing data transfer patterns."
            )

        # Check for elastic IP charges
        if breakdown.elastic_ip_cost.amount > 0:
            indicators["elastic_ip_charges"] = True
            indicators["has_waste"] = True
            indicators["recommendations"].append(
                f"Elastic IP charges detected (${breakdown.elastic_ip_cost.amount:.2f}). "
                "Ensure IPs are associated with running instances."
            )

        return indicators

    def compare_instance_costs(
        self,
        breakdown1: EC2CostBreakdown,
        breakdown2: EC2CostBreakdown,
    ) -> Dict[str, any]:
        """
        Compare costs between two instances or time periods.

        Args:
            breakdown1: First cost breakdown
            breakdown2: Second cost breakdown

        Returns:
            Dictionary with comparison metrics
        """
        def calc_change(val1: float, val2: float) -> Dict[str, float]:
            if val2 == 0:
                return {"absolute": val1 - val2, "percentage": 0.0}
            pct_change = ((val1 - val2) / val2) * 100
            return {"absolute": val1 - val2, "percentage": pct_change}

        return {
            "total_cost": calc_change(
                breakdown1.total_cost.amount,
                breakdown2.total_cost.amount,
            ),
            "compute_cost": calc_change(
                breakdown1.compute_cost.amount,
                breakdown2.compute_cost.amount,
            ),
            "storage_cost": calc_change(
                breakdown1.storage_cost.amount,
                breakdown2.storage_cost.amount,
            ),
            "data_transfer_cost": calc_change(
                breakdown1.data_transfer_cost.amount,
                breakdown2.data_transfer_cost.amount,
            ),
        }
