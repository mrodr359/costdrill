"""
EC2 instance list and detail screens.
"""

from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Static, LoadingIndicator
from textual.worker import Worker, WorkerState

from costdrill.core.aws_client import AWSClient
from costdrill.core.cached_ec2_aggregator import CachedEC2Aggregator
from costdrill.core.ec2_models import EC2InstanceWithCosts, RegionalEC2Summary
from costdrill.core.exceptions import (
    AWSAuthenticationError,
    CostExplorerNotEnabledException,
)


class EC2ListScreen(Screen):
    """Screen showing all EC2 instances in a region."""

    CSS = """
    EC2ListScreen {
        background: #11121f;
        color: #f8f9fd;
    }

    .header-panel {
        background: #1f2a50;
        padding: 1 2;
        dock: top;
        height: auto;
    }

    .header-title {
        text-style: bold;
        color: #8be9fd;
    }

    .stats-container {
        layout: horizontal;
        height: auto;
        padding: 1 2;
    }

    .stat-card {
        width: 1fr;
        background: #23243a;
        border: solid #44475a;
        padding: 1 2;
        margin: 0 1;
    }

    .stat-value {
        text-style: bold;
        color: #8be9fd;
        text-align: center;
    }

    .stat-label {
        color: #7f85a3;
        text-align: center;
    }

    .table-container {
        height: 1fr;
        padding: 0 2;
    }

    DataTable {
        background: #1b1d2e;
        color: #f8f9fd;
    }

    .loading-container {
        align: center middle;
        height: 100%;
    }

    .error-container {
        align: center middle;
        background: #2d1f1f;
        border: solid #ff5555;
        padding: 2 4;
        margin: 2;
    }

    .error-title {
        text-style: bold;
        color: #ff5555;
        text-align: center;
    }

    .error-message {
        color: #ff8888;
        text-align: center;
        margin-top: 1;
    }

    .action-buttons {
        layout: horizontal;
        height: auto;
        dock: bottom;
        padding: 1 2;
        background: #1f2a50;
    }

    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("q", "app.pop_screen", "Back"),
        ("r", "refresh", "Refresh"),
    ]

    def __init__(self, region: str = "us-east-1"):
        super().__init__()
        self.region = region
        self.summary: Optional[RegionalEC2Summary] = None
        self.error_message: Optional[str] = None

    def compose(self) -> ComposeResult:
        """Compose the screen widgets."""
        yield Header()

        # Header with title
        with Container(classes="header-panel"):
            yield Static(f"[b]EC2 Instances - {self.region}[/b]", classes="header-title")

        # Loading state (will be hidden once data loads)
        with Container(classes="loading-container", id="loading"):
            yield LoadingIndicator()
            yield Static("Loading EC2 instances and costs...", classes="stat-label")

        # Error state (hidden by default)
        with Container(classes="error-container", id="error"):
            yield Static("⚠️  Error Loading Data", classes="error-title")
            yield Static("", id="error-text", classes="error-message")
            yield Button("Retry", id="retry-button", variant="primary")

        # Stats panel (hidden until data loads)
        with Container(classes="stats-container", id="stats"):
            with Vertical(classes="stat-card"):
                yield Static("0", id="total-instances", classes="stat-value")
                yield Static("Total Instances", classes="stat-label")

            with Vertical(classes="stat-card"):
                yield Static("0", id="running-instances", classes="stat-value")
                yield Static("Running", classes="stat-label")

            with Vertical(classes="stat-card"):
                yield Static("0", id="stopped-instances", classes="stat-value")
                yield Static("Stopped", classes="stat-label")

            with Vertical(classes="stat-card"):
                yield Static("$0.00", id="total-cost", classes="stat-value")
                yield Static("Total Cost (30d)", classes="stat-label")

        # Data table (hidden until data loads)
        with Container(classes="table-container", id="table-container"):
            yield DataTable(id="instances-table")

        # Action buttons
        with Container(classes="action-buttons"):
            yield Button("Refresh", id="refresh-button", variant="primary")
            yield Button("Back", id="back-button")

        yield Footer()

    def on_mount(self) -> None:
        """Handle screen mount."""
        # Hide stats and table initially
        self.query_one("#stats").display = False
        self.query_one("#table-container").display = False
        self.query_one("#error").display = False

        # Setup table
        table = self.query_one("#instances-table", DataTable)
        table.add_columns("Name", "Instance ID", "Type", "State", "Cost (30d)", "Daily Cost")
        table.cursor_type = "row"

        # Start loading data
        self.load_instances()

    def load_instances(self) -> None:
        """Load EC2 instances with costs."""
        self.run_worker(self._fetch_instances, exclusive=True, name="fetch_instances")

    async def _fetch_instances(self) -> None:
        """Worker to fetch instances from AWS."""
        try:
            # Initialize AWS client and aggregator
            aws_client = AWSClient(region=self.region)
            ec2_aggregator = CachedEC2Aggregator(
                aws_client=aws_client,
                region=self.region,
                enable_cache=True,
            )

            # Fetch instances
            self.summary = ec2_aggregator.get_all_instances_with_costs(days=30)

            # Update UI on main thread
            self.call_from_thread(self._update_ui)

        except AWSAuthenticationError as e:
            self.error_message = f"Authentication failed: {str(e)}\nPlease check your AWS credentials."
            self.call_from_thread(self._show_error)

        except CostExplorerNotEnabledException as e:
            self.error_message = f"{str(e)}\nPlease enable Cost Explorer in AWS Billing console."
            self.call_from_thread(self._show_error)

        except Exception as e:
            self.error_message = f"Error loading instances: {str(e)}"
            self.call_from_thread(self._show_error)

    def _update_ui(self) -> None:
        """Update UI with loaded data."""
        if not self.summary:
            return

        # Hide loading, show stats and table
        self.query_one("#loading").display = False
        self.query_one("#stats").display = True
        self.query_one("#table-container").display = True

        # Update stats
        self.query_one("#total-instances", Static).update(str(self.summary.instance_count))
        self.query_one("#running-instances", Static).update(str(self.summary.running_instance_count))
        self.query_one("#stopped-instances", Static).update(str(self.summary.stopped_instance_count))
        self.query_one("#total-cost", Static).update(f"${self.summary.total_cost.amount:.2f}")

        # Populate table
        table = self.query_one("#instances-table", DataTable)
        table.clear()

        for inst in self.summary.instances:
            # Color code state
            state = inst.instance.state.value
            if state == "running":
                state_display = f"[green]{state}[/]"
            elif state == "stopped":
                state_display = f"[red]{state}[/]"
            else:
                state_display = f"[yellow]{state}[/]"

            table.add_row(
                inst.instance.name,
                inst.instance.instance_id,
                inst.instance.instance_type,
                state_display,
                f"${inst.total_cost.amount:.2f}",
                f"${inst.daily_cost:.2f}",
            )

        self.notify(f"Loaded {self.summary.instance_count} instances")

    def _show_error(self) -> None:
        """Show error message."""
        self.query_one("#loading").display = False
        self.query_one("#stats").display = False
        self.query_one("#table-container").display = False
        self.query_one("#error").display = True
        self.query_one("#error-text", Static).update(self.error_message or "Unknown error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "refresh-button" or event.button.id == "retry-button":
            # Show loading and refresh
            self.query_one("#loading").display = True
            self.query_one("#stats").display = False
            self.query_one("#table-container").display = False
            self.query_one("#error").display = False
            self.load_instances()
        elif event.button.id == "back-button":
            self.app.pop_screen()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection to show instance details."""
        if not self.summary:
            return

        # Get the instance from the selected row
        row_index = event.cursor_row
        if row_index < len(self.summary.instances):
            instance_with_costs = self.summary.instances[row_index]
            # Push detail screen
            self.app.push_screen(EC2DetailScreen(instance_with_costs, self.region))

    def action_refresh(self) -> None:
        """Refresh the instance list."""
        self.query_one("#loading").display = True
        self.query_one("#stats").display = False
        self.query_one("#table-container").display = False
        self.query_one("#error").display = False
        self.load_instances()


