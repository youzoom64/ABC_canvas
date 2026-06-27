# powan_id: node-defe15d75c
# title: ログレベル体系
# parent: node-5815509426
# powanKind: nerve
# codeLanguage: python

"""Interface for the six-level logging level system.

This nerve powan gathers the organ-level definitions for level names, order,
and the custom TRACE numeric value into one small public surface.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Final, Iterable, Mapping

TRACE_LEVEL: Final[int] = 5

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

LOG_LEVEL_ORDER: Final[Mapping[str, int]] = {
    level: index for index, level in enumerate(LOG_LEVELS)
}

LOGGING_LEVEL_VALUES: Final[Mapping[str, int]] = {
    TRACE: TRACE_LEVEL,
    DEBUG: logging.DEBUG,
    INFO: logging.INFO,
    WARNING: logging.WARNING,
    ERROR: logging.ERROR,
    CRITICAL: logging.CRITICAL,
}


@dataclass(frozen=True, slots=True)
class LogLevelSpec:
    """Canonical information for one supported logging level."""

    name: str
    order: int
    logging_value: int


LOG_LEVEL_SPECS: Final[tuple[LogLevelSpec, ...]] = tuple(
    LogLevelSpec(
        name=level,
        order=LOG_LEVEL_ORDER[level],
        logging_value=LOGGING_LEVEL_VALUES[level],
    )
    for level in LOG_LEVELS
)


def iter_log_level_specs() -> Iterable[LogLevelSpec]:
    """Yield the six supported levels from weakest to strongest."""

    return iter(LOG_LEVEL_SPECS)


def get_log_level_spec(level: str) -> LogLevelSpec:
    """Return the canonical spec for a level name."""

    normalized = level.lower()
    for spec in LOG_LEVEL_SPECS:
        if spec.name == normalized:
            return spec
    raise KeyError(f"Unsupported log level: {level!r}")


def logging_value_for(level: str) -> int:
    """Return the numeric value used by Python logging for a level."""

    return get_log_level_spec(level).logging_value


def order_for(level: str) -> int:
    """Return the six-level ordering index for a level."""

    return get_log_level_spec(level).order


def is_supported_log_level(level: str) -> bool:
    """Return True when level is one of the six canonical names."""

    return level.lower() in LOG_LEVEL_ORDER
