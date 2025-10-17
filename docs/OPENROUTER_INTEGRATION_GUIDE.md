# OpenRouter API Integration Guide for Multi-Agent Systems

**Version**: 1.0
**Date**: 2025-10-16
**Status**: Production Guide
**Audience**: Developers, DevOps, System Integrators

---

## Table of Contents

1. [Overview](#overview)
2. [Why OpenRouter for Multi-Agent Systems](#why-openrouter-for-multi-agent-systems)
3. [Architecture](#architecture)
4. [Setup & Configuration](#setup--configuration)
5. [Agent-Specific Model Configuration](#agent-specific-model-configuration)
6. [Creating Presets](#creating-presets)
7. [API Key Management](#api-key-management)
8. [Cost Optimization](#cost-optimization)
9. [Testing & Mocking](#testing--mocking)
10. [Production Best Practices](#production-best-practices)
11. [Troubleshooting](#troubleshooting)

---

## Overview

**What is OpenRouter?**

OpenRouter is a unified API gateway that provides access to 100+ AI models from multiple providers (OpenAI, Anthropic, Google, Meta, Mistral, etc.) through a single API interface. It's particularly valuable for multi-agent systems that need different models for different tasks.

**Key Benefits**:
- ✅ **Single API Key** - Access all models with one key
- ✅ **Cost Transparency** - See exact costs per model/request
- ✅ **Automatic Fallbacks** - If one model is down, automatically use another
- ✅ **Rate Limit Pooling** - Better rate limit management across models
- ✅ **Model Comparison** - Easy A/B testing of different models

**AgentONE Use Case**:

AgentONE uses 7 specialized agents, each requiring different AI capabilities:
- **Intent Agent** - Fast, cheap model for parsing (GPT-4o-mini)
- **Planning Agent** - Strong reasoning model (Claude 3.5 Sonnet)
- **Search Agent** - Cost-effective model (Gemini 2.0 Flash)
- **Verification Agent** - High-accuracy model (GPT-4o)
- **Writing Agent** - Creative model (Claude 3.5 Sonnet)
- **Evaluation Agent** - Analytical model (GPT-4o)
- **Turnitin Agent** - Detection-resistant model (Claude 3 Opus)

---

## Why OpenRouter for Multi-Agent Systems

### Problem: Managing Multiple AI Providers

**Without OpenRouter**:
```python
# Need separate API keys and clients for each provider
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
google_client = GenerativeAI(api_key=os.getenv("GOOGLE_API_KEY"))

# Different API interfaces
openai_response = openai_client.chat.completions.create(...)
anthropic_response = anthropic_client.messages.create(...)
google_response = google_client.generate_content(...)

# Manual cost tracking
track_cost("openai", "gpt-4o", tokens)
track_cost("anthropic", "claude-3.5-sonnet", tokens)
```

**Problems**:
- ❌ Multiple API keys to manage
- ❌ Different API interfaces to learn
- ❌ Manual cost tracking and aggregation
- ❌ No automatic failover between providers
- ❌ Complex rate limit management

### Solution: OpenRouter Unified Interface

**With OpenRouter**:
```python
# Single API key, OpenAI-compatible interface
client = OpenAIChatClient(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
    model_id="anthropic/claude-3.5-sonnet"  # Any model!
)

# Same interface for all models
response = await client.chat.completions.create(...)

# Automatic cost tracking via OpenRouter dashboard
# Automatic failover and rate limit management
```

**Benefits**:
- ✅ One API key for 100+ models
- ✅ Consistent OpenAI-compatible interface
- ✅ Built-in cost tracking and analytics
- ✅ Automatic provider failover
- ✅ Unified rate limit management

---

## Architecture

### AgentONE Multi-Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    OpenRouter Gateway                        │
│  (https://openrouter.ai/api/v1)                             │
│                                                              │
│  Single API Key: sk-or-v1-xxxxx                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ OpenAI-Compatible API
                            │
        ┌───────────────────┴───────────────────┐
        │   Microsoft Agent Framework            │
        │   OpenAIChatClient                     │
        └───────────────────┬───────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │         AgentONE Orchestrator          │
        │      (Sequential Multi-Agent Flow)      │
        └───────────────────┬───────────────────┘
                            │
        ┌───────────────────┴───────────────────────────┐
        │                                                │
   ┌────▼────┐  ┌────────┐  ┌────────┐  ┌──────────┐  │
   │ Intent  │  │Planning│  │ Search │  │Verification│ │
   │ Agent   │  │ Agent  │  │ Agent  │  │  Agent   │  │
   │         │  │        │  │        │  │          │  │
   │GPT-4o   │  │Claude  │  │Gemini  │  │ GPT-4o   │  │
   │-mini    │  │3.5     │  │2.0 Exp │  │          │  │
   └─────────┘  └────────┘  └────────┘  └──────────┘  │
                                                        │
        ┌───────────────────┬───────────────────────┐  │
        │                   │                       │  │
   ┌────▼────┐  ┌───────────▼────┐  ┌──────────────▼──┴┐
   │ Writing │  │  Evaluation    │  │    Turnitin      │
   │ Agent   │  │  Agent         │  │    Agent         │
   │         │  │                │  │                  │
   │Claude   │  │  GPT-4o        │  │  Claude 3 Opus   │
   │3.5      │  │                │  │                  │
   └─────────┘  └────────────────┘  └──────────────────┘
```

### Key Design Principles

1. **One Client Per Agent** - Each agent has its own `OpenAIChatClient` instance
2. **Model Selection at Init Time** - Model is configured when agent is created
3. **Execution Settings at Run Time** - Temperature, max_tokens passed at execution
4. **Centralized Configuration** - All model configs in `prowzi_config.yaml`
5. **Cost Tracking via OpenRouter** - Automatic cost tracking in OpenRouter dashboard

---

## Setup & Configuration

### Step 1: Get OpenRouter API Key

1. **Sign up**: Visit [https://openrouter.ai/](https://openrouter.ai/)
2. **Add Credits**: Navigate to "Billing" → "Add Credits" (minimum $5)
3. **Create API Key**: Go to "Keys" → "Create Key"
4. **Copy Key**: Format is `sk-or-v1-...` (not `sk-...` like OpenAI)

### Step 2: Environment Variables

Create a `.env` file in your project root:

```bash
# OpenRouter Configuration (REQUIRED)
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Optional: OpenRouter Site Name (shows in dashboard)
OPENROUTER_SITE_URL=https://github.com/yourusername/AgentONE
OPENROUTER_APP_NAME=AgentONE

# Optional: Fallback to regular OpenAI (if OpenRouter down)
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
```

**Security Best Practices**:
```bash
# NEVER commit .env to git
echo ".env" >> .gitfile

# For production, use environment variables or secret management
# AWS Secrets Manager, Azure Key Vault, HashiCorp Vault, etc.
```

### Step 3: Configuration File

Create `prowzi_config.yaml` (or edit existing):

```yaml
# OpenRouter Configuration
openrouter:
  api_key: ${OPENROUTER_API_KEY}  # Load from env var
  base_url: ${OPENROUTER_BASE_URL}
  site_url: ${OPENROUTER_SITE_URL}
  app_name: ${OPENROUTER_APP_NAME}

  # Optional: Default fallback model
  default_model: "openai/gpt-4o-mini"

  # Optional: Automatic fallback chain
  fallback_models:
    - "openai/gpt-4o-mini"
    - "anthropic/claude-3-5-haiku-20241022"
    - "google/gemini-2.0-flash-exp:free"

# Model Presets (defined below)
models:
  # Fast & Cheap - For parsing, classification
  fast:
    name: "openai/gpt-4o-mini"
    temperature: 0.3
    max_tokens: 1000
    cost_per_1k_input: 0.00015
    cost_per_1k_output: 0.0006

  # Balanced - For general tasks
  balanced:
    name: "anthropic/claude-3-5-sonnet-20241022"
    temperature: 0.7
    max_tokens: 4000
    cost_per_1k_input: 0.003
    cost_per_1k_output: 0.015

  # Powerful - For complex reasoning
  powerful:
    name: "openai/gpt-4o"
    temperature: 0.7
    max_tokens: 4000
    cost_per_1k_input: 0.005
    cost_per_1k_output: 0.015

  # Creative - For writing, content generation
  creative:
    name: "anthropic/claude-3-5-sonnet-20241022"
    temperature: 0.9
    max_tokens: 8000
    cost_per_1k_input: 0.003
    cost_per_1k_output: 0.015

  # Free/Experimental - For development/testing
  experimental:
    name: "google/gemini-2.0-flash-exp:free"
    temperature: 0.7
    max_tokens: 8000
    cost_per_1k_input: 0.0
    cost_per_1k_output: 0.0

# Agent-Specific Model Assignments
agents:
  intent:
    model: "fast"  # References models.fast
    temperature: 0.3
    max_tokens: 1000
    description: "Parse user intent, extract requirements"

  planning:
    model: "balanced"  # References models.balanced
    temperature: 0.7
    max_tokens: 4000
    description: "Create research plan, decompose tasks"

  search:
    model: "experimental"  # Free for development!
    temperature: 0.5
    max_tokens: 2000
    description: "Score search results, generate queries"

  verification:
    model: "powerful"  # Need high accuracy
    temperature: 0.3
    max_tokens: 4000
    description: "Verify sources, check citations"

  writing:
    model: "creative"  # Need quality prose
    temperature: 0.9
    max_tokens: 8000
    description: "Generate paper sections, outlines"

  evaluation:
    model: "powerful"  # Need analytical depth
    temperature: 0.5
    max_tokens: 4000
    description: "Evaluate paper quality, identify issues"

  turnitin:
    model: "creative"  # Claude 3 Opus for best results
    temperature: 0.8
    max_tokens: 8000
    description: "Rewrite sections to avoid detection"

# Cost Limits (Optional)
cost_management:
  max_cost_per_request: 0.50  # Maximum $0.50 per request
  max_cost_per_session: 5.00  # Maximum $5 per research session
  daily_budget: 100.00        # Maximum $100 per day
  alert_threshold: 0.80       # Alert at 80% of budget
```

### Step 4: Python Configuration Class

Update `prowzi/config/settings.py`:

```python
"""Configuration management for Prowzi using OpenRouter."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ModelConfig:
    """Configuration for a specific AI model."""
    name: str
    temperature: float = 0.7
    max_tokens: int = 4000
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for a request."""
        input_cost = (input_tokens / 1000) * self.cost_per_1k_input
        output_cost = (output_tokens / 1000) * self.cost_per_1k_output
        return input_cost + output_cost


@dataclass
class AgentConfig:
    """Configuration for a specific agent."""
    model: str  # References a model preset
    temperature: float
    max_tokens: int
    description: str = ""


@dataclass
class ProwziConfig:
    """Main configuration for Prowzi application."""

    # OpenRouter settings
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_site_url: Optional[str] = None
    openrouter_app_name: Optional[str] = "AgentONE"

    # Model presets
    models: Dict[str, ModelConfig] = field(default_factory=dict)

    # Agent configurations
    agents: Dict[str, AgentConfig] = field(default_factory=dict)

    # Cost management
    max_cost_per_request: float = 0.50
    max_cost_per_session: float = 5.00
    daily_budget: float = 100.00
    alert_threshold: float = 0.80

    # Fallback models
    fallback_models: list[str] = field(default_factory=list)

    def get_model_for_agent(self, agent_name: str) -> ModelConfig:
        """Get the model configuration for a specific agent.

        Args:
            agent_name: Name of the agent (e.g., "intent", "planning")

        Returns:
            ModelConfig for the agent's assigned model

        Raises:
            KeyError: If agent or model not found
        """
        if agent_name not in self.agents:
            raise KeyError(f"Agent '{agent_name}' not found in configuration")

        agent_config = self.agents[agent_name]
        model_preset = agent_config.model

        if model_preset not in self.models:
            raise KeyError(f"Model preset '{model_preset}' not found in configuration")

        return self.models[model_preset]

    @classmethod
    def from_yaml(cls, config_path: Path) -> "ProwziConfig":
        """Load configuration from YAML file with environment variable substitution.

        Args:
            config_path: Path to prowzi_config.yaml

        Returns:
            ProwziConfig instance
        """
        with open(config_path) as f:
            config_data = yaml.safe_load(f)

        # Substitute environment variables
        config_data = cls._substitute_env_vars(config_data)

        # Parse model configs
        models = {}
        for preset_name, model_data in config_data.get("models", {}).items():
            models[preset_name] = ModelConfig(**model_data)

        # Parse agent configs
        agents = {}
        for agent_name, agent_data in config_data.get("agents", {}).items():
            agents[agent_name] = AgentConfig(**agent_data)

        # Parse OpenRouter settings
        openrouter = config_data.get("openrouter", {})
        cost_mgmt = config_data.get("cost_management", {})

        return cls(
            openrouter_api_key=openrouter.get("api_key"),
            openrouter_base_url=openrouter.get("base_url", "https://openrouter.ai/api/v1"),
            openrouter_site_url=openrouter.get("site_url"),
            openrouter_app_name=openrouter.get("app_name", "AgentONE"),
            models=models,
            agents=agents,
            max_cost_per_request=cost_mgmt.get("max_cost_per_request", 0.50),
            max_cost_per_session=cost_mgmt.get("max_cost_per_session", 5.00),
            daily_budget=cost_mgmt.get("daily_budget", 100.00),
            alert_threshold=cost_mgmt.get("alert_threshold", 0.80),
            fallback_models=openrouter.get("fallback_models", []),
        )

    @staticmethod
    def _substitute_env_vars(data: Any) -> Any:
        """Recursively substitute ${ENV_VAR} with environment variable values."""
        if isinstance(data, dict):
            return {k: ProwziConfig._substitute_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [ProwziConfig._substitute_env_vars(item) for item in data]
        elif isinstance(data, str) and data.startswith("${") and data.endswith("}"):
            env_var = data[2:-1]
            return os.getenv(env_var, data)
        return data


# Global configuration instance
_config: Optional[ProwziConfig] = None


def get_config(config_path: Optional[Path] = None) -> ProwziConfig:
    """Get or create global configuration instance.

    Args:
        config_path: Optional path to config file. If not provided, uses default.

    Returns:
        ProwziConfig instance
    """
    global _config

    if _config is None:
        if config_path is None:
            # Default to prowzi_config.yaml in project root
            config_path = Path(__file__).parent.parent.parent / "prowzi_config.yaml"

        _config = ProwziConfig.from_yaml(config_path)

    return _config


def reset_config():
    """Reset global configuration (useful for testing)."""
    global _config
    _config = None
```

---

## Agent-Specific Model Configuration

### Pattern: One Client Per Agent

Each agent creates its own `OpenAIChatClient` with its assigned model:

```python
"""Intent Agent with OpenRouter integration."""

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from prowzi.config.settings import get_config


class IntentAgent:
    """Agent for parsing user intent and extracting requirements."""

    def __init__(self, config=None):
        """Initialize the Intent Agent.

        Args:
            config: Optional ProwziConfig instance. Uses default if not provided.
        """
        self.config = config or get_config()

        # Get agent-specific configuration
        agent_config = self.config.agents["intent"]
        model_config = self.config.get_model_for_agent("intent")

        # Create OpenAI chat client pointing to OpenRouter
        self.chat_client = OpenAIChatClient(
            api_key=self.config.openrouter_api_key,
            base_url=self.config.openrouter_base_url,
            model_id=model_config.name,  # e.g., "openai/gpt-4o-mini"
        )

        # Create Agent Framework agent with system prompt
        self.agent = ChatAgent(
            chat_client=self.chat_client,
            instructions=self._create_system_prompt(),
        )

    def _create_system_prompt(self) -> str:
        """Create agent-specific system prompt."""
        return """You are an expert intent analysis agent specialized in academic research.

Your role is to:
1. Parse user queries and extract research requirements
2. Identify document type (research paper, thesis, literature review)
3. Extract explicit requirements (stated by user)
4. Infer implicit requirements (standard academic requirements)
5. Assess confidence in understanding user intent

Output JSON with:
- document_type: str
- explicit_requirements: List[str]
- implicit_requirements: List[str]
- confidence_score: float (0.0-1.0)
- needs_clarification: bool
- clarification_questions: List[str] (if applicable)

Be thorough, precise, and ask for clarification when needed."""

    async def analyze(self, prompt: str) -> dict:
        """Analyze user intent and extract requirements.

        Args:
            prompt: User's research request

        Returns:
            Parsed intent analysis as dictionary
        """
        # Get execution settings from agent config
        agent_config = self.config.agents["intent"]

        # Create execution settings (temperature, max_tokens at RUN time)
        from agent_framework.openai import OpenAIChatExecutionSettings

        settings = OpenAIChatExecutionSettings(
            temperature=agent_config.temperature,
            max_tokens=agent_config.max_tokens,
        )

        # Run agent with execution settings
        response = await self.agent.run(prompt, execution_settings=settings)

        # Parse JSON response
        result = self._extract_json(response.response)

        # Track cost (optional)
        if hasattr(response, 'usage'):
            cost = self.config.get_model_for_agent("intent").estimate_cost(
                response.usage.input_tokens,
                response.usage.output_tokens
            )
            result['estimated_cost'] = cost

        return result
```

### Key Points

1. **Model Selection at Init**: `model_id=` is set when creating `OpenAIChatClient`
2. **Execution Settings at Run Time**: `temperature=`, `max_tokens=` passed to `agent.run()`
3. **System Prompts**: Each agent has specialized instructions for its task
4. **Cost Tracking**: Optionally estimate cost using token usage

---

## Creating Presets

### Preset Categories

Create model presets based on task characteristics, not agent names:

```yaml
models:
  # SPEED TIER - Fast, cheap models for simple tasks
  ultra_fast:
    name: "google/gemini-2.0-flash-exp:free"
    temperature: 0.3
    max_tokens: 1000
    cost_per_1k_input: 0.0
    cost_per_1k_output: 0.0
    use_case: "Classification, parsing, simple extraction"

  fast:
    name: "openai/gpt-4o-mini"
    temperature: 0.3
    max_tokens: 2000
    cost_per_1k_input: 0.00015
    cost_per_1k_output: 0.0006
    use_case: "Intent analysis, query generation"

  # BALANCED TIER - Good quality, reasonable cost
  balanced:
    name: "anthropic/claude-3-5-haiku-20241022"
    temperature: 0.7
    max_tokens: 4000
    cost_per_1k_input: 0.001
    cost_per_1k_output: 0.005
    use_case: "General reasoning, planning, analysis"

  balanced_plus:
    name: "anthropic/claude-3-5-sonnet-20241022"
    temperature: 0.7
    max_tokens: 4000
    cost_per_1k_input: 0.003
    cost_per_1k_output: 0.015
    use_case: "Complex reasoning, writing, evaluation"

  # QUALITY TIER - Best quality, higher cost
  quality:
    name: "openai/gpt-4o"
    temperature: 0.7
    max_tokens: 4000
    cost_per_1k_input: 0.005
    cost_per_1k_output: 0.015
    use_case: "Critical tasks, verification, evaluation"

  quality_plus:
    name: "anthropic/claude-3-opus-20240229"
    temperature: 0.8
    max_tokens: 8000
    cost_per_1k_input: 0.015
    cost_per_1k_output: 0.075
    use_case: "Highest quality, creative writing"

  # SPECIALIZED TIER - Task-specific models
  creative_writing:
    name: "anthropic/claude-3-5-sonnet-20241022"
    temperature: 0.9  # Higher temperature for creativity
    max_tokens: 8000
    cost_per_1k_input: 0.003
    cost_per_1k_output: 0.015
    use_case: "Content generation, paper writing"

  analytical:
    name: "openai/o1-mini"  # Reasoning-optimized
    temperature: 1.0  # o1 models ignore temperature
    max_tokens: 4000
    cost_per_1k_input: 0.003
    cost_per_1k_output: 0.012
    use_case: "Complex problem solving, analysis"

  code_generation:
    name: "anthropic/claude-3-5-sonnet-20241022"
    temperature: 0.3  # Low temperature for code
    max_tokens: 8000
    cost_per_1k_input: 0.003
    cost_per_1k_output: 0.015
    use_case: "Code generation, technical tasks"
```

### Environment-Specific Presets

Create different presets for dev/staging/production:

```yaml
# Development Environment
models:
  fast:
    name: "google/gemini-2.0-flash-exp:free"  # Free tier!
    temperature: 0.3
    max_tokens: 1000

  balanced:
    name: "anthropic/claude-3-5-haiku-20241022"  # Cheaper
    temperature: 0.7
    max_tokens: 2000

  powerful:
    name: "openai/gpt-4o-mini"  # Cheaper alternative
    temperature: 0.7
    max_tokens: 2000

# Production Environment
models:
  fast:
    name: "openai/gpt-4o-mini"  # Production-grade
    temperature: 0.3
    max_tokens: 2000

  balanced:
    name: "anthropic/claude-3-5-sonnet-20241022"
    temperature: 0.7
    max_tokens: 4000

  powerful:
    name: "openai/gpt-4o"  # Best quality
    temperature: 0.7
    max_tokens: 4000
```

**Loading environment-specific config**:

```python
import os

config_file = f"prowzi_config.{os.getenv('ENVIRONMENT', 'dev')}.yaml"
config = ProwziConfig.from_yaml(Path(config_file))
```

---

## API Key Management

### Development

**Local `.env` file**:
```bash
# .env (NEVER commit to git)
OPENROUTER_API_KEY=sk-or-v1-dev-key-here
```

**Load in code**:
```python
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")
```

### Production

**Option 1: Environment Variables** (Simplest)
```bash
# Set in production environment
export OPENROUTER_API_KEY=sk-or-v1-prod-key-here
```

**Option 2: AWS Secrets Manager**
```python
import boto3
import json

def get_openrouter_key():
    client = boto3.client('secretsmanager', region_name='us-west-2')
    response = client.get_secret_value(SecretId='prod/openrouter/api-key')
    secret = json.loads(response['SecretString'])
    return secret['OPENROUTER_API_KEY']
```

**Option 3: Azure Key Vault**
```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def get_openrouter_key():
    credential = DefaultAzureCredential()
    client = SecretClient(
        vault_url="https://your-vault.vault.azure.net/",
        credential=credential
    )
    secret = client.get_secret("openrouter-api-key")
    return secret.value
```

**Option 4: HashiCorp Vault**
```python
import hvac

def get_openrouter_key():
    client = hvac.Client(url='https://vault.example.com:8200')
    client.auth.token.login(token=os.getenv('VAULT_TOKEN'))
    secret = client.secrets.kv.v2.read_secret_version(
        path='openrouter/api-key'
    )
    return secret['data']['data']['OPENROUTER_API_KEY']
```

### Key Rotation

**Best practice**: Rotate API keys every 90 days

```python
# Track key age
KEY_CREATED_DATE = "2025-01-15"
KEY_MAX_AGE_DAYS = 90

def check_key_age():
    from datetime import datetime, timedelta
    created = datetime.strptime(KEY_CREATED_DATE, "%Y-%m-%d")
    age = (datetime.now() - created).days

    if age > KEY_MAX_AGE_DAYS:
        logger.warning(
            "OpenRouter API key is old",
            extra={"context": {"age_days": age, "max_age": KEY_MAX_AGE_DAYS}}
        )
```

---

## Cost Optimization

### Strategy 1: Use Appropriate Models

**Cost-Effectiveness Table** (as of Oct 2025):

| Model | Input ($/1M tokens) | Output ($/1M tokens) | Best For |
|-------|---------------------|----------------------|----------|
| **Gemini 2.0 Flash Exp (Free!)** | $0 | $0 | Development, testing |
| **GPT-4o-mini** | $150 | $600 | Fast tasks, parsing |
| **Claude 3.5 Haiku** | $1,000 | $5,000 | General purpose |
| **GPT-4o** | $5,000 | $15,000 | High accuracy |
| **Claude 3.5 Sonnet** | $3,000 | $15,000 | Writing, reasoning |
| **Claude 3 Opus** | $15,000 | $75,000 | Premium quality |

**Example: Intent Agent Cost Comparison**

Assuming 500 tokens input, 300 tokens output:

- **Gemini 2.0 Flash (Free)**: $0.00
- **GPT-4o-mini**: $0.00026 ($150 input + $600 output per 1M tokens)
- **Claude 3.5 Sonnet**: $0.0060 (23x more expensive!)
- **GPT-4o**: $0.0070 (27x more expensive!)

**Recommendation**: Use cheapest model that achieves task requirements!

### Strategy 2: Implement Cost Limits

```python
class CostGuard:
    """Guard against excessive API costs."""

    def __init__(self, config: ProwziConfig):
        self.config = config
        self.session_cost = 0.0
        self.daily_cost = 0.0
        self.request_count = 0

    async def check_and_track(
        self,
        agent_name: str,
        input_tokens: int,
        output_tokens: int
    ) -> bool:
        """Check if request is within cost limits.

        Returns:
            True if request allowed, False if cost limit exceeded
        """
        model = self.config.get_model_for_agent(agent_name)
        estimated_cost = model.estimate_cost(input_tokens, output_tokens)

        # Check per-request limit
        if estimated_cost > self.config.max_cost_per_request:
            logger.error(
                "Request cost exceeds limit",
                extra={"context": {
                    "estimated_cost": estimated_cost,
                    "limit": self.config.max_cost_per_request,
                    "agent": agent_name
                }}
            )
            return False

        # Check session limit
        if self.session_cost + estimated_cost > self.config.max_cost_per_session:
            logger.error(
                "Session cost limit exceeded",
                extra={"context": {
                    "session_cost": self.session_cost,
                    "estimated_cost": estimated_cost,
                    "limit": self.config.max_cost_per_session
                }}
            )
            return False

        # Track costs
        self.session_cost += estimated_cost
        self.request_count += 1

        # Alert if approaching limit
        if self.session_cost / self.config.max_cost_per_session > self.config.alert_threshold:
            logger.warning(
                "Approaching session cost limit",
                extra={"context": {
                    "session_cost": self.session_cost,
                    "limit": self.config.max_cost_per_session,
                    "percentage": (self.session_cost / self.config.max_cost_per_session) * 100
                }}
            )

        return True
```

### Strategy 3: Cache Responses

```python
from functools import lru_cache
import hashlib

class CachedAgent:
    """Agent with response caching to avoid redundant API calls."""

    def __init__(self, agent: ChatAgent):
        self.agent = agent
        self.cache = {}

    def _cache_key(self, prompt: str, settings: dict) -> str:
        """Generate cache key from prompt and settings."""
        content = f"{prompt}:{settings.get('temperature')}:{settings.get('max_tokens')}"
        return hashlib.sha256(content.encode()).hexdigest()

    async def run_cached(self, prompt: str, **kwargs):
        """Run agent with caching."""
        key = self._cache_key(prompt, kwargs)

        if key in self.cache:
            logger.info(
                "Cache hit - skipping API call",
                extra={"context": {"cache_key": key[:16]}}
            )
            return self.cache[key]

        response = await self.agent.run(prompt, **kwargs)
        self.cache[key] = response

        return response
```

### Strategy 4: Monitor OpenRouter Dashboard

OpenRouter provides real-time cost tracking:

1. **Visit**: [https://openrouter.ai/activity](https://openrouter.ai/activity)
2. **View**:
   - Cost per model
   - Requests per agent (via `X-Title` header)
   - Daily/monthly spending
   - Token usage breakdown
3. **Set Alerts**: Configure budget alerts in dashboard

---

## Testing & Mocking

### Problem: Tests Need API Keys

Tests fail without valid OpenRouter API key:

```python
# Test fails with: "OpenAI API key is required"
def test_intent_agent():
    agent = IntentAgent()  # Tries to create OpenAIChatClient!
    result = await agent.analyze("Write a paper")
```

### Solution 1: Mock OpenAIChatClient

**Create mock configuration** (`prowzi/tests/conftest.py`):

```python
import pytest
from unittest.mock import AsyncMock, Mock
from prowzi.config.settings import ProwziConfig, ModelConfig, AgentConfig


@pytest.fixture
def mock_config() -> ProwziConfig:
    """Mock configuration with fake API key."""
    return ProwziConfig(
        openrouter_api_key="sk-or-v1-test-key-fake",
        openrouter_base_url="https://openrouter.ai/api/v1",
        models={
            "fast": ModelConfig(
                name="openai/gpt-4o-mini",
                temperature=0.3,
                max_tokens=1000,
            ),
            "balanced": ModelConfig(
                name="anthropic/claude-3-5-sonnet",
                temperature=0.7,
                max_tokens=4000,
            ),
        },
        agents={
            "intent": AgentConfig(
                model="fast",
                temperature=0.3,
                max_tokens=1000,
            ),
            "planning": AgentConfig(
                model="balanced",
                temperature=0.7,
                max_tokens=4000,
            ),
        },
    )


@pytest.fixture
def mock_openai_chat_client():
    """Mock OpenAIChatClient for testing."""
    mock_client = AsyncMock()

    # Mock response structure
    mock_response = Mock()
    mock_response.response = '{"result": "success"}'
    mock_response.usage = Mock()
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50

    # Setup async mock
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    return mock_client


@pytest.fixture
def mock_chat_agent():
    """Mock ChatAgent for testing."""
    mock_agent = AsyncMock()

    # Mock response
    mock_response = Mock()
    mock_response.response = '{"status": "complete"}'

    mock_agent.run = AsyncMock(return_value=mock_response)

    return mock_agent
```

**Use mocks in tests**:

```python
from unittest.mock import patch
import pytest


@pytest.mark.asyncio
async def test_intent_agent_with_mock(mock_config, mock_chat_agent):
    """Test Intent Agent with mocked dependencies."""

    # Mock OpenAIChatClient creation
    with patch("prowzi.agents.intent_agent.OpenAIChatClient"):
        # Mock ChatAgent creation
        with patch("prowzi.agents.intent_agent.ChatAgent", return_value=mock_chat_agent):
            agent = IntentAgent(config=mock_config)

            # Setup mock response
            mock_chat_agent.run.return_value.response = '''{
                "document_type": "research_paper",
                "explicit_requirements": ["quantum computing"],
                "implicit_requirements": ["peer reviewed sources"],
                "confidence_score": 0.9,
                "needs_clarification": false
            }'''

            # Run test
            result = await agent.analyze("Write about quantum computing")

            # Assertions
            assert result["document_type"] == "research_paper"
            assert result["confidence_score"] == 0.9
            assert not result["needs_clarification"]

            # Verify agent was called
            mock_chat_agent.run.assert_called_once()
```

### Solution 2: Use Test API Key

**Option for integration tests**:

```python
# .env.test
OPENROUTER_API_KEY=sk-or-v1-test-key-with-low-limits
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# pytest.ini
[pytest]
env_files = .env.test


# Integration test (actually calls API)
@pytest.mark.integration
@pytest.mark.asyncio
async def test_intent_agent_integration(mock_config):
    """Integration test with real API (requires test API key)."""
    agent = IntentAgent(config=mock_config)

    result = await agent.analyze("Write a short paper about AI")

    assert "document_type" in result
    assert "confidence_score" in result
    assert 0.0 <= result["confidence_score"] <= 1.0
```

**Run integration tests separately**:
```bash
# Skip integration tests by default
pytest -v

# Run only integration tests
pytest -v -m integration
```

### Solution 3: VCR.py for HTTP Mocking

Record actual API responses for replay in tests:

```python
import vcr
import pytest


my_vcr = vcr.VCR(
    cassette_library_dir='tests/cassettes',
    record_mode='once',  # Record once, then replay
    match_on=['uri', 'method'],
)


@pytest.mark.asyncio
@my_vcr.use_cassette('intent_agent_analyze.yaml')
async def test_intent_agent_with_recording():
    """Test using recorded API response."""
    agent = IntentAgent()

    # First run: records response to cassette
    # Subsequent runs: replays from cassette
    result = await agent.analyze("Write about quantum computing")

    assert result["document_type"] == "research_paper"
```

---

## Production Best Practices

### 1. Implement Retry Logic with Exponential Backoff

```python
import asyncio
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)


class RobustAgent:
    """Agent with automatic retry logic."""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    )
    async def analyze_with_retry(self, prompt: str) -> dict:
        """Analyze with automatic retry on failure."""
        try:
            return await self.agent.run(prompt)
        except Exception as e:
            logger.error(
                "Agent execution failed",
                extra={"context": {"error": str(e), "attempt": self._retry_attempt}}
            )
            raise
```

### 2. Use Fallback Models

```python
async def run_with_fallback(self, prompt: str) -> dict:
    """Try primary model, fall back to alternatives if it fails."""
    models = [
        self.config.get_model_for_agent("intent").name,
        *self.config.fallback_models
    ]

    for model_name in models:
        try:
            logger.info(
                "Trying model",
                extra={"context": {"model": model_name}}
            )

            # Update client model
            self.chat_client.model_id = model_name

            # Attempt request
            response = await self.agent.run(prompt)

            logger.info(
                "Model succeeded",
                extra={"context": {"model": model_name}}
            )

            return response

        except Exception as e:
            logger.warning(
                "Model failed, trying fallback",
                extra={"context": {"model": model_name, "error": str(e)}}
            )
            continue

    raise RuntimeError("All models failed")
```

### 3. Implement Rate Limiting

```python
from aiolimiter import AsyncLimiter


class RateLimitedAgent:
    """Agent with built-in rate limiting."""

    def __init__(self, agent: ChatAgent, max_rate: int = 10, time_period: int = 60):
        self.agent = agent
        # Max 10 requests per 60 seconds
        self.limiter = AsyncLimiter(max_rate, time_period)

    async def run_rate_limited(self, prompt: str, **kwargs):
        """Run agent with rate limiting."""
        async with self.limiter:
            return await self.agent.run(prompt, **kwargs)
```

### 4. Add Request Headers for Tracking

OpenRouter supports custom headers for tracking:

```python
self.chat_client = OpenAIChatClient(
    api_key=self.config.openrouter_api_key,
    base_url=self.config.openrouter_base_url,
    model_id=model_config.name,
    default_headers={
        "HTTP-Referer": self.config.openrouter_site_url,  # Shows in dashboard
        "X-Title": f"AgentONE-{agent_name}",  # Tracks which agent made request
    }
)
```

### 5. Monitor and Alert

```python
import structlog

logger = structlog.get_logger()


class MonitoredAgent:
    """Agent with comprehensive monitoring."""

    async def run_monitored(self, prompt: str) -> dict:
        """Run agent with monitoring and alerting."""
        import time
        start_time = time.time()

        try:
            response = await self.agent.run(prompt)
            duration = time.time() - start_time

            # Log success metrics
            logger.info(
                "agent_execution_success",
                extra={"context": {
                    "agent": self.name,
                    "duration_seconds": duration,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "estimated_cost": self._estimate_cost(response.usage),
                }}
            )

            # Alert if slow
            if duration > 10.0:
                logger.warning(
                    "slow_agent_execution",
                    extra={"context": {
                        "agent": self.name,
                        "duration": duration,
                        "threshold": 10.0
                    }}
                )

            return response

        except Exception as e:
            duration = time.time() - start_time

            logger.error(
                "agent_execution_failure",
                extra={"context": {
                    "agent": self.name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration": duration,
                }}
            )

            # Alert on repeated failures
            self._track_failure()
            if self.failure_count > 3:
                self._send_alert("High failure rate detected")

            raise
```

---

## Troubleshooting

### Issue 1: "OpenAI API key is required"

**Symptoms**:
```
ServiceInitializationError: OpenAI API key is required.
Set via 'api_key' parameter or 'OPENAI_API_KEY' environment variable.
```

**Causes**:
1. Missing `.env` file
2. Wrong environment variable name
3. API key not loaded

**Solutions**:
```bash
# Check environment variable is set
echo $OPENROUTER_API_KEY  # Linux/Mac
echo %OPENROUTER_API_KEY%  # Windows CMD
$env:OPENROUTER_API_KEY  # Windows PowerShell

# Verify .env file exists and has correct format
cat .env
# Should contain: OPENROUTER_API_KEY=sk-or-v1-...

# Load .env in Python
from dotenv import load_dotenv
load_dotenv()
print(os.getenv("OPENROUTER_API_KEY"))  # Should print key
```

### Issue 2: "Model not found" or 404 Error

**Symptoms**:
```
Error: Model 'gpt-4o' not found
```

**Cause**: Model name doesn't include provider prefix for OpenRouter

**Solution**: Use OpenRouter model format:
```python
# ❌ Wrong (OpenAI format)
model_id="gpt-4o"

# ✅ Correct (OpenRouter format)
model_id="openai/gpt-4o"
```

**Model name format**: `{provider}/{model-name}`
- OpenAI: `openai/gpt-4o`, `openai/gpt-4o-mini`
- Anthropic: `anthropic/claude-3-5-sonnet-20241022`
- Google: `google/gemini-2.0-flash-exp:free`
- Meta: `meta-llama/llama-3.1-70b-instruct`

### Issue 3: "Insufficient Credits"

**Symptoms**:
```
Error: Insufficient credits. Please add credits to your account.
```

**Solution**:
1. Visit [https://openrouter.ai/credits](https://openrouter.ai/credits)
2. Click "Add Credits"
3. Add minimum $5 (recommended $25-50 for development)
4. Wait 1-2 minutes for credits to appear
5. Retry request

### Issue 4: Rate Limiting

**Symptoms**:
```
Error: Rate limit exceeded. Try again in X seconds.
```

**Solutions**:
```python
# 1. Add exponential backoff
from tenacity import retry, wait_exponential

@retry(wait=wait_exponential(multiplier=1, min=2, max=60))
async def call_api():
    return await agent.run(prompt)

# 2. Implement client-side rate limiting
from aiolimiter import AsyncLimiter
limiter = AsyncLimiter(max_rate=10, time_period=60)

async with limiter:
    response = await agent.run(prompt)

# 3. Use free tier models for development
model_id="google/gemini-2.0-flash-exp:free"  # No rate limits!
```

### Issue 5: Slow Response Times

**Symptoms**: Requests take >10 seconds

**Causes**:
1. Using O1/O1-mini models (inherently slow, optimized for reasoning)
2. Large max_tokens setting
3. Complex prompts
4. Network latency

**Solutions**:
```python
# 1. Use faster models
model_id="openai/gpt-4o-mini"  # Faster than gpt-4o
model_id="anthropic/claude-3-5-haiku"  # Faster than sonnet

# 2. Reduce max_tokens
max_tokens=1000  # Instead of 8000

# 3. Simplify prompts
# ❌ Complex: "Analyze this text and provide..."  (5+ second processing)
# ✅ Simple: "Summarize in 3 sentences" (1-2 second processing)

# 4. Use streaming for long responses
async for chunk in agent.run_stream(prompt):
    print(chunk, end="", flush=True)
```

### Issue 6: Incorrect Model Behavior

**Symptoms**: Model doesn't follow instructions, gives unexpected outputs

**Solutions**:
```python
# 1. Check temperature setting
temperature=0.3  # More deterministic, follows instructions better
temperature=0.9  # More creative, may deviate from instructions

# 2. Improve system prompt clarity
# ❌ Vague: "You are a helpful assistant"
# ✅ Specific: "You are an expert research assistant. Output JSON only."

# 3. Add output format examples
instructions = """
Output JSON in this exact format:
{
  "field1": "value",
  "field2": 123
}

Example:
{
  "document_type": "research_paper",
  "confidence": 0.9
}
"""

# 4. Try different model
# Some models are better at following instructions:
# - Best: GPT-4o, Claude 3.5 Sonnet
# - Good: GPT-4o-mini, Claude 3.5 Haiku
# - Variable: Gemini, Llama models
```

### Issue 7: High Costs

**Symptoms**: Bills higher than expected

**Solutions**:
```python
# 1. Check OpenRouter dashboard
# https://openrouter.ai/activity
# Look for: expensive models, high token counts, excessive requests

# 2. Implement cost guards
from prowzi.config.cost_guard import CostGuard

guard = CostGuard(config)
if not await guard.check_and_track(agent_name, input_tokens, output_tokens):
    raise CostLimitExceededError()

# 3. Use cheaper models where possible
# Intent parsing: GPT-4o-mini ($0.0002 vs GPT-4o $0.007)
# Search scoring: Gemini 2.0 Flash (FREE vs Claude Sonnet $0.006)
# Verification: GPT-4o only where accuracy critical

# 4. Cache responses aggressively
# Use Redis, SQLite, or in-memory cache for repeated prompts

# 5. Reduce max_tokens
max_tokens=1000  # Costs 75% less than max_tokens=4000

# 6. Set budget alerts
# OpenRouter dashboard → Settings → Budget Alerts
```

---

## Additional Resources

### Official Documentation

- **OpenRouter Docs**: https://openrouter.ai/docs
- **OpenRouter Models**: https://openrouter.ai/models
- **OpenRouter Pricing**: https://openrouter.ai/models?price=true
- **Microsoft Agent Framework**: https://github.com/microsoft/agent-framework
- **Agent Framework Docs**: (internal docs/INDEX.md)

### Example Code

- **Complete agent examples**: `python/prowzi/agents/`
- **Configuration examples**: `prowzi_config.yaml`
- **Test mocking examples**: `python/prowzi/tests/conftest.py`

### Support

- **OpenRouter Discord**: https://discord.gg/openrouter
- **OpenRouter Issues**: support@openrouter.ai
- **Agent Framework Issues**: GitHub Issues

---

## Appendix A: Complete Agent Example

```python
"""Complete example: Intent Agent with OpenRouter integration."""

import json
from typing import Optional
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient, OpenAIChatExecutionSettings
from prowzi.config.settings import get_config, ProwziConfig
from prowzi.config.logging_config import get_logger

logger = get_logger(__name__)


class IntentAgent:
    """Agent for analyzing user intent and extracting requirements."""

    def __init__(self, config: Optional[ProwziConfig] = None):
        """Initialize Intent Agent with OpenRouter.

        Args:
            config: Optional configuration. Uses default if not provided.
        """
        self.config = config or get_config()

        # Get agent configuration
        agent_config = self.config.agents["intent"]
        model_config = self.config.get_model_for_agent("intent")

        logger.info(
            "Initializing Intent Agent",
            extra={"context": {
                "model": model_config.name,
                "temperature": agent_config.temperature,
                "max_tokens": agent_config.max_tokens,
            }}
        )

        # Create OpenRouter-connected client
        self.chat_client = OpenAIChatClient(
            api_key=self.config.openrouter_api_key,
            base_url=self.config.openrouter_base_url,
            model_id=model_config.name,
            default_headers={
                "HTTP-Referer": self.config.openrouter_site_url,
                "X-Title": "AgentONE-Intent",
            }
        )

        # Create agent with system prompt
        self.agent = ChatAgent(
            chat_client=self.chat_client,
            instructions=self._create_system_prompt(),
        )

        self.agent_config = agent_config
        self.model_config = model_config

    def _create_system_prompt(self) -> str:
        """Create specialized system prompt for intent analysis."""
        return """You are an expert intent analysis agent for academic research.

Your task: Parse user queries and extract research requirements.

Output JSON format:
{
  "document_type": "research_paper|thesis|literature_review",
  "explicit_requirements": ["requirement1", "requirement2"],
  "implicit_requirements": ["requirement3", "requirement4"],
  "confidence_score": 0.0-1.0,
  "needs_clarification": true|false,
  "clarification_questions": ["question1", "question2"]
}

Be thorough and ask for clarification when uncertain."""

    async def analyze(self, prompt: str) -> dict:
        """Analyze user intent and extract requirements.

        Args:
            prompt: User's research request

        Returns:
            Dictionary with intent analysis results

        Raises:
            ValueError: If response cannot be parsed
        """
        logger.info(
            "Analyzing user intent",
            extra={"context": {"prompt_length": len(prompt)}}
        )

        # Create execution settings
        settings = OpenAIChatExecutionSettings(
            temperature=self.agent_config.temperature,
            max_tokens=self.agent_config.max_tokens,
        )

        try:
            # Run agent
            response = await self.agent.run(prompt, execution_settings=settings)

            # Parse JSON response
            result = json.loads(response.response)

            # Track cost
            if hasattr(response, 'usage'):
                cost = self.model_config.estimate_cost(
                    response.usage.input_tokens,
                    response.usage.output_tokens
                )
                result['_metadata'] = {
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens,
                    'estimated_cost': cost,
                    'model': self.model_config.name,
                }

                logger.info(
                    "Intent analysis complete",
                    extra={"context": {
                        "confidence": result.get("confidence_score"),
                        "needs_clarification": result.get("needs_clarification"),
                        "cost": cost,
                    }}
                )

            return result

        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse agent response",
                extra={"context": {"error": str(e), "response": response.response}}
            )
            raise ValueError(f"Invalid JSON response: {e}")

        except Exception as e:
            logger.error(
                "Intent analysis failed",
                extra={"context": {"error": str(e), "error_type": type(e).__name__}}
            )
            raise
```

---

## Appendix B: Quick Reference

### Essential Commands

```bash
# Setup
pip install agent-framework python-dotenv pyyaml

# Create .env file
echo "OPENROUTER_API_KEY=sk-or-v1-your-key" > .env

# Test configuration
python -c "from prowzi.config.settings import get_config; print(get_config())"

# Run tests with mocking
pytest prowzi/tests/ -v --tb=short

# Check OpenRouter usage
curl https://openrouter.ai/api/v1/generation-stats \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"
```

### Model Selection Cheat Sheet

| Task | Recommended Model | Reasoning |
|------|------------------|-----------|
| **Parsing/Classification** | `openai/gpt-4o-mini` | Fast, cheap, accurate |
| **Planning/Reasoning** | `anthropic/claude-3-5-sonnet` | Strong reasoning |
| **Creative Writing** | `anthropic/claude-3-5-sonnet` | Best prose quality |
| **Code Generation** | `anthropic/claude-3-5-sonnet` | Best coding model |
| **Analysis/Evaluation** | `openai/gpt-4o` | Highest accuracy |
| **Development/Testing** | `google/gemini-2.0-flash-exp:free` | Free! |

### Cost Optimization Checklist

- [ ] Use cheapest model that meets requirements
- [ ] Set appropriate max_tokens (don't request 8000 if 1000 sufficient)
- [ ] Implement response caching
- [ ] Use free models for development
- [ ] Monitor OpenRouter dashboard daily
- [ ] Set budget alerts
- [ ] Implement cost guards in code
- [ ] Use lower temperature for deterministic tasks

---

**Document Version**: 1.0
**Last Updated**: October 16, 2025
**Maintained By**: AgentONE Development Team
**License**: Internal Use Only
