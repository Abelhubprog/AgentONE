# Prowzi - Production-Ready Autonomous Multi-Agent System

**Prowzi** is an enterprise-grade autonomous multi-agent system built on Microsoft Agent Framework. It features specialized AI agents that collaborate autonomously to solve complex tasks through dynamic planning, self-organization, and intelligent task delegation.

## 🎯 Overview

Prowzi represents the state-of-the-art in autonomous multi-agent systems, featuring:

- **5 Specialized Agents** with distinct expertise domains
- **Autonomous Collaboration** through Magentic workflow orchestration
- **Dynamic Task Delegation** based on agent capabilities
- **Intelligent Planning** with fact ledger and progress tracking
- **Production-Ready** with fault tolerance and observability
- **Extensible Architecture** for custom agents and tools

## 🏗️ Architecture

```
                           ┌─────────────┐
                           │   Prowzi    │
                           │  Orchestrator│
                           └──────┬──────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
            ┌───────▼──────┐ ┌───▼────┐ ┌─────▼──────┐
            │   Research   │ │Analyst │ │  Planner   │
            │    Agent     │ │ Agent  │ │   Agent    │
            └──────────────┘ └────────┘ └────────────┘
                    │             │             │
            ┌───────▼──────┐ ┌───▼────────────────────┐
            │   Executor   │ │    Validator Agent     │
            │    Agent     │ │                        │
            └──────────────┘ └────────────────────────┘
                    │
            ┌───────▼──────────────────────────┐
            │        Tool Ecosystem            │
            │  • Web Search                    │
            │  • Data Analysis                 │
            │  • Code Generation               │
            │  • File Operations               │
            │  • API Integration               │
            └──────────────────────────────────┘
```

## 🤖 Agent Roles

### 1. Research Agent
- **Expertise**: Information gathering, fact verification, data collection
- **Capabilities**: Web search, document analysis, source validation
- **When Active**: Initial research, fact-checking, background investigation

### 2. Analyst Agent
- **Expertise**: Data analysis, pattern recognition, insights extraction
- **Capabilities**: Statistical analysis, trend identification, comparative analysis
- **When Active**: Data interpretation, decision support, quality metrics

### 3. Planner Agent
- **Expertise**: Strategic planning, task decomposition, resource allocation
- **Capabilities**: Breaking complex tasks, dependency management, timeline estimation
- **When Active**: Project planning, workflow design, optimization

### 4. Executor Agent
- **Expertise**: Implementation, code generation, task execution
- **Capabilities**: Writing code, creating content, executing plans
- **When Active**: Development, content creation, implementation

### 5. Validator Agent
- **Expertise**: Quality assurance, testing, verification
- **Capabilities**: Code review, testing, compliance checking
- **When Active**: Quality control, final validation, approval

## 🚀 Quick Start

### Basic Usage

```python
from prowzi import ProwziSystem

# Initialize Prowzi
prowzi = ProwziSystem()

# Execute autonomous task
result = await prowzi.execute(
    "Analyze the benefits of autonomous agents and create a technical report"
)

print(result.final_output)
```

### Advanced Usage with Monitoring

```python
from prowzi import ProwziSystem, ProwziConfig

# Configure Prowzi
config = ProwziConfig(
    max_turns=20,
    enable_checkpointing=True,
    checkpoint_dir="./prowzi_checkpoints",
    enable_monitoring=True,
)

prowzi = ProwziSystem(config=config)

# Execute with real-time monitoring
async for event in prowzi.execute_stream(
    "Design a scalable microservices architecture for e-commerce"
):
    print(f"[{event.agent}] {event.action}: {event.message}")
```

## 📦 Installation

```bash
# Ensure you're in the python directory
cd python

# Prowzi uses the existing agent-framework installation
# No additional installation needed if you've already set up the environment
```

## 🎯 Use Cases

### 1. Research & Analysis
```python
result = await prowzi.execute(
    "Research current trends in AI agents and provide a comprehensive analysis"
)
```

### 2. Software Development
```python
result = await prowzi.execute(
    "Design and implement a REST API for user management with tests"
)
```

### 3. Content Creation
```python
result = await prowzi.execute(
    "Create a technical blog post about autonomous systems with code examples"
)
```

### 4. Problem Solving
```python
result = await prowzi.execute(
    "Analyze system performance issues and propose optimization strategies"
)
```

