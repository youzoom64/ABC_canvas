# powan_id: node-6bc4998fc0
# title: TRACEレベル登録
# parent: node-8a2f4ee457
# powanKind: organ
# codeLanguage: python

"""Register the TRACE level with Python's standard logging module.

This organ powan owns only TRACE registration. It defines the TRACE numeric
level and makes the name visible to ``logging`` through ``addLevelName``.
"""

from __future__ import annotations

import logging
from typing import Final

TRACE_LEVEL: Final[int] = 5
TRACE_LEVEL_NAME: Final[str] = "TRACE"


def register_trace_level() -> int:
    """Register TRACE with ``logging`` and return its numeric level.

    Calling this function multiple times is safe. If TRACE is already registered
    at the expected value, the logging registry is left as-is.
    """
    if logging.getLevelName(TRACE_LEVEL) != TRACE_LEVEL_NAME:
        logging.addLevelName(TRACE_LEVEL, TRACE_LEVEL_NAME)
    return TRACE_LEVEL


def is_trace_level_registered() -> bool:
    """Return whether ``logging`` currently resolves level 5 as TRACE."""
    return logging.getLevelName(TRACE_LEVEL) == TRACE_LEVEL_NAME


__all__ = [
    "TRACE_LEVEL",
    "TRACE_LEVEL_NAME",
    "is_trace_level_registered",
    "register_trace_level",
]
