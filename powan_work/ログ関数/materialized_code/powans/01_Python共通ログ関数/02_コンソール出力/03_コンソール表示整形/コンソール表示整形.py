# powan_id: node-bbc4e005cb
# title: コンソール表示整形
# parent: node-30e768b421
# powanKind: nerve
# codeLanguage: python

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Mapping

LevelFormatter = Callable[[Any], str]
MessageSanitizer = Callable[[Any], str]


def default_level_formatter(level: Any, width: int = 5) -> str:
    """Return an uppercase, fixed-width level label for console output."""
    text = str(level if level is not None else "INFO").strip().upper() or "INFO"
    return text[:width].ljust(width)


def default_message_sanitizer(message: Any) -> str:
    """Make a message safe to print on a single console log line."""
    if message is None:
        return ""
    text = str(message)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return " \u23ce ".join(part.strip() for part in text.split("\n"))


def select_console_format(style: str = "compact") -> str:
    """Choose the template used by format_console_log."""
    styles = {
        "compact": "[{level}] {message}",
        "dev": "[{level}] {name}: {message}",
        "timestamp": "{timestamp} [{level}] {message}",
        "timestamp-dev": "{timestamp} [{level}] {name}: {message}",
    }
    return styles.get(str(style or "compact").strip().lower(), styles["compact"])


def format_console_log(
    level: Any,
    message: Any,
    *,
    name: str = "console",
    style: str = "compact",
    timestamp: datetime | None = None,
    level_formatter: LevelFormatter = default_level_formatter,
    message_sanitizer: MessageSanitizer = default_message_sanitizer,
    extra: Mapping[str, Any] | None = None,
) -> str:
    """Format a console log line by joining format choice, level label, and safe message."""
    when = timestamp or datetime.now(timezone.utc).astimezone()
    values: dict[str, Any] = {
        "timestamp": when.isoformat(timespec="seconds"),
        "level": level_formatter(level),
        "name": str(name or "console"),
        "message": message_sanitizer(message),
    }
    if extra:
        values.update(extra)
    return select_console_format(style).format_map(_MissingAsEmpty(values))


class _MissingAsEmpty(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return ""


__all__ = [
    "default_level_formatter",
    "default_message_sanitizer",
    "select_console_format",
    "format_console_log",
]
