"""Prowzi Agents Package"""

from prowzi.agents.intent_agent import IntentAgent, IntentAnalysis
from prowzi.agents.planning_agent import (
    PlanningAgent,
    ResearchPlan,
    Task,
    SearchQuery,
    QualityCheckpoint,
    QueryType,
    TaskPriority,
)
from prowzi.agents.search_agent import (
    SearchAgent,
    SearchAgentResult,
    QueryResultSummary,
)
from prowzi.agents.verification_agent import (
    VerificationAgent,
    VerificationAgentResult,
    SourceVerification,
)
from prowzi.agents.writing_agent import (
    WritingAgent,
    WritingAgentResult,
    SectionDraft,
    SectionOutline,
)
from prowzi.agents.evaluation_agent import (
    EvaluationAgent,
    EvaluationAgentResult,
    EvaluationCriterion,
    SectionEvaluation,
)
from prowzi.agents.turnitin_agent import (
    TurnitinAgent,
    TurnitinAgentResult,
    TurnitinDocument,
    TurnitinIteration,
    TurnitinReport,
    TurnitinSubmission,
    TurnitinThresholds,
)

__all__ = [
    "IntentAgent",
    "IntentAnalysis",
    "PlanningAgent",
    "ResearchPlan",
    "Task",
    "SearchQuery",
    "QualityCheckpoint",
    "QueryType",
    "TaskPriority",
    "SearchAgent",
    "SearchAgentResult",
    "QueryResultSummary",
    "VerificationAgent",
    "VerificationAgentResult",
    "SourceVerification",
    "WritingAgent",
    "WritingAgentResult",
    "SectionDraft",
    "SectionOutline",
    "EvaluationAgent",
    "EvaluationAgentResult",
    "EvaluationCriterion",
    "SectionEvaluation",
    "TurnitinAgent",
    "TurnitinAgentResult",
    "TurnitinDocument",
    "TurnitinIteration",
    "TurnitinReport",
    "TurnitinSubmission",
    "TurnitinThresholds",
]
