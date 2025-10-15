# Prowzi Reimplementation Guide - MS Agent Framework

**Document Version**: 2.0  
**Last Updated**: January 2025  
**Status**: Foundation Complete (60%), MVP in Progress  
**Framework**: Microsoft Agent Framework v1.0.0b251007

---

## 🎯 Executive Summary

This document provides complete context for the Prowzi reimplementation using Microsoft Agent Framework. Prowzi is being rebuilt from the ground up as a production-ready autonomous multi-agent system for academic research automation.

### What We're Building

**Prowzi v2** - A 7-agent autonomous research system that transforms academic research from hours of manual work into minutes of guided autonomy. The system analyzes requirements, plans research strategies, gathers evidence from multiple sources, verifies quality, generates academic content, evaluates results, and optionally checks for plagiarism.

### Why the Reimplementation

The original Prowzi (in `agentic_layer/`) was built with custom agent orchestration. While functional, it had:
- Complex custom coordination logic
- Tightly coupled components
- Limited observability
- Manual error handling
- No standardized workflow patterns

**Microsoft Agent Framework** provides:
- ✅ Production-ready orchestration (Workflows, Checkpointing)
- ✅ Enterprise-grade reliability (Error recovery, Retries)
- ✅ Built-in observability (OpenTelemetry integration)
- ✅ Clean abstractions (ChatAgent, WorkflowBuilder)
- ✅ Type safety (Pydantic models, Python 3.13+)
- ✅ Async-first performance

### Progress Status

**✅ Complete (60%)**:
- Configuration system with 6+ models
- Intent Agent (document parsing + analysis)
- Planning Agent (task decomposition + query generation)
- Document parsing tools (PDF/DOCX/MD/TXT)
- Search tools (3/8 APIs integrated)
- Comprehensive documentation

**🚧 In Progress (40%)**:
- Search Agent
- Verification Agent
- Writing Agent
- Evaluation Agent
- Master Orchestrator
- Test suite

**📅 Timeline**: 2-3 weeks to MVP completion

---

## 📊 Architecture Comparison

### Old Architecture (agentic_layer/)

```
agentic_layer/
├── agents/
│   ├── base_agent.py           # Custom BaseAgent class
│   ├── intent_context_agent.py # 445 lines custom implementation
│   ├── planning_agent.py       # Custom planning logic
│   ├── evidence_search_agent.py
│   ├── verification_agent.py
│   ├── writing_agent.py
│   ├── evaluation_agent.py
│   └── turnitin_agent.py
├── agent_controller.py         # Custom orchestration (600+ lines)
├── model_dispatcher.py         # Custom LLM routing
├── tool_registry.py            # Custom tool management
└── context_manager.py          # Custom ACE context

Key Patterns:
- Custom base class with _call_llm() method
- Manual tool execution with _execute_tool()
- Custom orchestration in AgentController
- Manual WebSocket event emission
- Explicit stage transitions
- Custom checkpointing logic
```

### New Architecture (prowzi/)

```
prowzi/
├── agents/
│   ├── intent_agent.py         # ChatAgent + OpenAIChatClient
│   ├── planning_agent.py       # Uses agent_framework patterns
│   ├── search_agent.py         # 🚧 TODO
│   ├── verification_agent.py   # 🚧 TODO
│   ├── writing_agent.py        # 🚧 TODO
│   ├── evaluation_agent.py     # 🚧 TODO
│   └── turnitin_agent.py       # 🚧 TODO
├── tools/
│   ├── parsing_tools.py        # Pure functions (no classes)
│   ├── search_tools.py         # Async SearchEngine classes
│   ├── analysis_tools.py       # 🚧 TODO
│   └── citation_tools.py       # 🚧 TODO
├── workflows/
│   └── orchestrator.py         # WorkflowBuilder + Sequential
├── config/
│   └── settings.py             # ProwziConfig (multi-model)
└── tests/                      # 🚧 TODO

Key Patterns:
- MS Agent Framework ChatAgent
- OpenAIChatClient for OpenRouter
- WorkflowBuilder for orchestration
- FileCheckpointStorage for state
- Native async/await throughout
- Pydantic dataclasses for validation
```

