"""Structured logging setup using structlog."""

import os

import structlog


def setup_logging(log_level: str = "INFO") -> None:
    """Configure structlog for the application."""
    renderer = (
        structlog.dev.ConsoleRenderer()
        if os.getenv("LOG_FORMAT", "console") == "console"
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            structlog.get_level_from_name(log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.typing.FilteringBoundLogger:
    """Get a named logger instance."""
    return structlog.get_logger(name)
