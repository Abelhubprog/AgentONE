"""
Verification Agent

Performs credibility and accuracy assessment on search results prior to
writing. Uses Claude 4.5 Sonnet (via OpenRouter) with heuristic fallbacks.
"""

from __future__ import annotations

import json
import logging
import re
import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient

from prowzi.agents.intent_agent import IntentAnalysis
from prowzi.agents.planning_agent import ResearchPlan
from prowzi.agents.search_agent import QueryResultSummary, SearchAgentResult
from prowzi.config import ProwziConfig, get_config
from prowzi.tools.search_tools import SearchResult, SourceType

logger = logging.getLogger(__name__)

CONTENT_SNIPPET_CHARS = 1200
MAX_SOURCES_DEFAULT = 24
BATCH_SIZE = 8


@dataclass
class SourceVerification:
    """Verification details for a single source."""

    source: SearchResult
    query: str
    query_type: str
    priority: str
    credibility: int
    accuracy: int
    recency: int
    relevance: int
    bias: int
    overall_score: float
    verdict: str
    confidence: str
    concerns: List[str]
    follow_up_actions: List[str]
    supporting_evidence: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source.to_dict(),
            "query": self.query,
            "query_type": self.query_type,
            "priority": self.priority,
            "credibility": self.credibility,
            "accuracy": self.accuracy,
            "recency": self.recency,
            "relevance": self.relevance,
            "bias": self.bias,
            "overall_score": self.overall_score,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "concerns": self.concerns,
            "follow_up_actions": self.follow_up_actions,
            "supporting_evidence": self.supporting_evidence,
            "metadata": self.metadata,
        }


@dataclass
class VerificationAgentResult:
    """Aggregated verification analysis for all candidate sources."""

    verified_sources: List[SourceVerification]
    average_score: float
    accepted_sources: List[str]
    rejected_sources: List[str]
    high_risk_sources: List[str]
    analyst_summary: str
    risk_flags: List[str]
    recommended_next_steps: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verified_sources": [item.to_dict() for item in self.verified_sources],
            "average_score": self.average_score,
            "accepted_sources": self.accepted_sources,
            "rejected_sources": self.rejected_sources,
            "high_risk_sources": self.high_risk_sources,
            "analyst_summary": self.analyst_summary,
            "risk_flags": self.risk_flags,
            "recommended_next_steps": self.recommended_next_steps,
            "metadata": self.metadata,
        }


@dataclass
class _SourceCandidate:
    candidate_id: int
    query_summary: QueryResultSummary
    result: SearchResult


