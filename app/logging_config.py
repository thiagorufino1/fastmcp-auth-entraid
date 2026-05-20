from __future__ import annotations

import logging
import os
import sys
from typing import Final

import structlog

_DEFAULT_LEVEL: Final[str] = "INFO"
_VALID_LEVELS: Final[frozenset[str]] = frozenset(
    {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}
)
_configured: bool = False


def _resolve_level() -> int:
    raw = os.getenv("LOG_LEVEL", _DEFAULT_LEVEL).strip().upper() or _DEFAULT_LEVEL
    if raw not in _VALID_LEVELS:
        raw = _DEFAULT_LEVEL
    return logging.getLevelNamesMapping()[raw]


def configure_logging(*, force: bool = False) -> None:
    """Configure structlog + stdlib logging once per process.

    Emits JSON to stderr. Reads LOG_LEVEL env var (default INFO).
    Idempotent: second call is a no-op unless force=True.
    """
    global _configured
    if _configured and not force:
        return

    level = _resolve_level()

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )

    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
        )
    )
    root.addHandler(handler)
    root.setLevel(level)

    _configured = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
