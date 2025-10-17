"""Tests for Planning Agent.

Tests the research planning functionality including:
- Task decomposition
- Search query generation
- Dependency resolution
- Resource estimation
- Parallel execution planning
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from prowzi.agents.planning_agent import (
    PlanningAgent,
    ResearchPlan,
    Task,
    SearchQuery,
    QueryType,
)
from prowzi.agents.intent_agent import IntentAnalysis


class TestPlanningAgentBasic:
    """Basic Planning Agent functionality tests."""

    @pytest.mark.asyncio
    async def test_create_basic_plan(
        self,
        mock_chat_agent: AsyncMock,
        sample_intent_analysis: IntentAnalysis,
    ):
        """Test creating a basic research plan."""
        # Setup mock response
        mock_response = Mock()
        mock_response.response = """
        {
            "tasks": [
                {
                    "task_id": "task_001",
                    "name": "Research quantum fundamentals",
                    "description": "Find foundational papers",
                    "task_type": "research",
                    "priority": 1,
                    "estimated_duration": 30
                }
            ],
            "search_queries": [
                {
                    "query": "quantum computing introduction",
                    "query_type": "broad",
                    "priority": 1,
                    "keywords": ["quantum", "computing"],
                    "expected_results": 20
                }
            ]
        }
        """
        mock_chat_agent.run.return_value = mock_response

        with patch("prowzi.agents.planning_agent.ChatAgent", return_value=mock_chat_agent):
            agent = PlanningAgent()
            agent.agent = mock_chat_agent

            plan = await agent.create_plan(sample_intent_analysis)

            # Assertions
            assert isinstance(plan, ResearchPlan)
            assert len(plan.tasks) > 0
            assert len(plan.search_queries) > 0
            assert len(plan.execution_order) > 0

    @pytest.mark.asyncio
    async def test_plan_with_custom_constraints(
        self,
        mock_chat_agent: AsyncMock,
        sample_intent_analysis: IntentAnalysis,
    ):
        """Test creating plan with custom resource constraints."""
        mock_response = Mock()
        mock_response.response = '{"tasks": [], "search_queries": []}'
        mock_chat_agent.run.return_value = mock_response

        constraints = {
            "max_duration": 60,  # minutes
            "max_cost": 2.00,  # USD
            "max_queries": 50,
        }

        with patch("prowzi.agents.planning_agent.ChatAgent", return_value=mock_chat_agent):
            agent = PlanningAgent()
            agent.agent = mock_chat_agent

            plan = await agent.create_plan(sample_intent_analysis, constraints)

            # Verify constraints are respected
            assert plan.resource_estimates["total_duration_minutes"] <= constraints["max_duration"]
            assert plan.resource_estimates["total_cost_usd"] <= constraints["max_cost"]


class TestTaskDecomposition:
    """Test task decomposition and hierarchy."""

    def test_hierarchical_tasks(self, sample_research_plan: ResearchPlan):
        """Test that tasks can have subtasks."""
        task = Task(
            task_id="parent_001",
            name="Research quantum computing",
            description="Main research task",
            task_type="research",
            priority=1,
            estimated_duration=60,
            depends_on=[],
            subtasks=[
                Task(
                    task_id="sub_001",
                    name="Research algorithms",
                    description="Subtask",
                    task_type="research",
                    priority=2,
                    estimated_duration=20,
                    depends_on=[],
                    subtasks=[],
                    status="pending",
                    queries=[],
                    metadata={},
                )
            ],
            status="pending",
            queries=[],
            metadata={},
        )

        assert len(task.subtasks) == 1
        assert task.subtasks[0].task_id == "sub_001"

    def test_task_dependencies(self):
        """Test task dependency tracking."""
        task1 = Task(
            task_id="task_001",
            name="Background research",
            description="Initial research",
            task_type="research",
            priority=1,
            estimated_duration=30,
            depends_on=[],
            subtasks=[],
            status="pending",
            queries=[],
            metadata={},
        )

        task2 = Task(
            task_id="task_002",
            name="Deep dive research",
            description="Detailed analysis",
            task_type="research",
            priority=2,
            estimated_duration=45,
            depends_on=["task_001"],  # Depends on task1
            subtasks=[],
            status="pending",
            queries=[],
            metadata={},
        )

        assert "task_001" in task2.depends_on


class TestSearchQueryGeneration:
    """Test search query generation and optimization."""

    def test_query_types(self, sample_search_query: SearchQuery):
        """Test different query type generation."""
        queries = [
            SearchQuery(
                query="quantum computing overview",
                query_type=QueryType.BROAD,
                priority=1,
                keywords=["quantum", "computing"],
                expected_results=50,
                min_quality_score=0.6,
            ),
            SearchQuery(
                query="Shor's algorithm implementation",
                query_type=QueryType.SPECIFIC,
                priority=2,
                keywords=["Shor", "algorithm", "implementation"],
                expected_results=10,
                min_quality_score=0.9,
            ),
            SearchQuery(
                query="quantum vs classical computing",
                query_type=QueryType.COMPARATIVE,
                priority=3,
                keywords=["quantum", "classical", "comparison"],
                expected_results=20,
                min_quality_score=0.7,
            ),
        ]

        assert queries[0].query_type == QueryType.BROAD
        assert queries[1].query_type == QueryType.SPECIFIC
        assert queries[2].query_type == QueryType.COMPARATIVE

    def test_query_prioritization(self):
        """Test that queries are properly prioritized."""
        queries = [
            SearchQuery(
                query="high priority query",
                query_type=QueryType.SPECIFIC,
                priority=1,
                keywords=["important"],
                expected_results=10,
                min_quality_score=0.9,
            ),
            SearchQuery(
                query="low priority query",
                query_type=QueryType.BROAD,
                priority=5,
                keywords=["general"],
                expected_results=50,
                min_quality_score=0.5,
            ),
        ]

        # Sort by priority
        sorted_queries = sorted(queries, key=lambda q: q.priority)

        assert sorted_queries[0].priority == 1
        assert sorted_queries[1].priority == 5


class TestExecutionPlanning:
    """Test execution order and parallelization."""

    def test_execution_order(self, sample_research_plan: ResearchPlan):
        """Test that execution order respects dependencies."""
        assert len(sample_research_plan.execution_order) > 0
        assert all(isinstance(task_id, str) for task_id in sample_research_plan.execution_order)

    def test_parallel_groups(self, sample_research_plan: ResearchPlan):
        """Test that independent tasks are grouped for parallel execution."""
        assert len(sample_research_plan.parallel_groups) > 0

        # Each group should contain task IDs that can run in parallel
        for group in sample_research_plan.parallel_groups:
            assert isinstance(group, list)
            assert all(isinstance(task_id, str) for task_id in group)

    def test_dependency_graph(self, sample_research_plan: ResearchPlan):
        """Test dependency graph is correctly built."""
        # Dependencies should map task_id to list of dependent task_ids
        assert isinstance(sample_research_plan.dependencies, dict)


class TestResourceEstimation:
    """Test resource estimation and optimization."""

    def test_duration_estimation(self, sample_research_plan: ResearchPlan):
        """Test that duration is estimated for plan."""
        estimates = sample_research_plan.resource_estimates

        assert "total_duration_minutes" in estimates
        assert estimates["total_duration_minutes"] > 0

    def test_cost_estimation(self, sample_research_plan: ResearchPlan):
        """Test that cost is estimated for plan."""
        estimates = sample_research_plan.resource_estimates

        assert "total_cost_usd" in estimates
        assert estimates["total_cost_usd"] >= 0

    def test_api_call_estimation(self, sample_research_plan: ResearchPlan):
        """Test that API calls are estimated."""
        estimates = sample_research_plan.resource_estimates

        assert "total_api_calls" in estimates
        assert estimates["total_api_calls"] > 0


class TestPlanningAgentEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_minimal_intent(self, mock_chat_agent: AsyncMock):
        """Test planning with minimal intent information."""
        minimal_intent = IntentAnalysis(
            user_query="Write something",
            document_type="essay",
            field="General",
            academic_level="unknown",
            word_count=500,
            requirements=["Write content"],
            confidence_score=0.50,
            missing_info=["field", "citation_style"],
            requires_user_input=True,
        )

        mock_response = Mock()
        mock_response.response = '{"tasks": [], "search_queries": []}'
        mock_chat_agent.run.return_value = mock_response

        with patch("prowzi.agents.planning_agent.ChatAgent", return_value=mock_chat_agent):
            agent = PlanningAgent()
            agent.agent = mock_chat_agent

            plan = await agent.create_plan(minimal_intent)

            # Should still create a valid plan, even if simple
            assert isinstance(plan, ResearchPlan)

    @pytest.mark.asyncio
    async def test_complex_requirements(self, mock_chat_agent: AsyncMock):
        """Test planning with very complex requirements."""
        complex_intent = IntentAnalysis(
            user_query="Write comprehensive analysis",
            document_type="dissertation",
            field="Quantum Physics",
            academic_level="phd",
            word_count=50000,
            requirements=[
                "Extensive literature review (100+ papers)",
                "Original research contribution",
                "Mathematical proofs",
                "Experimental validation",
                "Comprehensive bibliography",
            ],
            citation_style="Chicago",
            region="International",
            timeframe="1990-2025",
            confidence_score=0.95,
            missing_info=[],
            requires_user_input=False,
        )

        mock_response = Mock()
        mock_response.response = '{"tasks": [], "search_queries": []}'
        mock_chat_agent.run.return_value = mock_response

        with patch("prowzi.agents.planning_agent.ChatAgent", return_value=mock_chat_agent):
            agent = PlanningAgent()
            agent.agent = mock_chat_agent

            plan = await agent.create_plan(complex_intent)

            # Should handle complexity appropriately
            assert isinstance(plan, ResearchPlan)


class TestPlanningAgentLogging:
    """Test logging behavior."""

    @pytest.mark.asyncio
    async def test_logs_planning_start(
        self,
        mock_chat_agent: AsyncMock,
        sample_intent_analysis: IntentAnalysis,
        caplog,
    ):
        """Test that planning agent logs start of planning."""
        mock_response = Mock()
        mock_response.response = '{"tasks": [], "search_queries": []}'
        mock_chat_agent.run.return_value = mock_response

        with patch("prowzi.agents.planning_agent.ChatAgent", return_value=mock_chat_agent):
            agent = PlanningAgent()
            agent.agent = mock_chat_agent

            await agent.create_plan(sample_intent_analysis)

            assert "Planning Agent" in caplog.text or "Creating research plan" in caplog.text

    @pytest.mark.asyncio
    async def test_logs_plan_completion(
        self,
        mock_chat_agent: AsyncMock,
        sample_intent_analysis: IntentAnalysis,
        caplog,
    ):
        """Test that agent logs successful plan creation."""
        mock_response = Mock()
        mock_response.response = '{"tasks": [], "search_queries": []}'
        mock_chat_agent.run.return_value = mock_response

        with patch("prowzi.agents.planning_agent.ChatAgent", return_value=mock_chat_agent):
            agent = PlanningAgent()
            agent.agent = mock_chat_agent

            await agent.create_plan(sample_intent_analysis)

            assert "complete" in caplog.text.lower() or "created" in caplog.text.lower()
