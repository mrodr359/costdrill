#!/usr/bin/env python3
"""
Comprehensive EC2 cost analysis example.

This example demonstrates:
1. Getting a single instance with complete cost breakdown
2. Getting all instances in a region with costs
3. Filtering instances by tags
4. Finding cost optimization opportunities
5. Analyzing cost breakdowns by component
"""

import logging
from rich.console import Console
from rich.table import Table

from costdrill.core.aws_client import AWSClient
from costdrill.core.cached_ec2_aggregator import CachedEC2Aggregator
from costdrill.core.exceptions import (
    AWSAuthenticationError,
    ResourceNotFoundError,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)
console = Console()


def print_instance_details(instance_with_costs):
    """Print detailed information about an instance."""
    instance = instance_with_costs.instance
    breakdown = instance_with_costs.cost_breakdown

    console.print(f"\n[bold cyan]Instance: {instance.name}[/bold cyan]")
    console.print(f"Instance ID: {instance.instance_id}")
    console.print(f"Type: {instance.instance_type}")
    console.print(f"State: {instance.state.value}")
    console.print(f"Region: {instance.region}")
    console.print(f"Launch Time: {instance.launch_time}")
    console.print(f"Uptime: {instance.uptime_hours:.1f} hours")

    # Cost breakdown
    console.print(f"\n[bold green]Cost Breakdown[/bold green]")
    console.print(f"Total Cost: ${breakdown.total_cost.amount:.2f}")
    console.print(f"  Compute: ${breakdown.compute_cost.amount:.2f} ({breakdown.compute_percentage:.1f}%)")
    console.print(f"  Storage: ${breakdown.storage_cost.amount:.2f} ({breakdown.storage_percentage:.1f}%)")
    console.print(f"  Data Transfer: ${breakdown.data_transfer_cost.amount:.2f} ({breakdown.data_transfer_percentage:.1f}%)")
    console.print(f"  Other: ${breakdown.other_costs.amount:.2f}")

    # Per-unit costs
    console.print(f"\n[bold yellow]Unit Costs[/bold yellow]")
    console.print(f"Cost per Hour: ${breakdown.cost_per_hour:.4f}")
    console.print(f"Daily Cost: ${instance_with_costs.daily_cost:.2f}")
    console.print(f"Monthly Projection: ${instance_with_costs.monthly_projection:.2f}")

    # Storage details
    if instance.ebs_volumes:
        console.print(f"\n[bold magenta]EBS Volumes[/bold magenta]")
        for vol in instance.ebs_volumes:
            console.print(f"  {vol.display_name}")


def print_regional_summary_table(summary):
    """Print a table of all instances in the region."""
    table = Table(title=f"EC2 Instances in {summary.region}")

    table.add_column("Instance ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Type", style="yellow")
    table.add_column("State")
    table.add_column("Total Cost", justify="right", style="magenta")
    table.add_column("Daily Cost", justify="right")

    for inst in summary.instances:
        state_color = "green" if inst.instance.is_running else "red"
        table.add_row(
            inst.instance.instance_id,
            inst.instance.name,
            inst.instance.instance_type,
            f"[{state_color}]{inst.instance.state.value}[/{state_color}]",
            f"${inst.total_cost.amount:.2f}",
            f"${inst.daily_cost:.2f}",
        )

    console.print(table)

    # Summary stats
    console.print(f"\n[bold]Summary Statistics[/bold]")
    console.print(f"Total Instances: {summary.instance_count}")
    console.print(f"Running: {summary.running_instance_count}")
    console.print(f"Stopped: {summary.stopped_instance_count}")
    console.print(f"Total Cost: ${summary.total_cost.amount:.2f}")
    console.print(f"Average Cost per Instance: ${summary.average_cost_per_instance:.2f}")


def print_optimization_opportunities(opportunities):
    """Print cost optimization opportunities."""
    if not opportunities:
        console.print("\n[green]No optimization opportunities found![/green]")
        return

    console.print(f"\n[bold red]Cost Optimization Opportunities ({len(opportunities)} found)[/bold red]")

    for i, opp in enumerate(opportunities, 1):
        console.print(f"\n[yellow]{i}. {opp['instance_name']} ({opp['instance_id']})[/yellow]")
        console.print(f"   Instance Type: {opp['instance_type']}")
        console.print(f"   State: {opp['state']}")
        console.print(f"   Cost: ${opp['total_cost']:.2f}")

        indicators = opp['indicators']
        console.print(f"   Issues:")
        for recommendation in indicators['recommendations']:
            console.print(f"     • {recommendation}")


