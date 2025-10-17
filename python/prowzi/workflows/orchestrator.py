"""Prowzi workflow orchestrator with advanced staged execution."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from prowzi.agents.evaluation_agent import EvaluationAgent, EvaluationAgentResult
from prowzi.agents.intent_agent import IntentAgent, IntentAnalysis
from prowzi.agents.planning_agent import PlanningAgent, ResearchPlan
from prowzi.agents.search_agent import SearchAgent, SearchAgentResult
from prowzi.agents.turnitin_agent import TurnitinAgent, TurnitinAgentResult, TurnitinThresholds
from prowzi.agents.verification_agent import VerificationAgent, VerificationAgentResult
from prowzi.agents.writing_agent import WritingAgent, WritingAgentResult
from prowzi.config import ProwziConfig, get_config
from prowzi.workflows.checkpoint import CheckpointManager, WorkflowCheckpoint
from prowzi.workflows.telemetry import TelemetryCollector

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str, Dict[str, Any]], Awaitable[None]]


def _new_dict() -> Dict[str, Any]:
    return {}


@dataclass
class ProwziOrchestrationResult:
    """Aggregated results from the full research pipeline."""

    intent: IntentAnalysis
    plan: ResearchPlan
    search: SearchAgentResult
    verification: VerificationAgentResult
    draft: WritingAgentResult
    evaluation: EvaluationAgentResult
    turnitin: TurnitinAgentResult
    metadata: Dict[str, Any] = field(default_factory=_new_dict)


@dataclass
class _StageExecutionStats:
    name: str
    attempts: int = 0
    duration_seconds: float = 0.0
    success: bool = False
    skipped: bool = False
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=_new_dict)


@dataclass
class _StageSpec:
    name: str
    executor: Callable[["_StageContext"], Awaitable[Tuple[Dict[str, Any], Dict[str, Any]]]]
    max_retries: int = 1
    retry_backoff: float = 1.5
    predicate: Optional[Callable[["_StageContext"], bool]] = None


@dataclass
class _StageContext:
    prompt: str
    document_paths: Optional[List[str | Path]]
    additional_context: Optional[Dict[str, Any]]
    custom_constraints: Optional[Dict[str, Any]]
    max_results_per_query: int
    max_sections: int
    thresholds: Optional[TurnitinThresholds]
    progress_callback: Optional[ProgressCallback]
    intent: Optional[IntentAnalysis] = None
    plan: Optional[ResearchPlan] = None
    search: Optional[SearchAgentResult] = None
    verification: Optional[VerificationAgentResult] = None
    draft: Optional[WritingAgentResult] = None
    evaluation: Optional[EvaluationAgentResult] = None
    initial_evaluation: Optional[EvaluationAgentResult] = None
    turnitin: Optional[TurnitinAgentResult] = None
    stage_metrics: Dict[str, Any] = field(default_factory=_new_dict)


class ProwziOrchestrator:
    """Runs the end-to-end Prowzi workflow with resilient staged orchestration."""

    def __init__(self, config: Optional[ProwziConfig] = None) -> None:
        self.config = config or get_config()
        self.intent_agent = IntentAgent(config=self.config)
        self.planning_agent = PlanningAgent(config=self.config)
        self.search_agent = SearchAgent(config=self.config)
        self.verification_agent = VerificationAgent(config=self.config)
        self.writing_agent = WritingAgent(config=self.config)
        self.evaluation_agent = EvaluationAgent(config=self.config)
        self.turnitin_agent = TurnitinAgent(config=self.config)

        # Checkpoint and telemetry setup
        if self.config.enable_checkpointing:
            self.checkpoint_manager = CheckpointManager(checkpoint_dir=self.config.checkpoint_dir)
            logger.info("Checkpointing enabled at: %s", self.config.checkpoint_dir)
        else:
            self.checkpoint_manager = None

        if self.config.enable_telemetry:
            telemetry_dir = self.config.checkpoint_dir / "telemetry"
            self.telemetry_collector = TelemetryCollector(output_dir=telemetry_dir)
            logger.info("Telemetry collection enabled at: %s", telemetry_dir)
        else:
            self.telemetry_collector = None

        self._stage_specs: List[_StageSpec] = [
            _StageSpec(name="intent", executor=self._stage_intent, max_retries=2),
            _StageSpec(name="planning", executor=self._stage_planning, max_retries=2),
            _StageSpec(name="search", executor=self._stage_search, max_retries=3, retry_backoff=2.0),
            _StageSpec(name="verification", executor=self._stage_verification, max_retries=2),
            _StageSpec(name="writing", executor=self._stage_writing, max_retries=2),
            _StageSpec(name="evaluation", executor=self._stage_evaluation, max_retries=2),
            _StageSpec(
                name="turnitin",
                executor=self._stage_turnitin,
                max_retries=max(2, getattr(self.turnitin_agent, "max_attempts", 2)),
            ),
            _StageSpec(
                name="post_turnitin_evaluation",
                executor=self._stage_post_turnitin_evaluation,
                predicate=self._should_run_post_turnitin_evaluation,
                max_retries=2,
            ),
        ]

    async def run_research(
        self,
        prompt: str,
    document_paths: Optional[List[str | Path]] = None,
        additional_context: Optional[Dict[str, Any]] = None,
        *,
        custom_constraints: Optional[Dict[str, Any]] = None,
        max_results_per_query: int = 12,
        max_sections: int = 8,
        thresholds: Optional[TurnitinThresholds] = None,
        progress_callback: Optional[ProgressCallback] = None,
        checkpoint_id: Optional[str] = None,
    ) -> ProwziOrchestrationResult:
        """Execute the complete pipeline with retries, metrics, checkpoints, and telemetry."""
        # Generate session ID
        session_id = checkpoint_id or str(uuid.uuid4())

        # Start telemetry
        if self.telemetry_collector:
            self.telemetry_collector.start_session(session_id=session_id, prompt=prompt)

        # Try to resume from checkpoint
        if checkpoint_id and self.checkpoint_manager:
            logger.info("Attempting to resume from checkpoint: %s", checkpoint_id)
            checkpoint = self.checkpoint_manager.load_checkpoint(checkpoint_id)
            if checkpoint:
                context = self._restore_context_from_checkpoint(
                    checkpoint=checkpoint,
                    prompt=prompt,
                    document_paths=document_paths,
                    additional_context=additional_context,
                    custom_constraints=custom_constraints,
                    max_results_per_query=max_results_per_query,
                    max_sections=max_sections,
                    thresholds=thresholds,
                    progress_callback=progress_callback,
                )
                logger.info("Resumed from checkpoint at stage: %s", checkpoint.metadata.stage)
            else:
                logger.warning("Checkpoint %s not found, starting fresh", checkpoint_id)
                context = _StageContext(
                    prompt=prompt,
                    document_paths=document_paths,
                    additional_context=additional_context,
                    custom_constraints=custom_constraints,
                    max_results_per_query=max_results_per_query,
                    max_sections=max_sections,
                    thresholds=thresholds,
                    progress_callback=progress_callback,
                )
        else:
            context = _StageContext(
                prompt=prompt,
                document_paths=document_paths,
                additional_context=additional_context,
                custom_constraints=custom_constraints,
                max_results_per_query=max_results_per_query,
                max_sections=max_sections,
                thresholds=thresholds,
                progress_callback=progress_callback,
            )

        stage_stats: List[_StageExecutionStats] = []
        workflow_start = time.perf_counter()

        # Determine starting stage index for resume
        start_stage_idx = 0
        if checkpoint_id and self.checkpoint_manager:
            checkpoint = self.checkpoint_manager.load_checkpoint(checkpoint_id)
            if checkpoint:
                for idx, spec in enumerate(self._stage_specs):
                    if spec.name == checkpoint.metadata.stage:
                        start_stage_idx = idx + 1
                        break

        for idx, spec in enumerate(self._stage_specs):
            if idx < start_stage_idx:
                logger.info("Skipping already completed stage: %s", spec.name)
                continue

            stage_start = time.perf_counter()
            stats = _StageExecutionStats(name=spec.name)

            # Telemetry: stage started
            if self.telemetry_collector:
                self.telemetry_collector.record_stage_event(
                    session_id=session_id, stage=spec.name, status="started", attempt=1, duration=0.0
                )

            if spec.predicate and not spec.predicate(context):
                stats.skipped = True
                stage_stats.append(stats)
                context.stage_metrics[spec.name] = {"status": "skipped"}
                await self._emit(f"{spec.name}_skipped", {"reason": "predicate"}, context.progress_callback)
                if self.telemetry_collector:
                    self.telemetry_collector.record_stage_event(
                        session_id=session_id,
                        stage=spec.name,
                        status="skipped",
                        attempt=1,
                        duration=time.perf_counter() - stage_start,
                    )
                continue

            attempt = 0
            while attempt < spec.max_retries:
                attempt += 1
                stats.attempts = attempt
                await self._emit(f"{spec.name}_start", {"attempt": attempt}, context.progress_callback)
                attempt_start = time.perf_counter()

                try:
                    event_payload, detail_metrics = await spec.executor(context)
                    attempt_duration = time.perf_counter() - attempt_start
                    stats.duration_seconds += attempt_duration
                    stats.success = True
                    stats.details = detail_metrics
                    context.stage_metrics[spec.name] = {
                        **detail_metrics,
                        "attempts": attempt,
                        "duration_seconds": stats.duration_seconds,
                        "status": "completed",
                    }
                    await self._emit(spec.name, event_payload, context.progress_callback)

                    # Telemetry: stage completed
                    if self.telemetry_collector:
                        self.telemetry_collector.record_stage_event(
                            session_id=session_id,
                            stage=spec.name,
                            status="completed",
                            attempt=attempt,
                            duration=attempt_duration,
                            details=detail_metrics,
                        )

                    # Checkpoint: save after successful stage
                    if self.checkpoint_manager and self.config.enable_checkpointing:
                        self._save_checkpoint(session_id, spec.name, context)

                    break
                except Exception as exc:
                    stats.error = repr(exc)
                    logger.exception("Stage %s failed on attempt %s", spec.name, attempt)

                    # Telemetry: retry or failure
                    if self.telemetry_collector:
                        status = "retrying" if attempt < spec.max_retries else "failed"
                        self.telemetry_collector.record_stage_event(
                            session_id=session_id,
                            stage=spec.name,
                            status=status,
                            attempt=attempt,
                            duration=time.perf_counter() - attempt_start,
                            error=str(exc),
                        )

                    await self._emit(
                        f"{spec.name}_retry",
                        {"attempt": attempt, "error": str(exc)},
                        context.progress_callback,
                    )
                    if attempt >= spec.max_retries:
                        raise
                    backoff = spec.retry_backoff ** attempt
                    await asyncio.sleep(backoff)

            stage_stats.append(stats)

        workflow_duration = time.perf_counter() - workflow_start
        if context.turnitin is None or context.draft is None or context.evaluation is None:
            raise RuntimeError("Pipeline did not complete successfully; final artifacts missing.")

        if context.intent is None or context.plan is None or context.search is None or context.verification is None:
            raise RuntimeError("Pipeline did not complete successfully; prerequisite artifacts missing.")

        turnitin_result = context.turnitin
        draft_result = context.draft
        evaluation_result = context.evaluation

        stage_summary: Dict[str, Dict[str, Any]] = {stat.name: asdict(stat) for stat in stage_stats}
        post_eval_stats: Dict[str, Any] = stage_summary.get("post_turnitin_evaluation", {"skipped": True})

        initial_evaluation = context.initial_evaluation

        metadata: Dict[str, Any] = {
            "workflow_duration_seconds": workflow_duration,
            "turnitin_attempts": len(turnitin_result.iterations),
            "turnitin_success": turnitin_result.success,
            "re_evaluated": not post_eval_stats.get("skipped", True),
            "initial_evaluation_score": initial_evaluation.total_score if initial_evaluation else None,
            "final_evaluation_score": evaluation_result.total_score,
            "evaluation_delta": (evaluation_result.total_score - initial_evaluation.total_score) if initial_evaluation else None,
            "stage_metrics": stage_summary,
            "stage_details": context.stage_metrics,
            "session_id": session_id,
        }

        # Complete telemetry session
        if self.telemetry_collector:
            self.telemetry_collector.complete_session(
                session_id=session_id,
                success=True,
                total_duration=workflow_duration,
                final_metadata=metadata,
            )

        return ProwziOrchestrationResult(
            intent=context.intent,
            plan=context.plan,
            search=context.search,
            verification=context.verification,
            draft=draft_result,
            evaluation=evaluation_result,
            turnitin=turnitin_result,
            metadata=metadata,
        )

    async def _stage_intent(self, context: _StageContext) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        intent = await self.intent_agent.analyze(
            prompt=context.prompt,
            document_paths=context.document_paths,
            additional_context=context.additional_context,
        )
        context.intent = intent
        return {"intent": intent.to_dict()}, {
            "confidence": intent.confidence_score,
            "explicit_requirements": len(intent.explicit_requirements),
            "missing_info": len(intent.missing_info),
        }

    async def _stage_planning(self, context: _StageContext) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if context.intent is None:
            raise RuntimeError("Intent stage must run before planning stage.")
        plan = await self.planning_agent.create_plan(
            intent_analysis=context.intent,
            custom_constraints=context.custom_constraints,
        )
        context.plan = plan
        return {
            "tasks": len(plan.execution_order),
            "search_queries": len(plan.search_queries),
            "plan": plan.to_dict(),
        }, {
            "tasks": len(plan.execution_order),
            "parallel_groups": len(plan.parallel_groups),
            "quality_checkpoints": len(plan.quality_checkpoints),
        }

    async def _stage_search(self, context: _StageContext) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if context.plan is None or context.intent is None:
            raise RuntimeError("Planning and intent stages must complete before search.")
        search = await self.search_agent.execute_plan(
            plan=context.plan,
            intent=context.intent,
            max_results_per_query=context.max_results_per_query,
        )
        context.search = search
        return {
            "total_results": search.total_results,
            "high_quality": search.high_quality_results,
            "coverage_gaps": search.coverage_gaps,
        }, {
            "engines_used": search.metadata.get("engines_used"),
            "average_relevance": search.average_relevance,
        }

    async def _stage_verification(self, context: _StageContext) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if context.intent is None or context.search is None or context.plan is None:
            raise RuntimeError("Search stage must complete before verification.")
        verification = await self.verification_agent.verify_sources(
            intent=context.intent,
            search_results=context.search,
            plan=context.plan,
        )
        context.verification = verification
        return {
            "accepted": verification.accepted_sources,
            "rejected": verification.rejected_sources,
            "average_score": verification.average_score,
            "risk_flags": verification.risk_flags,
        }, {
            "accepted_count": len(verification.accepted_sources),
            "rejected_count": len(verification.rejected_sources),
            "high_risk_sources": len(verification.high_risk_sources),
        }

    async def _stage_writing(self, context: _StageContext) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if context.intent is None or context.plan is None or context.verification is None:
            raise RuntimeError("Verification stage must complete before writing.")
        draft = await self.writing_agent.generate_document(
            intent=context.intent,
            plan=context.plan,
            verification=context.verification,
            max_sections=context.max_sections,
        )
        context.draft = draft
        return {
            "sections": len(draft.sections),
            "word_count": draft.total_word_count,
        }, {
            "sections": len(draft.sections),
            "word_count": draft.total_word_count,
            "bibliography_entries": len(draft.bibliography),
        }

    async def _stage_evaluation(self, context: _StageContext) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if context.intent is None or context.plan is None or context.verification is None or context.draft is None:
            raise RuntimeError("Writing stage must complete before evaluation.")
        evaluation = await self.evaluation_agent.evaluate_draft(
            intent=context.intent,
            plan=context.plan,
            verification=context.verification,
            draft=context.draft,
        )
        context.evaluation = evaluation
        context.initial_evaluation = evaluation
        return {
            "score": evaluation.total_score,
            "pass_threshold": evaluation.pass_threshold,
            "risks": evaluation.risks,
        }, {
            "score": evaluation.total_score,
            "pass_threshold": evaluation.pass_threshold,
            "risk_count": len(evaluation.risks),
        }

    async def _stage_turnitin(self, context: _StageContext) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if context.intent is None or context.plan is None or context.verification is None or context.draft is None:
            raise RuntimeError("Evaluation stage must complete before Turnitin submission.")
        turnitin = await self.turnitin_agent.ensure_compliance(
            intent=context.intent,
            plan=context.plan,
            verification=context.verification,
            draft=context.draft,
            thresholds=context.thresholds,
        )
        context.turnitin = turnitin
        context.draft = turnitin.final_document
        return {
            "success": turnitin.success,
            "attempts": len(turnitin.iterations),
            "similarity": turnitin.final_report.similarity_score,
            "ai_detection": turnitin.final_report.ai_detection_score,
        }, {
            "success": turnitin.success,
            "attempts": len(turnitin.iterations),
            "similarity": turnitin.final_report.similarity_score,
            "ai_detection": turnitin.final_report.ai_detection_score,
        }

    async def _stage_post_turnitin_evaluation(
        self, context: _StageContext
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if context.intent is None or context.plan is None or context.verification is None or context.draft is None:
            raise RuntimeError("Turnitin stage must complete before post evaluation.")
        evaluation = await self.evaluation_agent.evaluate_draft(
            intent=context.intent,
            plan=context.plan,
            verification=context.verification,
            draft=context.draft,
        )
        previous_score = context.initial_evaluation.total_score if context.initial_evaluation else None
        context.evaluation = evaluation
        return {
            "score": evaluation.total_score,
            "pass_threshold": evaluation.pass_threshold,
            "risks": evaluation.risks,
        }, {
            "score": evaluation.total_score,
            "delta": (evaluation.total_score - previous_score) if previous_score is not None else None,
            "risk_count": len(evaluation.risks),
        }

    def _should_run_post_turnitin_evaluation(self, context: _StageContext) -> bool:
        if context.turnitin is None:
            return False
        return any(iteration.redraft_applied for iteration in context.turnitin.iterations)

    @staticmethod
    async def _emit(
        stage: str,
        payload: Dict[str, Any],
        callback: Optional[ProgressCallback],
    ) -> None:
        if callback is None:
            return
        try:
            await callback(stage, payload)
        except Exception as exc:
            logger.warning("Progress callback for stage '%s' failed: %s", stage, exc)

    def _save_checkpoint(self, session_id: str, stage_name: str, context: _StageContext) -> None:
        """Save workflow checkpoint after successful stage completion."""
        if not self.checkpoint_manager:
            return

        try:
            context_dict = {
                "intent": context.intent,
                "plan": context.plan,
                "search": context.search,
                "verification": context.verification,
                "draft": context.draft,
                "evaluation": context.evaluation,
                "initial_evaluation": context.initial_evaluation,
                "turnitin": context.turnitin,
                "stage_metrics": context.stage_metrics,
                "document_paths": [str(p) for p in context.document_paths] if context.document_paths else None,
                "additional_context": context.additional_context,
                "custom_constraints": context.custom_constraints,
                "max_results_per_query": context.max_results_per_query,
                "max_sections": context.max_sections,
                "thresholds": context.thresholds,
            }

            self.checkpoint_manager.save_checkpoint(
                session_id=session_id,
                stage=stage_name,
                prompt=context.prompt,
                context=context_dict,
                stage_metrics=context.stage_metrics,
            )
            logger.info("Checkpoint saved for session %s at stage %s", session_id, stage_name)
        except Exception as exc:
            logger.warning("Failed to save checkpoint: %s", exc)

    def _restore_context_from_checkpoint(
        self,
        checkpoint: WorkflowCheckpoint,
        prompt: str,
        document_paths: Optional[List[str | Path]],
        additional_context: Optional[Dict[str, Any]],
        custom_constraints: Optional[Dict[str, Any]],
        max_results_per_query: int,
        max_sections: int,
        thresholds: Optional[TurnitinThresholds],
        progress_callback: Optional[ProgressCallback],
    ) -> _StageContext:
        """Restore context from checkpoint data."""
        # WorkflowCheckpoint already contains the agent results directly
        return _StageContext(
            prompt=prompt,
            document_paths=document_paths,
            additional_context=additional_context,
            custom_constraints=custom_constraints,
            max_results_per_query=max_results_per_query,
            max_sections=max_sections,
            thresholds=thresholds,
            progress_callback=progress_callback,
            intent=checkpoint.intent,
            plan=checkpoint.plan,
            search=checkpoint.search,
            verification=checkpoint.verification,
            draft=checkpoint.draft,
            evaluation=checkpoint.evaluation,
            initial_evaluation=checkpoint.initial_evaluation,
            turnitin=checkpoint.turnitin,
            stage_metrics=checkpoint.stage_metrics,
        )

    async def resume_from_checkpoint(
        self,
        checkpoint_id: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ProwziOrchestrationResult:
        """Resume a workflow from a saved checkpoint."""
        if not self.checkpoint_manager:
            raise ValueError("Checkpointing is not enabled")

        checkpoint = self.checkpoint_manager.load_checkpoint(checkpoint_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")

        logger.info("Resuming workflow from checkpoint: %s (stage: %s)", checkpoint_id, checkpoint.metadata.stage)

        # Resume workflow with checkpoint ID to restore state
        return await self.run_research(
            prompt=checkpoint.metadata.prompt,
            progress_callback=progress_callback,
            checkpoint_id=checkpoint_id,
        )
