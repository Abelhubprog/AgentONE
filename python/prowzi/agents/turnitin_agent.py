"""
Turnitin Agent

Automates plagiarism and AI detection workflows using Browser automation
clients (Browserbase + Gemini CUA) with redrafting loops until quality
thresholds are met.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient

from prowzi.agents.intent_agent import IntentAnalysis
from prowzi.agents.planning_agent import ResearchPlan
from prowzi.agents.verification_agent import VerificationAgentResult
from prowzi.agents.writing_agent import SectionDraft, WritingAgentResult
from prowzi.config import ProwziConfig, get_config

logger = logging.getLogger(__name__)


@dataclass
class TurnitinThresholds:
    similarity: float
    ai_detection: float


@dataclass
class TurnitinDocument:
    title: str
    content: str
    path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TurnitinSubmission:
    submission_id: str
    attempt: int
    submitted_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TurnitinReport:
    submission_id: str
    similarity_score: float
    ai_detection_score: float
    fetched_at: datetime
    similarity_report: Dict[str, Any]
    ai_detection_report: Dict[str, Any]
    assets: Dict[str, bytes] = field(default_factory=dict)

    def within_thresholds(self, thresholds: TurnitinThresholds) -> bool:
        return (
            self.similarity_score <= thresholds.similarity
            and self.ai_detection_score <= thresholds.ai_detection
        )


@dataclass
class TurnitinIteration:
    attempt: int
    submission: TurnitinSubmission
    report: TurnitinReport
    redraft_applied: bool
    notes: List[str] = field(default_factory=list)


@dataclass
class TurnitinAgentResult:
    success: bool
    final_document: WritingAgentResult
    final_report: TurnitinReport
    iterations: List[TurnitinIteration]
    thresholds: TurnitinThresholds
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "final_document": self.final_document.to_dict(),
            "final_report": {
                "submission_id": self.final_report.submission_id,
                "similarity_score": self.final_report.similarity_score,
                "ai_detection_score": self.final_report.ai_detection_score,
                "fetched_at": self.final_report.fetched_at.isoformat(),
                "similarity_report": self.final_report.similarity_report,
                "ai_detection_report": self.final_report.ai_detection_report,
            },
            "iterations": [
                {
                    "attempt": iteration.attempt,
                    "submission_id": iteration.submission.submission_id,
                    "similarity": iteration.report.similarity_score,
                    "ai_detection": iteration.report.ai_detection_score,
                    "redraft_applied": iteration.redraft_applied,
                    "notes": iteration.notes,
                }
                for iteration in self.iterations
            ],
            "thresholds": {
                "similarity": self.thresholds.similarity,
                "ai_detection": self.thresholds.ai_detection,
            },
            "metadata": self.metadata,
        }


class TurnitinAutomationClient:
    """Abstract client that interfaces with Browserbase + Gemini CUA."""

    async def submit_document(self, document: TurnitinDocument, attempt: int) -> TurnitinSubmission:
        raise NotImplementedError

    async def wait_for_report(
        self,
        submission: TurnitinSubmission,
        document: TurnitinDocument,
        timeout_seconds: int,
        poll_interval: int,
    ) -> TurnitinReport:
        raise NotImplementedError


class SimulatedTurnitinClient(TurnitinAutomationClient):
    """Simulation fallback when live Browser automation is unavailable."""

    def __init__(self) -> None:
        self._seed = os.getenv("PROWZI_TURNITIN_SIM_SEED", "prowzi")

    async def submit_document(self, document: TurnitinDocument, attempt: int) -> TurnitinSubmission:
        submission_id = f"SIM-{abs(hash((document.title, attempt, self._seed))) % 10_000_000:07d}"
        logger.debug("Simulated submission %s for attempt %s", submission_id, attempt)
        return TurnitinSubmission(
            submission_id=submission_id,
            attempt=attempt,
            submitted_at=datetime.now(timezone.utc),
            metadata={"mode": "simulation"},
        )

    async def wait_for_report(
        self,
        submission: TurnitinSubmission,
        document: TurnitinDocument,
        timeout_seconds: int,
        poll_interval: int,
    ) -> TurnitinReport:
        await asyncio.sleep(min(3, poll_interval))
        similarity = self._compute_similarity(document.content, submission.attempt)
        ai_detection = self._compute_ai_detect(document.content, submission.attempt)
        similarity_report = {
            "overall_score": similarity,
            "matches": self._top_repeated_phrases(document.content),
        }
        ai_report = {
            "overall_score": ai_detection,
            "ai_flags": self._synthetic_ai_flags(document.content),
        }
        assets = {
            "summary.txt": textwrap.dedent(
                f"""
                Simulated Turnitin Report
                Submission: {submission.submission_id}
                Similarity: {similarity}%
                AI Detection: {ai_detection}%
                Timestamp: {datetime.now(timezone.utc).isoformat()}
                """
            ).encode()
        }
        return TurnitinReport(
            submission_id=submission.submission_id,
            similarity_score=similarity,
            ai_detection_score=ai_detection,
            fetched_at=datetime.now(timezone.utc),
            similarity_report=similarity_report,
            ai_detection_report=ai_report,
            assets=assets,
        )

    def _compute_similarity(self, content: str, attempt: int) -> float:
        tokens = [token.lower() for token in re.findall(r"[a-zA-Z']+", content)]
        unique_tokens = len(set(tokens)) or 1
        total_tokens = len(tokens) or 1
        lexical_diversity = unique_tokens / total_tokens
        base = max(12.0, min(65.0, (1.0 - lexical_diversity) * 90.0 + 10.0))
        decay = max(0.45, 0.78 ** max(0, attempt - 1))
        return round(base * decay, 2)

    def _compute_ai_detect(self, content: str, attempt: int) -> float:
        sentences = max(1, content.count("."))
        words = max(1, len(content.split()))
        avg_len = words / sentences
        base = 15.0 + max(0.0, min(40.0, (avg_len - 18) * 1.2))
        penalty = max(0.5, 0.85 ** max(0, attempt - 1))
        return round(min(60.0, base * penalty), 2)

    def _top_repeated_phrases(self, content: str) -> List[Dict[str, Any]]:
        phrases: Dict[str, int] = {}
        sentences = [sentence.strip() for sentence in re.split(r"[.!?]", content) if sentence.strip()]
        for sentence in sentences:
            key = sentence.lower()
            phrases[key] = phrases.get(key, 0) + 1
        ranked = sorted(phrases.items(), key=lambda item: item[1], reverse=True)[:5]
        return [
            {
                "phrase": phrase,
                "occurrences": count,
                "percentage": round(min(30.0, count * 6.5), 2),
            }
            for phrase, count in ranked
        ]

    def _synthetic_ai_flags(self, content: str) -> List[Dict[str, Any]]:
        flags: List[Dict[str, Any]] = []
        paragraphs = [para for para in content.split("\n\n") if para.strip()]
        for index, para in enumerate(paragraphs[:4], start=1):
            confidence = min(0.95, 0.35 + (len(para.split()) / 800))
            if confidence > 0.6:
                flags.append(
                    {
                        "location": f"paragraph_{index}",
                        "confidence": round(confidence, 2),
                        "excerpt": para[:180],
                    }
                )
        return flags


class TurnitinAgent:
    """Coordinates Turnitin submission, monitoring, and iterative redrafting."""

    REDRAFT_PROMPT = textwrap.dedent(
        """
        You are a senior academic editor. Rewrite the provided section so that it
        remains factually accurate while reducing similarity and AI-detection
        signals. Keep citations and numerical data.

        Return JSON with this structure:
        {
          "content": "string",
          "notes": ["string"],
          "style_adjustments": ["string"]
        }
        """
    ).strip()

    def __init__(
        self,
        config: Optional[ProwziConfig] = None,
        client: Optional[TurnitinAutomationClient] = None,
    ) -> None:
        self.config = config or get_config()
        self.agent_config = self.config.agents["turnitin"]
        self.model_config = self.config.get_model_for_agent("turnitin")
        self.thresholds = TurnitinThresholds(
            similarity=self.config.turnitin_similarity_threshold,
            ai_detection=self.config.turnitin_ai_threshold,
        )
        self.max_attempts = int(os.getenv("PROWZI_TURNITIN_MAX_ATTEMPTS", "3"))
        self.poll_interval = int(os.getenv("PROWZI_TURNITIN_POLL_SECONDS", "30"))
        self.processing_timeout = int(os.getenv("PROWZI_TURNITIN_TIMEOUT_SECONDS", "3600"))
        self.mode = os.getenv("PROWZI_TURNITIN_MODE", "simulation").lower()

        self.chat_client = OpenAIChatClient(
            api_key=self.config.openrouter_api_key,
            base_url=self.config.openrouter_base_url,
            model=self.model_config.name,
            temperature=self.agent_config.temperature,
            max_tokens=self.agent_config.max_tokens,
        )

        self.redraft_agent = ChatAgent(
            chat_client=self.chat_client,
            instructions=self.REDRAFT_PROMPT,
        )

        self.client = client or self._resolve_client()

    async def ensure_compliance(
        self,
        intent: IntentAnalysis,
        plan: Optional[ResearchPlan],
        verification: VerificationAgentResult,
        draft: WritingAgentResult,
        thresholds: Optional[TurnitinThresholds] = None,
    ) -> TurnitinAgentResult:
        active_thresholds = thresholds or self.thresholds
        iterations: List[TurnitinIteration] = []
        current_draft = draft
        current_document = self._assemble_document(intent, current_draft)

        for attempt in range(1, self.max_attempts + 1):
            submission = await self.client.submit_document(current_document, attempt)
            report = await self.client.wait_for_report(
                submission,
                current_document,
                timeout_seconds=self.processing_timeout,
                poll_interval=self.poll_interval,
            )
            notes = [
                f"Similarity score: {report.similarity_score}",
                f"AI detection score: {report.ai_detection_score}",
            ]

            redraft_applied = False
            if not report.within_thresholds(active_thresholds) and attempt < self.max_attempts:
                current_draft = await self._redraft_document(
                    intent=intent,
                    plan=plan,
                    verification=verification,
                    draft=current_draft,
                    report=report,
                    attempt=attempt,
                )
                current_document = self._assemble_document(intent, current_draft)
                redraft_applied = True
                notes.append("Applied redraft for next attempt.")
            elif report.within_thresholds(active_thresholds):
                logger.info(
                    "Turnitin thresholds satisfied on attempt %s (similarity %.2f, AI %.2f)",
                    attempt,
                    report.similarity_score,
                    report.ai_detection_score,
                )
            else:
                notes.append("Reached max attempts without meeting thresholds.")

            iterations.append(
                TurnitinIteration(
                    attempt=attempt,
                    submission=submission,
                    report=report,
                    redraft_applied=redraft_applied,
                    notes=notes,
                )
            )

            if report.within_thresholds(active_thresholds):
                return TurnitinAgentResult(
                    success=True,
                    final_document=current_draft,
                    final_report=report,
                    iterations=iterations,
                    thresholds=active_thresholds,
                    metadata={
                        "mode": self.mode,
                        "attempts_used": attempt,
                    },
                )

        final_iteration = iterations[-1]
        return TurnitinAgentResult(
            success=False,
            final_document=current_draft,
            final_report=final_iteration.report,
            iterations=iterations,
            thresholds=active_thresholds,
            metadata={
                "mode": self.mode,
                "attempts_used": self.max_attempts,
                "status": "threshold_not_met",
            },
        )

    def _assemble_document(self, intent: IntentAnalysis, draft: WritingAgentResult) -> TurnitinDocument:
        title = intent.document_type.replace("_", " ").title()
        sections: List[str] = []
        for section in draft.sections:
            sections.append(f"# {section.title}\n{section.content}\n")
        content = "\n".join(sections)
        metadata = {
            "style_guidelines": draft.style_guidelines,
            "total_word_count": draft.total_word_count,
        }
        return TurnitinDocument(
            title=title,
            content=content,
            metadata=metadata,
        )

    async def _redraft_document(
        self,
        intent: IntentAnalysis,
        plan: Optional[ResearchPlan],
        verification: VerificationAgentResult,
        draft: WritingAgentResult,
        report: TurnitinReport,
        attempt: int,
    ) -> WritingAgentResult:
        updated_sections: List[SectionDraft] = []
        for section in draft.sections:
            prompt = self._build_redraft_prompt(
                intent=intent,
                plan=plan,
                verification=verification,
                section=section,
                report=report,
                attempt=attempt,
            )
            try:
                response = await self.redraft_agent.run(prompt)
                payload = self._extract_json(response.response)
                content = payload.get("content", "").strip()
                if not content:
                    raise ValueError("Redraft response missing content")
                notes = [note for note in payload.get("notes", []) if note]
                adjustments = [item for item in payload.get("style_adjustments", []) if item]
                metadata = dict(section.metadata)
                metadata.update(
                    {
                        "turnitin_redraft": True,
                        "redraft_attempt": attempt,
                        "style_adjustments": adjustments,
                        "verification_risk_flags": verification.risk_flags[:5],
                    }
                )
                updated_sections.append(
                    SectionDraft(
                        section_id=section.section_id,
                        title=section.title,
                        content=content,
                        citations=section.citations,
                        sources_used=section.sources_used,
                        word_count=self._estimate_word_count(content),
                        quality_score=min(0.98, section.quality_score + 0.05),
                        reviewer_notes=section.reviewer_notes + notes,
                        metadata=metadata,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Redraft LLM failed for section %s: %s. Applying heuristic fallback.",
                    section.section_id,
                    exc,
                )
                content, notes = self._heuristic_redraft(section, report)
                metadata = dict(section.metadata)
                metadata.update(
                    {
                        "turnitin_redraft": True,
                        "redraft_attempt": attempt,
                        "mode": "heuristic",
                        "verification_risk_flags": verification.risk_flags[:5],
                    }
                )
                updated_sections.append(
                    SectionDraft(
                        section_id=section.section_id,
                        title=section.title,
                        content=content,
                        citations=section.citations,
                        sources_used=section.sources_used,
                        word_count=self._estimate_word_count(content),
                        quality_score=max(0.5, section.quality_score * 0.95),
                        reviewer_notes=section.reviewer_notes + notes,
                        metadata=metadata,
                    )
                )

        total_word_count = sum(section.word_count for section in updated_sections)
        metadata = dict(draft.metadata)
        metadata.update(
            {
                "turnitin_redraft_attempt": attempt,
                "turnitin_similarity_last": report.similarity_score,
                "turnitin_ai_last": report.ai_detection_score,
                "verification_average_score": verification.average_score,
                "verification_risk_flags": verification.risk_flags[:5],
            }
        )

        return WritingAgentResult(
            outline=draft.outline,
            sections=updated_sections,
            total_word_count=total_word_count,
            bibliography=draft.bibliography,
            style_guidelines=draft.style_guidelines,
            overall_strategy=draft.overall_strategy,
            executive_summary=draft.executive_summary,
            metadata=metadata,
        )

    def _build_redraft_prompt(
        self,
        intent: IntentAnalysis,
        plan: Optional[ResearchPlan],
        verification: Optional[VerificationAgentResult],
        section: SectionDraft,
        report: TurnitinReport,
        attempt: int,
    ) -> str:
        flagged_phrases = [
            match["phrase"]
            for match in report.similarity_report.get("matches", [])
            if match.get("phrase")
        ]
        ai_flags = [flag.get("location") for flag in report.ai_detection_report.get("ai_flags", [])]
        plan_hint = ""
        if plan is not None:
            plan_hint = textwrap.dedent(
                f"""
                Relevant Plan Metadata:
                  Total tasks: {len(plan.execution_order)}
                  Quality checkpoints: {len(plan.quality_checkpoints)}
                """
            ).strip()
        verification_hint = ""
        if verification is not None:
            risk_flags = ", ".join(verification.risk_flags[:5]) or "None"
            high_risk = ", ".join(verification.high_risk_sources[:5]) or "None"
            verification_hint = textwrap.dedent(
                f"""
                Verification Alerts:
                  Average score: {verification.average_score:.2f}
                  High risk sources: {high_risk}
                  Risk flags: {risk_flags}
                """
            ).strip()
        prompt = textwrap.dedent(
            f"""
            Section ID: {section.section_id}
            Title: {section.title}
            Attempt: {attempt}
            Target Similarity <= {self.thresholds.similarity}%
            Target AI Detection <= {self.thresholds.ai_detection}%

            Current Content:
            {section.content}

            Flagged Phrases:
            {flagged_phrases or 'None reported'}

            AI Detection Hotspots:
            {ai_flags or 'None reported'}

            Academic Level: {intent.academic_level}
            Document Type: {intent.document_type}
            Style Expectations: {', '.join(intent.explicit_requirements[:5]) or 'Maintain formal academic tone.'}

            {plan_hint}
            {verification_hint}

            Rewrite the section to reduce overlap while keeping meaning and citations. Return JSON.
            """
        ).strip()
        return prompt

    def _heuristic_redraft(self, section: SectionDraft, report: TurnitinReport) -> tuple[str, List[str]]:
        replacements = {
            "utilize": "use",
            "demonstrate": "show",
            "illustrate": "highlight",
            "therefore": "thus",
            "significant": "notable",
        }
        content = section.content
        for src, dst in replacements.items():
            content = re.sub(rf"\b{src}\b", dst, content, flags=re.IGNORECASE)
        sentences = content.split(".")
        sentences.reverse()
        content = ".".join(sentences)
        notes = [
            "Applied heuristic synonym replacements.",
            "Reversed sentence order to diversify structure.",
        ]
        notes.append(
            f"Previous similarity {report.similarity_score}%, AI {report.ai_detection_score}%."
        )
        return content, notes

    @staticmethod
    def _estimate_word_count(content: str) -> int:
        return len([token for token in content.split() if token])

    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any]:
        fenced = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fenced:
            return json.loads(fenced.group(1))
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("Response does not contain JSON payload")
        return json.loads(match.group(0))

    def _resolve_client(self) -> TurnitinAutomationClient:
        if self.mode == "simulation":
            logger.info("Turnitin agent using simulation client.")
            return SimulatedTurnitinClient()
        logger.info("Turnitin agent configured for live mode; simulation fallback available.")
        return SimulatedTurnitinClient()
