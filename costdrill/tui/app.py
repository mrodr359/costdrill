"""
Main Textual application for the CostDrill TUI launch experience.
"""

from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, Static, Select, LoadingIndicator

from costdrill.core.aws_client import AWSClient
from costdrill.core.cost_explorer import CostExplorer
from costdrill.core.exceptions import (
    AWSAuthenticationError,
    AWSCredentialsNotFoundError,
    CostExplorerNotEnabledException,
)


class DynamicChecklist(Container):
    """Dynamic checklist that validates AWS connectivity."""

    def compose(self) -> ComposeResult:
        yield Static("[#8be9fd][b]Launch Checklist[/b][/]", classes="checklist-title")
        yield Static("[yellow]⟳[/yellow] Checking AWS credentials...", id="check-credentials", classes="check-item")
        yield Static("[dim]⟳[/dim] Checking AWS connectivity...", id="check-connectivity", classes="check-item")
        yield Static("[dim]⟳[/dim] Checking Cost Explorer...", id="check-cost-explorer", classes="check-item")

    def update_check(self, check_id: str, status: str, message: str) -> None:
        """Update a checklist item.

        Args:
            check_id: ID of the check item (e.g., "check-credentials")
            status: "checking", "success", "error", "warning"
            message: The message to display
        """
        icons = {
            "checking": "[yellow]⟳[/yellow]",
            "success": "[green]✓[/green]",
            "error": "[red]✗[/red]",
            "warning": "[yellow]⚠[/yellow]",
        }
        icon = icons.get(status, "[dim]•[/dim]")
        self.query_one(f"#{check_id}", Static).update(f"{icon} {message}")


class HeroBanner(Container):
    """Top hero banner with branding and key messaging."""

    def compose(self) -> ComposeResult:
        yield Static(
            """\
[#8be9fd][b]COSTDRILL[/b][/]
[dim]AWS cost visibility without the console fatigue.[/dim]

[b]Navigate[/b] services, [b]drill[/b] into spend, and surface [magenta][b]savings signals[/b][/magenta] in seconds.
            """,
            classes="hero-title",
        )


class AccentPanel(Container):
    """Reusable accent panel."""

    def __init__(self, title: str, body: str, *, classes: str = "") -> None:
        super().__init__(classes=f"accent-panel {classes}")
        self._title = title
        self._body = body

    def compose(self) -> ComposeResult:
        yield Static(f"[#bd93f9][b]{self._title}[/b][/]", classes="panel-heading")
        yield Static(self._body, classes="panel-body")


class ServiceSelector(Container):
    """Widget for selecting AWS services."""

    SERVICES = [
        ("EC2 — Elastic Compute Cloud", "ec2"),
        ("S3 — Simple Storage Service [Coming Soon]", "s3"),
        ("RDS — Relational Database Service [Coming Soon]", "rds"),
        ("Lambda — Serverless Functions [Coming Soon]", "lambda"),
        ("CloudFront — Global CDN [Coming Soon]", "cloudfront"),
    ]

    def compose(self) -> ComposeResult:
        yield Static("[#8be9fd][b]Choose a starting point[/b][/]", classes="selector-heading")
        yield Static(
            "Pick a service to explore resource level costs. You can refine to regions and "
            "resource groups after selection.",
            classes="selector-blurb",
        )
        yield Select(
            options=[(label, value) for label, value in self.SERVICES],
            prompt="Select AWS Service",
            id="service-select",
        )
        yield Static(
            "[dim]Hotkeys: ↑↓ navigate • ↵ select • q quit[/dim]",
            classes="selector-hint",
        )


class QuickInsights(Container):
    """Showcase quick insight tiles to set expectations."""

    def compose(self) -> ComposeResult:
        yield AccentPanel(
            "Deep Dives",
            "[cyan]Break down[/] compute vs storage vs transfer with a glance.",
            classes="tile",
        )
        yield AccentPanel(
            "Save Smart",
            "Surface [magenta]right-sizing[/] opportunities before the bill hits.",
            classes="tile",
        )
        yield AccentPanel(
            "Share Wins",
            "Export [green]JSON[/], [green]CSV[/], or [green]Markdown[/] reports instantly.",
            classes="tile",
        )


