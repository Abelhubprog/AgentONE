# Checkpoint and Telemetry System

## Overview

The Prowzi orchestrator now includes production-grade **checkpoint persistence** and **real-time telemetry** infrastructure for workflow resumability and operational monitoring.

## Architecture

### Components

1. **CheckpointManager** (`workflows/checkpoint.py`)
   - Saves workflow state after each successful stage
   - Supports resume from any checkpoint
   - Pickle-based serialization with JSON metadata
   - Stores complete agent results for perfect state restoration

2. **TelemetryCollector** (`workflows/telemetry.py`)
   - Records per-stage metrics (duration, retries, errors)
   - Aggregates workflow-level statistics
   - JSON-based persistence for external analysis
   - Real-time event streaming for monitoring

3. **WorkflowMonitor** (`cli/monitor.py`)
   - Rich terminal UI for live monitoring
   - Stage-by-stage progress visualization
   - Retry and latency tracking
   - Session history and detail views

4. **CLI Interface** (`cli/main.py`)
   - Commands: `run`, `resume`, `sessions`, `show`, `monitor`
   - Full workflow lifecycle management
   - Checkpoint resume capability

## Configuration

### Environment Variables

```bash
# Enable checkpointing (default: false)
export PROWZI_ENABLE_CHECKPOINTING=true

# Checkpoint directory (default: ./prowzi_checkpoints)
export PROWZI_CHECKPOINT_DIR=/path/to/checkpoints

# Enable telemetry (default: true)
export PROWZI_ENABLE_TELEMETRY=true
```

### Programmatic Configuration

```python
from prowzi.config import ProwziConfig

config = ProwziConfig()
config.enable_checkpointing = True
config.enable_telemetry = True
config.checkpoint_dir = Path("./my_checkpoints")
```

## Usage

### 1. Running Workflows with Checkpoints

```python
from prowzi.workflows import ProwziOrchestrator
from prowzi.config import get_config

config = get_config()
config.enable_checkpointing = True
config.enable_telemetry = True

orchestrator = ProwziOrchestrator(config=config)

result = await orchestrator.run_research(
    prompt="Write a research paper on quantum computing",
    max_results_per_query=15,
)

# Session ID available in metadata
session_id = result.metadata["session_id"]
print(f"Workflow completed. Session: {session_id}")
```

### 2. Resuming from Checkpoint

```python
# Resume from checkpoint after interruption
result = await orchestrator.resume_from_checkpoint(
    checkpoint_id="abc123-def456",
)
```

### 3. Real-Time Monitoring

```python
from prowzi.cli.monitor import WorkflowMonitor, ProgressListener
from prowzi.workflows.telemetry import TelemetryCollector

# Create telemetry collector
telemetry = TelemetryCollector(output_dir=Path("./telemetry"))
session_id = "my-session-123"

# Create progress listener
progress_listener = ProgressListener(telemetry=telemetry, session_id=session_id)

# Run with live monitoring
result = await orchestrator.run_research(
    prompt="Research topic",
    progress_callback=progress_listener,
)
```

### 4. CLI Commands

```bash
# Run a new workflow
python -m prowzi.cli.main run "Write a research paper on AI safety" \
    --max-results 20 \
    --enable-checkpoints

# Resume from checkpoint
python -m prowzi.cli.main resume abc123-def456

# List recent sessions
python -m prowzi.cli.main sessions --limit 50

# Show session details
python -m prowzi.cli.main show abc123-def456

# Live monitor (attach to running workflow)
python -m prowzi.cli.main monitor abc123-def456
```

## Checkpoint Structure

### File Layout

```
prowzi_checkpoints/
├── abc123-def456_intent.pkl          # Pickled checkpoint
├── abc123-def456_intent.json         # Human-readable metadata
├── abc123-def456_planning.pkl
├── abc123-def456_planning.json
└── ...
```

### Checkpoint Data

```python
@dataclass
class WorkflowCheckpoint:
    metadata: CheckpointMetadata
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

## Telemetry Data

### Per-Stage Metrics

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

### Workflow Metrics

```python
@dataclass
class WorkflowMetrics:
    session_id: str
    prompt: str
    started_at: datetime
    completed_at: Optional[datetime]
    total_duration_seconds: float
    stages: List[StageMetrics]
    total_retries: int
    failed_stages: List[str]
    success: bool
    metadata: Dict[str, Any]
