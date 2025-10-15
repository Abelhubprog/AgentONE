"""
Planning Agent

Strategic task decomposition and search query generation.
Uses GPT-4o for structured planning with hierarchical task breakdown.

Responsibilities:
    - Decompose research requirements into hierarchical tasks
    - Generate comprehensive search queries (5 types per requirement)
    - Resolve task dependencies and create execution order
    - Estimate resources (time, tokens, cost)
    - Define quality checkpoints
    - Plan contingencies for edge cases
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import json

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient

from prowzi.config import get_config
from prowzi.agents.intent_agent import IntentAnalysis


class QueryType(Enum):
    """Types of search queries"""
    BROAD = "broad"  # General overview
    SPECIFIC = "specific"  # Targeted deep dive
    COMPARATIVE = "comparative"  # Comparing approaches/methods
    RECENT = "recent"  # Latest developments
    METHODOLOGICAL = "methodological"  # Methods and techniques
    CHALLENGE = "challenge"  # Problems and limitations


class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class SearchQuery:
    """
    A single search query.

    Attributes:
        query: The search query string
        query_type: Type of query
        priority: Priority level
        category: Knowledge category this belongs to
        estimated_sources: Expected number of sources
        keywords: Key terms to look for in results
    """
    query: str
    query_type: QueryType
    priority: TaskPriority
    category: str
    estimated_sources: int = 5
    keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "query_type": self.query_type.value,
            "priority": self.priority.value,
            "category": self.category,
            "estimated_sources": self.estimated_sources,
            "keywords": self.keywords,
        }


@dataclass
class Task:
    """
    A single task in the workflow.

    Attributes:
        id: Unique task identifier
        name: Task name
        description: Task description
        priority: Task priority
        depends_on: List of task IDs this depends on
        subtasks: List of subtasks
        duration_minutes: Estimated duration
        assigned_agent: Agent responsible for this task
        queries: Search queries for this task (if applicable)
        metadata: Additional task metadata
    """
    id: str
    name: str
    description: str
    priority: TaskPriority
    depends_on: List[str] = field(default_factory=list)
    subtasks: List['Task'] = field(default_factory=list)
    duration_minutes: int = 10
    assigned_agent: Optional[str] = None
    queries: List[SearchQuery] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority.value,
            "depends_on": self.depends_on,
            "subtasks": [st.to_dict() for st in self.subtasks],
            "duration_minutes": self.duration_minutes,
            "assigned_agent": self.assigned_agent,
            "queries": [q.to_dict() for q in self.queries],
            "metadata": self.metadata,
        }


@dataclass
class QualityCheckpoint:
    """
    Quality checkpoint in the workflow.

    Attributes:
        name: Checkpoint name
        criteria: List of quality criteria to check
        minimum_threshold: Minimum score to pass (0.0-1.0)
        after_task: Task ID this checkpoint follows
    """
    name: str
    criteria: List[str]
    minimum_threshold: float
    after_task: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "criteria": self.criteria,
            "minimum_threshold": self.minimum_threshold,
            "after_task": self.after_task,
        }


@dataclass
class ResearchPlan:
    """
    Complete research plan output.

    Attributes:
        task_hierarchy: Root task with all subtasks
        execution_order: Ordered list of task IDs
        parallel_groups: Groups of tasks that can run in parallel
        search_queries: All generated search queries
        quality_checkpoints: Quality validation checkpoints
        resource_estimates: Estimated resources needed
        contingencies: Contingency plans for common issues
        metadata: Additional plan metadata
    """
    task_hierarchy: Task
    execution_order: List[str]
    parallel_groups: List[List[str]]
    search_queries: List[SearchQuery]
    quality_checkpoints: List[QualityCheckpoint]
    resource_estimates: Dict[str, Any]
    contingencies: List[Dict[str, str]]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_hierarchy": self.task_hierarchy.to_dict(),
            "execution_order": self.execution_order,
            "parallel_groups": self.parallel_groups,
            "search_queries": [q.to_dict() for q in self.search_queries],
            "quality_checkpoints": [c.to_dict() for c in self.quality_checkpoints],
            "resource_estimates": self.resource_estimates,
            "contingencies": self.contingencies,
            "metadata": self.metadata,
        }


class PlanningAgent:
    """
    Planning Agent implementation.

    Decomposes research requirements into actionable tasks with search queries.

    Usage:
        >>> agent = PlanningAgent()
        >>> plan = await agent.create_plan(intent_analysis)
        >>> print(f"Total tasks: {len(plan.execution_order)}")
        >>> print(f"Search queries: {len(plan.search_queries)}")
    """

    def __init__(self, config=None):
        """
        Initialize Planning Agent.

        Args:
            config: Optional ProwziConfig instance
        """
        self.config = config or get_config()

        # Get model configuration
        model_config = self.config.get_model_for_agent("planning")

        # Create chat client
        self.chat_client = OpenAIChatClient(
            api_key=self.config.openrouter_api_key,
            base_url=self.config.openrouter_base_url,
            model=model_config.name,
        )

        # Create planning agent
        self.agent = ChatAgent(
            chat_client=self.chat_client,
            instructions=self._create_system_prompt(),
        )

    def _create_system_prompt(self) -> str:
        """Create system prompt for planning"""
        return """You are an expert research planning agent specialized in academic workflows.