### 5. Strategic Planning
```python
result = await prowzi.execute(
    "Develop a 6-month roadmap for implementing AI in our enterprise"
)
```

## 🔧 Configuration

### Environment Variables

Create or update `python/.env`:

```env
# OpenRouter Configuration
OPENAI_API_KEY=sk-or-v1-your-key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_CHAT_MODEL_ID=openai/gpt-4o-mini

# Prowzi Configuration
PROWZI_MAX_TURNS=20
PROWZI_ENABLE_CHECKPOINTING=true
PROWZI_CHECKPOINT_DIR=./prowzi_checkpoints
PROWZI_LOG_LEVEL=INFO
```

### Programmatic Configuration

```python
from prowzi import ProwziConfig

config = ProwziConfig(
    # Workflow settings
    max_turns=20,
    max_retries=3,
    
    # Agent configuration
    research_model="openai/gpt-4o-mini",
    analyst_model="anthropic/claude-3.5-sonnet",
    planner_model="openai/gpt-4-turbo",
    
    # Features
    enable_checkpointing=True,
    enable_monitoring=True,
    enable_web_search=True,
    
    # Performance
    timeout_seconds=300,
    parallel_execution=True,
)
```

## 📊 Features

### ✅ Autonomous Collaboration
Agents self-organize and collaborate without explicit coordination logic.

### ✅ Dynamic Planning
System adapts plans based on results and learnings during execution.

### ✅ Fault Tolerance
Checkpoint/resume capabilities for long-running tasks.

### ✅ Real-Time Monitoring
Event streaming for complete visibility into agent activities.

### ✅ Quality Assurance
Built-in validation and quality control at every stage.

### ✅ Extensible
Easy to add custom agents, tools, and workflows.

## 🔍 Monitoring & Observability

### Event Streaming

```python
async for event in prowzi.execute_stream(task):
    match event.type:
        case "agent_selected":
            print(f"Selected: {event.agent_name}")
        case "tool_called":
            print(f"Tool: {event.tool_name}")
        case "decision_made":
            print(f"Decision: {event.decision}")
        case "progress_update":
            print(f"Progress: {event.progress}%")
```

### Metrics Collection

```python
metrics = prowzi.get_metrics()
print(f"Total agents: {metrics.agent_calls}")
print(f"Total tools: {metrics.tool_calls}")
print(f"Duration: {metrics.execution_time}s")
print(f"Cost: ${metrics.estimated_cost}")
```

## 🎓 Examples

See the `examples/` directory:

- `prowzi_basic.py` - Basic usage
- `prowzi_research.py` - Research task example
- `prowzi_development.py` - Software development workflow
- `prowzi_analysis.py` - Data analysis workflow
- `prowzi_advanced.py` - Advanced features and customization

## 🚢 Production Deployment

### Checklist

- [ ] Configure persistent CheckpointStorage (Redis/Database)
- [ ] Enable OpenTelemetry tracing
- [ ] Set up cost monitoring and alerts
- [ ] Implement rate limiting
- [ ] Add authentication and authorization
- [ ] Configure error notifications
- [ ] Set up logging aggregation
- [ ] Implement health checks
- [ ] Add performance monitoring
- [ ] Create runbooks and documentation

### Example Production Setup

```python
from prowzi import ProwziSystem
from prowzi.storage import RedisCheckpointStorage
from prowzi.monitoring import PrometheusMetrics

prowzi = ProwziSystem(
    config=ProwziConfig(
        checkpoint_storage=RedisCheckpointStorage(
            redis_url="redis://localhost:6379"
        ),
        metrics_collector=PrometheusMetrics(),
        enable_telemetry=True,
        log_level="INFO",
    )
)
```

## 🤝 Contributing

Prowzi is part of the AgentONE project. To extend:

1. **Add Custom Agents**: Subclass `ProwziAgent` in `prowzi/agents/`
2. **Add Tools**: Create functions in `prowzi/tools/`
3. **Modify Workflows**: Edit `prowzi/workflow.py`
4. **Add Examples**: Create new examples in `examples/`

## 📄 License

Copyright (c) Microsoft. All rights reserved.
Licensed under the MIT License.

## 🔗 Related Projects

- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- [OpenRouter](https://openrouter.ai)
- [AgentONE](https://github.com/Abelhubprog/AgentONE)

---

**Built with ❤️ using Microsoft Agent Framework**
