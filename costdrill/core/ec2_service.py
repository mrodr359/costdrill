"""
EC2 service for managing instance metadata and operations.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from botocore.exceptions import ClientError

from costdrill.core.aws_client import AWSClient
from costdrill.core.ec2_models import (
    EBSVolume,
    EC2Instance,
    InstanceState,
)
from costdrill.core.exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)


class EC2Service:
    """Service for EC2 instance operations and metadata retrieval."""

    def __init__(self, aws_client: AWSClient, region: Optional[str] = None):
        """
        Initialize EC2 service.

        Args:
            aws_client: AWS client instance
            region: Specific region (uses client's default if not specified)
        """
        self.aws_client = aws_client
        self.region = region or aws_client.region or "us-east-1"
        self.client = aws_client.get_ec2_client(region=self.region)

    def list_instances(
        self,
        filters: Optional[List[Dict[str, any]]] = None,
        include_terminated: bool = False,
    ) -> List[EC2Instance]:
        """
        List all EC2 instances in the region.

        Args:
            filters: Optional EC2 filters (e.g., [{'Name': 'tag:Environment', 'Values': ['prod']}])
            include_terminated: Whether to include terminated instances

        Returns:
            List of EC2Instance objects
        """
        try:
            # Build filters
            api_filters = filters or []
            if not include_terminated:
                # Exclude terminated instances
                api_filters.append({
                    "Name": "instance-state-name",
                    "Values": ["pending", "running", "stopping", "stopped", "shutting-down"],
                })

            logger.info(f"Listing EC2 instances in region: {self.region}")

            # Use pagination to handle large result sets
            instances = []
            paginator = self.client.get_paginator("describe_instances")

            for page in paginator.paginate(Filters=api_filters):
                for reservation in page.get("Reservations", []):
                    for instance_data in reservation.get("Instances", []):
                        instance = self._parse_instance(instance_data)
                        instances.append(instance)

            logger.info(f"Found {len(instances)} instances")
            return instances

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_message = e.response.get("Error", {}).get("Message", "")
            logger.error(f"Error listing EC2 instances: {error_code} - {error_message}")
            raise

    def get_instance(self, instance_id: str) -> EC2Instance:
        """
        Get details for a specific EC2 instance.

        Args:
            instance_id: EC2 instance ID

        Returns:
            EC2Instance object

        Raises:
            ResourceNotFoundError: If instance not found
        """
        try:
            logger.info(f"Fetching instance details: {instance_id}")

            response = self.client.describe_instances(InstanceIds=[instance_id])

            reservations = response.get("Reservations", [])
            if not reservations or not reservations[0].get("Instances"):
                raise ResourceNotFoundError("EC2 Instance", instance_id)

            instance_data = reservations[0]["Instances"][0]
            return self._parse_instance(instance_data)

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")

            if error_code == "InvalidInstanceID.NotFound":
                raise ResourceNotFoundError("EC2 Instance", instance_id) from e

            error_message = e.response.get("Error", {}).get("Message", "")
            logger.error(f"Error fetching instance {instance_id}: {error_code} - {error_message}")
            raise

    def get_instances_by_ids(self, instance_ids: List[str]) -> List[EC2Instance]:
        """
        Get details for multiple EC2 instances by ID.

        Args:
            instance_ids: List of EC2 instance IDs

        Returns:
            List of EC2Instance objects
        """
        if not instance_ids:
            return []

        try:
            logger.info(f"Fetching {len(instance_ids)} instances")

            # EC2 API has a limit, so batch if necessary
            batch_size = 100
            all_instances = []

            for i in range(0, len(instance_ids), batch_size):
                batch = instance_ids[i:i + batch_size]
                response = self.client.describe_instances(InstanceIds=batch)

                for reservation in response.get("Reservations", []):
                    for instance_data in reservation.get("Instances", []):
                        instance = self._parse_instance(instance_data)
                        all_instances.append(instance)

            return all_instances

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_message = e.response.get("Error", {}).get("Message", "")
            logger.error(f"Error fetching instances: {error_code} - {error_message}")
            raise

    def get_instances_by_tag(
        self,
        tag_key: str,
        tag_value: Optional[str] = None,
    ) -> List[EC2Instance]:
        """
        Get instances filtered by tag.

        Args:
            tag_key: Tag key to filter by
            tag_value: Optional tag value (if None, matches any value for the key)

        Returns:
            List of EC2Instance objects
        """
        filters = [{
            "Name": f"tag:{tag_key}",
            "Values": [tag_value] if tag_value else ["*"],
        }]

        return self.list_instances(filters=filters)

    def get_running_instances(self) -> List[EC2Instance]:
        """
        Get all running instances in the region.

        Returns:
            List of running EC2Instance objects
        """
        filters = [{
            "Name": "instance-state-name",
            "Values": ["running"],
        }]

        return self.list_instances(filters=filters)

    def get_stopped_instances(self) -> List[EC2Instance]:
        """
        Get all stopped instances in the region.

        Returns:
            List of stopped EC2Instance objects
        """
        filters = [{
            "Name": "instance-state-name",
            "Values": ["stopped"],
        }]

        return self.list_instances(filters=filters)

    def get_volumes_for_instance(self, instance_id: str) -> List[EBSVolume]:
        """
        Get all EBS volumes attached to an instance.

        Args:
            instance_id: EC2 instance ID

        Returns:
            List of EBSVolume objects
        """
        try:
            logger.debug(f"Fetching volumes for instance: {instance_id}")

            filters = [{
                "Name": "attachment.instance-id",
                "Values": [instance_id],
            }]

            response = self.client.describe_volumes(Filters=filters)
            volumes = []

            for vol_data in response.get("Volumes", []):
                volume = self._parse_volume(vol_data, instance_id)
                volumes.append(volume)

            return volumes

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_message = e.response.get("Error", {}).get("Message", "")
            logger.error(f"Error fetching volumes for {instance_id}: {error_code} - {error_message}")
            return []

    def _parse_instance(self, instance_data: Dict) -> EC2Instance:
        """
        Parse EC2 instance data from AWS API response.

        Args:
            instance_data: Raw instance data from AWS API

        Returns:
            EC2Instance object
        """
        # Parse state
        state_name = instance_data.get("State", {}).get("Name", "unknown")
        try:
            state = InstanceState(state_name)
        except ValueError:
            state = InstanceState.STOPPED

        # Parse tags
        tags = {}
        for tag in instance_data.get("Tags", []):
            tags[tag["Key"]] = tag["Value"]

        # Parse security groups
        security_groups = [
            sg.get("GroupName", sg.get("GroupId", ""))
            for sg in instance_data.get("SecurityGroups", [])
        ]

        # Parse EBS volumes
        ebs_volumes = []
        for bdm in instance_data.get("BlockDeviceMappings", []):
            if "Ebs" in bdm:
                # We'll fetch detailed volume info separately if needed
                ebs_volumes.append(EBSVolume(
                    volume_id=bdm["Ebs"].get("VolumeId", ""),
                    size_gb=0,  # Will be fetched separately
                    volume_type="unknown",
                    device_name=bdm.get("DeviceName", ""),
                    delete_on_termination=bdm["Ebs"].get("DeleteOnTermination", True),
                ))

        # Parse launch time
        launch_time_str = instance_data.get("LaunchTime")
        if isinstance(launch_time_str, datetime):
            launch_time = launch_time_str
        else:
            launch_time = datetime.now()

        # Parse placement
        placement = instance_data.get("Placement", {})
        availability_zone = placement.get("AvailabilityZone", self.region)

        # Parse platform
        platform = "Windows" if instance_data.get("Platform") == "windows" else "Linux/UNIX"

        # Parse IAM instance profile
        iam_profile = None
        if "IamInstanceProfile" in instance_data:
            iam_profile = instance_data["IamInstanceProfile"].get("Arn", "")

        return EC2Instance(
            instance_id=instance_data.get("InstanceId", ""),
            instance_type=instance_data.get("InstanceType", "unknown"),
            state=state,
            region=self.region,
            availability_zone=availability_zone,
            launch_time=launch_time,
            platform=platform,
            vpc_id=instance_data.get("VpcId"),
            subnet_id=instance_data.get("SubnetId"),
            private_ip=instance_data.get("PrivateIpAddress"),
            public_ip=instance_data.get("PublicIpAddress"),
            tags=tags,
            security_groups=security_groups,
            ebs_volumes=ebs_volumes,
            key_name=instance_data.get("KeyName"),
            iam_instance_profile=iam_profile,
            monitoring_enabled=instance_data.get("Monitoring", {}).get("State") == "enabled",
            tenancy=placement.get("Tenancy", "default"),
        )

    def _parse_volume(self, vol_data: Dict, instance_id: str) -> EBSVolume:
        """
        Parse EBS volume data from AWS API response.

        Args:
            vol_data: Raw volume data from AWS API
            instance_id: Instance ID the volume is attached to

        Returns:
            EBSVolume object
        """
        # Find attachment info for this instance
        device_name = ""
        delete_on_termination = True
        state = "unknown"

        for attachment in vol_data.get("Attachments", []):
            if attachment.get("InstanceId") == instance_id:
                device_name = attachment.get("Device", "")
                delete_on_termination = attachment.get("DeleteOnTermination", True)
                state = attachment.get("State", "unknown")
                break

        return EBSVolume(
            volume_id=vol_data.get("VolumeId", ""),
            size_gb=vol_data.get("Size", 0),
            volume_type=vol_data.get("VolumeType", "standard"),
            iops=vol_data.get("Iops"),
            throughput=vol_data.get("Throughput"),
            device_name=device_name,
            state=state,
            delete_on_termination=delete_on_termination,
        )

    def get_instance_types_in_region(self) -> List[str]:
        """
        Get unique instance types used in the region.

        Returns:
            List of instance type names
        """
        instances = self.list_instances()
        instance_types = set(i.instance_type for i in instances)
        return sorted(instance_types)

    def get_region_summary(self) -> Dict[str, any]:
        """
        Get summary statistics for EC2 instances in the region.

        Returns:
            Dictionary with summary statistics
        """
        instances = self.list_instances()

        running = sum(1 for i in instances if i.state == InstanceState.RUNNING)
        stopped = sum(1 for i in instances if i.state == InstanceState.STOPPED)
        total_storage = sum(i.total_storage_gb for i in instances)

        # Group by instance type
        by_type: Dict[str, int] = {}
        for instance in instances:
            by_type[instance.instance_type] = by_type.get(instance.instance_type, 0) + 1

        return {
            "region": self.region,
            "total_instances": len(instances),
            "running_instances": running,
            "stopped_instances": stopped,
            "total_storage_gb": total_storage,
            "instances_by_type": by_type,
            "unique_instance_types": len(by_type),
        }
