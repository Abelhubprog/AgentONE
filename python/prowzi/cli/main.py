"""Main CLI entry point for Prowzi workflow management."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from prowzi.cli.monitor import list_sessions, monitor_session_live, show_session
from prowzi.config import ProwziConfig, get_config
from prowzi.workflows import ProwziOrchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_telemetry_dir(config: Optional[ProwziConfig] = None) -> Path:
    """Get telemetry directory from config."""
    cfg = config or get_config()
    return cfg.checkpoint_dir / "telemetry"


async def run_workflow_command(args: argparse.Namespace) -> None:
    """Run a new workflow with monitoring."""
    config = get_config()
    config.enable_checkpointing = args.enable_checkpoints
    config.enable_telemetry = True

    orchestrator = ProwziOrchestrator(config=config)

    logger.info("Starting workflow for prompt: %s", args.prompt[:100])

    result = await orchestrator.run_research(
        prompt=args.prompt,
        document_paths=[Path(p) for p in args.documents] if args.documents else None,
        max_results_per_query=args.max_results,
        max_sections=args.max_sections,
    )

    logger.info("Workflow completed successfully")
    logger.info("Session ID: %s", result.metadata.get("session_id"))
    logger.info("Duration: %.2fs", result.metadata["workflow_duration_seconds"])
    logger.info("Total retries: %d", result.metadata.get("total_retries", 0))
    logger.info("Final evaluation score: %.2f", result.evaluation.total_score)


async def resume_workflow_command(args: argparse.Namespace) -> None:
    """Resume a workflow from checkpoint."""
    config = get_config()
    config.enable_checkpointing = True
    config.enable_telemetry = True

    orchestrator = ProwziOrchestrator(config=config)

    logger.info("Resuming workflow from checkpoint: %s", args.checkpoint_id)

    result = await orchestrator.resume_from_checkpoint(checkpoint_id=args.checkpoint_id)

    logger.info("Workflow resumed and completed successfully")
    logger.info("Session ID: %s", result.metadata.get("session_id"))
    logger.info("Duration: %.2fs", result.metadata["workflow_duration_seconds"])
    logger.info("Final evaluation score: %.2f", result.evaluation.total_score)


def list_sessions_command(args: argparse.Namespace) -> None:
    """List recent workflow sessions."""
    telemetry_dir = get_telemetry_dir()
    list_sessions(telemetry_dir=telemetry_dir, limit=args.limit)


def show_session_command(args: argparse.Namespace) -> None:
    """Show details for a specific session."""
    telemetry_dir = get_telemetry_dir()
    show_session(telemetry_dir=telemetry_dir, session_id=args.session_id)


async def monitor_command(args: argparse.Namespace) -> None:
    """Monitor a workflow session in real-time."""
    telemetry_dir = get_telemetry_dir()
    await monitor_session_live(telemetry_dir=telemetry_dir, session_id=args.session_id)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Prowzi Workflow CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run workflow
    run_parser = subparsers.add_parser("run", help="Run a new workflow")
    run_parser.add_argument("prompt", type=str, help="Research prompt")
    run_parser.add_argument("--documents", "-d", nargs="+", help="Optional document paths")
    run_parser.add_argument("--max-results", type=int, default=12, help="Max results per search query")
    run_parser.add_argument("--max-sections", type=int, default=8, help="Max sections in draft")
    run_parser.add_argument("--enable-checkpoints", action="store_true", help="Enable checkpointing")

    # Resume workflow
    resume_parser = subparsers.add_parser("resume", help="Resume workflow from checkpoint")
    resume_parser.add_argument("checkpoint_id", type=str, help="Checkpoint ID to resume from")

    # List sessions
    list_parser = subparsers.add_parser("sessions", help="List recent workflow sessions")
    list_parser.add_argument("--limit", type=int, default=20, help="Number of sessions to show")

    # Show session
    show_parser = subparsers.add_parser("show", help="Show details for a specific session")
    show_parser.add_argument("session_id", type=str, help="Session ID to display")

    # Monitor session
    monitor_parser = subparsers.add_parser("monitor", help="Monitor a workflow session in real-time")
    monitor_parser.add_argument("session_id", type=str, help="Session ID to monitor")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "run":
        asyncio.run(run_workflow_command(args))
    elif args.command == "resume":
        asyncio.run(resume_workflow_command(args))
    elif args.command == "sessions":
        list_sessions_command(args)
    elif args.command == "show":
        show_session_command(args)
    elif args.command == "monitor":
        asyncio.run(monitor_command(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
