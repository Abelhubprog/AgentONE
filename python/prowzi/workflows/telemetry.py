"""Real-time telemetry and progress monitoring for Prowzi workflows."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StageMetrics:
    """Metrics for a single stage execution."""

    stage: str
    status: str  # started, completed, failed, skipped, retrying
    attempt: int
    duration_seconds: float
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class WorkflowMetrics:
    """Aggregated metrics for entire workflow execution."""

    session_id: str
    prompt: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_duration_seconds: float = 0.0
    stages: List[StageMetrics] = field(default_factory=list)
    total_retries: int = 0
    failed_stages: List[str] = field(default_factory=list)
    success: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class TelemetryCollector:
    """Collects and persists workflow telemetry data."""

    def __init__(self, output_dir: Path, enabled: bool = True) -> None:
        self.output_dir = output_dir
        self.enabled = enabled
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.active_sessions: Dict[str, WorkflowMetrics] = {}

    def start_session(self, session_id: str, prompt: str) -> None:
        """Start tracking a new workflow session."""
        if not self.enabled:
            return

        metrics = WorkflowMetrics(
            session_id=session_id,
            prompt=prompt[:500],
            started_at=datetime.now(timezone.utc),
        )
        self.active_sessions[session_id] = metrics
        logger.debug("Telemetry session started: %s", session_id)

    def record_stage_event(
        self,
        session_id: str,
        stage: str,
        status: str,
        attempt: int = 1,
        duration: float = 0.0,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        """Record a stage execution event."""
        if not self.enabled:
            return

        metrics = self.active_sessions.get(session_id)
        if not metrics:
            logger.warning("No active session found: %s", session_id)
            return

        stage_metric = StageMetrics(
            stage=stage,
            status=status,
            attempt=attempt,
            duration_seconds=duration,
            timestamp=datetime.now(timezone.utc),
            details=details or {},
            error=error,
        )

        metrics.stages.append(stage_metric)

        if status == "retrying":
            metrics.total_retries += 1
        elif status == "failed":
            if stage not in metrics.failed_stages:
                metrics.failed_stages.append(stage)

        self._persist_session(session_id)

    def complete_session(
        self,
        session_id: str,
        success: bool,
        total_duration: float,
        final_metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mark a session as completed."""
        if not self.enabled:
            return

        metrics = self.active_sessions.get(session_id)
        if not metrics:
            logger.warning("No active session found: %s", session_id)
            return

        metrics.completed_at = datetime.now(timezone.utc)
        metrics.total_duration_seconds = total_duration
        metrics.success = success
        if final_metadata:
            metrics.metadata.update(final_metadata)

        self._persist_session(session_id)
        logger.info(
            "Telemetry session completed: %s (success: %s, retries: %d)",
            session_id,
            success,
            metrics.total_retries,
        )

    def get_session_metrics(self, session_id: str) -> Optional[WorkflowMetrics]:
        """Retrieve metrics for a session."""
        return self.active_sessions.get(session_id)

    def _persist_session(self, session_id: str) -> None:
        """Persist session metrics to disk."""
        metrics = self.active_sessions.get(session_id)
        if not metrics:
            return

        try:
            telemetry_path = self.output_dir / f"telemetry_{session_id}.json"
            data = {
                "session_id": metrics.session_id,
                "prompt": metrics.prompt,
                "started_at": metrics.started_at.isoformat(),
                "completed_at": metrics.completed_at.isoformat() if metrics.completed_at else None,
                "total_duration_seconds": metrics.total_duration_seconds,
                "total_retries": metrics.total_retries,
                "failed_stages": metrics.failed_stages,
                "success": metrics.success,
                "metadata": metrics.metadata,
                "stages": [
                    {
                        "stage": s.stage,
                        "status": s.status,
                        "attempt": s.attempt,
                        "duration_seconds": s.duration_seconds,
                        "timestamp": s.timestamp.isoformat(),
                        "details": s.details,
                        "error": s.error,
                    }
                    for s in metrics.stages
                ],
            }

            with open(telemetry_path, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to persist telemetry for session %s: %s", session_id, exc)

    def load_session(self, session_id: str) -> Optional[WorkflowMetrics]:
        """Load persisted session metrics."""
        if not self.enabled:
            return None

        try:
            telemetry_path = self.output_dir / f"telemetry_{session_id}.json"
            if not telemetry_path.exists():
                return None

            with open(telemetry_path) as f:
                data = json.load(f)

            stages = [
                StageMetrics(
                    stage=s["stage"],
                    status=s["status"],
                    attempt=s["attempt"],
                    duration_seconds=s["duration_seconds"],
                    timestamp=datetime.fromisoformat(s["timestamp"]),
                    details=s.get("details", {}),
                    error=s.get("error"),
                )
                for s in data.get("stages", [])
            ]

            metrics = WorkflowMetrics(
                session_id=data["session_id"],
                prompt=data["prompt"],
                started_at=datetime.fromisoformat(data["started_at"]),
                completed_at=datetime.fromisoformat(data["completed_at"])
                if data.get("completed_at")
                else None,
                total_duration_seconds=data["total_duration_seconds"],
                stages=stages,
                total_retries=data["total_retries"],
                failed_stages=data["failed_stages"],
                success=data["success"],
                metadata=data.get("metadata", {}),
            )

            self.active_sessions[session_id] = metrics
            return metrics

        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to load telemetry for session %s: %s", session_id, exc)
            return None

    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent workflow sessions."""
        sessions: List[Dict[str, Any]] = []

        for telemetry_file in sorted(
            self.output_dir.glob("telemetry_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:limit]:
            try:
                with open(telemetry_file) as f:
                    data = json.load(f)
                sessions.append(
                    {
                        "session_id": data["session_id"],
                        "prompt": data["prompt"][:100],
                        "started_at": data["started_at"],
                        "success": data["success"],
                        "total_retries": data["total_retries"],
                        "stages_completed": len([s for s in data.get("stages", []) if s["status"] == "completed"]),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to read telemetry file %s: %s", telemetry_file, exc)

        return sessions
