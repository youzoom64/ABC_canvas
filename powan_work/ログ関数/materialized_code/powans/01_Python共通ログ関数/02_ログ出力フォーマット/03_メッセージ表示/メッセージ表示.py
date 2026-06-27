# powan_id: node-b867eee2fd
# title: メッセージ表示
# parent: node-c6a89ade0d
# powanKind: nerve
# codeLanguage: python

from __future__ import annotations

from typing import Any


def message_to_text(value: object) -> str:
    """Return a display-safe text form for any log message value."""
    if value is None:
        return ''
    try:
        return str(value)
    except Exception as exc:
        return f'<unprintable message: {type(exc).__name__}>'


def limit_message_length(message: str, max_length: int | None = None, suffix: str = '...') -> str:
    """Trim a log message without letting the display exceed max_length."""
    text = str(message)
    if max_length is None or max_length < 0 or len(text) <= max_length:
        return text
    if max_length <= 0:
        return ''
    if max_length <= len(suffix):
        return suffix[:max_length]
    return text[: max_length - len(suffix)] + suffix


def format_multiline_message(message: str, indent: str = '    ') -> str:
    """Indent continuation lines so multi-line log messages stay readable."""
    text = str(message)
    lines = text.splitlines()
    if len(lines) <= 1:
        return text
    return lines[0] + '\n' + '\n'.join(indent + line for line in lines[1:])


def format_message(
    value: Any,
    *,
    max_length: int | None = None,
    indent: str = '    ',
    suffix: str = '...',
) -> str:
    """Convert, shorten, and align a log message for human-readable output."""
    text = message_to_text(value)
    text = limit_message_length(text, max_length=max_length, suffix=suffix)
    return format_multiline_message(text, indent=indent)


__all__ = [
    'format_message',
    'format_multiline_message',
    'limit_message_length',
    'message_to_text',
]