---

## 🔄 Mapping Old to New

### 1. Agent Pattern

**Old (`agentic_layer/base_agent.py`)**:
```python
class BaseAgent(ABC):
    def __init__(self, agent_name, model_dispatcher, tool_registry, system_prompt):
        self.agent_name = agent_name
        self.model_dispatcher = model_dispatcher
        self.tool_registry = tool_registry
        self.system_prompt = system_prompt
    
    async def _call_llm(self, user_prompt, history=None, tools=None, **kwargs):
        # Custom LLM calling logic
        response, model_details = await self.model_dispatcher.dispatch(...)
        # Custom logging and stats tracking
        return response, model_details
    
    async def _execute_tool(self, tool_name, tool_arguments, **kwargs):
        # Custom tool execution
        return await self.tool_registry.execute(...)
    
    @abstractmethod
    async def run(self, context):
        # Custom agent logic
        pass
```

**New (`prowzi/agents/intent_agent.py`)**:
```python
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient

class IntentAgent:
    def __init__(self, config=None):
        self.config = config or get_config()
        
        # MS Agent Framework client
        self.chat_client = OpenAIChatClient(
            api_key=self.config.openrouter_api_key,
            base_url=self.config.openrouter_base_url,
            model=model_config.name,
        )
        
        # Framework agent with instructions
        self.agent = ChatAgent(
            chat_client=self.chat_client,
            instructions=self._create_system_prompt(),
        )
    
    async def analyze(self, prompt, document_paths=None):
        # Simple, clean agent invocation
        response = await self.agent.run(prompt)
        # Parse and return structured result
        return self._parse_response(response.response)
```

**Key Differences**:
- ❌ No custom base class needed
- ❌ No manual LLM dispatcher
- ❌ No tool registry management
- ✅ Use framework's ChatAgent
- ✅ OpenAIChatClient handles OpenRouter
- ✅ Clean async/await patterns
- ✅ Structured outputs via Pydantic

### 2. Model Management

**Old (`agentic_layer/model_dispatcher.py`)**:
```python
class ModelDispatcher:
    def __init__(self, config):
        self.models = config['models']
        self.fallbacks = config['fallbacks']
        self.clients = {}  # Manual client management
    
    async def dispatch(self, messages, model=None, agent_mode=None, **kwargs):
        # 600+ lines of custom routing logic
        # Manual retry logic
        # Manual fallback handling
        # Custom cost tracking
        # WebSocket event emission
        pass
```

**New (`prowzi/config/settings.py`)**:
```python
@dataclass
class ModelConfig:
    name: str
    provider: str
    cost_per_1m_input: float
    cost_per_1m_output: float
    max_tokens: int
    context_window: int
    supports_tools: bool
    tier: ModelTier

class ProwziConfig:
    def __init__(self):
        self.models = self._initialize_models()
        self.agents = self._initialize_agents()
        
    def get_model_for_agent(self, agent_name) -> ModelConfig:
        agent_config = self.agents[agent_name]
        return self.models[agent_config.primary_model]
    
    def estimate_cost(self, input_tokens, output_tokens, model_name) -> float:
        model = self.models[model_name]
        return (input_tokens/1M * model.cost_per_1m_input + 
                output_tokens/1M * model.cost_per_1m_output)
```

**Each agent creates its own client**:
```python
# Intent Agent uses Claude 4.5 Sonnet
client = OpenAIChatClient(
    api_key=config.openrouter_api_key,
    base_url=config.openrouter_base_url,
    model="anthropic/claude-4.5-sonnet"
)

# Planning Agent uses GPT-4o
client = OpenAIChatClient(
    api_key=config.openrouter_api_key,
    base_url=config.openrouter_base_url,
    model="openai/gpt-4o"
)
```

