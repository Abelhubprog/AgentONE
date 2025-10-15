# Prowzi Quick Reference

## 🚀 Installation

```bash
cd python
uv sync --dev
```

## 🔧 Configuration

Create `python/.env`:
```bash
OPENAI_API_KEY=sk-or-v1-...  # OpenRouter key (required)
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

## 📝 Basic Usage

### Intent Analysis
```python
from prowzi import IntentAgent

intent_agent = IntentAgent()
analysis = await intent_agent.analyze(
    prompt="Write 10000-word PhD literature review on AI in healthcare",
    document_paths=["paper.pdf"]  # Optional
)

print(analysis.document_type)  # "literature_review"
print(analysis.field)           # "healthcare_ai"
print(analysis.word_count)      # 10000
print(analysis.confidence_score)  # 0.85
```

### Research Planning
```python
from prowzi import PlanningAgent

planning_agent = PlanningAgent()
plan = await planning_agent.create_plan(analysis)

print(len(plan.search_queries))  # 11 queries
print(plan.resource_estimates['total_cost_usd'])  # $2.50
```

### Document Parsing
```python
from prowzi.tools import parse_document

result = parse_document("paper.pdf")
print(result['word_count'])  # 5234
print(result['metadata'])    # {title, author, ...}
```

### Academic Search
```python
from prowzi.tools import SemanticScholarSearch, ArXivSearch, multi_engine_search

engines = [SemanticScholarSearch(), ArXivSearch()]
results = await multi_engine_search(
    query="AI in clinical decision support",
    engines=engines,
    max_results_per_engine=10
)

for r in results:
    print(f"{r.title} ({r.citation_count} citations)")
```

## 📊 Available Models

| Model | Context | Cost (Input) | Best For |
|-------|---------|--------------|----------|
| Claude 4.5 Sonnet | 1M | $3.0/1M | Document parsing, writing |
| GPT-4o | 128K | $2.5/1M | Planning, evaluation |
| Gemini 2.0 Flash | 1M | FREE | Search, batch tasks |
| Claude 3.5 Sonnet | 200K | $3.0/1M | Analysis, verification |
| GPT-4o-mini | 128K | $0.15/1M | General tasks |

## 🎯 Agent Configurations

```python
from prowzi.config import get_config

config = get_config()

# Get agent model
model = config.get_model_for_agent("intent")  # Claude 4.5

# Estimate cost
cost = config.estimate_cost(
    input_tokens=100_000,
    output_tokens=5_000,
    model_name="gpt-4o"
)  # $0.28

# Get enabled search APIs
apis = config.get_enabled_search_apis()
```

## 🔍 Search Engines

| Engine | Type | Free | Focus |
|--------|------|------|-------|
| Semantic Scholar | Academic | ✅ | Papers, citations |
| arXiv | Academic | ✅ | Preprints (CS, physics) |
| PubMed | Academic | ✅ | Biomedical |
| Perplexity | Web | ❌ | AI-powered search |
| Exa | Web | ❌ | Semantic search |
| Tavily | Web | ❌ | Research-focused |

## 📁 Package Structure

```
prowzi/
├── agents/           # Specialized agents
│   ├── intent_agent.py      ✅
│   ├── planning_agent.py    ✅
│   └── ...                  🚧
├── tools/            # Reusable tools
│   ├── parsing_tools.py     ✅
│   ├── search_tools.py      ✅
│   └── ...                  🚧
├── config/           # Configuration
│   └── settings.py          ✅
└── workflows/        # Orchestration
    └── orchestrator.py      🚧
```

## 📊 Data Models

### IntentAnalysis
```python
analysis.document_type      # "literature_review"
analysis.field              # "healthcare_ai"
analysis.academic_level     # "phd"
analysis.word_count         # 10000
analysis.explicit_requirements
analysis.implicit_requirements
analysis.missing_info
analysis.confidence_score   # 0.0-1.0
```

### ResearchPlan
```python
plan.task_hierarchy         # Root task tree
plan.execution_order        # ["task1", "task2", ...]
plan.search_queries         # [SearchQuery(...), ...]
plan.quality_checkpoints    # [QualityCheckpoint(...), ...]
plan.resource_estimates     # {duration, tokens, cost}
```

### SearchResult
```python
result.title
result.url
result.content              # Abstract/snippet
result.source_type          # ACADEMIC_PAPER, PREPRINT, WEB_ARTICLE
result.author
result.citation_count
result.relevance_score
```

## ⚡ Quick Start

```bash
# Run demo
cd python/prowzi
uv run python quickstart.py

# Or use in code
python3 << 'EOF'
import asyncio
from prowzi import IntentAgent, PlanningAgent

async def demo():
    intent = IntentAgent()
    analysis = await intent.analyze("Write PhD review on quantum computing")
    
    planner = PlanningAgent()
    plan = await planner.create_plan(analysis)
    
    print(f"Queries: {len(plan.search_queries)}")
    print(f"Cost: ${plan.resource_estimates['total_cost_usd']:.2f}")

asyncio.run(demo())
EOF
```

## 🐛 Troubleshooting

**Missing API Key**:
```bash
export OPENAI_API_KEY=sk-or-v1-...
```

**Import Error**:
```bash
cd python
uv sync --dev
```

**Document Parsing Error**:
```bash
pip install PyPDF2 python-docx
```

**Search API Error**:
- Check API key in .env
- Verify API is enabled in config
- Some APIs require paid accounts

## 📖 Documentation

- **IMPLEMENTATION_STATUS.md** - Complete status (700 lines)
- **IMPLEMENTATION_SUMMARY.md** - What was built (500 lines)
- **quickstart.py** - Working demo (200 lines)
- **Inline docs** - All functions have docstrings

## 🎯 Status

| Component | Status | Lines |
|-----------|--------|-------|
| Config System | ✅ | 500 |
| Intent Agent | ✅ | 400 |
| Planning Agent | ✅ | 500 |
| Parsing Tools | ✅ | 350 |
| Search Tools | ✅ | 500 |
| Search Agent | 🚧 | - |
| Verification | 🚧 | - |
| Writing | 🚧 | - |
| Evaluation | 🚧 | - |
| Orchestrator | 🚧 | - |

**Total**: 60% complete | 2,750+ lines | MVP in 2-3 weeks

## 🔗 Links

- **MS Agent Framework**: `../../README.md`
- **Old Prowzi Specs**: `../../overhaul/`
- **Examples**: `../../python/examples/`

---

*Prowzi: Autonomous research excellence* 🚀
