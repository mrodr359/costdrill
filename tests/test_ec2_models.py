"""
Tests for EC2 data models.
"""

import pytest
from datetime import datetime, timedelta

from costdrill.core.ec2_models import (
    EBSVolume,
    EC2CostBreakdown,
    EC2Instance,
    EC2InstanceWithCosts,
    InstanceState,
    RegionalEC2Summary,
)
from costdrill.core.models import CostAmount, CostMetrics


def test_ebs_volume_creation():
    """Test EBS volume model."""
    volume = EBSVolume(
        volume_id="vol-12345",
        size_gb=100,
        volume_type="gp3",
        iops=3000,
        throughput=125,
        device_name="/dev/sda1",
    )

    assert volume.volume_id == "vol-12345"
    assert volume.size_gb == 100
    assert volume.volume_type == "gp3"
    assert volume.display_name == "gp3 100GB (vol-12345)"


def test_ec2_instance_creation():
    """Test EC2 instance model."""
    launch_time = datetime.now() - timedelta(days=5)

    instance = EC2Instance(
        instance_id="i-1234567890",
        instance_type="t3.micro",
        state=InstanceState.RUNNING,
        region="us-east-1",
        availability_zone="us-east-1a",
        launch_time=launch_time,
        tags={"Name": "Test Instance", "Environment": "Dev"},
    )

    assert instance.instance_id == "i-1234567890"
    assert instance.name == "Test Instance"
    assert instance.is_running is True
    assert instance.get_tag("Environment") == "Dev"
    assert instance.uptime_hours > 0


def test_ec2_instance_without_name_tag():
    """Test EC2 instance without Name tag uses instance ID."""
    instance = EC2Instance(
        instance_id="i-9876543210",
        instance_type="t3.small",
        state=InstanceState.STOPPED,
        region="us-west-2",
        availability_zone="us-west-2a",
        launch_time=datetime.now(),
        tags={},
    )

    assert instance.name == "i-9876543210"
    assert instance.is_running is False


def test_ec2_instance_total_storage():
    """Test calculating total storage across volumes."""
    volumes = [
        EBSVolume(volume_id="vol-1", size_gb=50, volume_type="gp3"),
        EBSVolume(volume_id="vol-2", size_gb=100, volume_type="gp3"),
        EBSVolume(volume_id="vol-3", size_gb=25, volume_type="gp2"),
    ]

    instance = EC2Instance(
        instance_id="i-test",
        instance_type="t3.medium",
        state=InstanceState.RUNNING,
        region="us-east-1",
        availability_zone="us-east-1a",
        launch_time=datetime.now(),
        ebs_volumes=volumes,
    )

    assert instance.total_storage_gb == 175


def test_ec2_cost_breakdown():
    """Test EC2 cost breakdown model."""
    breakdown = EC2CostBreakdown(
        instance_id="i-test",
        total_cost=CostAmount(100.0),
        compute_cost=CostAmount(60.0),
        storage_cost=CostAmount(30.0),
        data_transfer_cost=CostAmount(5.0),
        snapshot_cost=CostAmount(3.0),
        elastic_ip_cost=CostAmount(2.0),
        other_costs=CostAmount(0.0),
        running_hours=720.0,
        storage_gb_hours=7200.0,
        cost_per_hour=0.083,
        cost_per_gb_month=0.10,
    )

    assert breakdown.total_cost.amount == 100.0
    assert breakdown.compute_percentage == 60.0
    assert breakdown.storage_percentage == 30.0
    assert breakdown.data_transfer_percentage == 5.0


def test_ec2_cost_breakdown_dict():
    """Test cost breakdown dictionary representation."""
    breakdown = EC2CostBreakdown(
        instance_id="i-test",
        total_cost=CostAmount(100.0),
        compute_cost=CostAmount(80.0),
        storage_cost=CostAmount(15.0),
        data_transfer_cost=CostAmount(5.0),
        snapshot_cost=CostAmount(0.0),
        elastic_ip_cost=CostAmount(0.0),
        other_costs=CostAmount(0.0),
        running_hours=720.0,
        storage_gb_hours=7200.0,
        cost_per_hour=0.11,
        cost_per_gb_month=0.10,
    )

    breakdown_dict = breakdown.get_cost_breakdown_dict()

    assert "compute" in breakdown_dict
    assert breakdown_dict["compute"]["amount"] == 80.0
    assert breakdown_dict["compute"]["percentage"] == 80.0
    assert breakdown_dict["storage"]["percentage"] == 15.0


def test_ec2_instance_with_costs():
    """Test EC2 instance with costs model."""
    instance = EC2Instance(
        instance_id="i-test",
        instance_type="t3.large",
        state=InstanceState.RUNNING,
        region="us-east-1",
        availability_zone="us-east-1a",
        launch_time=datetime.now(),
        tags={"Name": "Production Server"},
    )

    breakdown = EC2CostBreakdown(
        instance_id="i-test",
        total_cost=CostAmount(150.0),
        compute_cost=CostAmount(100.0),
        storage_cost=CostAmount(40.0),
        data_transfer_cost=CostAmount(10.0),
        snapshot_cost=CostAmount(0.0),
        elastic_ip_cost=CostAmount(0.0),
        other_costs=CostAmount(0.0),
        running_hours=720.0,
        storage_gb_hours=7200.0,
        cost_per_hour=0.14,
        cost_per_gb_month=0.10,
    )

    start_date = datetime.now() - timedelta(days=30)
    end_date = datetime.now()

    instance_with_costs = EC2InstanceWithCosts(
        instance=instance,
        cost_breakdown=breakdown,
        start_date=start_date,
        end_date=end_date,
    )

    assert instance_with_costs.instance_id == "i-test"
    assert instance_with_costs.instance_name == "Production Server"
    assert instance_with_costs.total_cost.amount == 150.0
    assert instance_with_costs.daily_cost == 5.0
    assert instance_with_costs.monthly_projection == 150.0