Your role is to create comprehensive, actionable research plans by:
1. Breaking down research requirements into hierarchical tasks
2. Generating diverse search queries to gather comprehensive evidence
3. Resolving task dependencies and creating optimal execution order
4. Estimating resource requirements (time, tokens, cost)
5. Defining quality checkpoints to ensure research standards
6. Planning contingencies for common issues

For search query generation, create queries of these types:
- BROAD: General overview queries for foundational understanding
- SPECIFIC: Targeted queries for deep dives into particular aspects
- COMPARATIVE: Queries comparing different approaches/methods/tools
- RECENT: Queries focused on latest developments and trends
- METHODOLOGICAL: Queries about research methods and techniques
- CHALLENGE: Queries about problems, limitations, and critiques

Generate 3-5 queries per knowledge requirement, prioritizing:
- HIGH: Critical for core understanding
- MEDIUM: Important for depth and context
- LOW: Nice-to-have for comprehensiveness

For task decomposition:
- Create hierarchical structure (max 3 levels deep)
- Identify dependencies between tasks
- Group parallelizable tasks
- Estimate duration for each task
- Assign to appropriate agent (intent, search, verification, writing, evaluation)

Quality checkpoints should:
- Follow major task completions
- Have clear, measurable criteria
- Set reasonable minimum thresholds (typically 0.7-0.8)

Resource estimates should include:
- Total duration (minutes)
- Token estimates (input + output)
- Cost estimates (USD)
- Source targets (number of papers/articles needed)