**Key Differences**:
- ❌ No central dispatcher needed
- ❌ No manual retry logic
- ✅ Each agent gets optimal model
- ✅ Framework handles retries
- ✅ OpenRouter provides fallbacks
- ✅ Simple cost calculation

### 3. Tool Management

**Old (`agentic_layer/tool_registry.py`)**:
```python
class ToolRegistry:
    def __init__(self):
        self.tools = {}
        self.tool_schemas = {}
    
    def register_tool(self, name, function, schema):
        # Manual tool registration
        self.tools[name] = function
        self.tool_schemas[name] = schema
    
    async def execute(self, tool_name, arguments):
        # Manual execution with error handling
        # Custom logging
        # Context injection
        pass
```

**New (`prowzi/tools/`)**:
```python
# Pure functions - no registry needed
async def parse_document(file_path: str) -> Dict[str, Any]:
    """Parse document and return structured data"""
    # Simple, testable function
    return {
        "content": content,
        "metadata": metadata,
        "word_count": word_count,
    }

async def multi_engine_search(
    query: str,
    engines: List[SearchEngine],
    max_results: int = 10
) -> List[SearchResult]:
    """Search across multiple engines"""
    # Clean async function
    tasks = [engine.search(query) for engine in engines]
    results = await asyncio.gather(*tasks)
    return deduplicate_results(results)
```

**Key Differences**:
- ❌ No tool registry needed
- ❌ No manual schema management
- ✅ Import and call directly
- ✅ Type hints provide schema
- ✅ Easy to test in isolation
- ✅ No hidden dependencies

### 4. Orchestration

**Old (`agentic_layer/agent_controller.py`)**:
```python
class AgentController:
    def __init__(self):
        self.agents = {}
        self.context_manager = ACEContextManager()
        self.workflow_state = WorkflowState.INITIALIZATION
    
    async def run_workflow(self, mission_id, user_input):
        # 600+ lines of custom orchestration
        # Manual stage transitions
        # Custom error handling
        # WebSocket event emission
        # Manual checkpointing
        
        # Stage 1: Intent
        intent_result = await self.intent_agent.run(context)
        context = self.context_manager.update(mission_id, intent_result)
        
        # Stage 2: Planning
        planning_result = await self.planning_agent.run(context)
        context = self.context_manager.update(mission_id, planning_result)
        
        # ... 5 more stages
        # ... manual error recovery
        # ... manual WebSocket updates
```

**New (`prowzi/workflows/orchestrator.py`)**:
```python
from agent_framework import WorkflowBuilder
from agent_framework._workflows import FileCheckpointStorage

class ProwziOrchestrator:
    def __init__(self, config=None):
        self.config = config or get_config()
        self.agents = self._initialize_agents()
    
    async def run_research(self, prompt, document_paths=None, checkpoint_id=None):
        # Build workflow using framework
        workflow = (
            WorkflowBuilder()
            .add_edge(self.agents["intent"], self.agents["planning"])
            .add_edge(self.agents["planning"], self.agents["search"])
            .add_edge(self.agents["search"], self.agents["verification"])
            .add_edge(self.agents["verification"], self.agents["writing"])
            .add_edge(self.agents["writing"], self.agents["evaluation"])
            .add_edge(self.agents["evaluation"], self.agents["turnitin"], conditional=True)
            .with_checkpointing(FileCheckpointStorage("./checkpoints"))
            .build()
        )
        
        # Stream events (framework handles everything)
        async for event in workflow.run_stream({"prompt": prompt}):
            yield event
```

**Key Differences**:
- ❌ No 600-line controller needed
- ❌ No manual stage management
- ❌ No custom error handling
- ✅ Declarative workflow builder
- ✅ Built-in checkpointing
- ✅ Automatic error recovery
- ✅ Clean event streaming

---

## 🏗️ Current Implementation Details

### Configuration (`prowzi/config/settings.py`)

**Complete** - 500 lines

