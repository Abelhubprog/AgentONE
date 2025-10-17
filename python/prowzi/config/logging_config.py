"""
Structured logging configuration for Prowzi.

This module provides centralized logging configuration with:
- JSON structured logging for production
- Human-readable console logging for development
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Automatic log rotation
- Performance tracking

Usage:
    from prowzi.config.logging_config import setup_logging, get_logger

    # Setup logging (call once at application start)
    setup_logging(level="INFO", json_format=False)

    # Get logger for your module
    logger = get_logger(__name__)
    logger.info("Application started", extra={"version": "1.0.0"})
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any

# Default log format for console (human-readable)
CONSOLE_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DETAILED_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"

# Log levels mapping
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def setup_logging(
    level: str = "INFO",
    log_file: str | Path | None = None,
    json_format: bool = False,
    detailed: bool = False,
) -> None:
    """
    Setup centralized logging configuration for Prowzi.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for logging to file with rotation
        json_format: If True, use JSON structured logging (for production)
        detailed: If True, include function name and line number in logs

    Example:
        # Development mode
        setup_logging(level="DEBUG", detailed=True)

        # Production mode
        setup_logging(level="INFO", log_file="logs/prowzi.log", json_format=True)
    """
    # Get root logger
    root_logger = logging.getLogger()

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Set log level
    log_level = LOG_LEVELS.get(level.upper(), logging.INFO)
    root_logger.setLevel(log_level)

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Choose format based on settings
    if json_format:
        # JSON format for production (can be parsed by log aggregators)
        try:
            import json
            class JSONFormatter(logging.Formatter):
                def format(self, record: logging.LogRecord) -> str:
                    log_data = {
                        "timestamp": self.formatTime(record),
                        "level": record.levelname,
                        "logger": record.name,
                        "message": record.getMessage(),
                        "module": record.module,
                        "function": record.funcName,
                        "line": record.lineno,
                    }
                    # Add extra fields
                    if hasattr(record, "extra"):
                        log_data.update(record.extra)
                    return json.dumps(log_data)
            console_formatter = JSONFormatter()
        except ImportError:
            # Fallback to standard format if json not available
            console_formatter = logging.Formatter(DETAILED_FORMAT if detailed else CONSOLE_FORMAT)
    else:
        # Human-readable format for development
        console_formatter = logging.Formatter(DETAILED_FORMAT if detailed else CONSOLE_FORMAT)

    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation (if log_file specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Rotating file handler (max 10MB, keep 5 backups)
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(console_formatter)
        root_logger.addHandler(file_handler)

    # Suppress overly verbose third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    root_logger.info(
        "Logging configured",
        extra={"level": level, "json_format": json_format, "log_file": str(log_file) if log_file else None},
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given module name.

    Args:
        name: Logger name (typically __name__ from the calling module)

    Returns:
        logging.Logger: Configured logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Starting process", extra={"task_id": "123"})
        logger.error("Process failed", extra={"error": str(e)}, exc_info=True)
    """
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that automatically adds context to all log messages.

    Useful for adding common context (e.g., session_id, user_id) to all logs
    from a particular component.

    Example:
        base_logger = get_logger(__name__)
        logger = LoggerAdapter(base_logger, {"session_id": "abc123"})
        logger.info("Processing request")  # Automatically includes session_id
    """

    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Add extra context to log record."""
        # Merge adapter's extra with any extra passed to log call
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


# Convenience function for quick setup in CLI/scripts
def quick_setup(verbose: bool = False) -> None:
    """
    Quick logging setup for CLI tools and scripts.

    Args:
        verbose: If True, set level to DEBUG; otherwise INFO
    """
    setup_logging(
        level="DEBUG" if verbose else "INFO",
        detailed=verbose,
    )


# Pre-configured logger for this module
logger = get_logger(__name__)
