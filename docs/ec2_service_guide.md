# EC2 Service Integration Guide

Complete guide for using the CostDrill EC2 service to analyze instance costs with detailed breakdowns.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Core Features](#core-features)
- [API Reference](#api-reference)
- [Cost Analysis](#cost-analysis)
- [Optimization](#optimization)
- [Best Practices](#best-practices)

## Overview

The CostDrill EC2 service provides comprehensive cost analysis for EC2 instances by combining:
- **EC2 instance metadata** (type, state, tags, volumes, etc.)
- **Cost Explorer data** (historical costs with breakdowns)
- **Intelligent analysis** (categorization, optimization opportunities)

### Key Capabilities

✅ Get complete cost breakdown for any EC2 instance
✅ Analyze all instances in a region with costs
✅ Filter by tags, state, instance type
✅ Identify cost optimization opportunities
✅ Break down costs by component (compute, storage, data transfer)
✅ Calculate per-hour and projected monthly costs
✅ Built-in caching for performance

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│             CachedEC2Aggregator (Recommended)               │
│  • Automatic caching with TTL                                │
│  • Cache invalidation                                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   EC2CostAggregator                          │
│  • Combines EC2Service + CostExplorer                       │
│  • get_instance_with_costs()                                │
│  • get_all_instances_with_costs()                           │
│  • get_cost_optimization_opportunities()                    │
└──────────┬────────────────────────────┬─────────────────────┘
           │                            │
           ▼                            ▼
┌──────────────────────┐    ┌──────────────────────────┐
│    EC2Service        │    │   CostExplorer           │
│  • list_instances()  │    │   • get_ec2_costs()      │
│  • get_instance()    │    │   • get_cost_and_usage() │
│  • get_volumes()     │    └──────────────────────────┘
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│                    EC2CostAnalyzer                            │
│  • Categorizes costs (compute, storage, data transfer)       │
│  • Calculates waste indicators                               │
│  • Provides optimization recommendations                     │
└──────────────────────────────────────────────────────────────┘
```

## Quick Start

### Installation

```bash
pip install costdrill
```

### Basic Usage

```python
from costdrill.core.aws_client import AWSClient
from costdrill.core.cached_ec2_aggregator import CachedEC2Aggregator

# Initialize
aws_client = AWSClient(region="us-east-1")
ec2_aggregator = CachedEC2Aggregator(
    aws_client=aws_client,
    region="us-east-1",
    enable_cache=True,
)

# Get single instance with costs
instance_with_costs = ec2_aggregator.get_instance_with_costs(
    instance_id="i-1234567890abcdef0",
    days=30,
)

print(f"Instance: {instance_with_costs.instance.name}")
print(f"Total Cost: {instance_with_costs.total_cost}")
print(f"Daily Cost: ${instance_with_costs.daily_cost:.2f}")

# Get all instances in region
regional_summary = ec2_aggregator.get_all_instances_with_costs(days=30)

print(f"Total Instances: {regional_summary.instance_count}")
print(f"Total Cost: {regional_summary.total_cost}")
```

## Core Features

### 1. Single Instance Analysis

Get complete details and cost breakdown for a specific instance:

```python
instance_with_costs = ec2_aggregator.get_instance_with_costs(
    instance_id="i-1234567890abcdef0",
    days=30,
)

# Access instance metadata
instance = instance_with_costs.instance
print(f"Instance Type: {instance.instance_type}")
print(f"State: {instance.state.value}")
print(f"Launch Time: {instance.launch_time}")
print(f"Uptime Hours: {instance.uptime_hours:.1f}")
print(f"Storage: {instance.total_storage_gb} GB")

# Access cost breakdown
breakdown = instance_with_costs.cost_breakdown
print(f"Compute Cost: {breakdown.compute_cost}")
print(f"Storage Cost: {breakdown.storage_cost}")
print(f"Data Transfer: {breakdown.data_transfer_cost}")
print(f"Cost per Hour: ${breakdown.cost_per_hour:.4f}")
```

### 2. Regional Analysis

Analyze all EC2 instances in a region:

```python
regional_summary = ec2_aggregator.get_all_instances_with_costs(
    days=30,
    include_terminated=False,
)

print(f"Region: {regional_summary.region}")
print(f"Total Instances: {regional_summary.instance_count}")
print(f"Running: {regional_summary.running_instance_count}")
print(f"Stopped: {regional_summary.stopped_instance_count}")
print(f"Total Cost: {regional_summary.total_cost}")
print(f"Avg Cost/Instance: ${regional_summary.average_cost_per_instance:.2f}")
```

### 3. Filter by Tags

Get instances with specific tags and their costs:

```python
# Filter by tag
prod_instances = ec2_aggregator.get_instances_by_tag_with_costs(
    tag_key="Environment",
    tag_value="Production",
    days=30,
)

for inst in prod_instances.instances:
    print(f"{inst.instance.name}: ${inst.total_cost.amount:.2f}")

# Or filter from existing summary
regional_summary = ec2_aggregator.get_all_instances_with_costs(days=30)
dev_instances = regional_summary.get_instances_by_tag("Environment", "Development")
```

### 4. Top Cost Instances

Identify your most expensive instances:

```python
regional_summary = ec2_aggregator.get_all_instances_with_costs(days=30)

# Get top 10 most expensive instances
top_10 = regional_summary.get_top_cost_instances(limit=10)

for i, inst in enumerate(top_10, 1):
    print(f"{i}. {inst.instance.name} ({inst.instance.instance_type})")
    print(f"   Total Cost: ${inst.total_cost.amount:.2f}")
    print(f"   Daily Cost: ${inst.daily_cost:.2f}")
    print(f"   Monthly Projection: ${inst.monthly_projection:.2f}")
```

### 5. Group by Instance Type

Analyze costs by instance type:

```python
regional_summary = ec2_aggregator.get_all_instances_with_costs(days=30)
by_type = regional_summary.get_instances_by_type()

for instance_type, instances in sorted(by_type.items()):
    total_cost = sum(i.total_cost.amount for i in instances)
    avg_cost = total_cost / len(instances) if instances else 0

    print(f"{instance_type}:")
    print(f"  Count: {len(instances)}")
    print(f"  Total Cost: ${total_cost:.2f}")
    print(f"  Avg Cost: ${avg_cost:.2f}")
```

### 6. Running vs Stopped Analysis

Compare costs between running and stopped instances:

```python
regional_summary = ec2_aggregator.get_all_instances_with_costs(days=30)
by_state = regional_summary.get_instances_by_state()

for state, instances in by_state.items():
    total_cost = sum(i.total_cost.amount for i in instances)
    print(f"{state.value}:")
    print(f"  Count: {len(instances)}")
    print(f"  Total Cost: ${total_cost:.2f}")
```

## Cost Analysis

### Cost Breakdown Components

Each instance has costs broken down into six categories:

1. **Compute Cost** - Instance runtime (On-Demand, Reserved, Spot)
2. **Storage Cost** - EBS volumes, provisioned IOPS
3. **Data Transfer Cost** - Data transfer out, inter-region
4. **Snapshot Cost** - EBS snapshots
5. **Elastic IP Cost** - Elastic IP addresses
6. **Other Costs** - Miscellaneous charges

```python
breakdown = instance_with_costs.cost_breakdown

# Get breakdown as dictionary
breakdown_dict = breakdown.get_cost_breakdown_dict()

for component, data in breakdown_dict.items():
    print(f"{component.title()}:")
    print(f"  Amount: ${data['amount']:.2f}")
    print(f"  Percentage: {data['percentage']:.1f}%")
```

### Per-Unit Costs

Calculate unit costs for budgeting:

```python
breakdown = instance_with_costs.cost_breakdown

# Hourly costs
print(f"Cost per Hour: ${breakdown.cost_per_hour:.4f}")

# Daily costs
daily_cost = instance_with_costs.daily_cost
print(f"Daily Cost: ${daily_cost:.2f}")

# Monthly projection
monthly = instance_with_costs.monthly_projection
print(f"Monthly Projection: ${monthly:.2f}")
print(f"Annual Projection: ${monthly * 12:.2f}")
```

### Usage Metrics

Access usage metrics for deeper analysis:

```python
breakdown = instance_with_costs.cost_breakdown

print(f"Running Hours: {breakdown.running_hours:.1f}")
print(f"Storage GB-Hours: {breakdown.storage_gb_hours:.1f}")

# View detailed usage type breakdown
for usage_type, cost in breakdown.usage_type_breakdown.items():
    print(f"{usage_type}: {cost}")
```

## Optimization

### Identify Optimization Opportunities

Automatically find potential cost savings:

```python
opportunities = ec2_aggregator.get_cost_optimization_opportunities(days=30)

for opp in opportunities:
    print(f"\nInstance: {opp['instance_name']} ({opp['instance_id']})")
    print(f"Instance Type: {opp['instance_type']}")
    print(f"State: {opp['state']}")
    print(f"Cost: ${opp['total_cost']:.2f}")

    print("Issues:")
    for recommendation in opp['indicators']['recommendations']:
        print(f"  • {recommendation}")
```

### Waste Indicators

The analyzer identifies several waste patterns:

1. **Stopped with Costs** - Stopped instances still incurring charges
2. **High Storage Ratio** - Storage costs exceed compute costs
3. **High Data Transfer** - Excessive data transfer charges
4. **Elastic IP Charges** - Unassociated or idle Elastic IPs

```python
from costdrill.core.ec2_cost_analyzer import EC2CostAnalyzer

analyzer = EC2CostAnalyzer()

waste_indicators = analyzer.calculate_waste_indicators(
    breakdown=instance_with_costs.cost_breakdown,
    instance_state=instance_with_costs.instance.state.value,
)

if waste_indicators['has_waste']:
    print("⚠️  Potential waste detected!")
    for recommendation in waste_indicators['recommendations']:
        print(f"  • {recommendation}")
```

## API Reference

### CachedEC2Aggregator

Main interface for EC2 cost analysis with automatic caching.

#### Methods

**get_instance_with_costs(instance_id, days=30)**
```python
Get single instance with complete cost breakdown.

Args:
    instance_id (str): EC2 instance ID
    days (int): Number of days of cost data

Returns:
    EC2InstanceWithCosts: Instance with cost breakdown
```

**get_all_instances_with_costs(days=30, include_terminated=False)**
```python
Get all instances in region with costs.

Args:
    days (int): Number of days of cost data
    include_terminated (bool): Include terminated instances

Returns:
    RegionalEC2Summary: Summary with all instances
```

**get_instances_by_tag_with_costs(tag_key, tag_value=None, days=30)**
```python
Get instances filtered by tag with costs.

Args:
    tag_key (str): Tag key to filter by
    tag_value (str, optional): Tag value to match
    days (int): Number of days of cost data

Returns:
    RegionalEC2Summary: Filtered instances
```

**get_running_instances_with_costs(days=30)**
```python
Get only running instances with costs.

Args:
    days (int): Number of days of cost data

Returns:
    RegionalEC2Summary: Running instances only
```

**get_cost_optimization_opportunities(days=30)**
```python
Identify cost optimization opportunities.

Args:
    days (int): Number of days to analyze

Returns:
    List[Dict]: List of optimization opportunities
```

### Data Models

**EC2Instance**
- instance_id, instance_type, state, region
- launch_time, uptime_hours, tags
- ebs_volumes, total_storage_gb
- vpc_id, subnet_id, security_groups

**EC2CostBreakdown**
- total_cost, compute_cost, storage_cost
- data_transfer_cost, snapshot_cost, elastic_ip_cost
- running_hours, cost_per_hour
- usage_type_breakdown

**EC2InstanceWithCosts**
- instance (EC2Instance)
- cost_breakdown (EC2CostBreakdown)
- start_date, end_date
- daily_cost, monthly_projection

**RegionalEC2Summary**
- region, instances, total_cost
- instance_count, running_instance_count
- get_top_cost_instances(), get_instances_by_tag()
- get_instances_by_type(), get_instances_by_state()

## Best Practices

### 1. Use Caching

Always use `CachedEC2Aggregator` in production:

```python
# Good - with caching
ec2_aggregator = CachedEC2Aggregator(
    aws_client=aws_client,
    cache_ttl=3600,
    enable_cache=True,
)

# Avoid - without caching (slower, more API calls)
from costdrill.core.ec2_cost_aggregator import EC2CostAggregator
ec2_aggregator = EC2CostAggregator(aws_client)
```

### 2. Choose Appropriate Time Ranges

Shorter time ranges are faster:

```python
# Fast - Last 7 days
summary = ec2_aggregator.get_all_instances_with_costs(days=7)

# Slower - Last 90 days
summary = ec2_aggregator.get_all_instances_with_costs(days=90)
```

### 3. Filter Early

Filter at the API level when possible:

```python
# Good - Filter at API level
prod_instances = ec2_aggregator.get_instances_by_tag_with_costs(
    tag_key="Environment",
    tag_value="Production",
    days=30,
)

# Less efficient - Fetch all then filter
all_instances = ec2_aggregator.get_all_instances_with_costs(days=30)
prod_instances = all_instances.get_instances_by_tag("Environment", "Production")
```

### 4. Handle Errors Gracefully

```python
from costdrill.core.exceptions import ResourceNotFoundError

try:
    instance = ec2_aggregator.get_instance_with_costs(instance_id)
except ResourceNotFoundError:
    print(f"Instance {instance_id} not found")
except Exception as e:
    print(f"Error: {e}")
```

### 5. Clear Cache Periodically

```python
# Clear expired entries
expired_count = ec2_aggregator.clear_expired_cache()

# Clear all cache
ec2_aggregator.clear_cache()

# Invalidate specific instance
ec2_aggregator.invalidate_instance_cache("i-1234567890abcdef0")
```

## Performance Tips

1. **Enable caching** - Reduces API calls and improves response times
2. **Use shorter time ranges** - Fetch only the data you need
3. **Batch operations** - Get all instances at once vs. individual calls
4. **Clear expired cache** - Periodically clean up old cache entries
5. **Filter efficiently** - Use API-level filtering when possible

## Troubleshooting

### No Cost Data

**Issue**: Instance has no cost data
**Solution**: Cost Explorer data is typically 24 hours delayed. Check previous days.

### Slow Performance

**Issue**: Queries are slow
**Solution**: Enable caching and reduce time range (e.g., 7 days instead of 90).

### Missing Instances

**Issue**: Expected instances not appearing
**Solution**: Check region, verify instance exists, and ensure not terminated.

### High Cache Memory

**Issue**: Cache directory growing large
**Solution**: Clear expired cache regularly: `ec2_aggregator.clear_expired_cache()`

## Additional Resources

- [Cost Explorer Integration Guide](./cost_explorer_integration.md)
- [Examples Directory](../examples/)
- [GitHub Repository](https://github.com/mrodr359/costdrill)
- [Report Issues](https://github.com/mrodr359/costdrill/issues)
