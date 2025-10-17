"""Prowzi: Production-Ready Autonomous Multi-Agent Research System

Built on Microsoft Agent Framework with OpenRouter integration.
Implements 7 specialized agents for end-to-end research automation.

Agents:
    - IntentAgent: Document parsing and requirement understanding
    - PlanningAgent: Task decomposition and search query generation
    - SearchAgent: Multi-engine evidence gathering (8 APIs)
    - VerificationAgent: Source validation and credibility scoring
    - WritingAgent: Academic content generation with citations
    - EvaluationAgent: Quality assessment and standards checking
    - TurnitinAgent: Plagiarism detection and iterative refinement

Usage:
    >>> from prowzi import ProwziOrchestrator
    >>> orchestrator = ProwziOrchestrator()
    >>> result = await orchestrator.run_research(
    ...     prompt="Write 10000-word PhD literature review on AI in healthcare",
    ...     files=["paper1.pdf", "paper2.pdf"]
    ... )
"""

__version__ = "1.0.0"

from prowzi.agents.evaluation_agent import EvaluationAgent
from prowzi.agents.intent_agent import IntentAgent
from prowzi.agents.planning_agent import PlanningAgent
from prowzi.agents.search_agent import SearchAgent
from prowzi.agents.turnitin_agent import TurnitinAgent
from prowzi.agents.verification_agent import VerificationAgent
from prowzi.agents.writing_agent import WritingAgent
from prowzi.config.settings import ProwziConfig
from prowzi.workflows.orchestrator import ProwziOrchestrator

__all__ = [
    "EvaluationAgent",
    "IntentAgent",
    "PlanningAgent",
    "ProwziConfig",
    "ProwziOrchestrator",
    "SearchAgent",
    "TurnitinAgent",
    "VerificationAgent",
    "WritingAgent",
]
