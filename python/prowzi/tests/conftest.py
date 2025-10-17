"""Pytest configuration and shared fixtures for Prowzi tests.

This module provides common fixtures and test utilities used across
all test modules in the Prowzi test suite.
"""

import pytest
from pathlib import Path
from typing import Dict, Any
from unittest.mock import AsyncMock, Mock, MagicMock

from prowzi.agents.intent_agent import IntentAnalysis
from prowzi.agents.planning_agent import ResearchPlan, Task, SearchQuery, QueryType, TaskPriority
from prowzi.tools.search_tools import SearchResult, SourceType


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def test_data_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for test data."""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


@pytest.fixture
def mock_config() -> Dict[str, Any]:
    """Mock configuration for testing."""
    return {
        "openrouter_api_key": "test-key-12345",
        "openrouter_base_url": "https://openrouter.ai/api/v1",
        "models": {
            "intent": "anthropic/claude-3.5-sonnet",
            "planning": "openai/gpt-4o",
            "search": "google/gemini-2.0-flash-exp",
        },
        "output_dir": "test_output",
        "max_retries": 3,
        "timeout": 30,
    }


# ============================================================================
# Intent Agent Fixtures
# ============================================================================

@pytest.fixture
def sample_intent_analysis() -> IntentAnalysis:
    """Sample IntentAnalysis for testing."""
    return IntentAnalysis(
        document_type="research_paper",
        field="Computer Science",
        academic_level="undergraduate",
        word_count=3000,
        explicit_requirements=[
            "Introduction to quantum computing",
            "Quantum algorithms (Shor's, Grover's)",
            "Current applications and limitations",
        ],
        implicit_requirements=[
            "Technical depth appropriate for undergraduates",
            "Balance theory and practical applications",
        ],
        citation_style="APA",
        region="United States",
        timeframe="2020-2025",
        confidence_score=0.95,
        missing_info=[],
        requires_user_input=False,
    )


@pytest.fixture
def incomplete_intent_analysis() -> IntentAnalysis:
    """IntentAnalysis with missing information for testing."""
    return IntentAnalysis(
        document_type="essay",
        field="Technology",
        academic_level="high_school",
        word_count=1500,
        explicit_requirements=["Discuss AI"],
        implicit_requirements=[],
        citation_style=None,
        region=None,
        timeframe=None,
        confidence_score=0.65,
        missing_info=["citation_style", "region", "timeframe"],
        requires_user_input=True,
    )


# ============================================================================
# Planning Agent Fixtures
# ============================================================================

@pytest.fixture
def sample_search_query() -> SearchQuery:
    """Sample SearchQuery for testing."""
    return SearchQuery(
        query="quantum computing algorithms",
        query_type=QueryType.SPECIFIC,
        priority=TaskPriority.HIGH,
        category="computer_science",
        estimated_sources=10,
        keywords=["quantum", "algorithms", "computing"],
    )


@pytest.fixture
def sample_task() -> Task:
    """Sample Task for testing."""
    return Task(
        id="task_001",
        name="Research quantum algorithms",
        description="Find papers on Shor's and Grover's algorithms",
        priority=TaskPriority.HIGH,
        depends_on=[],
        subtasks=[],
        duration_minutes=30,
        assigned_agent="search",
        queries=[],
        metadata={"section": "introduction"},
    )


@pytest.fixture
def sample_research_plan() -> ResearchPlan:
    """Sample ResearchPlan for testing."""
    task = Task(
        id="task_001",
        name="Quantum Computing Overview",
        description="Research quantum computing fundamentals",
        priority=TaskPriority.HIGH,
        depends_on=[],
        subtasks=[],
        duration_minutes=45,
        assigned_agent="search",
        queries=[],
        metadata={},
    )

    query = SearchQuery(
        query="quantum computing introduction",
        query_type=QueryType.BROAD,
        priority=1,
        keywords=["quantum", "computing"],
        expected_results=20,
        min_quality_score=0.7,
    )

    return ResearchPlan(
        document_type="research_paper",
        field="Computer Science",
        target_word_count=3000,
        tasks={"task_001": task},
        search_queries=[query],
        execution_order=["task_001"],
        parallel_groups=[["task_001"]],
        dependencies={},
        quality_checkpoints=["verify_sources", "check_citations"],
        contingencies={"no_results": "broaden_search"},
        resource_estimates={
            "total_duration_minutes": 45,
            "total_cost_usd": 0.50,
            "total_api_calls": 10,
        },
        metadata={"created_at": "2025-10-16"},
    )


# ============================================================================
# Search Tools Fixtures
# ============================================================================

@pytest.fixture
def sample_search_result() -> SearchResult:
    """Sample SearchResult for testing."""
    return SearchResult(
        title="Quantum Computing: A Survey",
        url="https://arxiv.org/abs/2301.12345",
        content="This paper surveys recent advances in quantum computing...",
        source_type=SourceType.ACADEMIC_PAPER,
        author="John Doe, Jane Smith",
        publication_date="2023-01-15",
        citation_count=42,
        venue="arXiv Quantum Physics",
        doi="10.48550/arXiv.2301.12345",
        relevance_score=0.95,
        metadata={"arxiv_id": "2301.12345"},
    )


@pytest.fixture
def multiple_search_results() -> list[SearchResult]:
    """Multiple SearchResults for testing deduplication and ranking."""
    return [
        SearchResult(
            title="Quantum Computing Introduction",
            url="https://example.com/quantum1",
            content="Introduction to quantum computing concepts",
            source_type=SourceType.WEB_ARTICLE,
            relevance_score=0.9,
        ),
        SearchResult(
            title="Quantum Computing: An Overview",  # Similar title
            url="https://example.com/quantum2",
            content="Overview of quantum computing principles",
            source_type=SourceType.WEB_ARTICLE,
            relevance_score=0.85,
        ),
        SearchResult(
            title="Quantum Algorithms Deep Dive",
            url="https://arxiv.org/abs/1234.56789",
            content="Detailed analysis of quantum algorithms",
            source_type=SourceType.ACADEMIC_PAPER,
            citation_count=150,
            relevance_score=0.95,
        ),
    ]


# ============================================================================
# Mock API Fixtures
# ============================================================================

@pytest.fixture
def mock_openrouter_response() -> Dict[str, Any]:
    """Mock OpenRouter API response."""
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "This is a test response from the AI model.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        },
        "model": "anthropic/claude-3.5-sonnet",
    }


@pytest.fixture
def mock_semantic_scholar_response() -> Dict[str, Any]:
    """Mock Semantic Scholar API response."""
    return {
        "data": [
            {
                "title": "Quantum Computing Research",
                "url": "https://www.semanticscholar.org/paper/abc123",
                "abstract": "This paper presents research on quantum computing.",
                "authors": [{"name": "Alice Researcher"}, {"name": "Bob Scientist"}],
                "year": 2024,
                "citationCount": 25,
                "venue": "Nature Quantum",
                "externalIds": {"DOI": "10.1038/s41586-024-12345"},
            }
        ]
    }


@pytest.fixture
def mock_arxiv_response() -> str:
    """Mock arXiv API XML response."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
    <entry>
        <id>http://arxiv.org/abs/2310.12345v1</id>
        <title>Quantum Algorithms Survey</title>
        <summary>Comprehensive survey of quantum algorithms...</summary>
        <author><name>Charlie Quantum</name></author>
        <published>2023-10-15T00:00:00Z</published>
    </entry>
