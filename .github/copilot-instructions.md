# Microsoft Agent Framework & AgentONE - AI Coding Agent Instructions

## Project Overview

This repository contains TWO major codebases:

### 1. **Microsoft Agent Framework** (Primary)
Multi-language (.NET + Python) framework for building AI agents and multi-agent workflows. Supports simple chat agents, complex multi-agent orchestration, graph-based workflows, and the A2A (Agent-to-Agent) protocol.

**Location**: `python/packages/`, `dotnet/src/`, `dotnet/samples/`, `python/samples/`

### 2. **AgentONE/Prowzi Application** (Secondary)
Production autonomous research platform built ON TOP of Agent Framework. 7-agent orchestration for academic research with real-time WebSocket feedback, browser automation, and quality assurance.

**Location**: `agentic_layer/`, `overhaul/` (comprehensive 160K+ word implementation docs), `python/prowzi/`

⚠️ **CRITICAL**: When editing code, determine which codebase you're working in:
- Framework changes → Follow framework patterns (immutable, protocol-based)
- AgentONE changes → Follow application patterns (database sessions, orchestrator events)

## Architecture

### Microsoft Agent Framework

**Language-Specific Implementations**:
- **Python**: Modular packages in `python/packages/` (core, a2a, azure-ai, copilotstudio, mem0, redis, devui, lab)
- **.NET**: Organized in `dotnet/src/` with multi-targeting (net9.0, net8.0, netstandard2.0, net472)
- **Cross-language parity**: Both implementations follow similar patterns but with language-idiomatic naming (see ADR-0005)

### Key Architectural Patterns

**Workflows** use graph-based execution with:
- `Executor` abstraction for both agents and custom functions
- `WorkflowBuilder` for imperative workflow construction with `.add_edge()` chaining
- `WorkflowContext` for state management and message routing
- Checkpoint/restore capabilities via `CheckpointStorage` protocol (InMemory or File-based)
- Declarative YAML definitions (`.NET` only, Python coming) via `DeclarativeWorkflowBuilder`

**Multi-Agent Orchestration** supports:
- `ConcurrentBuilder` for fan-out/fan-in patterns with custom aggregators
- `SequentialBuilder` for chained execution
- `MagenticBuilder` for dynamic multi-agent collaboration with auto-planning
- A2A protocol integration for distributed agent communication

**Naming Conventions** (Python-specific, ADR-0005):
- `AgentProtocol` (not `Agent` or `AIAgent`) - protocol for agent implementations
- `ChatAgent` (not `ChatClientAgent`) - concrete agent using chat clients
- `ChatClientProtocol` (not `IChatClient`) - protocol for chat client implementations
- Remove `AI` prefix and `Chat` prefix where context is clear (e.g., `Role` not `ChatRole`)
- Use `Protocol` suffix for protocols, `Base` prefix for base classes

### AgentONE/Prowzi Application

**7-Agent Autonomous Workflow**:
```
User Input → Intent Context Agent → Planning Agent → Evidence Search Agent →
Verification Agent → Writing Agent → Evaluation Agent → Turnitin Agent → Result
```

**Key Components**:
- `agentic_layer/agent_orchestrator.py` - Master controller for sequential agent execution with state preservation
- `agentic_layer/agents/base_agent.py` - Base class for all Prowzi agents (NOT framework agents)
- `agentic_layer/context_manager.py` - ACE (Agentic Context Engineering) system for shared knowledge
- `overhaul/` - **START HERE**: 160K+ words of implementation strategy, architecture decisions, and checklists

**Architecture Pattern**: Each agent is a specialized worker with:
- Specific AI model selection (GPT-5, Claude 4.5, Gemini 2.5, etc. via OpenRouter)
- Database session for persistence (PostgreSQL + pgvector)
- WebSocket event emission for real-time UI updates
- Error recovery and retry logic
- Cost and performance tracking

