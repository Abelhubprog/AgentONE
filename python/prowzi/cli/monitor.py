"""CLI monitoring interface for Prowzi workflows with real-time telemetry."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from prowzi.workflows.telemetry import TelemetryCollector

logger = logging.getLogger(__name__)


@dataclass
class StageProgress:
    """Track progress for a single stage."""

    name: str
    status: str  # pending, running, completed, failed, skipped
    attempt: int
    duration: float
    error: Optional[str] = None


class WorkflowMonitor:
    """Real-time CLI monitor for workflow execution with rich terminal UI."""

    def __init__(self, telemetry_dir: Path, session_id: str) -> None:
        self.telemetry_dir = telemetry_dir
        self.session_id = session_id
        self.console = Console()
        self.telemetry = TelemetryCollector(output_dir=telemetry_dir)
        self.stages: Dict[str, StageProgress] = {}
        self.workflow_start: Optional[datetime] = None
        self.workflow_end: Optional[datetime] = None

    def create_dashboard(self) -> Table:
        """Create rich terminal dashboard for workflow monitoring."""
        metrics = self.telemetry.get_session_metrics(self.session_id)
        if not metrics:
            return Table(title="Workflow Monitor - No Active Session")

        # Main table
        table = Table(title=f"Prowzi Workflow Monitor - Session: {self.session_id[:8]}...", expand=True)
        table.add_column("Stage", style="cyan", no_wrap=True)
        table.add_column("Status", style="bold")
        table.add_column("Attempt", justify="center")
        table.add_column("Duration", justify="right")
        table.add_column("Details")

        for stage_metric in metrics.stages:
            status_style = {
                "started": "yellow",
                "completed": "green",
                "failed": "red",
                "skipped": "dim",
                "retrying": "magenta",
            }.get(stage_metric.status, "white")

            status_text = Text(stage_metric.status.upper(), style=status_style)

            details = ""
            if stage_metric.error:
                details = f"Error: {stage_metric.error[:50]}"
            elif stage_metric.details:
                # Show key metrics from details
                if "score" in stage_metric.details:
                    details = f"Score: {stage_metric.details['score']:.2f}"
                elif "sources_count" in stage_metric.details:
                    details = f"Sources: {stage_metric.details['sources_count']}"

            table.add_row(
                stage_metric.stage,
                status_text,
                str(stage_metric.attempt),
                f"{stage_metric.duration_seconds:.2f}s",
                details,
            )

        return table

    def create_summary_panel(self) -> Panel:
        """Create summary panel with aggregate stats."""
        metrics = self.telemetry.get_session_metrics(self.session_id)
        if not metrics:
            return Panel("No metrics available")

        total_duration = metrics.total_duration_seconds
        completed = len([s for s in metrics.stages if s.status == "completed"])
        total_stages = len([s for s in metrics.stages if s.status != "skipped"])
        total_retries = metrics.total_retries

        summary = f"""
[bold cyan]Workflow Summary[/bold cyan]

[yellow]Total Duration:[/yellow] {total_duration:.2f}s
[yellow]Stages:[/yellow] {completed}/{total_stages} completed
[yellow]Total Retries:[/yellow] {total_retries}
[yellow]Success:[/yellow] {"✓" if metrics.success else "✗"}
        """

        return Panel(summary.strip(), title="Summary", border_style="green" if metrics.success else "red")

    async def monitor_live(self, refresh_rate: float = 0.5) -> None:
        """Live monitoring with auto-refresh."""
        with Live(self.create_dashboard(), console=self.console, refresh_per_second=2) as live:
            while True:
                metrics = self.telemetry.get_session_metrics(self.session_id)
                if metrics and metrics.completed_at:
                    # Workflow completed
                    live.update(self.create_dashboard())
                    break

                live.update(self.create_dashboard())
                await asyncio.sleep(refresh_rate)

        # Show final summary
        self.console.print("\n")
        self.console.print(self.create_summary_panel())

    def display_snapshot(self) -> None:
        """Display single snapshot of current state."""
        self.console.print(self.create_dashboard())
        self.console.print("\n")
        self.console.print(self.create_summary_panel())


class ProgressListener:
    """Progress callback that updates telemetry in real-time."""

    def __init__(self, telemetry: TelemetryCollector, session_id: str) -> None:
        self.telemetry = telemetry
        self.session_id = session_id
        self.stage_starts: Dict[str, float] = {}

    async def __call__(self, stage: str, payload: Dict[str, Any]) -> None:
        """Handle progress events."""
        import time

        if stage.endswith("_start"):
            stage_name = stage.replace("_start", "")
            self.stage_starts[stage_name] = time.perf_counter()
            self.telemetry.record_stage_event(
                session_id=self.session_id, stage=stage_name, status="started", attempt=payload.get("attempt", 1)
            )
        elif stage.endswith("_retry"):
            stage_name = stage.replace("_retry", "")
            duration = time.perf_counter() - self.stage_starts.get(stage_name, time.perf_counter())
            self.telemetry.record_stage_event(
                session_id=self.session_id,
                stage=stage_name,
                status="retrying",
                attempt=payload.get("attempt", 1),
                duration=duration,
                error=payload.get("error"),
            )
        elif stage.endswith("_skipped"):
            stage_name = stage.replace("_skipped", "")
            self.telemetry.record_stage_event(
                session_id=self.session_id, stage=stage_name, status="skipped", attempt=1, duration=0.0
            )
        else:
            # Stage completed
            duration = time.perf_counter() - self.stage_starts.get(stage, time.perf_counter())
            self.telemetry.record_stage_event(
                session_id=self.session_id,
                stage=stage,
                status="completed",
                attempt=payload.get("attempt", 1),
                duration=duration,
                details=payload,
            )


def list_sessions(telemetry_dir: Path, limit: int = 20) -> None:
    """List recent workflow sessions."""
    console = Console()
    telemetry = TelemetryCollector(output_dir=telemetry_dir)

    sessions = telemetry.list_sessions(limit=limit)
    if not sessions:
        console.print("[yellow]No workflow sessions found[/yellow]")
        return

    table = Table(title="Recent Workflow Sessions")
    table.add_column("Session ID", style="cyan")
    table.add_column("Prompt", style="white")
    table.add_column("Started", style="dim")
    table.add_column("Status", style="bold")
    table.add_column("Retries", justify="center")
    table.add_column("Stages", justify="center")

    for session in sessions:
        status_style = "green" if session["success"] else "red"
        status = Text("✓" if session["success"] else "✗", style=status_style)

        table.add_row(
            session["session_id"][:12],
            session["prompt"],
            session["started_at"],
            status,
            str(session["total_retries"]),
            str(session["stages_completed"]),
        )

    console.print(table)


def show_session(telemetry_dir: Path, session_id: str) -> None:
    """Show detailed view of a specific session."""
    monitor = WorkflowMonitor(telemetry_dir=telemetry_dir, session_id=session_id)
    monitor.display_snapshot()


async def monitor_session_live(telemetry_dir: Path, session_id: str) -> None:
    """Monitor a session with live updates."""
    monitor = WorkflowMonitor(telemetry_dir=telemetry_dir, session_id=session_id)
    await monitor.monitor_live()
