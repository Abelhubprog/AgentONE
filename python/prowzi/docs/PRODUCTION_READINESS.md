# Prowzi Checkpoint & Telemetry Integration - Production Readiness Guide

## 🎯 Executive Summary

The Prowzi orchestrator now features **production-grade observability and fault tolerance** through integrated checkpoint persistence and real-time telemetry infrastructure. This enables:

- **Workflow Resumability**: Resume from any stage after interruptions
- **Operational Monitoring**: Real-time visibility into stage progress, retries, and latency
- **Audit Trails**: Complete telemetry history for compliance and debugging
- **Operator Dashboards**: Rich terminal UI for live workflow tracking

---

## 🚀 Quick Start

### Enable Checkpoints & Telemetry

```python
from prowzi.workflows import ProwziOrchestrator
from prowzi.config import get_config

# Configure
config = get_config()
config.enable_checkpointing = True  # Enable resume capability
config.enable_telemetry = True      # Enable metrics collection

# Run workflow
orchestrator = ProwziOrchestrator(config=config)
result = await orchestrator.run_research(
    prompt="Write a PhD thesis on quantum computing applications",
)

# Session ID for monitoring
session_id = result.metadata["session_id"]
print(f"✓ Workflow complete. Session: {session_id}")
```

### Resume After Interruption

```python
# If workflow was interrupted, resume from last checkpoint
result = await orchestrator.resume_from_checkpoint(
    checkpoint_id="abc123-def456"
)
```

### CLI Monitoring

```bash
# Run with checkpoints
python -m prowzi.cli.main run "Research prompt" --enable-checkpoints

# List recent sessions
python -m prowzi.cli.main sessions

# View session details
python -m prowzi.cli.main show abc123-def456

# Live monitoring (attach to running workflow)
python -m prowzi.cli.main monitor abc123-def456
```

---

## 📋 Architecture Overview

### Components

```
workflows/
├── checkpoint.py        # CheckpointManager - state persistence
├── telemetry.py         # TelemetryCollector - metrics tracking
└── orchestrator.py      # Integrated checkpoint + telemetry hooks

cli/
├── monitor.py           # WorkflowMonitor - rich terminal UI
└── main.py              # CLI commands for lifecycle management
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  Prowzi Orchestrator                         │
│                                                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐ │
│  │  Intent  │──▶│ Planning │──▶│  Search  │──▶│ Verify  │ │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬────┘ │
│       │              │              │              │        │
│       ▼              ▼              ▼              ▼        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         CheckpointManager (Pickle + JSON)           │   │
│  │  • Save after each successful stage                 │   │
│  │  • Resume from any checkpoint                       │   │
│  └─────────────────────────────────────────────────────┘   │
│       │              │              │              │        │
│       ▼              ▼              ▼              ▼        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │       TelemetryCollector (Real-time Metrics)        │   │
│  │  • Per-stage duration, retries, errors              │   │
│  │  • Workflow-level aggregates                        │   │
│  │  • JSON export for external systems                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
└───────────────────────────┼─────────────────────────────────┘
                            ▼
                   ┌─────────────────┐
                   │  CLI Monitor    │
                   │  (Rich UI)      │
                   │  • Live updates │
                   │  • Retry tracking│
                   │  • Latency viz  │
                   └─────────────────┘
```

---

## 💾 Checkpoint System

### How It Works

1. **Automatic Saving**: After each successful stage, orchestrator calls `CheckpointManager.save_checkpoint()`
2. **State Capture**: All agent results (intent, plan, search, etc.) serialized to pickle + JSON
3. **Resume Logic**: On startup, if `checkpoint_id` provided, load state and skip completed stages
4. **Idempotency**: Stages already completed are skipped; workflow continues from next stage

### Checkpoint Structure

