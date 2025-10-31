"""
Main CLI entry point for CostDrill.
"""

import sys
from typing import Optional

import click
from rich.console import Console

from costdrill import __version__

console = Console()


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show version and exit")
@click.option("--service", type=str, help="Start with a specific service (e.g., ec2, s3)")
@click.option("--region", type=str, help="AWS region to focus on")
@click.pass_context
def cli(ctx: click.Context, version: bool, service: Optional[str], region: Optional[str]) -> None:
    """
    CostDrill - Interactive AWS cost exploration tool.

    Launch the interactive TUI to explore AWS costs with drill-down capabilities.
    """
    if version:
        console.print(f"CostDrill version {__version__}")
        sys.exit(0)

    if ctx.invoked_subcommand is None:
        # No subcommand, launch interactive TUI
        launch_tui(service=service, region=region)


@cli.command()
@click.option("--instance", type=str, help="Specific EC2 instance ID")
@click.option("--region", type=str, help="AWS region")
@click.option("--aggregate", is_flag=True, help="Aggregate all EC2 costs")
@click.option("--output", type=click.Choice(["json", "csv", "markdown"]), help="Output format")
@click.option("--export", type=click.Path(), help="Export report to file")
def ec2(
    instance: Optional[str],
    region: Optional[str],
    aggregate: bool,
    output: Optional[str],
    export: Optional[str]
) -> None:
    """Get EC2 cost information."""
    console.print("[yellow]EC2 cost analysis coming soon![/yellow]")
    # TODO: Implement EC2 cost fetching and display


@cli.command()
@click.option("--bucket", type=str, help="Specific S3 bucket name")
@click.option("--region", type=str, help="AWS region")
@click.option("--output", type=click.Choice(["json", "csv", "markdown"]), help="Output format")
def s3(bucket: Optional[str], region: Optional[str], output: Optional[str]) -> None:
    """Get S3 cost information."""
    console.print("[yellow]S3 cost analysis coming soon![/yellow]")
    # TODO: Implement S3 cost fetching and display


@cli.command()
@click.option("--instance", type=str, help="Specific RDS instance ID")
@click.option("--region", type=str, help="AWS region")
@click.option("--output", type=click.Choice(["json", "csv", "markdown"]), help="Output format")
def rds(instance: Optional[str], region: Optional[str], output: Optional[str]) -> None:
    """Get RDS cost information."""
    console.print("[yellow]RDS cost analysis coming soon![/yellow]")
    # TODO: Implement RDS cost fetching and display


def launch_tui(service: Optional[str] = None, region: Optional[str] = None) -> None:
    """Launch the interactive TUI."""
    from costdrill.tui.app import CostDrillApp

    app = CostDrillApp(initial_service=service, initial_region=region)
    app.run()


def main() -> None:
    """Main entry point."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
