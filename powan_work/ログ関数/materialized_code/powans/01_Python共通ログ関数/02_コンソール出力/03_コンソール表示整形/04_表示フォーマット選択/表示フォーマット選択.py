# powan_id: node-14cf6a99bc
# title: 表示フォーマット選択
# parent: node-bbc4e005cb
# powanKind: nerve
# codeLanguage: python

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ConsoleFormatChoice:
    """A selected console log format and its display traits."""

    style: str
    template: str
    includes_timestamp: bool = False
    includes_logger_name: bool = False
    includes_location: bool = False


_COMPACT = ConsoleFormatChoice(
    style="compact",
    template="[{level}] {message}",
)

_FORMATS: dict[str, ConsoleFormatChoice] = {
    "compact": _COMPACT,
    "simple": _COMPACT,
    "short": _COMPACT,
    "default": _COMPACT,
    "dev": ConsoleFormatChoice(
        style="dev",
        template="[{level}] {name}: {message}",
        includes_logger_name=True,
    ),
    "debug": ConsoleFormatChoice(
        style="debug",
        template="[{level}] {name} {location}: {message}",
        includes_logger_name=True,
        includes_location=True,
    ),
    "timestamp": ConsoleFormatChoice(
        style="timestamp",
        template="{timestamp} [{level}] {message}",
        includes_timestamp=True,
    ),
    "time": ConsoleFormatChoice(
        style="timestamp",
        template="{timestamp} [{level}] {message}",
        includes_timestamp=True,
    ),
    "timestamp-dev": ConsoleFormatChoice(
        style="timestamp-dev",
        template="{timestamp} [{level}] {name}: {message}",
        includes_timestamp=True,
        includes_logger_name=True,
    ),
    "dev-timestamp": ConsoleFormatChoice(
        style="timestamp-dev",
        template="{timestamp} [{level}] {name}: {message}",
        includes_timestamp=True,
        includes_logger_name=True,
    ),
}


def normalize_console_style(style: Any = None, *, include_timestamp: bool | None = None, developer: bool = False) -> str:
    """Return the canonical style key for console format selection."""
    key = str(style or "compact").strip().lower().replace("_", "-")
    key = key if key in _FORMATS else "compact"

    wants_time = include_timestamp if include_timestamp is not None else _FORMATS[key].includes_timestamp
    wants_dev = developer or _FORMATS[key].includes_logger_name or _FORMATS[key].includes_location

    if wants_time and wants_dev:
        return "timestamp-dev"
    if wants_time:
        return "timestamp"
    if wants_dev:
        return "dev" if key != "debug" else "debug"
    return "compact"


def choose_console_format(
    style: Any = "compact",
    *,
    include_timestamp: bool | None = None,
    developer: bool = False,
    custom_formats: Mapping[str, str] | None = None,
) -> ConsoleFormatChoice:
    """Choose a console output template for compact, dev, or timestamped display."""
    key = normalize_console_style(style, include_timestamp=include_timestamp, developer=developer)
    if custom_formats:
        custom_key = str(style or "").strip().lower().replace("_", "-")
        if custom_key in custom_formats:
            template = str(custom_formats[custom_key])
            return ConsoleFormatChoice(
                style=custom_key,
                template=template,
                includes_timestamp="{timestamp}" in template,
                includes_logger_name="{name}" in template,
                includes_location="{location}" in template,
            )
    return _FORMATS[key]


def select_console_format(style: Any = "compact", **options: Any) -> str:
    """Return only the format template expected by a console log formatter."""
    return choose_console_format(style, **options).template


__all__ = [
    "ConsoleFormatChoice",
    "choose_console_format",
    "normalize_console_style",
    "select_console_format",
]
