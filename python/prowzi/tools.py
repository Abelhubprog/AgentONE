# Copyright (c) Microsoft. All rights reserved.

"""
Prowzi Tools - Comprehensive tool ecosystem for autonomous agents

This module provides a rich set of tools that Prowzi agents can use to:
- Search and retrieve information
- Analyze data and extract insights
- Generate and validate code
- Manipulate files and data structures
- Perform calculations and transformations

All tools are designed to be:
- Type-safe with proper annotations
- Descriptive with clear docstrings
- Robust with error handling
- Autonomous-friendly (agents decide when to use them)
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any


# ============================================================================
# Information Retrieval Tools
# ============================================================================


def search_knowledge_base(
    query: Annotated[str, "The search query to find relevant information"],
) -> str:
    """Search a knowledge base for relevant information.

    This is a simulated search that provides structured information
    based on common queries. In production, this would connect to:
    - Vector databases (Qdrant, Pinecone, Weaviate)
    - Search engines (Elasticsearch, Algolia)
    - Knowledge graphs
    - Internal documentation systems

    Args:
        query: Search query string

    Returns:
        Relevant information or indication that no results were found
    """
    # Simulated knowledge base responses
    knowledge = {
        "autonomous agents": """
        Autonomous agents are AI systems that can:
        - Make decisions without human intervention
        - Collaborate with other agents
        - Learn from experience and adapt
        - Use tools and external resources
        - Plan and execute multi-step tasks
        
        Key benefits: Scalability, efficiency, 24/7 operation, consistency
        """,
        "multi-agent systems": """
        Multi-agent systems consist of multiple autonomous agents that:
        - Have specialized roles and expertise
        - Communicate and coordinate with each other
        - Solve complex problems collaboratively
        - Self-organize to achieve goals
        
        Common patterns: Sequential, concurrent, hierarchical, peer-to-peer
        """,
        "microsoft agent framework": """
        Microsoft Agent Framework is an enterprise-grade framework for building AI agents:
        - Supports multiple LLM providers
        - Built-in workflows and orchestration
        - Production-ready with observability
        - Extensible architecture
        - Both .NET and Python implementations
        """,
    }

    query_lower = query.lower()
    for key, value in knowledge.items():
        if key in query_lower:
            return f"Found information about '{key}':\n{value.strip()}"

    return f"No specific information found for query: '{query}'. Consider refining the search terms."


def get_current_datetime() -> str:
    """Get the current date and time.

    Returns:
        Current date and time in ISO format
    """
    return datetime.now().isoformat()


def get_system_info() -> dict[str, Any]:
    """Get information about the current system and environment.

    Returns:
        Dictionary with system information
    """
    return {
        "platform": os.name,
        "cwd": os.getcwd(),
        "python_version": os.sys.version,
        "environment": "development",
    }


# ============================================================================
# Data Analysis Tools
# ============================================================================


def calculate(
    expression: Annotated[str, "Mathematical expression to evaluate (e.g., '2 + 2', '15% of 200')"],
) -> str:
    """Safely evaluate a mathematical expression.

    Supports basic arithmetic operations. Use for calculations and
    mathematical analysis.

    Args:
        expression: Mathematical expression as string

    Returns:
        Calculation result or error message
    """
    try:
        # Handle percentage calculations
        if "%" in expression and " of " in expression:
            parts = expression.lower().split(" of ")
            if len(parts) == 2:
                percent_part = parts[0].replace("%", "").strip()
                value_part = parts[1].strip()
                percent = float(eval(percent_part, {"__builtins__": {}}))
                value = float(eval(value_part, {"__builtins__": {}}))
                result = (percent / 100) * value
                return f"{result}"

        # Safe evaluation with restricted builtins
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error evaluating expression: {str(e)}"


def count_items(
    items: Annotated[list[Any], "List of items to count"],
) -> int:
    """Count the number of items in a list.

    Args:
        items: List of items

    Returns:
        Count of items
    """
    return len(items)


def find_pattern(
    text: Annotated[str, "Text to search in"],
    pattern: Annotated[str, "Pattern to search for (supports regex)"],
) -> dict[str, Any]:
    """Find patterns in text using regular expressions.

    Args:
        text: Text to search in
        pattern: Pattern to find (regex supported)

    Returns:
        Dictionary with matches and count
    """
    try:
        matches = re.findall(pattern, text, re.IGNORECASE)
        return {"matches": matches, "count": len(matches), "pattern": pattern}
    except Exception as e:
        return {"error": str(e), "matches": [], "count": 0}


def analyze_text(
    text: Annotated[str, "Text to analyze"],
) -> dict[str, Any]:
    """Analyze text and provide statistics.

    Args:
        text: Text to analyze

    Returns:
        Dictionary with text statistics
    """
    words = text.split()
    sentences = text.split(".")
    lines = text.split("\n")

    return {
        "character_count": len(text),
        "word_count": len(words),
        "sentence_count": len(sentences),
        "line_count": len(lines),
        "average_word_length": sum(len(w) for w in words) / len(words) if words else 0,
    }


# ============================================================================
# Code Generation and Validation Tools
# ============================================================================


def validate_python_syntax(
    code: Annotated[str, "Python code to validate"],
) -> dict[str, Any]:
    """Validate Python code syntax.

    Args:
        code: Python code string

    Returns:
        Dictionary with validation results
    """
    try:
        compile(code, "<string>", "exec")
        return {"valid": True, "message": "Syntax is valid"}
    except SyntaxError as e:
        return {
            "valid": False,
            "message": f"Syntax error at line {e.lineno}: {e.msg}",
            "line": e.lineno,
            "offset": e.offset,
        }
    except Exception as e:
        return {"valid": False, "message": f"Error: {str(e)}"}


def format_code_snippet(
    code: Annotated[str, "Code to format"],
    language: Annotated[str, "Programming language (python, javascript, etc.)"] = "python",
) -> str:
    """Format code snippet with syntax highlighting markers.

    Args:
        code: Code to format
        language: Programming language

    Returns:
        Formatted code with language markers
    """
    return f"```{language}\n{code}\n```"


def generate_function_template(
    function_name: Annotated[str, "Name of the function"],
    parameters: Annotated[list[str], "List of parameter names"],
    return_type: Annotated[str, "Return type"] = "Any",
) -> str:
    """Generate a function template with docstring.

    Args:
        function_name: Name of the function
        parameters: List of parameter names
        return_type: Return type annotation

    Returns:
        Function template as string
    """
    params_str = ", ".join(parameters)
    params_doc = "\n    ".join([f"{p}: Description of {p}" for p in parameters])

    template = f'''def {function_name}({params_str}) -> {return_type}:
    """Brief description of {function_name}.

    Args:
    {params_doc}

    Returns:
        Description of return value
    """
    # TODO: Implement function
    pass
'''
    return template


# ============================================================================
# File and Data Operations
# ============================================================================


def read_text_file(
    file_path: Annotated[str, "Path to the text file to read"],
) -> str:
    """Read contents of a text file.

    Args:
        file_path: Path to file

    Returns:
        File contents or error message
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return f"Error: File not found: {file_path}"
        if not path.is_file():
            return f"Error: Not a file: {file_path}"

        return path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {str(e)}"


