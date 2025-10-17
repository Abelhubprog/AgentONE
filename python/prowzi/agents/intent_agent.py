"""Intent & Context Agent

Entry point for Prowzi system. Analyzes user requirements and parses documents.
Uses Claude 4.5 Sonnet (1M context) for document parsing and GPT-4o for intent analysis.

Responsibilities:
    - Parse uploaded documents (PDF, DOCX, MD, TXT)
    - Extract document requirements and context
    - Understand user intent and research goals
    - Identify document type, field, academic level
    - Detect missing information
    - Initialize ACE context for workflow
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient

from prowzi.config import get_config
from prowzi.config.logging_config import get_logger
from prowzi.tools.parsing_tools import parse_multiple_documents

logger = get_logger(__name__)


@dataclass
class IntentAnalysis:
    """Structured output from Intent Agent.

    Attributes:
        document_type: Type of document (e.g., "literature_review", "research_paper")
        field: Academic field (e.g., "healthcare_ai_clinical_decision_support")
        academic_level: Level (e.g., "phd", "masters", "undergraduate")
        word_count: Target word count
        explicit_requirements: List of explicitly stated requirements
        implicit_requirements: List of inferred requirements
        missing_info: List of missing information that needs clarification
        confidence_score: Confidence in intent understanding (0.0-1.0)
        requires_user_input: Whether clarification is needed
        citation_style: Citation style (e.g., "APA", "MLA", "IEEE")
        region: Geographic region if specified
        timeframe: Time period for sources
        parsed_documents: List of parsed document summaries
        metadata: Additional extracted metadata
    """
    document_type: str
    field: str
    academic_level: str
    word_count: int
    explicit_requirements: List[str]
    implicit_requirements: List[str]
    missing_info: List[str]
    confidence_score: float
    requires_user_input: bool
    citation_style: Optional[str] = None
    region: Optional[str] = None
    timeframe: Optional[str] = None
    parsed_documents: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.parsed_documents is None:
            self.parsed_documents = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "document_type": self.document_type,
            "field": self.field,
            "academic_level": self.academic_level,
            "word_count": self.word_count,
            "explicit_requirements": self.explicit_requirements,
            "implicit_requirements": self.implicit_requirements,
            "missing_info": self.missing_info,
            "confidence_score": self.confidence_score,
            "requires_user_input": self.requires_user_input,
            "citation_style": self.citation_style,
            "region": self.region,
            "timeframe": self.timeframe,
            "parsed_documents": self.parsed_documents,
            "metadata": self.metadata,
        }


class IntentAgent:
    """Intent & Context Agent implementation.

    This agent serves as the entry point for the Prowzi workflow.
    It analyzes user intent and parses documents to understand requirements.

    Usage:
        >>> agent = IntentAgent()
        >>> analysis = await agent.analyze(
        ...     prompt="Write 10000-word PhD literature review on AI in healthcare",
        ...     document_paths=["paper1.pdf", "paper2.pdf"]
        ... )
        >>> print(analysis.document_type)
        'literature_review'
    """

    def __init__(self, config=None):
        """Initialize Intent Agent.

        Args:
            config: Optional ProwziConfig instance. Uses default if not provided.
        """
        self.config = config or get_config()

        # Get agent configuration
        agent_config = self.config.agents["intent"]
        model_config = self.config.get_model_for_agent("intent")

        # Create OpenAI chat client for OpenRouter
        self.chat_client = OpenAIChatClient(
            api_key=self.config.openrouter_api_key,
            base_url=self.config.openrouter_base_url,
            model_id=model_config.name,
        )

        # System prompts
        self.parsing_prompt = self._create_parsing_prompt()
        self.intent_prompt = self._create_intent_prompt()

        # Create agents
        self.parsing_agent = ChatAgent(
            chat_client=self.chat_client,
            instructions=self.parsing_prompt,
        )

        self.intent_agent = ChatAgent(
            chat_client=self.chat_client,
            instructions=self.intent_prompt,
        )

    def _create_parsing_prompt(self) -> str:
        """Create system prompt for document parsing"""
        return """You are an expert document parser specialized in academic content analysis.

