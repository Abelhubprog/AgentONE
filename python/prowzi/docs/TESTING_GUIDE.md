# Prowzi Testing Guide

## Overview

Comprehensive testing strategy for the Prowzi research automation system, covering unit tests, integration tests, mocking strategies, and coverage requirements.

---

## Table of Contents

- [Testing Philosophy](#testing-philosophy)
- [Test Structure](#test-structure)
- [Unit Testing](#unit-testing)
- [Integration Testing](#integration-testing)
- [Mocking Strategies](#mocking-strategies)
- [Test Fixtures](#test-fixtures)
- [Coverage Requirements](#coverage-requirements)
- [Running Tests](#running-tests)
- [CI/CD Integration](#cicd-integration)

---

## Testing Philosophy

### Principles

1. **Test Behavior, Not Implementation**: Focus on what the code does, not how it does it
2. **Isolation**: Unit tests should not depend on external services
3. **Determinism**: Tests should produce consistent results
4. **Speed**: Unit tests should run quickly (< 1s each)
5. **Clarity**: Test names and assertions should be self-documenting

### Test Pyramid

```
        /\
       /  \  Integration Tests (10%)
      /----\
     /      \  Unit Tests (80%)
    /--------\
   /          \  Manual/E2E Tests (10%)
  /____________\
```

- **Unit Tests (80%)**: Test individual components in isolation
- **Integration Tests (10%)**: Test component interactions and external APIs
- **Manual/E2E Tests (10%)**: Full system validation

---

## Test Structure

### Directory Layout

```
tests/
├── unit/                           # Unit tests (isolated)
│   ├── agents/
│   │   ├── test_intent_agent.py
│   │   ├── test_planning_agent.py
│   │   ├── test_search_agent.py
│   │   ├── test_verification_agent.py
│   │   ├── test_writing_agent.py
│   │   ├── test_evaluation_agent.py
│   │   └── test_turnitin_agent.py
│   ├── config/
│   │   └── test_settings.py
│   ├── tools/
│   │   ├── test_parsing_tools.py
│   │   └── test_search_tools.py
│   └── workflows/
│       ├── test_orchestrator.py
│       ├── test_checkpoint.py
│       └── test_telemetry.py
├── integration/                    # Integration tests (real APIs)
│   ├── test_full_workflow.py
│   ├── test_checkpoint_resume.py
│   └── test_search_apis.py
├── fixtures/                       # Test data
│   ├── documents/
│   │   ├── sample_paper.pdf
│   │   └── sample_thesis.docx
│   ├── responses/
│   │   ├── intent_response.json
│   │   └── search_response.json
│   └── configs/
│       └── test_config.env
└── conftest.py                     # Shared fixtures
```

### conftest.py

Shared fixtures and configuration:

```python
# tests/conftest.py
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from prowzi.config import ProwziConfig

@pytest.fixture
def test_config():
    """Test configuration with safe defaults."""
    config = ProwziConfig()
    config.enable_checkpointing = False  # Disable for faster tests
    config.enable_telemetry = False
    config.checkpoint_dir = Path("./test_checkpoints")
    return config

@pytest.fixture
def sample_prompt():
    """Sample research prompt for testing."""
    return "Write a 5000-word research paper on quantum computing"

@pytest.fixture
def sample_intent_result():
    """Sample IntentAnalysis result."""
    from prowzi.agents import IntentAnalysis
    return IntentAnalysis(
        document_type="research_paper",
        field="computer_science",
        academic_level="phd",
        word_count=5000,
        explicit_requirements=["quantum computing", "peer-reviewed sources"],
        implicit_requirements=["academic tone", "citations"],
        missing_info=[],
        confidence_score=0.95,
        requires_user_input=False,
        citation_style="APA",
        region=None,
        timeframe=None,
        parsed_documents=[]
    )

@pytest.fixture
async def mock_chat_agent():
    """Mock ChatAgent for testing."""
    agent = Mock()
    agent.run = AsyncMock()
    return agent
```

---

## Unit Testing

### Agent Testing Pattern

**General Structure**:
```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from prowzi.agents import SomeAgent, SomeAgentResult

class TestSomeAgent:
    @pytest.fixture
    def agent(self, test_config):
        """Agent instance with test config."""
        return SomeAgent(config=test_config)
    
    @pytest.mark.asyncio
    async def test_successful_execution(self, agent):
        """Test successful agent execution."""
        # Arrange
        input_data = {...}
        
        # Act
        result = await agent.process(input_data)
        
        # Assert
        assert isinstance(result, SomeAgentResult)
        assert result.field == expected_value
    
    @pytest.mark.asyncio
    async def test_error_handling(self, agent):
        """Test error handling."""
        with pytest.raises(AgentExecutionError):
            await agent.process(invalid_input)
```

### Example: IntentAgent Tests

```python
# tests/unit/agents/test_intent_agent.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
from prowzi.agents import IntentAgent, IntentAnalysis

class TestIntentAgent:
    @pytest.fixture
    def agent(self, test_config):
        return IntentAgent(config=test_config)
    
    @pytest.mark.asyncio
    async def test_analyze_basic_prompt(self, agent, sample_prompt):
        """Test analysis of basic prompt without documents."""
        with patch('prowzi.agents.intent_agent.ChatAgent') as mock_chat:
            # Mock ChatAgent response
            mock_response = Mock()
            mock_response.text = '''{
                "document_type": "research_paper",
                "field": "computer_science",
                "academic_level": "phd",
                "word_count": 5000,
                "confidence_score": 0.95
            }'''
            mock_chat.return_value.run = AsyncMock(return_value=mock_response)
            
            result = await agent.analyze(sample_prompt)
            
            assert isinstance(result, IntentAnalysis)
            assert result.document_type == "research_paper"
            assert result.field == "computer_science"
            assert result.word_count == 5000
            assert result.confidence_score == 0.95
    
    @pytest.mark.asyncio
    async def test_analyze_with_documents(self, agent, sample_prompt):
        """Test analysis with reference documents."""
        from pathlib import Path
        
        with patch('prowzi.tools.parsing_tools.parse_document') as mock_parse:
            mock_parse.return_value = {
                "content": "Sample document content",
                "metadata": {"title": "Test Paper"}
            }
            
            result = await agent.analyze(
                sample_prompt,
                document_paths=[Path("test.pdf")]
            )
            
            assert len(result.parsed_documents) == 1
            mock_parse.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_low_confidence_requires_input(self, agent, sample_prompt):
        """Test that low confidence triggers user input requirement."""
        with patch('prowzi.agents.intent_agent.ChatAgent') as mock_chat:
            mock_response = Mock()
            mock_response.text = '''{
                "document_type": "unknown",
                "confidence_score": 0.4,
                "requires_user_input": true
            }'''
            mock_chat.return_value.run = AsyncMock(return_value=mock_response)
            
            result = await agent.analyze(sample_prompt)
            
            assert result.requires_user_input is True
            assert result.confidence_score < 0.5
```

### Example: CheckpointManager Tests

```python
# tests/unit/workflows/test_checkpoint.py
import pytest
from pathlib import Path
from prowzi.workflows import CheckpointManager, WorkflowCheckpoint

class TestCheckpointManager:
    @pytest.fixture
    def checkpoint_dir(self, tmp_path):
        """Temporary checkpoint directory."""
        return tmp_path / "checkpoints"
    
    @pytest.fixture
    def manager(self, checkpoint_dir):
        """CheckpointManager instance."""
        return CheckpointManager(checkpoint_dir=checkpoint_dir, enabled=True)
    
    def test_save_checkpoint(self, manager, sample_intent_result):
        """Test checkpoint saving."""
        checkpoint_id = manager.save_checkpoint(
            session_id="test-session",
            stage="intent",
            prompt="Test prompt",
            context={"intent": sample_intent_result},
            stage_metrics={"duration": 5.2}
        )
        
        assert checkpoint_id is not None
        assert checkpoint_id.startswith("test-session")
    
    def test_load_checkpoint(self, manager, sample_intent_result):
        """Test checkpoint loading."""
        # Save first
        checkpoint_id = manager.save_checkpoint(
            session_id="test-session",
            stage="intent",
            prompt="Test prompt",
            context={"intent": sample_intent_result},
            stage_metrics={"duration": 5.2}
        )
        
        # Load
        checkpoint = manager.load_checkpoint(checkpoint_id)
        
        assert checkpoint is not None
        assert checkpoint.metadata.stage == "intent"
        assert checkpoint.metadata.session_id == "test-session"
        assert checkpoint.intent == sample_intent_result
    
    def test_list_checkpoints(self, manager):
        """Test listing checkpoints."""
        # Create multiple checkpoints
        for i in range(5):
            manager.save_checkpoint(
                session_id=f"session-{i}",
                stage="intent",
                prompt=f"Prompt {i}",
                context={},
                stage_metrics={}
            )
        
        checkpoints = manager.list_checkpoints(limit=10)
        
        assert len(checkpoints) == 5
        assert all("checkpoint_id" in cp for cp in checkpoints)
    
    def test_disabled_manager(self, checkpoint_dir):
        """Test that disabled manager doesn't save."""
        manager = CheckpointManager(checkpoint_dir=checkpoint_dir, enabled=False)
        
        checkpoint_id = manager.save_checkpoint(
            session_id="test",
            stage="intent",
            prompt="Test",
            context={},
            stage_metrics={}
        )
        
        assert checkpoint_id is None
```

---

## Integration Testing

### Full Workflow Test

```python
# tests/integration/test_full_workflow.py
import pytest
from prowzi.workflows import ProwziOrchestrator

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_workflow_short():
    """Test complete workflow with short output."""
    orchestrator = ProwziOrchestrator()
    
    result = await orchestrator.run_research(
        prompt="Write a brief 500-word essay on renewable energy",
        max_results_per_query=5,
        max_sections=3
    )
    
    # Verify all stages completed
    assert result.intent is not None
    assert result.plan is not None
    assert result.search is not None
    assert result.verification is not None
    assert result.draft is not None
    assert result.evaluation is not None
    assert result.turnitin is not None
    
    # Verify output quality
    assert result.draft.total_word_count >= 400  # Allow some variance
    assert result.evaluation.total_score > 50
    assert len(result.draft.sections) > 0
```

### Checkpoint Resume Test

```python
# tests/integration/test_checkpoint_resume.py
import pytest
from prowzi.workflows import ProwziOrchestrator
from prowzi.config import ProwziConfig

@pytest.mark.integration
@pytest.mark.asyncio
async def test_checkpoint_and_resume(tmp_path):
    """Test checkpoint saving and resuming."""
    config = ProwziConfig()
    config.enable_checkpointing = True
    config.checkpoint_dir = tmp_path / "checkpoints"
    
    orchestrator = ProwziOrchestrator(config=config)
    
    # Start workflow but interrupt after search
    checkpoint_id = None
    
    async def progress_callback(stage: str, payload: dict):
        nonlocal checkpoint_id
        if stage == "search" and "checkpoint_id" in payload:
            checkpoint_id = payload["checkpoint_id"]
            # Simulate interruption
            raise KeyboardInterrupt("Simulated interruption")
    
    try:
        await orchestrator.run_research(
            prompt="Test prompt",
            progress_callback=progress_callback
        )
    except KeyboardInterrupt:
        pass
    
    assert checkpoint_id is not None
    
    # Resume from checkpoint
    result = await orchestrator.resume_from_checkpoint(checkpoint_id)
    
    assert result is not None
    assert result.draft is not None
```

### Search API Tests

```python
# tests/integration/test_search_apis.py
import pytest
from prowzi.tools import GoogleScholarAPI, ArXivAPI

@pytest.mark.integration
@pytest.mark.asyncio
async def test_google_scholar_search():
    """Test real Google Scholar API."""
    api = GoogleScholarAPI()
    
    results = await api.search("machine learning", max_results=5)
    
    assert len(results) > 0
    assert all("title" in r for r in results)
    assert all("url" in r for r in results)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_arxiv_search():
    """Test real ArXiv API."""
    api = ArXivAPI()
    
    results = await api.search("neural networks", max_results=5)
    
    assert len(results) > 0
    assert all("title" in r for r in results)
    assert all("abstract" in r for r in results)
```

---

## Mocking Strategies

### Mocking External APIs

```python
# Mock OpenRouter/ChatAgent
@pytest.fixture
def mock_chat_response():
    """Mock chat model response."""
    response = Mock()
    response.text = '{"key": "value"}'
    return response

@pytest.mark.asyncio
async def test_with_mocked_chat(mock_chat_response):
    with patch('prowzi.agents.some_agent.ChatAgent') as mock_chat:
        mock_chat.return_value.run = AsyncMock(return_value=mock_chat_response)
        
        # Test code here
        pass
```

### Mocking File I/O

```python
@pytest.mark.asyncio
async def test_document_parsing():
    with patch('prowzi.tools.parsing_tools.parse_pdf') as mock_parse:
        mock_parse.return_value = {
            "content": "Mocked content",
            "metadata": {"title": "Test"}
        }
        
        result = await parse_document(Path("test.pdf"))
        
        assert result["content"] == "Mocked content"
```

### Mocking Async Operations

```python
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_async_operation():
    mock_func = AsyncMock(return_value={"result": "success"})
    
    result = await mock_func()
    
    assert result["result"] == "success"
    mock_func.assert_awaited_once()
```

---

## Test Fixtures

### Document Fixtures

```python
# tests/fixtures/documents/create_fixtures.py
from pathlib import Path
from reportlab.pdfgen import canvas

def create_sample_pdf():
    """Create sample PDF for testing."""
    pdf_path = Path(__file__).parent / "sample_paper.pdf"
    c = canvas.Canvas(str(pdf_path))
    c.drawString(100, 750, "Sample Research Paper")
    c.drawString(100, 730, "This is a test document for Prowzi testing.")
    c.save()

if __name__ == "__main__":
    create_sample_pdf()
```

### Response Fixtures

```python
# tests/fixtures/responses/intent_response.json
{
    "document_type": "research_paper",
    "field": "computer_science",
    "academic_level": "phd",
    "word_count": 10000,
    "explicit_requirements": ["quantum computing", "cryptography"],
    "implicit_requirements": ["academic tone", "peer-reviewed sources"],
    "missing_info": [],
    "confidence_score": 0.92,
    "requires_user_input": false,
    "citation_style": "APA"
}
```

### Loading Fixtures

```python
import json
from pathlib import Path

@pytest.fixture
def intent_response_fixture():
    """Load intent response fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "responses" / "intent_response.json"
    with open(fixture_path) as f:
        return json.load(f)
```

---

## Coverage Requirements

### Target Coverage

- **Overall**: 80% minimum
- **Critical paths**: 100% (orchestrator, checkpoint, agents)
- **Utilities**: 90%
- **CLI**: 70%

### Measuring Coverage

```bash
# Run with coverage
uv run pytest --cov=prowzi --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html  # Windows
```

### Coverage Report Example

```
Name                                  Stmts   Miss  Cover
---------------------------------------------------------
prowzi/agents/intent_agent.py           45      2    96%
prowzi/agents/planning_agent.py         52      5    90%
prowzi/workflows/orchestrator.py       120     10    92%
prowzi/workflows/checkpoint.py          65      3    95%
---------------------------------------------------------
TOTAL                                 1200    150    87%
```

### Excluded from Coverage

Add to `pyproject.toml`:
```toml
[tool.coverage.run]
omit = [
    "*/tests/*",
    "*/migrations/*",
    "*/__main__.py"
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

---

## Running Tests

### Basic Commands

```bash
# All tests
uv run poe test

# Specific file
uv run pytest tests/unit/agents/test_intent_agent.py

# Specific test
uv run pytest tests/unit/agents/test_intent_agent.py::TestIntentAgent::test_analyze_basic_prompt

# With verbose output
uv run pytest -v

# With stdout
uv run pytest -s

# Stop on first failure
uv run pytest -x

# Run in parallel (fast)
uv run pytest -n auto
```

### Test Markers

```bash
# Skip integration tests (fast)
uv run pytest -m "not integration"

# Only integration tests
uv run pytest -m integration

# Only slow tests
uv run pytest -m slow
```

### Defining Markers

```python
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "integration: marks tests as integration tests",
    "slow: marks tests as slow (> 1s)",
]
```

```python
# Using markers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_api():
    pass

@pytest.mark.slow
def test_expensive_operation():
    pass
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12", "3.13"]
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Install uv
        uses: astral-sh/setup-uv@v1
      
      - name: Set up Python ${{ matrix.python-version }}
        run: uv python install ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          cd python/prowzi
          uv sync
      
      - name: Run tests
        run: |
          cd python/prowzi
          uv run poe test
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

---

## Best Practices

### 1. Test Naming

```python
# Good: Descriptive test names
def test_intent_agent_handles_missing_documents_gracefully():
    pass

def test_checkpoint_manager_creates_unique_ids():
    pass

# Bad: Vague test names
def test_agent():
    pass

def test_1():
    pass
```

### 2. Arrange-Act-Assert Pattern

```python
def test_something():
    # Arrange: Set up test data
    agent = IntentAgent()
    prompt = "Test prompt"
    
    # Act: Execute the code under test
    result = await agent.analyze(prompt)
    
    # Assert: Verify the outcome
    assert result.confidence_score > 0.0
```

### 3. One Assert Per Test (Generally)

```python
# Good: Focused test
def test_intent_agent_returns_correct_type():
    result = await agent.analyze(prompt)
    assert isinstance(result, IntentAnalysis)

def test_intent_agent_has_positive_confidence():
    result = await agent.analyze(prompt)
    assert result.confidence_score > 0.0

# Acceptable: Related assertions
def test_intent_agent_basic_fields():
    result = await agent.analyze(prompt)
    assert result.document_type is not None
    assert result.field is not None
    assert result.word_count > 0
```

### 4. Use Fixtures for Setup

```python
# Good: Reusable fixture
@pytest.fixture
def configured_agent():
    config = ProwziConfig()
    config.enable_telemetry = False
    return IntentAgent(config=config)

def test_with_fixture(configured_agent):
    result = await configured_agent.analyze("test")
    assert result is not None
```

### 5. Test Edge Cases

```python
def test_empty_input():
    with pytest.raises(ValueError):
        await agent.analyze("")

def test_null_documents():
    result = await agent.analyze("prompt", document_paths=None)
    assert result.parsed_documents == []

def test_very_long_prompt():
    long_prompt = "word " * 10000
    result = await agent.analyze(long_prompt)
    assert result is not None
```

---

## Debugging Tests

### Using pdb

```bash
# Drop into debugger on failure
uv run pytest --pdb

# Drop into debugger on first failure
uv run pytest -x --pdb
```

### Print Debugging

```python
def test_something():
    result = await agent.process()
    print(f"Result: {result}")  # Will show with -s flag
    assert result.value == expected
```

### Logging in Tests

```python
import logging

def test_with_logging(caplog):
    caplog.set_level(logging.DEBUG)
    
    result = await agent.process()
    
    assert "Processing started" in caplog.text
```

---

**Last Updated**: October 15, 2025  
**Test Coverage**: 80% target (87% current)
