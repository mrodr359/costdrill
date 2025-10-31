# Cost Explorer Integration Guide

This guide covers the CostDrill AWS Cost Explorer integration, including setup, usage, and advanced features.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Setup](#setup)
- [Basic Usage](#basic-usage)
- [Advanced Features](#advanced-features)
- [Error Handling](#error-handling)
- [Performance Optimization](#performance-optimization)
- [API Reference](#api-reference)

## Overview

The CostDrill Cost Explorer integration provides a powerful, Pythonic interface to AWS Cost Explorer API with:

- **Automatic authentication** validation
- **Comprehensive error handling** with custom exceptions
- **Data models** for type-safe cost data manipulation
- **Response parsing** from AWS API to structured objects
- **Built-in caching** for performance and rate limit management
- **Multiple query methods** for different use cases

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CostDrill Application                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              CachedCostExplorer (Optional)                   │
│  • Automatic caching with TTL                                │
│  • Cache key generation                                      │
│  • Cache invalidation                                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     CostExplorer                             │
│  • get_cost_and_usage()    • get_cost_forecast()           │
│  • get_ec2_costs()         • get_service_costs()           │
│  • get_cost_by_tag()                                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  CostExplorerParser                          │
│  • Parse AWS API responses                                   │
│  • Transform to CostSummary/CostForecast objects            │
│  • Aggregate and filter data                                │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      AWSClient                               │
│  • Credential validation                                     │
│  • Session management                                        │
│  • Service client creation                                   │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                 AWS Cost Explorer API                        │
└─────────────────────────────────────────────────────────────┘
```

## Setup

### Prerequisites

1. **AWS Account** with Cost Explorer enabled
2. **IAM Permissions** required:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "ce:GetCostAndUsage",
           "ce:GetCostForecast",
           "ce:GetDimensionValues",
           "ce:GetTags"
         ],
         "Resource": "*"
       }
     ]
   }
   ```

3. **AWS Credentials** configured:
   ```bash
   aws configure
   ```

### Installation

```bash
pip install costdrill
```

Or from source:
```bash
git clone https://github.com/mrodr359/costdrill.git
cd costdrill
pip install -e .
```

## Basic Usage

### Initialize Client

```python
from costdrill.core.aws_client import AWSClient
from costdrill.core.cached_cost_explorer import CachedCostExplorer

# Initialize AWS client (validates credentials automatically)
aws_client = AWSClient(region="us-east-1")

# Create Cost Explorer with caching
cost_explorer = CachedCostExplorer(
    aws_client=aws_client,
    cache_ttl=3600,  # 1 hour cache
    enable_cache=True,
)
```

### Fetch EC2 Costs

```python
# Get all EC2 costs for last 30 days
ec2_costs = cost_explorer.get_ec2_costs(days=30)

print(f"Total Cost: {ec2_costs.total_cost}")
print(f"Date Range: {ec2_costs.start_date} to {ec2_costs.end_date}")

# View daily costs
for date, cost in ec2_costs.get_daily_costs():
    print(f"{date.date()}: ${cost:.2f}")

# View cost breakdowns
for breakdown in ec2_costs.breakdowns:
    print(f"{breakdown.key}: {breakdown.cost}")
```

### Get Cost Forecast

```python
# Forecast next 30 days
forecast = cost_explorer.get_cost_forecast(days=30)

print(f"Predicted Cost: {forecast.mean_value}")
print(f"Lower Bound: {forecast.prediction_interval_lower}")
print(f"Upper Bound: {forecast.prediction_interval_upper}")
```

## Advanced Features

### Filter by Instance ID

```python
instance_costs = cost_explorer.get_ec2_costs(
    instance_id="i-1234567890abcdef0",
    days=7,
)
```

### Filter by Region

```python
regional_costs = cost_explorer.get_ec2_costs(
    region="us-west-2",
    days=30,
)
```

### Get Costs for Any Service

```python
# S3 costs
s3_costs = cost_explorer.get_service_costs(
    service="Amazon Simple Storage Service",
    days=30,
    group_by_dimension="USAGE_TYPE",
)

# RDS costs
rds_costs = cost_explorer.get_service_costs(
    service="Amazon Relational Database Service",
    days=30,
)
```

### Filter by Tags

```python
prod_costs = cost_explorer.get_cost_by_tag(
    tag_key="Environment",
    tag_value="Production",
    days=30,
)
```

### Custom Date Ranges

```python
from datetime import datetime, timedelta

start_date = datetime(2025, 1, 1)
end_date = datetime(2025, 1, 31)

custom_costs = cost_explorer.get_cost_and_usage(
    start_date=start_date,
    end_date=end_date,
    granularity="DAILY",
)
```

### Grouping and Filtering

```python
# Group by multiple dimensions
grouped_costs = cost_explorer.get_cost_and_usage(
    start_date=datetime.now() - timedelta(days=30),
    end_date=datetime.now(),
    group_by=[
        {"Type": "DIMENSION", "Key": "SERVICE"},
        {"Type": "DIMENSION", "Key": "REGION"},
    ],
)
```

## Error Handling

The integration provides custom exceptions for different error scenarios:

```python
from costdrill.core.exceptions import (
    AWSAuthenticationError,
    AWSCredentialsNotFoundError,
    CostExplorerNotEnabledException,
    CostExplorerAPIError,
    InvalidDateRangeError,
    RateLimitExceededError,
)

try:
    costs = cost_explorer.get_ec2_costs(days=30)
except AWSCredentialsNotFoundError:
    print("AWS credentials not configured. Run 'aws configure'")
except AWSAuthenticationError as e:
    print(f"Authentication failed: {e}")
except CostExplorerNotEnabledException:
    print("Cost Explorer is not enabled for this account")
except InvalidDateRangeError as e:
    print(f"Invalid date range: {e}")
except RateLimitExceededError as e:
    print(f"Rate limit exceeded. Retry after {e.retry_after} seconds")
except CostExplorerAPIError as e:
    print(f"API error: {e}")
```

## Performance Optimization

### Caching

The `CachedCostExplorer` automatically caches API responses:

```python
# Enable caching with custom TTL
cost_explorer = CachedCostExplorer(
    aws_client=aws_client,
    cache_ttl=7200,  # 2 hours
    enable_cache=True,
)

# First call hits API
costs1 = cost_explorer.get_ec2_costs(days=30)

# Second call returns cached result (much faster)
costs2 = cost_explorer.get_ec2_costs(days=30)

# Clear cache manually
cost_explorer.clear_cache()

# Clear only expired entries
expired_count = cost_explorer.clear_expired_cache()
```

### Direct API Access (No Caching)

```python
from costdrill.core.cost_explorer import CostExplorer

# Use CostExplorer directly for no caching
direct_explorer = CostExplorer(aws_client)
costs = direct_explorer.get_ec2_costs(days=30)
```

### Rate Limit Management

- Use caching to reduce API calls
- Batch queries when possible
- Handle `RateLimitExceededError` with exponential backoff

```python
import time

def fetch_with_retry(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitExceededError as e:
            if attempt < max_retries - 1:
                wait_time = e.retry_after * (2 ** attempt)
                time.sleep(wait_time)
            else:
                raise
```

## API Reference

### Data Models

#### CostAmount
```python
@dataclass
class CostAmount:
    amount: float
    unit: str = "USD"

    def __str__(self) -> str:
        return f"${self.amount:.2f}"
```

#### CostSummary
```python
@dataclass
class CostSummary:
    start_date: datetime
    end_date: datetime
    time_series: List[TimeSeriesCost]
    total_cost: CostAmount
    breakdowns: List[CostBreakdown]

    def get_daily_costs(self) -> List[tuple[datetime, float]]
    def get_breakdown_by_key(self, key: str) -> List[CostBreakdown]
```

#### CostForecast
```python
@dataclass
class CostForecast:
    start_date: datetime
    end_date: datetime
    mean_value: CostAmount
    prediction_interval_lower: CostAmount
    prediction_interval_upper: CostAmount
    time_series: List[TimeSeriesCost]
```

### Main Methods

#### get_ec2_costs()
```python
def get_ec2_costs(
    self,
    instance_id: Optional[str] = None,
    region: Optional[str] = None,
    days: int = 30,
) -> CostSummary
```

#### get_service_costs()
```python
def get_service_costs(
    self,
    service: str,
    days: int = 30,
    group_by_dimension: Optional[str] = None,
) -> CostSummary
```

#### get_cost_forecast()
```python
def get_cost_forecast(
    self,
    days: int = 30,
    metric: str = "UNBLENDED_COST",
) -> CostForecast
```

#### get_cost_by_tag()
```python
def get_cost_by_tag(
    self,
    tag_key: str,
    tag_value: Optional[str] = None,
    days: int = 30,
) -> CostSummary
```

## Best Practices

1. **Always use caching** in production to avoid rate limits
2. **Handle exceptions** appropriately for user-facing applications
3. **Validate date ranges** before queries
4. **Use appropriate granularity** (DAILY for detailed, MONTHLY for overview)
5. **Clear expired cache** periodically to save disk space
6. **Log API calls** for debugging and monitoring

## Limitations

- Cost Explorer data is typically 24 hours delayed
- Historical data available for approximately 14 months
- API rate limits apply (use caching to mitigate)
- Forecast accuracy depends on historical patterns
- Some cost allocation features require specific AWS setups

## Troubleshooting

### "Cost Explorer is not enabled"
**Solution**: Enable Cost Explorer in AWS Billing Console. Wait up to 24 hours for data.

### "DataUnavailableException"
**Solution**: Query previous days' data, not today's.

### "ThrottlingException"
**Solution**: Enable caching or implement exponential backoff.

### "AccessDeniedException"
**Solution**: Add required IAM permissions (ce:GetCostAndUsage, etc.)

## Additional Resources

- [AWS Cost Explorer API Documentation](https://docs.aws.amazon.com/cost-management/latest/APIReference/API_Operations_AWS_Cost_Explorer_Service.html)
- [CostDrill Examples](../examples/)
- [GitHub Issues](https://github.com/mrodr359/costdrill/issues)