Your role is to:
1. Extract key information from academic documents
2. Identify document structure, topics, and key points
3. Recognize academic level, style, and citation patterns
4. Extract methodology, findings, and conclusions
5. Identify the field and subfield of research

When analyzing documents:
- Focus on extracting factual information
- Identify the document's purpose and contribution
- Note the writing style and academic level
- Extract any explicit requirements or guidelines
- Identify citation style and referencing patterns

Provide structured summaries that capture:
- Main topics and themes
- Key findings and arguments
- Methodology used
- Academic level indicators
- Citation and reference style
- Any explicit requirements or constraints

Be precise and comprehensive in your analysis."""

    def _create_intent_prompt(self) -> str:
        """Create system prompt for intent analysis"""
        return """You are an expert research intent analyzer.

Your role is to understand user requirements for academic document creation by:
1. Identifying the document type (literature review, research paper, thesis, etc.)
2. Determining the academic field and subfield
3. Recognizing the academic level (PhD, Masters, Undergraduate)
4. Extracting explicit and implicit requirements
5. Identifying missing information that needs clarification
6. Understanding scope, depth, and quality expectations

You must extract:
- Document type and purpose
- Academic field (be specific, e.g., "healthcare_ai_clinical_decision_support")
- Academic level
- Target word count
- Explicit requirements (stated by user)
- Implicit requirements (inferred from context)
- Missing information (region, citation style, timeframe, etc.)
- Confidence in your understanding (0.0-1.0)

Always provide structured JSON output following this schema:
{
  "document_type": "string",
  "field": "string",
  "academic_level": "string",
  "word_count": integer,
  "explicit_requirements": ["string"],
  "implicit_requirements": ["string"],
  "missing_info": ["string"],
  "confidence_score": float,
  "requires_user_input": boolean,
  "citation_style": "string or null",
  "region": "string or null",
  "timeframe": "string or null"
}

Be thorough in inferring requirements. Academic writing has many implicit standards."""

    async def analyze(
        self,
        prompt: str,
        document_paths: Optional[List[str | Path]] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> IntentAnalysis:
        """Analyze user intent and parse documents.

        Args:
            prompt: User's research prompt/request
            document_paths: Optional list of paths to documents to parse
            additional_context: Optional additional context dictionary

        Returns:
            IntentAnalysis object with structured understanding

        Example:
            >>> agent = IntentAgent()
            >>> result = await agent.analyze(
            ...     prompt="Write 10000-word PhD literature review on AI in clinical decision support",
            ...     document_paths=["research_paper.pdf", "guidelines.docx"]
            ... )
            >>> print(f"Document type: {result.document_type}")
            >>> print(f"Confidence: {result.confidence_score}")
        """
        logger.info("🔍 Intent Agent: Starting analysis...")

        # Step 1: Parse documents if provided
        parsed_documents = []
        document_summaries = []

        if document_paths:
            logger.info(f"📄 Parsing {len(document_paths)} documents...")
            parsed_documents = parse_multiple_documents(document_paths, extract_metadata=True)

            # Generate summaries using parsing agent
            for i, doc_result in enumerate(parsed_documents, 1):
                if "error" in doc_result:
                    logger.warning(f"  ⚠️  Error parsing document {i}: {doc_result['error']}")
                    continue

                logger.debug(f"  ✓ Parsed: {doc_result['file_name']} ({doc_result['word_count']} words)")

                # Create summary using parsing agent
                summary_prompt = f"""Analyze this document and provide a concise summary:

File: {doc_result['file_name']}
Type: {doc_result['file_type']}
Word Count: {doc_result['word_count']}

Content (first 5000 characters):
{doc_result['content'][:5000]}

Provide a structured summary including:
1. Main topic and purpose
2. Key points and findings
3. Academic level indicators
4. Writing style and tone
5. Any explicit requirements or guidelines mentioned
6. Citation style (if apparent)

