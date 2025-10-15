# Prowzi Architecture Documentation

## System Overview

Prowzi is a production-ready academic research automation system built on **Microsoft Agent Framework v1.0.0b251007**. It orchestrates 10 specialized AI agents through a resilient, observable workflow pipeline to produce high-quality research documents.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Prowzi Research System                               │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      Agent Pipeline (Sequential)                        │ │
│  │                                                                         │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐          │ │
│  │  │ Intent   │─▶│ Planning │─▶│  Search  │─▶│ Verification │          │ │
│  │  │ Agent    │  │ Agent    │  │  Agent   │  │    Agent     │          │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘          │ │
│  │       │              │             │                │                   │ │
│  │       ▼              ▼             ▼                ▼                   │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                             │ │
│  │  │ Writing  │─▶│Evaluation│─▶│ Turnitin │                             │ │
│  │  │ Agent    │  │  Agent   │  │  Agent   │                             │ │
│  │  └──────────┘  └──────────┘  └──────────┘                             │ │
│  │                                                                         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                     │                                        │
│                                     ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      Orchestrator (Workflow Engine)                     │ │
│  │  • Staged Execution: Sequential with conditional branching              │ │
│  │  • Resilience: Per-stage retries with exponential backoff               │ │
│  │  • Observability: Real-time telemetry + checkpoint persistence          │ │
│  │  • Context Management: Passes results between agents                    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                     │                                        │
│                    ┌────────────────┴────────────────┐                      │
│                    ▼                                 ▼                      │
│  ┌───────────────────────────────┐   ┌───────────────────────────────┐    │
│  │    CheckpointManager          │   │    TelemetryCollector         │    │
│  │  • Pickle + JSON persistence  │   │  • Per-stage metrics          │    │
│  │  • Resume from any stage      │   │  • Workflow aggregates        │    │
│  │  • State restoration          │   │  • JSON export                │    │
│  └───────────────────────────────┘   └───────────────────────────────┘    │
│                                                                              │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       ▼
                    ┌──────────────────────────────────────┐
                    │      External Interfaces              │
                    ├──────────────────────────────────────┤
                    │ • CLI (Rich Terminal UI)             │
                    │ • Python API                         │
                    │ • Progress Callbacks                 │
                    │ • Telemetry Export (JSON)            │
                    └──────────────────────────────────────┘
```

---

## Component Architecture

### 1. Agent Layer

Each agent is a specialized AI component with:
- **Single Responsibility**: Focused on one aspect of research
- **Structured I/O**: Type-safe dataclasses for inputs/outputs
- **Model Strategy**: Optimized model selection per task
- **Error Handling**: Graceful degradation with fallbacks

#### Agent Inventory

| Agent | Purpose | Input | Output | Model |
|-------|---------|-------|--------|-------|
| Intent | Analyze requirements | Prompt + Documents | IntentAnalysis | Claude 4.5 + GPT-4o |
| Planning | Create research plan | IntentAnalysis | ResearchPlan | GPT-4o |
| Search | Execute searches | ResearchPlan | SearchAgentResult | GPT-4o Mini |
| Verification | Validate sources | SearchAgentResult | VerificationAgentResult | GPT-4o |
| Writing | Generate draft | Plan + Search + Verification | WritingAgentResult | Claude 4.5 |
| Evaluation | Score quality | Draft + Context | EvaluationAgentResult | GPT-4o |
| Turnitin | Detect plagiarism/AI | Draft | TurnitinAgentResult | GPT-4o |

### 2. Tool Layer

Specialized utilities supporting agents:

```
tools/
├── parsing_tools.py      # Document parsing (PDF, DOCX, Markdown, TXT)
├── search_tools.py       # Multi-API search (8+ search engines)
└── analysis_tools.py     # Source verification, quality scoring
```

**Parsing Tools**:
- PDF extraction with PyMuPDF
- DOCX parsing with python-docx
- Markdown and plain text support
- Metadata extraction

**Search Tools**:
- Google Scholar
- PubMed
- arXiv
- Semantic Scholar
- IEEE Xplore
- JSTOR
- Web of Science
- SpringerLink

**Analysis Tools**:
- Domain credibility scoring
- Citation pattern analysis
- Recency validation
- Methodology assessment

### 3. Orchestration Layer

**ProwziOrchestrator** manages workflow execution:

```python
class ProwziOrchestrator:
    """End-to-end workflow manager with resilience."""
    
    # Staged execution with conditional logic
    _stage_specs: List[_StageSpec] = [
        _StageSpec(name="intent", max_retries=2),
        _StageSpec(name="planning", max_retries=2),
        _StageSpec(name="search", max_retries=3, retry_backoff=2.0),
        _StageSpec(name="verification", max_retries=2),
        _StageSpec(name="writing", max_retries=2),
        _StageSpec(name="evaluation", max_retries=2),
        _StageSpec(name="turnitin", max_retries=3),
        _StageSpec(
            name="post_turnitin_evaluation",
            predicate=_should_run_post_turnitin_evaluation,
            max_retries=2
        ),
    ]
