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
[gradient(#8be9fd,#bd93f9)]COSTDRILL[/gradient]
[dim]AWS cost visibility without the console fatigue.[/dim]

[bold]Navigate[/bold] services, [bold]drill[/bold] into spend, and surface [bold magenta]savings signals[/bold magenta] in seconds.
            """,
            classes="hero-title",
        )
        yield Static(
            """\
[bold color=#8be9fd]Launch Checklist[/bold color=#8be9fd]
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
        yield Static(f"[bold color=#bd93f9]{self._title}[/bold color=#bd93f9]", classes="panel-heading")
        yield Static(self._body, classes="panel-body")


class ServiceSelector(Container):
    """Widget for selecting AWS services."""

    SERVICES = [
        ("EC2 — Elastic Compute Cloud", "ec2"),
        ("S3 — Simple Storage Service", "s3"),
        ("RDS — Relational Database Service", "rds"),
        ("Lambda — Serverless Functions", "lambda"),
        ("CloudFront — Global CDN", "cloudfront"),
    ]

    def compose(self) -> ComposeResult:
        yield Static("[bold color=#8be9fd]Choose a starting point[/bold color=#8be9fd]", classes="selector-heading")
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
            "[cyan]Break down[/cyan] compute vs storage vs transfer with a glance.",
            classes="tile",
        )
        yield AccentPanel(
            "Save Smart",
            "Surface [magenta]right-sizing[/magenta] opportunities before the bill hits.",
            classes="tile",
        )
        yield AccentPanel(
            "Share Wins",
            "Export [green]JSON[/green], [green]CSV[/green], or [green]Markdown[/green] reports instantly.",
            classes="tile",
        )


class CostDrillApp(App):
    """Main CostDrill TUI application."""

    CSS = """
    :root {
        --color-background-top: #11121f;
        --color-background-bottom: #1b1e2d;
        --color-panel: #23243a;
        --color-panel-border: #44475a;
        --color-accent: #bd93f9;
        --color-accent-strong: #ff79c6;
        --color-muted: #7f85a3;
        --color-text: #f8f9fd;
    }

    Screen {
        background: linear-gradient(140deg, var(--color-background-top), var(--color-background-bottom));
        color: var(--color-text);
    }

    Header, Footer {
        background: linear-gradient(90deg, #2d2143, #1f2a50);
        color: var(--color-text);
        border: none;
    }

    .main-layout {
        padding: 2 3;
        height: 100%;
        width: 100%;
    }

    HeroBanner {
        padding: 2 3;
        border: solid 1px color(var(--color-panel-border) 60%);
        background: color(var(--color-panel) 90%);
        border-left: solid 3px var(--color-accent);
        margin-bottom: 1;
        box-shadow: 0 1 4 0 rgba(0, 0, 0, 0.35);
    }

    .hero-title {
        text-style: bold;
        line-height: 1.4;
    }

    .hero-checklist {
        margin-top: 1;
        color: var(--color-muted);
    }

    .content {
        height: 1fr;
        gap: 2;
    }

    .left-column, .right-column {
        background: color(var(--color-panel) 95%);
        border: solid 1px color(var(--color-panel-border) 70%);
        border-radius: 1;
        padding: 2 3;
        box-shadow: 0 2 6 0 rgba(0, 0, 0, 0.25);
    }

    .left-column {
        width: 2fr;
    }

    .right-column {
        width: 3fr;
    }

    .selector-heading {
        color: var(--color-accent);
        text-style: bold;
    }

    .selector-blurb {
        margin-top: 1;
        color: var(--color-muted);
    }

    #service-select {
        margin-top: 1;
        height: 3;
        border: solid 1px color(var(--color-panel-border) 70%);
        background: #1b1d2e;
        color: var(--color-text);
        selection-background: var(--color-accent-strong);
        selection-color: #111;
    }

    .selector-hint {
        margin-top: 1;
        color: color(var(--color-muted) 70%);
    }

    QuickInsights {
        layout: horizontal;
        gap: 1;
    }

    AccentPanel {
        layout: vertical;
        gap: 1;
    }

    .tile {
        width: 1fr;
        height: auto;
        background: #1a1c2d;
        border: solid 1px color(var(--color-panel-border) 60%);
        border-top: solid 2px var(--color-accent-strong);
        padding: 1 2;
        color: color(var(--color-text) 90%);
    }

    .accent-panel .panel-heading {
        color: var(--color-accent);
        text-style: bold;
        margin-bottom: 1;
    }

    .accent-panel .panel-body {
        color: color(var(--color-text) 85%);
    }

    .insight-footer {
        margin-top: 2;
        color: color(var(--color-muted) 70%);
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
                        "Need guidance on FinOps maturity? [bold link=#]Open the playbook[/bold] "
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
            self.notify(f"Selected service: {service}")
            # TODO: Navigate to service-specific view
            # TODO: Fetch and display cost data

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.dark = not self.dark


if __name__ == "__main__":
    app = CostDrillApp()
    app.run()
