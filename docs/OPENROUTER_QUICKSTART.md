# OpenRouter Quick Start - 5 Minute Setup

**Goal**: Get AgentONE agents running with OpenRouter in 5 minutes

---

## Step 1: Get API Key (2 minutes)

1. Visit [https://openrouter.ai/](https://openrouter.ai/)
2. Sign up or log in
3. Click "Keys" → "Create New Key"
4. Copy key (starts with `sk-or-v1-...`)
5. Add credits: "Billing" → "Add Credits" (minimum $5)

---

## Step 2: Configure Environment (1 minute)

Create `.env` file in project root:

```bash
# .env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

**Windows PowerShell**:
```powershell
@"
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
"@ | Out-File -FilePath .env -Encoding utf8
```

**Linux/Mac**:
```bash
cat << EOF > .env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
EOF
```

---

## Step 3: Verify Setup (1 minute)

```python
# test_openrouter.py
import os
from dotenv import load_dotenv
from agent_framework.openai import OpenAIChatClient
from agent_framework import ChatAgent

# Load environment
load_dotenv()

# Create client
client = OpenAIChatClient(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url=os.getenv("OPENROUTER_BASE_URL"),
    model_id="openai/gpt-4o-mini"  # Cheap model for testing
)

# Create agent
agent = ChatAgent(
    chat_client=client,
    instructions="You are a helpful assistant."
)

# Test
import asyncio

async def test():
    response = await agent.run("Say 'OpenRouter working!'")
    print(response.response)

asyncio.run(test())
```

**Run test**:
```bash
python test_openrouter.py
# Should output: "OpenRouter working!"
```

---

## Step 4: Run AgentONE Agents (1 minute)

```python
# test_agent.py
from prowzi.agents.intent_agent import IntentAgent
import asyncio

async def test_intent_agent():
    agent = IntentAgent()

    result = await agent.analyze(
        "Write a research paper about quantum computing"
    )

    print(f"Document type: {result['document_type']}")
    print(f"Confidence: {result['confidence_score']}")
    print(f"Requirements: {result['explicit_requirements']}")

asyncio.run(test_intent_agent())
```

**Run**:
```bash
python test_agent.py
```

---

## Troubleshooting

### Error: "API key is required"

**Check environment variable**:
```bash
# PowerShell
$env:OPENROUTER_API_KEY

# Linux/Mac
echo $OPENROUTER_API_KEY
```

**If empty, reload .env**:
```python
from dotenv import load_dotenv
load_dotenv(override=True)
```

### Error: "Insufficient credits"

Visit [https://openrouter.ai/credits](https://openrouter.ai/credits) and add credits.

### Error: "Model not found"

Use OpenRouter format: `provider/model-name`

✅ Correct: `openai/gpt-4o-mini`
❌ Wrong: `gpt-4o-mini`

---

## Free Models for Testing

Use these while developing (no cost!):

```python
model_id="google/gemini-2.0-flash-exp:free"
model_id="google/gemini-pro-1.5-exp:free"
model_id="meta-llama/llama-3.2-3b-instruct:free"
```

---

## Cost Estimates

For a typical research session (7 agents):

| Model Tier | Cost per Session | Use Case |
|------------|------------------|----------|
| **Free (Gemini)** | $0.00 | Development |
| **Cheap (GPT-4o-mini)** | $0.20 | Testing |
| **Balanced (Claude Haiku)** | $1.50 | Staging |
| **Premium (GPT-4o/Claude Sonnet)** | $5.00 | Production |

**Recommendation**: Use free models for development, upgrade for production.

---

## Next Steps

1. **Read full guide**: `docs/OPENROUTER_INTEGRATION_GUIDE.md`
2. **Configure agents**: Edit `prowzi_config.yaml`
3. **Run tests**: `pytest prowzi/tests/ -v`
4. **Monitor costs**: [https://openrouter.ai/activity](https://openrouter.ai/activity)

---

**Questions?** See full guide or join OpenRouter Discord: https://discord.gg/openrouter
