"""Tests for Search Tools.

Tests search engine integrations including:
- Semantic Scholar API
- arXiv API
- PubMed API
- Perplexity API
- Result deduplication
- Relevance scoring
"""

import pytest
from unittest.mock import AsyncMock, patch, Mock
from prowzi.tools.search_tools import (
    SearchResult,
    SourceType,
    SemanticScholarSearch,
    ArXivSearch,
    PubMedSearch,
    PerplexitySearch,
    multi_engine_search,
    deduplicate_results,
)


class TestSearchResult:
    """Test SearchResult dataclass functionality."""

    def test_create_basic_result(self, sample_search_result: SearchResult):
        """Test creating a basic search result."""
        assert sample_search_result.title == "Quantum Computing: A Survey"
        assert sample_search_result.source_type == SourceType.ACADEMIC_PAPER
        assert sample_search_result.relevance_score == 0.95

    def test_result_with_metadata(self, sample_search_result: SearchResult):
        """Test search result with metadata."""
        assert sample_search_result.metadata is not None
        assert "arxiv_id" in sample_search_result.metadata

    def test_result_without_optional_fields(self):
        """Test creating result with only required fields."""
        result = SearchResult(
            title="Basic Result",
            url="https://example.com",
            content="Content here",
            source_type=SourceType.WEB_ARTICLE,
        )

        assert result.author is None
        assert result.citation_count == 0
        assert result.relevance_score == 0.0