Models configured:
```python
{
    "claude-4.5-sonnet": ModelConfig(
        name="anthropic/claude-4.5-sonnet",
        cost_per_1m_input=3.0,
        context_window=1_000_000,
        tier=ModelTier.PREMIUM
    ),
    "gpt-4o": ModelConfig(
        name="openai/gpt-4o",
        cost_per_1m_input=2.5,
        context_window=128_000,
        tier=ModelTier.ADVANCED
    ),
    "gemini-2.0-flash": ModelConfig(
        name="google/gemini-2.0-flash-exp:free",
        cost_per_1m_input=0.0,
        context_window=1_000_000,
        tier=ModelTier.STANDARD
    ),
}
```

Agent assignments:
```python
{
    "intent": AgentConfig(
        primary_model="claude-4.5-sonnet",  # 1M context for docs
        fallback_models=["claude-3.5-sonnet", "gpt-4o"],
        temperature=0.3
    ),
    "planning": AgentConfig(
        primary_model="gpt-4o",  # Best at structured planning
        fallback_models=["claude-3.5-sonnet"],
        temperature=0.5
    ),
    "search": AgentConfig(
        primary_model="gemini-2.0-flash",  # Fast, free
        fallback_models=["gpt-4o-mini"],
        temperature=0.4
    ),
}
```

### Intent Agent (`prowzi/agents/intent_agent.py`)

**Complete** - 400 lines

From old implementation:
```python
# OLD: agentic_layer/agents/intent_context_agent.py (445 lines)
class IntentContextAgent(BaseAgent):
    async def run(self, context):
        # Parse documents with custom logic
        # Call LLM through dispatcher
        # Manual result parsing
        # Manual context updates
        return agent_output_tuple
```

To new implementation:
```python
# NEW: prowzi/agents/intent_agent.py (400 lines)
class IntentAgent:
    async def analyze(self, prompt, document_paths=None):
        # 1. Parse documents using tools
        parsed_docs = parse_multiple_documents(document_paths)
        
        # 2. Generate summaries with parsing agent
        summaries = []
        for doc in parsed_docs:
            response = await self.parsing_agent.run(summary_prompt)
            summaries.append(response.response)
        
        # 3. Analyze intent with intent agent
        response = await self.intent_agent.run(intent_prompt)
        
        # 4. Parse JSON and return structured IntentAnalysis
        return IntentAnalysis(**parsed_json)
```

Key improvements:
- Clean separation: document parsing (tools) vs intent analysis (agent)
- Structured output via Pydantic dataclass
- No manual context management
- Simple async/await flow

### Planning Agent (`prowzi/agents/planning_agent.py`)

**Complete** - 500 lines

From old implementation:
```python
# OLD: agentic_layer/agents/planning_agent.py
class PlanningAgent(BaseAgent):
    async def run(self, context):
        # Extract intent from context
        # Generate task hierarchy
        # Generate search queries
        # Manual dependency resolution
        # Return complex nested dict
```

To new implementation:
```python
# NEW: prowzi/agents/planning_agent.py
class PlanningAgent:
    async def create_plan(self, intent_analysis):
        # 1. Build planning prompt from intent
        prompt = self._build_planning_prompt(intent_analysis)
        
        # 2. Get plan from agent
        response = await self.agent.run(prompt)
        
        # 3. Parse into structured ResearchPlan
        plan = self._parse_plan_response(response.response, intent_analysis)
        
        return plan  # ResearchPlan dataclass
```

Structured outputs:
```python
@dataclass
class ResearchPlan:
    task_hierarchy: Task
    execution_order: List[str]
    parallel_groups: List[List[str]]
    search_queries: List[SearchQuery]
    quality_checkpoints: List[QualityCheckpoint]
    resource_estimates: Dict[str, Any]
    contingencies: List[Dict[str, str]]
```

### Search Tools (`prowzi/tools/search_tools.py`)

**Complete** - 500 lines (3/8 APIs)

Old approach was scattered across multiple files. New approach is centralized:

