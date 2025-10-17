"""
Script to automatically replace print() statements with proper logging calls.

This script:
1. Finds all print() statements in prowzi code
2. Analyzes the context to determine appropriate log level
3. Replaces print() with logger.info/debug/warning/error
4. Adds logger import if not present

Usage:
    python scripts/replace_prints_with_logging.py
"""

import re
from pathlib import Path
from typing import List, Tuple

# Files to process
PROWZI_ROOT = Path(__file__).parent.parent / "prowzi"

# Patterns to detect log level from context
ERROR_PATTERNS = [
    r"error",
    r"exception",
    r"fail",
    r"critical",
    r"fatal",
]

WARNING_PATTERNS = [
    r"warning",
    r"warn",
    r"deprecated",
    r"missing",
    r"not found",
    r"unable",
    r"cannot",
    r"invalid",
]

DEBUG_PATTERNS = [
    r"debug",
    r"trace",
    r"detail",
    r"verbose",
]


def determine_log_level(print_content: str, surrounding_code: str) -> str:
    """Determine appropriate log level based on context."""
    combined = (print_content + " " + surrounding_code).lower()

    # Check for error patterns
    if any(re.search(pattern, combined) for pattern in ERROR_PATTERNS):
        return "error"

    # Check for warning patterns
    if any(re.search(pattern, combined) for pattern in WARNING_PATTERNS):
        return "warning"

    # Check for debug patterns
    if any(re.search(pattern, combined) for pattern in DEBUG_PATTERNS):
        return "debug"

    # Default to info
    return "info"


def has_logger_import(content: str) -> bool:
    """Check if file already has logger import."""
    patterns = [
        r"import logging",
        r"from .*logging",
        r"from prowzi.config.logging_config import",
        r"logger = ",
    ]
    return any(re.search(pattern, content) for pattern in patterns)


def add_logger_import(content: str, module_name: str) -> str:
    """Add logger import at the top of the file."""
    # Find the position after the last import or docstring
    lines = content.split("\n")
    insert_position = 0

    in_docstring = False
    docstring_char = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Track docstrings
        if stripped.startswith('"""') or stripped.startswith("'''"):
            if not in_docstring:
                in_docstring = True
                docstring_char = '"""' if stripped.startswith('"""') else "'''"
            elif stripped.endswith(docstring_char):
                in_docstring = False
                insert_position = i + 1

        # Track imports
        if not in_docstring and (stripped.startswith("import ") or stripped.startswith("from ")):
            insert_position = i + 1

    # Add blank line and logger import
    logger_import = f"\nfrom prowzi.config.logging_config import get_logger\n\nlogger = get_logger(__name__)\n"

    lines.insert(insert_position, logger_import)
    return "\n".join(lines)


def convert_print_to_logger(match: re.Match, surrounding_code: str) -> str:
    """Convert a print() statement to logger call."""
    print_content = match.group(1)

    # Determine log level
    log_level = determine_log_level(print_content, surrounding_code)

    # Handle f-strings
    if print_content.strip().startswith('f"') or print_content.strip().startswith("f'"):
        # Already an f-string, just replace print with logger
        return f"logger.{log_level}({print_content})"

    # Handle format strings
    if ".format(" in print_content:
        # Convert to f-string if simple, otherwise keep as-is
        return f"logger.{log_level}({print_content})"

    # Simple strings
    return f"logger.{log_level}({print_content})"


def process_file(file_path: Path) -> Tuple[int, List[str]]:
    """
    Process a single Python file to replace print statements.

    Returns:
        Tuple of (count of replacements, list of changes made)
    """
    if not file_path.exists():
        return 0, []

    with open(file_path, "r", encoding="utf-8") as f:
        original_content = f.read()

    content = original_content
    changes = []

    # Find all print statements
    print_pattern = re.compile(r'print\((.*?)\)(?:\s*#.*)?$', re.MULTILINE)
    matches = list(print_pattern.finditer(content))

    if not matches:
        return 0, []

    # Add logger import if needed
    if not has_logger_import(content):
        content = add_logger_import(content, file_path.stem)
        changes.append(f"Added logger import to {file_path.name}")

    # Replace print statements (in reverse order to maintain positions)
    for match in reversed(matches):
        # Get surrounding code for context
        start = max(0, match.start() - 200)
        end = min(len(content), match.end() + 200)
        surrounding = content[start:end]

        # Convert print to logger
        old_text = match.group(0)
        new_text = convert_print_to_logger(match, surrounding)

        content = content[:match.start()] + new_text + content[match.end():]
        changes.append(f"  {file_path.name}:{match.start()} - Replaced: {old_text[:50]}")

    # Only write if changes were made
    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    return len(matches), changes


def main():
    """Main entry point."""
    print("="*60)
    print("Replacing print() statements with proper logging")
    print("="*60)
    print()

    # Find all Python files in prowzi
    python_files = list(PROWZI_ROOT.rglob("*.py"))
    python_files = [f for f in python_files if "__pycache__" not in str(f)]

    print(f"Found {len(python_files)} Python files to process")
    print()

    total_replacements = 0
    all_changes = []

    for file_path in sorted(python_files):
        count, changes = process_file(file_path)
        if count > 0:
            total_replacements += count
            print(f"✅ {file_path.relative_to(PROWZI_ROOT)}: {count} print statements replaced")
            all_changes.extend(changes)

    print()
    print("="*60)
    print(f"Total: {total_replacements} print statements replaced with logging")
    print("="*60)
    print()

    if all_changes:
        print("Changes made:")
        for change in all_changes[:20]:  # Show first 20 changes
            print(change)
        if len(all_changes) > 20:
            print(f"  ... and {len(all_changes) - 20} more changes")

    print()
    print("✅ Done! Remember to:")
    print("1. Review the changes")
    print("2. Test the application")
    print("3. Update any documentation mentioning print()")


if __name__ == "__main__":
    main()