def write_text_file(
    file_path: Annotated[str, "Path where to write the file"],
    content: Annotated[str, "Content to write"],
) -> str:
    """Write content to a text file.

    Args:
        file_path: Destination path
        content: Content to write

    Returns:
        Success or error message
    """
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters to {file_path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


def list_files(
    directory: Annotated[str, "Directory to list files from"],
    pattern: Annotated[str, "File pattern (e.g., '*.py', '*.txt')"] = "*",
) -> list[str]:
    """List files in a directory matching a pattern.

    Args:
        directory: Directory path
        pattern: Glob pattern for files

    Returns:
        List of matching file paths
    """
    try:
        path = Path(directory)
        if not path.exists():
            return [f"Error: Directory not found: {directory}"]
        if not path.is_dir():
            return [f"Error: Not a directory: {directory}"]

        files = [str(f) for f in path.glob(pattern) if f.is_file()]
        return files if files else [f"No files matching '{pattern}' found in {directory}"]
    except Exception as e:
        return [f"Error listing files: {str(e)}"]


def parse_json(
    json_string: Annotated[str, "JSON string to parse"],
) -> dict[str, Any] | str:
    """Parse a JSON string into a dictionary.

    Args:
        json_string: JSON string

    Returns:
        Parsed dictionary or error message
    """
    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        return f"JSON parse error at line {e.lineno}, column {e.colno}: {e.msg}"
    except Exception as e:
        return f"Error parsing JSON: {str(e)}"


def create_json(
    data: Annotated[dict[str, Any], "Dictionary to convert to JSON"],
    pretty: Annotated[bool, "Whether to format with indentation"] = True,
) -> str:
    """Convert a dictionary to JSON string.

    Args:
        data: Dictionary to convert
        pretty: Whether to use pretty printing

    Returns:
        JSON string
    """
    try:
        if pretty:
            return json.dumps(data, indent=2, ensure_ascii=False)
        return json.dumps(data, ensure_ascii=False)
    except Exception as e:
        return f"Error creating JSON: {str(e)}"


# ============================================================================
# String and Text Manipulation
# ============================================================================


def format_as_table(
    headers: Annotated[list[str], "Column headers"],
    rows: Annotated[list[list[str]], "Table rows"],
) -> str:
    """Format data as a text table.

    Args:
        headers: Column headers
        rows: Table rows

    Returns:
        Formatted table as string
    """
    if not headers or not rows:
        return "Error: Headers and rows are required"

    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    # Format header
    header_row = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    separator = "-+-".join("-" * w for w in col_widths)

    # Format rows
    data_rows = []
    for row in rows:
        formatted_row = " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))
        data_rows.append(formatted_row)

    return f"{header_row}\n{separator}\n" + "\n".join(data_rows)


def create_bullet_list(
    items: Annotated[list[str], "List items"],
    numbered: Annotated[bool, "Whether to use numbers instead of bullets"] = False,
) -> str:
    """Create a formatted bullet or numbered list.

    Args:
        items: List items
        numbered: Use numbers instead of bullets

    Returns:
        Formatted list as string
    """
    if numbered:
        return "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items))
    return "\n".join(f"• {item}" for item in items)


# ============================================================================
# Tool Registry
# ============================================================================


def get_all_prowzi_tools() -> list[Any]:
    """Get all available Prowzi tools.

    Returns:
        List of all tool functions
    """
    return [
        # Information retrieval
        search_knowledge_base,
        get_current_datetime,
        get_system_info,
        # Data analysis
        calculate,
        count_items,
        find_pattern,
        analyze_text,
        # Code tools
        validate_python_syntax,
        format_code_snippet,
        generate_function_template,
        # File operations
        read_text_file,
        write_text_file,
        list_files,
        parse_json,
        create_json,
        # Text formatting
        format_as_table,
        create_bullet_list,
    ]


def get_research_tools() -> list[Any]:
    """Get tools suitable for research tasks."""
    return [
        search_knowledge_base,
        get_current_datetime,
        find_pattern,
        analyze_text,
        read_text_file,
        list_files,
    ]


def get_analyst_tools() -> list[Any]:
    """Get tools suitable for analysis tasks."""
    return [
        calculate,
        count_items,
        find_pattern,
        analyze_text,
        parse_json,
        format_as_table,
    ]


def get_planner_tools() -> list[Any]:
    """Get tools suitable for planning tasks."""
    return [
        get_current_datetime,
        create_bullet_list,
        format_as_table,
        count_items,
    ]


def get_executor_tools() -> list[Any]:
    """Get tools suitable for execution tasks."""
    return [
        validate_python_syntax,
        format_code_snippet,
        generate_function_template,
        write_text_file,
        read_text_file,
        create_json,
        parse_json,
    ]


def get_validator_tools() -> list[Any]:
    """Get tools suitable for validation tasks."""
    return [
        validate_python_syntax,
        analyze_text,
        read_text_file,
        parse_json,
        count_items,
    ]
