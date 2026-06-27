# powan_id: node-30e768b421
# title: コンソール出力
# parent: node-704b909f82
# powanKind:
# codeLanguage: python

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from typing import Any, Mapping, TextIO


@dataclass(frozen=True)
class ConsoleOutputResult:
    """Result of configuring console output for a logger."""

    logger: logging.Logger
    handler: logging.StreamHandler | None
    enabled: bool
    stream_name: str
    level: int | str
    color_enabled: bool


class ConsoleFormatter(logging.Formatter):
    """Small formatter for readable console log lines."""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[1;31m",
    }
    RESET = "\033[0m"

    def __init__(self, *, compact: bool = True, color: bool = False) -> None:
        fmt = "[%(levelname)s] %(message)s" if compact else "%(levelname)s:%(name)s:%(message)s"
        super().__init__(fmt)
        self.color = color

    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        if not self.color:
            return rendered
        color_code = self.COLORS.get(record.levelname, "")
        if not color_code:
            return rendered
        return f"{color_code}{rendered}{self.RESET}"


def configure_console_output(
    logger: logging.Logger,
    *,
    level: int | str = logging.INFO,
    enabled: bool = True,
    stream: TextIO | None = None,
    stream_name: str | None = None,
    compact: bool = True,
    color: bool | None = None,
    handler_name: str = "console",
    replace_existing: bool = False,
) -> ConsoleOutputResult:
    """Configure standard-library console logging for one logger.

    This powan owns the visible console path: choose a stream, build a
    StreamHandler, apply level and readable formatting, optionally color output,
    and avoid duplicate console handlers unless replacement is requested.
    """

    chosen_stream, chosen_name = _resolve_stream(stream, stream_name, level)
    color_enabled = _resolve_color(color, chosen_stream)

    if not enabled:
        return ConsoleOutputResult(logger, None, False, chosen_name, level, color_enabled)

    existing = _find_named_handler(logger, handler_name)
    if existing is not None:
        if not replace_existing:
            return ConsoleOutputResult(logger, existing, True, chosen_name, level, color_enabled)
        logger.removeHandler(existing)

    handler = logging.StreamHandler(chosen_stream)
    handler.set_name(handler_name)
    handler.setLevel(level)
    handler.setFormatter(ConsoleFormatter(compact=compact, color=color_enabled))
    logger.addHandler(handler)
    return ConsoleOutputResult(logger, handler, True, chosen_name, level, color_enabled)


def _resolve_stream(stream: TextIO | None, stream_name: str | None, level: int | str) -> tuple[TextIO, str]:
    if stream is not None:
        return stream, stream_name or "custom"
    if stream_name in {"stdout", "out"}:
        return sys.stdout, "stdout"
    if stream_name in {"stderr", "err"}:
        return sys.stderr, "stderr"
    numeric_level = logging.getLevelName(str(level).upper()) if isinstance(level, str) else level
    if isinstance(numeric_level, int) and numeric_level >= logging.WARNING:
        return sys.stderr, "stderr"
    return sys.stdout, "stdout"


def _resolve_color(color: bool | None, stream: TextIO) -> bool:
    if color is not None:
        return bool(color)
    return bool(getattr(stream, "isatty", lambda: False)())


def _find_named_handler(logger: logging.Logger, name: str) -> logging.StreamHandler | None:
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and handler.get_name() == name:
            return handler
    return None


__all__ = [
    "ConsoleFormatter",
    "ConsoleOutputResult",
    "configure_console_output",
]