```
prowzi_checkpoints/
├── abc123-def456_intent.pkl          # Pickled WorkflowCheckpoint
├── abc123-def456_intent.json         # Human-readable metadata
├── abc123-def456_planning.pkl
├── abc123-def456_planning.json
└── ...
```

### WorkflowCheckpoint Schema

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

### Resume Example

```python
# Workflow interrupted after search stage
# Checkpoints exist: intent, planning, search

# Resume
orchestrator = ProwziOrchestrator(config=config)
result = await orchestrator.resume_from_checkpoint("abc123-def456")

# Orchestrator will:
# 1. Load checkpoint (search is last completed stage)
# 2. Restore context (intent, plan, search results)
# 3. Skip intent, planning, search stages
# 4. Execute verification → writing → evaluation → turnitin
# 5. Save new checkpoints for remaining stages
```

---

## 📊 Telemetry System

### Metrics Collected

#### Per-Stage Metrics
```python
{
  "stage": "search",
  "status": "completed",        # started | completed | failed | retrying | skipped
  "attempt": 2,                 # Retry count
  "duration_seconds": 8.1,
  "timestamp": "2024-01-15T10:30:23Z",
  "details": {
    "sources_count": 48,
    "queries_executed": 12
  },
  "error": null
}
```

#### Workflow-Level Metrics
```python
{
  "session_id": "abc123-def456",
  "prompt": "Write research paper...",
  "started_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:45:30Z",
  "total_duration_seconds": 930.5,
  "total_retries": 3,
  "failed_stages": [],
  "success": true,
  "stages": [ /* per-stage metrics */ ]
}
```

### Telemetry Files

```
prowzi_checkpoints/telemetry/
├── telemetry_abc123-def456.json
├── telemetry_xyz789-ghi012.json
└── ...
```

### Export to External Systems

```python
from prowzi.workflows.telemetry import TelemetryCollector

telemetry = TelemetryCollector(output_dir=Path("./telemetry"))
metrics = telemetry.load_session("abc123-def456")

# Export to Prometheus
export_to_prometheus(metrics)

# Export to Splunk
export_to_splunk(metrics)

# Export to Datadog
send_to_datadog(metrics)
```

---

## 🖥️ CLI Monitoring Dashboard

### Live Monitoring

```bash
python -m prowzi.cli.main monitor abc123-def456
```

**Output**:
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
│ writing  │ ⋯       │   -     │     -    │ Pending              │
│ eval     │ ⋯       │   -     │     -    │ Pending              │
│ turnitin │ ⋯       │   -     │     -    │ Pending              │
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

### List Sessions

```bash
python -m prowzi.cli.main sessions --limit 20
```

**Output**:
```
╭─────────────────────────────────────────────────────────────────╮
│                  Recent Workflow Sessions                        │
├────────────┬──────────────────────┬────────┬────────┬──────────┤
│ Session ID │ Prompt               │ Status │ Retries│ Stages   │
├────────────┼──────────────────────┼────────┼────────┼──────────┤
│ abc123-d...│ Write research pape..│ ✓      │   3    │   7/7    │
│ xyz789-g...│ PhD thesis on quant..│ ✗      │   8    │   4/7    │
│ def456-a...│ Literature review o..│ ✓      │   1    │   7/7    │
╰────────────┴──────────────────────┴────────┴────────┴──────────╯
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# Enable checkpointing (default: false)
export PROWZI_ENABLE_CHECKPOINTING=true

# Checkpoint directory (default: ./prowzi_checkpoints)
export PROWZI_CHECKPOINT_DIR=/data/prowzi/checkpoints

# Enable telemetry (default: true)
export PROWZI_ENABLE_TELEMETRY=true
```

### Programmatic Configuration

```python
from prowzi.config import ProwziConfig
from pathlib import Path

config = ProwziConfig()
config.enable_checkpointing = True
config.enable_telemetry = True
config.checkpoint_dir = Path("/data/prowzi/checkpoints")
```

---

## 🛠️ Best Practices