```

**Key Features**:
- **Per-stage retry logic**: Independent retry counts and backoff strategies
- **Conditional execution**: Predicate-based stage gating
- **Context passing**: Immutable context shared across stages
- **Metrics collection**: Duration, attempts, errors per stage

### 4. Persistence Layer

**CheckpointManager** (`workflows/checkpoint.py`):

```python
@dataclass
class WorkflowCheckpoint:
    metadata: CheckpointMetadata  # session_id, stage, timestamp
    intent: Optional[IntentAnalysis]
    plan: Optional[ResearchPlan]
    search: Optional[SearchAgentResult]
    verification: Optional[VerificationAgentResult]
    draft: Optional[WritingAgentResult]
    evaluation: Optional[EvaluationAgentResult]
    initial_evaluation: Optional[EvaluationAgentResult]
    turnitin: Optional[TurnitinAgentResult]
    stage_metrics: Dict[str, Any]
```

**Storage Strategy**:
- Pickle files (`.pkl`): Complete object graphs
- JSON metadata (`.json`): Human-readable summaries
- Atomic writes: Ensures consistency
- Versioning: Checkpoint IDs with stage names

### 5. Observability Layer

**TelemetryCollector** (`workflows/telemetry.py`):

```python
@dataclass
class StageMetrics:
    stage: str
    status: str  # started, completed, failed, skipped, retrying
    attempt: int
    duration_seconds: float
    timestamp: datetime
    details: Dict[str, Any]
    error: Optional[str]
```

**Data Flow**:
1. Orchestrator emits stage events
2. TelemetryCollector records to memory
3. Automatic JSON persistence on each event
4. Aggregation for workflow-level metrics

### 6. Configuration Layer

**ProwziConfig** (`config/settings.py`):

```python
class ProwziConfig:
    # Model configurations (4 tiers)
    models: Dict[str, ModelConfig]
    
    # Agent assignments
    intent_models: List[str]
    planning_model: str
    search_model: str
    # ...
    
    # System settings
    enable_checkpointing: bool
    enable_telemetry: bool
    checkpoint_dir: Path
    
    # Quality thresholds
    min_source_quality: float
    turnitin_similarity_threshold: float
    turnitin_ai_threshold: float
