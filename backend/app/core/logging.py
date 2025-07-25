"""
Structured Logging Setup
=========================
Configures structlog for JSON or console output depending on environment.
All NetWatch components should use `get_logger(__name__)` to obtain a logger.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from app.core.config import get_settings


def configure_logging() -> None:
    """Configure structlog and stdlib logging for the entire application."""
    settings = get_settings()
    log_level = getattr(logging, settings.log_level, logging.INFO)

    # Configure stdlib root logger
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Silence noisy libraries
    for lib in ("uvicorn.access", "sqlalchemy.engine", "httpx"):
        logging.getLogger(lib).setLevel(logging.WARNING)

    # Shared processors for all log entries
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.log_format == "json" and not settings.is_development:
        # Production: clean JSON output
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development: colourful console output
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Return a bound structlog logger for the given module name."""
    return structlog.get_logger(name)
