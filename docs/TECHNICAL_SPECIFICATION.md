# Prowzi Technical Specification - MS Agent Framework

**Version**: 2.0
**Framework**: Microsoft Agent Framework v1.0.0b251007
**Language**: Python 3.13+
**Status**: Foundation Complete (60%)

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Component Specifications](#component-specifications)
4. [Data Models](#data-models)
5. [Workflows](#workflows)
6. [API Integrations](#api-integrations)
7. [Performance Requirements](#performance-requirements)
8. [Security & Privacy](#security--privacy)
9. [Testing Strategy](#testing-strategy)

---

## System Overview

### Purpose

Prowzi is an autonomous multi-agent system that automates academic research and writing. It transforms a research prompt and optional documents into high-quality academic content with proper citations, quality validation, and plagiarism checking.

### Key Features

- **Autonomous Operation**: Minimal human intervention required
- **Multi-Model Strategy**: Uses optimal LLM for each task (Claude, GPT-4, Gemini)
- **Academic Source Integration**: 8+ search engines (Semantic Scholar, arXiv, PubMed, etc.)
- **Quality Assurance**: Multi-stage verification and evaluation
- **Production Ready**: Error recovery, checkpointing, observability

### System Capabilities

| Capability | Status | Implementation |
|------------|--------|----------------|
| Document Parsing | ✅ Complete | PDF, DOCX, Markdown, TXT |
| Intent Analysis | ✅ Complete | Claude 4.5 Sonnet (1M context) |
| Research Planning | ✅ Complete | GPT-4o (128K context) |
| Multi-Engine Search | 🚧 Partial | 3/8 engines integrated |
| Source Verification | 📅 Planned | Credibility scoring |
| Content Generation | 📅 Planned | Claude 4.5 Sonnet |
| Quality Evaluation | 📅 Planned | GPT-4o with rubric |
| Plagiarism Check | 📅 Optional | Turnitin automation |
| Checkpointing | 📅 Planned | FileCheckpointStorage |
| Observability | 📅 Planned | OpenTelemetry |

---

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User Interface                        │
│  (CLI / API / WebSocket) - Future implementation            │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   Master Orchestrator                        │
│  - WorkflowBuilder (Sequential pattern)                     │
│  - FileCheckpointStorage                                     │
│  - Event streaming                                           │
└────────────┬────────────────────────────────────────────────┘
             │
             │ 7-Stage Sequential Pipeline
             │
             ├─► Stage 1: Intent & Context Agent
             │   - Document parsing (PDF/DOCX/MD/TXT)
             │   - Requirement extraction
             │   - Model: Claude 4.5 Sonnet (1M context)
             │
             ├─► Stage 2: Planning Agent
             │   - Task decomposition (47+ subtasks)
             │   - Search query generation (11+ queries)
             │   - Resource estimation
             │   - Model: GPT-4o (128K context)
             │
             ├─► Stage 3: Evidence Search Agent
             │   - Multi-engine search (8 APIs)
             │   - Parallel execution
             │   - Result aggregation & deduplication
             │   - Model: Gemini 2.0 Flash (free, 1M context)
             │
             ├─► Stage 4: Verification Agent
             │   - Credibility scoring
             │   - Bias detection
             │   - Citation validation
             │   - Model: Claude 3.5 Sonnet
             │
             ├─► Stage 5: Writing Agent
             │   - Academic content generation
             │   - Citation integration
             │   - Structure adherence
             │   - Model: Claude 4.5 Sonnet (1M context)
             │
             ├─► Stage 6: Evaluation Agent
             │   - Quality assessment
             │   - Rubric scoring
             │   - Improvement recommendations
             │   - Model: GPT-4o
             │
             └─► Stage 7: Turnitin Agent (Optional)
                 - Plagiarism detection
                 - AI content detection
                 - Iterative refinement
                 - Model: Gemini Computer Use Agent
```

### Technology Stack

#### Core Framework
```python
agent_framework==1.0.0b251007  # MS Agent Framework
pydantic>=2.0.0                # Data validation
aiohttp>=3.9.0                 # Async HTTP
asyncio                        # Async runtime
```

#### LLM Gateway
```python
# OpenRouter (unified access to 100+ models)
base_url: https://openrouter.ai/api/v1
models:
  - anthropic/claude-4.5-sonnet      # $3/1M input
  - openai/gpt-4o                    # $2.5/1M input
  - google/gemini-2.0-flash-exp:free # Free
  - anthropic/claude-3.5-sonnet      # $3/1M input
  - openai/gpt-4o-mini               # $0.15/1M input
```

#### Document Parsing
```python
PyPDF2>=3.0.0       # PDF parsing
python-docx>=1.1.0  # DOCX parsing
pyyaml>=6.0.0       # YAML/Markdown frontmatter
```

#### Search APIs
```python
# Academic sources
- Semantic Scholar API (semanticscholar.org)
- arXiv API (export.arxiv.org)
- PubMed E-utilities (eutils.ncbi.nlm.nih.gov)

# Web sources
- Perplexity API
- Exa API (exa.ai)
- Tavily API
- Serper API
- You.com API
```

#### Optional Features
```python
playwright>=1.40.0     # Browser automation (Turnitin)
rich>=13.0.0           # CLI interface
opentelemetry-sdk      # Observability
```

---

## Component Specifications

### 1. Intent & Context Agent

**Purpose**: Parse documents and extract research requirements

**Status**: ✅ Complete (400 lines)

**Implementation**:
```python
class IntentAgent:
    """
    Entry point for Prowzi. Analyzes user prompts and documents
    to extract structured research requirements.
    """

    def __init__(self, config: ProwziConfig = None):
        self.config = config or get_config()
        model_config = self.config.get_model_for_agent("intent")

        # Two-stage processing
        self.parsing_agent = ChatAgent(
            chat_client=OpenAIChatClient(...),
            instructions=self.PARSING_PROMPT
        )

        self.intent_agent = ChatAgent(
            chat_client=OpenAIChatClient(...),
            instructions=self.INTENT_PROMPT
        )

    async def analyze(
        self,
        prompt: str,
        document_paths: Optional[List[str]] = None
    ) -> IntentAnalysis:
        """
        Analyze user intent from prompt and documents.

        Returns:
            IntentAnalysis with 15+ structured fields
        """
```

**Input**:
- User prompt (string)
- Optional document paths (list of file paths)

**Output** (IntentAnalysis dataclass):
```python
@dataclass
class IntentAnalysis:
    document_type: str              # "literature_review", "thesis", etc.
    field: str                      # "computer_science_ai_ml"
    academic_level: str             # "phd", "masters", "undergraduate"
    word_count: int                 # Target word count
    explicit_requirements: List[str] # User-stated requirements
    implicit_requirements: List[str] # Inferred requirements
    missing_info: List[str]          # Questions to clarify
    confidence_score: float          # 0-100
    citation_style: str              # "APA", "MLA", "IEEE", "Harvard"
    region: Optional[str]            # Geographic focus
    timeframe: Optional[str]         # "2020-2024", "last_5_years"
    parsed_documents: List[Dict]     # Parsed document metadata
```

**Model**: Claude 4.5 Sonnet
- **Context Window**: 1,000,000 tokens
- **Cost**: $3.00 per 1M input tokens
- **Why**: Best for parsing large documents and extracting structured information

**Performance**:
- Parse time: ~5-10 seconds for typical PhD prompt
- Document processing: ~2-5 seconds per document
- Confidence threshold: ≥70% for auto-proceed

### 2. Planning Agent

**Purpose**: Decompose research into tasks and generate search queries

**Status**: ✅ Complete (500 lines)

**Implementation**:
```python
class PlanningAgent:
    """
    Creates comprehensive research plan with task hierarchy,
    search queries, and quality checkpoints.
    """

    def __init__(self, config: ProwziConfig = None):
        self.config = config or get_config()
        model_config = self.config.get_model_for_agent("planning")

        self.agent = ChatAgent(
            chat_client=OpenAIChatClient(...),
            instructions=self.PLANNING_PROMPT
        )

    async def create_plan(
        self,
        intent_analysis: IntentAnalysis
    ) -> ResearchPlan:
        """
        Generate comprehensive research plan.

        Returns:
            ResearchPlan with hierarchical tasks and queries
        """
```

**Input**:
- IntentAnalysis from Intent Agent

**Output** (ResearchPlan dataclass):
```python
@dataclass
class ResearchPlan:
    task_hierarchy: Task                  # Root task with subtasks
    execution_order: List[str]            # Task IDs in order
    parallel_groups: List[List[str]]      # Tasks that can run parallel
    search_queries: List[SearchQuery]     # 11+ generated queries
    quality_checkpoints: List[QualityCheckpoint]
    resource_estimates: Dict[str, Any]    # Time, cost, sources
    contingencies: List[Dict[str, str]]   # Fallback plans

@dataclass
class Task:
    id: str
    name: str
    description: str
    priority: TaskPriority    # CRITICAL, HIGH, MEDIUM, LOW
    depends_on: List[str]     # Task IDs
    subtasks: List['Task']    # Recursive hierarchy
    duration_minutes: int
    assigned_agent: str
    queries: List[str]        # Related search queries

@dataclass
class SearchQuery:
    query: str
    query_type: QueryType     # BROAD, SPECIFIC, COMPARATIVE, etc.
    priority: TaskPriority
    category: str             # "foundations", "methodology", etc.
    estimated_sources: int
    keywords: List[str]
```

**Task Hierarchy**:
```
Root: Complete Literature Review (255 min)
├─ 1. Foundation Research (60 min)
│  ├─ 1.1 Define Scope
│  ├─ 1.2 Identify Key Concepts
│  └─ 1.3 Map Relationships
├─ 2. Source Collection (90 min)
│  ├─ 2.1 Execute Searches
│  ├─ 2.2 Screen Results
│  └─ 2.3 Collect Papers
├─ 3. Source Analysis (75 min)
│  ├─ 3.1 Verify Credibility
│  ├─ 3.2 Extract Key Findings
│  └─ 3.3 Synthesize Insights
├─ 4. Content Generation (60 min)
│  ├─ 4.1 Write Introduction
│  ├─ 4.2 Write Literature Review
│  ├─ 4.3 Write Methodology
│  ├─ 4.4 Write Discussion
│  └─ 4.5 Write Conclusion
└─ 5. Quality Assurance (30 min)
   ├─ 5.1 Evaluate Content
   ├─ 5.2 Check Citations
   └─ 5.3 Final Review
```

**Query Types**:
1. **BROAD**: General overview queries
2. **SPECIFIC**: Targeted technical queries
3. **COMPARATIVE**: Comparison queries
4. **RECENT**: Latest developments (2020-2024)
5. **METHODOLOGICAL**: Research methods
6. **CHALLENGE**: Open problems

**Model**: GPT-4o
- **Context Window**: 128,000 tokens
- **Cost**: $2.50 per 1M input tokens
- **Why**: Best at structured planning and task decomposition

**Performance**:
- Planning time: ~10-15 seconds
- Typical output: 47 tasks, 11 queries
- Estimated cost for execution: ~$2.50

### 3. Evidence Search Agent

**Purpose**: Execute search queries across multiple engines

**Status**: 🚧 In Progress (implementation needed)

**Design**:
```python
class SearchAgent:
    """
    Executes search queries across multiple academic and web
    search engines, aggregates results, scores relevance.
    """

    def __init__(self, config: ProwziConfig = None):
        self.config = config or get_config()
        model_config = self.config.get_model_for_agent("search")

        self.relevance_scorer = ChatAgent(
            chat_client=OpenAIChatClient(...),
            instructions=self.SCORING_PROMPT
        )

        # Initialize search engines
        self.engines = [
            SemanticScholarSearch(config.search_apis["semantic_scholar"]),
            ArXivSearch(config.search_apis["arxiv"]),
            PubMedSearch(config.search_apis["pubmed"]),
            # + 5 more engines
        ]

    async def execute_searches(
        self,
        plan: ResearchPlan,
        max_results_per_query: int = 50
    ) -> List[SearchResult]:
        """
        Execute all search queries and return scored results.
        """
```

**Input**:
- ResearchPlan with search queries
- Configuration (max results, engines to use)

**Output**:
- List[SearchResult] with relevance scores
- Deduplication applied
- Sorted by relevance

**Search Engines** (8 total):

| Engine | Status | Type | Cost | Rate Limit |
|--------|--------|------|------|------------|
| Semantic Scholar | ✅ Complete | Academic | Free | 100/5min |
| arXiv | ✅ Complete | Preprints | Free | Unlimited |
| PubMed | ✅ Complete | Biomedical | Free | 3 req/sec |
| Perplexity | 🚧 Stub | Web + AI | $5/1K | 50/min |
| Exa | 🚧 Stub | Web | $5/1K | 1K/day |
| Tavily | 🚧 Stub | Web | $5/1K | 1K/mo free |
| Serper | 🚧 Stub | Google | $5/1K | 2.5K/mo free |
| You.com | 🚧 Stub | Web + AI | $3/1K | 500/mo free |

**Deduplication Strategy**:
```python
def deduplicate_results(results: List[SearchResult]) -> List[SearchResult]:
    """
    Remove duplicates using:
    1. URL exact match
    2. Title similarity (MD5 hash)
    """
    seen_urls = set()
    seen_titles = set()
    unique = []

    for result in results:
        url_match = result.url in seen_urls
        title_hash = hashlib.md5(result.title.lower().encode()).hexdigest()
        title_match = title_hash in seen_titles

        if not url_match and not title_match:
            unique.append(result)
            seen_urls.add(result.url)
            seen_titles.add(title_hash)

    return unique
```

**Model**: Gemini 2.0 Flash
- **Context Window**: 1,000,000 tokens
- **Cost**: Free (experimental)
- **Why**: Fast, free, good enough for relevance scoring

**Performance Requirements**:
- Execute all queries in parallel
- Complete within 60 seconds for 11 queries
- Return top 50 results per query (550 total)
- Deduplicate to ~200-300 unique sources
- Score relevance for filtering

### 4. Verification Agent

**Purpose**: Validate source credibility and quality

**Status**: 📅 Planned (400 lines estimated)

**Design**:
```python
class VerificationAgent:
    """
    Validates sources for credibility, accuracy, recency,
    relevance, and bias.
    """

    def __init__(self, config: ProwziConfig = None):
        self.config = config or get_config()
        model_config = self.config.get_model_for_agent("verification")

        self.agent = ChatAgent(
            chat_client=OpenAIChatClient(...),
            instructions=self.VERIFICATION_PROMPT
        )

    async def verify_sources(
        self,
        search_results: List[SearchResult],
        intent_analysis: IntentAnalysis
    ) -> List[VerificationResult]:
        """
        Verify each source and assign scores.
        """
```

**Input**:
- List[SearchResult] from Search Agent
- IntentAnalysis for context

**Output** (VerificationResult dataclass):
```python
@dataclass
class VerificationResult:
    search_result: SearchResult
    credibility_score: float        # 0-30 points
    accuracy_score: float           # 0-25 points
    recency_score: float            # 0-15 points
    relevance_score: float          # 0-20 points
    bias_score: float               # 0-10 points (lower = less bias)
    total_score: float              # Sum of above (0-100)
    reasoning: str                  # Explanation
    warnings: List[str]             # Any concerns
    approved: bool                  # Pass quality threshold
```

**Scoring Rubric**:

1. **Credibility (0-30)**:
   - Peer-reviewed journal: 30
   - Conference paper: 25
   - Preprint (arXiv): 20
   - Blog/website: 10
   - Unknown: 5

2. **Accuracy (0-25)**:
   - Citations present: +10
   - Data/evidence: +10
   - Methodology clear: +5

3. **Recency (0-15)**:
   - Last 2 years: 15
   - 2-5 years: 10
   - 5-10 years: 5
   - >10 years: 0

4. **Relevance (0-20)**:
   - Directly addresses topic: 20
   - Partially relevant: 10
   - Tangentially related: 5

5. **Bias (0-10)**:
   - No apparent bias: 10
   - Minor bias: 7
   - Significant bias: 3

**Quality Threshold**: Total score ≥60 to approve

**Model**: Claude 3.5 Sonnet
- **Context Window**: 200,000 tokens
- **Cost**: $3.00 per 1M input tokens
- **Why**: Strong analytical reasoning for credibility assessment

**Performance Requirements**:
- Verify 200-300 sources in 5-10 minutes
- Batch processing (10 sources per batch)
- Approve ~50-100 high-quality sources

### 5. Writing Agent

**Purpose**: Generate academic content with citations

**Status**: 📅 Planned (600 lines estimated)

**Design**:
```python
class WritingAgent:
    """
    Generates academic content following structure guidelines
    with integrated citations.
    """

    def __init__(self, config: ProwziConfig = None):
        self.config = config or get_config()
        model_config = self.config.get_model_for_agent("writing")

        self.agent = ChatAgent(
            chat_client=OpenAIChatClient(...),
            instructions=self.WRITING_PROMPT
        )

    async def write_document(
        self,
        plan: ResearchPlan,
        verified_sources: List[VerificationResult],
        intent_analysis: IntentAnalysis,
        evaluation_feedback: Optional[EvaluationResult] = None
    ) -> Document:
        """
        Generate complete academic document.
        """
```

**Input**:
- ResearchPlan (structure guidance)
- List[VerificationResult] (approved sources)
- IntentAnalysis (requirements)
- Optional EvaluationResult (for refinement)

**Output** (Document dataclass):
```python
@dataclass
class Document:
    title: str
    abstract: str
    sections: List[Section]
    bibliography: List[str]
    word_count: int
    citation_count: int
    metadata: Dict[str, Any]

@dataclass
class Section:
    heading: str
    level: int                # 1 = top-level, 2 = subsection
    content: str
    citations: List[Citation]
    word_count: int
```

**Academic Structure**:
```
1. Title Page
2. Abstract (150-300 words)
3. Introduction
   - Context and motivation
   - Research questions/objectives
   - Scope and limitations
4. Literature Review
   - Theoretical foundations
   - Key studies and findings
   - Research gaps
5. Methodology (if applicable)
   - Approach and methods
   - Data sources
6. Results/Discussion
   - Main findings
   - Analysis and interpretation
   - Implications
7. Conclusion
   - Summary of contributions
   - Future directions
8. References
```

**Citation Integration**:
```python
# Inline citations
"Recent studies show AI improves clinical outcomes (Smith et al., 2023)."

# Multiple citations
"This approach has been widely adopted (Jones, 2022; Lee & Park, 2023; Chen, 2024)."

# Direct quotes
'"AI systems must be explainable" (Johnson, 2023, p. 45).'
```

**Model**: Claude 4.5 Sonnet
- **Context Window**: 1,000,000 tokens
- **Cost**: $3.00 per 1M input tokens
- **Why**: Best long-form writer with strong context retention

**Performance Requirements**:
- Generate 5,000-10,000 words in 15-30 minutes
- Maintain coherence across sections
- Integrate 30-50 citations naturally
- Meet target word count (±10%)
- Follow academic style guidelines

### 6. Evaluation Agent

**Purpose**: Assess document quality and provide feedback

**Status**: 📅 Planned (400 lines estimated)

**Design**:
```python
class EvaluationAgent:
    """
    Evaluates document against academic standards and
    provides improvement recommendations.
    """

    def __init__(self, config: ProwziConfig = None):
        self.config = config or get_config()
        model_config = self.config.get_model_for_agent("evaluation")

        self.agent = ChatAgent(
            chat_client=OpenAIChatClient(...),
            instructions=self.EVALUATION_PROMPT
        )

    async def evaluate_document(
        self,
        document: Document,
        intent_analysis: IntentAnalysis,
        verified_sources: List[VerificationResult]
    ) -> EvaluationResult:
        """
        Evaluate document and provide feedback.
        """
```

**Input**:
- Document from Writing Agent
- IntentAnalysis (requirements)
- List[VerificationResult] (expected sources)

**Output** (EvaluationResult dataclass):
```python
@dataclass
class EvaluationResult:
    content_score: float          # 0-30 points
    structure_score: float        # 0-20 points
    citations_score: float        # 0-20 points
    writing_score: float          # 0-20 points
    requirements_score: float     # 0-10 points
    total_score: float            # Sum of above (0-100)
    grade: str                    # A+, A, B+, B, C+, C, D, F
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    approved: bool                # Score ≥ 75
```

**Evaluation Rubric**:

1. **Content (0-30)**:
   - Depth of analysis: 10 points
   - Evidence support: 10 points
   - Originality: 10 points

2. **Structure (0-20)**:
   - Logical flow: 10 points
   - Section completeness: 10 points

3. **Citations (0-20)**:
   - Citation accuracy: 10 points
   - Citation coverage: 5 points
   - Citation formatting: 5 points

4. **Writing (0-20)**:
   - Clarity: 7 points
   - Grammar: 7 points
   - Academic tone: 6 points

5. **Requirements (0-10)**:
   - Meets word count: 5 points
   - Addresses all requirements: 5 points

**Quality Threshold**: Total score ≥75 to approve

**Model**: GPT-4o
- **Context Window**: 128,000 tokens
- **Cost**: $2.50 per 1M input tokens
- **Why**: Strong analytical evaluation with consistent scoring

**Performance Requirements**:
- Evaluate 10,000-word document in 30-60 seconds
- Provide specific, actionable feedback
- Consistent scoring across evaluations

### 7. Turnitin Agent (Optional)

**Purpose**: Check for plagiarism and AI detection

**Status**: 📅 Optional Phase 2 (500 lines estimated)

**Design**:
```python
class TurnitinAgent:
    """
    Submits document to Turnitin, retrieves reports,
    and iteratively refines if thresholds exceeded.
    """

    def __init__(self, config: ProwziConfig = None):
        self.config = config or get_config()

        # Browser automation
        self.browser = await playwright.chromium.launch()

        # Redrafter for improvements
        self.redrafter = ChatAgent(
            chat_client=OpenAIChatClient(...),
            instructions=self.REWRITE_PROMPT
        )

    async def check_plagiarism(
        self,
        document: Document,
        max_iterations: int = 3
    ) -> TurnitinResult:
        """
        Check plagiarism and refine until thresholds met.
        """
```

**Input**:
- Document from Writing Agent
- Max iterations for refinement

**Output** (TurnitinResult dataclass):
```python
@dataclass
class TurnitinResult:
    similarity_score: float       # 0-100%
    ai_detection_score: float     # 0-100%
    reports: List[str]            # Report URLs
    iterations: int               # Refinement iterations
    approved: bool                # Passed thresholds
    final_document: Document      # Refined version
```

**Workflow**:
1. Submit document to Turnitin
2. Wait for report (poll every 30s, timeout 60min)
3. Download similarity and AI detection reports
4. Extract scores
5. If scores exceed thresholds:
   - Call redrafter agent
   - Resubmit refined document
   - Repeat up to max_iterations
6. Return final result

**Thresholds**:
- Similarity: ≤15%
- AI Detection: ≤30%

**Model**: Gemini Computer Use Agent
- **Why**: Browser automation capabilities

**Performance Requirements**:
- Submit and retrieve reports
- Handle Turnitin timeouts gracefully
- Iterative refinement within thresholds

---

## Data Models

### Core Models

All dataclasses use Pydantic-style validation with type hints:

```python
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum

# Enums
class DocumentType(str, Enum):
    LITERATURE_REVIEW = "literature_review"
    THESIS = "thesis"
    RESEARCH_PROPOSAL = "research_proposal"
    ESSAY = "essay"

class AcademicLevel(str, Enum):
    PHD = "phd"
    MASTERS = "masters"
    UNDERGRADUATE = "undergraduate"
    HIGH_SCHOOL = "high_school"

class QueryType(str, Enum):
    BROAD = "broad"
    SPECIFIC = "specific"
    COMPARATIVE = "comparative"
    RECENT = "recent"
    METHODOLOGICAL = "methodological"
    CHALLENGE = "challenge"

class TaskPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class SourceType(str, Enum):
    ACADEMIC_PAPER = "academic_paper"
    PREPRINT = "preprint"
    WEB_ARTICLE = "web_article"
    BOOK = "book"
    DOCUMENTATION = "documentation"

# See component specifications for full dataclass definitions
```

### Model Hierarchy

```
IntentAnalysis
    └─> ResearchPlan
            ├─> List[SearchQuery]
            └─> Task (hierarchical)

ResearchPlan + SearchResults
    └─> List[SearchResult]
            └─> List[VerificationResult]

VerificationResult + ResearchPlan + IntentAnalysis
    └─> Document
            ├─> List[Section]
            └─> List[Citation]

Document + IntentAnalysis + VerificationResult
    └─> EvaluationResult

Document (if evaluation fails)
    └─> TurnitinResult
```

---

## Workflows

### Sequential Pipeline

```python
from agent_framework import WorkflowBuilder
from agent_framework._workflows import FileCheckpointStorage

class ProwziOrchestrator:
    def __init__(self, config: ProwziConfig = None):
        self.config = config or get_config()
        self.agents = self._initialize_agents()

    def _initialize_agents(self):
        return {
            "intent": IntentAgent(self.config),
            "planning": PlanningAgent(self.config),
            "search": SearchAgent(self.config),
            "verification": VerificationAgent(self.config),
            "writing": WritingAgent(self.config),
            "evaluation": EvaluationAgent(self.config),
            "turnitin": TurnitinAgent(self.config),
        }

    async def run_research(
        self,
        prompt: str,
        document_paths: Optional[List[str]] = None,
        checkpoint_id: Optional[str] = None,
        skip_turnitin: bool = True
    ):
        """
        Execute full research workflow with checkpointing.

        Yields:
            WorkflowEvent - Stream of events during execution
        """

        # Build workflow
        builder = WorkflowBuilder()

        # Sequential stages
        builder.add_edge(self.agents["intent"], self.agents["planning"])
        builder.add_edge(self.agents["planning"], self.agents["search"])
        builder.add_edge(self.agents["search"], self.agents["verification"])
        builder.add_edge(self.agents["verification"], self.agents["writing"])
        builder.add_edge(self.agents["writing"], self.agents["evaluation"])

        # Conditional Turnitin stage
        if not skip_turnitin:
            builder.add_edge(
                self.agents["evaluation"],
                self.agents["turnitin"],
                condition=lambda ctx: not ctx.data["evaluation"].approved
            )

        # Enable checkpointing
        builder.with_checkpointing(FileCheckpointStorage("./checkpoints"))

        # Build workflow
        workflow = builder.build()

        # Prepare initial context
        initial_data = {
            "prompt": prompt,
            "document_paths": document_paths or [],
        }

        # Execute workflow (resume if checkpoint_id provided)
        if checkpoint_id:
            async for event in workflow.run_stream_from_checkpoint(checkpoint_id):
                yield event
        else:
            async for event in workflow.run_stream(initial_data):
                yield event
```

### Event Types

```python
@dataclass
class WorkflowEvent:
    type: str                # "agent_start", "agent_complete", "checkpoint"
    agent_name: str
    data: Dict[str, Any]
    timestamp: float
    cost: float              # Incremental cost
```

### Checkpointing

Checkpoints saved after each agent completes:

```
./checkpoints/
├── {session_id}/
│   ├── checkpoint_001_intent.json
│   ├── checkpoint_002_planning.json
│   ├── checkpoint_003_search.json
│   ├── checkpoint_004_verification.json
│   ├── checkpoint_005_writing.json
│   ├── checkpoint_006_evaluation.json
│   └── checkpoint_007_turnitin.json
```

Checkpoint structure:
```json
{
  "checkpoint_id": "001_intent",
  "session_id": "uuid",
  "agent_name": "intent",
  "timestamp": 1234567890.123,
  "data": {
    "intent_analysis": {...},
    "cost": 0.05
  },
  "next_agent": "planning"
}
```

---

## API Integrations

### OpenRouter Configuration

```python
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY = os.getenv("OPENAI_API_KEY")  # Uses OpenAI format

# Request headers
headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "HTTP-Referer": "https://github.com/Abelhubprog/AgentONE",
    "X-Title": "Prowzi Research Assistant",
}

# Model selection
models = {
    "intent": "anthropic/claude-4.5-sonnet",
    "planning": "openai/gpt-4o",
    "search": "google/gemini-2.0-flash-exp:free",
    "verification": "anthropic/claude-3.5-sonnet",
    "writing": "anthropic/claude-4.5-sonnet",
    "evaluation": "openai/gpt-4o",
}
```

### Search API Specifications

**1. Semantic Scholar**
```python
url = "https://api.semanticscholar.org/graph/v1/paper/search"
params = {
    "query": search_query,
    "fields": "title,url,abstract,authors,year,citationCount,venue",
    "limit": 100,
}
# No API key required, rate limit: 100 requests per 5 minutes
```

**2. arXiv**
```python
url = "http://export.arxiv.org/api/query"
params = {
    "search_query": f"all:{search_query}",
    "start": 0,
    "max_results": 100,
}
# Returns XML, no API key, no rate limit
```

**3. PubMed**
```python
# Step 1: Search for PMIDs
search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
params = {
    "db": "pubmed",
    "term": search_query,
    "retmax": 100,
    "retmode": "json",
}

# Step 2: Fetch details
fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
params = {
    "db": "pubmed",
    "id": ",".join(pmids),
    "retmode": "xml",
}
# No API key required, rate limit: 3 requests/second
```

**4. Perplexity** (Stub)
```python
url = "https://api.perplexity.ai/v1/search"
headers = {"Authorization": f"Bearer {PERPLEXITY_API_KEY}"}
data = {"query": search_query, "max_results": 50}
```

**5-8. Other APIs** - See search_tools.py for specifications

---

## Performance Requirements

### Latency Targets

| Stage | Target | Maximum | Typical |
|-------|--------|---------|---------|
| Intent Analysis | 10s | 30s | 8s |
| Planning | 15s | 60s | 12s |
| Search (11 queries) | 60s | 120s | 45s |
| Verification (200 sources) | 300s | 600s | 420s |
| Writing (8K words) | 900s | 1800s | 1200s |
| Evaluation | 60s | 120s | 45s |
| Turnitin (optional) | 3600s | 7200s | 4500s |
| **Total (no Turnitin)** | **~25min** | **~45min** | **~30min** |

### Cost Estimates

| Stage | Model | Tokens | Cost |
|-------|-------|--------|------|
| Intent | Claude 4.5 | 10K in, 2K out | $0.04 |
| Planning | GPT-4o | 5K in, 3K out | $0.02 |
| Search | Gemini Flash | 50K in, 5K out | $0.00 |
| Verification | Claude 3.5 | 200K in, 20K out | $0.72 |
| Writing | Claude 4.5 | 150K in, 10K out | $0.48 |
| Evaluation | GPT-4o | 15K in, 3K out | $0.05 |
| **Total** | | | **~$1.31** |

### Throughput

- Concurrent sessions: 10+ (depending on API limits)
- Max API rate limits respected
- Retry with exponential backoff
- Circuit breaker for failed APIs

---

## Security & Privacy

### API Key Management

```python
# Environment variables
OPENAI_API_KEY=sk-or-v1-...         # OpenRouter
SEMANTIC_SCHOLAR_API_KEY=...        # Optional
PERPLEXITY_API_KEY=...              # If using
EXA_API_KEY=...                     # If using
TAVILY_API_KEY=...                  # If using
SERPER_API_KEY=...                  # If using
YOU_API_KEY=...                     # If using
```

- Never commit API keys
- Use .env files (gitignored)
- Rotate keys regularly
- Monitor usage and costs

### Document Handling

- Documents parsed locally (not sent to external APIs)
- Only metadata sent to LLMs (titles, abstracts)
- User can exclude sensitive documents
- Generated content is user-owned

### Data Retention

- Checkpoints stored locally
- Optional cleanup after completion
- No data sent to third parties (except LLM providers)
- User controls all outputs

---

## Testing Strategy

### Unit Tests

```python
# Test each agent independently
tests/
├── test_intent_agent.py
│   ├── test_analyze_basic_prompt
│   ├── test_analyze_with_documents
│   ├── test_parse_pdf
│   └── test_parse_json_response
├── test_planning_agent.py
│   ├── test_create_plan
│   ├── test_task_hierarchy
│   └── test_query_generation
├── test_search_agent.py
│   ├── test_semantic_scholar_search
│   ├── test_arxiv_search
│   ├── test_pubmed_search
│   └── test_multi_engine_search
├── test_verification_agent.py
├── test_writing_agent.py
├── test_evaluation_agent.py
└── test_turnitin_agent.py
```

### Integration Tests

```python
# Test complete workflow
tests/integration/
├── test_full_workflow.py
│   ├── test_end_to_end_research
│   ├── test_checkpoint_resume
│   └── test_error_recovery
└── test_api_integrations.py
    ├── test_openrouter_connection
    ├── test_search_apis
    └── test_rate_limiting
```

### Mock Data

```python
# Mock external APIs
tests/mocks/
├── mock_openrouter.py
├── mock_semantic_scholar.py
├── mock_arxiv.py
└── mock_pubmed.py
```

### Coverage Target

- **Minimum**: 80% code coverage
- **Critical paths**: 100% coverage
- **Tools**: pytest, pytest-cov, pytest-asyncio

---

## Appendix

### File Structure

```
prowzi/
├── __init__.py                    # Package exports
├── config/
│   ├── __init__.py
│   └── settings.py                # ✅ Complete (500 lines)
├── agents/
│   ├── __init__.py
│   ├── intent_agent.py            # ✅ Complete (400 lines)
│   ├── planning_agent.py          # ✅ Complete (500 lines)
│   ├── search_agent.py            # 🚧 TODO (400 lines)
│   ├── verification_agent.py      # 🚧 TODO (350 lines)
│   ├── writing_agent.py           # 🚧 TODO (600 lines)
│   ├── evaluation_agent.py        # 🚧 TODO (400 lines)
│   └── turnitin_agent.py          # 🚧 TODO (500 lines)
├── tools/
│   ├── __init__.py
│   ├── parsing_tools.py           # ✅ Complete (350 lines)
│   ├── search_tools.py            # 🚧 Partial (500 lines, 3/8 APIs)
│   ├── analysis_tools.py          # 🚧 TODO (200 lines)
│   └── citation_tools.py          # 🚧 TODO (250 lines)
├── workflows/
│   ├── __init__.py
│   └── orchestrator.py            # 🚧 TODO (400 lines)
└── tests/
    ├── __init__.py
    ├── test_intent_agent.py       # 🚧 TODO
    ├── test_planning_agent.py     # 🚧 TODO
    └── ...                        # 🚧 TODO
```

### References

- MS Agent Framework: `../../README.md`
- Old Prowzi Specs: `../05-15_*.md`
- Old Implementation: `../../agentic_layer/`
- Python Docs: `../../python/README.md`

---

**Version**: 2.0
**Last Updated**: January 2025
**Status**: Foundation complete, MVP in progress
