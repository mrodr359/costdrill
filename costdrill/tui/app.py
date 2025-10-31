"""
Main Textual application for the CostDrill TUI launch experience.
"""

from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, Static, Select


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
        yield Static(
            """\
[#8be9fd][b]Launch Checklist[/b][/]
[green]•[/green] AWS credentials configured
[green]•[/green] Cost Explorer enabled
[green]•[/green] Choose a service to begin your journey
            """,
            classes="hero-checklist",
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

    .hero-checklist {
        margin-top: 1;
        color: #7f85a3;
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

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Container(classes="main-layout"):
            yield HeroBanner()
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
        if self.initial_service:
            self.notify(f"Starting with service: {self.initial_service}")

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