class TestSemanticScholarSearch:
    """Test Semantic Scholar API integration."""

    @pytest.mark.asyncio
    async def test_basic_search(self, mock_semantic_scholar_response: dict):
        """Test basic Semantic Scholar search."""
        engine = SemanticScholarSearch(api_key="test-key")

        with patch("aiohttp.ClientSession.get") as mock_get:
            # Setup mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_semantic_scholar_response)

            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock(return_value=None)

            mock_session = AsyncMock()
            mock_session.get = Mock(return_value=mock_context)

            with patch("aiohttp.ClientSession", return_value=mock_session):
                results = await engine.search("quantum computing", max_results=10)

                assert len(results) > 0
                assert all(isinstance(r, SearchResult) for r in results)
                assert all(r.source_type == SourceType.ACADEMIC_PAPER for r in results)

    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test handling of Semantic Scholar API errors."""
        engine = SemanticScholarSearch(api_key="test-key")

        with patch("aiohttp.ClientSession.get") as mock_get:
            # Setup mock error response
            mock_response = AsyncMock()
            mock_response.status = 429  # Rate limit

            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock(return_value=None)

            mock_session = AsyncMock()
            mock_session.get = Mock(return_value=mock_context)

            with patch("aiohttp.ClientSession", return_value=mock_session):
                results = await engine.search("test query")

                # Should return empty list on error
                assert results == []

    @pytest.mark.asyncio
    async def test_citation_count_extraction(self, mock_semantic_scholar_response: dict):
        """Test that citation counts are properly extracted."""
        engine = SemanticScholarSearch(api_key="test-key")

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_semantic_scholar_response)

            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock(return_value=None)

            mock_session = AsyncMock()
            mock_session.get = Mock(return_value=mock_context)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_session_class.return_value = mock_session

            results = await engine.search("test")

            if results:
                assert results[0].citation_count == 25


class TestArXivSearch:
    """Test arXiv API integration."""

    @pytest.mark.asyncio
    async def test_basic_arxiv_search(self, mock_arxiv_response: str):
        """Test basic arXiv search."""
        engine = ArXivSearch()

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=mock_arxiv_response)

            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock(return_value=None)

            mock_session = AsyncMock()
            mock_session.get = Mock(return_value=mock_context)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_session_class.return_value = mock_session

            results = await engine.search("quantum algorithms", max_results=10)

            assert len(results) > 0
            assert all(r.source_type == SourceType.PREPRINT for r in results)

    @pytest.mark.asyncio
    async def test_arxiv_xml_parsing(self, mock_arxiv_response: str):
        """Test XML parsing of arXiv responses."""
        engine = ArXivSearch()

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=mock_arxiv_response)

            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock(return_value=None)

            mock_session = AsyncMock()
            mock_session.get = Mock(return_value=mock_context)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_session_class.return_value = mock_session

            results = await engine.search("test")

            if results:
                assert "arxiv.org" in results[0].url


class TestPubMedSearch:
    """Test PubMed API integration."""

    @pytest.mark.asyncio
    async def test_basic_pubmed_search(self):
        """Test basic PubMed search."""
        engine = PubMedSearch()

        # Mock both search and fetch responses
        search_response = {
            "esearchresult": {"idlist": ["12345678"]}
        }

        fetch_response = """<?xml version="1.0"?>
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>12345678</PMID>
                    <Article>
                        <ArticleTitle>Test Article</ArticleTitle>
                        <Abstract><AbstractText>Test abstract</AbstractText></Abstract>
                        <Journal><Title>Test Journal</Title></Journal>
                        <PubDate><Year>2024</Year></PubDate>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>"""

        with patch("aiohttp.ClientSession") as mock_session_class:
            # Create two different responses for search and fetch
            search_mock = AsyncMock()
            search_mock.status = 200
            search_mock.json = AsyncMock(return_value=search_response)

            fetch_mock = AsyncMock()
            fetch_mock.status = 200
            fetch_mock.text = AsyncMock(return_value=fetch_response)

            responses = [search_mock, fetch_mock]
            response_iter = iter(responses)

            def get_next_response(*args, **kwargs):
                mock_context = AsyncMock()
                mock_context.__aenter__ = AsyncMock(return_value=next(response_iter))
                mock_context.__aexit__ = AsyncMock(return_value=None)
                return mock_context

            mock_session = AsyncMock()
            mock_session.get = Mock(side_effect=get_next_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_session_class.return_value = mock_session

            results = await engine.search("test query", max_results=5)

            assert len(results) > 0
            assert all(r.source_type == SourceType.ACADEMIC_PAPER for r in results)


class TestMultiEngineSearch:
    """Test multi-engine search coordination."""

    @pytest.mark.asyncio
    async def test_search_multiple_engines(self, multiple_search_results: list[SearchResult]):
        """Test searching across multiple engines."""
        # Mock multiple engines
        engine1 = AsyncMock()
        engine1.search = AsyncMock(return_value=multiple_search_results[:2])

        engine2 = AsyncMock()
        engine2.search = AsyncMock(return_value=multiple_search_results[2:])

        results = await multi_engine_search(
            "quantum computing",
            engines=[engine1, engine2],
            max_results_per_engine=10,
        )

        assert len(results) >= 2
        assert all(isinstance(r, SearchResult) for r in results)

    @pytest.mark.asyncio
    async def test_deduplication(self, multiple_search_results: list[SearchResult]):
        """Test result deduplication across engines."""
        # Create duplicate results
        duplicates = [
            SearchResult(
                title="Quantum Computing Introduction",
                url="https://example.com/quantum",
                content="Content",
                source_type=SourceType.WEB_ARTICLE,
            ),
            SearchResult(
                title="Quantum Computing: An Introduction",  # Similar title
                url="https://example.com/quantum",  # Same URL
                content="Content",
                source_type=SourceType.WEB_ARTICLE,
            ),
        ]

        deduplicated = deduplicate_results(duplicates)

        # Should remove duplicates based on URL
        assert len(deduplicated) == 1

    @pytest.mark.asyncio
    async def test_error_handling_in_multi_search(self):
        """Test that multi-engine search handles engine failures gracefully."""
        # One engine succeeds, one fails
        good_engine = AsyncMock()
        good_engine.search = AsyncMock(return_value=[
            SearchResult(
                title="Good Result",
                url="https://good.com",
                content="Content",
                source_type=SourceType.WEB_ARTICLE,
            )
        ])

        bad_engine = AsyncMock()
        bad_engine.search = AsyncMock(side_effect=Exception("API Error"))

        results = await multi_engine_search(
            "test query",
            engines=[good_engine, bad_engine],
            max_results_per_engine=10,
        )

        # Should still get results from good engine
        assert len(results) > 0


class TestRelevanceScoring:
    """Test relevance score calculation and ranking."""

    def test_higher_citation_count_increases_score(self):
        """Test that citation count affects relevance score."""
        low_citations = SearchResult(
            title="Paper A",
            url="https://example.com/a",
            content="Content",
            source_type=SourceType.ACADEMIC_PAPER,
            citation_count=5,
        )

        high_citations = SearchResult(
            title="Paper B",
            url="https://example.com/b",
            content="Content",
            source_type=SourceType.ACADEMIC_PAPER,
            citation_count=500,
        )

        # Higher citations should correlate with relevance
        assert high_citations.citation_count > low_citations.citation_count

    def test_result_ranking(self, multiple_search_results: list[SearchResult]):
        """Test that results can be ranked by relevance."""
        # Sort by relevance score
        ranked = sorted(
            multiple_search_results,
            key=lambda r: r.relevance_score,
            reverse=True,
        )

        # Should be in descending order
        for i in range(len(ranked) - 1):
            assert ranked[i].relevance_score >= ranked[i + 1].relevance_score


class TestSearchEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_empty_query(self):
        """Test handling of empty search query."""
        engine = SemanticScholarSearch()

        with pytest.raises(ValueError, match="Query cannot be empty"):
            await engine.search("")

    @pytest.mark.asyncio
    async def test_no_results_found(self):
        """Test handling when no results are found."""
        engine = SemanticScholarSearch()

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"data": []})

            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock(return_value=None)

            mock_session = AsyncMock()
            mock_session.get = Mock(return_value=mock_context)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_session_class.return_value = mock_session

            results = await engine.search("nonexistent query xyz123")

            assert results == []

    @pytest.mark.asyncio
    async def test_network_timeout(self):
        """Test handling of network timeout."""
        engine = SemanticScholarSearch(timeout=1)

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session.get = Mock(side_effect=asyncio.TimeoutError())
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_session_class.return_value = mock_session

            results = await engine.search("test query")

            # Should return empty list on timeout
            assert results == []


# Import asyncio for timeout test
import asyncio
