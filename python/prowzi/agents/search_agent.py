"""
Search Agent

Executes multi-engine searches based on the research plan and scores relevance
using Gemini Flash (via OpenRouter). Aggregates, filters, and annotates results
for downstream verification and writing agents.
"""

from __future__ import annotations

import json
import logging
import re
import textwrap
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient

from prowzi.agents.intent_agent import IntentAnalysis
from prowzi.agents.planning_agent import ResearchPlan, SearchQuery
from prowzi.config import get_config, ProwziConfig
from prowzi.config.settings import SearchAPIConfig
from prowzi.tools.search_tools import (
    ArXivSearch,
    PerplexitySearch,
    PubMedSearch,
    SearchResult,
    SemanticScholarSearch,
    multi_engine_search,
)

logger = logging.getLogger(__name__)


MAX_RESULTS_PER_QUERY_DEFAULT = 25
MAX_RESULTS_FOR_SCORING = 20
SNIPPET_MAX_CHARS = 420


@dataclass
class QueryResultSummary:
    """Scored search results for a single query."""

    query: SearchQuery
    results: List[SearchResult]
    summary: str
    recommendations: List[str]
    coverage_gaps: List[str]
    engines_used: List[str]
    duration_seconds: float
    total_results: int
    filtered_out: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query.to_dict(),
            "results": [result.to_dict() for result in self.results],
            "summary": self.summary,
            "recommendations": self.recommendations,
            "coverage_gaps": self.coverage_gaps,
            "engines_used": self.engines_used,
            "duration_seconds": self.duration_seconds,
            "total_results": self.total_results,
            "filtered_out": self.filtered_out,
            "metadata": self.metadata,
        }


@dataclass
class SearchAgentResult:
    """Aggregated search execution result across all queries."""

    query_summaries: List[QueryResultSummary]
    total_results: int
    high_quality_results: int
    average_relevance: float
    coverage_gaps: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_summaries": [summary.to_dict() for summary in self.query_summaries],
            "total_results": self.total_results,
            "high_quality_results": self.high_quality_results,
            "average_relevance": self.average_relevance,
            "coverage_gaps": self.coverage_gaps,
            "metadata": self.metadata,
        }


