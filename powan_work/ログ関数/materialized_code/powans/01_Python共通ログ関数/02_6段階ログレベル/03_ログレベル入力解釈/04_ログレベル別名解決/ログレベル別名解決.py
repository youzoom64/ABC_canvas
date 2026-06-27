# powan_id: node-fb1ea5b224
# title: ログレベル別名解決
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


def normalize_log_level_text(level: str) -> str:
    """Normalize a textual log-level input before alias lookup."""
    if not isinstance(level, str):
        raise TypeError(f"log level must be str, got {type(level).__name__}")

    normalized = "_".join(level.strip().casefold().replace("-", " " ).split())
    if not normalized:
        raise ValueError("log level must not be empty")
    return normalized


def resolve_log_level_alias(level: str) -> str:
    """Resolve a log-level name or alias to one of the official six level names."""
    normalized = normalize_log_level_text(level)

    try:
        return LOG_LEVEL_ALIASES[normalized]
    except KeyError as exc:
        expected = ", ".join(VALID_LOG_LEVELS)
        aliases = ", ".join(sorted(LOG_LEVEL_ALIASES))
        raise ValueError(
            f"unknown log level alias {level!r}; expected one of {expected}; "
            f"known aliases: {aliases}"
        ) from exc