class VerificationAgent:
    """Assess search results for credibility, accuracy, and bias."""

    VERIFICATION_PROMPT = textwrap.dedent(
        """
        You are a meticulous academic verification specialist. Evaluate sources
        against a rigorous rubric, considering credibility, factual accuracy,
        recency, topical relevance, and potential bias. Highlight risks and make
        clear recommendations on whether to trust, further review, or reject
        each source. Base decisions strictly on provided information.
        """
    ).strip()

    JSON_RESPONSE_SPEC = textwrap.dedent(
        """
        Return JSON with this exact structure:
        {
          "batch_summary": "string",
          "sources": [
            {
              "source_id": <int matching the Source ID>,
              "verdict": "use" | "review" | "reject",
              "credibility": 0-30,
              "accuracy": 0-25,
              "recency": 0-15,
              "relevance": 0-20,
              "bias": 0-10,
              "overall_score": 0-100,
              "confidence": "low" | "medium" | "high",
              "concerns": ["string"],
              "follow_up_actions": ["string"],
              "supporting_evidence": ["string"]
            }
          ],
          "risk_flags": ["string"],
          "recommended_next_steps": ["string"]
        }
        """
    ).strip()

    def __init__(self, config: Optional[ProwziConfig] = None):
        self.config = config or get_config()
        self.agent_config = self.config.agents["verification"]
        self.model_config = self.config.get_model_for_agent("verification")

        self.chat_client = OpenAIChatClient(
            api_key=self.config.openrouter_api_key,
            base_url=self.config.openrouter_base_url,
            model_id=self.model_config.name,
            # NOTE: temperature and max_tokens not supported by OpenAIChatClient init
            # These should be passed in ChatAgent.run() execution_settings instead
        )

        self.verification_agent = ChatAgent(
            chat_client=self.chat_client,
            instructions=self.VERIFICATION_PROMPT,
        )

    async def verify_sources(
        self,
        intent: IntentAnalysis,
        search_results: SearchAgentResult,
        plan: Optional[ResearchPlan] = None,
        max_sources: int = MAX_SOURCES_DEFAULT,
    ) -> VerificationAgentResult:
        """
        Run credibility and accuracy checks on search results.

        Args:
            intent: Parsed intent analysis
            search_results: Aggregated search agent output
            plan: Optional research plan for additional context
            max_sources: Max sources to evaluate across all queries

        Returns:
            Structured verification analysis
        """
        candidates = self._select_candidates(search_results, max_sources)
        if not candidates:
            raise ValueError("No search results provided for verification")

        verified: List[SourceVerification] = []
        summaries: List[str] = []
        risk_flags: List[str] = []
        recommendations: List[str] = []
        llm_batches = 0
        fallback_batches = 0

        for batch in self._chunk_candidates(candidates, BATCH_SIZE):
            batch_result, batch_summary, batch_flags, batch_recs, mode = await self._process_batch(
                intent=intent,
                plan=plan,
                batch=batch,
                coverage_gaps=search_results.coverage_gaps,
            )
            verified.extend(batch_result)
            if batch_summary:
                summaries.append(batch_summary)
            risk_flags.extend(batch_flags)
            recommendations.extend(batch_recs)
            if mode == "llm":
                llm_batches += 1
            else:
                fallback_batches += 1

        average_score = 0.0
        if verified:
            average_score = sum(item.overall_score for item in verified) / len(verified)

        accepted = [item.source.url for item in verified if item.verdict == "use"]
        rejected = [item.source.url for item in verified if item.verdict == "reject"]
        high_risk = [
            item.source.url
            for item in verified
            if item.verdict != "use" or item.overall_score < 60
        ]

        accepted = list(dict.fromkeys(accepted))
        rejected = list(dict.fromkeys(rejected))
        high_risk = list(dict.fromkeys(high_risk))

        analyst_summary = " ".join(summaries).strip()
        risk_flags = sorted({flag for flag in risk_flags if flag})
        recommendations = sorted({rec for rec in recommendations if rec})

        metadata = {
            "model": self.model_config.name,
            "batches": llm_batches + fallback_batches,
            "llm_batches": llm_batches,
            "fallback_batches": fallback_batches,
            "processed_sources": len(verified),
            "mode": (
                "llm"
                if fallback_batches == 0
                else ("heuristic" if llm_batches == 0 else "mixed")
            ),
        }

        return VerificationAgentResult(
            verified_sources=verified,
            average_score=average_score,
            accepted_sources=accepted,
            rejected_sources=rejected,
            high_risk_sources=high_risk,
            analyst_summary=analyst_summary,
            risk_flags=risk_flags,
            recommended_next_steps=recommendations,
            metadata=metadata,
        )

    def _select_candidates(
        self,
        search_results: SearchAgentResult,
        max_sources: int,
    ) -> List[_SourceCandidate]:
        candidates: List[_SourceCandidate] = []
        candidate_id = 1
        for summary in search_results.query_summaries:
            for result in summary.results:
                candidates.append(
                    _SourceCandidate(
                        candidate_id=candidate_id,
                        query_summary=summary,
                        result=result,
                    )
                )
                candidate_id += 1

        candidates.sort(
            key=lambda item: item.result.relevance_score if item.result.relevance_score else 0.0,
            reverse=True,
        )

        if max_sources and max_sources > 0:
            candidates = candidates[:max_sources]

        return candidates

    async def _process_batch(
        self,
        intent: IntentAnalysis,
        plan: Optional[ResearchPlan],
        batch: Sequence[_SourceCandidate],
        coverage_gaps: Sequence[str],
    ) -> tuple[List[SourceVerification], str, List[str], List[str], str]:
        prompt = self._build_batch_prompt(intent, plan, batch, coverage_gaps)
        try:
            response = await self.verification_agent.run(prompt)
            data = self._extract_json(response.response)
            verifications = self._build_verifications_from_llm(batch, data)
            if not verifications:
                raise ValueError("LLM response contained no source assessments")
            summary = data.get("batch_summary", "") or data.get("analyst_summary", "")
            risk_flags = self._ensure_list(data.get("risk_flags"))
            recommendations = self._ensure_list(data.get("recommended_next_steps"))
            return verifications, summary, risk_flags, recommendations, "llm"
        except Exception as exc:  # noqa: BLE001
            logger.warning("Verification batch failed; reverting to heuristic scoring: %s", exc)
            verifications = [self._heuristic_evaluate(candidate) for candidate in batch]
            summary = "LLM verification unavailable. Applied heuristic evaluation based on metadata."
            risk_flags = [f"LLM verification failed: {exc}"]
            recommendations = ["Retry automated verification when LLM service recovers."]
            return verifications, summary, risk_flags, recommendations, "heuristic"

    def _build_verifications_from_llm(
        self,
        batch: Sequence[_SourceCandidate],
        data: Dict[str, Any],
    ) -> List[SourceVerification]:
        candidate_map = {candidate.candidate_id: candidate for candidate in batch}
        handled_ids = set()
        verifications: List[SourceVerification] = []

        for item in data.get("sources", []):
            source_id = item.get("source_id") or item.get("index")
            if source_id is None:
                continue
            candidate = candidate_map.get(source_id)
            if not candidate:
                continue
            verifications.append(self._build_llm_verification(candidate, item))
            handled_ids.add(source_id)

        for candidate in batch:
            if candidate.candidate_id not in handled_ids:
                verifications.append(self._heuristic_evaluate(candidate))

        return verifications

    def _build_llm_verification(
        self,
        candidate: _SourceCandidate,
        item: Dict[str, Any],
    ) -> SourceVerification:
        credibility = self._clamp_int(item.get("credibility", 0), 0, 30)
        accuracy = self._clamp_int(item.get("accuracy", 0), 0, 25)
        recency = self._clamp_int(item.get("recency", 0), 0, 15)
        relevance = self._clamp_int(item.get("relevance", 0), 0, 20)
        bias = self._clamp_int(item.get("bias", 0), 0, 10)
        overall = float(item.get("overall_score", credibility + accuracy + recency + relevance + bias))
        verdict = str(item.get("verdict", "review")).lower()
        confidence = str(item.get("confidence", "medium"))

        concerns = self._ensure_list(item.get("concerns"))
        follow_up = self._ensure_list(item.get("follow_up_actions"))
        evidence = self._ensure_list(item.get("supporting_evidence"))

        metadata = {
            "mode": "llm",
            "confidence": confidence,
            "flags": self._ensure_list(item.get("flags")),
            "source_id": candidate.candidate_id,
        }

        return SourceVerification(
            source=candidate.result,
            query=candidate.query_summary.query.query,
            query_type=candidate.query_summary.query.query_type.value,
            priority=candidate.query_summary.query.priority.value,
            credibility=credibility,
            accuracy=accuracy,
            recency=recency,
            relevance=relevance,
            bias=bias,
            overall_score=overall,
            verdict=verdict,
            confidence=confidence,
            concerns=concerns,
            follow_up_actions=follow_up,
            supporting_evidence=evidence,
            metadata=metadata,
        )

    def _heuristic_evaluate(self, candidate: _SourceCandidate) -> SourceVerification:
        result = candidate.result
        query = candidate.query_summary.query

        citation_count = result.citation_count or 0
        is_academic = result.source_type in {SourceType.ACADEMIC_PAPER, SourceType.PREPRINT}
        credibility_base = 12 if is_academic else 8
        credibility = credibility_base + min(12, citation_count // 10 * 3)
        if result.venue:
            credibility += 3
        credibility = self._clamp_int(credibility, 6, 30)

        accuracy = 12 + min(8, citation_count // 15 * 2)
        if result.source_type in {SourceType.BLOG, SourceType.NEWS}:
            accuracy -= 4
        accuracy = self._clamp_int(accuracy, 6, 25)

        recency = 10
        year = self._extract_year(result.publication_date)
        if year:
            current_year = datetime.utcnow().year
            age = max(0, current_year - year)
            if age <= 1:
                recency = 15
            elif age <= 3:
                recency = 12
            elif age <= 5:
                recency = 9
            elif age <= 10:
                recency = 7
            else:
                recency = 5
        recency = self._clamp_int(recency, 3, 15)

        relevance = int(round((result.relevance_score or 0.0) * 20))
        relevance = self._clamp_int(relevance, 4, 20)

        bias = 9
        if result.source_type in {SourceType.BLOG, SourceType.NEWS}:
            bias = 7
        elif result.source_type == SourceType.WEB_ARTICLE:
            bias = 8
        bias = self._clamp_int(bias, 4, 10)

        overall = float(credibility + accuracy + recency + relevance + bias)

        concerns: List[str] = []
        follow_up: List[str] = []
        if credibility < 14:
            concerns.append("Low credibility due to limited citations or venue uncertainty.")
            follow_up.append("Locate peer-reviewed sources to confirm key claims.")
        if recency < 8:
            msg = "Potentially outdated source; verify with newer research."
            concerns.append(msg)
            follow_up.append("Search for recent publications covering the same topic.")
        if relevance < 10:
            concerns.append("Limited alignment with the stated research query.")
        if result.source_type in {SourceType.BLOG, SourceType.NEWS}:
            concerns.append("Non-academic publication; validate factual statements.")

        verdict = "use"
        if overall < 55 or credibility < 12:
            verdict = "reject"
        elif overall < 75 or recency < 8:
            verdict = "review"

        evidence = [
            f"Heuristic evaluation based on metadata. Relevance score: {result.relevance_score:.2f}",
        ]

        metadata = {
            "mode": "heuristic",
            "source_id": candidate.candidate_id,
        }

        return SourceVerification(
            source=result,
            query=query.query,
            query_type=query.query_type.value,
            priority=query.priority.value,
            credibility=credibility,
            accuracy=accuracy,
            recency=recency,
            relevance=relevance,
            bias=bias,
            overall_score=overall,
            verdict=verdict,
            confidence="low",
            concerns=concerns,
            follow_up_actions=follow_up,
            supporting_evidence=evidence,
            metadata=metadata,
        )

    def _build_batch_prompt(
        self,
        intent: IntentAnalysis,
        plan: Optional[ResearchPlan],
        batch: Sequence[_SourceCandidate],
        coverage_gaps: Sequence[str],
    ) -> str:
        explicit = ", ".join(intent.explicit_requirements[:5]) if intent.explicit_requirements else "None"
        implicit = ", ".join(intent.implicit_requirements[:3]) if intent.implicit_requirements else "None"
        missing = ", ".join(intent.missing_info[:3]) if intent.missing_info else "None"
        categories = sorted({candidate.query_summary.query.category for candidate in batch if candidate.query_summary.query.category})
        categories_str = ", ".join(categories) if categories else "General"
        gaps_str = ", ".join(coverage_gaps) if coverage_gaps else "None reported"

        plan_hint = ""
        if plan is not None:
            plan_hint = textwrap.dedent(
                f"""
                Workflow Highlights:
                - Total tasks: {len(plan.execution_order)}
                - Quality checkpoints: {len(plan.quality_checkpoints)}
                - Contingencies planned: {len(plan.contingencies)}
                """
            ).strip()

        source_blocks = []
        for candidate in batch:
            result = candidate.result
            query = candidate.query_summary.query
            snippet = result.content or result.metadata.get("summary") or ""
            snippet = snippet.replace("\r", " \n").strip()
            if len(snippet) > CONTENT_SNIPPET_CHARS:
                snippet = f"{snippet[:CONTENT_SNIPPET_CHARS]}..."
            snippet = snippet or "No extracted snippet available."
            snippet = textwrap.indent(snippet, "    ")

            block = textwrap.dedent(
                f"""
                Source {candidate.candidate_id}:
                  Query: {query.query}
                  Query Type: {query.query_type.value}
                  Priority: {query.priority.value}
                  Category: {query.category}
                  Estimated Sources: {query.estimated_sources}
                  Keywords: {', '.join(query.keywords) if query.keywords else 'None'}
                  Title: {result.title}
                  URL: {result.url}
                  Source Type: {result.source_type.value}
                  Publication Date: {result.publication_date or 'Unknown'}
                  Citation Count: {result.citation_count or 0}
                  Venue: {result.venue or 'Unknown'}
                  Existing LLM Notes: {result.metadata.get('relevance_reason', 'n/a')}
                  Relevance Score: {round((result.relevance_score or 0.0) * 100, 2)}
                  Snippet:\n{snippet}
                """
            ).strip()
            source_blocks.append(block)

        context_header = textwrap.dedent(
            f"""
            Project Context:
            - Document Type: {intent.document_type}
            - Field: {intent.field}
            - Academic Level: {intent.academic_level}
            - Target Word Count: {intent.word_count}
            - Explicit Requirements: {explicit}
            - Implicit Requirements: {implicit}
            - Outstanding Questions: {missing}
            - Query Categories in Batch: {categories_str}
            - Known Coverage Gaps: {gaps_str}
            """
        ).strip()

        if plan_hint:
            context_header = f"{context_header}\n{plan_hint}"

        sources_section = "\n\n".join(source_blocks)

        prompt = (
            f"{context_header}\n\nEvaluate the following sources using the provided rubric."
            f"\n\n{sources_section}\n\n{self.JSON_RESPONSE_SPEC}"
        )
        return prompt

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
    def _chunk_candidates(
        candidates: Sequence[_SourceCandidate],
        size: int,
    ) -> Iterable[List[_SourceCandidate]]:
        chunk: List[_SourceCandidate] = []
        for candidate in candidates:
            chunk.append(candidate)
            if len(chunk) == size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk

    @staticmethod
    def _ensure_list(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if item]
        return [str(value)]

    @staticmethod
    def _extract_year(value: Optional[str]) -> Optional[int]:
        if not value:
            return None
        match = re.search(r"(19|20)\d{2}", value)
        if match:
            try:
                return int(match.group(0))
            except ValueError:
                return None
        return None

    @staticmethod
    def _clamp_int(value: Any, minimum: int, maximum: int) -> int:
        try:
            integer = int(value)
        except (TypeError, ValueError):
            integer = minimum
        return max(minimum, min(maximum, integer))
