"""
Evaluation Agent

Scores the generated draft against academic rubrics, identifies gaps, and
recommends iterative improvements before submission.
"""

from __future__ import annotations

import json
import logging
import re
import textwrap
from dataclasses import dataclass, field
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
class EvaluationCriterion:
    """Detailed scoring for a single rubric criterion."""

    name: str
    score: float
    max_score: float
    rationale: str
    action_items: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "score": self.score,
            "max_score": self.max_score,
            "rationale": self.rationale,
            "action_items": self.action_items,
        }


@dataclass
class SectionEvaluation:
    """Per-section evaluation with targeted guidance."""

    section_id: str
    score: float
    strengths: List[str]
    improvements: List[str]
    blocking_issues: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_id": self.section_id,
            "score": self.score,
            "strengths": self.strengths,
            "improvements": self.improvements,
            "blocking_issues": self.blocking_issues,
        }


@dataclass
class EvaluationAgentResult:
    """Final evaluation summary for the draft."""

    total_score: float
    pass_threshold: float
    overall_assessment: str
    reviewer_summary: str
    risks: List[str]
    next_iteration_plan: List[str]
    criteria: List[EvaluationCriterion]
    section_feedback: List[SectionEvaluation]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_score": self.total_score,
            "pass_threshold": self.pass_threshold,
            "overall_assessment": self.overall_assessment,
            "reviewer_summary": self.reviewer_summary,
            "risks": self.risks,
            "next_iteration_plan": self.next_iteration_plan,
            "criteria": [criterion.to_dict() for criterion in self.criteria],
            "section_feedback": [feedback.to_dict() for feedback in self.section_feedback],
            "metadata": self.metadata,
        }