### 1. Always Enable Telemetry in Production

```python
config.enable_telemetry = True  # Minimal overhead, critical visibility
```

### 2. Enable Checkpoints for Long Workflows

For workflows > 5 minutes or expensive stages (large search, complex writing):

```python
config.enable_checkpointing = True
```

### 3. Cleanup Old Checkpoints

```python
from datetime import datetime, timedelta
from pathlib import Path

def cleanup_old_checkpoints(checkpoint_dir: Path, days: int = 7):
    cutoff = datetime.now() - timedelta(days=days)
    for ckpt in checkpoint_dir.glob("*.pkl"):
        if ckpt.stat().st_mtime < cutoff.timestamp():
            ckpt.unlink()
            ckpt.with_suffix(".json").unlink(missing_ok=True)
```

### 4. Monitor Retry Patterns

High retries indicate:
- API rate limits → adjust retry backoff
- Network issues → check connectivity
- Model outages → verify OpenRouter status

```python
metrics = telemetry.load_session(session_id)
if metrics.total_retries > 5:
    logger.warning("High retry count: %d", metrics.total_retries)
```

### 5. Resume Strategy

When resuming:
1. Verify checkpoint exists
2. Check stage completion status
3. Ensure consistent parameters (thresholds, constraints)
4. Monitor for state inconsistencies

---

## 🧪 Testing Checkpoint & Telemetry

### Test Checkpoint Persistence

```python
# Save checkpoint
orchestrator.checkpoint_manager.save_checkpoint(
    session_id="test-123",
    stage="intent",
    prompt="Test prompt",
    context={"intent": intent_result},
    stage_metrics={"duration": 1.5}
)

# Load checkpoint
checkpoint = orchestrator.checkpoint_manager.load_checkpoint("test-123")
assert checkpoint.intent == intent_result
```

### Test Telemetry Recording

```python
telemetry = TelemetryCollector(output_dir=Path("./test_telemetry"))
telemetry.start_session(session_id="test-123", prompt="Test")
telemetry.record_stage_event(
    session_id="test-123",
    stage="intent",
    status="completed",
    duration=1.5
)
telemetry.complete_session(session_id="test-123", success=True, total_duration=10.0)

metrics = telemetry.get_session_metrics("test-123")
assert len(metrics.stages) == 1
assert metrics.total_duration_seconds == 10.0
```

---

## 🚀 Production Deployment Checklist

- [ ] Set `PROWZI_ENABLE_TELEMETRY=true`
- [ ] Configure checkpoint directory with sufficient storage
- [ ] Set up telemetry export to monitoring system (Prometheus, Datadog, etc.)
- [ ] Implement automated checkpoint cleanup (cron job or Lambda)
- [ ] Configure retry backoff parameters for production load
- [ ] Set up alerting on high retry counts or failed stages
- [ ] Document resume procedures for operators
- [ ] Test resume scenarios in staging environment

---

## 📚 References

- [Full Documentation](docs/CHECKPOINT_TELEMETRY.md)
- [Orchestrator Implementation](workflows/orchestrator.py)
- [Checkpoint Manager](workflows/checkpoint.py)
- [Telemetry Collector](workflows/telemetry.py)
- [CLI Monitor](cli/monitor.py)
- [Configuration Guide](config/settings.py)

---

## 🎯 Key Achievements

✅ **Production-Ready Observability**: Real-time monitoring with per-stage metrics  
✅ **Fault Tolerance**: Resume from any stage after interruption  
✅ **Operator Visibility**: Rich terminal UI with live updates  
✅ **Audit Compliance**: Complete telemetry history in JSON  
✅ **Zero-Config Defaults**: Works out of the box with sensible defaults  
✅ **Export-Ready**: Integrate with any external monitoring system  

**Status**: Checkpoint and telemetry infrastructure is **production-ready** and **fully integrated** into the Prowzi orchestrator. 🚀
