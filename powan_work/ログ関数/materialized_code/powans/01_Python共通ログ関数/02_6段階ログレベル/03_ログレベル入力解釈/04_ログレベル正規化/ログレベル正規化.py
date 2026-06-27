# powan_id: node-bfac90b06b
# title: ログレベル正規化
# parent: node-b56f0cd50f
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from numbers import Integral, Real
from typing import Any, Final

VALID_LOG_LEVELS: Final[tuple[str, ...]] = (
    "trace",
    "debug",
    "info",
    "warning",
    "error",
    "critical",
)

LOG_LEVEL_VALUES: Final[dict[str, int]] = {
    "trace": 5,
    "debug": 10,
    "info": 20,
    "warning": 30,
    "error": 40,
    "critical": 50,
}

LOG_LEVEL_ALIASES: Final[dict[str, str]] = {
    "all": "trace",
    "verbose": "trace",
    "trace": "trace",
    "dbg": "debug",
    "debug": "debug",
    "information": "info",
    "informational": "info",
    "inf": "info",
    "info": "info",
    "notice": "info",
    "warn": "warning",
    "warning": "warning",
    "warnings": "warning",
    "err": "error",
    "error": "error",
    "exception": "error",
    "fatal": "critical",
    "crit": "critical",
    "critical": "critical",
    "panic": "critical",
}

_NUMERIC_LEVELS: Final[dict[int, str]] = {
    0: "trace",
    1: "debug",
    2: "info",
    3: "warning",
    4: "error",
    5: "critical",
    10: "debug",
    20: "info",
    30: "warning",
    40: "error",
    50: "critical",
}


def resolve_log_level_alias(level: str) -> str:
    """Resolve a normalized text level or alias to the canonical log level name."""
    key = _normalize_level_text(level)
    return LOG_LEVEL_ALIASES.get(key, key)


def validate_log_level(level: str) -> str:
    """Return the canonical level when valid, otherwise raise a readable ValueError."""
    if level in VALID_LOG_LEVELS:
        return level

    valid = ", ".join(VALID_LOG_LEVELS)
    aliases = ", ".join(sorted(name for name in LOG_LEVEL_ALIASES if name not in VALID_LOG_LEVELS))
    raise ValueError(
        f"Unknown log level {level!r}. Expected one of: {valid}. "
        f"Accepted aliases include: {aliases}."
    )


def normalize_log_level(level: Any, *, default: str | None = None) -> str:
    """Normalize external log-level input to trace/debug/info/warning/error/critical.

    Strings are stripped, case-folded, and matched against aliases such as
    warn, fatal, and verbose. Integers accept both compact ranks 0..5 and
    common logging values 5/10/20/30/40/50. None may use an explicit default.
    """
    if level is None:
        if default is None:
            raise ValueError(
                "Log level is None. Pass a log level or provide a default such as 'info'."
            )
        level = default

    if isinstance(level, bool):
        raise ValueError("Boolean values are not valid log levels. Use a level name instead.")

    if isinstance(level, str):
        candidate = resolve_log_level_alias(level)
        return validate_log_level(candidate)

    if isinstance(level, Integral):
        candidate = _NUMERIC_LEVELS.get(int(level))
        if candidate is None:
            raise ValueError(
                f"Unknown numeric log level {level!r}. Expected rank 0..5 or logging value "
                "5, 10, 20, 30, 40, or 50."
            )
        return candidate

    if isinstance(level, Real):
        if level.is_integer():
            return normalize_log_level(int(level), default=default)
        raise ValueError(
            f"Numeric log level {level!r} is not an integer. Expected rank 0..5 or "
            "logging value 5, 10, 20, 30, 40, or 50."
        )

    raise ValueError(
        f"Unsupported log level type {type(level).__name__}. "
        "Expected str, int, float integer value, or None with a default."
    )


def _normalize_level_text(level: str) -> str:
    text = level.strip().casefold().replace("-", "_").replace(" ", "_")
    while "__" in text:
        text = text.replace("__", "_")
    text = text.strip("_")
    if not text:
        raise ValueError("Log level is empty. Expected trace, debug, info, warning, error, or critical.")
    return text


__all__ = [
    "VALID_LOG_LEVELS",
    "LOG_LEVEL_VALUES",
    "LOG_LEVEL_ALIASES",
    "normalize_log_level",
    "resolve_log_level_alias",
    "validate_log_level",
]
