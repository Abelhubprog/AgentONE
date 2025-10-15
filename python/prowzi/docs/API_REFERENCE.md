# Prowzi API Reference

## Overview

This document provides a complete API reference for the Prowzi research automation system.

---

## Table of Contents

- [Core Orchestrator](#core-orchestrator)
- [Agents](#agents)
- [Configuration](#configuration)
- [Workflows](#workflows)
- [CLI](#cli)
- [Tools](#tools)
- [Data Classes](#data-classes)

---

## Core Orchestrator

### ProwziOrchestrator

Main workflow orchestrator managing the complete research pipeline.

```python
from prowzi.workflows import ProwziOrchestrator
```

#### Constructor

```python
ProwziOrchestrator(config: Optional[ProwziConfig] = None)
```

**Parameters**:
- `config` (Optional[ProwziConfig]): Configuration object. If None, uses `get_config()`.

**Example**:
```python
from prowzi.workflows import ProwziOrchestrator
from prowzi.config import ProwziConfig

config = ProwziConfig()
config.enable_checkpointing = True
orchestrator = ProwziOrchestrator(config=config)
```

#### Methods

##### run_research

```python
async def run_research(
    prompt: str,
    document_paths: Optional[List[str | Path]] = None,
    additional_context: Optional[Dict[str, Any]] = None,
    *,
    custom_constraints: Optional[Dict[str, Any]] = None,
    max_results_per_query: int = 12,
    max_sections: int = 8,
    thresholds: Optional[TurnitinThresholds] = None,
    progress_callback: Optional[ProgressCallback] = None,
    checkpoint_id: Optional[str] = None,
) -> ProwziOrchestrationResult
```

Execute the complete research pipeline.

**Parameters**:
- `prompt` (str): Research prompt or instructions
- `document_paths` (Optional[List[str | Path]]): Optional reference documents
- `additional_context` (Optional[Dict[str, Any]]): Additional context for agents
- `custom_constraints` (Optional[Dict[str, Any]]): Custom writing constraints
- `max_results_per_query` (int): Maximum search results per query (default: 12)
- `max_sections` (int): Maximum sections in draft (default: 8)
- `thresholds` (Optional[TurnitinThresholds]): Custom Turnitin thresholds
- `progress_callback` (Optional[ProgressCallback]): Async callback for progress updates
- `checkpoint_id` (Optional[str]): Resume from this checkpoint ID

**Returns**: `ProwziOrchestrationResult` with all agent results and metadata

**Example**:
```python
result = await orchestrator.run_research(
    prompt="Write a 10,000-word PhD thesis on quantum computing applications in cryptography",
    document_paths=["reference1.pdf", "reference2.pdf"],
    max_results_per_query=15,
    max_sections=10,
)

print(f"Draft word count: {result.draft.total_word_count}")
print(f"Evaluation score: {result.evaluation.total_score}")
print(f"Turnitin success: {result.turnitin.success}")
```

##### resume_from_checkpoint

```python
async def resume_from_checkpoint(
    checkpoint_id: str,
    progress_callback: Optional[ProgressCallback] = None,
) -> ProwziOrchestrationResult
```

Resume a workflow from a saved checkpoint.

**Parameters**:
- `checkpoint_id` (str): Checkpoint ID to resume from
- `progress_callback` (Optional[ProgressCallback]): Progress callback

**Returns**: `ProwziOrchestrationResult`

**Example**:
```python
result = await orchestrator.resume_from_checkpoint("abc123-def456")
```

---

## Agents

### IntentAgent

Analyzes research requirements from prompt and documents.

```python
from prowzi.agents import IntentAgent
```

#### Constructor

```python
IntentAgent(config: Optional[ProwziConfig] = None)
```

#### Methods

##### analyze

```python
async def analyze(
    prompt: str,
    document_paths: Optional[List[str | Path]] = None,
    additional_context: Optional[Dict[str, Any]] = None,
) -> IntentAnalysis
```

**Example**:
```python
intent_agent = IntentAgent()
analysis = await intent_agent.analyze(
    prompt="Write a research paper on AI safety",
    document_paths=["paper1.pdf"]
)

print(analysis.document_type)  # "research_paper"
print(analysis.academic_level)  # "phd"
print(analysis.word_count)  # 10000
```

---

### PlanningAgent

Creates detailed research plan with search queries.

```python
from prowzi.agents import PlanningAgent
```

#### Methods

##### create_plan

```python
async def create_plan(
    intent: IntentAnalysis,
    additional_context: Optional[Dict[str, Any]] = None,
) -> ResearchPlan
```

**Example**:
```python
planning_agent = PlanningAgent()
plan = await planning_agent.create_plan(intent_analysis)

print(len(plan.search_queries))  # 12-24 queries
print(plan.section_templates)
```

---

### SearchAgent

Executes multi-API search queries.

```python
from prowzi.agents import SearchAgent
```

#### Methods

##### search

```python
async def search(
    plan: ResearchPlan,
    max_results_per_query: int = 12,
) -> SearchAgentResult
```

**Example**:
```python
search_agent = SearchAgent()
results = await search_agent.search(plan, max_results_per_query=15)

print(len(results.sources))  # 48+ sources
print(results.coverage_analysis)
```

---

### VerificationAgent

Validates source credibility and quality.

```python
from prowzi.agents import VerificationAgent
```

#### Methods

##### verify

```python
async def verify(
    search_result: SearchAgentResult,
    intent: IntentAnalysis,
) -> VerificationAgentResult
```

**Example**:
```python
verification_agent = VerificationAgent()
verified = await verification_agent.verify(search_result, intent_analysis)

print(verified.average_score)  # 0.0-1.0
print(len(verified.accepted_sources))
print(len(verified.rejected_sources))
```

---

### WritingAgent

Generates structured academic drafts with citations.

```python
from prowzi.agents import WritingAgent
```

#### Methods

##### write_draft

```python
async def write_draft(
    intent: IntentAnalysis,
    plan: ResearchPlan,
    search: SearchAgentResult,
    verification: VerificationAgentResult,
    custom_constraints: Optional[Dict[str, Any]] = None,
    max_sections: int = 8,
) -> WritingAgentResult
```

**Example**:
```python
writing_agent = WritingAgent()
draft = await writing_agent.write_draft(
    intent=intent_analysis,
    plan=plan,
    search=search_result,
    verification=verification_result,
    max_sections=10
)

print(draft.total_word_count)
print(len(draft.sections))
print(len(draft.bibliography))
```

---

### EvaluationAgent

Scores draft quality against rubric.

```python
from prowzi.agents import EvaluationAgent
```

#### Methods

##### evaluate_draft

```python
async def evaluate_draft(
    intent: IntentAnalysis,
    plan: ResearchPlan,
    verification: VerificationAgentResult,
    draft: WritingAgentResult,
) -> EvaluationAgentResult
```

**Example**:
```python
evaluation_agent = EvaluationAgent()
evaluation = await evaluation_agent.evaluate_draft(
    intent=intent_analysis,
    plan=plan,
    verification=verification_result,
    draft=draft_result
)

print(evaluation.total_score)  # 0-100
print(evaluation.pass_threshold)  # True/False
print(evaluation.strengths)
print(evaluation.improvements)
```

---

### TurnitinAgent

Simulates plagiarism and AI detection with iterative redrafting.

```python
from prowzi.agents import TurnitinAgent
```

#### Methods

##### ensure_compliance

```python
async def ensure_compliance(
    draft: WritingAgentResult,
    intent: IntentAnalysis,
    thresholds: Optional[TurnitinThresholds] = None,
) -> TurnitinAgentResult
```

**Example**:
```python
turnitin_agent = TurnitinAgent()
turnitin_result = await turnitin_agent.ensure_compliance(
    draft=draft_result,
    intent=intent_analysis,
    thresholds=TurnitinThresholds(
        max_similarity=15.0,
        max_ai_score=10.0
    )
)

print(turnitin_result.success)
print(turnitin_result.final_report.similarity_score)
print(turnitin_result.final_report.ai_score)
print(len(turnitin_result.iterations))
```

---

## Configuration

### ProwziConfig

Central configuration class.

```python
from prowzi.config import ProwziConfig, get_config
```

#### Constructor

```python
ProwziConfig(env_file: Optional[str] = None)
```

**Parameters**:
- `env_file` (Optional[str]): Path to .env file (default: searches standard locations)

#### Properties

```python
# Model configurations
models: Dict[str, ModelConfig]
intent_models: List[str]
planning_model: str
search_model: str
verification_model: str
writing_model: str
evaluation_model: str
turnitin_model: str

# Search APIs
search_apis: Dict[str, Any]

# System settings
enable_checkpointing: bool
enable_telemetry: bool
checkpoint_dir: Path
output_dir: Path
log_level: str

# Quality thresholds
min_source_quality: float
min_relevance_score: float
turnitin_similarity_threshold: float
turnitin_ai_threshold: float
```

#### Example

```python
# Get default config
config = get_config()

# Customize
config.enable_checkpointing = True
config.checkpoint_dir = Path("/data/checkpoints")
config.turnitin_similarity_threshold = 12.0

# Use with orchestrator
orchestrator = ProwziOrchestrator(config=config)
```

#### Environment Variables

```bash
# OpenRouter
OPENAI_API_KEY=sk-or-v1-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1

# Checkpointing
PROWZI_ENABLE_CHECKPOINTING=true
PROWZI_CHECKPOINT_DIR=./prowzi_checkpoints

# Telemetry
PROWZI_ENABLE_TELEMETRY=true

# Quality
PROWZI_MIN_SOURCE_QUALITY=0.7
PROWZI_TURNITIN_SIMILARITY=15.0
PROWZI_TURNITIN_AI=10.0
```

---

## Workflows

### CheckpointManager

Manages workflow state persistence.

```python
from prowzi.workflows import CheckpointManager
```

#### Constructor

```python
CheckpointManager(checkpoint_dir: Path, enabled: bool = True)
```

#### Methods

##### save_checkpoint

```python
def save_checkpoint(
    session_id: str,
    stage: str,
    prompt: str,
    context: Dict[str, Any],
    stage_metrics: Dict[str, Any],
) -> str
```

Returns checkpoint ID.

##### load_checkpoint

```python
def load_checkpoint(checkpoint_id: str) -> Optional[WorkflowCheckpoint]
```

##### list_checkpoints

```python
def list_checkpoints(limit: int = 50) -> List[Dict[str, Any]]
```

**Example**:
```python
manager = CheckpointManager(checkpoint_dir=Path("./checkpoints"))

# Save
checkpoint_id = manager.save_checkpoint(
    session_id="abc123",
    stage="search",
    prompt="Research prompt",
    context={"intent": intent_result, "plan": plan_result},
    stage_metrics={"duration": 5.2}
)

# Load
checkpoint = manager.load_checkpoint(checkpoint_id)
print(checkpoint.intent)
print(checkpoint.plan)

# List
checkpoints = manager.list_checkpoints(limit=20)
for cp in checkpoints:
    print(f"{cp['checkpoint_id']}: {cp['stage']}")
```

---

### TelemetryCollector

Real-time metrics collection.

```python
from prowzi.workflows import TelemetryCollector
```

#### Constructor

```python
TelemetryCollector(output_dir: Path, enabled: bool = True)
```

#### Methods

##### start_session

```python
def start_session(session_id: str, prompt: str) -> None
```

##### record_stage_event

```python
def record_stage_event(
    session_id: str,
    stage: str,
    status: str,
    attempt: int = 1,
    duration: float = 0.0,
    details: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None
```

**Status values**: `"started"`, `"completed"`, `"failed"`, `"skipped"`, `"retrying"`

##### complete_session

```python
def complete_session(
    session_id: str,
    success: bool,
    total_duration: float,
    final_metadata: Optional[Dict[str, Any]] = None,
) -> None
```

##### get_session_metrics

```python
def get_session_metrics(session_id: str) -> Optional[WorkflowMetrics]
```

##### load_session

```python
def load_session(session_id: str) -> Optional[WorkflowMetrics]
```

##### list_sessions

```python
def list_sessions(limit: int = 50) -> List[Dict[str, Any]]
```

**Example**:
```python
telemetry = TelemetryCollector(output_dir=Path("./telemetry"))

# Start
telemetry.start_session("session-123", "Research prompt")

# Record events
telemetry.record_stage_event(
    "session-123", "search", "completed",
    attempt=2, duration=8.5, details={"sources": 48}
)

# Complete
telemetry.complete_session(
    "session-123", success=True, total_duration=120.5
)

# Query
metrics = telemetry.get_session_metrics("session-123")
print(metrics.total_duration_seconds)
print(metrics.total_retries)
```

---

## CLI

### Commands

#### run

Execute a new workflow.

```bash
python -m prowzi.cli.main run <prompt> [options]
```

**Options**:
- `--documents`, `-d`: Document paths (space-separated)
- `--max-results`: Max results per query (default: 12)
- `--max-sections`: Max sections in draft (default: 8)
- `--enable-checkpoints`: Enable checkpointing

**Example**:
```bash
python -m prowzi.cli.main run "Write a research paper on quantum computing" \
    --documents paper1.pdf paper2.pdf \
    --max-results 15 \
    --enable-checkpoints
```

#### resume

Resume from checkpoint.

```bash
python -m prowzi.cli.main resume <checkpoint_id>
```

**Example**:
```bash
python -m prowzi.cli.main resume abc123-def456
```

#### sessions

List recent workflow sessions.

```bash
python -m prowzi.cli.main sessions [--limit N]
```

**Options**:
- `--limit`: Number of sessions to show (default: 20)

**Example**:
```bash
python -m prowzi.cli.main sessions --limit 50
```

#### show

Show details for a specific session.

```bash
python -m prowzi.cli.main show <session_id>
```

**Example**:
```bash
python -m prowzi.cli.main show abc123-def456
```

#### monitor

Live monitoring of workflow execution.

```bash
python -m prowzi.cli.main monitor <session_id>
```

**Example**:
```bash
python -m prowzi.cli.main monitor abc123-def456
```

---

## Tools

### Parsing Tools

```python
from prowzi.tools.parsing_tools import (
    parse_document,
    parse_pdf,
    parse_docx,
    parse_markdown,
    parse_txt
)
```

#### parse_document

```python
async def parse_document(file_path: Path) -> Dict[str, Any]
```

Auto-detects format and parses document.

**Returns**:
```python
{
    "content": str,
    "metadata": {
        "title": str,
        "author": str,
        "pages": int,
        "word_count": int,
    }
}
```

---

### Search Tools

```python
from prowzi.tools.search_tools import (
    SearchAPI,
    GoogleScholarAPI,
    PubMedAPI,
    ArXivAPI,
    SemanticScholarAPI
)
```

#### SearchAPI (Base Class)

```python
class SearchAPI:
    async def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]
```

**Returns**:
```python
[
    {
        "title": str,
        "authors": List[str],
        "year": int,
        "abstract": str,
        "url": str,
        "source": str,  # "google_scholar", "pubmed", etc.
        "citations": int,
        "doi": Optional[str],
    },
    ...
]
```

---

## Data Classes

### IntentAnalysis

```python
@dataclass
class IntentAnalysis:
    document_type: str              # "research_paper", "literature_review", etc.
    field: str                      # "computer_science", "biology", etc.
    academic_level: str             # "phd", "masters", "undergraduate"
    word_count: int                 # Target word count
    explicit_requirements: List[str]
    implicit_requirements: List[str]
    missing_info: List[str]
    confidence_score: float         # 0.0-1.0
    requires_user_input: bool
    citation_style: Optional[str]   # "APA", "MLA", "Chicago", etc.
    region: Optional[str]
    timeframe: Optional[str]
    parsed_documents: List[Dict[str, Any]]
```

---

### ResearchPlan

```python
@dataclass
class ResearchPlan:
    search_queries: List[SearchQuery]
    section_templates: List[SectionTemplate]
    estimated_timeline: Dict[str, float]
    resource_requirements: Dict[str, Any]
    success_criteria: List[str]
    quality_checkpoints: List[str]
    contingency_plans: List[str]
```

---

### SearchAgentResult

```python
@dataclass
class SearchAgentResult:
    sources: List[Dict[str, Any]]
    query_performance: Dict[str, Any]
    coverage_analysis: Dict[str, Any]
    source_metadata: Dict[str, Any]
```

---

### VerificationAgentResult

```python
@dataclass
class VerificationAgentResult:
    verified_sources: List[SourceVerification]
    average_score: float
    accepted_sources: List[str]
    rejected_sources: List[str]
    high_risk_sources: List[str]
    analyst_summary: str
    risk_flags: List[str]
    recommended_next_steps: List[str]
```

---

### WritingAgentResult

```python
@dataclass
class WritingAgentResult:
    outline: List[SectionOutline]
    sections: List[SectionDraft]
    total_word_count: int
    bibliography: List[str]
    style_guidelines: List[str]
    overall_strategy: str
    executive_summary: str
```

---

### EvaluationAgentResult

```python
@dataclass
class EvaluationAgentResult:
    total_score: float              # 0-100
    section_scores: Dict[str, float]
    strengths: List[str]
    improvements: List[str]
    risks: List[str]
    pass_threshold: bool
    recommendations: List[str]
```

---

### TurnitinAgentResult

```python
@dataclass
class TurnitinAgentResult:
    iterations: List[TurnitinIteration]
    final_report: TurnitinReport
    success: bool
    total_attempts: int
```

---

### ProwziOrchestrationResult

```python
@dataclass
class ProwziOrchestrationResult:
    intent: IntentAnalysis
    plan: ResearchPlan
    search: SearchAgentResult
    verification: VerificationAgentResult
    draft: WritingAgentResult
    evaluation: EvaluationAgentResult
    turnitin: TurnitinAgentResult
    metadata: Dict[str, Any]
```

**Metadata includes**:
- `session_id`: Unique session identifier
- `workflow_duration_seconds`: Total execution time
- `turnitin_attempts`: Number of Turnitin iterations
- `turnitin_success`: Whether thresholds were met
- `re_evaluated`: Whether post-Turnitin evaluation ran
- `final_evaluation_score`: Final quality score
- `stage_metrics`: Per-stage execution stats

---

## Type Aliases

```python
ProgressCallback = Callable[[str, Dict[str, Any]], Awaitable[None]]
```

Progress callback signature for tracking workflow execution.

**Parameters**:
- `stage` (str): Stage name ("intent", "planning", etc.)
- `payload` (Dict[str, Any]): Stage-specific data

**Example**:
```python
async def my_progress_callback(stage: str, payload: Dict[str, Any]) -> None:
    print(f"Stage {stage} completed: {payload}")

result = await orchestrator.run_research(
    prompt="...",
    progress_callback=my_progress_callback
)
```

---

## Error Handling

### Common Exceptions

```python
# Configuration errors
ConfigurationError: Raised when config is invalid

# Agent errors
AgentExecutionError: Raised when agent execution fails
ModelNotAvailableError: Raised when model is unavailable

# Checkpoint errors
CheckpointNotFoundError: Raised when checkpoint doesn't exist
CheckpointCorruptedError: Raised when checkpoint can't be loaded

# Search errors
SearchAPIError: Raised when search API fails
RateLimitError: Raised when rate limit exceeded
```

### Example Error Handling

```python
from prowzi.workflows import ProwziOrchestrator
from prowzi.exceptions import AgentExecutionError, CheckpointNotFoundError

orchestrator = ProwziOrchestrator()

try:
    result = await orchestrator.run_research(prompt="...")
except AgentExecutionError as e:
    print(f"Agent failed: {e}")
    # Handle agent failure
except RateLimitError as e:
    print(f"Rate limited: {e}")
    # Implement backoff
except Exception as e:
    print(f"Unexpected error: {e}")
    # General error handling
```

---

## Best Practices

### 1. Always Use Config Objects

```python
# Good
config = get_config()
config.enable_checkpointing = True
orchestrator = ProwziOrchestrator(config=config)

# Avoid
orchestrator = ProwziOrchestrator()
orchestrator.config.enable_checkpointing = True  # Don't mutate after construction
```

### 2. Enable Checkpointing for Long Workflows

```python
config.enable_checkpointing = True  # Always for production
```

### 3. Use Progress Callbacks for Monitoring

```python
async def progress_callback(stage: str, payload: Dict[str, Any]):
    logger.info(f"Stage {stage}: {payload}")

result = await orchestrator.run_research(
    prompt="...",
    progress_callback=progress_callback
)
```

### 4. Handle Resume Scenarios

```python
try:
    result = await orchestrator.resume_from_checkpoint(checkpoint_id)
except CheckpointNotFoundError:
    # Start fresh
    result = await orchestrator.run_research(prompt="...")
```

### 5. Export Telemetry Regularly

```python
from prowzi.workflows import TelemetryCollector

telemetry = TelemetryCollector(output_dir=Path("./telemetry"))
metrics = telemetry.list_sessions(limit=100)

# Export to monitoring system
for session in metrics:
    await export_to_datadog(session)
```

---

## Version Compatibility

**Current Version**: 1.0.0  
**Framework**: Microsoft Agent Framework v1.0.0b251007  
**Python**: 3.10, 3.11, 3.12, 3.13

**Breaking Changes from v0.x**:
- None (first stable release)

---

**Last Updated**: October 15, 2025  
**API Status**: Stable (v1.0.0)