class SearchAgent:
    """
    Executes the research plan's search queries across multiple engines,
    scores relevance, and prepares structured outputs for verification.
    """

    SCORING_PROMPT = textwrap.dedent(
        """
        You are a senior research librarian helping an autonomous agent select
        the best sources for an academic project.

        Requirements:
        - Score each source for relevance on a 0-100 scale
        - Provide a short reason (<=40 words) highlighting why the source is
          useful or why it should be discarded
        - Identify key concepts or terms that match the user's needs
        - Recommend how to use the source (e.g., background, methodology,
          statistic, case study, definition)
        - Flag concerns such as paywalls, low credibility, or outdated content

        Return JSON with this exact shape:
        {
          "query_focus": "string",
          "results": [
            {
              "index": 1,
              "url": "https://...",
              "relevance": 0-100,
              "confidence": "low" | "medium" | "high",
              "matched_terms": ["term"],
              "recommended_use": ["background", "methodology", "statistic", "case_study", "definition"],
              "reason": "string",
              "flags": ["string"]
            }
          ],
          "coverage_gaps": ["string"],
          "next_actions": ["string"],
          "summary": "string"
        }
        """
    ).strip()

    def __init__(self, config: Optional[ProwziConfig] = None):
        self.config = config or get_config()
        self.agent_config = self.config.agents["search"]
        self.model_config = self.config.get_model_for_agent("search")
        self.relevance_threshold = self.config.min_relevance_score

        self.chat_client = OpenAIChatClient(
            api_key=self.config.openrouter_api_key,
            base_url=self.config.openrouter_base_url,
            model_id=self.model_config.name,
            # NOTE: temperature and max_tokens not supported by OpenAIChatClient init
            # These should be passed in ChatAgent.run() execution_settings instead
        )

        self.scoring_agent = ChatAgent(
            chat_client=self.chat_client,
            instructions=self.SCORING_PROMPT,
        )

        self.engines, self.max_engine_results = self._initialize_engines()

    async def execute_plan(
        self,
        plan: ResearchPlan,
        intent: IntentAnalysis,
        max_results_per_query: int = MAX_RESULTS_PER_QUERY_DEFAULT,
    ) -> SearchAgentResult:
        """
        Execute search queries generated by the planning agent.

        Args:
            plan: Research plan with search queries
            intent: Parsed intent analysis
            max_results_per_query: Max combined results per query after filtering

        Returns:
            Aggregated search execution result
        """
        if not plan.search_queries:
            raise ValueError("Research plan contains no search queries")

        summaries: List[QueryResultSummary] = []
        for query in plan.search_queries:
            summary = await self._process_query(
                query=query,
                intent=intent,
                max_results_per_query=max_results_per_query,
            )
            summaries.append(summary)

        all_results = [result for summary in summaries for result in summary.results]
        raw_total = sum(summary.total_results for summary in summaries)
        high_quality = len(all_results)
        average_relevance = 0.0
        if all_results:
            average_relevance = sum(r.relevance_score for r in all_results) / len(all_results)

        coverage_gaps = sorted({gap for summary in summaries for gap in summary.coverage_gaps if gap})
        engines_used = sorted({engine for summary in summaries for engine in summary.engines_used})

        metadata = {
            "queries_processed": len(plan.search_queries),
            "engines_used": engines_used,
            "model": self.model_config.name,
            "threshold": self.relevance_threshold,
        }

        return SearchAgentResult(
            query_summaries=summaries,
            total_results=raw_total,
            high_quality_results=high_quality,
            average_relevance=average_relevance,
            coverage_gaps=coverage_gaps,
            metadata=metadata,
        )

    async def _process_query(
        self,
        query: SearchQuery,
        intent: IntentAnalysis,
        max_results_per_query: int,
    ) -> QueryResultSummary:
        start_time = time.perf_counter()
        per_engine_limit = min(self.max_engine_results, max_results_per_query)
        engines = [engine for _, engine, _ in self.engines]
        engine_names = [name for name, _, _ in self.engines]

        results = await multi_engine_search(
            query=query.query,
            engines=engines,
            max_results_per_engine=per_engine_limit,
            deduplicate=True,
        )

        if not results:
            duration = time.perf_counter() - start_time
            return QueryResultSummary(
                query=query,
                results=[],
                summary="No sources found. Consider broadening the query.",
                recommendations=["Broaden the query or adjust keywords."],
                coverage_gaps=["No results returned across engines"],
                engines_used=engine_names,
                duration_seconds=duration,
                total_results=0,
                filtered_out=0,
                metadata={"scoring": {"mode": "none"}},
            )

        scored_results, summary, recommendations, coverage_gaps, scoring_meta = await self._score_results(
            query=query,
            intent=intent,
            results=results,
        )

        scored_results.sort(key=lambda r: r.relevance_score, reverse=True)
        filtered = [r for r in scored_results if r.relevance_score >= self.relevance_threshold]
        if max_results_per_query:
            filtered = filtered[:max_results_per_query]

        discarded = len(results) - len(filtered)
        duration = time.perf_counter() - start_time

        return QueryResultSummary(
            query=query,
            results=filtered,
            summary=summary,
            recommendations=recommendations,
            coverage_gaps=coverage_gaps,
            engines_used=engine_names,
            duration_seconds=duration,
            total_results=len(results),
            filtered_out=discarded,
            metadata={"scoring": scoring_meta},
        )

    async def _score_results(
        self,
        query: SearchQuery,
        intent: IntentAnalysis,
        results: List[SearchResult],
    ) -> Tuple[List[SearchResult], str, List[str], List[str], Dict[str, Any]]:
        payload = self._prepare_scoring_payload(query, intent, results)
        prompt = self._build_scoring_prompt(intent, query, payload)

        try:
            response = await self.scoring_agent.run(prompt)
            data = self._extract_json(response.response)
            scored_results = self._apply_llm_scores(query, results, data)
            summary = data.get("summary", "") or "Relevance scores generated via LLM."
            recommendations = data.get("next_actions", [])
            coverage_gaps = data.get("coverage_gaps", [])
            metadata = {
                "mode": "llm",
                "query_focus": data.get("query_focus"),
                "model": self.model_config.name,
            }
            return scored_results, summary, recommendations, coverage_gaps, metadata
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM scoring failed: %s", exc)
            for result in results:
                self._apply_heuristic_score(query, result)
            summary = "LLM scoring unavailable. Applied heuristic scoring based on recency and citations."
            recommendations = ["Retry LLM scoring when service is available."]
            coverage_gaps = []
            metadata = {
                "mode": "heuristic",
                "error": str(exc),
                "model": self.model_config.name,
            }
            return results, summary, recommendations, coverage_gaps, metadata

    def _prepare_scoring_payload(
        self,
        query: SearchQuery,
        intent: IntentAnalysis,
        results: List[SearchResult],
    ) -> List[Dict[str, Any]]:
        payload = []
        for index, result in enumerate(results[:MAX_RESULTS_FOR_SCORING], start=1):
            snippet = (result.content or "")[:SNIPPET_MAX_CHARS]
            payload.append(
                {
                    "index": index,
                    "title": result.title,
                    "url": result.url,
                    "source_type": result.source_type.value,
                    "summary": snippet,
                    "citation_count": result.citation_count,
                    "publication_date": result.publication_date,
                    "venue": result.venue,
                    "keywords": query.keywords,
                }
            )
        return payload

    def _build_scoring_prompt(
        self,
        intent: IntentAnalysis,
        query: SearchQuery,
        payload: List[Dict[str, Any]],
    ) -> str:
        explicit = ", ".join(intent.explicit_requirements[:5]) if intent.explicit_requirements else "None"
        implicit = ", ".join(intent.implicit_requirements[:3]) if intent.implicit_requirements else "None"
        missing = ", ".join(intent.missing_info[:3]) if intent.missing_info else "None"

        sources_block = "\n".join(
            textwrap.dedent(
                f"""
                Result {item['index']}:
                  Title: {item['title']}
                  URL: {item['url']}
                  Source Type: {item['source_type']}
                  Summary: {item['summary']}
                  Citation Count: {item['citation_count']}
                  Publication Date: {item['publication_date']}
                  Venue: {item['venue']}
                """.strip()
            )
            for item in payload
        )

        prompt = textwrap.dedent(
            f"""
            Project Context:
            - Document Type: {intent.document_type}
            - Field: {intent.field}
            - Academic Level: {intent.academic_level}
            - Target Word Count: {intent.word_count}
            - Explicit Requirements: {explicit}
            - Implicit Requirements: {implicit}
            - Outstanding Questions: {missing}

            Search Query: {query.query}
            Query Type: {query.query_type.value}
            Priority: {query.priority.value}
            Category: {query.category}

            Candidate Sources:
            {sources_block}
            """
        ).strip()
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

    def _apply_llm_scores(
        self,
        query: SearchQuery,
        results: List[SearchResult],
        data: Dict[str, Any],
    ) -> List[SearchResult]:
        indexed_results = {index + 1: result for index, result in enumerate(results[:MAX_RESULTS_FOR_SCORING])}
        url_map = {result.url: result for result in results}

        for item in data.get("results", []):
            result_obj: Optional[SearchResult] = None
            url = item.get("url")
            index = item.get("index")
            if url and url in url_map:
                result_obj = url_map[url]
            elif index and index in indexed_results:
                result_obj = indexed_results[index]

            if result_obj is None:
                continue

            score_raw = item.get("relevance", 0)
            try:
                score = max(0.0, min(1.0, float(score_raw) / 100.0))
            except (TypeError, ValueError):
                score = 0.0
            result_obj.relevance_score = score

            metadata = result_obj.metadata or {}
            metadata.update(
                {
                    "relevance_reason": item.get("reason"),
                    "matched_terms": item.get("matched_terms", []),
                    "recommended_use": item.get("recommended_use", []),
                    "confidence": item.get("confidence", "medium"),
                    "flags": item.get("flags", []),
                    "scoring_mode": "llm",
                }
            )
            result_obj.metadata = metadata

        # Apply heuristic fallback to any remaining results without a score
        for result in results:
            if result.relevance_score <= 0.0:
                self._apply_heuristic_score(query=query, result=result)

        return results

    def _apply_heuristic_score(
        self,
        query: Optional[SearchQuery],
        result: SearchResult,
    ) -> None:
        score = 0.4
        reason_parts = ["Baseline relevance"]

        if result.citation_count:
            boost = min(0.2, (result.citation_count or 0) / 200.0)
            score += boost
            reason_parts.append("Citations present")

        if result.publication_date:
            try:
                year = int(str(result.publication_date)[:4])
                current_year = time.gmtime().tm_year
                if year >= current_year - 2:
                    score += 0.2
                    reason_parts.append("Recent publication")
                elif year >= current_year - 5:
                    score += 0.1
            except (TypeError, ValueError):
                pass

        if query and query.keywords:
            text_blob = f"{result.title} {result.content}".lower()
            matched = [kw for kw in query.keywords if kw.lower() in text_blob]
            if matched:
                score += 0.15
                reason_parts.append(f"Matches keywords: {', '.join(matched[:3])}")

        result.relevance_score = min(1.0, score)
        metadata = result.metadata or {}
        metadata.update(
            {
                "relevance_reason": "; ".join(reason_parts),
                "matched_terms": metadata.get("matched_terms", []),
                "recommended_use": metadata.get("recommended_use", []),
                "confidence": metadata.get("confidence", "medium"),
                "flags": metadata.get("flags", []),
                "scoring_mode": metadata.get("scoring_mode", "heuristic"),
            }
        )
        result.metadata = metadata

    def _initialize_engines(self) -> Tuple[List[Tuple[str, Any, SearchAPIConfig]], int]:
        engines: List[Tuple[str, Any, SearchAPIConfig]] = []
        max_results = 10
        for name, api_config in self.config.search_apis.items():
            if not api_config.enabled:
                continue
            engine = self._create_engine(name, api_config)
            if engine is None:
                continue
            engines.append((name, engine, api_config))
            max_results = max(max_results, api_config.max_results)

        if not engines:
            raise RuntimeError("No search engines enabled. Configure API keys or enable free engines.")

        return engines, max_results

    def _create_engine(self, name: str, api_config: SearchAPIConfig):
        timeout = api_config.timeout_seconds
        if name == "semantic_scholar":
            return SemanticScholarSearch(api_key=api_config.api_key, timeout=timeout)
        if name == "arxiv":
            return ArXivSearch(timeout=timeout)
        if name == "pubmed":
            return PubMedSearch(timeout=timeout)
        if name == "perplexity":
            if not api_config.api_key:
                logger.warning("Perplexity API key missing; skipping engine.")
                return None
                return PerplexitySearch(api_key=api_config.api_key, timeout=timeout)
        # TODO: Add Exa, Tavily, Serper, You.com integrations
        logger.debug("Search engine '%s' not yet implemented; skipping.", name)
        return None