def main():
    """Main example function."""
    try:
        # Initialize AWS client
        console.print("[bold]Initializing AWS client...[/bold]")
        aws_client = AWSClient(region="us-east-1")

        if aws_client.credentials:
            console.print(f"✓ Authenticated as: {aws_client.credentials.arn}")
            console.print(f"✓ Account ID: {aws_client.credentials.account_id}")

        # Initialize cached EC2 aggregator
        console.print("\n[bold]Initializing EC2 cost aggregator...[/bold]")
        ec2_aggregator = CachedEC2Aggregator(
            aws_client=aws_client,
            region="us-east-1",
            cache_ttl=3600,
            enable_cache=True,
        )

        # Example 1: Get a specific instance with costs
        console.print("\n[bold cyan]=== Example 1: Single Instance Analysis ===[/bold cyan]")
        console.print("Enter an instance ID (or press Enter to skip):")
        instance_id = input().strip()

        if instance_id:
            try:
                instance_with_costs = ec2_aggregator.get_instance_with_costs(
                    instance_id=instance_id,
                    days=30,
                )
                print_instance_details(instance_with_costs)
            except ResourceNotFoundError:
                console.print(f"[red]Instance {instance_id} not found[/red]")

        # Example 2: Get all instances in the region
        console.print("\n[bold cyan]=== Example 2: Regional Analysis ===[/bold cyan]")
        console.print("Fetching all EC2 instances in us-east-1...")

        regional_summary = ec2_aggregator.get_all_instances_with_costs(
            days=30,
            include_terminated=False,
        )

        if regional_summary.instance_count > 0:
            print_regional_summary_table(regional_summary)

            # Example 3: Top cost instances
            console.print("\n[bold cyan]=== Example 3: Top 5 Most Expensive Instances ===[/bold cyan]")
            top_instances = regional_summary.get_top_cost_instances(limit=5)

            for i, inst in enumerate(top_instances, 1):
                console.print(
                    f"{i}. {inst.instance.name} ({inst.instance.instance_type}): "
                    f"${inst.total_cost.amount:.2f}"
                )

            # Example 4: Group by instance type
            console.print("\n[bold cyan]=== Example 4: Cost by Instance Type ===[/bold cyan]")
            by_type = regional_summary.get_instances_by_type()

            for instance_type, instances in sorted(by_type.items()):
                total_cost = sum(i.total_cost.amount for i in instances)
                console.print(
                    f"{instance_type}: {len(instances)} instances, "
                    f"${total_cost:.2f} total"
                )

            # Example 5: Filter by tag
            console.print("\n[bold cyan]=== Example 5: Filter by Tag ===[/bold cyan]")
            console.print("Enter a tag key to filter by (or press Enter to skip):")
            tag_key = input().strip()

            if tag_key:
                tagged_instances = regional_summary.get_instances_by_tag(tag_key)
                console.print(f"Found {len(tagged_instances)} instances with tag '{tag_key}'")

                for inst in tagged_instances:
                    tag_value = inst.instance.get_tag(tag_key)
                    console.print(
                        f"  {inst.instance.name}: {tag_key}={tag_value}, "
                        f"${inst.total_cost.amount:.2f}"
                    )

            # Example 6: Cost optimization opportunities
            console.print("\n[bold cyan]=== Example 6: Cost Optimization Opportunities ===[/bold cyan]")
            opportunities = ec2_aggregator.get_cost_optimization_opportunities(days=30)
            print_optimization_opportunities(opportunities)

            # Example 7: Running vs Stopped instances
            console.print("\n[bold cyan]=== Example 7: Running vs Stopped Analysis ===[/bold cyan]")
            by_state = regional_summary.get_instances_by_state()

            for state, instances in by_state.items():
                total_cost = sum(i.total_cost.amount for i in instances)
                console.print(
                    f"{state.value}: {len(instances)} instances, "
                    f"${total_cost:.2f} total"
                )

        else:
            console.print("[yellow]No EC2 instances found in this region[/yellow]")

        # Cache management
        console.print("\n[bold cyan]=== Cache Management ===[/bold cyan]")
        expired_count = ec2_aggregator.clear_expired_cache()
        console.print(f"Cleared {expired_count} expired cache entries")

        console.print("\n[bold green]✓ Analysis complete![/bold green]")

    except AWSAuthenticationError as e:
        console.print(f"[bold red]Authentication failed: {e}[/bold red]")
        console.print("Please check your AWS credentials configuration.")
        return 1

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        logger.exception("Unexpected error")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
