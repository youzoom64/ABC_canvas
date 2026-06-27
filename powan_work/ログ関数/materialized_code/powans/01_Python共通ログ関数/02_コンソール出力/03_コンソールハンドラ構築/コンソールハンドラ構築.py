# powan_id: node-37cb41da55
# title: コンソールハンドラ構築
# parent: node-30e768b421
# powanKind: nerve
# codeLanguage: python

"""Build a console StreamHandler with level, formatter, and stable name.

This nerve powan bundles the four console-handler organs: create the stream
handler, apply its level, attach the selected formatter, and set a stable name
for later duplicate checks.
"""

from __future__ import annotations

import logging
import sys
from typing import TextIO

DEFAULT_CONSOLE_FORMAT = "%(levelname)s:%(name)s:%(message)s"
DEFAULT_CONSOLE_HANDLER_NAME = "console"


def create_stream_handler(stream: TextIO | None = None) -> logging.StreamHandler:
    """Return a StreamHandler aimed at the requested console stream."""
    return logging.StreamHandler(stream if stream is not None else sys.stderr)


def apply_handler_level(
    handler: logging.Handler,
    level: int | str | None,
    *,
    default: int = logging.INFO,
) -> logging.Handler:
    """Set ``handler`` to the resolved logging level and return it."""
    handler.setLevel(default if level is None else level)
    return handler


def apply_formatter(
    handler: logging.Handler,
    formatter: logging.Formatter | str | None = None,
) -> logging.Handler:
    """Set a formatter on ``handler`` and return it."""
    if formatter is None:
        selected = logging.Formatter(DEFAULT_CONSOLE_FORMAT)
    elif isinstance(formatter, str):
        selected = logging.Formatter(formatter)
    else:
        selected = formatter
    handler.setFormatter(selected)
    return handler


def set_handler_name(
    handler: logging.Handler,
    name: str | None = DEFAULT_CONSOLE_HANDLER_NAME,
) -> logging.Handler:
    """Assign a stable name to ``handler`` and return it."""
    clean_name = (name or DEFAULT_CONSOLE_HANDLER_NAME).strip()
    handler.set_name(clean_name or DEFAULT_CONSOLE_HANDLER_NAME)
    return handler


def build_console_handler(
    *,
    stream: TextIO | None = None,
    level: int | str | None = logging.INFO,
    formatter: logging.Formatter | str | None = None,
    name: str | None = DEFAULT_CONSOLE_HANDLER_NAME,
) -> logging.StreamHandler:
    """Create and configure one console StreamHandler."""
    handler = create_stream_handler(stream)
    apply_handler_level(handler, level)
    apply_formatter(handler, formatter)
    set_handler_name(handler, name)
    return handler


__all__ = [
    "DEFAULT_CONSOLE_FORMAT",
    "DEFAULT_CONSOLE_HANDLER_NAME",
    "apply_formatter",
    "apply_handler_level",
    "build_console_handler",
    "create_stream_handler",
    "set_handler_name",
]