class EC2DetailScreen(Screen):
    """Screen showing detailed information about a specific EC2 instance."""

    CSS = """
    EC2DetailScreen {
        background: #11121f;
        color: #f8f9fd;
    }

    .detail-header {
        background: #1f2a50;
        padding: 1 2;
        dock: top;
        height: auto;
    }

    .detail-title {
        text-style: bold;
        color: #8be9fd;
    }

    .detail-subtitle {
        color: #7f85a3;
    }

    .content-scroll {
        height: 1fr;
    }

    .section {
        background: #1b1d2e;
        border: solid #3c3f58;
        padding: 2;
        margin: 1 2;
    }

    .section-title {
        text-style: bold;
        color: #bd93f9;
        margin-bottom: 1;
    }

    .info-row {
        margin: 0 0 0 2;
    }

    .cost-breakdown {
        layout: grid;
        grid-size: 2;
        grid-gutter: 1;
    }

    .cost-item {
        background: #23243a;
        padding: 1;
        border: solid #44475a;
    }

    .cost-label {
        color: #7f85a3;
    }

    .cost-value {
        text-style: bold;
        color: #8be9fd;
    }

    .cost-percent {
        color: #50fa7b;
    }

    .action-buttons {
        layout: horizontal;
        height: auto;
        dock: bottom;
        padding: 1 2;
        background: #1f2a50;
    }

    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("q", "app.pop_screen", "Back"),
    ]

    def __init__(self, instance_with_costs: EC2InstanceWithCosts, region: str):
        super().__init__()
        self.instance_with_costs = instance_with_costs
        self.region = region

    def compose(self) -> ComposeResult:
        """Compose the detail screen."""
        yield Header()

        instance = self.instance_with_costs.instance
        breakdown = self.instance_with_costs.cost_breakdown

        # Header
        with Container(classes="detail-header"):
            yield Static(f"[b]{instance.name}[/b]", classes="detail-title")
            yield Static(f"{instance.instance_id} • {instance.instance_type}", classes="detail-subtitle")

        # Scrollable content
        with VerticalScroll(classes="content-scroll"):
            # Instance info section
            with Container(classes="section"):
                yield Static("[b]Instance Information[/b]", classes="section-title")
                yield Static(f"State: [{self._get_state_color(instance.state.value)}]{instance.state.value}[/]", classes="info-row")
                yield Static(f"Region: {instance.region}", classes="info-row")
                yield Static(f"Availability Zone: {instance.availability_zone}", classes="info-row")
                yield Static(f"Platform: {instance.platform}", classes="info-row")
                yield Static(f"Launch Time: {instance.launch_time.strftime('%Y-%m-%d %H:%M:%S')}", classes="info-row")
                yield Static(f"Uptime: {instance.uptime_hours:.1f} hours", classes="info-row")
                if instance.vpc_id:
                    yield Static(f"VPC: {instance.vpc_id}", classes="info-row")
                if instance.private_ip:
                    yield Static(f"Private IP: {instance.private_ip}", classes="info-row")
                if instance.public_ip:
                    yield Static(f"Public IP: {instance.public_ip}", classes="info-row")

            # Cost summary section
            with Container(classes="section"):
                yield Static("[b]Cost Summary (30 days)[/b]", classes="section-title")
                yield Static(f"Total Cost: [#8be9fd][b]${breakdown.total_cost.amount:.2f}[/b][/]", classes="info-row")
                yield Static(f"Cost per Hour: ${breakdown.cost_per_hour:.4f}", classes="info-row")
                yield Static(f"Daily Cost: ${self.instance_with_costs.daily_cost:.2f}", classes="info-row")
                yield Static(f"Monthly Projection: ${self.instance_with_costs.monthly_projection:.2f}", classes="info-row")

            # Cost breakdown section
            with Container(classes="section"):
                yield Static("[b]Cost Breakdown[/b]", classes="section-title")
                with Container(classes="cost-breakdown"):
                    # Compute
                    with Container(classes="cost-item"):
                        yield Static("Compute", classes="cost-label")
                        yield Static(f"${breakdown.compute_cost.amount:.2f}", classes="cost-value")
                        yield Static(f"({breakdown.compute_percentage:.1f}%)", classes="cost-percent")

                    # Storage
                    with Container(classes="cost-item"):
                        yield Static("Storage (EBS)", classes="cost-label")
                        yield Static(f"${breakdown.storage_cost.amount:.2f}", classes="cost-value")
                        yield Static(f"({breakdown.storage_percentage:.1f}%)", classes="cost-percent")

                    # Data Transfer
                    with Container(classes="cost-item"):
                        yield Static("Data Transfer", classes="cost-label")
                        yield Static(f"${breakdown.data_transfer_cost.amount:.2f}", classes="cost-value")
                        yield Static(f"({breakdown.data_transfer_percentage:.1f}%)", classes="cost-percent")

                    # Snapshots
                    with Container(classes="cost-item"):
                        yield Static("Snapshots", classes="cost-label")
                        yield Static(f"${breakdown.snapshot_cost.amount:.2f}", classes="cost-value")

                    # Elastic IPs
                    with Container(classes="cost-item"):
                        yield Static("Elastic IPs", classes="cost-label")
                        yield Static(f"${breakdown.elastic_ip_cost.amount:.2f}", classes="cost-value")

                    # Other
                    with Container(classes="cost-item"):
                        yield Static("Other", classes="cost-label")
                        yield Static(f"${breakdown.other_costs.amount:.2f}", classes="cost-value")

            # EBS Volumes section
            if instance.ebs_volumes:
                with Container(classes="section"):
                    yield Static(f"[b]EBS Volumes ({len(instance.ebs_volumes)})[/b]", classes="section-title")
                    for vol in instance.ebs_volumes:
                        yield Static(f"• {vol.display_name} - {vol.device_name}", classes="info-row")

            # Tags section
            if instance.tags:
                with Container(classes="section"):
                    yield Static("[b]Tags[/b]", classes="section-title")
                    for key, value in instance.tags.items():
                        yield Static(f"{key}: {value}", classes="info-row")

        # Action buttons
        with Container(classes="action-buttons"):
            yield Button("Back", id="back-button", variant="primary")

        yield Footer()

    def _get_state_color(self, state: str) -> str:
        """Get color for instance state."""
        state_colors = {
            "running": "green",
            "stopped": "red",
            "stopping": "yellow",
            "pending": "yellow",
            "shutting-down": "yellow",
            "terminated": "red",
        }
        return state_colors.get(state, "white")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "back-button":
            self.app.pop_screen()