Be thorough, realistic, and strategic in your planning."""

    async def create_plan(
        self,
        intent_analysis: IntentAnalysis,
        custom_constraints: Optional[Dict[str, Any]] = None
    ) -> ResearchPlan:
        """
        Create comprehensive research plan.

        Args:
            intent_analysis: Output from IntentAgent
            custom_constraints: Optional custom constraints (max_duration, max_cost, etc.)

        Returns:
            ResearchPlan with complete task decomposition and queries
        """
        print("📋 Planning Agent: Creating research plan...")

        # Build planning prompt
        prompt = self._build_planning_prompt(intent_analysis, custom_constraints)

        # Get plan from agent
        response = await self.agent.run(prompt)

        # Parse response into ResearchPlan
        plan = self._parse_plan_response(response.response, intent_analysis)

        print("✅ Research plan created!")
        print(f"   Total tasks: {len(plan.execution_order)}")
        print(f"   Search queries: {len(plan.search_queries)}")
        print(f"   Parallel groups: {len(plan.parallel_groups)}")
        print(f"   Estimated duration: {plan.resource_estimates.get('total_duration_minutes', 0)} minutes")
        print(f"   Estimated cost: ${plan.resource_estimates.get('total_cost_usd', 0):.2f}")

        return plan

    def _build_planning_prompt(
        self,
        intent_analysis: IntentAnalysis,
        custom_constraints: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for planning agent"""
        prompt_parts = [
            "Create a comprehensive research plan for the following requirements:",
            "",
            f"DOCUMENT TYPE: {intent_analysis.document_type}",
            f"FIELD: {intent_analysis.field}",
            f"ACADEMIC LEVEL: {intent_analysis.academic_level}",
            f"TARGET WORD COUNT: {intent_analysis.word_count}",
            "",
            "EXPLICIT REQUIREMENTS:",
        ]

        for req in intent_analysis.explicit_requirements:
            prompt_parts.append(f"  - {req}")

        if intent_analysis.implicit_requirements:
            prompt_parts.append("")
            prompt_parts.append("IMPLICIT REQUIREMENTS:")
            for req in intent_analysis.implicit_requirements:
                prompt_parts.append(f"  - {req}")

        if intent_analysis.citation_style:
            prompt_parts.append(f"\nCITATION STYLE: {intent_analysis.citation_style}")

        if intent_analysis.timeframe:
            prompt_parts.append(f"TIMEFRAME: {intent_analysis.timeframe}")

        if intent_analysis.region:
            prompt_parts.append(f"REGION: {intent_analysis.region}")

        if custom_constraints:
            prompt_parts.append("\nCUSTOM CONSTRAINTS:")
            for key, value in custom_constraints.items():
                prompt_parts.append(f"  {key}: {value}")

        prompt_parts.extend([
            "",
            "Create a detailed plan including:",
            "1. Hierarchical task breakdown (research → analysis → writing → review)",
            "2. Search queries (3-5 per knowledge requirement, all 5 query types)",
            "3. Task dependencies and execution order",
            "4. Quality checkpoints with criteria",
            "5. Resource estimates (duration, tokens, cost, sources needed)",
            "6. Contingency plans",
            "",
            "Provide your plan as a structured response that I can parse."
        ])

        return "\n".join(prompt_parts)

    def _parse_plan_response(
        self,
        response: str,
        intent_analysis: IntentAnalysis
    ) -> ResearchPlan:
        """
        Parse agent response into ResearchPlan structure.

        This is a simplified implementation. In production, you'd use
        structured output or JSON schema validation.
        """
        # Create default plan structure
        # (In production, this would parse the LLM response)

        # Define task hierarchy
        root_task = Task(
            id="root",
            name=f"Complete {intent_analysis.document_type}",
            description=f"Complete {intent_analysis.word_count}-word {intent_analysis.document_type} on {intent_analysis.field}",
            priority=TaskPriority.CRITICAL,
            subtasks=[
                Task(
                    id="research_phase",
                    name="Research & Evidence Gathering",
                    description="Gather comprehensive evidence from multiple sources",
                    priority=TaskPriority.CRITICAL,
                    duration_minutes=60,
                    assigned_agent="search",
                ),
                Task(
                    id="verification_phase",
                    name="Source Verification",
                    description="Validate sources for credibility and relevance",
                    priority=TaskPriority.HIGH,
                    depends_on=["research_phase"],
                    duration_minutes=30,
                    assigned_agent="verification",
                ),
                Task(
                    id="analysis_phase",
                    name="Content Analysis",
                    description="Analyze and synthesize gathered evidence",
                    priority=TaskPriority.HIGH,
                    depends_on=["verification_phase"],
                    duration_minutes=45,
                    assigned_agent="planning",
                ),
                Task(
                    id="writing_phase",
                    name="Document Writing",
                    description="Write complete document with proper structure",
                    priority=TaskPriority.CRITICAL,
                    depends_on=["analysis_phase"],
                    duration_minutes=90,
                    assigned_agent="writing",
                ),
                Task(
                    id="evaluation_phase",
                    name="Quality Evaluation",
                    description="Evaluate document against academic standards",
                    priority=TaskPriority.HIGH,
                    depends_on=["writing_phase"],
                    duration_minutes=30,
                    assigned_agent="evaluation",
                ),
            ]
        )

        # Generate search queries
        search_queries = self._generate_default_queries(intent_analysis)

        # Define execution order
        execution_order = [
            "research_phase",
            "verification_phase",
            "analysis_phase",
            "writing_phase",
            "evaluation_phase",
        ]

        # Define parallel groups (tasks that can run concurrently)
        parallel_groups = [
            ["research_phase"],
            ["verification_phase"],
            ["analysis_phase"],
            ["writing_phase"],
            ["evaluation_phase"],
        ]

        # Define quality checkpoints
        checkpoints = [
            QualityCheckpoint(
                name="Research Completeness",
                criteria=[
                    "Sufficient sources gathered (minimum 50)",
                    "Diverse source types",
                    "Recent sources included",
                    "Authoritative sources included"
                ],
                minimum_threshold=0.75,
                after_task="research_phase"
            ),
            QualityCheckpoint(
                name="Source Quality",
                criteria=[
                    "Sources are credible",
                    "Sources are relevant",
                    "Citations are valid",
                    "No obvious bias"
                ],
                minimum_threshold=0.80,
                after_task="verification_phase"
            ),
            QualityCheckpoint(
                name="Writing Quality",
                criteria=[
                    "Meets word count target",
                    "Proper structure",
                    "Clear argumentation",
                    "Correct citations",
                    "Academic tone"
                ],
                minimum_threshold=0.85,
                after_task="writing_phase"
            ),
        ]

        # Estimate resources
        total_duration = sum(task.duration_minutes for task in root_task.subtasks)
        estimated_tokens = (intent_analysis.word_count * 2)  # Rough estimate
        estimated_cost = (estimated_tokens / 1_000_000) * 3.0  # Average cost per 1M tokens

        resource_estimates = {
            "total_duration_minutes": total_duration,
            "total_tokens_estimated": estimated_tokens,
            "total_cost_usd": estimated_cost,
            "target_sources": len(search_queries) * 5,  # 5 sources per query
        }

        # Define contingencies
        contingencies = [
            {
                "scenario": "Insufficient search results",
                "action": "Expand search terms, use alternative APIs, lower relevance threshold"
            },
            {
                "scenario": "Low quality sources",
                "action": "Increase verification strictness, search academic databases specifically"
            },
            {
                "scenario": "Token limit exceeded",
                "action": "Chunk content, summarize sections, use higher context models"
            },
            {
                "scenario": "Quality checkpoint failure",
                "action": "Iterate on previous phase, add more sources, refine content"
            },
        ]

        # Create plan
        plan = ResearchPlan(
            task_hierarchy=root_task,
            execution_order=execution_order,
            parallel_groups=parallel_groups,
            search_queries=search_queries,
            quality_checkpoints=checkpoints,
            resource_estimates=resource_estimates,
            contingencies=contingencies,
            metadata={
                "created_from_intent": intent_analysis.to_dict(),
                "total_tasks": len(execution_order),
            }
        )

        return plan

    def _generate_default_queries(self, intent_analysis: IntentAnalysis) -> List[SearchQuery]:
        """Generate default search queries based on intent analysis"""
        queries = []
        field = intent_analysis.field
        doc_type = intent_analysis.document_type

        # Generate queries for different aspects
        query_templates = [
            # Broad overview
            (f"{field} overview systematic review", QueryType.BROAD, TaskPriority.HIGH, "Background"),
            (f"{field} foundations introduction", QueryType.BROAD, TaskPriority.MEDIUM, "Background"),

            # Specific deep dives
            (f"{field} applications implementations", QueryType.SPECIFIC, TaskPriority.HIGH, "Applications"),
            (f"{field} algorithms techniques methods", QueryType.SPECIFIC, TaskPriority.HIGH, "Methodology"),

            # Recent developments
            (f"{field} latest developments 2023 2024", QueryType.RECENT, TaskPriority.HIGH, "Current Research"),
            (f"{field} trends future directions", QueryType.RECENT, TaskPriority.MEDIUM, "Current Research"),

            # Methodological
            (f"{field} research methodology", QueryType.METHODOLOGICAL, TaskPriority.MEDIUM, "Methodology"),
            (f"{field} evaluation metrics", QueryType.METHODOLOGICAL, TaskPriority.MEDIUM, "Methodology"),

            # Challenges
            (f"{field} challenges limitations", QueryType.CHALLENGE, TaskPriority.HIGH, "Challenges"),
            (f"{field} ethical concerns issues", QueryType.CHALLENGE, TaskPriority.MEDIUM, "Challenges"),

            # Comparative
            (f"{field} comparison approaches", QueryType.COMPARATIVE, TaskPriority.MEDIUM, "Analysis"),
        ]

        for query_text, query_type, priority, category in query_templates:
            queries.append(
                SearchQuery(
                    query=query_text,
                    query_type=query_type,
                    priority=priority,
                    category=category,
                    estimated_sources=5,
                )
            )

        return queries
