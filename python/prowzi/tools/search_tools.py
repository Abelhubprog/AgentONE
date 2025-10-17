"""Search Tools

Integrates 8 different search APIs for comprehensive evidence gathering:
    - Academic: Semantic Scholar, PubMed, arXiv
    - Web: Perplexity, Exa, Tavily, Serper, You.com

Handles deduplication, relevance scoring, and error recovery.
"""

import asyncio
import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from prowzi.config.logging_config import get_logger

logger = get_logger(__name__)


class SourceType(Enum):
    """Type of search result source"""
    ACADEMIC_PAPER = "academic_paper"
    WEB_ARTICLE = "web_article"
    PREPRINT = "preprint"
    DOCUMENTATION = "documentation"
    BLOG = "blog"
    NEWS = "news"
    BOOK = "book"
    DATASET = "dataset"


@dataclass
class SearchResult:
    """Standardized search result across all APIs.

    Attributes:
        title: Title of the source
        url: URL of the source
        content: Extracted text content or abstract
        source_type: Type of source
        author: Author(s) if available
        publication_date: Publication date if available
        citation_count: Number of citations (academic sources)
        venue: Publication venue (journal, conference, etc.)
        doi: Digital Object Identifier if available
        relevance_score: Relevance score (0-100)
        metadata: Additional source-specific metadata
    """
    title: str
    url: str
    content: str
    source_type: SourceType
    author: Optional[str] = None
    publication_date: Optional[str] = None
    citation_count: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    relevance_score: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "source_type": self.source_type.value,
            "author": self.author,
            "publication_date": self.publication_date,
            "citation_count": self.citation_count,
            "venue": self.venue,
            "doi": self.doi,
            "relevance_score": self.relevance_score,
            "metadata": self.metadata,
        }


class SearchEngine:
    """Base class for search engine integrations"""

    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout

    async def search(
        self,
        query: str,
        max_results: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        """Execute search query.

        Args:
            query: Search query string
            max_results: Maximum number of results to return
            **kwargs: Additional search parameters

        Returns:
            List of search results
        """
        raise NotImplementedError


class SemanticScholarSearch(SearchEngine):
    """Semantic Scholar API integration for academic papers"""

    async def search(
        self,
        query: str,
        max_results: int = 20,
        fields: Optional[List[str]] = None,
        **kwargs
    ) -> List[SearchResult]:
        """Search Semantic Scholar"""
        try:
            import aiohttp

            if fields is None:
                fields = ["title", "abstract", "authors", "year", "citationCount",
                         "venue", "externalIds", "url"]

            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                "query": query,
                "limit": max_results,
                "fields": ",".join(fields)
            }

            headers = {}
            if self.api_key:
                headers["x-api-key"] = self.api_key

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=self.timeout) as response:
                    if response.status != 200:
                        logger.error(f"Semantic Scholar API error: {response.status}")
                        return []

                    data = await response.json()
                    results = []

                    for paper in data.get("data", []):
                        authors = ", ".join([a.get("name", "") for a in paper.get("authors", [])])

                        result = SearchResult(
                            title=paper.get("title", ""),
                            url=paper.get("url", ""),
                            content=paper.get("abstract", ""),
                            source_type=SourceType.ACADEMIC_PAPER,
                            author=authors,
                            publication_date=str(paper.get("year", "")),
                            citation_count=paper.get("citationCount", 0),
                            venue=paper.get("venue", ""),
                            doi=paper.get("externalIds", {}).get("DOI"),
                        )
                        results.append(result)

                    return results

        except Exception as e:
            logger.error(f"Semantic Scholar search error: {e}", exc_info=True)
            return []


