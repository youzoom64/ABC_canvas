# powan_id: node-f40ed83058
# title: ログレベル妥当性検査
# parent: node-b56f0cd50f
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

VALID_LOG_LEVELS: tuple[str, ...] = (
    "trace",
    "debug",
    "info",
    "warning",
    "error",
    "critical",
)

VALID_LOG_LEVEL_SET: frozenset[str] = frozenset(VALID_LOG_LEVELS)

LOG_LEVEL_ALIASES: dict[str, str] = {
    "verbose": "trace",
    "v": "trace",
    "trc": "trace",
    "dbg": "debug",
    "information": "info",
    "notice": "info",
    "warn": "warning",
    "err": "error",
    "exception": "error",
    "crit": "critical",
    "fatal": "critical",
    "panic": "critical",
}


def _format_valid_levels() -> str:
    return ", ".join(VALID_LOG_LEVELS)


def _format_alias_examples() -> str:
    examples = (
        "verbose->trace",
        "warn->warning",
        "err->error",
        "fatal->critical",
    )
    return ", ".join(examples)


def format_log_level_error(level: object) -> str:
    """Return a readable validation error message for an invalid log level."""
    return (
        f"invalid log level {level!r}; expected one of: {_format_valid_levels()}. "
        f"Common aliases before validation include: {_format_alias_examples()}."
    )


def validate_log_level(level: str) -> str:
    """Validate and return a canonical 6-step log level name.

    This organ accepts only canonical names. Alias resolution belongs to the
    surrounding log-level interpretation nerve before this validator is called.
    """
    if not isinstance(level, str):
        raise ValueError(format_log_level_error(level))

    if level not in VALID_LOG_LEVEL_SET:
        raise ValueError(format_log_level_error(level))

    return level