</feed>"""


# ============================================================================
# Agent Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_chat_agent() -> AsyncMock:
    """Mock ChatAgent for testing."""
    agent = AsyncMock()
    agent.run = AsyncMock()

    # Create a mock response object
    mock_response = Mock()
    mock_response.response = "Mocked agent response"
    mock_response.usage = {"input_tokens": 100, "output_tokens": 50}

    agent.run.return_value = mock_response
    return agent


@pytest.fixture
def mock_intent_agent(mock_chat_agent: AsyncMock) -> Mock:
    """Mock IntentAgent for testing."""
    from prowzi.agents.intent_agent import IntentAgent

    mock_agent = Mock(spec=IntentAgent)
    mock_agent.agent = mock_chat_agent
    mock_agent.analyze = AsyncMock()

    return mock_agent


@pytest.fixture
def mock_planning_agent(mock_chat_agent: AsyncMock) -> Mock:
    """Mock PlanningAgent for testing."""
    from prowzi.agents.planning_agent import PlanningAgent

    mock_agent = Mock(spec=PlanningAgent)
    mock_agent.agent = mock_chat_agent
    mock_agent.create_plan = AsyncMock()

    return mock_agent


# ============================================================================
# Async Testing Utilities
# ============================================================================

@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Logging Fixtures
# ============================================================================

@pytest.fixture
def capture_logs(caplog):
    """Capture logs for testing logging behavior."""
    import logging
    caplog.set_level(logging.DEBUG)
    return caplog


# ============================================================================
# File I/O Fixtures
# ============================================================================

@pytest.fixture
def temp_checkpoint_file(tmp_path: Path) -> Path:
    """Create a temporary checkpoint file for testing."""
    checkpoint_file = tmp_path / "checkpoints" / "test_checkpoint.json"
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    return checkpoint_file


@pytest.fixture
def sample_pdf_content() -> bytes:
    """Sample PDF content for document parsing tests."""
    # Minimal valid PDF structure
    return b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
trailer
<< /Size 4 /Root 1 0 R >>
startxref
%%EOF"""


@pytest.fixture
def sample_docx_requirements() -> str:
    """Sample requirements text from a DOCX file."""
    return """
    Research Requirements:

    1. Topic: Quantum Computing Applications
    2. Length: 3000 words
    3. Format: APA style
    4. Sections required:
       - Introduction
       - Literature Review
       - Methodology
       - Findings
       - Conclusion
    5. Minimum 15 academic sources
    """


# ============================================================================
# Performance Testing Fixtures
# ============================================================================

@pytest.fixture
def benchmark_config() -> Dict[str, Any]:
    """Configuration for performance benchmarking tests."""
    return {
        "max_duration_seconds": 5.0,
        "memory_limit_mb": 512,
        "iterations": 100,
    }
