"""
Custom exceptions for CostDrill.
"""


class CostDrillException(Exception):
    """Base exception for CostDrill."""

    pass


class AWSAuthenticationError(CostDrillException):
    """Raised when AWS authentication fails."""

    def __init__(self, message: str = "AWS authentication failed"):
        self.message = message
        super().__init__(self.message)


class AWSCredentialsNotFoundError(AWSAuthenticationError):
    """Raised when AWS credentials are not configured."""

    def __init__(self) -> None:
        super().__init__(
            "AWS credentials not found. Please configure credentials using 'aws configure' "
            "or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables."
        )


class AWSPermissionError(CostDrillException):
    """Raised when AWS API call fails due to insufficient permissions."""

    def __init__(self, service: str, action: str, details: str = ""):
        self.service = service
        self.action = action
        self.details = details
        message = f"Insufficient permissions for {service}:{action}"
        if details:
            message += f" - {details}"
        super().__init__(message)


class CostExplorerNotEnabledException(CostDrillException):
    """Raised when Cost Explorer is not enabled for the account."""

    def __init__(self) -> None:
        super().__init__(
            "AWS Cost Explorer is not enabled for this account. "
            "Please enable it in the AWS Billing console."
        )


class CostExplorerAPIError(CostDrillException):
    """Raised when Cost Explorer API call fails."""

    def __init__(self, message: str, error_code: str = ""):
        self.error_code = error_code
        super().__init__(f"Cost Explorer API error: {message}")


class InvalidDateRangeError(CostDrillException):
    """Raised when date range is invalid."""

    def __init__(self, message: str = "Invalid date range specified"):
        super().__init__(message)


class ResourceNotFoundError(CostDrillException):
    """Raised when a requested AWS resource is not found."""

    def __init__(self, resource_type: str, resource_id: str):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(f"{resource_type} '{resource_id}' not found")


class RateLimitExceededError(CostDrillException):
    """Raised when AWS API rate limit is exceeded."""

    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(
            f"AWS API rate limit exceeded. Please retry after {retry_after} seconds."
        )