Keep your summary concise but comprehensive."""

                summary_response = await self.parsing_agent.run(summary_prompt)

                document_summaries.append({
                    "file_name": doc_result["file_name"],
                    "word_count": doc_result["word_count"],
                    "summary": summary_response.response,
                    "metadata": doc_result.get("metadata", {})
                })

        # Step 2: Analyze intent
        logger.info("🎯 Analyzing user intent...")

        # Build context for intent analysis
        context_parts = [
            f"USER PROMPT: {prompt}",
        ]

        if document_summaries:
            context_parts.append("\nPARSED DOCUMENTS:")
            for i, doc_summary in enumerate(document_summaries, 1):
                context_parts.append(f"\nDocument {i}: {doc_summary['file_name']}")
                context_parts.append(f"Summary: {doc_summary['summary']}")

        if additional_context:
            context_parts.append(f"\nADDITIONAL CONTEXT: {json.dumps(additional_context, indent=2)}")

        intent_prompt_text = "\n".join(context_parts)
        intent_prompt_text += "\n\nAnalyze the above and provide your structured JSON analysis."

        # Get intent analysis
        intent_response = await self.intent_agent.run(intent_prompt_text)

        # Parse JSON response
        try:
            # Extract JSON from response
            response_text = intent_response.response

            # Find JSON object in response
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1

            if start_idx != -1 and end_idx > start_idx:
                json_text = response_text[start_idx:end_idx]
                intent_data = json.loads(json_text)
            else:
                raise ValueError("No JSON object found in response")

            # Create IntentAnalysis object
            analysis = IntentAnalysis(
                document_type=intent_data.get("document_type", "unknown"),
                field=intent_data.get("field", "general"),
                academic_level=intent_data.get("academic_level", "undergraduate"),
                word_count=intent_data.get("word_count", 1000),
                explicit_requirements=intent_data.get("explicit_requirements", []),
                implicit_requirements=intent_data.get("implicit_requirements", []),
                missing_info=intent_data.get("missing_info", []),
                confidence_score=intent_data.get("confidence_score", 0.5),
                requires_user_input=intent_data.get("requires_user_input", False),
                citation_style=intent_data.get("citation_style"),
                region=intent_data.get("region"),
                timeframe=intent_data.get("timeframe"),
                parsed_documents=document_summaries,
                metadata={
                    "original_prompt": prompt,
                    "document_count": len(document_summaries),
                    "total_parsed_words": sum(d["word_count"] for d in document_summaries),
                }
            )

            logger.info("✅ Intent analysis complete!")
            logger.info(f"   Document type: {analysis.document_type}")
            logger.info(f"   Field: {analysis.field}")
            logger.info(f"   Level: {analysis.academic_level}")
            logger.info(f"   Target: {analysis.word_count} words")
            logger.info(f"   Confidence: {analysis.confidence_score:.2f}")

            if analysis.missing_info:
                logger.warning(f"   ⚠️  Missing info: {', '.join(analysis.missing_info)}")

            return analysis

        except Exception as e:
            logger.error(f"❌ Error parsing intent analysis: {e}")
            logger.debug(f"Raw response: {intent_response.response}")

            # Return default analysis
            return IntentAnalysis(
                document_type="unknown",
                field="general",
                academic_level="undergraduate",
                word_count=1000,
                explicit_requirements=[prompt],
                implicit_requirements=[],
                missing_info=["document_type", "field", "academic_level"],
                confidence_score=0.3,
                requires_user_input=True,
                parsed_documents=document_summaries,
                metadata={"error": str(e)}
            )

    async def clarify(
        self,
        analysis: IntentAnalysis,
        user_responses: Dict[str, Any]
    ) -> IntentAnalysis:
        """Update analysis with user clarifications.

        Args:
            analysis: Original IntentAnalysis
            user_responses: Dictionary of user responses to missing_info

        Returns:
            Updated IntentAnalysis
        """
        logger.info("🔄 Updating intent analysis with clarifications...")

        # Update fields from user responses
        if "citation_style" in user_responses:
            analysis.citation_style = user_responses["citation_style"]

        if "region" in user_responses:
            analysis.region = user_responses["region"]

        if "timeframe" in user_responses:
            analysis.timeframe = user_responses["timeframe"]

        # Remove clarified items from missing_info
        analysis.missing_info = [
            item for item in analysis.missing_info
            if item not in user_responses
        ]

        # Update requires_user_input flag
        analysis.requires_user_input = len(analysis.missing_info) > 0

        # Increase confidence score
        analysis.confidence_score = min(1.0, analysis.confidence_score + 0.2)

        logger.info("✅ Intent analysis updated!")

        return analysis