```python
# Standardized result format
@dataclass
class SearchResult:
    title: str
    url: str
    content: str
    source_type: SourceType
    author: Optional[str]
    citation_count: Optional[int]
    relevance_score: float

# Engine implementations
class SemanticScholarSearch(SearchEngine):
    async def search(self, query, max_results=10):
        # Semantic Scholar API integration
        return [SearchResult(...), ...]

class ArXivSearch(SearchEngine):
    async def search(self, query, max_results=10):
        # arXiv API integration
        return [SearchResult(...), ...]

# Parallel multi-engine search
async def multi_engine_search(query, engines, max_results_per_engine=10):
    tasks = [engine.search(query, max_results_per_engine) for engine in engines]
    results = await asyncio.gather(*tasks)
    return deduplicate_results(flatten(results))
```

---

## 🎯 Implementation Roadmap

### Phase 1: Foundation (✅ Complete)

**Goal**: Establish architecture and core components  
**Duration**: 1 week  
**Status**: ✅ Done

Completed:
- [x] Configuration system with multi-model support
- [x] Intent Agent with document parsing
- [x] Planning Agent with task decomposition
- [x] Document parsing tools (PDF/DOCX/MD/TXT)
- [x] Search tools (Semantic Scholar, arXiv, PubMed)
- [x] Package structure and initialization
- [x] Comprehensive documentation

### Phase 2: Search & Verification (🚧 Current)

**Goal**: Implement evidence gathering and validation  
**Duration**: 1 week  
**Status**: 🚧 In Progress

Tasks:
- [ ] Search Agent (execute queries, score relevance)
- [ ] Complete search tool integrations (Perplexity, Exa, Tavily, Serper, You.com)
- [ ] Verification Agent (credibility scoring, bias detection)
- [ ] Analysis tools (relevance scoring, content extraction)

### Phase 3: Writing & Evaluation (📅 Next)

**Goal**: Generate and assess academic content  
**Duration**: 1 week  
**Status**: 📅 Planned

Tasks:
- [ ] Writing Agent (content generation, citation management)
- [ ] Citation tools (bibliography generation, format conversion)
- [ ] Evaluation Agent (quality assessment, rubric scoring)
- [ ] Improvement recommendation system

### Phase 4: Orchestration & Testing (📅 Upcoming)

**Goal**: Complete workflow and ensure quality  
**Duration**: 1 week  
**Status**: 📅 Planned

Tasks:
- [ ] Master Orchestrator (Sequential workflow, checkpointing)
- [ ] Comprehensive test suite (80% coverage)
- [ ] Integration tests for full workflow
- [ ] Performance optimization
- [ ] Error recovery testing

### Phase 5: Optional Features (📅 Future)

**Goal**: Advanced features for production  
**Duration**: 2-3 weeks  
**Status**: 📅 Optional

Tasks:
- [ ] Turnitin Agent (browser automation)
- [ ] CLI interface (Rich terminal UI)
- [ ] WebSocket support (real-time updates)
- [ ] Caching layer (result persistence)
- [ ] Admin dashboard

---

## 📖 Documentation Structure

### For Developers

1. **PROWZI_REIMPLEMENTATION_GUIDE.md** (this file)
   - Complete context and architecture comparison
   - Old vs new patterns
   - Implementation roadmap

2. **IMPLEMENTATION_STATUS.md** (`prowzi/`)
   - Current progress (60% complete)
   - Component status and metrics
   - Next steps

3. **IMPLEMENTATION_SUMMARY.md** (`prowzi/`)
   - What was built (detailed)
   - How to use it now
   - Code examples

4. **QUICKREF.md** (`prowzi/`)
   - Quick start guide
   - API reference
   - Common patterns

### For Context

5. **Original Specs** (`overhaul/05-15_*.md`)
   - Agent specifications from v1
   - Architecture patterns
   - Implementation details

6. **Old Implementation** (`agentic_layer/`)
   - Reference implementation
   - Patterns to adapt
   - Lessons learned

---

## 🔑 Key Principles

### 1. Simplicity Over Complexity

**Old**: Custom base classes, manual coordination, explicit state management  
**New**: Framework abstractions, declarative workflows, implicit state

