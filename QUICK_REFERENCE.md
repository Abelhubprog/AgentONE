# AgentONE Quick Reference Card

## 🚀 Common Commands

```powershell
# Verify setup
uv run python examples/00_verify_setup.py

# Run examples
uv run python examples/01_openrouter_basic.py
uv run python examples/02_sequential_workflow.py
uv run python examples/03_magentic_workflow.py

# Run tests
cd python
uv run poe test

# Lint code
uv run poe lint

# Format code
uv run poe fmt
```

## 🔧 Basic Agent Creation

```python
from agent_framework.openai import OpenAIChatClient

# Create client
client = OpenAIChatClient()

# Create agent
agent = client.create_agent(
    name="MyAgent",
    instructions="Your expertise here...",
    tools=[function1, function2]
)

# Run agent
result = await agent.run("Your query")

# Stream response
async for chunk in agent.run_stream("Query"):
    print(chunk.text, end="", flush=True)
```

## 🛠️ Tool Definition

```python
from typing import Annotated

def my_tool(
    param1: Annotated[str, "Description of param1"],
    param2: Annotated[int, "Description of param2"],
) -> str:
    """Tool description for the LLM."""
    # Your implementation
    return "result"
```

## 🔄 Sequential Workflow

```python
# Create specialized agents
agent1 = client.create_agent(name="Agent1", instructions="...")
agent2 = client.create_agent(name="Agent2", instructions="...")

# Execute sequentially
result1 = await agent1.run(task)
result2 = await agent2.run(f"Based on: {result1}, do this...")
```

## 🤖 Magentic Autonomous Workflow

```python
from agent_framework._workflows import MagenticBuilder

workflow = (
    MagenticBuilder()
    .add_participant(agent1)
    .add_participant(agent2)
    .add_participant(agent3)
    .with_max_turns(15)
    .build()
)

result = await workflow.run("Complex task...")
```

## 💾 Checkpointing

```python
from agent_framework._workflows import FileCheckpointStorage

checkpoint = FileCheckpointStorage("./checkpoints")

workflow = (
    MagenticBuilder()
    .add_participant(agent)
    .with_checkpointing(checkpoint)
    .build()
)

# Run with checkpointing
result = await workflow.run(task)

# Resume from checkpoint
result = await workflow.run_from_checkpoint(checkpoint_id)
```

## 🧵 Thread Persistence

```python
thread = agent.get_new_thread()

# All calls share context
await agent.run("Message 1", thread=thread)
await agent.run("Message 2", thread=thread)
await agent.run("What did I say earlier?", thread=thread)
```

## 📊 Event Monitoring

```python
async def event_handler(event):
    if event.source == "agent":
        print(f"Agent: {event.message}")
    elif event.source == "orchestrator":
        print(f"Orchestrator: {event.message}")

workflow = (
    MagenticBuilder()
    .with_callback(event_handler, mode=MagenticCallbackMode.NON_STREAMING)
    .build()
)
```

## 🔐 Configuration

### Environment Variables (.env)
```env
OPENAI_API_KEY=sk-or-v1-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_CHAT_MODEL_ID=openai/gpt-4o-mini
```

### Explicit Configuration
```python
client = OpenAIChatClient(
    api_key="sk-or-v1-...",
    base_url="https://openrouter.ai/api/v1",
    model_id="openai/gpt-4o-mini",
    default_headers={
        "HTTP-Referer": "https://your-app.com",
        "X-Title": "Your App Name"
    }
)
```

## 🎯 Model Selection

```python
# Cost-effective
model_id="openai/gpt-4o-mini"
model_id="deepseek/deepseek-chat"

# High-quality
model_id="openai/gpt-4-turbo"
model_id="anthropic/claude-3.5-sonnet"

# Specialized
model_id="google/gemini-2.0-flash"
model_id="meta-llama/llama-3.1-70b-instruct"
```

## 🐛 Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Error Handling

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def resilient_call():
    return await agent.run(query)
```

## 📚 Common Patterns

### Pattern: Content Pipeline
```python
writer → reviewer → editor → publisher
```

### Pattern: Code Review
```python
generator → security_check → performance_review → test_generator
```

### Pattern: Research
```python
collector → analyst1..N → synthesizer → writer
```

## 🚨 Troubleshooting

| Issue | Solution |
|-------|----------|
| "API key required" | Update `python/.env` |
| "Model not found" | Check [openrouter.ai/models](https://openrouter.ai/models) |
| "Rate limit" | Add retry logic, upgrade plan |
| "Import errors" | Run `uv sync --dev` |
| Tool not called | Check function has proper type hints |

## 📞 Resources

- **Setup**: `GETTING_STARTED.md`
- **Examples**: `python/examples/README.md`
- **Framework**: [github.com/microsoft/agent-framework](https://github.com/microsoft/agent-framework)
- **OpenRouter**: [openrouter.ai/docs](https://openrouter.ai/docs)
