"""
Writing Agent

Transforms verified research into a polished academic draft. Creates a
strategy-aligned outline, drafts sections with citations, and prepares
bibliography metadata for downstream evaluation.
"""

from __future__ import annotations

import json
import logging
import re
import textwrap
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient

from prowzi.agents.intent_agent import IntentAnalysis
from prowzi.agents.planning_agent import ResearchPlan, Task
from prowzi.agents.verification_agent import SourceVerification, VerificationAgentResult
from prowzi.config import ProwziConfig, get_config

logger = logging.getLogger(__name__)

MAX_SECTIONS_DEFAULT = 8
SECTION_WORD_BUFFER = 0.9


@dataclass
class SectionOutline:
    """Outline entry for a single document section."""

    section_id: str
    title: str
    objective: str
    target_word_count: int
    key_points: List[str]
    source_ids: List[str]
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_id": self.section_id,
            "title": self.title,
            "objective": self.objective,
            "target_word_count": self.target_word_count,
            "key_points": self.key_points,
            "source_ids": self.source_ids,
            "dependencies": self.dependencies,
        }


@dataclass
class SectionDraft:
    """Drafted content for a section."""

    section_id: str
    title: str
    content: str
    citations: List[str]
    sources_used: List[str]
    word_count: int
    quality_score: float
    reviewer_notes: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_id": self.section_id,
            "title": self.title,
            "content": self.content,
            "citations": self.citations,
            "sources_used": self.sources_used,
            "word_count": self.word_count,
            "quality_score": self.quality_score,
            "reviewer_notes": self.reviewer_notes,
            "metadata": self.metadata,
        }


@dataclass
class WritingAgentResult:
    """Aggregated writing result for the entire draft."""

    outline: List[SectionOutline]
    sections: List[SectionDraft]
    total_word_count: int
    bibliography: List[str]
    style_guidelines: List[str]
    overall_strategy: str
    executive_summary: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "outline": [item.to_dict() for item in self.outline],
            "sections": [section.to_dict() for section in self.sections],
            "total_word_count": self.total_word_count,
            "bibliography": self.bibliography,
            "style_guidelines": self.style_guidelines,
            "overall_strategy": self.overall_strategy,
            "executive_summary": self.executive_summary,
            "metadata": self.metadata,
        }