### 2. Composition Over Inheritance

**Old**: `class IntentAgent(BaseAgent)`  
**New**: `class IntentAgent:` with `ChatAgent` instance

### 3. Explicit Over Implicit

**Old**: Hidden context updates, magical state transitions  
**New**: Clear data flow, structured outputs, visible state

### 4. Type Safety

**Old**: Untyped dicts, manual validation  
**New**: Pydantic dataclasses, type hints everywhere

### 5. Async First

**Old**: Mixed sync/async, manual event loops  
**New**: Async by default, proper `await` usage

### 6. Testability

**Old**: Tightly coupled, hard to mock  
**New**: Pure functions, dependency injection, easy to test

---

## 💡 Lessons from Old Implementation

### What Worked Well

1. **7-Stage Sequential Workflow** ✅
   - Clear separation of concerns
   - Easy to understand and debug
   - Good checkpointing boundaries
   - **Keeping this pattern**

2. **Multi-Model Strategy** ✅
   - Different models for different tasks
   - Cost optimization
   - Fallback handling
   - **Enhanced with OpenRouter**

3. **Structured Outputs** ✅
   - JSON schemas for agent responses
   - Validation at boundaries
   - **Improved with Pydantic**

4. **ACE Context System** ✅
   - Session, User, Knowledge layers
   - Good for state management
   - **Simplified with WorkflowContext**

### What Needed Improvement

1. **Custom Base Classes** ❌
   - Too much boilerplate
   - Hard to understand
   - **Replaced with ChatAgent**

2. **Manual Orchestration** ❌
   - 600+ lines of controller code
   - Error-prone state transitions
   - **Replaced with WorkflowBuilder**

3. **Tool Registry** ❌
   - Unnecessary abstraction
   - Hard to test
   - **Replaced with direct imports**

4. **Model Dispatcher** ❌
   - Complex retry logic
   - Manual fallback handling
   - **Replaced with OpenRouter + framework**

5. **Mixed Patterns** ❌
   - Some sync, some async
   - Inconsistent error handling
   - **Standardized with async everywhere**

---

## 🚀 Getting Started

### For Contributors

1. **Understand the framework**:
   ```bash
   cd ../../  # Root of AgentONE
   cat README.md  # MS Agent Framework overview
   cat python/examples/03_magentic_workflow.py  # Advanced patterns
   ```

2. **Review current implementation**:
   ```bash
   cd python/prowzi
   cat IMPLEMENTATION_STATUS.md  # Current status
   cat QUICKREF.md  # Quick reference
   python quickstart.py  # Working demo
   ```

3. **Compare with old implementation**:
   ```bash
   cd ../../agentic_layer
   ls agents/  # Old agent implementations
   cat agent_controller.py  # Old orchestration
   ```

4. **Implement next agent**:
   - Use Intent or Planning agent as template
   - Follow MS Agent Framework patterns
   - Add comprehensive tests
   - Update documentation

### For Users

1. **Install and configure**:
   ```bash
   cd python
   uv sync --dev
   echo "OPENAI_API_KEY=sk-or-v1-..." > .env
   ```

2. **Run demo**:
   ```bash
   cd prowzi
   python quickstart.py
   ```

3. **Use in code**:
   ```python
   from prowzi import IntentAgent, PlanningAgent
   
   intent = IntentAgent()
   analysis = await intent.analyze("Your research prompt")
   
   planner = PlanningAgent()
   plan = await planner.create_plan(analysis)
   ```

---

## 📞 Questions & Support

**Architecture Questions**: See sections above comparing old vs new  
**Implementation Details**: See `IMPLEMENTATION_STATUS.md`  
**Usage Examples**: See `QUICKREF.md` and `quickstart.py`  
**Framework Docs**: See `../../README.md` and `../../docs/`  
**Old Prowzi Specs**: See `overhaul/05-15_*.md`

---

**Last Updated**: January 2025  
**Maintainer**: MS Agent Framework Implementation Team  
**Status**: Foundation complete, MVP in progress 🚀