```

---

## Data Flow

### Complete Research Pipeline

```
User Prompt
    │
    ├─▶ Intent Agent
    │       ├─ Parse documents (if provided)
    │       ├─ Analyze requirements
    │       └─▶ IntentAnalysis
    │           ├─ document_type (e.g., "research_paper")
    │           ├─ field (e.g., "computer_science")
    │           ├─ academic_level ("phd", "masters", etc.)
    │           ├─ word_count (target)
    │           └─ requirements (explicit + implicit)
    │
    ├─▶ Planning Agent
    │       ├─ Decompose into tasks
    │       ├─ Generate search queries (6 types)
    │       └─▶ ResearchPlan
    │           ├─ search_queries (12-24 queries)
    │           ├─ section_templates
    │           └─ success_criteria
    │
    ├─▶ Search Agent
    │       ├─ Execute queries across 8+ APIs
    │       ├─ Deduplicate results
    │       └─▶ SearchAgentResult
    │           ├─ sources (48+ sources)
    │           ├─ query_performance
    │           └─ coverage_analysis
    │
    ├─▶ Verification Agent
    │       ├─ Validate each source
    │       ├─ Score credibility (0-1)
    │       └─▶ VerificationAgentResult
    │           ├─ verified_sources
    │           ├─ average_score
    │           ├─ accepted_sources
    │           └─ rejected_sources
    │
    ├─▶ Writing Agent
    │       ├─ Create outline
    │       ├─ Draft sections with citations
    │       ├─ Editorial review
    │       └─▶ WritingAgentResult
    │           ├─ outline
    │           ├─ sections (with inline citations)
    │           ├─ bibliography
    │           └─ total_word_count
    │
    ├─▶ Evaluation Agent
    │       ├─ Score against rubric
    │       ├─ Section-level feedback
    │       └─▶ EvaluationAgentResult
    │           ├─ total_score (0-100)
    │           ├─ section_scores
    │           ├─ strengths
    │           └─ improvements
    │
    ├─▶ Turnitin Agent
    │       ├─ Simulate plagiarism check
    │       ├─ Simulate AI detection
    │       ├─ Iterative redrafting (if needed)
    │       └─▶ TurnitinAgentResult
    │           ├─ iterations (redraft history)
    │           ├─ final_report
    │           │   ├─ similarity_score
    │           │   └─ ai_score
    │           └─ success (thresholds met)
    │
    └─▶ [Optional] Post-Turnitin Evaluation
            ├─ Re-score after redrafting
            └─▶ Updated EvaluationAgentResult
```

### Context Flow

```python
@dataclass
class _StageContext:
    """Shared context passed through pipeline."""
    
    # Input parameters
    prompt: str
    document_paths: Optional[List[str | Path]]
    additional_context: Optional[Dict[str, Any]]
    custom_constraints: Optional[Dict[str, Any]]
    max_results_per_query: int
    max_sections: int
    thresholds: Optional[TurnitinThresholds]
    progress_callback: Optional[ProgressCallback]
    
    # Agent results (populated sequentially)
    intent: Optional[IntentAnalysis] = None
    plan: Optional[ResearchPlan] = None
    search: Optional[SearchAgentResult] = None
    verification: Optional[VerificationAgentResult] = None
    draft: Optional[WritingAgentResult] = None
    evaluation: Optional[EvaluationAgentResult] = None
    initial_evaluation: Optional[EvaluationAgentResult] = None
    turnitin: Optional[TurnitinAgentResult] = None
    stage_metrics: Dict[str, Any] = field(default_factory=dict)
```

---

## Model Selection Strategy

### Multi-Tier Architecture

```python
# Tier 1: Premium (Complex reasoning, large context)
models = {
    "claude-4.5-sonnet": ModelConfig(
        cost_per_1m_input=3.0,
        context_window=1_000_000,
        tier="premium"
    ),
}

# Tier 2: Advanced (Structured output, reliability)
models = {
    "gpt-4o": ModelConfig(
        cost_per_1m_input=2.5,
        context_window=128_000,
        tier="advanced"
    ),
}

# Tier 3: Standard (Balanced performance)
models = {
    "gpt-4o-mini": ModelConfig(
        cost_per_1m_input=0.15,
        context_window=128_000,
        tier="standard"
    ),
}

