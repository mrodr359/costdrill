"""
AWS client wrapper for boto3 interactions.
"""

import logging
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    NoCredentialsError,
    ProfileNotFound,
)

from costdrill.core.exceptions import (
    AWSAuthenticationError,
    AWSCredentialsNotFoundError,
    AWSPermissionError,
)
from costdrill.core.models import AWSCredentials

logger = logging.getLogger(__name__)


class AWSClient:
    """Wrapper for AWS SDK (boto3) operations."""

    def __init__(self, region: Optional[str] = None, profile: Optional[str] = None):
        """
        Initialize AWS client.

        Args:
            region: AWS region (defaults to AWS CLI config)
            profile: AWS profile name (defaults to default profile)

        Raises:
            AWSCredentialsNotFoundError: If credentials are not configured
            AWSAuthenticationError: If authentication fails
        """
        self.region = region
        self.profile = profile
        self.session = self._create_session()
        self._credentials: Optional[AWSCredentials] = None

        # Validate credentials on initialization
        self.validate_credentials()

    def _create_session(self) -> boto3.Session:
        """
        Create boto3 session with specified profile and region.

        Returns:
            Configured boto3 Session

        Raises:
            AWSCredentialsNotFoundError: If profile is not found
        """
        kwargs: Dict[str, Any] = {}
        if self.profile:
            kwargs["profile_name"] = self.profile
        if self.region:
            kwargs["region_name"] = self.region

        try:
            return boto3.Session(**kwargs)
        except ProfileNotFound as e:
            logger.error(f"AWS profile '{self.profile}' not found")
            raise AWSCredentialsNotFoundError() from e

    def get_cost_explorer_client(self) -> Any:
        """
        Get AWS Cost Explorer client.

        Returns:
            Boto3 Cost Explorer client
        """
        # Cost Explorer is always in us-east-1
        return self.session.client("ce", region_name="us-east-1")

    def get_ec2_client(self, region: Optional[str] = None) -> Any:
        """
        Get AWS EC2 client.

        Args:
            region: Optional specific region (defaults to session region)

        Returns:
            Boto3 EC2 client
        """
        if region:
            return self.session.client("ec2", region_name=region)
        return self.session.client("ec2")

    def get_s3_client(self) -> Any:
        """
        Get AWS S3 client.

        Returns:
            Boto3 S3 client
        """
        return self.session.client("s3")

    def get_rds_client(self, region: Optional[str] = None) -> Any:
        """
        Get AWS RDS client.

        Args:
            region: Optional specific region (defaults to session region)

        Returns:
            Boto3 RDS client
        """
        if region:
            return self.session.client("rds", region_name=region)
        return self.session.client("rds")

    def validate_credentials(self) -> AWSCredentials:
        """
        Validate AWS credentials and retrieve account information.

        Returns:
            AWSCredentials object with account information

        Raises:
            AWSCredentialsNotFoundError: If credentials are not configured
            AWSAuthenticationError: If authentication fails
            AWSPermissionError: If insufficient permissions
        """
        try:
            sts = self.session.client("sts")
            response = sts.get_caller_identity()

            self._credentials = AWSCredentials(
                account_id=response["Account"],
                user_id=response["UserId"],
                arn=response["Arn"],
                region=self.session.region_name,
                profile=self.profile,
            )

            logger.info(f"Successfully authenticated as {self._credentials.arn}")
            return self._credentials

        except NoCredentialsError as e:
            logger.error("AWS credentials not found")
            raise AWSCredentialsNotFoundError() from e

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_message = e.response.get("Error", {}).get("Message", "")

            if error_code == "InvalidClientTokenId":
                raise AWSAuthenticationError(
                    "Invalid AWS credentials. Please check your access key."
                ) from e
            elif error_code == "SignatureDoesNotMatch":
                raise AWSAuthenticationError(
                    "AWS signature does not match. Please check your secret key."
                ) from e
            elif error_code == "AccessDenied":
                raise AWSPermissionError(
                    "sts", "GetCallerIdentity", error_message
                ) from e
            else:
                raise AWSAuthenticationError(
                    f"Authentication failed: {error_message}"
                ) from e

        except BotoCoreError as e:
            logger.error(f"AWS authentication error: {e}")
            raise AWSAuthenticationError(str(e)) from e

    @property
    def credentials(self) -> Optional[AWSCredentials]:
        """Get cached credentials information."""
        return self._credentials

    def get_available_regions(self, service: str = "ec2") -> list[str]:
        """
        Get list of available AWS regions for a service.

        Args:
            service: AWS service name (default: ec2)

        Returns:
            List of region names
        """
        try:
            return self.session.get_available_regions(service)
        except Exception as e:
            logger.warning(f"Could not fetch available regions: {e}")
            # Return common regions as fallback
            return [
                "us-east-1",
                "us-east-2",
                "us-west-1",
                "us-west-2",
                "eu-west-1",
                "eu-central-1",
                "ap-southeast-1",
                "ap-northeast-1",
            ]
