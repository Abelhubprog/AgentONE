"""
Document Parsing Tools

Handles PDF, DOCX, Markdown, and text file extraction.
Optimized for large documents with streaming and chunking.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import mimetypes


def parse_document(
    file_path: str | Path,
    extract_metadata: bool = True
) -> Dict[str, Any]:
    """
    Parse a document and extract text content and metadata.

    Args:
        file_path: Path to the document file
        extract_metadata: Whether to extract metadata (title, author, etc.)

    Returns:
        Dictionary with:
            - content: Extracted text content
            - metadata: Document metadata (if extract_metadata=True)
            - file_type: Type of document
            - word_count: Number of words
            - char_count: Number of characters

    Example:
        >>> result = parse_document("research_paper.pdf")
        >>> print(result["content"][:100])
        >>> print(f"Word count: {result['word_count']}")
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Detect file type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    file_extension = file_path.suffix.lower()

    # Route to appropriate parser
    if file_extension == ".pdf":
        content, metadata = _parse_pdf(file_path, extract_metadata)
    elif file_extension in [".docx", ".doc"]:
        content, metadata = _parse_docx(file_path, extract_metadata)
    elif file_extension in [".md", ".markdown"]:
        content, metadata = _parse_markdown(file_path, extract_metadata)
    elif file_extension == ".txt":
        content, metadata = _parse_text(file_path, extract_metadata)
    else:
        raise ValueError(f"Unsupported file type: {file_extension}")

    # Calculate statistics
    word_count = len(content.split())
    char_count = len(content)

    return {
        "content": content,
        "metadata": metadata if extract_metadata else {},
        "file_type": file_extension[1:],  # Remove leading dot
        "file_name": file_path.name,
        "file_size_bytes": file_path.stat().st_size,
        "word_count": word_count,
        "char_count": char_count,
    }


def _parse_pdf(file_path: Path, extract_metadata: bool) -> tuple[str, Dict[str, Any]]:
    """Parse PDF using PyPDF2 or pdfplumber"""
    try:
        import PyPDF2

        content_parts = []
        metadata = {}

        with open(file_path, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)

            # Extract metadata
            if extract_metadata and pdf_reader.metadata:
                metadata = {
                    "title": pdf_reader.metadata.get("/Title", ""),
                    "author": pdf_reader.metadata.get("/Author", ""),
                    "subject": pdf_reader.metadata.get("/Subject", ""),
                    "creator": pdf_reader.metadata.get("/Creator", ""),
                    "producer": pdf_reader.metadata.get("/Producer", ""),
                    "creation_date": pdf_reader.metadata.get("/CreationDate", ""),
                    "num_pages": len(pdf_reader.pages),
                }

            # Extract text from all pages
            for page_num, page in enumerate(pdf_reader.pages, start=1):
                text = page.extract_text()
                if text.strip():
                    content_parts.append(f"[Page {page_num}]\n{text}")

        content = "\n\n".join(content_parts)

        return content, metadata

    except ImportError:
        raise ImportError(
            "PyPDF2 is required for PDF parsing. Install with: pip install PyPDF2"
        )


def _parse_docx(file_path: Path, extract_metadata: bool) -> tuple[str, Dict[str, Any]]:
    """Parse DOCX using python-docx"""
    try:
        from docx import Document

        doc = Document(file_path)

        # Extract text from paragraphs
        content_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                content_parts.append(para.text)

        content = "\n\n".join(content_parts)

        # Extract metadata
        metadata = {}
        if extract_metadata:
            core_props = doc.core_properties
            metadata = {
                "title": core_props.title or "",
                "author": core_props.author or "",
                "subject": core_props.subject or "",
                "keywords": core_props.keywords or "",
                "created": str(core_props.created) if core_props.created else "",
                "modified": str(core_props.modified) if core_props.modified else "",
            }

        return content, metadata

    except ImportError:
        raise ImportError(
            "python-docx is required for DOCX parsing. Install with: pip install python-docx"
        )


def _parse_markdown(file_path: Path, extract_metadata: bool) -> tuple[str, Dict[str, Any]]:
    """Parse Markdown file"""
    content = file_path.read_text(encoding="utf-8")

    metadata = {}
    if extract_metadata:
        # Extract front matter if present (YAML-style)
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    import yaml
                    metadata = yaml.safe_load(parts[1])
                    content = parts[2].strip()
                except ImportError:
                    pass  # Skip front matter extraction if yaml not available

    return content, metadata


def _parse_text(file_path: Path, extract_metadata: bool) -> tuple[str, Dict[str, Any]]:
    """Parse plain text file"""
    content = file_path.read_text(encoding="utf-8")
    metadata = {}

    return content, metadata


def parse_multiple_documents(
    file_paths: List[str | Path],
    extract_metadata: bool = True
) -> List[Dict[str, Any]]:
    """
    Parse multiple documents in batch.

    Args:
        file_paths: List of paths to document files
        extract_metadata: Whether to extract metadata

    Returns:
        List of parsed document dictionaries
    """
    results = []

    for file_path in file_paths:
        try:
            result = parse_document(file_path, extract_metadata)
            results.append(result)
        except Exception as e:
            results.append({
                "error": str(e),
                "file_path": str(file_path),
                "success": False
            })

    return results


def extract_citations(text: str) -> List[str]:
    """
    Extract citations from text using common patterns.

    Supports formats:
        - APA: (Author, Year)
        - MLA: (Author Page)
        - IEEE: [1], [2]
        - Harvard: (Author Year)

    Args:
        text: Text content to extract citations from

    Returns:
        List of citation strings found in text
    """
    import re

    citations = []

    # APA/Harvard style: (Author, Year) or (Author Year)
    apa_pattern = r'\(([A-Z][a-z]+(?:,?\s+(?:et\s+al\.|&\s+[A-Z][a-z]+)?)\s*,?\s*\d{4}[a-z]?)\)'
    citations.extend(re.findall(apa_pattern, text))

    # IEEE style: [1], [2-5]
    ieee_pattern = r'\[(\d+(?:-\d+)?(?:,\s*\d+(?:-\d+)?)*)\]'
    citations.extend(re.findall(ieee_pattern, text))

    return list(set(citations))  # Remove duplicates


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 100,
    separator: str = "\n\n"
) -> List[str]:
    """
    Split text into overlapping chunks for processing.

    Useful for handling large documents that exceed model context windows.

    Args:
        text: Text to chunk
        chunk_size: Target size of each chunk (in characters)
        chunk_overlap: Overlap between chunks (in characters)
        separator: Preferred split points (e.g., paragraphs)

    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # If not at end, try to find separator near end
        if end < len(text):
            sep_pos = text.rfind(separator, start, end)
            if sep_pos != -1 and sep_pos > start + (chunk_size // 2):
                end = sep_pos + len(separator)

        chunks.append(text[start:end])
        start = end - chunk_overlap

    return chunks
