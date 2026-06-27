# powan_id: node-5815509426
# title: 6段階ログレベル
# parent: node-704b909f82
# powanKind:
# codeLanguage: python

"""Six-step log level nerve interface.

This powan represents the common six-level log vocabulary used by the parent
Python logging entry point.  It provides one stable surface for level names,
input normalization, level comparison, standard logging integration, and
presentation metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Final, Iterable, Mapping

TRACE_LEVEL: Final[int] = 5
TRACE_NAME: Final[str] = "TRACE"

LOG_LEVELS: Final[tuple[str, ...]] = (
    "trace",
    "debug",
    "info",
    "warning",
    "error",
    "critical",
)

LEVEL_ORDER: Final[dict[str, int]] = {name: index for index, name in enumerate(LOG_LEVELS)}

LEVEL_VALUES: Final[dict[str, int]] = {
    "trace": TRACE_LEVEL,
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

LEVEL_ALIASES: Final[dict[str, str]] = {
    "t": "trace",
    "trc": "trace",
    "trace": "trace",
    "verbose": "trace",
    "d": "debug",
    "dbg": "debug",
    "debug": "debug",
    "i": "info",
    "inf": "info",
    "info": "info",
    "information": "info",
    "notice": "info",
    "w": "warning",
    "warn": "warning",
    "warning": "warning",
    "e": "error",
    "err": "error",
    "error": "error",
    "exception": "error",
    "c": "critical",
    "crit": "critical",
    "critical": "critical",
    "fatal": "critical",
    "panic": "critical",
}

NUMERIC_LEVELS: Final[dict[int, str]] = {
    TRACE_LEVEL: "trace",
    logging.DEBUG: "debug",
    logging.INFO: "info",
    logging.WARNING: "warning",
    logging.ERROR: "error",
    logging.CRITICAL: "critical",
}

DISPLAY_NAMES: Final[dict[str, str]] = {name: name.upper() for name in LOG_LEVELS}
SHORT_NAMES: Final[dict[str, str]] = {
    "trace": "TRC",
    "debug": "DBG",
    "info": "INF",
    "warning": "WARN",
    "error": "ERR",
    "critical": "CRIT",
}
DISPLAY_COLORS: Final[dict[str, str]] = {
    "trace": "bright_black",
    "debug": "cyan",
    "info": "green",
    "warning": "yellow",
    "error": "red",
    "critical": "bright_red",
}


@dataclass(frozen=True, slots=True)
class LogLevelInfo:
    name: str
    display_name: str
    short_name: str
    logging_value: int
    order: int
    color: str


def canonical_level_names() -> tuple[str, ...]:
    """Return canonical log levels from most detailed to most severe."""
    return LOG_LEVELS


def normalize_level(value: Any, *, default: str | None = None) -> str:
    """Normalize external input into one canonical six-step level name."""
    if value is None:
        if default is None:
            raise ValueError("log level is required")
        value = default

    if isinstance(value, bool):
        raise ValueError("boolean values are not valid log levels")

    if isinstance(value, int):
        try:
            return NUMERIC_LEVELS[value]
        except KeyError as exc:
            raise ValueError(f"unknown numeric log level: {value!r}") from exc

    token = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    if not token:
        raise ValueError("log level must not be empty")

    try:
        return LEVEL_ALIASES[token]
    except KeyError as exc:
        expected = ", ".join(LOG_LEVELS)
        raise ValueError(f"unknown log level {value!r}; expected one of {expected}") from exc


def logging_value(value: Any) -> int:
    """Return the Python logging numeric value for a level."""
    return LEVEL_VALUES[normalize_level(value)]


def level_order(value: Any) -> int:
    """Return the severity order for a level."""
    return LEVEL_ORDER[normalize_level(value)]


def compare_levels(left: Any, right: Any) -> int:
    """Compare two levels: -1 weaker, 0 equal, 1 stronger."""
    left_order = level_order(left)
    right_order = level_order(right)
    return (left_order > right_order) - (left_order < right_order)


def should_log(level: Any, minimum: Any) -> bool:
    """Return True when level is at least as severe as minimum."""
    return compare_levels(level, minimum) >= 0


def register_trace_level() -> int:
    """Register TRACE with Python logging and return its numeric value."""
    if logging.getLevelName(TRACE_LEVEL) != TRACE_NAME:
        logging.addLevelName(TRACE_LEVEL, TRACE_NAME)
    return TRACE_LEVEL


def install_trace_method() -> None:
    """Install logger.trace(...) when the runtime does not have it yet."""
    if hasattr(logging.Logger, "trace"):
        return

    def trace(self: logging.Logger, message: object, *args: object, **kwargs: object) -> None:
        if self.isEnabledFor(TRACE_LEVEL):
            self._log(TRACE_LEVEL, message, args, **kwargs)

    setattr(logging.Logger, "trace", trace)


def connect_standard_logging() -> int:
    """Activate TRACE support in Python's standard logging module."""
    trace_level = register_trace_level()
    install_trace_method()
    return trace_level


def level_info(value: Any) -> LogLevelInfo:
    """Return logging, judgment, and display data for one level."""
    name = normalize_level(value)
    return LogLevelInfo(
        name=name,
        display_name=DISPLAY_NAMES[name],
        short_name=SHORT_NAMES[name],
        logging_value=LEVEL_VALUES[name],
        order=LEVEL_ORDER[name],
        color=DISPLAY_COLORS[name],
    )


def level_display(value: Any) -> dict[str, object]:
    """Return display-ready information for a level."""
    info = level_info(value)
    return {
        "level": info.name,
        "display_name": info.display_name,
        "short_name": info.short_name,
        "color": info.color,
        "order": info.order,
        "logging_value": info.logging_value,
    }


def iter_level_info() -> Iterable[LogLevelInfo]:
    """Yield all supported levels from most detailed to most severe."""
    for name in LOG_LEVELS:
        yield level_info(name)


def as_mapping() -> Mapping[str, LogLevelInfo]:
    """Return all level information keyed by canonical level name."""
    return {info.name: info for info in iter_level_info()}


__all__ = [
    "TRACE_LEVEL",
    "TRACE_NAME",
    "LOG_LEVELS",
    "LogLevelInfo",
    "as_mapping",
    "canonical_level_names",
    "compare_levels",
    "connect_standard_logging",
    "install_trace_method",
    "iter_level_info",
    "level_display",
    "level_info",
    "level_order",
    "logging_value",
    "normalize_level",
    "register_trace_level",
    "should_log",
]