# Tier 4: Efficient (High-volume, simple tasks)
models = {
    "gemini-2.0-flash": ModelConfig(
        cost_per_1m_input=0.0,
        context_window=1_000_000,
        tier="efficient"
    ),
}
```

### Agent-Model Mapping

| Agent | Primary Model | Fallback | Rationale |
|-------|---------------|----------|-----------|
| Intent (parsing) | Claude 4.5 | GPT-4o | 1M context for long docs |
| Intent (analysis) | GPT-4o | GPT-4o Mini | Structured output |
| Planning | GPT-4o | GPT-4o Mini | Complex decomposition |
| Search | GPT-4o Mini | Gemini Flash | High-volume queries |
| Verification | GPT-4o | GPT-4o Mini | Quality-critical |
| Writing | Claude 4.5 | GPT-4o | Creative + long-form |
| Evaluation | GPT-4o | GPT-4o Mini | Rubric scoring |
| Turnitin | GPT-4o | GPT-4o Mini | Redrafting logic |

---

## Resilience Patterns

### 1. Per-Stage Retries

```python
@dataclass
class _StageSpec:
    name: str
    executor: Callable
    max_retries: int = 1
    retry_backoff: float = 1.5
    predicate: Optional[Callable] = None
```

**Retry Logic**:
```python
attempt = 0
while attempt < spec.max_retries:
    attempt += 1
    try:
        result = await spec.executor(context)
        break  # Success
    except Exception as exc:
        if attempt >= spec.max_retries:
            raise  # Exhausted retries
        backoff = spec.retry_backoff ** attempt
        await asyncio.sleep(backoff)
```

### 2. Graceful Degradation

Each agent has **heuristic fallbacks**:

```python
# Writing Agent example
try:
    sections = await self._draft_with_llm(outline, sources)
except Exception:
    logger.warning("LLM drafting failed, using heuristic fallback")
    sections = self._draft_with_heuristics(outline, sources)
```

### 3. Checkpoint Recovery

```python
# Automatic checkpoint saves
if self.checkpoint_manager and self.config.enable_checkpointing:
    self._save_checkpoint(session_id, stage_name, context)

# Resume logic
if checkpoint_id and self.checkpoint_manager:
    checkpoint = self.checkpoint_manager.load_checkpoint(checkpoint_id)
    context = self._restore_context_from_checkpoint(checkpoint, ...)
    # Skip completed stages
    for idx, spec in enumerate(self._stage_specs):
        if spec.name == checkpoint.metadata.stage:
            start_stage_idx = idx + 1
```

### 4. Telemetry Tracking

```python
# Record all stage transitions
telemetry.record_stage_event(
    session_id=session_id,
    stage=stage_name,
    status="completed",  # or "retrying", "failed"
    attempt=attempt_number,
    duration=duration_seconds,
    details=stage_metrics,
    error=error_message
)
```

---

## Extensibility Points

### 1. Adding New Agents

```python
# 1. Define agent class
class NewAgent:
    def __init__(self, config: ProwziConfig):
        self.config = config
        self.client = get_chat_client(config.new_agent_model)
    
    async def execute(self, context: YourContext) -> YourResult:
        # Agent logic
        pass

# 2. Add to orchestrator
class ProwziOrchestrator:
    def __init__(self, config):
        # ...
        self.new_agent = NewAgent(config)
        
        self._stage_specs.append(
            _StageSpec(name="new_stage", executor=self._stage_new, max_retries=2)
        )
    
    async def _stage_new(self, context: _StageContext):
        result = await self.new_agent.execute(...)
        context.new_result = result
        return event_payload, detail_metrics
```

### 2. Custom Search APIs

```python
# tools/search_tools.py
class CustomSearchAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def search(self, query: str) -> List[Dict[str, Any]]:
        # Implement API call
        pass

# Register in config
config.search_apis["custom_api"] = {
    "class": CustomSearchAPI,
    "api_key": os.getenv("CUSTOM_API_KEY")
}
```

### 3. Custom Progress Callbacks

```python
async def custom_callback(stage: str, payload: Dict[str, Any]) -> None:
    """Send progress to external system."""
    await send_to_slack(f"Stage {stage} completed: {payload}")
    await update_dashboard(stage, payload)

