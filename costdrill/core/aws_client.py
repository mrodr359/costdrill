"""
AWS client wrapper for boto3 interactions.
"""

from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError


class AWSClient:
    """Wrapper for AWS SDK (boto3) operations."""

    def __init__(self, region: Optional[str] = None, profile: Optional[str] = None):
        """
        Initialize AWS client.

        Args:
            region: AWS region (defaults to AWS CLI config)
            profile: AWS profile name (defaults to default profile)
        """
        self.region = region
        self.profile = profile
        self.session = self._create_session()

    def _create_session(self) -> boto3.Session:
        """Create boto3 session with specified profile and region."""
        kwargs: Dict[str, Any] = {}
        if self.profile:
            kwargs["profile_name"] = self.profile
        if self.region:
            kwargs["region_name"] = self.region

        return boto3.Session(**kwargs)

    def get_cost_explorer_client(self) -> Any:
        """Get AWS Cost Explorer client."""
        return self.session.client("ce")

    def get_ec2_client(self) -> Any:
        """Get AWS EC2 client."""
        return self.session.client("ec2")

    def get_s3_client(self) -> Any:
        """Get AWS S3 client."""
        return self.session.client("s3")

    def get_rds_client(self) -> Any:
        """Get AWS RDS client."""
        return self.session.client("rds")

    def validate_credentials(self) -> bool:
        """
        Validate AWS credentials.

        Returns:
            True if credentials are valid, False otherwise
        """
        try:
            sts = self.session.client("sts")
            sts.get_caller_identity()
            return True
        except (BotoCoreError, ClientError):
            return False