class WritingAgent:
    """Generates a research-aligned academic draft."""

    OUTLINE_PROMPT = textwrap.dedent(
        """
        You are an award-winning academic writer. Design an outline that aligns
        with the research plan, leverages verified sources, and satisfies
        project requirements.

        Return JSON with this structure:
        {
          "overall_strategy": "string",
          "style_guidelines": ["string"],
          "sections": [
            {
              "section_id": "S1",
              "title": "string",
              "objective": "string",
              "target_word_count": 500,
              "key_points": ["string"],
              "source_ids": ["SRC-1"],
              "dependencies": ["S0"]
            }
          ]
        }
        """
    ).strip()

    SECTION_PROMPT = textwrap.dedent(
        """
        You are writing a section of an academic document. Stay faithful to the
        outline objective, weave in the designated sources, and produce
        well-structured paragraphs with inline citation markers such as
        (Author, Year) or numeric placeholders.

        Return JSON with this structure:
        {
          "content": "string",
          "citations": ["(Author, Year)"],
          "sources_used": ["SRC-1"],
          "word_count": 500,
          "quality_score": 0.0-1.0,
          "reviewer_notes": ["string"],
          "next_actions": ["string"]
        }
        """
    ).strip()

    REVIEW_PROMPT = textwrap.dedent(
        """
        You are a senior editor. Review the assembled draft for coherence and
        produce an executive summary plus key editorial notes. Highlight gaps or
        sections that need expansion.

        Return JSON with this structure:
        {
          "executive_summary": "string",
          "editorial_notes": ["string"],
          "risk_flags": ["string"],
          "estimated_quality": 0.0-1.0
        }
        """
    ).strip()

    def __init__(self, config: Optional[ProwziConfig] = None):
        self.config = config or get_config()
        self.agent_config = self.config.agents["writing"]
        self.model_config = self.config.get_model_for_agent("writing")

        self.chat_client = OpenAIChatClient(
            api_key=self.config.openrouter_api_key,
            base_url=self.config.openrouter_base_url,
            model_id=self.model_config.name,
            # NOTE: temperature and max_tokens not supported by OpenAIChatClient init
            # These should be passed in ChatAgent.run() execution_settings instead
        )

        self.outline_agent = ChatAgent(
            chat_client=self.chat_client,
            instructions=self.OUTLINE_PROMPT,
        )
        self.section_agent = ChatAgent(
            chat_client=self.chat_client,
            instructions=self.SECTION_PROMPT,
        )
        self.review_agent = ChatAgent(
            chat_client=self.chat_client,
            instructions=self.REVIEW_PROMPT,
        )

    async def generate_document(
        self,
        intent: IntentAnalysis,
        plan: ResearchPlan,
        verification: VerificationAgentResult,
        max_sections: int = MAX_SECTIONS_DEFAULT,
    ) -> WritingAgentResult:
        """Create a full academic draft."""
        accepted_sources = [
            record for record in verification.verified_sources if record.verdict == "use"
        ]
        if not accepted_sources:
            raise ValueError("Verification results contain no accepted sources for writing")

        source_catalog = self._build_source_catalog(accepted_sources)
        outline_payload = await self._generate_outline(
            intent=intent,
            plan=plan,
            sources=source_catalog,
            max_sections=max_sections,
        )
        outline = outline_payload.get("sections", [])
        style_guidelines = outline_payload.get("style_guidelines", [])
        overall_strategy = outline_payload.get("overall_strategy", "")

        section_drafts: List[SectionDraft] = []
        for outline_entry in outline:
            draft = await self._draft_section(
                intent=intent,
                plan=plan,
                outline=outline_entry,
                source_catalog=source_catalog,
            )
            section_drafts.append(draft)

        review = await self._review_document(section_drafts, style_guidelines)
        bibliography = self._generate_bibliography(source_catalog)
        total_word_count = sum(section.word_count for section in section_drafts)

        metadata = {
            "model": self.model_config.name,
            "sections": len(section_drafts),
            "style_guidelines": len(style_guidelines),
            "quality_estimate": review.get("estimated_quality"),
            "risk_flags": review.get("risk_flags", []),
        }

        return WritingAgentResult(
            outline=[self._dict_to_outline(item) for item in outline],
            sections=section_drafts,
            total_word_count=total_word_count,
            bibliography=bibliography,
            style_guidelines=style_guidelines,
            overall_strategy=overall_strategy,
            executive_summary=review.get("executive_summary", ""),
            metadata=metadata,
        )

    async def _generate_outline(
        self,
        intent: IntentAnalysis,
        plan: ResearchPlan,
        sources: Dict[str, SourceVerification],
        max_sections: int,
    ) -> Dict[str, Any]:
        context = self._build_outline_context(intent, plan, sources, max_sections)
        try:
            response = await self.outline_agent.run(context)
            data = self._extract_json(response.response)
            sections = data.get("sections", [])[:max_sections]
            if not sections:
                raise ValueError("Outline response missing sections")
            data["sections"] = sections
            return data
        except Exception as exc:  # noqa: BLE001
            logger.warning("Outline generation failed; using heuristic outline: %s", exc)
            return self._fallback_outline(intent, plan, sources, max_sections)

    async def _draft_section(
        self,
        intent: IntentAnalysis,
        plan: ResearchPlan,
        outline: Dict[str, Any],
        source_catalog: Dict[str, SourceVerification],
    ) -> SectionDraft:
        context = self._build_section_context(intent, plan, outline, source_catalog)
        try:
            response = await self.section_agent.run(context)
            data = self._extract_json(response.response)
            content = data.get("content", "").strip()
            if not content:
                raise ValueError("Section draft missing content")
            citations = self._ensure_list(data.get("citations"))
            sources_used = self._ensure_list(data.get("sources_used"))
            word_count = int(data.get("word_count", self._estimate_word_count(content)))
            quality = float(data.get("quality_score", 0.7))
            notes = self._ensure_list(data.get("reviewer_notes"))
            metadata = {
                "mode": "llm",
                "next_actions": self._ensure_list(data.get("next_actions")),
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Section draft failed; applying heuristic fallback for %s: %s", outline.get("title"), exc)
            content, citations = self._fallback_section(outline, source_catalog)
            sources_used = outline.get("source_ids", [])
            word_count = self._estimate_word_count(content)
            quality = 0.55
            notes = ["Manual expansion recommended due to fallback drafting."]
            metadata = {"mode": "heuristic", "error": str(exc)}

        return SectionDraft(
            section_id=str(outline.get("section_id", "UNKNOWN")),
            title=str(outline.get("title", "Untitled Section")),
            content=content,
            citations=citations,
            sources_used=sources_used,
            word_count=word_count,
            quality_score=max(0.0, min(1.0, quality)),
            reviewer_notes=notes,
            metadata=metadata,
        )

    async def _review_document(
        self,
        sections: Sequence[SectionDraft],
        style_guidelines: Sequence[str],
    ) -> Dict[str, Any]:
        if not sections:
            return {}

        context = self._build_review_context(sections, style_guidelines)
        try:
            response = await self.review_agent.run(context)
            return self._extract_json(response.response)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Document review failed; returning heuristic summary: %s", exc)
            summary = "\n\n".join(section.content[:200] for section in sections[:2])
            return {
                "executive_summary": summary or "Draft generated; human review advised.",
                "editorial_notes": ["Unable to run automated review."],
                "risk_flags": [str(exc)],
                "estimated_quality": 0.5,
            }

    def _build_outline_context(
        self,
        intent: IntentAnalysis,
        plan: ResearchPlan,
        sources: Dict[str, SourceVerification],
        max_sections: int,
    ) -> str:
        source_lines = []
        for source_id, verification in list(sources.items())[:20]:
            result = verification.source
            source_lines.append(
                textwrap.dedent(
                    f"""
                    {source_id}:
                      Title: {result.title}
                      URL: {result.url}
                      Query: {verification.query}
                      Rationale: {result.metadata.get('relevance_reason', 'n/a')}
                      Credibility: {verification.credibility}/30
                    """
                ).strip()
            )

        plan_summary = self._summarize_plan(plan.task_hierarchy, level=0)
        coverage = ", ".join(plan.metadata.get("coverage_gaps", [])) if plan.metadata else "Unknown"

        context = textwrap.dedent(
            f"""
            Project Brief:
              Document Type: {intent.document_type}
              Field: {intent.field}
              Academic Level: {intent.academic_level}
              Target Word Count: {intent.word_count}
              Explicit Requirements: {', '.join(intent.explicit_requirements[:5]) or 'None'}
              Implicit Requirements: {', '.join(intent.implicit_requirements[:5]) or 'None'}
              Outstanding Questions: {', '.join(intent.missing_info[:5]) or 'None'}

            Research Plan Summary:
            {plan_summary}

            Verified Sources (top {min(len(source_lines), 20)} of {len(sources)}):
            """ + textwrap.indent('\n\n'.join(source_lines) or 'None', '  ') + """

            Guidance:
              - Max Sections: {max_sections}
              - Known Coverage Gaps: {coverage}
            """
        ).strip()
        return context

    def _build_section_context(
        self,
        intent: IntentAnalysis,
        plan: ResearchPlan,
        outline: Dict[str, Any],
        source_catalog: Dict[str, SourceVerification],
    ) -> str:
        section_id = outline.get("section_id", "S?")
        source_details = []
        for source_id in outline.get("source_ids", [])[:6]:
            verification = source_catalog.get(source_id)
            if not verification:
                continue
            result = verification.source
            snippet = result.content or result.metadata.get("summary") or ""
            snippet = snippet.strip().replace("\r", " ")
            if len(snippet) > 600:
                snippet = f"{snippet[:600]}..."
            source_details.append(
                textwrap.dedent(
                    f"""
                    {source_id}:
                      Title: {result.title}
                      URL: {result.url}
                      Venue: {result.venue or 'Unknown'}
                      Publication Date: {result.publication_date or 'Unknown'}
                      Summary: {snippet or 'No summary available.'}
                    """
                ).strip()
            )

        task_trace = self._find_task_for_section(plan.task_hierarchy, section_id)
        task_context = task_trace[-1] if task_trace else None

        context = textwrap.dedent(
            f"""
            Section Brief:
              Section ID: {section_id}
              Title: {outline.get('title')}
              Objective: {outline.get('objective')}
              Target Word Count: {outline.get('target_word_count')}
              Key Points: {', '.join(outline.get('key_points', [])) or 'Ensure logical flow.'}
              Dependencies: {', '.join(outline.get('dependencies', [])) or 'None'}

            Task Context:
              {task_context.description if task_context else 'General section drafting'}

            Audience & Tone:
              Academic Level: {intent.academic_level}
              Document Type: {intent.document_type}
              Required Style: {', '.join(intent.explicit_requirements[:3]) or 'Academic formal'}

            Approved Sources:
            """ + textwrap.indent('\n\n'.join(source_details) or 'None provided. Use caution.', '  ') + """

            Instructions:
              - Integrate sources faithfully with inline markers.
              - Maintain coherent paragraph transitions.
              - Flag uncertainties in reviewer notes.
            """
        ).strip()
        return context

    def _build_review_context(
        self,
        sections: Sequence[SectionDraft],
        style_guidelines: Sequence[str],
    ) -> str:
        section_summaries = []
        for section in sections:
            preview = section.content[:800].replace("\n", " ").strip()
            section_summaries.append(
                textwrap.dedent(
                    f"""
                    Section {section.section_id} - {section.title}
                      Word Count: {section.word_count}
                      Quality Score: {section.quality_score}
                      Summary: {preview}
                      Notes: {', '.join(section.reviewer_notes) or 'None'}
                    """
                ).strip()
            )

        sections_text = textwrap.indent('\n\n'.join(section_summaries) or 'No sections generated.', '  ')
        guidelines_text = textwrap.indent('\n'.join(style_guidelines) or 'No specific style directives.', '  ')
        context = textwrap.dedent(
            f"""
            Draft Overview:
            {sections_text}

            Style Guidelines:
            {guidelines_text}
            """
        ).strip()
        return context

    def _build_source_catalog(
        self,
        accepted_sources: Sequence[SourceVerification],
    ) -> Dict[str, SourceVerification]:
        catalog: Dict[str, SourceVerification] = {}
        for index, record in enumerate(accepted_sources, start=1):
            catalog[f"SRC-{index}"] = record
        return catalog

    def _generate_bibliography(
        self,
        source_catalog: Dict[str, SourceVerification],
    ) -> List[str]:
        bibliography: List[str] = []
        for source_id, verification in source_catalog.items():
            result = verification.source
            author = result.author or "Unknown Author"
            year = self._extract_year(result.publication_date) or "n.d."
            title = result.title or "Untitled"
            venue = result.venue or "Unknown Venue"
            bibliography.append(f"{author} ({year}). {title}. {venue}. {result.url}")
        return bibliography

    def _fallback_outline(
        self,
        intent: IntentAnalysis,
        plan: ResearchPlan,
        sources: Dict[str, SourceVerification],
        max_sections: int,
    ) -> Dict[str, Any]:
        tasks = self._collect_primary_tasks(plan.task_hierarchy)
        sections: List[Dict[str, Any]] = []
        for index, task in enumerate(tasks[:max_sections], start=1):
            section_id = f"S{index}"
            source_ids = list(sources.keys())[ (index - 1) :: max(len(tasks), 1) ][:3]
            sections.append(
                {
                    "section_id": section_id,
                    "title": task.name or f"Section {index}",
                    "objective": task.description or "Expand on the task objectives.",
                    "target_word_count": max(int(intent.word_count / max_sections * SECTION_WORD_BUFFER), 400),
                    "key_points": [point for point in task.metadata.get("key_points", [])][:4],
                    "source_ids": source_ids,
                    "dependencies": task.depends_on,
                }
            )

        return {
            "overall_strategy": "Generated via heuristic fallback; ensure manual review.",
            "style_guidelines": intent.explicit_requirements[:5],
            "sections": sections or [
                {
                    "section_id": "S1",
                    "title": "Introduction",
                    "objective": "Introduce the topic and research goals.",
                    "target_word_count": max(int(intent.word_count * SECTION_WORD_BUFFER), 500),
                    "key_points": ["Establish context", "Present thesis"],
                    "source_ids": list(sources.keys())[:3],
                    "dependencies": [],
                }
            ],
        }

    def _fallback_section(
        self,
        outline: Dict[str, Any],
        source_catalog: Dict[str, SourceVerification],
    ) -> tuple[str, List[str]]:
        title = outline.get("title", "Section")
        objective = outline.get("objective", "Explain key concepts.")
        key_points = outline.get("key_points", [])
        paragraphs = [f"{title}: {objective}"]
        for point in key_points[:3]:
            paragraphs.append(f"- {point}")
        citations = []
        for source_id in outline.get("source_ids", [])[:3]:
            verification = source_catalog.get(source_id)
            if not verification:
                continue
            citations.append(f"({verification.source.author or 'Unknown'}, {self._extract_year(verification.source.publication_date) or 'n.d.'})")
        content = "\n".join(paragraphs)
        return content, citations

    def _find_task_for_section(
        self,
        root: Task,
        section_id: str,
    ) -> List[Task]:
        path: List[Task] = []

        def traverse(task: Task, trail: List[Task]) -> Optional[List[Task]]:
            updated_trail = trail + [task]
            if task.metadata.get("section_id") == section_id:
                return updated_trail
            for subtask in task.subtasks:
                matched = traverse(subtask, updated_trail)
                if matched:
                    return matched
            return None

        result = traverse(root, [])
        return result or []

    def _collect_primary_tasks(self, task: Task) -> List[Task]:
        tasks = [task]
        tasks.extend(task.subtasks)
        return tasks

    def _summarize_plan(self, task: Task, level: int) -> str:
        indent = "  " * level
        summary = f"{indent}- {task.name} [{task.priority.value}]"
        if task.description:
            summary += f": {task.description[:120]}"
        child_summaries = [self._summarize_plan(child, level + 1) for child in task.subtasks]
        return "\n".join([summary, *child_summaries]) if child_summaries else summary

    def _dict_to_outline(self, entry: Dict[str, Any]) -> SectionOutline:
        return SectionOutline(
            section_id=str(entry.get("section_id", "")),
            title=str(entry.get("title", "")),
            objective=str(entry.get("objective", "")),
            target_word_count=int(entry.get("target_word_count", 0)),
            key_points=[str(item) for item in entry.get("key_points", [])],
            source_ids=[str(item) for item in entry.get("source_ids", [])],
            dependencies=[str(item) for item in entry.get("dependencies", [])],
        )

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

    @staticmethod
    def _ensure_list(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if item]
        return [str(value).strip()]

    @staticmethod
    def _estimate_word_count(text: str) -> int:
        tokens = [token for token in text.split() if token]
        return len(tokens)

    @staticmethod
    def _extract_year(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        match = re.search(r"(19|20)\d{2}", value)
        if match:
            return match.group(0)
        return None