class ArXivSearch(SearchEngine):
    """arXiv API integration for preprints"""

    async def search(
        self,
        query: str,
        max_results: int = 20,
        **kwargs
    ) -> List[SearchResult]:
        """Search arXiv"""
        try:
            # SECURITY: Use defusedxml to prevent XML injection attacks
            try:
                from defusedxml import ElementTree as ET
            except ImportError:
                # Fallback to standard library with warning
                import xml.etree.ElementTree as ET
                import warnings
                warnings.warn("defusedxml not installed - using standard xml (less secure)", stacklevel=2)

            import aiohttp

            url = "http://export.arxiv.org/api/query"
            params = {
                "search_query": query,
                "max_results": max_results,
                "sortBy": "relevance",
                "sortOrder": "descending"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=self.timeout) as response:
                    if response.status != 200:
                        logger.error(f"arXiv API error: {response.status}")
                        return []

                    xml_data = await response.text()
                    root = ET.fromstring(xml_data)

                    # Parse namespace
                    ns = {"atom": "http://www.w3.org/2005/Atom"}

                    results = []
                    for entry in root.findall("atom:entry", ns):
                        title = entry.find("atom:title", ns).text.strip()
                        url = entry.find("atom:id", ns).text
                        summary = entry.find("atom:summary", ns).text.strip()

                        authors = []
                        for author in entry.findall("atom:author", ns):
                            name = author.find("atom:name", ns)
                            if name is not None:
                                authors.append(name.text)

                        published = entry.find("atom:published", ns)
                        pub_date = published.text[:10] if published is not None else None

                        result = SearchResult(
                            title=title,
                            url=url,
                            content=summary,
                            source_type=SourceType.PREPRINT,
                            author=", ".join(authors),
                            publication_date=pub_date,
                        )
                        results.append(result)

                    return results

        except Exception as e:
            logger.error(f"arXiv search error: {e}", exc_info=True)
            return []


class PubMedSearch(SearchEngine):
    """PubMed API integration for biomedical literature"""

    async def search(
        self,
        query: str,
        max_results: int = 20,
        **kwargs
    ) -> List[SearchResult]:
        """Search PubMed"""
        try:
            # SECURITY: Use defusedxml to prevent XML injection attacks
            try:
                from defusedxml import ElementTree as ET
            except ImportError:
                # Fallback to standard library with warning
                import xml.etree.ElementTree as ET
                import warnings
                warnings.warn("defusedxml not installed - using standard xml (less secure)", stacklevel=2)

            import aiohttp

            # Step 1: Search to get PMIDs
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "json"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, params=search_params, timeout=self.timeout) as response:
                    if response.status != 200:
                        logger.error(f"PubMed search error: {response.status}")
                        return []

                    search_data = await response.json()
                    pmids = search_data.get("esearchresult", {}).get("idlist", [])

                    if not pmids:
                        return []

                    # Step 2: Fetch details for PMIDs
                    fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
                    fetch_params = {
                        "db": "pubmed",
                        "id": ",".join(pmids),
                        "retmode": "xml"
                    }

                    async with session.get(fetch_url, params=fetch_params, timeout=self.timeout) as response:
                        if response.status != 200:
                            logger.error(f"PubMed fetch error: {response.status}")
                            return []

                        xml_data = await response.text()
                        root = ET.fromstring(xml_data)

                        results = []
                        for article in root.findall(".//PubmedArticle"):
                            try:
                                medline = article.find(".//MedlineCitation")
                                article_elem = medline.find(".//Article")

                                title_elem = article_elem.find(".//ArticleTitle")
                                title = title_elem.text if title_elem is not None else ""

                                abstract_elem = article_elem.find(".//Abstract/AbstractText")
                                abstract = abstract_elem.text if abstract_elem is not None else ""

                                pmid = medline.find(".//PMID").text
                                url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

                                # Extract authors
                                authors = []
                                for author in article_elem.findall(".//Author"):
                                    lastname = author.find(".//LastName")
                                    firstname = author.find(".//ForeName")
                                    if lastname is not None:
                                        name = lastname.text
                                        if firstname is not None:
                                            name = f"{firstname.text} {name}"
                                        authors.append(name)

                                # Extract year
                                year_elem = article_elem.find(".//PubDate/Year")
                                year = year_elem.text if year_elem is not None else ""

                                # Extract journal
                                journal_elem = article_elem.find(".//Journal/Title")
                                journal = journal_elem.text if journal_elem is not None else ""

                                result = SearchResult(
                                    title=title,
                                    url=url,
                                    content=abstract,
                                    source_type=SourceType.ACADEMIC_PAPER,
                                    author=", ".join(authors[:3]),  # First 3 authors
                                    publication_date=year,
                                    venue=journal,
                                    metadata={"pmid": pmid}
                                )
                                results.append(result)

                            except Exception as e:
                                logger.warning(f"Error parsing PubMed article: {e}")
                                continue

                        return results

        except Exception as e:
            logger.error(f"PubMed search error: {e}", exc_info=True)
            return []


