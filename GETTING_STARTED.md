# 🚀 AgentONE - Getting Started Guide

> **Building the World's Most Advanced Autonomous Multi-Agent Systems**

Welcome to AgentONE! This guide will help you build production-ready, enterprise-grade autonomous multi-agent systems using Microsoft Agent Framework with OpenRouter.

## 📋 Table of Contents

1. [Quick Start](#-quick-start-5-minutes)
2. [Understanding the Architecture](#-understanding-the-architecture)
3. [Core Concepts](#-core-concepts)
4. [Building Your First Agent](#-building-your-first-agent)
5. [Multi-Agent Workflows](#-multi-agent-workflows)
6. [Production Deployment](#-production-deployment)
7. [Troubleshooting](#-troubleshooting)

---

## ⚡ Quick Start (5 Minutes)

### Step 1: Install Dependencies

```powershell
# Install uv package manager (if not installed)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Navigate to python directory
cd python

# Create virtual environment and install dependencies
uv sync --dev
```

### Step 2: Configure OpenRouter

1. Get your API key from [https://openrouter.ai/keys](https://openrouter.ai/keys)
2. Edit `python/.env`:

```env
OPENAI_API_KEY=sk-or-v1-your-actual-key-here
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_CHAT_MODEL_ID=openai/gpt-4o-mini
```

### Step 3: Verify Setup

```powershell
uv run python examples/00_verify_setup.py
```

You should see all tests pass! ✅

### Step 4: Run Your First Agent

```powershell
uv run python examples/01_openrouter_basic.py
```

🎉 Congratulations! You've just run your first autonomous agent!

---

## 🏗️ Understanding the Architecture

AgentONE leverages Microsoft Agent Framework's powerful architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                      Your Application                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Microsoft Agent Framework (Python)             │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │   Agents    │  │   Workflows  │  │  Orchestration  │   │
│  │             │  │              │  │                 │   │
│  │  • ChatAgent│  │  • Sequential│  │  • Magentic     │   │
│  │  • Custom   │  │  • Concurrent│  │  • Dynamic      │   │
│  │  • Tools    │  │  • Graph     │  │  • Autonomous   │   │
│  └─────────────┘  └──────────────┘  └─────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │      Observability & Infrastructure                 │   │
│  │  • OpenTelemetry • Checkpointing • Middleware      │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        OpenRouter                           │
│          (Unified Gateway to 100+ LLM Providers)           │
│                                                             │
│  • OpenAI (GPT-4, GPT-4o-mini)                            │
│  • Anthropic (Claude 3.5 Sonnet)                          │
│  • Google (Gemini 2.0 Flash)                              │
│  • Meta (Llama 3.1)                                       │
│  • Many more...                                            │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

1. **Agents**: Autonomous AI entities with specialized instructions and tools
2. **Workflows**: Orchestration patterns for multi-agent collaboration
3. **Tools/Functions**: External capabilities agents can invoke
4. **Chat Clients**: Connections to LLM providers (via OpenRouter)
5. **Middleware**: Cross-cutting concerns (logging, auth, rate limiting)
6. **Checkpointing**: Fault tolerance for long-running workflows

---

## 🧠 Core Concepts

### 1. Agents

Agents are autonomous AI entities that:
- Have specialized instructions (their "expertise")
- Can use tools/functions to interact with external systems
- Maintain conversation context via threads
- Can collaborate with other agents

**Example:**
```python
from agent_framework.openai import OpenAIChatClient

client = OpenAIChatClient()
agent = client.create_agent(
    name="ResearchAgent",
    instructions="You are an expert researcher specializing in technology.",
    tools=[search_web, analyze_data]
)

result = await agent.run("What are the latest trends in AI?")
```

### 2. Tools/Functions

Tools extend agent capabilities:
- Agents autonomously decide when to call tools
- Tools are regular Python functions with type hints
- Return values are automatically sent back to the agent

**Example:**
```python
from typing import Annotated

def get_weather(
    location: Annotated[str, "The city/location to check"],
) -> str:
    """Get current weather for a location."""
    # Your implementation
    return f"Weather in {location}: Sunny, 72°F"

agent = client.create_agent(
    name="WeatherBot",
    instructions="Help users with weather information.",
    tools=[get_weather]
)
```

### 3. Workflows

Workflows orchestrate multiple agents:

#### Sequential
Agents execute in a specific order with handoffs:
```python
Writer → Reviewer → Editor → Publisher
```

#### Concurrent
Agents execute in parallel, results are aggregated:
```python
┌→ Researcher1 ┐
├→ Researcher2 ├→ Aggregator → Final Result
└→ Researcher3 ┘
```

#### Magentic (Autonomous)
Agents self-organize and collaborate dynamically:
```python
Task → Orchestrator
         ↓
   [Autonomous Planning]
         ↓
   Agent Selection & Collaboration
         ↓
   Self-Organized Execution
         ↓
   Final Result
```

### 4. Threads

Threads maintain conversation context:
```python
thread = agent.get_new_thread()

# All messages in this thread share context
await agent.run("Hello, I'm working on a project", thread=thread)
await agent.run("Can you help me with the architecture?", thread=thread)
await agent.run("What did we discuss earlier?", thread=thread)
```

---

## 🔨 Building Your First Agent

### Simple Agent

```python
import asyncio
from agent_framework.openai import OpenAIChatClient

async def main():
    client = OpenAIChatClient()
    agent = client.create_agent(
        name="Assistant",
        instructions="You are a helpful assistant."
    )
    
    result = await agent.run("Tell me about autonomous agents.")
    print(result)

asyncio.run(main())
```

### Agent with Tools

```python
from typing import Annotated

def calculate(
    expression: Annotated[str, "Mathematical expression to evaluate"]
) -> float:
    """Safely evaluate a mathematical expression."""
    try:
        return eval(expression, {"__builtins__": {}})
    except:
        return 0.0

agent = client.create_agent(
    name="MathBot",
    instructions="Help users with mathematical calculations.",
    tools=[calculate]
)

result = await agent.run("What is 15% of 250?")
```

### Streaming Agent

```python
async for chunk in agent.run_stream("Tell me a story about AI."):
    if chunk.text:
        print(chunk.text, end="", flush=True)
```

---

## 🤝 Multi-Agent Workflows

### Sequential Workflow (Writer → Reviewer)

```python
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient

# Create specialized agents
writer = OpenAIChatClient().create_agent(
    name="Writer",
    instructions="You are a creative content writer."
)

reviewer = OpenAIChatClient().create_agent(
    name="Reviewer",
    instructions="You are a critical content reviewer."
)

# Execute workflow
task = "Write a blog post about autonomous agents"

# Step 1: Writer creates content
content = await writer.run(task)

# Step 2: Reviewer provides feedback
feedback = await reviewer.run(f"Review this: {content}")

# Step 3: Writer refines based on feedback
final = await writer.run(f"Improve based on: {feedback}\n\nOriginal: {content}")

print(final)
```

### Autonomous Magentic Workflow

```python
from agent_framework._workflows import MagenticBuilder

# Create specialized team
research_agent = create_research_agent()
writer = create_writer_agent()
architect = create_architect_agent()

# Build autonomous workflow
workflow = (
    MagenticBuilder()
    .add_participant(research_agent)
    .add_participant(writer)
    .add_participant(architect)
    .with_max_turns(15)
    .build()
)

# Execute - agents self-organize to solve the task
result = await workflow.run(
    "Design a scalable system for processing real-time data streams"
)

print(result.final_result)
```

---

## 🚢 Production Deployment

### Essential Patterns

#### 1. Error Handling & Retries

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def resilient_agent_call(agent, query):
    try:
        return await agent.run(query)
    except Exception as e:
        logger.error(f"Agent call failed: {e}")
        raise
```

#### 2. Checkpointing for Fault Tolerance

```python
from agent_framework._workflows import FileCheckpointStorage

checkpoint = FileCheckpointStorage("./checkpoints")

workflow = (
    MagenticBuilder()
    .add_participant(agent1)
    .add_participant(agent2)
    .with_checkpointing(checkpoint)
    .build()
)

# Workflow can be resumed if interrupted
result = await workflow.run(task)

# Later, resume from checkpoint
# result = await workflow.run_from_checkpoint(checkpoint_id)
```

#### 3. Observability with OpenTelemetry

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Configure OpenTelemetry
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

span_processor = BatchSpanProcessor(OTLPSpanExporter())
trace.get_tracer_provider().add_span_processor(span_processor)

# Framework automatically instruments agents
```

#### 4. Cost Management

```python
# Use cheaper models for simple tasks
simple_agent = OpenAIChatClient(
    model_id="openai/gpt-4o-mini"  # Cost-effective
).create_agent(...)

# Use premium models for complex tasks
complex_agent = OpenAIChatClient(
    model_id="anthropic/claude-3.5-sonnet"  # High-quality
).create_agent(...)

# Set workflow limits
workflow = (
    MagenticBuilder()
    .with_max_turns(10)  # Prevent runaway costs
    .build()
)
```

### Production Checklist

- [ ] **API Keys**: Use secrets manager (not hardcoded)
- [ ] **Rate Limiting**: Implement backoff and throttling
- [ ] **Monitoring**: OpenTelemetry + application insights
- [ ] **Error Handling**: Retries with exponential backoff
- [ ] **Cost Controls**: Budget alerts and usage tracking
- [ ] **Checkpointing**: Fault-tolerant workflows
- [ ] **Security**: Input validation, output sanitization
- [ ] **Testing**: Unit, integration, and load tests
- [ ] **Logging**: Structured logging with correlation IDs
- [ ] **Documentation**: Architecture diagrams and runbooks

---

## 🔧 Troubleshooting

### Common Issues

#### ❌ "API key is required"
**Solution**: Check `python/.env` has `OPENAI_API_KEY=sk-or-v1-...`

#### ❌ "Model not found"
**Solution**: Verify model ID at [https://openrouter.ai/models](https://openrouter.ai/models)

#### ❌ "Rate limit exceeded"
**Solution**: 
- Upgrade OpenRouter plan
- Add retry logic with backoff
- Reduce `max_turns` in workflows

#### ❌ "Function calling not working"
**Solution**: Not all models support function calling. Use:
- `openai/gpt-4o-mini` ✅
- `anthropic/claude-3.5-sonnet` ✅
- `google/gemini-2.0-flash` ✅

#### ❌ "Import errors"
**Solution**: 
```powershell
cd python
uv sync --dev
```

### Debug Mode

Enable verbose logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 📚 Next Steps

1. **Run Examples**: Try all examples in `python/examples/`
2. **Read Documentation**: Explore `docs/` for design decisions
3. **Join Community**: Check GitHub issues and discussions
4. **Build Your System**: Start with simple agents, scale to complex workflows
5. **Deploy to Production**: Follow production deployment checklist

### Recommended Learning Path

1. ✅ **Week 1**: Single agents with tools (Example 1)
2. ✅ **Week 2**: Sequential workflows (Example 2)
3. ✅ **Week 3**: Autonomous collaboration (Example 3)
4. ✅ **Week 4**: Production deployment with observability

---

## 🎯 Real-World Use Cases

### 1. Content Production Pipeline
```
Research Agent → Writer Agent → SEO Optimizer → Editor → Publisher
```

### 2. Code Review System
```
Code Generator → Security Analyzer → Performance Reviewer → Test Generator
```

### 3. Customer Support
```
Intent Classifier → Specialist Agent Pool → Response Generator → QA Checker
```

### 4. Research Analysis
```
Data Collector → Analyst 1..N → Synthesizer → Report Writer
```

### 5. DevOps Automation
```
Monitor → Analyzer → Decision Maker → Executor → Validator
```

---

## 💡 Pro Tips

1. **Start Simple**: Build single agents first, then add complexity
2. **Test Thoroughly**: Use cheaper models (`gpt-4o-mini`) for development
3. **Monitor Costs**: Set up OpenRouter budget alerts
4. **Iterate on Instructions**: Agent quality depends heavily on clear instructions
5. **Use Threads**: Maintain context for better multi-turn conversations
6. **Checkpoint Often**: Enable checkpointing for workflows > 5 minutes
7. **Log Everything**: Structured logging helps debug complex workflows
8. **Model Selection**: Match model capabilities to task complexity

---

## 📞 Support & Resources

- **GitHub**: [microsoft/agent-framework](https://github.com/microsoft/agent-framework)
- **OpenRouter**: [openrouter.ai/docs](https://openrouter.ai/docs)
- **Examples**: `python/examples/`
- **Design Docs**: `docs/design/`
- **ADRs**: `docs/decisions/`

---

## 🚀 Ready to Build?

You now have everything you need to build world-class autonomous multi-agent systems!

```powershell
# Start building!
uv run python examples/01_openrouter_basic.py
```

**Happy building! 🎉**
