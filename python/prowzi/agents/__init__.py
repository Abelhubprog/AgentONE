"""Prowzi Agents Package"""

from prowzi.agents.evaluation_agent import (
    EvaluationAgent,
    EvaluationAgentResult,
    EvaluationCriterion,
    SectionEvaluation,
)
from prowzi.agents.intent_agent import IntentAgent, IntentAnalysis
from prowzi.agents.planning_agent import (
    PlanningAgent,
    QualityCheckpoint,
    QueryType,
    ResearchPlan,
    SearchQuery,
    Task,
    TaskPriority,
)
from prowzi.agents.search_agent import (
    QueryResultSummary,
    SearchAgent,
    SearchAgentResult,
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
from prowzi.agents.verification_agent import (
    SourceVerification,
    VerificationAgent,
    VerificationAgentResult,
)
from prowzi.agents.writing_agent import (
    SectionDraft,
    SectionOutline,
    WritingAgent,
    WritingAgentResult,
)

__all__ = [
    "EvaluationAgent",
    "EvaluationAgentResult",
    "EvaluationCriterion",
    "IntentAgent",
    "IntentAnalysis",
    "PlanningAgent",
    "QualityCheckpoint",
    "QueryResultSummary",
    "QueryType",
    "ResearchPlan",
    "SearchAgent",
    "SearchAgentResult",
    "SearchQuery",
    "SectionDraft",
    "SectionEvaluation",
    "SectionOutline",
    "SourceVerification",
    "Task",
    "TaskPriority",
    "TurnitinAgent",
    "TurnitinAgentResult",
    "TurnitinDocument",
    "TurnitinIteration",
    "TurnitinReport",
    "TurnitinSubmission",
    "TurnitinThresholds",
    "VerificationAgent",
    "VerificationAgentResult",
    "WritingAgent",
    "WritingAgentResult",
]