result = await orchestrator.run_research(
    prompt="...",
    progress_callback=custom_callback
)
```

### 4. Custom Telemetry Export

```python
from prowzi.workflows.telemetry import TelemetryCollector

telemetry = TelemetryCollector(output_dir=Path("./telemetry"))
metrics = telemetry.load_session(session_id)

# Export to monitoring system
await export_to_prometheus(metrics)
await export_to_datadog(metrics)
await export_to_cloudwatch(metrics)
```

---

## Performance Characteristics

### Latency Breakdown (Typical 10,000-word paper)

| Stage | Duration | Retries | Dominant Factor |
|-------|----------|---------|-----------------|
| Intent | 2-5s | Rare | Document parsing |
| Planning | 3-8s | Rare | Query generation |
| Search | 15-45s | Moderate | API rate limits |
| Verification | 8-20s | Rare | LLM calls per source |
| Writing | 60-180s | Low | Long-form generation |
| Evaluation | 5-15s | Rare | Rubric scoring |
| Turnitin | 10-120s | High | Iterative redrafting |

**Total**: 100-400 seconds (~2-7 minutes)

### Cost Estimation

| Model | Input Cost | Output Cost | Typical Usage |
|-------|------------|-------------|---------------|
| Claude 4.5 | $3.00/1M | $15.00/1M | 50K in + 20K out |
| GPT-4o | $2.50/1M | $10.00/1M | 100K in + 30K out |
| GPT-4o Mini | $0.15/1M | $0.60/1M | 200K in + 50K out |

**Typical 10K-word paper**: $0.50 - $2.00 per workflow

### Scalability

- **Concurrent workflows**: Limited by API rate limits (not system)
- **Checkpoint storage**: ~100KB per checkpoint × 8 stages = 800KB/workflow
- **Telemetry storage**: ~20KB per session
- **Memory footprint**: ~50-200MB per active workflow

---

## Security Considerations

### 1. API Key Management

```python
# Never hardcode keys
api_key = os.getenv("OPENAI_API_KEY")

# Use .env files (gitignored)
# .env
OPENAI_API_KEY=sk-or-v1-...
```

### 2. Document Handling

- Documents parsed in-memory (no temp files)
- Sensitive content never logged
- Configurable retention policies for checkpoints

### 3. Rate Limiting

```python
# Built into search tools
class SearchTool:
    async def search_with_backoff(self, query: str):
        for attempt in range(max_retries):
            try:
                return await self.api.search(query)
            except RateLimitError:
                await asyncio.sleep(2 ** attempt)
```

### 4. Input Validation

```python
# Intent agent validates all inputs
if word_count < 100 or word_count > 100_000:
    raise ValueError("Word count must be 100-100,000")

if not is_valid_document_type(document_type):
    raise ValueError(f"Invalid document type: {document_type}")
```

---

## Future Enhancements

### Planned for v2.0

1. **Distributed Execution**
   - Celery-based task queue
   - Horizontal scaling for search/verification

2. **Advanced Checkpointing**
   - S3/Azure Blob storage
   - Incremental snapshots
   - Compression for large drafts

3. **Enhanced Observability**
   - OpenTelemetry integration
   - Grafana dashboards
   - Real-time alerting

4. **Collaborative Features**
   - Multi-user workflows
   - Review/approval stages
   - Version control for drafts

5. **Advanced AI Features**
   - Agentic workflows with loops
   - Self-healing pipelines
   - Automated quality improvement

---

## References

- [Microsoft Agent Framework Docs](https://github.com/microsoft/AgentONE)
- [OpenRouter API](https://openrouter.ai/docs)
- [Implementation Status](IMPLEMENTATION_STATUS.md)
- [Production Readiness Guide](PRODUCTION_READINESS.md)
- [Checkpoint & Telemetry Docs](CHECKPOINT_TELEMETRY.md)

---

**Last Updated**: October 15, 2025  
**Framework Version**: Microsoft Agent Framework v1.0.0b251007  
**Architecture Status**: Production-Ready (95% complete)
