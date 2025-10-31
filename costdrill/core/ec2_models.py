"""
Data models for EC2 instances and costs.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from costdrill.core.models import CostAmount


class InstanceState(Enum):
    """EC2 instance states."""

    PENDING = "pending"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    SHUTTING_DOWN = "shutting-down"
    TERMINATED = "terminated"


@dataclass
class EBSVolume:
    """EBS volume attached to an instance."""

    volume_id: str
    size_gb: int
    volume_type: str  # gp2, gp3, io1, io2, st1, sc1
    iops: Optional[int] = None
    throughput: Optional[int] = None
    device_name: str = ""
    state: str = "attached"
    delete_on_termination: bool = True

    @property
    def display_name(self) -> str:
        """Get a display-friendly volume name."""
        return f"{self.volume_type} {self.size_gb}GB ({self.volume_id})"


@dataclass
class EC2Instance:
    """EC2 instance metadata."""

    instance_id: str
    instance_type: str
    state: InstanceState
    region: str
    availability_zone: str
    launch_time: datetime
    platform: str = "Linux/UNIX"  # or "Windows"
    vpc_id: Optional[str] = None
    subnet_id: Optional[str] = None
    private_ip: Optional[str] = None
    public_ip: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    security_groups: List[str] = field(default_factory=list)
    ebs_volumes: List[EBSVolume] = field(default_factory=list)
    key_name: Optional[str] = None
    iam_instance_profile: Optional[str] = None
    monitoring_enabled: bool = False
    tenancy: str = "default"  # default, dedicated, host

    @property
    def name(self) -> str:
        """Get instance name from tags or use instance ID."""
        return self.tags.get("Name", self.instance_id)

    @property
    def is_running(self) -> bool:
        """Check if instance is running."""
        return self.state == InstanceState.RUNNING

    @property
    def total_storage_gb(self) -> int:
        """Get total EBS storage in GB."""
        return sum(vol.size_gb for vol in self.ebs_volumes)

    @property
    def uptime_hours(self) -> float:
        """Calculate instance uptime in hours."""
        if self.state == InstanceState.TERMINATED:
            return 0.0
        delta = datetime.now() - self.launch_time
        return delta.total_seconds() / 3600

    def get_tag(self, key: str, default: str = "") -> str:
        """
        Get tag value by key.

        Args:
            key: Tag key
            default: Default value if tag not found

        Returns:
            Tag value or default
        """
        return self.tags.get(key, default)


@dataclass
class EC2CostBreakdown:
    """Detailed cost breakdown for an EC2 instance."""

    instance_id: str
    total_cost: CostAmount

    # Component costs
    compute_cost: CostAmount
    storage_cost: CostAmount
    data_transfer_cost: CostAmount
    snapshot_cost: CostAmount
    elastic_ip_cost: CostAmount
    other_costs: CostAmount

    # Usage metrics
    running_hours: float
    storage_gb_hours: float

    # Cost per unit
    cost_per_hour: float
    cost_per_gb_month: float

    # Breakdown by usage type
    usage_type_breakdown: Dict[str, CostAmount] = field(default_factory=dict)

    @property
    def compute_percentage(self) -> float:
        """Get compute cost as percentage of total."""
        if self.total_cost.amount == 0:
            return 0.0
        return (self.compute_cost.amount / self.total_cost.amount) * 100

    @property
    def storage_percentage(self) -> float:
        """Get storage cost as percentage of total."""
        if self.total_cost.amount == 0:
            return 0.0
        return (self.storage_cost.amount / self.total_cost.amount) * 100

    @property
    def data_transfer_percentage(self) -> float:
        """Get data transfer cost as percentage of total."""
        if self.total_cost.amount == 0:
            return 0.0
        return (self.data_transfer_cost.amount / self.total_cost.amount) * 100

    def get_cost_breakdown_dict(self) -> Dict[str, Dict[str, any]]:
        """
        Get cost breakdown as a dictionary.

        Returns:
            Dictionary with cost components
        """
        return {
            "compute": {
                "amount": self.compute_cost.amount,
                "percentage": self.compute_percentage,
            },
            "storage": {
                "amount": self.storage_cost.amount,
                "percentage": self.storage_percentage,
            },
            "data_transfer": {
                "amount": self.data_transfer_cost.amount,
                "percentage": self.data_transfer_percentage,
            },
            "snapshot": {
                "amount": self.snapshot_cost.amount,
                "percentage": (self.snapshot_cost.amount / self.total_cost.amount * 100)
                if self.total_cost.amount > 0
                else 0.0,
            },
            "elastic_ip": {
                "amount": self.elastic_ip_cost.amount,
                "percentage": (self.elastic_ip_cost.amount / self.total_cost.amount * 100)
                if self.total_cost.amount > 0
                else 0.0,
            },
            "other": {
                "amount": self.other_costs.amount,
                "percentage": (self.other_costs.amount / self.total_cost.amount * 100)
                if self.total_cost.amount > 0
                else 0.0,
            },
        }


@dataclass
class EC2InstanceWithCosts:
    """EC2 instance with associated cost data."""

    instance: EC2Instance
    cost_breakdown: EC2CostBreakdown
    start_date: datetime
    end_date: datetime

    @property
    def instance_id(self) -> str:
        """Get instance ID."""
        return self.instance.instance_id

    @property
    def instance_name(self) -> str:
        """Get instance name."""
        return self.instance.name

    @property
    def total_cost(self) -> CostAmount:
        """Get total cost."""
        return self.cost_breakdown.total_cost

    @property
    def daily_cost(self) -> float:
        """Calculate average daily cost."""
        days = (self.end_date - self.start_date).days
        if days == 0:
            return self.total_cost.amount
        return self.total_cost.amount / days

    @property
    def monthly_projection(self) -> float:
        """Project monthly cost based on current rate."""
        return self.daily_cost * 30


@dataclass
class RegionalEC2Summary:
    """Summary of all EC2 instances in a region."""

    region: str
    instances: List[EC2InstanceWithCosts]
    total_cost: CostAmount
    start_date: datetime
    end_date: datetime

    @property
    def instance_count(self) -> int:
        """Get total number of instances."""
        return len(self.instances)

    @property
    def running_instance_count(self) -> int:
        """Get number of running instances."""
        return sum(1 for i in self.instances if i.instance.is_running)

    @property
    def stopped_instance_count(self) -> int:
        """Get number of stopped instances."""
        return sum(1 for i in self.instances if i.instance.state == InstanceState.STOPPED)

    @property
    def total_storage_gb(self) -> int:
        """Get total storage across all instances."""
        return sum(i.instance.total_storage_gb for i in self.instances)

    @property
    def average_cost_per_instance(self) -> float:
        """Calculate average cost per instance."""
        if self.instance_count == 0:
            return 0.0
        return self.total_cost.amount / self.instance_count

    def get_instances_by_type(self) -> Dict[str, List[EC2InstanceWithCosts]]:
        """
        Group instances by instance type.

        Returns:
            Dictionary mapping instance type to list of instances
        """
        by_type: Dict[str, List[EC2InstanceWithCosts]] = {}
        for instance in self.instances:
            instance_type = instance.instance.instance_type
            if instance_type not in by_type:
                by_type[instance_type] = []
            by_type[instance_type].append(instance)
        return by_type

    def get_instances_by_state(self) -> Dict[InstanceState, List[EC2InstanceWithCosts]]:
        """
        Group instances by state.

        Returns:
            Dictionary mapping state to list of instances
        """
        by_state: Dict[InstanceState, List[EC2InstanceWithCosts]] = {}
        for instance in self.instances:
            state = instance.instance.state
            if state not in by_state:
                by_state[state] = []
            by_state[state].append(instance)
        return by_state

    def get_top_cost_instances(self, limit: int = 10) -> List[EC2InstanceWithCosts]:
        """
        Get instances with highest costs.

        Args:
            limit: Maximum number of instances to return

        Returns:
            List of instances sorted by cost (descending)
        """
        return sorted(
            self.instances,
            key=lambda x: x.total_cost.amount,
            reverse=True,
        )[:limit]

    def get_instances_by_tag(self, tag_key: str, tag_value: Optional[str] = None) -> List[EC2InstanceWithCosts]:
        """
        Filter instances by tag.

        Args:
            tag_key: Tag key to filter by
            tag_value: Optional tag value to match

        Returns:
            List of matching instances
        """
        result = []
        for instance in self.instances:
            if tag_key in instance.instance.tags:
                if tag_value is None or instance.instance.tags[tag_key] == tag_value:
                    result.append(instance)
        return result
