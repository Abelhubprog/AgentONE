"""Minimal working tests for Intent Agent - Initial coverage baseline."""

import pytest
from prowzi.agents.intent_agent import IntentAnalysis


class TestIntentAnalysisDataclass:
    """Test IntentAnalysis dataclass functionality."""

    def test_create_complete_analysis(self):
        """Test creating a complete IntentAnalysis object."""
        analysis = IntentAnalysis(
            document_type="research_paper",
            field="Computer Science",
            academic_level="undergraduate",
            word_count=3000,
            explicit_requirements=["Intro", "Methods", "Results"],
            implicit_requirements=["Technical depth"],
            missing_info=[],
            confidence_score=0.95,
            requires_user_input=False,
            citation_style="APA",
        )

        assert analysis.document_type == "research_paper"
        assert analysis.confidence_score == 0.95
        assert len(analysis.explicit_requirements) == 3
        assert analysis.requires_user_input is False

    def test_to_dict_method(self):
        """Test converting IntentAnalysis to dictionary."""
        analysis = IntentAnalysis(
            document_type="essay",
            field="History",
            academic_level="high_school",
            word_count=1500,
            explicit_requirements=["Discuss topic"],
            implicit_requirements=[],
            missing_info=["citation_style"],
            confidence_score=0.70,
            requires_user_input=True,
        )

        result_dict = analysis.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["document_type"] == "essay"
        assert result_dict["word_count"] == 1500
        assert result_dict["confidence_score"] == 0.70

    def test_default_values(self):
        """Test that default values are properly initialized."""
        analysis = IntentAnalysis(
            document_type="report",
            field="Business",
            academic_level="masters",
            word_count=5000,
            explicit_requirements=["Analysis"],
            implicit_requirements=[],
            missing_info=[],
            confidence_score=0.85,
            requires_user_input=False,
        )

        # Check defaults from __post_init__
        assert analysis.parsed_documents == []
        assert analysis.metadata == {}
        assert analysis.citation_style is None
        assert analysis.region is None
        assert analysis.timeframe is None