class CostDrillApp(App):
    """Main CostDrill TUI application."""

    CSS = """
    Screen {
        background: #11121f;
        color: #f8f9fd;
    }

    Header, Footer {
        background: #1f2a50;
        color: #f8f9fd;
        border: none;
    }

    .main-layout {
        padding: 2 3;
        height: 100%;
        width: 100%;
        background: #11121f;
    }

    HeroBanner {
        padding: 2 3;
        background: #23243a;
        border: solid #44475a;
        border-left: tall #bd93f9;
        margin-bottom: 1;
        layout: vertical;
    }

    .hero-title {
        text-style: bold;
    }

    DynamicChecklist {
        margin-top: 1;
        layout: vertical;
    }

    .checklist-title {
        color: #8be9fd;
        text-style: bold;
        margin-bottom: 1;
    }

    .check-item {
        margin: 0 0 0 1;
        color: #f8f9fd;
    }

    .content {
        height: 1fr;
    }

    .left-column, .right-column {
        background: #1b1d2e;
        border: solid #3c3f58;
        padding: 2 3;
        layout: vertical;
    }

    .left-column {
        width: 2fr;
    }

    .right-column {
        width: 3fr;
    }

    .selector-heading {
        color: #8be9fd;
        text-style: bold;
    }

    .selector-blurb {
        margin-top: 1;
        color: #7f85a3;
    }

    #service-select {
        margin-top: 1;
        height: 3;
        border: solid #3c3f58;
        background: #1b1d2e;
        color: #f8f9fd;
    }

    .selector-hint {
        margin-top: 1;
        color: #646b8a;
    }

    QuickInsights {
        layout: horizontal;
    }

    AccentPanel {
        layout: vertical;
    }

    .tile {
        width: 1fr;
        height: auto;
        background: #171829;
        border: solid #34364f;
        border-top: solid #ff79c6;
        padding: 1 2;
        color: #dde3ff;
    }

    .accent-panel .panel-heading {
        color: #bd93f9;
        text-style: bold;
        margin-bottom: 1;
    }

    .accent-panel .panel-body {
        color: #f0f3ff;
    }

    .insight-footer {
        margin-top: 2;
        color: #646b8a;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Toggle Dark Mode"),
    ]

    def __init__(
        self,
        initial_service: Optional[str] = None,
        initial_region: Optional[str] = None,
    ):
        super().__init__()
        self.initial_service = initial_service
        self.initial_region = initial_region
        self.title = "CostDrill • AWS Cost Explorer"
        self.sub_title = "Interactive cloud cost analysis"
        self.aws_ready = False
        self.aws_client: Optional[AWSClient] = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Container(classes="main-layout"):
            yield HeroBanner()
            yield DynamicChecklist(id="checklist")
            with Horizontal(classes="content"):
                with Vertical(classes="left-column"):
                    yield ServiceSelector()
                with Vertical(classes="right-column"):
                    yield QuickInsights()
                    yield Static(
                        "Need guidance on FinOps maturity? [b]Open the playbook[/b] "
                        "after finishing your first drill-down.",
                        classes="insight-footer",
                    )
        yield Footer()

    def on_mount(self) -> None:
        """Handle app mount."""
        # Start AWS connectivity checks
        self.run_worker(self._check_aws_connectivity, exclusive=True, name="aws_checks")

        if self.initial_service:
            self.notify(f"Starting with service: {self.initial_service}")

    async def _check_aws_connectivity(self) -> None:
        """Worker to check AWS connectivity asynchronously."""
        checklist = self.query_one("#checklist", DynamicChecklist)

        # Check 1: AWS Credentials
        try:
            self.call_from_thread(
                checklist.update_check,
                "check-credentials",
                "checking",
                "Checking AWS credentials..."
            )

            # Try to create AWS client
            region = self.initial_region or "us-east-1"
            self.aws_client = AWSClient(region=region)

            # If we get here, credentials are configured
            self.call_from_thread(
                checklist.update_check,
                "check-credentials",
                "success",
                "AWS credentials configured"
            )

        except AWSCredentialsNotFoundError:
            self.call_from_thread(
                checklist.update_check,
                "check-credentials",
                "error",
                "AWS credentials not found. Run 'aws configure'"
            )
            self.call_from_thread(
                checklist.update_check,
                "check-connectivity",
                "error",
                "Skipped (no credentials)"
            )
            self.call_from_thread(
                checklist.update_check,
                "check-cost-explorer",
                "error",
                "Skipped (no credentials)"
            )
            return

        except AWSAuthenticationError as e:
            self.call_from_thread(
                checklist.update_check,
                "check-credentials",
                "error",
                f"Authentication failed: {str(e)[:40]}..."
            )
            self.call_from_thread(
                checklist.update_check,
                "check-connectivity",
                "error",
                "Skipped (auth failed)"
            )
            self.call_from_thread(
                checklist.update_check,
                "check-cost-explorer",
                "error",
                "Skipped (auth failed)"
            )
            return

        except Exception as e:
            self.call_from_thread(
                checklist.update_check,
                "check-credentials",
                "error",
                f"Error: {str(e)[:40]}..."
            )
            self.call_from_thread(
                checklist.update_check,
                "check-connectivity",
                "error",
                "Skipped (error)"
            )
            self.call_from_thread(
                checklist.update_check,
                "check-cost-explorer",
                "error",
                "Skipped (error)"
            )
            return

        # Check 2: AWS Connectivity
        try:
            self.call_from_thread(
                checklist.update_check,
                "check-connectivity",
                "checking",
                "Checking AWS connectivity..."
            )

            # Credentials were already validated in AWSClient init
            if self.aws_client and self.aws_client.credentials:
                account_id = self.aws_client.credentials.account_id
                self.call_from_thread(
                    checklist.update_check,
                    "check-connectivity",
                    "success",
                    f"Connected to AWS (Account: {account_id})"
                )
            else:
                self.call_from_thread(
                    checklist.update_check,
                    "check-connectivity",
                    "error",
                    "Failed to connect to AWS"
                )
                self.call_from_thread(
                    checklist.update_check,
                    "check-cost-explorer",
                    "error",
                    "Skipped (no connection)"
                )
                return

        except Exception as e:
            self.call_from_thread(
                checklist.update_check,
                "check-connectivity",
                "error",
                f"Connection error: {str(e)[:40]}..."
            )
            self.call_from_thread(
                checklist.update_check,
                "check-cost-explorer",
                "error",
                "Skipped (no connection)"
            )
            return

        # Check 3: Cost Explorer
        try:
            self.call_from_thread(
                checklist.update_check,
                "check-cost-explorer",
                "checking",
                "Checking Cost Explorer..."
            )

            # Try to make a simple Cost Explorer API call
            cost_explorer = CostExplorer(self.aws_client)
            from datetime import datetime, timedelta

            # Try to get cost data for the last day
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)

            # This will raise CostExplorerNotEnabledException if not enabled
            _ = cost_explorer.get_cost_and_usage(
                start_date=start_date,
                end_date=end_date,
                granularity="DAILY"
            )

            self.call_from_thread(
                checklist.update_check,
                "check-cost-explorer",
                "success",
                "Cost Explorer enabled and accessible"
            )

            # Mark as ready
            self.aws_ready = True
            self.call_from_thread(
                self.notify,
                "[green]✓[/green] All checks passed! Ready to explore costs."
            )

        except CostExplorerNotEnabledException:
            self.call_from_thread(
                checklist.update_check,
                "check-cost-explorer",
                "warning",
                "Cost Explorer not enabled. Enable in AWS Billing Console"
            )
            self.call_from_thread(
                self.notify,
                "[yellow]⚠[/yellow] Cost Explorer not enabled. Some features limited."
            )

        except Exception as e:
            error_msg = str(e)
            if "AccessDeniedException" in error_msg:
                self.call_from_thread(
                    checklist.update_check,
                    "check-cost-explorer",
                    "error",
                    "Access denied. Check IAM permissions for Cost Explorer"
                )
            else:
                self.call_from_thread(
                    checklist.update_check,
                    "check-cost-explorer",
                    "error",
                    f"Error: {error_msg[:40]}..."
                )
            self.call_from_thread(
                self.notify,
                "[yellow]⚠[/yellow] Cost Explorer check failed. Some features may not work."
            )

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle service selection."""
        if event.select.id == "service-select":
            service = event.value

            if service == "ec2":
                # Import here to avoid circular imports
                from costdrill.tui.ec2_screen import EC2ListScreen

                # Determine region (use initial_region or default)
                region = self.initial_region or "us-east-1"
                self.push_screen(EC2ListScreen(region=region))
            else:
                self.notify(f"[yellow]{service.upper()} support coming soon![/yellow]")

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.dark = not self.dark


if __name__ == "__main__":
    app = CostDrillApp()
    app.run()
