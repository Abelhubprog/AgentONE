# AgentONE Examples - Production-Ready Multi-Agent Systems

This directory contains comprehensive examples demonstrating how to build world-class autonomous multi-agent systems using Microsoft Agent Framework with OpenRouter.

## 🎯 Overview

These examples progress from basic single-agent interactions to advanced autonomous multi-agent workflows, covering all patterns needed for enterprise-grade AI systems:

1. **Basic OpenRouter Integration** - Single agent with tools
2. **Sequential Workflows** - Multi-agent collaboration with handoffs
3. **Magentic Workflows** - Autonomous agents with dynamic planning

## 📋 Prerequisites

### 1. Environment Setup

```powershell
# Install uv package manager (if not already installed)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Navigate to python directory
cd python

# Create virtual environment with Python 3.13
uv sync --dev

# Activate virtual environment
.\.venv\Scripts\Activate.ps1
```

### 2. OpenRouter Configuration

Get your API key from [https://openrouter.ai/keys](https://openrouter.ai/keys)

Edit `python/.env`:
```env
OPENAI_API_KEY=sk-or-v1-your-actual-key-here
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_CHAT_MODEL_ID=openai/gpt-4o-mini
```

**💡 Recommended Models:**
- **Cost-Effective Testing**: `openai/gpt-4o-mini`, `deepseek/deepseek-chat`
- **High Performance**: `openai/gpt-4-turbo`, `anthropic/claude-3.5-sonnet`
- **Specialized**: `google/gemini-2.0-flash`, `meta-llama/llama-3.1-70b-instruct`

See all models at: [https://openrouter.ai/models](https://openrouter.ai/models)

## 🚀 Running Examples

### Example 1: Basic OpenRouter Integration

**File**: `01_openrouter_basic.py`

Demonstrates fundamental concepts:
- Environment-based configuration
- Explicit configuration with headers
- Function/tool calling
- Streaming vs non-streaming responses
- Multiple model providers

```powershell
uv run python examples/01_openrouter_basic.py
```

**What you'll learn:**
- ✅ How to connect Microsoft Agent Framework to OpenRouter
- ✅ Function/tool calling with autonomous agents
- ✅ Streaming responses for real-time interaction
- ✅ Switching between different LLM providers seamlessly

---

### Example 2: Sequential Multi-Agent Workflows

**File**: `02_sequential_workflow.py`

Demonstrates intermediate patterns:
- Specialized agent roles (Writer & Reviewer)
- Sequential execution with handoffs
- Iterative refinement loops
- Shared tools across agents
- Thread persistence for context

```powershell
uv run python examples/02_sequential_workflow.py
```

**What you'll learn:**
- ✅ Creating specialized agents with distinct expertise
- ✅ Sequential workflows with agent-to-agent handoffs
- ✅ Iterative refinement patterns (writer → reviewer → refined output)
- ✅ Context preservation across multiple turns
- ✅ Quality control through automated review

**Use Cases:**
- Content creation and editing pipelines
- Code generation with automated review
- Research and fact-checking workflows
- Multi-stage data processing

---

### Example 3: Advanced Magentic Workflows

**File**: `03_magentic_workflow.py`

Demonstrates advanced autonomous patterns:
- Dynamic agent selection and task delegation
- Self-organizing multi-agent collaboration
- Fact ledger for progress tracking
- Event streaming for observability
- Checkpoint/resume for fault tolerance

```powershell
uv run python examples/03_magentic_workflow.py
```

**⚠️ Note**: This example uses multiple LLM calls and may take several minutes. Use cost-effective models for testing.

**What you'll learn:**
- ✅ Autonomous multi-agent orchestration
- ✅ Dynamic planning and task decomposition
- ✅ Self-organizing agent teams
- ✅ Production-grade fault tolerance with checkpointing
- ✅ Real-time monitoring and observability
- ✅ Human-in-the-loop approval patterns

**Use Cases:**
- Complex research and analysis tasks
- Autonomous problem-solving systems
- Long-running workflows requiring fault tolerance
- Enterprise AI orchestration platforms

## 🏗️ Architecture Patterns

### Pattern 1: Single Agent (Example 1)
```
User → Agent (with tools) → Response
```
Best for: Simple tasks, direct Q&A, single-domain operations

### Pattern 2: Sequential Pipeline (Example 2)
```
User → Writer Agent → Reviewer Agent → Refined Output
         ↓               ↓
    [iterate until approved]
```
Best for: Multi-stage processing, quality-controlled outputs, content pipelines

### Pattern 3: Autonomous Collaboration (Example 3)
```
User Task → Orchestrator (Magentic)
              ↓
    [Dynamic Agent Selection]
              ↓
    Agent₁ ↔ Agent₂ ↔ Agent₃ ↔ ... ↔ Agentₙ
              ↓
    [Self-Organizing Collaboration]
              ↓
         Final Result
```
Best for: Complex problem-solving, research, autonomous systems, enterprise workflows

## 💡 Key Concepts

### Agents
- **Specialized Instructions**: Each agent has domain-specific expertise
- **Tools/Functions**: Agents can call external functions autonomously
- **Context Providers**: Share context across agent invocations
- **Middleware**: Intercept and modify agent behavior

### Workflows
- **Sequential**: Deterministic agent chains with explicit handoffs
- **Concurrent**: Parallel agent execution with result aggregation
- **Magentic**: Autonomous collaboration with dynamic planning

### Production Considerations
- **Checkpointing**: Save/resume workflows for fault tolerance
- **Observability**: Real-time event streaming and logging
- **Error Handling**: Retry logic, graceful degradation
- **Cost Management**: Model selection, rate limiting, caching

## 📊 Performance & Cost

### Estimated Costs (OpenRouter pricing as of Oct 2025)

**Example 1** (Basic):
- ~3-5 API calls per run
- Cost: ~$0.001 - $0.005 with gpt-4o-mini

**Example 2** (Sequential):
- ~6-12 API calls per run (depends on iterations)
- Cost: ~$0.005 - $0.02 with gpt-4o-mini

**Example 3** (Magentic):
- ~15-30+ API calls per run (depends on complexity)
- Cost: ~$0.02 - $0.10 with gpt-4o-mini

💡 **Cost Optimization Tips:**
1. Use cheaper models for testing (`gpt-4o-mini`, `deepseek-chat`)
2. Implement caching for repeated queries
3. Set `max_turns` limit on workflows
4. Use streaming to detect and stop unnecessary calls
5. Monitor usage with OpenRouter dashboard

## 🔧 Advanced Configuration

### Custom Headers for OpenRouter

```python
from agent_framework.openai import OpenAIChatClient

client = OpenAIChatClient(
    base_url="https://openrouter.ai/api/v1",
    model_id="openai/gpt-4o-mini",
    default_headers={
        "HTTP-Referer": "https://your-app.com",
        "X-Title": "Your App Name",
    }
)
```

### Using Different Models Per Agent

```python
research_agent = OpenAIChatClient(
    model_id="anthropic/claude-3.5-sonnet"
).create_agent(name="Researcher", instructions="...")

writer_agent = OpenAIChatClient(
    model_id="openai/gpt-4o-mini"  # Cheaper for writing
).create_agent(name="Writer", instructions="...")
```

### Checkpoint Storage

```python
from agent_framework._workflows import FileCheckpointStorage

# File-based (development)
checkpoint = FileCheckpointStorage("./checkpoints")

# For production, implement custom CheckpointStorage:
# - Database backend (PostgreSQL, MongoDB)
# - Redis for distributed systems
# - Cloud storage (S3, Azure Blob)
```

## 🎓 Learning Path

### Beginner
1. Run Example 1 to understand basic agent creation
2. Experiment with different models and tools
3. Try streaming vs non-streaming responses

### Intermediate
1. Run Example 2 to see sequential workflows
2. Modify agent instructions for different tasks
3. Add custom tools and functions
4. Experiment with thread persistence

### Advanced
1. Run Example 3 to experience autonomous collaboration
2. Implement custom checkpoint storage
3. Add observability with OpenTelemetry
4. Create domain-specific agent teams
5. Build production workflows with error handling

## 🚢 Production Deployment Checklist

- [ ] **API Key Management**: Use secrets manager (Azure Key Vault, AWS Secrets Manager)
- [ ] **Rate Limiting**: Implement backoff and retry logic
- [ ] **Monitoring**: OpenTelemetry, application insights, custom metrics
- [ ] **Error Handling**: Graceful degradation, fallback models
- [ ] **Cost Controls**: Budget alerts, usage tracking, model selection
- [ ] **Checkpointing**: Persistent storage for long-running workflows
- [ ] **Security**: Input validation, output sanitization, PII redaction
- [ ] **Testing**: Unit tests, integration tests, load tests
- [ ] **Documentation**: API docs, runbooks, architecture diagrams

## 📚 Additional Resources

### Microsoft Agent Framework
- [GitHub Repository](https://github.com/microsoft/agent-framework)
- [Python Documentation](https://github.com/microsoft/agent-framework/tree/main/python)
- [.NET Documentation](https://github.com/microsoft/agent-framework/tree/main/dotnet)

### OpenRouter
- [Documentation](https://openrouter.ai/docs)
- [Models & Pricing](https://openrouter.ai/models)
- [API Keys](https://openrouter.ai/keys)

### Design Documents
- [ADR-0005: Python Naming Conventions](../docs/decisions/0005-python-naming-conventions.md)
- [Workflow Architecture](../docs/design/)

## 🤝 Contributing

Found an issue or want to add an example? Contributions welcome!

1. Create examples that demonstrate specific patterns
2. Include comprehensive docstrings and comments
3. Follow the project's coding standards (see `python/DEV_SETUP.md`)
4. Test with multiple models to ensure compatibility

## 📄 License

Copyright (c) Microsoft. All rights reserved.

Licensed under the MIT License.
