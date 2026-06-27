# powan_id: node-8a2f4ee457
# title: 標準logging接続
# parent: node-5815509426
# powanKind: nerve
# codeLanguage: python

"""Bridge the six-level log vocabulary to Python's standard logging module.

This nerve powan keeps the public connection small: call
``connect_standard_logging()`` once before building loggers, and TRACE becomes
available beside the standard logging levels.
"""

from __future__ import annotations

import logging
from typing import Final

TRACE_LEVEL: Final[int] = 5
TRACE_LEVEL_NAME: Final[str] = "TRACE"

_STANDARD_LEVELS: Final[dict[str, int]] = {
    "trace": TRACE_LEVEL,
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


def register_trace_level() -> int:
    """Register TRACE with ``logging`` and return its numeric level."""
    current_name = logging.getLevelName(TRACE_LEVEL)
    if current_name != TRACE_LEVEL_NAME:
        logging.addLevelName(TRACE_LEVEL, TRACE_LEVEL_NAME)
    return TRACE_LEVEL


def to_standard_logging_level(level: str | int) -> int:
    """Convert a six-level log name or integer into a logging level value."""
    if isinstance(level, int):
        return level

    normalized = level.strip().lower()
    try:
        return _STANDARD_LEVELS[normalized]
    except KeyError as exc:
        allowed = ", ".join(_STANDARD_LEVELS)
        raise ValueError(f"unknown log level: {level!r}; expected one of {allowed}") from exc


def install_trace_method() -> None:
    """Add ``Logger.trace(...)`` if the current runtime does not have it yet."""
    if hasattr(logging.Logger, "trace"):
        return

    def trace(self: logging.Logger, message: object, *args: object, **kwargs: object) -> None:
        if self.isEnabledFor(TRACE_LEVEL):
            self._log(TRACE_LEVEL, message, args, **kwargs)

    setattr(logging.Logger, "trace", trace)


def connect_standard_logging() -> int:
    """Connect all standard logging hooks owned by this powan.

    Returns the TRACE numeric level so callers can apply it to loggers or
    handlers without duplicating the constant.
    """
    trace_level = register_trace_level()
    install_trace_method()
    return trace_level


__all__ = [
    "TRACE_LEVEL",
    "TRACE_LEVEL_NAME",
    "connect_standard_logging",
    "install_trace_method",
    "register_trace_level",
    "to_standard_logging_level",
]
