"""Structured logging configuration."""
from __future__ import annotations

import logging
import structlog
from structlog.stdlib import add_log_level

from app.config.settings import get_settings


def configure_logging() -> None:
    """Configure structured logging with processors."""
    settings = get_settings()

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        add_log_level,
        structlog.processors.TimeStamper(
            fmt="%Y-%m-%d %H:%M:%S",
            utc=False,
        ),
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ],
        ),
        structlog.processors.UnicodeDecoder(),
    ]

    # Dev console renderer
    if settings.debug:
        final_processors = shared_processors + [
            structlog.dev.ConsoleRenderer(
                colors=True,
                pad_event=50,
            )
        ]
    else:
        # JSON renderer for production
        final_processors = shared_processors + [structlog.processors.JSONRenderer()]

    structlog.configure(
        processors=final_processors,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper()),
        ),
        context_class=dict,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger for a module."""
    return structlog.get_logger(name)