```

### Telemetry Files

```json
{
  "session_id": "abc123-def456",
  "prompt": "Write a research paper...",
  "started_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:45:30Z",
  "total_duration_seconds": 930.5,
  "total_retries": 3,
  "failed_stages": [],
  "success": true,
  "stages": [
    {
      "stage": "intent",
      "status": "completed",
      "attempt": 1,
      "duration_seconds": 2.3,
      "timestamp": "2024-01-15T10:30:02Z",
      "details": {
        "document_type": "research_paper",
        "field": "computer_science"
      }
    },
    {
      "stage": "search",
      "status": "retrying",
      "attempt": 1,
      "duration_seconds": 5.2,
      "timestamp": "2024-01-15T10:30:15Z",
      "error": "Rate limit exceeded"
    },
    {
      "stage": "search",
      "status": "completed",
      "attempt": 2,
      "duration_seconds": 8.1,
      "timestamp": "2024-01-15T10:30:23Z",
      "details": {
        "sources_count": 48
      }
    }
  ]
}
```

## Monitoring Dashboard

### Live Terminal UI

```
╭─────────────────────────────────────────────────────────────────╮
│ Prowzi Workflow Monitor - Session: abc123-d...                  │
├──────────┬─────────┬─────────┬──────────┬──────────────────────┤
│ Stage    │ Status  │ Attempt │ Duration │ Details              │
├──────────┼─────────┼─────────┼──────────┼──────────────────────┤
│ intent   │ ✓       │   1     │   2.30s  │                      │
│ planning │ ✓       │   1     │   3.45s  │                      │
│ search   │ ✓       │   2     │  13.31s  │ Sources: 48          │
│ verify   │ ⟳       │   1     │   5.20s  │ Retrying...          │
╰──────────┴─────────┴─────────┴──────────┴──────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ Summary                                                          │
├──────────────────────────────────────────────────────────────────┤
│ Total Duration: 24.26s                                           │
│ Stages: 3/7 completed                                            │
│ Total Retries: 2                                                 │
│ Success: In Progress                                             │
╰──────────────────────────────────────────────────────────────────╯
```

## Integration Patterns

### Custom Progress Callbacks

```python
async def my_progress_callback(stage: str, payload: Dict[str, Any]) -> None:
    """Custom handler for workflow progress events."""
    print(f"Stage {stage} completed: {payload}")
    # Send to external monitoring system
    await send_to_datadog(stage, payload)

result = await orchestrator.run_research(
    prompt="Research topic",
    progress_callback=my_progress_callback,
)
```

### Checkpoint Interval Control

```python
# Save checkpoint every N stages (default: every stage)
config.checkpoint_interval = 2  # Save every 2 stages

orchestrator = ProwziOrchestrator(config=config)
```

### Telemetry Export

```python
from prowzi.workflows.telemetry import TelemetryCollector

telemetry = TelemetryCollector(output_dir=Path("./telemetry"))

# Load session metrics
metrics = telemetry.load_session("abc123-def456")

# Export to external system
export_to_prometheus(metrics)
export_to_splunk(metrics)
```

## Best Practices

### 1. Enable Checkpointing for Long Workflows

For workflows with expensive stages (e.g., large search operations, complex writing):

```python
config.enable_checkpointing = True
```

### 2. Use Telemetry for Production Monitoring

Always enable telemetry in production to track:
- Stage durations and bottlenecks
- Retry patterns and failure modes
- Overall workflow success rates

### 3. Resume Strategy

When resuming from checkpoint:
1. Verify checkpoint integrity (`load_checkpoint`)
2. Check stage completion status
3. Resume with same or updated parameters
4. Monitor for consistency issues

### 4. Cleanup Old Checkpoints

```python
from datetime import datetime, timedelta
from pathlib import Path

def cleanup_old_checkpoints(checkpoint_dir: Path, days: int = 7) -> None:
    """Remove checkpoints older than N days."""
    cutoff = datetime.now() - timedelta(days=days)
    for checkpoint_file in checkpoint_dir.glob("*.pkl"):
        if checkpoint_file.stat().st_mtime < cutoff.timestamp():
            checkpoint_file.unlink()
            # Also remove metadata
            checkpoint_file.with_suffix(".json").unlink(missing_ok=True)
```

## Troubleshooting

### Checkpoint Not Found

```python
# Verify checkpoint exists
from prowzi.workflows.checkpoint import CheckpointManager

manager = CheckpointManager(checkpoint_dir=Path("./checkpoints"))
checkpoints = manager.list_checkpoints()
print([c["checkpoint_id"] for c in checkpoints])
```

### Telemetry Not Recording

1. Verify `enable_telemetry=True` in config
2. Check write permissions on telemetry directory
3. Inspect logs for serialization errors

### Resume Fails Mid-Stage

Checkpoints save **after** stage completion. If a stage fails:
1. Workflow will retry up to `max_retries`
2. If all retries fail, checkpoint remains at previous stage
3. Fix underlying issue and resume from last checkpoint

## Performance Considerations

### Checkpoint Overhead

- **Per-stage checkpoint**: ~50-200ms (pickle + JSON write)
- **Storage**: ~10-100KB per checkpoint (depends on agent results)
- **Recommendation**: Enable for workflows > 5 minutes duration

### Telemetry Overhead

- **Per-event**: ~5-10ms (in-memory update + JSON write)
- **Storage**: ~5-20KB per session
- **Recommendation**: Always enable (minimal overhead)

## Future Enhancements

Planned features for v2.0:
- [ ] Distributed checkpoint storage (S3, Azure Blob)
- [ ] Webhook notifications for stage completion
- [ ] Grafana dashboard for telemetry visualization
- [ ] Checkpoint compression for large agent results
- [ ] Incremental checkpointing (delta snapshots)
- [ ] Workflow replay from telemetry logs

## References

- [Orchestrator Implementation](workflows/orchestrator.py)
- [Checkpoint Manager](workflows/checkpoint.py)
- [Telemetry Collector](workflows/telemetry.py)
- [CLI Monitor](cli/monitor.py)
- [Configuration Guide](config/settings.py)
