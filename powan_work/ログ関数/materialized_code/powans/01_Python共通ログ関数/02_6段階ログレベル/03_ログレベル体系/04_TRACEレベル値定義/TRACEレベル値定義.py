# powan_id: node-55ab8b5c41
# title: TRACEレベル値定義
# parent: node-defe15d75c
# powanKind: organ
# codeLanguage: python

"""Numeric value for the custom TRACE logging level."""

from __future__ import annotations

import logging
from typing import Final

TRACE_LEVEL_NAME: Final[str] = "TRACE"
TRACE_LEVEL_VALUE: Final[int] = 5


def trace_level_value() -> int:
    """Return the numeric logging value for TRACE."""

    return TRACE_LEVEL_VALUE


def is_trace_finer_than_debug() -> bool:
    """Return True when TRACE is numerically below DEBUG."""

    return TRACE_LEVEL_VALUE < logging.DEBUG
