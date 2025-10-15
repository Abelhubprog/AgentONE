# Prowzi Implementation Patterns - Developer Guide

**Version**: 2.0  
**Framework**: Microsoft Agent Framework v1.0.0b251007  
**Audience**: Developers implementing Prowzi agents  
**Status**: Active Development

---

## Table of Contents

1. [Agent Implementation Pattern](#agent-implementation-pattern)
2. [Tool Development Pattern](#tool-development-pattern)
3. [Workflow Integration](#workflow-integration)
4. [Testing Patterns](#testing-patterns)
5. [Error Handling](#error-handling)
6. [Best Practices](#best-practices)
7. [Common Pitfalls](#common-pitfalls)

---

## Agent Implementation Pattern

### Template Structure

Every Prowzi agent follows this consistent pattern:

```python
"""
Agent Name - Brief description
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from prowzi.config import get_config, ProwziConfig

# 1. Define output dataclass
@dataclass
class AgentOutput:
    """Structured output from this agent"""
    field1: str
    field2: int
    field3: List[str]
    field4: Optional[Dict[str, Any]] = None

# 2. Define agent class
class AgentName:
    """
    Agent purpose and responsibilities.
    
    Usage:
        agent = AgentName()
        result = await agent.main_method(input_data)
    
    Attributes:
        config: ProwziConfig instance
        chat_client: OpenAIChatClient for LLM
        agent: ChatAgent instance
    """
    
    # 3. System prompt (class constant)
    SYSTEM_PROMPT = """
You are an expert [role].

Your task is to [objective].

You should:
1. [Requirement 1]
2. [Requirement 2]
3. [Requirement 3]

Return your response in JSON format:
{
    "field1": "value",
    "field2": 123,
    "field3": ["item1", "item2"]
}
"""
    
    # 4. Initialization
    def __init__(self, config: Optional[ProwziConfig] = None):
        """
        Initialize agent with configuration.
        
        Args:
            config: Optional ProwziConfig. If None, loads default.
        """
        self.config = config or get_config()
        
        # Get model config for this agent
        model_config = self.config.get_model_for_agent("agent_name")
        
        # Create chat client
        self.chat_client = OpenAIChatClient(
            api_key=self.config.openrouter_api_key,
            base_url=self.config.openrouter_base_url,
            model=model_config.name,
            temperature=self.config.agents["agent_name"].temperature,
            max_tokens=self.config.agents["agent_name"].max_tokens,
        )
        
        # Create agent
        self.agent = ChatAgent(
            chat_client=self.chat_client,
            instructions=self.SYSTEM_PROMPT,
        )
    
    # 5. Main method (async)
    async def main_method(
        self,
        input_param1: str,
        input_param2: Optional[List[str]] = None
    ) -> AgentOutput:
        """
        Main agent method.
        
        Args:
            input_param1: Description
            input_param2: Optional description
        
        Returns:
            AgentOutput with structured results
        
        Raises:
            ValueError: If inputs invalid
            RuntimeError: If LLM fails
        """
        # 5a. Validate inputs
        if not input_param1:
            raise ValueError("input_param1 cannot be empty")
        
        # 5b. Build prompt
        prompt = self._build_prompt(input_param1, input_param2)
        
        # 5c. Call agent
        try:
            response = await self.agent.run(prompt)
        except Exception as e:
            raise RuntimeError(f"Agent failed: {e}")
        
        # 5d. Parse response
        parsed = self._parse_response(response.response)
        
        # 5e. Return structured output
        return AgentOutput(**parsed)
    
    # 6. Helper methods (private)
    def _build_prompt(
        self,
        param1: str,
        param2: Optional[List[str]]
    ) -> str:
        """Build prompt for agent"""
        prompt = f"Parameter 1: {param1}\n"
        
        if param2:
            prompt += f"Parameter 2: {', '.join(param2)}\n"
        
        return prompt
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from agent response"""
        import json
        import re
        
        # Extract JSON from markdown code blocks
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError("No JSON found in response")
        
        # Parse JSON
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
```

### Real Example: Intent Agent

```python
"""
Intent & Context Agent - Prowzi entry point
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from prowzi.config import get_config, ProwziConfig
from prowzi.tools.parsing_tools import parse_multiple_documents

@dataclass
class IntentAnalysis:
    """Output from Intent Agent"""
    document_type: str
    field: str
    academic_level: str
    word_count: int
    explicit_requirements: List[str]
    implicit_requirements: List[str]
    missing_info: List[str]
    confidence_score: float
    citation_style: str
    region: Optional[str] = None
    timeframe: Optional[str] = None
    parsed_documents: List[Dict] = None

class IntentAgent:
    """
    Analyzes user intent and extracts structured requirements.
    
    Two-stage processing:
    1. Parsing agent: Summarizes uploaded documents
    2. Intent agent: Analyzes prompt + summaries for requirements
    """
    
    PARSING_PROMPT = """
You are a document summarization expert.

Summarize the following document in 200-300 words, focusing on:
- Main topic and objectives
- Key findings or arguments
- Methodology (if applicable)
- Gaps or limitations mentioned

Document:
{document_content}
"""
    
    INTENT_PROMPT = """
You are a research requirement analyst.

Analyze the user's prompt and document summaries to extract:
- Document type (literature_review, thesis, etc.)
- Academic field
- Academic level (phd, masters, undergraduate)
- Target word count
- All requirements (explicit and implicit)
- Missing information
- Citation style preference

Return JSON matching IntentAnalysis structure.
"""
    
    def __init__(self, config: Optional[ProwziConfig] = None):
        self.config = config or get_config()
        
        # Get model for intent agent
        model_config = self.config.get_model_for_agent("intent")
        
        # Parsing agent (same model)
        self.parsing_agent = ChatAgent(
            chat_client=OpenAIChatClient(
                api_key=self.config.openrouter_api_key,
                base_url=self.config.openrouter_base_url,
                model=model_config.name,
                temperature=0.3,
                max_tokens=500,
            ),
            instructions=self.PARSING_PROMPT,
        )
        
        # Intent agent
        self.intent_agent = ChatAgent(
            chat_client=OpenAIChatClient(
                api_key=self.config.openrouter_api_key,
                base_url=self.config.openrouter_base_url,
                model=model_config.name,
                temperature=0.5,
                max_tokens=2000,
            ),
            instructions=self.INTENT_PROMPT,
        )
    
    async def analyze(
        self,
        prompt: str,
        document_paths: Optional[List[str]] = None
    ) -> IntentAnalysis:
        """
        Analyze user intent from prompt and documents.
        
        Args:
            prompt: User's research request
            document_paths: Optional list of document paths
        
        Returns:
            IntentAnalysis with structured requirements
        """
        # Stage 1: Parse documents
        parsed_docs = []
        summaries = []
        
        if document_paths:
            parsed_docs = parse_multiple_documents(document_paths)
            
            for doc in parsed_docs:
                # Generate summary with parsing agent
                summary_prompt = self.PARSING_PROMPT.format(
                    document_content=doc["content"][:10000]  # First 10K chars
                )
                response = await self.parsing_agent.run(summary_prompt)
                summaries.append(response.response)
        
        # Stage 2: Analyze intent
        intent_prompt = f"""
User Prompt: {prompt}

Document Summaries:
{chr(10).join(f"{i+1}. {s}" for i, s in enumerate(summaries))}

Analyze the above and return structured JSON.
"""
        
        response = await self.intent_agent.run(intent_prompt)
        parsed = self._parse_json_response(response.response)
        
        # Add parsed documents
        parsed["parsed_documents"] = parsed_docs
        
        return IntentAnalysis(**parsed)
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response"""
        import json
        import re
        
        # Try to find JSON in markdown code block
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON found in response")
            json_str = json_match.group(0)
        
        return json.loads(json_str)
```

---

## Tool Development Pattern

### Pure Function Pattern

Tools should be **pure functions** (no classes unless necessary):

```python
"""
Tool Name - Brief description
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

# 1. Define output model (if complex)
@dataclass
class ToolOutput:
    """Structured output from tool"""
    result: str
    metadata: Dict[str, Any]

# 2. Main function (async if I/O)
async def tool_function(
    input1: str,
    input2: Optional[int] = None,
    config: Optional[Dict] = None
) -> ToolOutput:
    """
    Tool description.
    
    Args:
        input1: Description
        input2: Optional description
        config: Optional configuration
    
    Returns:
        ToolOutput with results
    
    Raises:
        ValueError: If inputs invalid
        RuntimeError: If operation fails
    """
    # Validate inputs
    if not input1:
        raise ValueError("input1 required")
    
    # Perform operation
    result = await _do_work(input1, input2)
    
    # Return structured output
    return ToolOutput(
        result=result,
        metadata={"input1": input1, "input2": input2}
    )

# 3. Helper functions (private)
async def _do_work(param1: str, param2: Optional[int]) -> str:
    """Private helper function"""
    return f"Processed: {param1}"
```

### Class-Based Pattern (for stateful tools)

Use classes when you need:
- State management (API clients, connections)
- Resource cleanup (context managers)
- Multiple related methods

```python
"""
Search Engine - Academic search integration
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import aiohttp

@dataclass
class SearchResult:
    """Standardized search result"""
    title: str
    url: str
    content: str
    author: Optional[str] = None
    citation_count: Optional[int] = None

class SearchEngine:
    """Base class for search engines"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            await self.session.close()
    
    async def search(
        self,
        query: str,
        max_results: int = 10
    ) -> List[SearchResult]:
        """
        Execute search query.
        
        Args:
            query: Search query string
            max_results: Maximum results to return
        
        Returns:
            List of SearchResult objects
        """
        raise NotImplementedError("Subclass must implement")

class SemanticScholarSearch(SearchEngine):
    """Semantic Scholar academic search"""
    
    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    
    async def search(
        self,
        query: str,
        max_results: int = 10
    ) -> List[SearchResult]:
        """Search Semantic Scholar"""
        if not self.session:
            raise RuntimeError("Use as context manager")
        
        url = f"{self.BASE_URL}/paper/search"
        params = {
            "query": query,
            "fields": "title,url,abstract,authors,year,citationCount",
            "limit": max_results,
        }
        
        async with self.session.get(url, params=params) as response:
            if response.status != 200:
                raise RuntimeError(f"API error: {response.status}")
            
            data = await response.json()
            
            # Convert to SearchResult
            results = []
            for paper in data.get("data", []):
                results.append(SearchResult(
                    title=paper.get("title", ""),
                    url=paper.get("url", ""),
                    content=paper.get("abstract", ""),
                    author=", ".join(
                        a.get("name", "") for a in paper.get("authors", [])
                    ),
                    citation_count=paper.get("citationCount", 0),
                ))
            
            return results

# Usage
async def example():
    async with SemanticScholarSearch() as engine:
        results = await engine.search("machine learning healthcare")
        for result in results:
            print(f"{result.title} ({result.citation_count} citations)")
```

---

## Workflow Integration

### Sequential Workflow Pattern

```python
"""
Master Orchestrator - Prowzi workflow controller
"""
from typing import Optional, List, AsyncGenerator
from agent_framework import WorkflowBuilder, WorkflowContext
from agent_framework._workflows import FileCheckpointStorage
from prowzi.agents import (
    IntentAgent,
    PlanningAgent,
    SearchAgent,
    VerificationAgent,
    WritingAgent,
    EvaluationAgent,
)
from prowzi.config import get_config, ProwziConfig

class ProwziOrchestrator:
    """
    Master orchestrator for Prowzi research workflow.
    
    Usage:
        orchestrator = ProwziOrchestrator()
        
        async for event in orchestrator.run_research(prompt):
            print(f"Stage: {event.agent_name}, Status: {event.type}")
    """
    
    def __init__(self, config: Optional[ProwziConfig] = None):
        """Initialize orchestrator with agents"""
        self.config = config or get_config()
        
        # Initialize all agents
        self.agents = {
            "intent": IntentAgent(self.config),
            "planning": PlanningAgent(self.config),
            "search": SearchAgent(self.config),
            "verification": VerificationAgent(self.config),
            "writing": WritingAgent(self.config),
            "evaluation": EvaluationAgent(self.config),
        }
    
    async def run_research(
        self,
        prompt: str,
        document_paths: Optional[List[str]] = None,
        checkpoint_dir: str = "./checkpoints",
        checkpoint_id: Optional[str] = None
    ) -> AsyncGenerator:
        """
        Execute research workflow with checkpointing.
        
        Args:
            prompt: Research prompt
            document_paths: Optional documents
            checkpoint_dir: Directory for checkpoints
            checkpoint_id: Resume from checkpoint
        
        Yields:
            WorkflowEvent objects
        """
        # Build workflow
        workflow = (
            WorkflowBuilder()
            .add_edge(
                self.agents["intent"],
                self.agents["planning"],
                name="analyze_intent"
            )
            .add_edge(
                self.agents["planning"],
                self.agents["search"],
                name="execute_plan"
            )
            .add_edge(
                self.agents["search"],
                self.agents["verification"],
                name="verify_sources"
            )
            .add_edge(
                self.agents["verification"],
                self.agents["writing"],
                name="generate_content"
            )
            .add_edge(
                self.agents["writing"],
                self.agents["evaluation"],
                name="evaluate_quality"
            )
            .with_checkpointing(FileCheckpointStorage(checkpoint_dir))
            .build()
        )
        
        # Prepare initial data
        initial_data = {
            "prompt": prompt,
            "document_paths": document_paths or [],
        }
        
        # Execute workflow
        if checkpoint_id:
            # Resume from checkpoint
            async for event in workflow.run_stream_from_checkpoint(checkpoint_id):
                yield event
        else:
            # Start fresh
            async for event in workflow.run_stream(initial_data):
                yield event
```

### Custom Executor Pattern

For complex agent logic that needs workflow integration:

```python
from agent_framework._workflows import executor, Executor, WorkflowContext

@executor
class CustomExecutor(Executor):
    """
    Custom executor for complex agent logic.
    
    Use when agent needs:
    - Access to workflow context
    - Complex state management
    - Multi-step processing
    """
    
    def __init__(self, agent, config):
        self.agent = agent
        self.config = config
    
    async def execute(self, context: WorkflowContext) -> WorkflowContext:
        """
        Execute agent logic with context.
        
        Args:
            context: Current workflow context
        
        Returns:
            Updated workflow context
        """
        # Get data from context
        input_data = context.data.get("input_key")
        
        # Execute agent
        result = await self.agent.main_method(input_data)
        
        # Update context
        context.data["output_key"] = result
        
        # Calculate cost
        cost = self.config.estimate_cost(
            input_tokens=1000,
            output_tokens=500,
            model_name="gpt-4o"
        )
        context.metadata["cost"] += cost
        
        return context

# Usage in workflow
executor = CustomExecutor(agent, config)
workflow = WorkflowBuilder().add_edge(executor, next_executor).build()
```

---

## Testing Patterns

### Agent Unit Test

```python
"""
Test Intent Agent
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from prowzi.agents.intent_agent import IntentAgent, IntentAnalysis
from prowzi.config import ProwziConfig

@pytest.fixture
def mock_config():
    """Mock configuration"""
    config = MagicMock(spec=ProwziConfig)
    config.openrouter_api_key = "test-key"
    config.openrouter_base_url = "https://test.api"
    config.get_model_for_agent.return_value = MagicMock(name="gpt-4o")
    config.agents = {
        "intent": MagicMock(temperature=0.3, max_tokens=2000)
    }
    return config

@pytest.fixture
def mock_agent():
    """Mock ChatAgent"""
    agent = AsyncMock()
    agent.run.return_value = MagicMock(
        response='```json\n{"document_type": "literature_review"}\n```'
    )
    return agent

@pytest.mark.asyncio
async def test_analyze_basic_prompt(mock_config):
    """Test analyzing basic prompt without documents"""
    agent = IntentAgent(mock_config)
    
    # Mock the agent
    agent.intent_agent = mock_agent()
    
    result = await agent.analyze(
        prompt="Write a literature review on AI in healthcare"
    )
    
    assert isinstance(result, IntentAnalysis)
    assert result.document_type == "literature_review"

@pytest.mark.asyncio
async def test_analyze_with_documents(mock_config, tmp_path):
    """Test analyzing with document upload"""
    # Create test document
    doc_path = tmp_path / "test.txt"
    doc_path.write_text("Test document content")
    
    agent = IntentAgent(mock_config)
    agent.intent_agent = mock_agent()
    agent.parsing_agent = mock_agent()
    
    result = await agent.analyze(
        prompt="Analyze this document",
        document_paths=[str(doc_path)]
    )
    
    assert isinstance(result, IntentAnalysis)
    assert len(result.parsed_documents) > 0

@pytest.mark.asyncio
async def test_parse_json_response():
    """Test JSON extraction from LLM response"""
    agent = IntentAgent()
    
    # Test with markdown code block
    response = '```json\n{"field": "value"}\n```'
    parsed = agent._parse_json_response(response)
    assert parsed["field"] == "value"
    
    # Test with raw JSON
    response = '{"field": "value"}'
    parsed = agent._parse_json_response(response)
    assert parsed["field"] == "value"
    
    # Test with no JSON (should raise)
    with pytest.raises(ValueError):
        agent._parse_json_response("No JSON here")
```

### Tool Unit Test

```python
"""
Test search tools
"""
import pytest
from unittest.mock import AsyncMock, patch
from prowzi.tools.search_tools import (
    SemanticScholarSearch,
    SearchResult,
    multi_engine_search,
    deduplicate_results
)

@pytest.fixture
async def mock_session():
    """Mock aiohttp session"""
    session = AsyncMock()
    response = AsyncMock()
    response.status = 200
    response.json.return_value = {
        "data": [
            {
                "title": "Test Paper",
                "url": "https://test.com/paper1",
                "abstract": "Test abstract",
                "authors": [{"name": "Author 1"}],
                "citationCount": 42
            }
        ]
    }
    session.get.return_value.__aenter__.return_value = response
    return session

@pytest.mark.asyncio
async def test_semantic_scholar_search(mock_session):
    """Test Semantic Scholar search"""
    async with SemanticScholarSearch() as engine:
        engine.session = mock_session
        
        results = await engine.search("test query", max_results=10)
        
        assert len(results) == 1
        assert isinstance(results[0], SearchResult)
        assert results[0].title == "Test Paper"
        assert results[0].citation_count == 42

@pytest.mark.asyncio
async def test_multi_engine_search():
    """Test multi-engine search"""
    # Mock engines
    engine1 = AsyncMock()
    engine1.search.return_value = [
        SearchResult(title="Paper 1", url="url1", content="content1")
    ]
    
    engine2 = AsyncMock()
    engine2.search.return_value = [
        SearchResult(title="Paper 2", url="url2", content="content2")
    ]
    
    results = await multi_engine_search(
        query="test",
        engines=[engine1, engine2],
        max_results_per_engine=10
    )
    
    assert len(results) == 2
    assert results[0].title in ["Paper 1", "Paper 2"]

def test_deduplicate_results():
    """Test result deduplication"""
    results = [
        SearchResult(title="Paper 1", url="url1", content="content1"),
        SearchResult(title="Paper 1", url="url1", content="content1"),  # Duplicate
        SearchResult(title="Paper 2", url="url2", content="content2"),
    ]
    
    unique = deduplicate_results(results)
    
    assert len(unique) == 2
    assert unique[0].title == "Paper 1"
    assert unique[1].title == "Paper 2"
```

### Integration Test

```python
"""
Test full workflow integration
"""
import pytest
from prowzi import ProwziOrchestrator
from prowzi.config import get_config

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_workflow_end_to_end():
    """Test complete research workflow (requires API keys)"""
    config = get_config()
    orchestrator = ProwziOrchestrator(config)
    
    prompt = "Write a 1000-word literature review on AI in healthcare"
    
    events = []
    async for event in orchestrator.run_research(prompt):
        events.append(event)
        print(f"Event: {event.type} - {event.agent_name}")
    
    # Verify all stages executed
    agent_names = [e.agent_name for e in events]
    assert "intent" in agent_names
    assert "planning" in agent_names
    assert "search" in agent_names
    assert "verification" in agent_names
    assert "writing" in agent_names
    assert "evaluation" in agent_names
    
    # Verify final result
    final_event = events[-1]
    assert final_event.type == "agent_complete"
    assert "document" in final_event.data

@pytest.mark.integration
@pytest.mark.asyncio
async def test_checkpoint_resume():
    """Test resuming from checkpoint"""
    config = get_config()
    orchestrator = ProwziOrchestrator(config)
    
    prompt = "Test checkpoint"
    
    # Run workflow and save checkpoint
    checkpoint_id = None
    async for event in orchestrator.run_research(prompt):
        if event.type == "checkpoint":
            checkpoint_id = event.data["checkpoint_id"]
            break  # Stop after first checkpoint
    
    assert checkpoint_id is not None
    
    # Resume from checkpoint
    events = []
    async for event in orchestrator.run_research(
        prompt,
        checkpoint_id=checkpoint_id
    ):
        events.append(event)
    
    assert len(events) > 0
```

---

## Error Handling

### Retry Pattern

```python
import asyncio
from typing import TypeVar, Callable
from functools import wraps

T = TypeVar('T')

def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Retry decorator for async functions.
    
    Args:
        max_attempts: Maximum retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay on each retry
        exceptions: Tuple of exceptions to catch
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        raise
                    
                    print(f"Attempt {attempt + 1} failed: {e}")
                    print(f"Retrying in {current_delay}s...")
                    
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
        
        return wrapper
    return decorator

# Usage
@async_retry(max_attempts=3, delay=1.0, backoff=2.0)
async def call_api():
    """API call with automatic retry"""
    response = await client.get("https://api.example.com")
    return response.json()
```

### Fallback Pattern

```python
from typing import List, Optional

class AgentWithFallback:
    """Agent with fallback model support"""
    
    def __init__(self, config):
        self.config = config
        self.primary_model = config.agents["agent_name"].primary_model
        self.fallback_models = config.agents["agent_name"].fallback_models
        
        # Create clients for all models
        self.clients = {
            model: self._create_client(model)
            for model in [self.primary_model] + self.fallback_models
        }
    
    async def run_with_fallback(self, prompt: str) -> str:
        """
        Run agent with fallback models.
        
        Tries primary model first, then fallbacks if it fails.
        """
        models = [self.primary_model] + self.fallback_models
        
        for model in models:
            try:
                print(f"Trying model: {model}")
                client = self.clients[model]
                response = await client.run(prompt)
                return response.response
            except Exception as e:
                print(f"Model {model} failed: {e}")
                if model == models[-1]:
                    raise RuntimeError("All models failed")
                continue
```

### Validation Pattern

```python
from typing import Any, Dict
from pydantic import BaseModel, validator, Field

class ValidatedInput(BaseModel):
    """Validated input with Pydantic"""
    prompt: str = Field(..., min_length=10, max_length=10000)
    word_count: int = Field(..., ge=100, le=50000)
    academic_level: str = Field(..., regex="^(phd|masters|undergraduate)$")
    
    @validator('prompt')
    def prompt_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Prompt cannot be empty")
        return v
    
    @validator('word_count')
    def word_count_reasonable(cls, v, values):
        level = values.get('academic_level')
        if level == 'phd' and v < 5000:
            raise ValueError("PhD level requires ≥5000 words")
        return v

# Usage
def validate_and_process(data: Dict[str, Any]):
    """Validate input before processing"""
    try:
        validated = ValidatedInput(**data)
        return validated
    except Exception as e:
        raise ValueError(f"Invalid input: {e}")
```

---

## Best Practices

### 1. Type Hints Everywhere

```python
# ✅ Good
async def search(query: str, max_results: int = 10) -> List[SearchResult]:
    pass

# ❌ Bad
async def search(query, max_results=10):
    pass
```

### 2. Structured Outputs

```python
# ✅ Good - Use dataclasses
@dataclass
class Result:
    field1: str
    field2: int

# ❌ Bad - Return untyped dict
def process() -> dict:
    return {"field1": "value", "field2": 123}
```

### 3. Async by Default

```python
# ✅ Good - Async for I/O
async def fetch_data(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

# ❌ Bad - Sync for I/O
def fetch_data(url: str) -> str:
    response = requests.get(url)
    return response.text
```

### 4. Clear Naming

```python
# ✅ Good - Descriptive names
async def parse_pdf_document(file_path: str) -> ParsedDocument:
    pass

# ❌ Bad - Vague names
async def parse(path: str) -> dict:
    pass
```

### 5. Comprehensive Docstrings

```python
# ✅ Good - Google-style docstring
async def process_documents(paths: List[str]) -> List[Document]:
    """
    Process multiple documents in parallel.
    
    Args:
        paths: List of document file paths
    
    Returns:
        List of parsed Document objects
    
    Raises:
        FileNotFoundError: If any path invalid
        ValueError: If documents cannot be parsed
    
    Example:
        >>> docs = await process_documents(["doc1.pdf", "doc2.pdf"])
        >>> print(f"Processed {len(docs)} documents")
    """
    pass
```

### 6. Error Context

```python
# ✅ Good - Provide context in errors
try:
    result = await agent.run(prompt)
except Exception as e:
    raise RuntimeError(
        f"Agent failed for prompt '{prompt[:50]}...': {e}"
    ) from e

# ❌ Bad - Generic error
try:
    result = await agent.run(prompt)
except:
    raise RuntimeError("Agent failed")
```

---

## Common Pitfalls

### 1. Forgetting await

```python
# ❌ Wrong - Returns coroutine, not result
result = agent.run(prompt)

# ✅ Correct - Awaits coroutine
result = await agent.run(prompt)
```

### 2. Blocking I/O in Async

```python
# ❌ Wrong - Blocks event loop
async def process():
    data = requests.get("https://api.com")  # Sync I/O
    return data.json()

# ✅ Correct - Non-blocking I/O
async def process():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.com") as response:
            return await response.json()
```

### 3. Not Handling None

```python
# ❌ Wrong - Can raise AttributeError
result = agent.process(data)
return result.field

# ✅ Correct - Check for None
result = agent.process(data)
if result is None:
    raise ValueError("No result from agent")
return result.field
```

### 4. Mutable Default Arguments

```python
# ❌ Wrong - Mutable default
def process(items=[]):
    items.append("new")
    return items

# ✅ Correct - None default
def process(items=None):
    if items is None:
        items = []
    items.append("new")
    return items
```

### 5. Not Closing Resources

```python
# ❌ Wrong - Session not closed
async def search(query):
    session = aiohttp.ClientSession()
    response = await session.get(f"https://api.com?q={query}")
    return await response.json()

# ✅ Correct - Context manager
async def search(query):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.com?q={query}") as response:
            return await response.json()
```

### 6. Not Validating LLM Outputs

```python
# ❌ Wrong - Assume valid JSON
response = await agent.run(prompt)
return json.loads(response.response)

# ✅ Correct - Validate and handle errors
response = await agent.run(prompt)
try:
    parsed = self._parse_json(response.response)
    return IntentAnalysis(**parsed)
except (json.JSONDecodeError, ValueError) as e:
    raise ValueError(f"Invalid agent response: {e}")
```

---

## Next Steps

1. **Study existing implementations**:
   - `prowzi/agents/intent_agent.py` (400 lines)
   - `prowzi/agents/planning_agent.py` (500 lines)
   - `prowzi/tools/search_tools.py` (500 lines)

2. **Implement remaining agents** using patterns above:
   - Search Agent (execute searches, score relevance)
   - Verification Agent (validate sources)
   - Writing Agent (generate content)
   - Evaluation Agent (assess quality)

3. **Add comprehensive tests**:
   - Unit tests for each agent
   - Integration tests for workflow
   - Mock external APIs

4. **Build orchestrator**:
   - Sequential workflow
   - Checkpointing
   - Error recovery

---

**Version**: 2.0  
**Last Updated**: January 2025  
**Status**: Living document - update as patterns evolve
