# powan_id: node-cf047b81df
# title: ログレベル定義
# parent: node-defe15d75c
# powanKind: organ
# codeLanguage: python

"""Canonical names for the six supported logging levels."""

from __future__ import annotations

from typing import Final

TRACE: Final[str] = "trace"
DEBUG: Final[str] = "debug"
INFO: Final[str] = "info"
WARNING: Final[str] = "warning"
ERROR: Final[str] = "error"
CRITICAL: Final[str] = "critical"

LOG_LEVELS: Final[tuple[str, ...]] = (
    TRACE,
    DEBUG,
    INFO,
    WARNING,
    ERROR,
    CRITICAL,
)

LOG_LEVEL_SET: Final[frozenset[str]] = frozenset(LOG_LEVELS)


def is_defined_log_level(level: str) -> bool:
    """Return True when level is one of the canonical six names."""

    return level.lower() in LOG_LEVEL_SET
