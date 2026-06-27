# powan_id: node-b56f0cd50f
# title: ログレベル入力解釈
# parent: node-5815509426
# powanKind: nerve
# codeLanguage: python

from __future__ import annotations

import logging
from typing import Any

CANONICAL_LOG_LEVELS: tuple[str, ...] = (
    "trace",
    "debug",
    "info",
    "warning",
    "error",
    "critical",
)
CANONICAL_LOG_LEVEL_SET: frozenset[str] = frozenset(CANONICAL_LOG_LEVELS)

NUMERIC_LOG_LEVELS: dict[int, str] = {
    5: "trace",
    logging.DEBUG: "debug",
    logging.INFO: "info",
    logging.WARNING: "warning",
    logging.ERROR: "error",
    logging.CRITICAL: "critical",
}

LOG_LEVEL_ALIASES: dict[str, str] = {
    "t": "trace",
    "trc": "trace",
    "trace": "trace",
    "verbose": "trace",
    "v": "trace",
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


def normalize_log_level_input(value: Any) -> str:
    """Return a lowercase log-level token from external string or numeric input."""
    if value is None:
        raise ValueError("log level is required; expected trace, debug, info, warning, error, or critical")

    if isinstance(value, bool):
        raise ValueError("boolean values are not valid log levels")

    if isinstance(value, int):
        try:
            return NUMERIC_LOG_LEVELS[value]
        except KeyError as exc:
            expected_numbers = ", ".join(str(item) for item in sorted(NUMERIC_LOG_LEVELS))
            raise ValueError(f"unknown numeric log level {value!r}; expected one of {expected_numbers}") from exc

    if isinstance(value, str):
        token = value.strip().lower().replace("-", "_").replace(" ", "_")
        if not token:
            raise ValueError("log level must not be empty")
        return token

    raise TypeError(f"log level must be str or int, got {type(value).__name__}")


def resolve_log_level_alias(token: str) -> str:
    """Resolve a normalized log-level token or alias to a canonical 6-step level name."""
    clean = token.strip().lower().replace("-", "_").replace(" ", "_")
    if not clean:
        raise ValueError("log level must not be empty")

    try:
        return LOG_LEVEL_ALIASES[clean]
    except KeyError as exc:
        aliases = ", ".join(sorted(LOG_LEVEL_ALIASES))
        raise ValueError(f"unknown log level alias {token!r}; known aliases: {aliases}") from exc


def validate_log_level(level: str) -> str:
    """Validate and return a canonical 6-step log level name."""
    if not isinstance(level, str):
        raise TypeError(f"canonical log level must be str, got {type(level).__name__}")

    if level not in CANONICAL_LOG_LEVEL_SET:
        expected = ", ".join(CANONICAL_LOG_LEVELS)
        raise ValueError(f"invalid log level {level!r}; expected one of: {expected}")

    return level


def parse_log_level(value: Any) -> str:
    """Convert external log-level input into one canonical 6-step log level name."""
    normalized = normalize_log_level_input(value)
    resolved = resolve_log_level_alias(normalized)
    return validate_log_level(resolved)


def is_log_level(value: Any) -> bool:
    """Return True when value can be interpreted as a canonical 6-step log level."""
    try:
        parse_log_level(value)
    except (TypeError, ValueError):
        return False
    return True
