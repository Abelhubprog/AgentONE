"""Prowzi Tools Package"""

from prowzi.tools.parsing_tools import (
    parse_document,
    parse_multiple_documents,
    extract_citations,
    chunk_text,
)

from prowzi.tools.search_tools import (
    SearchEngine,
    SearchResult,
    SourceType,
    SemanticScholarSearch,
    ArXivSearch,
    PubMedSearch,
    PerplexitySearch,
    multi_engine_search,
    deduplicate_results,
    batch_search_queries,
)

__all__ = [
    # Parsing
    "parse_document",
    "parse_multiple_documents",
    "extract_citations",
    "chunk_text",
    # Search
    "SearchEngine",
    "SearchResult",
    "SourceType",
    "SemanticScholarSearch",
    "ArXivSearch",
    "PubMedSearch",
    "PerplexitySearch",
    "multi_engine_search",
    "deduplicate_results",
    "batch_search_queries",
]