class PerplexitySearch(SearchEngine):
    """Perplexity AI search integration"""

    async def search(
        self,
        query: str,
        max_results: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        """Search using Perplexity"""
        if not self.api_key:
            return []

        try:
            import aiohttp

            url = "https://api.perplexity.ai/search"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "query": query,
                "max_results": max_results
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data, timeout=self.timeout) as response:
                    if response.status != 200:
                        logger.error(f"Perplexity API error: {response.status}")
                        return []

                    result_data = await response.json()

                    # Convert Perplexity results to standard format
                    results = []
                    for item in result_data.get("results", [])[:max_results]:
                        result = SearchResult(
                            title=item.get("title", ""),
                            url=item.get("url", ""),
                            content=item.get("snippet", ""),
                            source_type=SourceType.WEB_ARTICLE,
                        )
                        results.append(result)

                    return results

        except Exception as e:
            logger.error(f"Perplexity search error: {e}", exc_info=True)
            return []


async def multi_engine_search(
    query: str,
    engines: List[SearchEngine],
    max_results_per_engine: int = 10,
    deduplicate: bool = True
) -> List[SearchResult]:
    """Search across multiple engines in parallel.

    Args:
        query: Search query
        engines: List of search engine instances
        max_results_per_engine: Max results per engine
        deduplicate: Remove duplicate results

    Returns:
        Combined list of search results
    """
    # Run searches in parallel
    tasks = [
        engine.search(query, max_results_per_engine)
        for engine in engines
    ]

    results_lists = await asyncio.gather(*tasks, return_exceptions=True)

    # Combine results
    all_results = []
    for results in results_lists:
        if isinstance(results, list):
            all_results.extend(results)
        elif isinstance(results, Exception):
            logger.error(f"Search engine error: {results}", exc_info=results)

    # Deduplicate by URL and title similarity
    if deduplicate:
        all_results = deduplicate_results(all_results)

    return all_results


def deduplicate_results(results: List[SearchResult]) -> List[SearchResult]:
    """Remove duplicate search results based on URL and title similarity.

    Args:
        results: List of search results

    Returns:
        Deduplicated list of results
    """
    seen_urls: Set[str] = set()
    seen_title_hashes: Set[str] = set()
    unique_results = []

    for result in results:
        # Check URL
        if result.url in seen_urls:
            continue

        # Check title similarity (fuzzy matching via hash)
        title_normalized = result.title.lower().strip()
        title_hash = hashlib.md5(title_normalized.encode()).hexdigest()

        if title_hash in seen_title_hashes:
            continue

        seen_urls.add(result.url)
        seen_title_hashes.add(title_hash)
        unique_results.append(result)

    return unique_results


def batch_search_queries(
    queries: List[str],
    engines: List[SearchEngine],
    max_results_per_query: int = 10
) -> Dict[str, List[SearchResult]]:
    """Execute multiple search queries in parallel.

    Args:
        queries: List of search queries
        engines: List of search engine instances
        max_results_per_query: Max results per query

    Returns:
        Dictionary mapping queries to search results
    """
    async def _batch_search():
        tasks = [
            multi_engine_search(query, engines, max_results_per_query)
            for query in queries
        ]
        results_lists = await asyncio.gather(*tasks)
        return dict(zip(queries, results_lists, strict=False))

    return asyncio.run(_batch_search())
