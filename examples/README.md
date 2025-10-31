## CostDrill Examples

This directory contains example scripts demonstrating how to use the CostDrill Cost Explorer integration.

### Prerequisites

1. **AWS Credentials**: Configure your AWS credentials using one of these methods:
   ```bash
   # Option 1: AWS CLI
   aws configure

   # Option 2: Environment variables
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_DEFAULT_REGION=us-east-1
   ```

2. **Cost Explorer Enabled**: Ensure AWS Cost Explorer is enabled in your AWS account:
   - Go to AWS Billing Console
   - Navigate to Cost Explorer
   - Click "Enable Cost Explorer" if not already enabled
   - Note: It may take up to 24 hours for data to appear

3. **Install CostDrill**:
   ```bash
   pip install -e ..
   ```

### Examples

#### basic_usage.py

Demonstrates core functionality of the Cost Explorer integration:

```bash
python basic_usage.py
```

Features demonstrated:
- AWS authentication and credential validation
- Fetching EC2 costs (all instances, specific instance, by region)
- Getting cost forecasts
- Fetching costs for other services (S3, RDS, etc.)
- Viewing cost breakdowns by usage type
- Using the caching layer for performance
- Cache management

### Example Output

```
2025-01-30 12:00:00 - INFO - Initializing AWS client...
2025-01-30 12:00:01 - INFO - Authenticated as: arn:aws:iam::123456789012:user/john
2025-01-30 12:00:01 - INFO - Account ID: 123456789012

=== Example 1: EC2 Costs (Last 30 days) ===
2025-01-30 12:00:02 - INFO - Fetching EC2 costs for instance=None, region=None
2025-01-30 12:00:03 - INFO - Date Range: 2024-12-31 to 2025-01-30
2025-01-30 12:00:03 - INFO - Total EC2 Cost: $1,234.56
2025-01-30 12:00:03 - INFO - Number of days: 30

Daily Costs:
  2024-12-31: $42.15
  2025-01-01: $41.89
  ...

Top 5 Cost Breakdowns:
  BoxUsage:t3.large: $650.25 (USAGE_TYPE)
  BoxUsage:t3.micro: $234.56 (USAGE_TYPE)
  DataTransfer-Out: $98.75 (USAGE_TYPE)
  ...
```

### Error Handling

The examples demonstrate proper error handling for common issues:

1. **Missing Credentials**:
   ```
   ERROR - Authentication failed: AWS credentials not found
   ```

2. **Cost Explorer Not Enabled**:
   ```
   ERROR - Cost Explorer not enabled for this account
   ```

3. **Permission Issues**:
   ```
   ERROR - Insufficient permissions for ce:GetCostAndUsage
   ```

### API Reference

#### Key Classes

**AWSClient**: Manages AWS authentication and service clients
```python
from costdrill.core.aws_client import AWSClient

client = AWSClient(region="us-east-1", profile="default")
credentials = client.validate_credentials()
```

**CachedCostExplorer**: Main interface for fetching cost data with automatic caching
```python
from costdrill.core.cached_cost_explorer import CachedCostExplorer

explorer = CachedCostExplorer(
    aws_client=client,
    cache_ttl=3600,  # 1 hour
    enable_cache=True,
)
```

#### Key Methods

**get_ec2_costs()**: Fetch EC2 costs with optional filtering
```python
# All EC2 costs
ec2_costs = explorer.get_ec2_costs(days=30)

# Specific instance
instance_costs = explorer.get_ec2_costs(
    instance_id="i-1234567890abcdef0",
    days=7,
)

# By region
regional_costs = explorer.get_ec2_costs(
    region="us-west-2",
    days=30,
)
```

**get_service_costs()**: Fetch costs for any AWS service
```python
s3_costs = explorer.get_service_costs(
    service="Amazon Simple Storage Service",
    days=30,
    group_by_dimension="USAGE_TYPE",
)
```

**get_cost_forecast()**: Get cost predictions
```python
forecast = explorer.get_cost_forecast(days=30)
print(f"Predicted cost: {forecast.mean_value}")
```

**get_cost_by_tag()**: Filter costs by resource tags
```python
tagged_costs = explorer.get_cost_by_tag(
    tag_key="Environment",
    tag_value="Production",
    days=30,
)
```

### Performance Tips

1. **Enable Caching**: Cache results to avoid hitting AWS API rate limits
   ```python
   explorer = CachedCostExplorer(
       aws_client=client,
       cache_ttl=3600,
       enable_cache=True,
   )
   ```

2. **Clear Expired Cache**: Periodically clean up old cache entries
   ```python
   explorer.clear_expired_cache()
   ```

3. **Use Appropriate Time Ranges**: Shorter time ranges return results faster
   ```python
   # Fast: Last 7 days
   costs = explorer.get_ec2_costs(days=7)

   # Slower: Last 90 days
   costs = explorer.get_ec2_costs(days=90)
   ```

### Troubleshooting

**Issue**: "DataUnavailableException"
- **Solution**: Cost data may not be available for the current day. Query data from previous days.

**Issue**: "ThrottlingException"
- **Solution**: Enable caching or add delays between API calls.

**Issue**: "AccessDeniedException"
- **Solution**: Ensure your IAM user/role has `ce:GetCostAndUsage` permission.

### Additional Resources

- [AWS Cost Explorer API Documentation](https://docs.aws.amazon.com/cost-management/latest/APIReference/API_Operations_AWS_Cost_Explorer_Service.html)
- [CostDrill GitHub Repository](https://github.com/mrodr359/costdrill)
- [Report Issues](https://github.com/mrodr359/costdrill/issues)
