"""
Prowzi Configuration System

Manages OpenRouter models, API keys, cost tracking, and agent-specific settings.
Supports multiple model strategies with automatic fallbacks.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
import os
from enum import Enum


class ModelTier(Enum):
    """Model performance tiers for cost optimization"""
    PREMIUM = "premium"  # GPT-5 Pro, Claude 4.5 Sonnet
    ADVANCED = "advanced"  # GPT-4o, Claude 3.5 Sonnet
    STANDARD = "standard"  # GPT-4o-mini, Gemini 2.0 Flash
    EFFICIENT = "efficient"  # Gemini Flash, Claude Haiku


@dataclass
class ModelConfig:
    """Configuration for a specific model"""
    name: str
    provider: str
    cost_per_1m_input: float  # USD per 1M input tokens
    cost_per_1m_output: float  # USD per 1M output tokens
    max_tokens: int = 8192
    context_window: int = 128_000
    supports_tools: bool = True
    tier: ModelTier = ModelTier.STANDARD


@dataclass
class AgentConfig:
    """Configuration for a specific agent"""
    name: str
    primary_model: str
    fallback_models: List[str] = field(default_factory=list)
    system_prompt: Optional[str] = None
    max_retries: int = 3
    timeout_seconds: int = 300
    temperature: float = 0.7
    max_tokens: int = 4096
    tools_enabled: bool = True


@dataclass
class SearchAPIConfig:
    """Configuration for search APIs"""
    api_name: str
    api_key: Optional[str] = None
    enabled: bool = True
    max_results: int = 10
    timeout_seconds: int = 30
    rate_limit_per_minute: int = 60


class ProwziConfig:
    """
    Central configuration for Prowzi system.

    Loads from environment variables and provides sensible defaults.
    Supports cost tracking and multi-model strategies.
    """

    def __init__(self, env_file: Optional[Path] = None):
        """
        Initialize Prowzi configuration.

        Args:
            env_file: Optional path to .env file. Defaults to python/.env
        """
        if env_file:
            self._load_env(env_file)

        # OpenRouter base configuration
        self.openrouter_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openrouter_base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
        self.openrouter_app_name = os.getenv("OPENROUTER_APP_NAME", "Prowzi/1.0.0")

        # Model configurations
        self.models = self._initialize_models()

        # Agent configurations
        self.agents = self._initialize_agents()

        # Search API configurations
        self.search_apis = self._initialize_search_apis()

        # System settings
        self.checkpoint_dir = Path(os.getenv("PROWZI_CHECKPOINT_DIR", "./prowzi_checkpoints"))
        self.output_dir = Path(os.getenv("PROWZI_OUTPUT_DIR", "./prowzi_output"))
        self.log_level = os.getenv("PROWZI_LOG_LEVEL", "INFO")
        self.enable_telemetry = os.getenv("PROWZI_ENABLE_TELEMETRY", "true").lower() == "true"
        self.enable_checkpointing = os.getenv("PROWZI_ENABLE_CHECKPOINTING", "false").lower() == "true"

        # Quality thresholds
        self.min_source_quality = float(os.getenv("PROWZI_MIN_SOURCE_QUALITY", "0.7"))
        self.min_relevance_score = float(os.getenv("PROWZI_MIN_RELEVANCE_SCORE", "0.6"))
        self.turnitin_similarity_threshold = float(os.getenv("PROWZI_TURNITIN_SIMILARITY", "15.0"))
        self.turnitin_ai_threshold = float(os.getenv("PROWZI_TURNITIN_AI", "10.0"))

        # Create directories if they don't exist
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _load_env(self, env_file: Path):
        """Load environment variables from .env file"""
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
        except ImportError:
            print("Warning: python-dotenv not installed. Install with: pip install python-dotenv")

    def _initialize_models(self) -> Dict[str, ModelConfig]:
        """Initialize model configurations"""
        return {
            # Premium tier - for critical analysis and planning
            "claude-4.5-sonnet": ModelConfig(
                name="anthropic/claude-4.5-sonnet",
                provider="anthropic",
                cost_per_1m_input=3.0,
                cost_per_1m_output=15.0,
                max_tokens=8192,
                context_window=1_000_000,
                tier=ModelTier.PREMIUM
            ),
            "gpt-5-pro": ModelConfig(
                name="openai/gpt-5-pro",
                provider="openai",
                cost_per_1m_input=5.0,
                cost_per_1m_output=25.0,
                max_tokens=8192,
                context_window=200_000,
                tier=ModelTier.PREMIUM
            ),

            # Advanced tier - for most agent tasks
            "gpt-4o": ModelConfig(
                name="openai/gpt-4o",
                provider="openai",
                cost_per_1m_input=2.5,
                cost_per_1m_output=10.0,
                max_tokens=4096,
                context_window=128_000,
                tier=ModelTier.ADVANCED
            ),
            "claude-3.5-sonnet": ModelConfig(
                name="anthropic/claude-3.5-sonnet",
                provider="anthropic",
                cost_per_1m_input=3.0,
                cost_per_1m_output=15.0,
                max_tokens=8192,
                context_window=200_000,
                tier=ModelTier.ADVANCED
            ),

            # Standard tier - good balance of cost and performance
            "gpt-4o-mini": ModelConfig(
                name="openai/gpt-4o-mini",
                provider="openai",
                cost_per_1m_input=0.15,
                cost_per_1m_output=0.6,
                max_tokens=16384,
                context_window=128_000,
                tier=ModelTier.STANDARD
            ),
            "gemini-2.0-flash": ModelConfig(
                name="google/gemini-2.0-flash-exp:free",
                provider="google",
                cost_per_1m_input=0.0,
                cost_per_1m_output=0.0,
                max_tokens=8192,
                context_window=1_000_000,
                tier=ModelTier.STANDARD
            ),
        }

    def _initialize_agents(self) -> Dict[str, AgentConfig]:
        """Initialize agent configurations"""
        return {
            "intent": AgentConfig(
                name="IntentAgent",
                primary_model="claude-4.5-sonnet",  # 1M context for document parsing
                fallback_models=["claude-3.5-sonnet", "gpt-4o"],
                temperature=0.3,  # Lower temp for precise extraction
                max_tokens=4096,
            ),

            "planning": AgentConfig(
                name="PlanningAgent",
                primary_model="gpt-4o",  # Best at structured planning
                fallback_models=["claude-3.5-sonnet", "gemini-2.0-flash"],
                temperature=0.5,
                max_tokens=8192,
            ),

            "search": AgentConfig(
                name="SearchAgent",
                primary_model="gemini-2.0-flash",  # Fast, free, good for batch queries
                fallback_models=["gpt-4o-mini"],
                temperature=0.4,
                max_tokens=4096,
            ),

            "verification": AgentConfig(
                name="VerificationAgent",
                primary_model="claude-3.5-sonnet",  # Excellent at analysis
                fallback_models=["gpt-4o"],
                temperature=0.2,  # Very precise for fact-checking
                max_tokens=4096,
            ),

            "writing": AgentConfig(
                name="WritingAgent",
                primary_model="claude-4.5-sonnet",  # Best for long-form content
                fallback_models=["gpt-4o", "claude-3.5-sonnet"],
                temperature=0.7,  # Balanced creativity
                max_tokens=8192,
            ),

            "evaluation": AgentConfig(
                name="EvaluationAgent",
                primary_model="gpt-4o",  # Strong at rubric-based assessment
                fallback_models=["claude-3.5-sonnet"],
                temperature=0.3,
                max_tokens=4096,
            ),

            "turnitin": AgentConfig(
                name="TurnitinAgent",
                primary_model="gpt-4o",  # Reliable for rewriting
                fallback_models=["claude-3.5-sonnet"],
                temperature=0.8,  # Higher creativity for paraphrasing
                max_tokens=8192,
            ),
        }

    def _initialize_search_apis(self) -> Dict[str, SearchAPIConfig]:
        """Initialize search API configurations"""
        return {
            "perplexity": SearchAPIConfig(
                api_name="Perplexity",
                api_key=os.getenv("PERPLEXITY_API_KEY"),
                enabled=bool(os.getenv("PERPLEXITY_API_KEY")),
                max_results=10,
            ),

            "exa": SearchAPIConfig(
                api_name="Exa",
                api_key=os.getenv("EXA_API_KEY"),
                enabled=bool(os.getenv("EXA_API_KEY")),
                max_results=10,
            ),

            "tavily": SearchAPIConfig(
                api_name="Tavily",
                api_key=os.getenv("TAVILY_API_KEY"),
                enabled=bool(os.getenv("TAVILY_API_KEY")),
                max_results=10,
            ),

            "semantic_scholar": SearchAPIConfig(
                api_name="SemanticScholar",
                api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY"),
                enabled=True,  # Free API
                max_results=20,
            ),

            "pubmed": SearchAPIConfig(
                api_name="PubMed",
                enabled=True,  # Free API
                max_results=20,
            ),

            "arxiv": SearchAPIConfig(
                api_name="arXiv",
                enabled=True,  # Free API
                max_results=20,
            ),

            "serper": SearchAPIConfig(
                api_name="Serper",
                api_key=os.getenv("SERPER_API_KEY"),
                enabled=bool(os.getenv("SERPER_API_KEY")),
                max_results=10,
            ),

            "you": SearchAPIConfig(
                api_name="You.com",
                api_key=os.getenv("YOU_API_KEY"),
                enabled=bool(os.getenv("YOU_API_KEY")),
                max_results=10,
            ),
        }

    def get_model_for_agent(self, agent_name: str) -> ModelConfig:
        """Get the primary model configuration for an agent"""
        agent_config = self.agents.get(agent_name)
        if not agent_config:
            raise ValueError(f"Unknown agent: {agent_name}")

        model_name = agent_config.primary_model
        model_config = self.models.get(model_name)
        if not model_config:
            raise ValueError(f"Unknown model: {model_name}")

        return model_config

    def get_enabled_search_apis(self) -> List[SearchAPIConfig]:
        """Get list of enabled search APIs"""
        return [api for api in self.search_apis.values() if api.enabled]

    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model_name: str
    ) -> float:
        """
        Estimate cost for a model call.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model_name: Name of the model

        Returns:
            Estimated cost in USD
        """
        model = self.models.get(model_name)
        if not model:
            return 0.0

        input_cost = (input_tokens / 1_000_000) * model.cost_per_1m_input
        output_cost = (output_tokens / 1_000_000) * model.cost_per_1m_output

        return input_cost + output_cost

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        return {
            "openrouter_base_url": self.openrouter_base_url,
            "openrouter_app_name": self.openrouter_app_name,
            "models": {k: vars(v) for k, v in self.models.items()},
            "agents": {k: vars(v) for k, v in self.agents.items()},
            "search_apis": {k: vars(v) for k, v in self.search_apis.items()},
            "checkpoint_dir": str(self.checkpoint_dir),
            "enable_checkpointing": self.enable_checkpointing,
            "output_dir": str(self.output_dir),
            "thresholds": {
                "min_source_quality": self.min_source_quality,
                "min_relevance_score": self.min_relevance_score,
                "turnitin_similarity": self.turnitin_similarity_threshold,
                "turnitin_ai": self.turnitin_ai_threshold,
            }
        }


# Global default configuration
_default_config: Optional[ProwziConfig] = None


def get_config() -> ProwziConfig:
    """Get the global Prowzi configuration instance"""
    global _default_config
    if _default_config is None:
        _default_config = ProwziConfig()
    return _default_config


def set_config(config: ProwziConfig):
    """Set the global Prowzi configuration instance"""
    global _default_config
    _default_config = config
