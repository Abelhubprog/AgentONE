"""Checkpoint management for workflow resumability."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from prowzi.agents.evaluation_agent import EvaluationAgentResult
from prowzi.agents.intent_agent import IntentAnalysis
from prowzi.agents.planning_agent import ResearchPlan
from prowzi.agents.search_agent import SearchAgentResult
from prowzi.agents.turnitin_agent import TurnitinAgentResult
from prowzi.agents.verification_agent import VerificationAgentResult
from prowzi.agents.writing_agent import WritingAgentResult

logger = logging.getLogger(__name__)


@dataclass
class CheckpointMetadata:
    """Metadata about a checkpoint."""

    checkpoint_id: str
    session_id: str
    created_at: datetime
    stage: str
    prompt: str
    stage_metrics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowCheckpoint:
    """Complete workflow state snapshot."""

    metadata: CheckpointMetadata
    intent: Optional[IntentAnalysis] = None
    plan: Optional[ResearchPlan] = None
    search: Optional[SearchAgentResult] = None
    verification: Optional[VerificationAgentResult] = None
    draft: Optional[WritingAgentResult] = None
    evaluation: Optional[EvaluationAgentResult] = None
    initial_evaluation: Optional[EvaluationAgentResult] = None
    turnitin: Optional[TurnitinAgentResult] = None
    stage_metrics: Dict[str, Any] = field(default_factory=dict)


class CheckpointManager:
    """Manages workflow checkpoints for resumability."""

    def __init__(self, checkpoint_dir: Path, enabled: bool = True) -> None:
        self.checkpoint_dir = checkpoint_dir
        self.enabled = enabled
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(
        self,
        session_id: str,
        stage: str,
        prompt: str,
        context: Dict[str, Any],
        stage_metrics: Dict[str, Any],
    ) -> str:
        """Save a workflow checkpoint."""
        if not self.enabled:
            logger.debug("Checkpointing disabled; skipping save.")
            return ""

        checkpoint_id = self._generate_checkpoint_id(session_id, stage)
        checkpoint_path = self.checkpoint_dir / f"{checkpoint_id}.pkl"
        metadata_path = self.checkpoint_dir / f"{checkpoint_id}.json"

        checkpoint_meta = CheckpointMetadata(
            checkpoint_id=checkpoint_id,
            session_id=session_id,
            created_at=datetime.now(timezone.utc),
            stage=stage,
            prompt=prompt[:500],
            stage_metrics=stage_metrics,
        )

        checkpoint = WorkflowCheckpoint(
            metadata=checkpoint_meta,
            intent=context.get("intent"),
            plan=context.get("plan"),
            search=context.get("search"),
            verification=context.get("verification"),
            draft=context.get("draft"),
            evaluation=context.get("evaluation"),
            initial_evaluation=context.get("initial_evaluation"),
            turnitin=context.get("turnitin"),
            stage_metrics=context.get("stage_metrics", {}),
        )

        try:
            # SECURITY: Use JSON instead of pickle to prevent arbitrary code execution
            # Convert dataclasses to dict for JSON serialization
            checkpoint_dict = {
                "intent": checkpoint.intent.__dict__ if hasattr(checkpoint.intent, '__dict__') else checkpoint.intent,
                "plan": checkpoint.plan.__dict__ if hasattr(checkpoint.plan, '__dict__') else checkpoint.plan,
                "search_results": checkpoint.search_results,
                "verification": checkpoint.verification.__dict__ if hasattr(checkpoint.verification, '__dict__') else checkpoint.verification,
                "draft": checkpoint.draft.__dict__ if hasattr(checkpoint.draft, '__dict__') else checkpoint.draft,
                "initial_evaluation": checkpoint.initial_evaluation.__dict__ if hasattr(checkpoint.initial_evaluation, '__dict__') else checkpoint.initial_evaluation,
                "turnitin": checkpoint.turnitin,
                "stage_metrics": checkpoint.stage_metrics,
            }

            with open(checkpoint_path, "w", encoding="utf-8") as f:
                json.dump(checkpoint_dict, f, indent=2)

            metadata_dict = {
                "checkpoint_id": checkpoint_meta.checkpoint_id,
                "session_id": checkpoint_meta.session_id,
                "created_at": checkpoint_meta.created_at.isoformat(),
                "stage": checkpoint_meta.stage,
                "prompt": checkpoint_meta.prompt,
                "stage_metrics": checkpoint_meta.stage_metrics,
            }
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata_dict, f, indent=2)

            logger.info("Checkpoint saved: %s (stage: %s)", checkpoint_id, stage)
            return checkpoint_id

        except Exception as exc:
            logger.exception("Failed to save checkpoint %s: %s", checkpoint_id, exc)
            return ""

    def load_checkpoint(self, checkpoint_id: str) -> Optional[WorkflowCheckpoint]:
        """Load a workflow checkpoint."""
        if not self.enabled:
            logger.warning("Checkpointing disabled; cannot load.")
            return None

        checkpoint_path = self.checkpoint_dir / f"{checkpoint_id}.pkl"
        if not checkpoint_path.exists():
            logger.error("Checkpoint not found: %s", checkpoint_id)
            return None

        try:
            # SECURITY: Use JSON instead of pickle to prevent arbitrary code execution
            # pickle.load() can execute malicious code - JSON is safe
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                checkpoint = json.load(f)
            logger.info("Checkpoint loaded: %s", checkpoint_id)
            return checkpoint
        except Exception as exc:
            logger.exception("Failed to load checkpoint %s: %s", checkpoint_id, exc)
            return None

    def list_checkpoints(self, session_id: Optional[str] = None) -> List[CheckpointMetadata]:
        """List all available checkpoints."""
        if not self.enabled:
            return []

        checkpoints: List[CheckpointMetadata] = []
        for metadata_path in self.checkpoint_dir.glob("*.json"):
            try:
                with open(metadata_path) as f:
                    data = json.load(f)
                if session_id is None or data.get("session_id") == session_id:
                    checkpoints.append(
                        CheckpointMetadata(
                            checkpoint_id=data["checkpoint_id"],
                            session_id=data["session_id"],
                            created_at=datetime.fromisoformat(data["created_at"]),
                            stage=data["stage"],
                            prompt=data["prompt"],
                            stage_metrics=data.get("stage_metrics", {}),
                        )
                    )
            except Exception as exc:
                logger.warning("Failed to read checkpoint metadata %s: %s", metadata_path, exc)

        return sorted(checkpoints, key=lambda c: c.created_at, reverse=True)

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint."""
        if not self.enabled:
            return False

        checkpoint_path = self.checkpoint_dir / f"{checkpoint_id}.pkl"
        metadata_path = self.checkpoint_dir / f"{checkpoint_id}.json"

        try:
            if checkpoint_path.exists():
                checkpoint_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()
            logger.info("Checkpoint deleted: %s", checkpoint_id)
            return True
        except Exception as exc:
            logger.exception("Failed to delete checkpoint %s: %s", checkpoint_id, exc)
            return False

    @staticmethod
    def _generate_checkpoint_id(session_id: str, stage: str) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"{session_id}_{stage}_{timestamp}"