class EvaluationAgent:
    """Performs rubric-driven evaluation of generated drafts."""

    EVALUATION_PROMPT = textwrap.dedent(
        """
        You are an academic quality assurance director. Evaluate the draft using
        the provided rubric and project requirements. Clearly score each
        criterion on a 0-100 scale (or provided max) and explain the rationale.

        Return JSON with this exact structure:
        {
          "total_score": 0-100,
          "pass_threshold": 70,
          "overall_assessment": "string",
          "reviewer_summary": "string",
          "risks": ["string"],
          "next_iteration_plan": ["string"],
          "criteria": [
            {
              "name": "Content",
              "score": 85,
              "max_score": 30,
              "rationale": "string",
              "action_items": ["string"]
            }
          ],
          "section_feedback": [
            {
              "section_id": "S1",
              "score": 80,
              "strengths": ["string"],
              "improvements": ["string"],
              "blocking_issues": ["string"]
            }
          ]
        }
        """
    ).strip()

    def __init__(self, config: Optional[ProwziConfig] = None):
        self.config = config or get_config()
        self.agent_config = self.config.agents["evaluation"]
        self.model_config = self.config.get_model_for_agent("evaluation")

        self.chat_client = OpenAIChatClient(
            api_key=self.config.openrouter_api_key,
            base_url=self.config.openrouter_base_url,
            model_id=self.model_config.name,
            # NOTE: temperature and max_tokens not supported by OpenAIChatClient init
            # These should be passed in ChatAgent.run() execution_settings instead
        )

        self.evaluator_agent = ChatAgent(
            chat_client=self.chat_client,
            instructions=self.EVALUATION_PROMPT,
        )

    async def evaluate_draft(
        self,
        intent: IntentAnalysis,
        plan: ResearchPlan,
        verification: VerificationAgentResult,
        draft: WritingAgentResult,
    ) -> EvaluationAgentResult:
        context = self._build_context(intent, plan, verification, draft)
        try:
            response = await self.evaluator_agent.run(context)
            payload = self._extract_json(response.response)
            return self._payload_to_result(payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Evaluation agent fallback triggered: %s", exc)
            return self._heuristic_evaluation(intent, plan, verification, draft, error=str(exc))

    def _build_context(
        self,
        intent: IntentAnalysis,
        plan: ResearchPlan,
        verification: VerificationAgentResult,
        draft: WritingAgentResult,
    ) -> str:
        requirements = textwrap.dedent(
            f"""
            Requirements Overview:
              Document Type: {intent.document_type}
              Academic Level: {intent.academic_level}
              Target Word Count: {intent.word_count}
              Citation Style: {intent.citation_style or 'Not specified'}
              Explicit Requirements: {', '.join(intent.explicit_requirements[:8]) or 'None'}
              Implicit Requirements: {', '.join(intent.implicit_requirements[:8]) or 'None'}
              Outstanding Questions: {', '.join(intent.missing_info[:5]) or 'None'}
            """
        ).strip()

        criteria_block = textwrap.dedent(
            """
            Evaluation Rubric:
              - Content (0-30): Depth, breadth, accuracy, coverage of research plan.
              - Structure (0-20): Logical organization, transitions, adherence to outline.
              - Citations (0-20): Correct usage, diversity, alignment with verification.
              - Writing Quality (0-20): Clarity, tone, grammar, academic voice.
              - Requirements Fit (0-10): Meets prompt, resolves missing info, matches level.
            """
        ).strip()

        section_summaries = []
        for section in draft.sections:
            preview = section.content[:600].replace("\n", " ").strip()
            section_summaries.append(
                textwrap.dedent(
                    f"""
                    Section {section.section_id} - {section.title}
                      Word Count: {section.word_count}
                      Quality Score: {section.quality_score}
                      Citations: {', '.join(section.citations[:6]) or 'None'}
                      Preview: {preview}
                    """
                ).strip()
            )

        verification_summary = textwrap.dedent(
            f"""
            Verified Sources Summary:
              Accepted: {len(verification.accepted_sources)}
              Rejected: {len(verification.rejected_sources)}
              High Risk: {len(verification.high_risk_sources)}
              Analyst Summary: {verification.analyst_summary[:400]}
            """
        ).strip()

        draft_overview = textwrap.indent('\n\n'.join(section_summaries) or 'No sections generated.', '  ')
        bibliography_preview = textwrap.indent('\n'.join(draft.bibliography[:10]) or 'None', '  ')
        style_guidelines_text = textwrap.indent('\n'.join(draft.style_guidelines) or 'None', '  ')
        verification_insights = textwrap.indent(verification_summary, '  ')

        context = (
            f"{requirements}\n\n{criteria_block}\n\nDraft Overview:\n"
            f"{draft_overview}\n\n"
            f"Bibliography Preview:\n{bibliography_preview}\n\n"
            f"Style Guidelines:\n{style_guidelines_text}\n\n"
            f"Verification Insights:\n{verification_insights}\n\n"
            f"Research Plan Metadata:\n  Total Tasks: {len(plan.execution_order)}\n"
            f"  Quality Checkpoints: {len(plan.quality_checkpoints)}\n"
            f"  Contingencies: {len(plan.contingencies)}\n\n"
            f"Please evaluate and provide JSON as specified above."
        )
        return context

    def _payload_to_result(self, payload: Dict[str, Any]) -> EvaluationAgentResult:
        criteria_data = payload.get("criteria", [])
        criteria = [
            EvaluationCriterion(
                name=str(item.get("name", "Unnamed")),
                score=float(item.get("score", 0.0)),
                max_score=float(item.get("max_score", 100.0)),
                rationale=str(item.get("rationale", "")),
                action_items=[str(action) for action in item.get("action_items", []) if action],
            )
            for item in criteria_data
        ]

        section_feedback = [
            SectionEvaluation(
                section_id=str(item.get("section_id", "")),
                score=float(item.get("score", 0.0)),
                strengths=[str(note) for note in item.get("strengths", []) if note],
                improvements=[str(note) for note in item.get("improvements", []) if note],
                blocking_issues=[str(note) for note in item.get("blocking_issues", []) if note],
            )
            for item in payload.get("section_feedback", [])
        ]

        total_score = float(payload.get("total_score", 0.0))
        pass_threshold = float(payload.get("pass_threshold", 70.0))

        metadata = {
            "mode": "llm",
            "raw_payload": payload,
        }

        return EvaluationAgentResult(
            total_score=total_score,
            pass_threshold=pass_threshold,
            overall_assessment=str(payload.get("overall_assessment", "")),
            reviewer_summary=str(payload.get("reviewer_summary", "")),
            risks=[str(risk) for risk in payload.get("risks", []) if risk],
            next_iteration_plan=[str(step) for step in payload.get("next_iteration_plan", []) if step],
            criteria=criteria,
            section_feedback=section_feedback,
            metadata=metadata,
        )

    def _heuristic_evaluation(
        self,
        intent: IntentAnalysis,
        plan: ResearchPlan,
        verification: VerificationAgentResult,
        draft: WritingAgentResult,
        error: Optional[str] = None,
    ) -> EvaluationAgentResult:
        content_score = self._content_coverage_score(plan, draft)
        structure_score = self._structure_score(draft)
        citation_score = self._citation_score(verification, draft)
        writing_score = self._writing_quality_score(draft)
        requirements_score = self._requirements_score(intent, draft)

        criteria = [
            EvaluationCriterion(
                name="Content",
                score=content_score * 30,
                max_score=30,
                rationale="Heuristic coverage based on task/section alignment.",
                action_items=["Ensure all planned tasks have dedicated coverage."],
            ),
            EvaluationCriterion(
                name="Structure",
                score=structure_score * 20,
                max_score=20,
                rationale="Evaluated outline completeness and section ordering.",
                action_items=["Tighten transitions between sections with low scores."],
            ),
            EvaluationCriterion(
                name="Citations",
                score=citation_score * 20,
                max_score=20,
                rationale="Compared citations count and diversity against verified sources.",
                action_items=["Integrate more accepted sources in low-coverage sections."],
            ),
            EvaluationCriterion(
                name="Writing Quality",
                score=writing_score * 20,
                max_score=20,
                rationale="Based on average section quality scores and readability heuristics.",
                action_items=["Revise sections with quality score below 0.65."],
            ),
            EvaluationCriterion(
                name="Requirements Fit",
                score=requirements_score * 10,
                max_score=10,
                rationale="Checked explicit requirement keywords within the draft.",
                action_items=["Address missing explicit requirement keywords."],
            ),
        ]

        total_score = sum(item.score for item in criteria)
        pass_threshold = 70.0
        overall_assessment = (
            "Draft meets minimum quality but requires revision." if total_score >= pass_threshold else "Draft below approval threshold; major revisions required."
        )

        section_feedback = [
            SectionEvaluation(
                section_id=section.section_id,
                score=max(0.0, min(100.0, section.quality_score * 100)),
                strengths=["Section generated via heuristic evaluation."],
                improvements=["Expand analysis and tighten citations."],
                blocking_issues=[""],
            )
            for section in draft.sections
        ]

        risks = []
        if content_score < 0.6:
            risks.append("Content coverage below threshold; investigate missing plan tasks.")
        if citation_score < 0.5:
            risks.append("Citation usage is sparse relative to verified sources.")
        if writing_score < 0.6:
            risks.append("Average section quality below 0.6; requires stylistic revision.")

        metadata = {
            "mode": "heuristic",
            "error": error,
            "content_score": content_score,
            "structure_score": structure_score,
            "citation_score": citation_score,
            "writing_score": writing_score,
            "requirements_score": requirements_score,
        }

        return EvaluationAgentResult(
            total_score=total_score,
            pass_threshold=pass_threshold,
            overall_assessment=overall_assessment,
            reviewer_summary="Automated heuristic evaluation completed due to LLM failure.",
            risks=risks,
            next_iteration_plan=["Re-run evaluation once LLM access is restored."],
            criteria=criteria,
            section_feedback=section_feedback,
            metadata=metadata,
        )

    def _content_coverage_score(self, plan: ResearchPlan, draft: WritingAgentResult) -> float:
        planned_sections = {task.id for task in plan.task_hierarchy.subtasks}
        drafted_sections = {section.section_id for section in draft.sections}
        if not planned_sections:
            return 1.0
        matched = sum(1 for section_id in drafted_sections if section_id in planned_sections)
        return max(0.2, matched / len(planned_sections))

    def _structure_score(self, draft: WritingAgentResult) -> float:
        if not draft.sections:
            return 0.0
        ideal_sequence = list(range(1, len(draft.sections) + 1))
        actual_sequence = []
        for section in draft.sections:
            try:
                actual_sequence.append(int(re.sub(r"\D", "", section.section_id) or 0))
            except ValueError:
                actual_sequence.append(0)
        monotonic = sum(1 for i, value in enumerate(actual_sequence) if value == ideal_sequence[i])
        return max(0.3, monotonic / len(ideal_sequence))

    def _citation_score(self, verification: VerificationAgentResult, draft: WritingAgentResult) -> float:
        if not draft.sections:
            return 0.0
        total_citations = sum(len(section.sources_used) for section in draft.sections)
        potential_sources = len(verification.accepted_sources) or 1
        diversity = len({source for section in draft.sections for source in section.sources_used})
        score = min(1.0, (total_citations / (len(draft.sections) * 3)) * 0.6 + (diversity / potential_sources) * 0.4)
        return max(0.2, score)

    def _writing_quality_score(self, draft: WritingAgentResult) -> float:
        if not draft.sections:
            return 0.0
        avg_quality = sum(section.quality_score for section in draft.sections) / len(draft.sections)
        readability_penalty = 0.0
        for section in draft.sections:
            readability_penalty += self._readability_penalty(section.content)
        readability_penalty = readability_penalty / len(draft.sections)
        score = max(0.2, min(1.0, avg_quality - readability_penalty))
        return score

    def _requirements_score(self, intent: IntentAnalysis, draft: WritingAgentResult) -> float:
        if not intent.explicit_requirements:
            return 1.0
        content_blob = " ".join(section.content.lower() for section in draft.sections)
        hits = sum(1 for req in intent.explicit_requirements if req.lower() in content_blob)
        return max(0.2, hits / len(intent.explicit_requirements))

    def _readability_penalty(self, text: str) -> float:
        sentences = max(1, text.count("."))
        words = max(1, len(text.split()))
        words_per_sentence = words / sentences
        penalty = 0.0
        if words_per_sentence > 28:
            penalty += min(0.3, (words_per_sentence - 28) / 50)
        long_word_ratio = sum(1 for word in text.split() if len(word) > 12) / words
        penalty += min(0.2, long_word_ratio)
        return penalty

    def _extract_json(self, text: str) -> Dict[str, Any]:
        json_block: Optional[str] = None
        fenced = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fenced:
            json_block = fenced.group(1)
        else:
            bare = re.search(r"\{.*\}", text, re.DOTALL)
            if bare:
                json_block = bare.group(0)
        if not json_block:
            raise ValueError("LLM response did not contain JSON")
        return json.loads(json_block)
