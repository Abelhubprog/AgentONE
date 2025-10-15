# Prowzi Development Guide

## Overview

This guide covers the development workflow, coding standards, and contribution guidelines for the Prowzi research automation system.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Documentation](#documentation)
- [Contributing](#contributing)

---

## Getting Started

### Prerequisites

- **Python**: 3.10, 3.11, 3.12, or 3.13
- **uv**: >= 0.8.2 (package manager)
- **Git**: For version control
- **OpenRouter API Key**: For model access

### Initial Setup

```bash
# Clone repository
git clone https://github.com/Abelhubprog/AgentONE.git
cd AgentONE/python/prowzi

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python versions
uv python install 3.10 3.11 3.12 3.13

# Setup development environment (Python 3.13)
uv run poe setup -p 3.13
```

This command:
1. Creates a virtual environment
2. Installs all dependencies (including dev dependencies)
3. Installs pre-commit hooks
4. Configures development tools

### Environment Configuration

Create `.env` file in `python/prowzi/`:

```bash
# OpenRouter API
OPENAI_API_KEY=sk-or-v1-YOUR_KEY_HERE
OPENAI_BASE_URL=https://openrouter.ai/api/v1

# Prowzi Settings
PROWZI_ENABLE_CHECKPOINTING=true
PROWZI_ENABLE_TELEMETRY=true
PROWZI_CHECKPOINT_DIR=./prowzi_checkpoints
PROWZI_OUTPUT_DIR=./prowzi_output
PROWZI_LOG_LEVEL=INFO

# Quality Thresholds
PROWZI_MIN_SOURCE_QUALITY=0.7
PROWZI_MIN_RELEVANCE_SCORE=0.6
PROWZI_TURNITIN_SIMILARITY=15.0
PROWZI_TURNITIN_AI=10.0
```

---

## Development Environment

### Directory Structure

```
python/prowzi/
├── prowzi/                    # Source code
│   ├── agents/               # All agent implementations
│   ├── config/               # Configuration management
│   ├── tools/                # Parsing and search tools
│   ├── workflows/            # Orchestrator, checkpoint, telemetry
│   ├── cli/                  # CLI commands and monitoring
│   └── utils/                # Shared utilities
├── tests/                     # Test suite
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── fixtures/             # Test fixtures
├── docs/                      # Documentation
├── samples/                   # Example scripts
├── pyproject.toml            # Project metadata and dependencies
├── shared_tasks.toml         # Poethepoet task definitions
└── .env                      # Environment variables
```

### Development Tools

**Installed via `poe setup`**:
- **pytest**: Test framework
- **pytest-asyncio**: Async test support
- **pytest-cov**: Coverage reporting
- **ruff**: Linter and formatter (120 char line length)
- **pyright**: Type checker (primary)
- **mypy**: Type checker (secondary)
- **pre-commit**: Git hooks for quality checks

### Poethepoet Tasks

All development tasks use `uv run poe <task>`:

```bash
# Quality checks
uv run poe test              # Run tests with coverage
uv run poe lint              # Lint and auto-fix
uv run poe fmt               # Format code
uv run poe pyright           # Type check (Pyright)
uv run poe mypy              # Type check (MyPy)
uv run poe check             # Run ALL checks (test + lint + fmt + pyright + mypy)

# Development
uv run poe setup -p 3.13     # Setup environment
uv run poe clean             # Clean build artifacts
```

---

## Project Structure

### Package Organization

```
prowzi/
├── agents/
│   ├── __init__.py
│   ├── intent_agent.py         # IntentAgent
│   ├── planning_agent.py       # PlanningAgent
│   ├── search_agent.py         # SearchAgent
│   ├── verification_agent.py   # VerificationAgent
│   ├── writing_agent.py        # WritingAgent
│   ├── evaluation_agent.py     # EvaluationAgent
│   └── turnitin_agent.py       # TurnitinAgent
├── config/
│   ├── __init__.py
│   ├── settings.py             # ProwziConfig, get_config()
│   └── models.py               # Model configurations
├── tools/
│   ├── __init__.py
│   ├── parsing_tools.py        # Document parsing
│   └── search_tools.py         # Search API wrappers
├── workflows/
│   ├── __init__.py
│   ├── orchestrator.py         # ProwziOrchestrator
│   ├── checkpoint.py           # CheckpointManager
│   └── telemetry.py            # TelemetryCollector
├── cli/
│   ├── __init__.py
│   ├── main.py                 # CLI entry point
│   └── monitor.py              # Monitoring UI
└── utils/
    ├── __init__.py
    ├── logging.py              # Logging setup
    └── retry.py                # Retry logic
```

### Key Design Patterns

**1. Agent Pattern**
- All agents inherit from base protocol
- Async methods for I/O operations
- Dataclass-based result objects
- Retry logic with exponential backoff

**2. Configuration Pattern**
- Centralized `ProwziConfig` class
- Environment variable support
- Singleton `get_config()` function
- Immutable after construction

**3. Workflow Pattern**
- Stage-based execution
- Checkpoint persistence between stages
- Real-time telemetry collection
- Progress callbacks for monitoring

---

## Coding Standards

### Python Style

**Follow Microsoft Agent Framework conventions** (see `.github/copilot-instructions.md`):

1. **Line Length**: 120 characters (enforced by ruff)
2. **Docstrings**: Google-style for all public APIs
3. **Parameters**: Max 3 positional; use keyword-only for others
4. **Type Hints**: Required for all function signatures
5. **Imports**: Group standard lib, third-party, local (isort)

### Example Function

```python
from typing import Optional, Dict, Any, List
from pathlib import Path

async def parse_document(
    file_path: Path,
    *,  # Keyword-only after this
    extract_metadata: bool = True,
    encoding: Optional[str] = None,
    **parse_kwargs: Any,
) -> Dict[str, Any]:
    """Parse a document and extract content and metadata.
    
    Args:
        file_path: Path to the document file
        extract_metadata: Whether to extract document metadata
        encoding: Character encoding (auto-detected if None)
        **parse_kwargs: Additional parsing options
    
    Returns:
        Dictionary containing:
            - content (str): Extracted text content
            - metadata (dict): Document metadata
    
    Raises:
        FileNotFoundError: If document doesn't exist
        ParseError: If parsing fails
    
    Example:
        >>> result = await parse_document(
        ...     Path("paper.pdf"),
        ...     extract_metadata=True
        ... )
        >>> print(result["metadata"]["title"])
    """
    # Implementation
    pass
```

### Type Annotations

```python
# Use Protocol for interfaces
from typing import Protocol

class SearchAPIProtocol(Protocol):
    async def search(self, query: str) -> List[Dict[str, Any]]: ...

# Use dataclasses for data structures
from dataclasses import dataclass

@dataclass
class SearchResult:
    title: str
    url: str
    score: float
    metadata: Dict[str, Any]

# Use Literal for string enums
from typing import Literal

ToolMode = Literal['auto', 'required', 'none']

# Avoid forcing imports - provide string alternatives
def configure_tools(
    mode: Literal['auto', 'required', 'none'] | ToolMode
) -> None:
    pass
```

### Async Best Practices

```python
# Good: Use async for I/O
async def fetch_data(url: str) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

# Good: Concurrent execution
async def fetch_multiple(urls: List[str]) -> List[Dict[str, Any]]:
    tasks = [fetch_data(url) for url in urls]
    return await asyncio.gather(*tasks)

# Avoid: Blocking calls in async functions
async def bad_example():
    time.sleep(5)  # Don't do this!
    # Use: await asyncio.sleep(5)
```

### Error Handling

```python
# Define custom exceptions
class ProwziError(Exception):
    """Base exception for Prowzi."""
    pass

class AgentExecutionError(ProwziError):
    """Agent execution failed."""
    pass

# Use specific exceptions
async def run_agent() -> Result:
    try:
        result = await agent.execute()
        return result
    except ModelNotAvailableError as e:
        raise AgentExecutionError(f"Model unavailable: {e}") from e
    except Exception as e:
        logger.exception("Unexpected error in agent execution")
        raise AgentExecutionError(f"Agent failed: {e}") from e
```

---

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/add-new-agent
```

### 2. Implement Feature

```python
# prowzi/agents/new_agent.py
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class NewAgentResult:
    """Result from NewAgent."""
    data: Dict[str, Any]
    confidence: float

class NewAgent:
    """New agent for specific functionality.
    
    Example:
        >>> agent = NewAgent()
        >>> result = await agent.process(input_data)
    """
    
    def __init__(self, config: Optional[ProwziConfig] = None):
        self.config = config or get_config()
    
    async def process(self, input_data: Any) -> NewAgentResult:
        """Process input data.
        
        Args:
            input_data: Input to process
        
        Returns:
            Processing result with confidence score
        """
        # Implementation
        pass
```

### 3. Add Tests

```python
# tests/unit/agents/test_new_agent.py
import pytest
from prowzi.agents import NewAgent, NewAgentResult

class TestNewAgent:
    @pytest.fixture
    def agent(self):
        return NewAgent()
    
    @pytest.mark.asyncio
    async def test_process_success(self, agent):
        result = await agent.process({"key": "value"})
        
        assert isinstance(result, NewAgentResult)
        assert result.confidence > 0.0
        assert "key" in result.data
    
    @pytest.mark.asyncio
    async def test_process_empty_input(self, agent):
        with pytest.raises(ValueError):
            await agent.process({})
```

### 4. Run Quality Checks

```bash
# Run all checks
uv run poe check

# Or individually
uv run poe test              # Tests with coverage
uv run poe lint              # Linting
uv run poe fmt               # Formatting
uv run poe pyright           # Type checking
```

### 5. Commit Changes

```bash
git add prowzi/agents/new_agent.py tests/unit/agents/test_new_agent.py
git commit -m "feat(agents): add NewAgent for specific functionality"
```

**Commit message format**:
- `feat(scope): description` - New feature
- `fix(scope): description` - Bug fix
- `docs(scope): description` - Documentation
- `test(scope): description` - Tests
- `refactor(scope): description` - Refactoring
- `perf(scope): description` - Performance improvement

### 6. Push and Create PR

```bash
git push origin feature/add-new-agent
```

Create pull request with:
- Clear description of changes
- Test results
- Documentation updates
- Breaking changes (if any)

---

## Testing

### Test Organization

```
tests/
├── unit/                      # Unit tests (isolated)
│   ├── agents/
│   ├── config/
│   ├── tools/
│   └── workflows/
├── integration/               # Integration tests (real APIs)
│   ├── test_full_workflow.py
│   └── test_search_apis.py
└── fixtures/                  # Test data
    ├── documents/
    └── responses/
```

### Writing Tests

**Unit Test Example**:
```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from prowzi.agents import IntentAgent

class TestIntentAgent:
    @pytest.fixture
    def mock_config(self):
        config = Mock()
        config.intent_models = ["gpt-4o-mini"]
        return config
    
    @pytest.fixture
    def agent(self, mock_config):
        return IntentAgent(config=mock_config)
    
    @pytest.mark.asyncio
    async def test_analyze_basic_prompt(self, agent):
        """Test basic prompt analysis."""
        with patch('prowzi.agents.intent_agent.ChatAgent') as mock_chat:
            mock_chat.return_value.run = AsyncMock(
                return_value=Mock(
                    text='{"document_type": "research_paper", ...}'
                )
            )
            
            result = await agent.analyze("Write a research paper")
            
            assert result.document_type == "research_paper"
            assert result.confidence_score > 0.0
```

**Integration Test Example**:
```python
import pytest
from prowzi.workflows import ProwziOrchestrator

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_workflow():
    """Test complete workflow end-to-end."""
    orchestrator = ProwziOrchestrator()
    
    result = await orchestrator.run_research(
        prompt="Write a short essay on AI ethics",
        max_sections=3  # Keep test short
    )
    
    assert result.intent is not None
    assert result.draft.total_word_count > 0
    assert result.evaluation.total_score > 0
```

### Running Tests

```bash
# All tests with coverage
uv run poe test

# Specific test file
uv run pytest tests/unit/agents/test_intent_agent.py

# Specific test
uv run pytest tests/unit/agents/test_intent_agent.py::TestIntentAgent::test_analyze_basic_prompt

# Skip integration tests
uv run pytest -m "not integration"

# Run only integration tests
uv run pytest -m integration

# Verbose output
uv run pytest -v

# Stop on first failure
uv run pytest -x
```

### Coverage Requirements

- **Target**: 80% minimum coverage
- **Critical paths**: 100% coverage required
- **View report**: `uv run pytest --cov --cov-report=html`

---

## Documentation

### Docstring Format

**Google Style**:
```python
def function(arg1: str, arg2: int, *, kwarg1: bool = True) -> Dict[str, Any]:
    """Short one-line summary.
    
    Longer description if needed. Can span multiple paragraphs.
    Explain behavior, edge cases, etc.
    
    Args:
        arg1: Description of arg1
        arg2: Description of arg2
        kwarg1: Description of kwarg1 (optional, defaults to True)
    
    Returns:
        Dictionary containing:
            - key1 (str): Description
            - key2 (int): Description
    
    Raises:
        ValueError: When arg2 is negative
        TypeError: When arg1 is not a string
    
    Example:
        >>> result = function("test", 42, kwarg1=False)
        >>> print(result["key1"])
        test
    """
    pass
```

### Documentation Files

When adding new features, update:
1. **API_REFERENCE.md** - API documentation
2. **ARCHITECTURE.md** - Architecture changes
3. **README.md** - Usage examples (if user-facing)
4. **CHANGELOG.md** - Version changes

---

## Contributing

### Pull Request Checklist

- [ ] Code follows style guidelines (passes `poe check`)
- [ ] Tests added/updated (coverage >= 80%)
- [ ] Documentation updated
- [ ] Commit messages follow format
- [ ] No breaking changes (or clearly documented)
- [ ] Pre-commit hooks pass
- [ ] Integration tests pass (if applicable)

### Code Review Process

1. **Self-review**: Check your own code first
2. **Automated checks**: Ensure CI passes
3. **Peer review**: At least one approval required
4. **Address feedback**: Make requested changes
5. **Merge**: Squash and merge to main

### Release Process

1. Update `CHANGELOG.md`
2. Bump version in `pyproject.toml`
3. Create release tag: `git tag v1.1.0`
4. Push tag: `git push origin v1.1.0`
5. CI automatically builds and publishes

---

## Common Development Tasks

### Adding a New Agent

1. Create `prowzi/agents/new_agent.py`
2. Define result dataclass
3. Implement agent class with async methods
4. Add to `prowzi/agents/__init__.py`
5. Update orchestrator if needed
6. Write tests in `tests/unit/agents/`
7. Update `API_REFERENCE.md`

### Adding a Search API

1. Create class in `prowzi/tools/search_tools.py`
2. Implement `SearchAPIProtocol`
3. Add API credentials to config
4. Update `SearchAgent` to use new API
5. Write tests with mocked responses
6. Document in `API_REFERENCE.md`

### Modifying Orchestrator

1. Update `prowzi/workflows/orchestrator.py`
2. Maintain checkpoint compatibility
3. Update telemetry events
4. Add integration tests
5. Update `ARCHITECTURE.md` data flow

### Adding Configuration Options

1. Add property to `ProwziConfig` in `config/settings.py`
2. Add environment variable support
3. Document in `API_REFERENCE.md`
4. Update example `.env` files

---

## Troubleshooting Development Issues

### Pre-commit Hooks Fail

```bash
# Manually run checks
uv run poe check

# Update hooks
pre-commit autoupdate

# Skip hooks temporarily (not recommended)
git commit --no-verify
```

### Import Errors

```bash
# Reinstall dependencies
uv sync

# Verify Python path
uv run python -c "import prowzi; print(prowzi.__file__)"
```

### Type Checking Errors

```bash
# Run Pyright
uv run poe pyright

# Run MyPy
uv run poe mypy

# Ignore specific line (last resort)
result: Any = some_call()  # type: ignore[misc]
```

### Test Failures

```bash
# Run with verbose output
uv run pytest -vv

# Run with stdout
uv run pytest -s

# Debug with pdb
uv run pytest --pdb
```

---

## Resources

- **Microsoft Agent Framework**: https://github.com/microsoft/agent-framework
- **Python Packaging**: https://packaging.python.org/
- **Pytest**: https://docs.pytest.org/
- **Ruff**: https://docs.astral.sh/ruff/
- **Pyright**: https://github.com/microsoft/pyright

---

**Last Updated**: October 15, 2025  
**Maintainer**: Microsoft Agent Framework Team