**Critical Docs**:
- `overhaul/00_START_HERE_MASTER_INDEX.md` - Entry point to all implementation docs
- `overhaul/IMPLEMENTATION_STRATEGY.md` - 15K word implementation bible (READ FIRST)
- `overhaul/COMPLETE_ARCHITECTURE_MAP.md` - Visual system architecture
- Agent-specific docs: `07_INTENT_CONTEXT_AGENT.md`, `08_PLANNING_AGENT.md`, `09_EVIDENCE_SEARCH_AGENT.md`

## Development Workflows

### Python Setup & Commands
```bash
# Setup (requires uv >= 0.8.2)
uv python install 3.10 3.11 3.12 3.13
uv run poe setup -p 3.13  # Creates venv, installs deps, pre-commit hooks

# Development tasks (via poethepoet)
uv run poe test              # Run tests with coverage
uv run poe lint              # Lint and auto-fix
uv run poe fmt               # Format with ruff (120 char line length)
uv run poe pyright           # Type checking (Pyright)
uv run poe mypy              # Type checking (MyPy)
uv run poe check             # Run ALL quality checks

# Package-specific testing
cd packages/core && uv run poe test

# Running samples
cd samples/getting_started/workflows && uv run python orchestration/magentic.py
```

### .NET Build & Test
```bash
dotnet build dotnet/agent-framework-dotnet.slnx
dotnet test dotnet/agent-framework-dotnet.slnx
# Target-specific: net9.0, net8.0, netstandard2.0, net472
```

### Critical Conventions

**Python Code Style** (enforced by pre-commit):
- 120 character line length
- Google-style docstrings for all public APIs
- Max 3 positional params; use keyword-only for others
- Avoid forcing users to import extra modules - provide string literal alternatives (e.g., `tool_mode: Literal['auto', 'required', 'none'] | ChatToolMode`)
- Document `**kwargs` usage or use named params like `client_kwargs: dict[str, Any]`

**AgentONE Code Style**:
- FastAPI patterns with async/await throughout
- SQLAlchemy ORM with AsyncSession for database access
- Type hints mandatory (enforced by mypy)
- Comprehensive error handling with custom exceptions
- WebSocket event emission via `orchestrator_events_mixin.py`

**.NET Standards**:
- C# 13, nullable reference types enabled
- Treat warnings as errors
- AOT-compatible for .NET 7+ targets
- Generate XML documentation files for all projects

## Testing & Validation

**Python**: 80% minimum test coverage target. Tests in `packages/*/tests/` using pytest with:
- `pytest --import-mode=importlib` for module isolation
- `-n logical --dist loadfile --dist worksteal` for parallel execution
- Coverage reports: `uv run poe test`

**.NET**: Comprehensive unit tests in `dotnet/tests/` including integration tests for Azure AI, Copilot Studio, and workflows.

## Integration Points

### Agent Providers
- **Azure OpenAI**: `AzureOpenAIChatClient` (Python) / `AzureOpenAIClient.GetChatClient()` (.NET)
- **OpenAI**: `OpenAIChatClient` (Python) / `ChatClient` (.NET)
- **Azure AI Foundry**: `AzureAIClient` with project endpoints
- **Copilot Studio**: `CopilotstudioClient` for Microsoft Copilot Studio integration

### A2A Protocol
Cross-platform agent-to-agent communication:
- **Client**: `A2AAgent` wraps remote agents via AgentCard discovery (`.well-known/agent.json`)
- **Server**: `MapA2A()` extension methods expose agents via A2A endpoints
- See `dotnet/samples/A2AClientServer/` and `python/samples/getting_started/agents/a2a/`

### Observability
Built-in OpenTelemetry integration for distributed tracing. See:
- Python: `python/samples/getting_started/observability/`
- .NET: `dotnet/samples/GettingStarted/AgentOpenTelemetry/`

## Key Files & Patterns

**Workflow Construction** (Python):
- `python/packages/core/agent_framework/_workflows/_builder.py` - WorkflowBuilder
- `python/packages/core/agent_framework/_workflows/_executor.py` - Executor base & @executor decorator
- `python/packages/core/agent_framework/_workflows/_checkpoint.py` - Checkpointing system

**Orchestration Patterns**:
- Magentic: `python/samples/getting_started/workflows/orchestration/magentic.py`
- Concurrent: `python/samples/getting_started/workflows/orchestration/concurrent_agents.py`
- Sequential: `python/samples/getting_started/workflows/orchestration/sequential_agents.py`

