# powan_id: node-ea7ec15e5f
# title: レベル幅揃え
# parent: node-e0dbd11130
# powanKind: organ
# codeLanguage: python

"""Helpers for aligning log level labels.

This organ powan keeps stacked log lines easy to scan by normalizing a
level name and padding it to a predictable display width.
"""

from __future__ import annotations

from typing import Mapping, Sequence


DEFAULT_LEVEL_WIDTH = 8

_LEVEL_ALIASES: Mapping[str, str] = {
    "WARN": "WARNING",
    "WARNING": "WARNING",
    "ERR": "ERROR",
    "ERROR": "ERROR",
    "FATAL": "CRITICAL",
    "CRIT": "CRITICAL",
    "CRITICAL": "CRITICAL",
    "INFO": "INFO",
    "DEBUG": "DEBUG",
    "TRACE": "TRACE",
    "NOTSET": "NOTSET",
}


def normalize_level_name(level_name: object, aliases: Mapping[str, str] | None = None) -> str:
    """Return a stable upper-case log level name before alignment."""
    text = str(level_name or "NOTSET").strip().upper()
    if not text:
        text = "NOTSET"
    table = aliases or _LEVEL_ALIASES
    return table.get(text, text)


def align_level_name(level_name: object, width: int = DEFAULT_LEVEL_WIDTH) -> str:
    """Return the normalized level name padded on the right.

    A width of 0 or less means "do not pad"; the normalized level name is
    returned unchanged so callers can explicitly disable column alignment.
    """
    clean = normalize_level_name(level_name)
    if width <= 0:
        return clean
    return clean.ljust(width)


def format_aligned_level(level: object, width: int = DEFAULT_LEVEL_WIDTH, bracketed: bool = False) -> str:
    """Format a log level for display in a log line.

    When bracketed is true, padding stays inside the brackets so every line
    keeps the same visual column, such as [INFO    ] and [WARNING ].
    """
    aligned = align_level_name(level, width)
    if bracketed:
        return f"[{aligned}]"
    return aligned


def alignment_width_for(level_names: Sequence[object], minimum: int = DEFAULT_LEVEL_WIDTH) -> int:
    """Choose a width that fits a group of level names without shrinking below minimum."""
    if minimum < 0:
        minimum = 0
    names = [normalize_level_name(level_name) for level_name in level_names]
    longest = max((len(name) for name in names), default=0)
    return max(minimum, longest)