def test_regional_ec2_summary():
    """Test regional EC2 summary model."""
    instances = []

    for i in range(5):
        instance = EC2Instance(
            instance_id=f"i-test{i}",
            instance_type="t3.micro",
            state=InstanceState.RUNNING if i < 3 else InstanceState.STOPPED,
            region="us-east-1",
            availability_zone="us-east-1a",
            launch_time=datetime.now(),
        )

        breakdown = EC2CostBreakdown(
            instance_id=f"i-test{i}",
            total_cost=CostAmount(10.0 * (i + 1)),
            compute_cost=CostAmount(8.0 * (i + 1)),
            storage_cost=CostAmount(2.0 * (i + 1)),
            data_transfer_cost=CostAmount(0.0),
            snapshot_cost=CostAmount(0.0),
            elastic_ip_cost=CostAmount(0.0),
            other_costs=CostAmount(0.0),
            running_hours=720.0,
            storage_gb_hours=3600.0,
            cost_per_hour=0.01,
            cost_per_gb_month=0.10,
        )

        instances.append(
            EC2InstanceWithCosts(
                instance=instance,
                cost_breakdown=breakdown,
                start_date=datetime.now() - timedelta(days=30),
                end_date=datetime.now(),
            )
        )

    summary = RegionalEC2Summary(
        region="us-east-1",
        instances=instances,
        total_cost=CostAmount(150.0),
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now(),
    )

    assert summary.instance_count == 5
    assert summary.running_instance_count == 3
    assert summary.stopped_instance_count == 2
    assert summary.average_cost_per_instance == 30.0


def test_regional_summary_get_top_cost_instances():
    """Test getting top cost instances from summary."""
    instances = []

    for i in range(10):
        instance = EC2Instance(
            instance_id=f"i-test{i}",
            instance_type="t3.micro",
            state=InstanceState.RUNNING,
            region="us-east-1",
            availability_zone="us-east-1a",
            launch_time=datetime.now(),
        )

        # Create costs with varying amounts
        breakdown = EC2CostBreakdown(
            instance_id=f"i-test{i}",
            total_cost=CostAmount(10.0 * (10 - i)),  # Descending costs
            compute_cost=CostAmount(8.0 * (10 - i)),
            storage_cost=CostAmount(2.0 * (10 - i)),
            data_transfer_cost=CostAmount(0.0),
            snapshot_cost=CostAmount(0.0),
            elastic_ip_cost=CostAmount(0.0),
            other_costs=CostAmount(0.0),
            running_hours=720.0,
            storage_gb_hours=3600.0,
            cost_per_hour=0.01,
            cost_per_gb_month=0.10,
        )

        instances.append(
            EC2InstanceWithCosts(
                instance=instance,
                cost_breakdown=breakdown,
                start_date=datetime.now() - timedelta(days=30),
                end_date=datetime.now(),
            )
        )

    summary = RegionalEC2Summary(
        region="us-east-1",
        instances=instances,
        total_cost=CostAmount(550.0),
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now(),
    )

    top_5 = summary.get_top_cost_instances(limit=5)

    assert len(top_5) == 5
    assert top_5[0].instance_id == "i-test0"
    assert top_5[0].total_cost.amount == 100.0
    assert top_5[4].total_cost.amount == 60.0


def test_regional_summary_filter_by_tag():
    """Test filtering instances by tag."""
    instances = []

    for i in range(5):
        tags = {"Environment": "prod" if i < 3 else "dev"}

        instance = EC2Instance(
            instance_id=f"i-test{i}",
            instance_type="t3.micro",
            state=InstanceState.RUNNING,
            region="us-east-1",
            availability_zone="us-east-1a",
            launch_time=datetime.now(),
            tags=tags,
        )

        breakdown = EC2CostBreakdown(
            instance_id=f"i-test{i}",
            total_cost=CostAmount(10.0),
            compute_cost=CostAmount(8.0),
            storage_cost=CostAmount(2.0),
            data_transfer_cost=CostAmount(0.0),
            snapshot_cost=CostAmount(0.0),
            elastic_ip_cost=CostAmount(0.0),
            other_costs=CostAmount(0.0),
            running_hours=720.0,
            storage_gb_hours=3600.0,
            cost_per_hour=0.01,
            cost_per_gb_month=0.10,
        )

        instances.append(
            EC2InstanceWithCosts(
                instance=instance,
                cost_breakdown=breakdown,
                start_date=datetime.now() - timedelta(days=30),
                end_date=datetime.now(),
            )
        )

    summary = RegionalEC2Summary(
        region="us-east-1",
        instances=instances,
        total_cost=CostAmount(50.0),
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now(),
    )

    prod_instances = summary.get_instances_by_tag("Environment", "prod")
    dev_instances = summary.get_instances_by_tag("Environment", "dev")

    assert len(prod_instances) == 3
    assert len(dev_instances) == 2
