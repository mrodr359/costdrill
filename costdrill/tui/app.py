"""
Main Textual application for CostDrill TUI.
"""

from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Footer, Header, Static, Select


class WelcomeScreen(Static):
    """Welcome screen widget."""

    def compose(self) -> ComposeResult:
        yield Static(
            """
[bold cyan]Welcome to CostDrill![/bold cyan]

Interactive AWS cost exploration tool.

[yellow]Getting Started:[/yellow]
1. Select an AWS service from the dropdown
2. Choose specific resources or view aggregates
3. Drill down into cost breakdowns
4. Export reports as needed

[dim]Press 'q' to quit at any time[/dim]
            """,
            classes="welcome-text"
        )


class ServiceSelector(Container):
    """Widget for selecting AWS services."""

    def compose(self) -> ComposeResult:
        services = [
            ("EC2 (Elastic Compute Cloud)", "ec2"),
            ("S3 (Simple Storage Service)", "s3"),
            ("RDS (Relational Database Service)", "rds"),
            ("Lambda", "lambda"),
            ("CloudFront", "cloudfront"),
        ]

        yield Static("[bold]Select AWS Service:[/bold]")
        yield Select(
            options=[(label, value) for label, value in services],
            prompt="Choose a service",
            id="service-select"
        )


class CostDrillApp(App):
    """Main CostDrill TUI application."""

    CSS = """
    Screen {
        background: $surface;
    }

    .welcome-text {
        padding: 2 4;
        background: $panel;
        border: solid $primary;
        margin: 1 2;
    }

    ServiceSelector {
        padding: 1 4;
        margin: 1 2;
    }

    #service-select {
        margin: 1 0;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Toggle Dark Mode"),
    ]

    def __init__(
        self,
        initial_service: Optional[str] = None,
        initial_region: Optional[str] = None
    ):
        super().__init__()
        self.initial_service = initial_service
        self.initial_region = initial_region
        self.title = "CostDrill - AWS Cost Explorer"
        self.sub_title = "Interactive cost analysis"

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Vertical(
            WelcomeScreen(),
            ServiceSelector(),
        )
        yield Footer()

    def on_mount(self) -> None:
        """Handle app mount."""
        if self.initial_service:
            self.notify(f"Starting with service: {self.initial_service}")

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle service selection."""
        if event.select.id == "service-select":
            service = event.value
            self.notify(f"Selected service: {service}")
            # TODO: Navigate to service-specific view
            # TODO: Fetch and display cost data

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.dark = not self.dark


if __name__ == "__main__":
    app = CostDrillApp()
    app.run()