**Declarative Workflows** (.NET):
- `dotnet/src/Microsoft.Agents.AI.Workflows.Declarative/DeclarativeWorkflowBuilder.cs` - YAML to workflow
- Sample YAML definitions: `workflow-samples/*.yaml`
- Code generation: `DeclarativeWorkflowBuilder.Eject()` converts YAML to C# code

**AgentONE Orchestrator Pattern**:
- Sequential agent execution with quality gates between stages
- State preservation via `ContextManager` and database persistence
- Real-time progress updates: `orchestrator.emit_event("agent_started", data)`
- Error recovery: Each agent has max 3 retries with exponential backoff
- Cost tracking: `session.total_cost` accumulated across all agent calls

## Common Patterns

**Creating Agents**:
```python
# Python
from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient

agent = ChatAgent(
    chat_client=AzureOpenAIChatClient(),
    instructions="You are a helpful assistant"
)
result = await agent.run("Hello!")
```

```csharp
// C#
using Microsoft.Agents.AI;
using Azure.AI.OpenAI;

var agent = new AzureOpenAIClient(endpoint, credential)
    .GetChatClient(deploymentName)
    .CreateAIAgent("Assistant", "You are helpful");

var result = await agent.RunAsync("Hello!");
```

**Workflow with Checkpointing** (Python):
```python
from agent_framework import WorkflowBuilder, FileCheckpointStorage

workflow = (
    WorkflowBuilder()
    .add_edge(agent1, agent2)
    .with_checkpointing(FileCheckpointStorage("./checkpoints"))
    .build()
)

# Resume from checkpoint
async for event in workflow.run_stream_from_checkpoint(checkpoint_id):
    ...
```

## Documentation & ADRs

- **Design Docs**: `docs/design/` - High-level architectural decisions
- **ADRs**: `docs/decisions/` - Specific technical decisions with rationale (see ADR template)
- **Samples**: Organized by complexity - start with `getting_started/agents`, then `workflows`
- **Migration Guides**: `dotnet/samples/SemanticKernelMigration/` for SK users

## Environment Configuration

Both Python and .NET use environment variables or `.env` files:
```bash
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_KEY=...  # Or use Azure CLI: az login

# Azure AI Foundry
AZURE_AI_PROJECT_ENDPOINT=https://...
AZURE_AI_MODEL_DEPLOYMENT_NAME=...

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_CHAT_MODEL_ID=gpt-4o-mini

# OpenRouter (for AgentONE)
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=sk-or-v1-...
```

Python: Pass `env_file_path="dev.env"` to client constructors for non-standard paths.

## AgentONE-Specific Workflows

When working with AgentONE agents:
1. **Always read implementation docs first**: `overhaul/IMPLEMENTATION_STRATEGY.md` before making changes
2. **Check agent-specific docs**: Each agent has a dedicated 10-15K word specification
3. **Follow the orchestrator pattern**: New agents must extend `BaseAgent` and emit WebSocket events
4. **Use ACE context**: Access shared knowledge via `self.context_manager.get_context()`
5. **Database sessions**: Always use `AsyncSession` and commit/rollback properly
6. **Model selection**: Choose appropriate model from OpenRouter based on task (see `model_dispatcher.py`)

**Example: Adding a new agent**
```python
from agentic_layer.agents.base_agent import BaseAgent

class NewAgent(BaseAgent):
    def __init__(self, config, db_session, context_manager):
        super().__init__(
            name="new_agent",
            model="anthropic/claude-3.5-sonnet",  # Select from OpenRouter
            config=config
        )
        self.db_session = db_session
        self.context_manager = context_manager

    async def execute(self, input_data):
        # Emit start event
        await self.emit_event("agent_started", {"agent": "new_agent"})

        # Access ACE context
        context = self.context_manager.get_context()

        # Do work
        result = await self.process(input_data)

        # Update database
        await self.save_to_db(result)

        # Emit completion
        await self.emit_event("agent_completed", {"result": result})

        return result
```
