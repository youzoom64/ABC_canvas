# powan_id: node-99d3ab89c7
# title: レベル表示名整形
# parent: node-bbc4e005cb
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

import logging
from typing import Any

DEFAULT_LEVEL_WIDTH = 8
DEFAULT_LEVEL_NAME = "INFO"


def normalize_level_name(level: Any, *, default: str = DEFAULT_LEVEL_NAME) -> str:
    """Return a clean logging level name for numbers, names, and LogRecord objects."""
    if isinstance(level, logging.LogRecord):
        candidate = level.levelname
    elif isinstance(level, int):
        candidate = logging.getLevelName(level)
    elif level is None:
        candidate = default
    else:
        candidate = level

    text = str(candidate if candidate is not None else default).strip()
    if not text or text.startswith("Level "):
        text = str(default).strip() or DEFAULT_LEVEL_NAME
    return text.upper()


def format_level_label(
    level: Any,
    *,
    width: int = DEFAULT_LEVEL_WIDTH,
    default: str = DEFAULT_LEVEL_NAME,
    align: str = "left",
    overflow: str = "clip",
) -> str:
    """Format a logging level name as a stable-width console label.

    The function only prepares the level label. It does not configure logging,
    create handlers, or print output.
    """
    size = max(1, int(width))
    label = normalize_level_name(level, default=default)

    if len(label) > size:
        if overflow == "keep":
            return label
        if overflow == "ellipsis" and size > 1:
            label = label[: size - 1] + "…"
        else:
            label = label[:size]

    if align == "right":
        return label.rjust(size)
    if align == "center":
        return label.center(size)
    return label.ljust(size)


def format_bracketed_level(level: Any, *, width: int = DEFAULT_LEVEL_WIDTH) -> str:
    """Return a bracketed stable-width level label such as '[INFO    ]'."""
    return f"[{format_level_label(level, width=width)}]"


__all__ = [
    "DEFAULT_LEVEL_WIDTH",
    "DEFAULT_LEVEL_NAME",
    "normalize_level_name",
    "format_level_label",
    "format_bracketed_level",
]
