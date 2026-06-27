# powan_id: node-882a905330
# title: 簡潔フォーマット生成
# parent: node-14cf6a99bc
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CompactConsoleFormat:
    """A compact console logging format and optional Formatter instance."""

    template: str
    formatter: logging.Formatter


def compact_console_template(*, level_width: int = 1, bracket_level: bool = True) -> str:
    """Return a short token template for console log lines.

    The template uses neutral tokens so the parent powan can adapt it to its own
    formatting pipeline: ``{level}`` for severity and ``{message}`` for text.
    """
    width = max(1, int(level_width))
    level = "{level}" if width == 1 else "{level:<%d}" % width
    if bracket_level:
        level = f"[{level}]"
    return f"{level} {{message}}"


def compact_logging_format(*, one_letter_level: bool = True) -> str:
    """Return a ``logging.Formatter`` compatible compact format string."""
    level_field = "%(levelname).1s" if one_letter_level else "%(levelname)s"
    return f"[{level_field}] %(message)s"


def make_compact_console_formatter(
    *,
    one_letter_level: bool = True,
    datefmt: str | None = None,
    style: str = "%",
) -> logging.Formatter:
    """Create a compact ``logging.Formatter`` for console output."""
    if style != "%":
        raise ValueError("compact console formatter uses percent-style logging fields")
    return logging.Formatter(
        compact_logging_format(one_letter_level=one_letter_level),
        datefmt=datefmt,
        style=style,
    )


def generate_compact_console_format(
    *,
    as_formatter: bool = False,
    one_letter_level: bool = True,
    level_width: int = 1,
    bracket_level: bool = True,
    datefmt: str | None = None,
) -> str | CompactConsoleFormat:
    """Generate the compact console format for this organ powan.

    By default this returns ``[{level}] {message}`` style text.  When
    ``as_formatter`` is true it also returns a ready-to-use ``logging.Formatter``.
    """
    template = compact_console_template(level_width=level_width, bracket_level=bracket_level)
    if not as_formatter:
        return template
    return CompactConsoleFormat(
        template=template,
        formatter=make_compact_console_formatter(
            one_letter_level=one_letter_level,
            datefmt=datefmt,
        ),
    )


def format_compact_console_line(
    level: Any,
    message: Any,
    *,
    level_width: int = 1,
    bracket_level: bool = True,
) -> str:
    """Render one compact console line without requiring ``logging``."""
    width = max(1, int(level_width))
    level_text = str(level or "INFO").strip().upper() or "INFO"
    level_text = level_text[:width].ljust(width)
    if bracket_level:
        level_text = f"[{level_text}]"
    return f"{level_text} {message}"


__all__ = [
    "CompactConsoleFormat",
    "compact_console_template",
    "compact_logging_format",
    "format_compact_console_line",
    "generate_compact_console_format",
    "make_compact_console_formatter",
]
