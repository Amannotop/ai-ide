"""Structured logging configuration."""
from __future__ import annotations

import logging
import structlog
from structlog import WriteLoggerFactory
from structlog.stdlib import add_log_level

from app.config.settings import get_settings

# Dev console renderer
console_renderer = structlog.dev.ConsoleRenderer(
    colors=True,
    exception_chaining=True,
    show_log_level=True,
    show_timestamp=True,
    pad_event=50,
)

# JSON renderer for production
json_renderer = structlog.processors.JSONRenderer()


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

    dev_processors = shared_processors + [console_renderer]
    prod_processors = shared_processors + [json_renderer]

    if settings.debug:
        final_processors = dev_processors
    else:
        final_processors = prod_processors

    structlog.configure(
        processors=final_processors,
        logger_factory=WriteLoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper()),
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger for a module."""
    return structlog.get_logger(name)