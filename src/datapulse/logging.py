"""Structured logging setup using structlog."""

import logging

import structlog

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "password",
        "token",
        "secret",
        "credential",
        "database_url",
        "connection_string",
        "authorization",
    }
)


def _mask_sensitive_fields(logger: object, method_name: str, event_dict: dict) -> dict:
    """Redact values of sensitive keys in log records."""
    for key in _SENSITIVE_KEYS:
        if key in event_dict:
            event_dict[key] = "***REDACTED***"
    return event_dict


def setup_logging(log_level: str = "INFO", log_format: str = "console") -> None:
    """Configure structlog for the application.

    Args:
        log_level: Minimum log level (e.g. "INFO", "DEBUG").
        log_format: Output format — "console" for human-readable, "json" for structured.
    """
    renderer = (
        structlog.dev.ConsoleRenderer()
        if log_format == "console"
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _mask_sensitive_fields,  # type: ignore[list-item]
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(log_level)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.typing.FilteringBoundLogger:
    """Get a named logger instance."""
    return structlog.get_logger(name)
