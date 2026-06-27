# powan_id: node-4d5c7e6f19
# title: 標準logging変換
# parent: node-8a2f4ee457
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

import logging
from typing import Final

TRACE_LEVEL: Final[int] = 5

_LEVEL_NAME_TO_VALUE: Final[dict[str, int]] = {
    "trace": TRACE_LEVEL,
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


def to_standard_logging_level(level: str | int) -> int:
    """Convert a six-level log level into a Python logging level value.

    The canonical six levels are trace, debug, info, warning, error, and
    critical. Debug and higher use Python's standard logging constants; trace
    maps to this project's custom level value. Integer values are returned as-is
    so callers can pass logging-compatible numeric levels directly.
    """
    if isinstance(level, int):
        return level

    normalized = level.strip().lower()
    try:
        return _LEVEL_NAME_TO_VALUE[normalized]
    except KeyError as exc:
        allowed = ", ".join(_LEVEL_NAME_TO_VALUE)
        raise ValueError(
            f"Unsupported log level {level!r}. Expected one of: {allowed}"
        ) from exc


__all__ = ["TRACE_LEVEL", "to_standard_logging_level"]
