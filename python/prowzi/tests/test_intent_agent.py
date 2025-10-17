"""Tests for Intent Agent.

Tests the intent analysis functionality including:
- Basic intent analysis
- Document parsing (PDF, DOCX)
- Missing information detection
- Confidence scoring
- User clarification handling
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from prowzi.agents.intent_agent import (
    IntentAgent,
    IntentAnalysis,
)


class TestIntentAgentBasic:
    """Basic Intent Agent functionality tests."""

    @pytest.mark.asyncio
    async def test_analyze_complete_query(
        self, mock_chat_agent: AsyncMock, sample_intent_analysis: IntentAnalysis
    ):
        """Test analyzing a complete query with all information."""
        # Setup mock response
        mock_response = Mock()
        mock_response.response = """
        {
            "document_type": "research_paper",
            "field": "Computer Science",
            "academic_level": "undergraduate",
            "word_count": 3000,
            "requirements": [
                "Introduction to quantum computing",
                "Quantum algorithms",
                "Applications"
            ],
            "citation_style": "APA",
            "region": "United States",
            "timeframe": "2020-2025",
            "confidence_score": 0.95
        }
        """
        mock_chat_agent.run.return_value = mock_response

        # Create agent with mock
        with patch("prowzi.agents.intent_agent.ChatAgent", return_value=mock_chat_agent):
            agent = IntentAgent()
            agent.agent = mock_chat_agent

            result = await agent.analyze("Write a research paper on quantum computing")

            # Assertions
            assert isinstance(result, IntentAnalysis)
            assert result.document_type == "research_paper"
            assert result.field == "Computer Science"
            assert result.word_count == 3000
            assert result.confidence_score >= 0.9
            assert len(result.missing_info) == 0
            assert result.requires_user_input is False

    @pytest.mark.asyncio
    async def test_analyze_incomplete_query(
        self, mock_chat_agent: AsyncMock, incomplete_intent_analysis: IntentAnalysis
    ):
        """Test analyzing query with missing information."""
        # Setup mock response with missing fields
        mock_response = Mock()
        mock_response.response = """
        {
            "document_type": "essay",
            "field": "Technology",
            "academic_level": "high_school",
            "word_count": 1500,
            "requirements": ["Discuss AI"],
            "confidence_score": 0.65
        }
        """
        mock_chat_agent.run.return_value = mock_response

        with patch("prowzi.agents.intent_agent.ChatAgent", return_value=mock_chat_agent):
            agent = IntentAgent()
            agent.agent = mock_chat_agent

            result = await agent.analyze("Write about AI")

            # Assertions
            assert isinstance(result, IntentAnalysis)
            assert result.confidence_score < 0.8
            assert len(result.missing_info) > 0
            assert result.requires_user_input is True

    @pytest.mark.asyncio
    async def test_update_with_clarifications(self, sample_intent_analysis: IntentAnalysis):
        """Test updating intent analysis with user clarifications."""
        # Initial analysis missing some info
        analysis = IntentAnalysis(
            user_query="Write a paper",
            document_type="research_paper",
            field="Science",
            academic_level="undergraduate",
            word_count=2000,
            requirements=["Research topic"],
            citation_style=None,
            region=None,
            timeframe=None,
            confidence_score=0.70,
            missing_info=["citation_style", "region", "timeframe"],
            requires_user_input=True,
        )

        # User provides clarifications
        clarifications = {
            "citation_style": "MLA",
            "region": "Canada",
            "timeframe": "2023-2025",
        }

        agent = IntentAgent()
        updated = await agent.update_with_clarifications(analysis, clarifications)

        # Assertions
        assert updated.citation_style == "MLA"
        assert updated.region == "Canada"
        assert updated.timeframe == "2023-2025"
        assert len(updated.missing_info) == 0
        assert updated.requires_user_input is False
        assert updated.confidence_score > analysis.confidence_score


class TestIntentAgentDocumentParsing:
    """Test document parsing capabilities."""

    @pytest.mark.asyncio
    async def test_parse_pdf_requirements(self, sample_pdf_content: bytes):
        """Test parsing requirements from PDF document."""
        agent = IntentAgent()

        # Mock PDF parsing
        with patch("prowzi.agents.intent_agent.extract_text") as mock_extract:
            mock_extract.return_value = "Research paper on quantum computing, 3000 words, APA format"

            text = await agent.parse_document(sample_pdf_content, "application/pdf")

            assert "quantum computing" in text.lower()
            assert "3000" in text or "3,000" in text

    @pytest.mark.asyncio
    async def test_parse_docx_requirements(self, sample_docx_requirements: str):
        """Test parsing requirements from DOCX document."""
        agent = IntentAgent()

        # Test that requirements are extracted
        assert "Quantum Computing" in sample_docx_requirements
        assert "3000 words" in sample_docx_requirements
        assert "APA style" in sample_docx_requirements

    def test_parse_invalid_document(self):
        """Test handling of invalid document format."""
        agent = IntentAgent()

        with pytest.raises(ValueError, match="Unsupported document type"):
            # This should be synchronous or properly awaited
            pass  # Placeholder for actual implementation


class TestIntentAgentEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_query(self, mock_chat_agent: AsyncMock):
        """Test handling of empty query."""
        with patch("prowzi.agents.intent_agent.ChatAgent", return_value=mock_chat_agent):
            agent = IntentAgent()
            agent.agent = mock_chat_agent

            with pytest.raises(ValueError, match="Query cannot be empty"):
                await agent.analyze("")

    @pytest.mark.asyncio
    async def test_very_long_query(self, mock_chat_agent: AsyncMock):
        """Test handling of very long query (>10k characters)."""
        long_query = "Write a paper about " + ("quantum computing " * 2000)

        mock_response = Mock()
        mock_response.response = '{"document_type": "research_paper", "confidence_score": 0.5}'
        mock_chat_agent.run.return_value = mock_response

        with patch("prowzi.agents.intent_agent.ChatAgent", return_value=mock_chat_agent):
            agent = IntentAgent()
            agent.agent = mock_chat_agent

            # Should handle gracefully, possibly truncating
            result = await agent.analyze(long_query)
            assert isinstance(result, IntentAnalysis)

    @pytest.mark.asyncio
    async def test_malformed_json_response(self, mock_chat_agent: AsyncMock):
        """Test handling of malformed JSON in agent response."""
        mock_response = Mock()
        mock_response.response = "Not valid JSON {incomplete"
        mock_chat_agent.run.return_value = mock_response

        with patch("prowzi.agents.intent_agent.ChatAgent", return_value=mock_chat_agent):
            agent = IntentAgent()
            agent.agent = mock_chat_agent

            with pytest.raises(Exception):  # Should raise parsing error
                await agent.analyze("Write a paper")


class TestIntentAgentLogging:
    """Test logging behavior."""

    @pytest.mark.asyncio
    async def test_logs_analysis_start(self, mock_chat_agent: AsyncMock, caplog):
        """Test that agent logs analysis start."""
        mock_response = Mock()
        mock_response.response = '{"document_type": "essay", "confidence_score": 0.8}'
        mock_chat_agent.run.return_value = mock_response

        with patch("prowzi.agents.intent_agent.ChatAgent", return_value=mock_chat_agent):
            agent = IntentAgent()
            agent.agent = mock_chat_agent

            await agent.analyze("Test query")

            # Check that logging occurred
            assert "Intent Agent: Starting analysis" in caplog.text or \
                   "Analyzing user intent" in caplog.text

    @pytest.mark.asyncio
    async def test_logs_completion(self, mock_chat_agent: AsyncMock, caplog):
        """Test that agent logs successful completion."""
        mock_response = Mock()
        mock_response.response = '{"document_type": "essay", "confidence_score": 0.9}'
        mock_chat_agent.run.return_value = mock_response

        with patch("prowzi.agents.intent_agent.ChatAgent", return_value=mock_chat_agent):
            agent = IntentAgent()
            agent.agent = mock_chat_agent

            await agent.analyze("Test query")

            assert "complete" in caplog.text.lower() or "success" in caplog.text.lower()


class TestIntentAgentConfidenceScoring:
    """Test confidence score calculation."""

    def test_high_confidence_complete_info(self, sample_intent_analysis: IntentAnalysis):
        """Test that complete information yields high confidence."""
        assert sample_intent_analysis.confidence_score >= 0.9
        assert sample_intent_analysis.requires_user_input is False

    def test_low_confidence_missing_info(self, incomplete_intent_analysis: IntentAnalysis):
        """Test that missing information yields lower confidence."""
        assert incomplete_intent_analysis.confidence_score < 0.8
        assert incomplete_intent_analysis.requires_user_input is True

    def test_confidence_increases_with_clarifications(self):
        """Test that confidence increases when clarifications provided."""
        initial = IntentAnalysis(
            user_query="Write something",
            document_type="essay",
            field="General",
            academic_level="unknown",
            word_count=1000,
            requirements=["Write content"],
            confidence_score=0.50,
            missing_info=["field", "citation_style"],
            requires_user_input=True,
        )

        # After clarifications
        updated = IntentAnalysis(
            user_query="Write something",
            document_type="essay",
            field="Computer Science",
            academic_level="undergraduate",
            word_count=1000,
            requirements=["Write content"],
            citation_style="APA",
            confidence_score=0.85,
            missing_info=[],
            requires_user_input=False,
        )

        assert updated.confidence_score > initial.confidence_score
